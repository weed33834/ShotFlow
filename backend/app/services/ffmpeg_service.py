"""ffmpeg 成片合成服务 — 拼接视频/图片 + 混音 + 烧录字幕。

替代 tools_service.assemble() 中的 NotImplementedError 空壳，完成
"链路最后一步"：把各 provider 产出的离散资产合成为最终成片。

设计参考：
- NarratoAI generate_video.py 的 _build_ffmpeg_merge_command：filter_complex
  分号分隔各轨、amix normalize=0 防音量稀释、subtitles 滤镜烧录字幕。
- MoneyPrinterTurbo video.py 的 concat_video_clips_with_ffmpeg：concat demuxer
  拼接多段视频。

合成管线（多 pass，兼顾正确性与可读性）：
  1. 图片 → 视频片段（-loop 1 -t dur -c:v libx264）
  2. 所有片段归一化到统一编码/分辨率/帧率（因不同 provider 产出格式不一，
     必须归一化后 concat -c copy 才不会花屏）
  3. concat demuxer 拼接（-f concat -safe 0 -c copy）
  4. 最终 pass：amix 混音（normalize=0）+ subtitles/drawtext 烧字幕 → 输出
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings
from app.services.audio_normalizer import normalize_audio_for_mixing
from app.services.ffmpeg_hwaccel import get_optimal_ffmpeg_encoder
from app.services.subtitle_service import generate_srt_from_durations

logger = logging.getLogger(__name__)

# 图片扩展名 → 需 -loop 1 转视频片段
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
# 视频扩展名
_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v"}
# 音频扩展名
_AUDIO_EXTS = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"}

_DEFAULT_IMAGE_DURATION = 3.0
_DEFAULT_RESOLUTION = (1280, 720)
_DEFAULT_FPS = 30
# 单次 ffmpeg 调用超时（秒），防止卡死
_FFMPEG_TIMEOUT = 1800

# 画面比例 → 目标分辨率映射（用户前端选择后直接控制输出尺寸）
_ASPECT_RESOLUTIONS: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:3": (1440, 1080),
    "3:4": (1080, 1440),
}


def _resolve_aspect_resolution(video_aspect: str, probe_resolution: tuple[int, int]) -> tuple[int, int]:
    """根据用户选择的画面比例返回目标分辨率。

    有明确比例时直接映射；空串时用探测到的首个资产分辨率，探测失败兜底默认值。
    """
    if video_aspect and video_aspect in _ASPECT_RESOLUTIONS:
        return _ASPECT_RESOLUTIONS[video_aspect]
    return probe_resolution if probe_resolution != _DEFAULT_RESOLUTION else _DEFAULT_RESOLUTION

# drawtext 兜底字体候选（subtitles 滤镜不可用时用 drawtext 烧字幕）
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]


# --------------------------------------------------------------------------- #
# ffmpeg 可用性检查（延迟，import 本模块不触发）
# --------------------------------------------------------------------------- #


def _resolve_ffmpeg_binary() -> str:
    """解析 ffmpeg 二进制路径：优先 settings.FFMPEG_PATH，否则 PATH 查找。"""
    if settings.FFMPEG_PATH:
        p = Path(settings.FFMPEG_PATH)
        if p.exists():
            return str(p)
        logger.warning("配置的 FFMPEG_PATH 不存在: %s，回退到 PATH 查找", settings.FFMPEG_PATH)
    return shutil.which("ffmpeg") or ""


def _resolve_ffprobe_binary() -> str:
    """解析 ffprobe：与 ffmpeg 同目录，否则 PATH 查找。"""
    if settings.FFMPEG_PATH:
        probe = Path(settings.FFMPEG_PATH).parent / "ffprobe"
        if probe.exists():
            return str(probe)
    return shutil.which("ffprobe") or ""


def is_ffmpeg_available() -> bool:
    """检查 ffmpeg 是否可用。延迟调用，模块 import 不报错。"""
    return bool(_resolve_ffmpeg_binary())


# --------------------------------------------------------------------------- #
# 底层执行
# --------------------------------------------------------------------------- #


def _run_ffmpeg(args: list[str], desc: str = "ffmpeg") -> None:
    """执行 ffmpeg，失败抛 RuntimeError 带完整 stderr。"""
    binary = _resolve_ffmpeg_binary()
    if not binary:
        raise RuntimeError(
            "ffmpeg 不可用：未配置 FFMPEG_PATH 且 PATH 中未找到 ffmpeg。"
            "请安装 ffmpeg 或在 .env 中设置 FFMPEG_PATH。"
        )
    # 在可用时将 libx264 替换为硬件加速编码器（如 h264_nvenc）。
    # 仅替换编码器名称、不追加 -hwaccel 解码参数，避免破坏 filter_complex 滤镜链。
    optimal_encoder = get_optimal_ffmpeg_encoder()
    if optimal_encoder != "libx264":
        args = [optimal_encoder if a == "libx264" else a for a in args]
    cmd = [binary, "-hide_banner"] + args
    logger.info("[ffmpeg] %s", desc)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=_FFMPEG_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"{desc} 超时（>{_FFMPEG_TIMEOUT}s）\n命令: {' '.join(cmd)}") from e
    if proc.returncode != 0:
        raise RuntimeError(
            f"{desc} 失败 (exit={proc.returncode})\n"
            f"命令: {' '.join(cmd)}\n"
            f"stderr:\n{proc.stderr[-3000:]}"
        )


def _probe_duration(path: Path) -> float:
    """ffprobe 探测时长（秒），失败返回 0。"""
    binary = _resolve_ffprobe_binary()
    if not binary:
        return 0.0
    try:
        proc = subprocess.run(
            [binary, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return float(proc.stdout.strip())
    except Exception:
        pass
    return 0.0


def _probe_resolution(path: Path) -> tuple[int, int]:
    """ffprobe 探测分辨率，失败返回默认 1280x720。"""
    binary = _resolve_ffprobe_binary()
    if not binary:
        return _DEFAULT_RESOLUTION
    try:
        proc = subprocess.run(
            [binary, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=s=x:p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parts = proc.stdout.strip().split("x")
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
    except Exception:
        pass
    return _DEFAULT_RESOLUTION


def _find_font() -> str:
    """查找可用字体文件供 drawtext 使用。"""
    for f in _FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return ""


# --------------------------------------------------------------------------- #
# 路径安全
# --------------------------------------------------------------------------- #


def _validate_input_path(p: str) -> Path:
    """校验输入路径存在且是文件，防止传入不存在或恶意路径。"""
    if not p:
        raise ValueError("资产路径为空")
    # URL 资产无法直接喂给 ffmpeg，需先下载到本地
    if p.startswith(("http://", "https://", "rtmp://", "rtsp://")):
        raise ValueError(
            f"assemble 需要本地文件路径，不支持 URL 资产: {p}。"
            "请先将资产下载到本地存储。"
        )
    path = Path(p).resolve()
    if not path.exists():
        raise FileNotFoundError(f"资产文件不存在: {p}")
    if not path.is_file():
        raise ValueError(f"资产路径不是文件: {p}")
    return path


def _default_output_path(task_id: str) -> Path:
    """生成默认输出路径：STORAGE_DIR/assembled/assemble_{task_id}.mp4。"""
    storage = Path(settings.STORAGE_DIR) / "assembled"
    storage.mkdir(parents=True, exist_ok=True)
    return storage / f"assemble_{task_id}.mp4"


def _validate_output_path(p: str) -> Path:
    """校验输出路径：父目录可创建，后缀确保 .mp4。"""
    path = Path(p).resolve()
    if path.suffix.lower() != ".mp4":
        path = path.with_suffix(".mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------- #
# 资产分类（供 tools_service 复用）
# --------------------------------------------------------------------------- #


def classify_asset(asset_type: str, path: str) -> str:
    """按 asset_type + 扩展名分类资产为 audio / image / video。"""
    ext = Path(path).suffix.lower()
    if asset_type == "audio" or ext in _AUDIO_EXTS:
        return "audio"
    if asset_type == "image" or ext in _IMAGE_EXTS:
        return "image"
    return "video"


# --------------------------------------------------------------------------- #
# 段落准备
# --------------------------------------------------------------------------- #


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in _IMAGE_EXTS


def _scale_filter(w: int, h: int, fps: int) -> str:
    """统一缩放+填充+帧率滤镜，保证所有片段分辨率一致后 concat -c copy 可用。

    force_original_aspect_ratio=decrease + pad 保持原比例并黑边填充到目标尺寸，
    避免不同分辨率的片段直接 concat 导致画面错位。
    """
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
        f"setsar=1,fps={fps}"
    )


def _compute_image_duration(
    audio_input: Path | None,
    num_images: int,
    subtitle_durations: list[float] | None,
) -> float:
    """推算每张图片的展示时长。

    优先用配音时长均分（图片配旁白是最常见场景），其次用字幕总时长均分，
    最后兜底默认值。保证图片片段不会过短或过长。
    """
    if num_images == 0:
        return _DEFAULT_IMAGE_DURATION
    if audio_input:
        dur = _probe_duration(audio_input)
        if dur > 0:
            return max(1.0, dur / num_images)
    if subtitle_durations:
        total = sum(subtitle_durations)
        if total > 0:
            return max(1.0, total / num_images)
    return _DEFAULT_IMAGE_DURATION


def _prepare_segments(
    asset_paths: list[Path],
    image_duration: float,
    resolution: tuple[int, int],
    fps: int,
    work_dir: Path,
) -> list[Path]:
    """把图片转视频片段 + 归一化视频片段，统一为 libx264/yuv420p 同分辨率。

    所有片段统一去除音轨（-an），因为音频在最终 pass 单独用 amix 混入，
    避免拼接时音轨对不齐。
    """
    w, h = resolution
    segments: list[Path] = []
    for idx, ap in enumerate(asset_paths):
        out = work_dir / f"seg_{idx:04d}.mp4"
        if _is_image(ap):
            # -loop 1 让单张图片循环输出，-t 限定时长
            _run_ffmpeg([
                "-loop", "1", "-i", str(ap),
                "-t", f"{image_duration:.3f}",
                "-vf", _scale_filter(w, h, fps),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-an",
                "-y", str(out),
            ], desc=f"图片转视频片段 {ap.name}")
        else:
            _run_ffmpeg([
                "-i", str(ap),
                "-vf", _scale_filter(w, h, fps),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-an",
                "-y", str(out),
            ], desc=f"视频归一化 {ap.name}")
        segments.append(out)
    return segments


def _concat_segments(segments: list[Path], work_dir: Path) -> Path:
    """concat demuxer 拼接所有片段。

    首选 -c copy（因已归一化编码参数），若因 SPS/PPS 不一致失败则回退重编码。
    """
    list_file = work_dir / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for seg in segments:
            # concat demuxer 的 file 指令需单引号包裹路径，转义路径中的单引号
            safe = str(seg).replace("'", r"'\''")
            f.write(f"file '{safe}'\n")
    out = work_dir / "concat.mp4"
    try:
        _run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy",
            "-y", str(out),
        ], desc="concat 拼接 (-c copy)")
    except RuntimeError:
        # -c copy 可能因 H.264 SPS/PPS 不一致失败，回退重编码保证可拼接
        logger.warning("concat -c copy 失败，回退到重编码拼接")
        _run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an",
            "-y", str(out),
        ], desc="concat 拼接 (重编码)")
    return out


# --------------------------------------------------------------------------- #
# 字幕滤镜构建
# --------------------------------------------------------------------------- #


def _escape_filter_path(path: str) -> str:
    """转义 filter_complex 中文件路径的特殊字符（冒号分隔选项、反斜杠转义）。"""
    return path.replace("\\", "\\\\").replace(":", "\\:")


def _build_subtitles_filter(srt_path: Path) -> str:
    """构建 subtitles 滤镜链（需 libass），烧录 SRT 到画面。"""
    escaped = _escape_filter_path(str(srt_path))
    return f"[0:v]subtitles='{escaped}'[vsub]"


def _build_drawtext_filter(
    subtitles: list[str],
    durations: list[float],
    fontfile: str,
    work_dir: Path,
) -> str:
    """构建 drawtext 滤镜链（subtitles 不可用时的兜底）。

    每条字幕写入单独的 txt 文件用 textfile 引用，绕开 drawtext text= 的转义地狱。
    """
    current = 0.0
    draws: list[str] = []
    for i, text in enumerate(subtitles):
        dur = max(0.1, float(durations[i])) if durations and i < len(durations) else 3.0
        start = current
        end = current + dur
        current = end
        # 写入临时文件，避免 text= 参数的特殊字符转义问题
        txt_file = work_dir / f"sub_{i:04d}.txt"
        txt_file.write_text(str(text), encoding="utf-8")
        escaped_path = _escape_filter_path(str(txt_file))
        font_part = f"fontfile='{fontfile}':" if fontfile else ""
        # enable 表达式内的逗号需转义为 \,，否则被 filter_complex 当作 filter 链分隔符
        enable_expr = f"between(t\\,{start:.3f}\\,{end:.3f})"
        draws.append(
            f"drawtext={font_part}textfile='{escaped_path}':"
            f"fontcolor=white:fontsize=48:"
            f"x=(w-text_w)/2:y=h-text_h-40:"
            f"box=1:boxcolor=black@0.5:boxborderw=10:"
            f"enable={enable_expr}"
        )
    return f"[0:v]{','.join(draws)}[vsub]"


# --------------------------------------------------------------------------- #
# 最终合成 pass
# --------------------------------------------------------------------------- #


def _run_final(
    concat_path: Path,
    audio_input: Path | None,
    bgm_input: Path | None,
    subtitle_filter: str | None,
    output: Path,
) -> None:
    """执行最终 pass：视频（可选字幕）+ 音频（可选 amix 混音）→ 输出 mp4。

    - 有字幕时必须重编码视频（滤镜要求）
    - 仅混音无字幕时可 -c:v copy 视频轨，省一次编码
    - 无音频时输出静音视频（-an）
    - 混音前对配音音频做 LUFS 响度标准化，保证不同 TTS 产出音量一致
    """
    # 在混音前对配音音频进行响度标准化
    normalized_path: str | None = None
    if audio_input:
        normalized_path = normalize_audio_for_mixing(
            str(audio_input), str(output.parent), target_lufs=-20.0,
        )
        if normalized_path:
            audio_input = Path(normalized_path)

    try:
        args: list[str] = ["-i", str(concat_path)]

        # 追加音频输入，记录输入索引
        next_idx = 1
        audio_idx = None
        bgm_idx = None
        if audio_input:
            audio_idx = next_idx
            next_idx += 1
            args += ["-i", str(audio_input)]
        if bgm_input:
            bgm_idx = next_idx
            next_idx += 1
            args += ["-i", str(bgm_input)]

        need_amix = audio_idx is not None and bgm_idx is not None
        has_subtitle = bool(subtitle_filter)
        use_filter = has_subtitle or need_amix

        if use_filter:
            parts: list[str] = []
            # 视频轨：字幕滤镜或直通
            if has_subtitle:
                parts.append(subtitle_filter)
                vmap = "[vsub]"
            else:
                vmap = "0:v"
            # 音频轨：amix 混音或直通单轨
            amap = None
            if need_amix:
                # normalize=0 防止 amix 把多轨音量按 1/n 稀释
                parts.append(
                    f"[{audio_idx}:a][{bgm_idx}:a]amix=inputs=2:duration=first:normalize=0[aout]"
                )
                amap = "[aout]"
            elif audio_idx is not None:
                # 直接引用输入流不能用方括号，方括号表示 filter graph 输出标签
                amap = f"{audio_idx}:a"
            elif bgm_idx is not None:
                amap = f"{bgm_idx}:a"

            args += ["-filter_complex", ";".join(parts)]
            args += ["-map", vmap]
            if amap:
                args += ["-map", amap]
            # 有字幕必须重编码；仅混音时视频直通拷贝
            if has_subtitle:
                args += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
            else:
                args += ["-c:v", "copy"]
        else:
            # 无滤镜：直接映射，视频拷贝
            args += ["-map", "0:v"]
            if audio_idx is not None:
                args += ["-map", f"{audio_idx}:a"]
            elif bgm_idx is not None:
                args += ["-map", f"{bgm_idx}:a"]
            args += ["-c:v", "copy"]

        # 音频编码
        if audio_idx is not None or bgm_idx is not None:
            args += ["-c:a", "aac", "-b:a", "192k"]
        else:
            args += ["-an"]

        args += ["-movflags", "+faststart", "-y", str(output)]
        _run_ffmpeg(args, desc="最终合成（混音+字幕）")
    finally:
        # 清理响度标准化产生的临时文件
        if normalized_path:
            try:
                Path(normalized_path).unlink(missing_ok=True)
            except Exception:
                pass


def _final_pass(
    concat_path: Path,
    audio_input: Path | None,
    bgm_input: Path | None,
    srt_path: Path | None,
    subtitles: list[str],
    durations: list[float],
    output: Path,
    work_dir: Path,
) -> None:
    """最终合成 pass，带 subtitles → drawtext → 无字幕 三级 fallback。

    参考 NarratoAI 的三级字幕 fallback 设计：优先 libass subtitles 滤镜
    （渲染质量最好），不可用时退到 drawtext（仅需 freetype），再不可用则
    跳过字幕（保证成片仍能产出）。
    """
    has_srt = srt_path is not None and srt_path.exists()

    if has_srt:
        # Level 1: subtitles 滤镜（需 libass，渲染质量最佳）
        try:
            _run_final(concat_path, audio_input, bgm_input,
                       _build_subtitles_filter(srt_path), output)
            return
        except RuntimeError as e:
            logger.warning("subtitles 滤镜失败，尝试 drawtext 兜底: %s", e)

        # Level 2: drawtext（仅需 freetype，兼容性更好）
        fontfile = _find_font()
        try:
            _run_final(concat_path, audio_input, bgm_input,
                       _build_drawtext_filter(subtitles, durations, fontfile, work_dir),
                       output)
            return
        except RuntimeError as e:
            logger.warning("drawtext 也失败，跳过字幕烧录: %s", e)

    # Level 3: 无字幕（保证成片仍能产出）
    _run_final(concat_path, audio_input, bgm_input, None, output)


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #


def assemble_video(
    asset_paths: list[str],
    audio_path: str = "",
    subtitles: list[str] = None,
    subtitle_durations: list[float] = None,
    bgm_path: str = "",
    output_path: str = "",
    task_id: str = "default",
    video_aspect: str = "",
) -> str:
    """用 ffmpeg 把多段视频/图片+音频+字幕合成成片，返回输出文件路径。

    参数:
        asset_paths: 本地视频/图片文件路径列表（按顺序拼接）
        audio_path: 配音音频路径（可选）
        subtitles: 字幕文本列表（可选，按顺序）
        subtitle_durations: 每条字幕时长（可选，缺失时按视频时长均分）
        bgm_path: 背景音乐路径（可选）
        output_path: 输出路径（空则用 STORAGE_DIR/assembled/assemble_{task_id}.mp4）
        task_id: 任务 ID（用于默认输出路径与临时目录命名）
        video_aspect: 画面比例（16:9/9:16/1:1/4:3/3:4，空则用首个资产分辨率）
    """
    if not asset_paths:
        raise ValueError("asset_paths 不能为空：至少需要一个视频/图片资产")

    if not is_ffmpeg_available():
        raise RuntimeError(
            "ffmpeg 不可用：未配置 FFMPEG_PATH 且 PATH 中未找到 ffmpeg。"
            "请安装 ffmpeg 或在 .env 中设置 FFMPEG_PATH。"
        )

    # 校验输入路径（存在性 + 防路径逃逸）
    validated_inputs = [_validate_input_path(p) for p in asset_paths]
    audio_input = _validate_input_path(audio_path) if audio_path else None
    bgm_input = _validate_input_path(bgm_path) if bgm_path else None
    output = _validate_output_path(output_path) if output_path else _default_output_path(task_id)

    subtitles = list(subtitles or [])

    # 临时工作目录（片段、concat list、SRT 等中间产物，用完即删）
    with tempfile.TemporaryDirectory(prefix=f"shotflow_{task_id}_") as tmpdir:
        work = Path(tmpdir)

        # 确定目标分辨率：优先用用户选择的画面比例，否则取首个资产的分辨率
        probed = _probe_resolution(validated_inputs[0])
        resolution = _resolve_aspect_resolution(video_aspect, probed)

        # 推算图片展示时长（有配音时按配音时长均分）
        num_images = sum(1 for p in validated_inputs if _is_image(p))
        image_dur = _compute_image_duration(audio_input, num_images, subtitle_durations)

        # 1. 准备归一化片段
        segments = _prepare_segments(validated_inputs, image_dur, resolution, _DEFAULT_FPS, work)

        # 2. concat 拼接
        concat_path = _concat_segments(segments, work)

        # 3. 生成 SRT（如有字幕且未提供时长，按拼接后视频时长均分）
        srt_path: Path | None = None
        if subtitles:
            if not subtitle_durations:
                total = _probe_duration(concat_path)
                if total > 0:
                    subtitle_durations = [total / len(subtitles)] * len(subtitles)
            srt_content = generate_srt_from_durations(subtitles, subtitle_durations)
            srt_path = work / "subtitles.srt"
            srt_path.write_text(srt_content, encoding="utf-8")

        # 4. 最终 pass：混音 + 烧字幕 → 输出
        _final_pass(
            concat_path, audio_input, bgm_input,
            srt_path, subtitles, subtitle_durations or [],
            output, work,
        )

    return str(output)

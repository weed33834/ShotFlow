"""视频增强服务 — Real-ESRGAN 超分辨率 + RIFE 帧插值。

用途：
1. 把低分辨率视频（如 720p）超分到 1080p/4K，提升清晰度
2. 把低帧率视频（如 24/30fps）补帧到 60fps，让画面更流畅
3. 作为成片后处理工序，提升最终输出质量

设计要点（开源工具优雅降级）：
- Real-ESRGAN / RIFE 都是可选的本地 CLI 工具（ncnn-vulkan 版，支持 GPU 加速）
- 二者通过 REALESRGAN_PATH / RIFE_PATH 环境变量或 PATH 指定，缺失时仅告警并跳过该步骤，
  不中断主链路 —— 保证无 GPU / 未装工具的环境仍能跑通（输出原视频或仅做某一步增强）
- 全部走 subprocess 调用外部 CLI，避免把重模型依赖打进 Python 进程
- 与 ffmpeg_service 同构：路径解析 → 可用性检查 → subprocess 执行 → 失败带 stderr 抛错

增强管线（多 pass，与 ffmpeg_service.assemble_video 风格一致）：
  1. ffmpeg 抽帧（-vsync 0 保留全部原始帧，PNG 无损）
  2. ffprobe 探测源帧率，据此推算 RIFE 补帧倍数
  3. Real-ESRGAN 逐帧超分（ncnn-vulkan 版只吃图片序列，不直接吃视频）
  4. RIFE 帧插值（每 pass 约 2x，循环逼近目标帧率）
  5. ffmpeg 按目标帧率重新编码为 mp4
"""

import logging
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# 单次外部 CLI 调用超时（秒）。超分/补帧对长视频很耗时，给足上限避免误杀。
_ENHANCE_TIMEOUT = 3600
# 抽帧 / 重编码时的 PNG 帧命名模式，需 ffmpeg / Real-ESRGAN / RIFE 三方一致
_FRAME_PATTERN = "frame_%08d.png"
# Real-ESRGAN 默认模型（通用超分，效果与速度均衡）
_REALESRGAN_MODEL = "realesrgan-x4plus"
# RIFE 默认模型（v4 综合质量最佳）
_RIFE_MODEL = "rife-v4"


# --------------------------------------------------------------------------- #
# 二进制解析（与 ffmpeg_service._resolve_ffmpeg_binary 同构，单独实现避免循环依赖）
# --------------------------------------------------------------------------- #


def _resolve_ffmpeg_binary() -> str:
    """解析 ffmpeg 路径：优先 settings.FFMPEG_PATH，否则 PATH 查找。"""
    # 用 getattr 防御性读取，避免旧配置对象无该字段时崩溃
    ffmpeg_path = getattr(settings, "FFMPEG_PATH", "") or ""
    if ffmpeg_path:
        p = Path(ffmpeg_path)
        if p.exists():
            return str(p)
        logger.warning("配置的 FFMPEG_PATH 不存在: %s，回退到 PATH 查找", ffmpeg_path)
    return shutil.which("ffmpeg") or ""


def _resolve_ffprobe_binary() -> str:
    """解析 ffprobe：与 ffmpeg 同目录，否则 PATH 查找。"""
    ffmpeg_path = getattr(settings, "FFMPEG_PATH", "") or ""
    if ffmpeg_path:
        probe = Path(ffmpeg_path).parent / "ffprobe"
        if probe.exists():
            return str(probe)
    return shutil.which("ffprobe") or ""


def _resolve_realesrgan_binary() -> str:
    """解析 Real-ESRGAN 二进制：优先 REALESRGAN_PATH，否则 PATH 查找。

    REALESRGAN_PATH 由 .env 配置，便于指向非 PATH 中的自定义编译版本。
    """
    # getattr 防御：即使 settings 未声明该字段也不崩
    custom = getattr(settings, "REALESRGAN_PATH", "") or ""
    if custom:
        p = Path(custom)
        if p.exists():
            return str(p)
        logger.warning("配置的 REALESRGAN_PATH 不存在: %s，回退到 PATH 查找", custom)
    return shutil.which("realesrgan-ncnn-vulkan") or ""


def _resolve_rife_binary() -> str:
    """解析 RIFE 二进制：优先 RIFE_PATH，否则 PATH 查找。"""
    custom = getattr(settings, "RIFE_PATH", "") or ""
    if custom:
        p = Path(custom)
        if p.exists():
            return str(p)
        logger.warning("配置的 RIFE_PATH 不存在: %s，回退到 PATH 查找", custom)
    return shutil.which("rife-ncnn-vulkan") or ""


# --------------------------------------------------------------------------- #
# 可用性检查（延迟，import 本模块不触发任何外部调用）
# --------------------------------------------------------------------------- #


def _is_ffmpeg_available() -> bool:
    return bool(_resolve_ffmpeg_binary())


def _is_realesrgan_available() -> bool:
    return bool(_resolve_realesrgan_binary())


def _is_rife_available() -> bool:
    return bool(_resolve_rife_binary())


def is_enhance_available() -> bool:
    """检查视频增强是否可用。

    增强 = 至少具备一种增强能力（超分 或 补帧），且 ffmpeg 可用（抽帧/重编码必备）。
    若两者都没装，则无增强可言，调用方应跳过或走 simulate。
    """
    has_enhance_tool = _is_realesrgan_available() or _is_rife_available()
    return _is_ffmpeg_available() and has_enhance_tool


# --------------------------------------------------------------------------- #
# 底层 subprocess 执行
# --------------------------------------------------------------------------- #


def _run_cli(cmd: list[str], desc: str) -> None:
    """执行外部 CLI，失败抛 RuntimeError 带完整 stderr。

    与 ffmpeg_service._run_ffmpeg 保持一致的错误信息风格，便于排查。
    """
    logger.info("[enhance] %s", desc)
    logger.debug("[enhance] 命令: %s", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=_ENHANCE_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"{desc} 超时（>{_ENHANCE_TIMEOUT}s）\n命令: {' '.join(cmd)}"
        ) from e
    if proc.returncode != 0:
        raise RuntimeError(
            f"{desc} 失败 (exit={proc.returncode})\n"
            f"命令: {' '.join(cmd)}\n"
            f"stderr:\n{proc.stderr[-3000:]}"
        )


def _probe_fps(path: Path) -> float:
    """ffprobe 探测视频帧率，失败返回 0。

    用于推算 RIFE 需要补多少倍才能达到目标帧率。
    """
    binary = _resolve_ffprobe_binary()
    if not binary:
        return 0.0
    try:
        # r_frame_rate 形如 "30000/1001"（29.97fps），需做除法
        proc = subprocess.run(
            [binary, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        raw = proc.stdout.strip()
        if proc.returncode == 0 and raw:
            if "/" in raw:
                num, den = raw.split("/", 1)
                den_f = float(den) or 1.0
                return float(num) / den_f
            return float(raw)
    except Exception as exc:
        logger.warning("探测帧率失败: %s", exc)
    return 0.0


# --------------------------------------------------------------------------- #
# 路径安全（与 ffmpeg_service._validate_input_path 同构）
# --------------------------------------------------------------------------- #


def _validate_input_path(p: str) -> Path:
    """校验输入路径存在且是本地文件。"""
    if not p:
        raise ValueError("资产路径为空")
    if p.startswith(("http://", "https://", "rtmp://", "rtsp://")):
        raise ValueError(
            f"enhance 需要本地文件路径，不支持 URL 资产: {p}。请先将资产下载到本地存储。"
        )
    path = Path(p).resolve()
    if not path.exists():
        raise FileNotFoundError(f"资产文件不存在: {p}")
    if not path.is_file():
        raise ValueError(f"资产路径不是文件: {p}")
    return path


def _default_output_path(input_path: Path, task_id: str) -> Path:
    """生成默认输出路径：STORAGE_DIR/enhanced/enhance_{task_id}.mp4。"""
    storage = Path(getattr(settings, "STORAGE_DIR", "") or str(Path(__file__).resolve().parents[4] / "storage"))
    out_dir = storage / "enhanced"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"enhance_{task_id}.mp4"


# --------------------------------------------------------------------------- #
# 管线各阶段
# --------------------------------------------------------------------------- #


def _extract_frames(ffmpeg: str, input_path: Path, frames_dir: Path) -> int:
    """用 ffmpeg 抽取全部原始帧为 PNG。

    -vsync/passthrough 0：保留每一帧不丢不重复，保证帧数与源一致，
    后续按目标帧率重编码时由 ffmpeg 控制时长。
    返回抽出的帧数（用于校验管线正确性）。
    """
    frames_dir.mkdir(parents=True, exist_ok=True)
    _run_cli(
        [ffmpeg, "-hide_banner", "-i", str(input_path),
         "-vsync", "0", str(frames_dir / _FRAME_PATTERN)],
        desc=f"抽帧 {input_path.name}",
    )
    frames = sorted(frames_dir.glob("*.png"))
    if not frames:
        raise RuntimeError(f"抽帧失败：{frames_dir} 下无 PNG 文件")
    return len(frames)


def _run_realesrgan(input_path: Path, output_dir: Path, scale: int) -> Path:
    """调用 Real-ESRGAN CLI 对图片序列做超分。

    ncnn-vulkan 版只接受「输入目录 + 输出目录」，逐张超分后输出同名 PNG。
    工具不可用时优雅降级：记录告警并原样返回输入目录（跳过超分）。
    """
    binary = _resolve_realesrgan_binary()
    if not binary:
        # 优雅降级：未安装 Real-ESRGAN 时跳过超分，直接用原帧进入下一阶段
        logger.warning(
            "Real-ESRGAN 不可用（未配置 REALESRGAN_PATH 且 PATH 未找到 "
            "realesrgan-ncnn-vulkan），跳过超分步骤。"
        )
        return input_path

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        _run_cli(
            [binary, "-i", str(input_path), "-o", str(output_dir),
             "-n", _REALESRGAN_MODEL, "-s", str(scale), "-f", "png"],
            desc=f"Real-ESRGAN 超分 x{scale}",
        )
    except RuntimeError as exc:
        # 超分失败不致命：回退到原始帧，保证补帧/重编码仍可进行
        logger.warning("Real-ESRGAN 超分失败，回退到原始帧: %s", exc)
        return input_path

    out_frames = sorted(output_dir.glob("*.png"))
    if not out_frames:
        logger.warning("Real-ESRGAN 未产出任何帧，回退到原始帧")
        return input_path
    return output_dir


def _run_rife_interpolation(input_dir: Path, output_dir: Path, target_fps: float, source_fps: float) -> Path:
    """调用 RIFE CLI 做帧插值，逼近目标帧率。

    RIFE ncnn-vulkan 版每跑一次约把帧数翻倍（2x）。为实现「目标帧率」控制，
    先按 target/source 计算需要的倍数，再决定跑几次 pass（每次 2x）。
    - 倍数 <= 1：无需补帧，原样返回
    - 倍数非 2 的幂：取 ceil(log2) 次 pass，可能略超目标（重编码时由 fps 控制时长）
    工具不可用时优雅降级：跳过补帧。
    """
    binary = _resolve_rife_binary()
    if not binary:
        logger.warning(
            "RIFE 不可用（未配置 RIFE_PATH 且 PATH 未找到 rife-ncnn-vulkan），跳过补帧步骤。"
        )
        return input_dir

    # 源帧率探测失败时无法计算倍数，安全起见跳过补帧
    if source_fps <= 0 or target_fps <= 0:
        logger.warning("源/目标帧率无效（source=%s, target=%s），跳过补帧", source_fps, target_fps)
        return input_dir

    multiplier = target_fps / source_fps
    if multiplier <= 1.0:
        # 目标帧率不超过源帧率，无需补帧
        logger.info("目标帧率 %.1f <= 源帧率 %.1f，跳过补帧", target_fps, source_fps)
        return input_dir

    # 每次 RIFE pass 约 2x，需要 ceil(log2(multiplier)) 次 pass 逼近目标
    passes = max(1, math.ceil(math.log2(multiplier)))
    logger.info("RIFE 补帧：源 %.1ffps → 目标 %.1ffps（约 %.2fx，%d pass）",
                source_fps, target_fps, multiplier, passes)

    current_dir = input_dir
    for i in range(passes):
        pass_out = output_dir if i == passes - 1 else output_dir.parent / f"rife_pass_{i}"
        pass_out.mkdir(parents=True, exist_ok=True)
        try:
            _run_cli(
                [binary, "-i", str(current_dir), "-o", str(pass_out),
                 "-m", _RIFE_MODEL],
                desc=f"RIFE 补帧 pass {i + 1}/{passes}",
            )
        except RuntimeError as exc:
            # 某次 pass 失败：用已得帧继续，不致全管线失败
            logger.warning("RIFE pass %d 失败，使用当前帧继续: %s", i + 1, exc)
            return current_dir
        out_frames = sorted(pass_out.glob("*.png"))
        if not out_frames:
            logger.warning("RIFE pass %d 未产出帧，使用当前帧继续", i + 1)
            return current_dir
        current_dir = pass_out
    return current_dir


def _normalize_frames(src_dir: Path, normalized_dir: Path) -> Path:
    """把任意命名的 PNG 帧序列重命名归一化为 frame_%08d.png。

    Real-ESRGAN 通常保留原名，但 RIFE 产出的帧名可能不同（如 0001.png / 1.png）。
    统一重命名后下游重编码只需一种输入模式，避免对 RIFE 命名做特判。
    用硬拷贝而非符号链接，兼容不支持 symlink 的文件系统/容器挂载。
    """
    normalized_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(src_dir.glob("*.png"))
    if not frames:
        raise RuntimeError(f"归一化失败：{src_dir} 下无 PNG 帧")
    for idx, fr in enumerate(frames, start=1):
        dest = normalized_dir / (_FRAME_PATTERN % idx)
        shutil.copyfile(str(fr), str(dest))
    return normalized_dir


def _reencode_frames(ffmpeg: str, frames_dir: Path, output_path: Path, fps: float) -> None:
    """把图片序列按指定帧率重新编码为 mp4。

    用 -framerate 显式指定输入帧率，保证帧数/帧率与目标时长匹配。
    -pix_fmt yuv420p 保证播放器兼容性（与 ffmpeg_service 一致）。
    输入帧名必须已归一化为 frame_%08d.png（由 _normalize_frames 保证）。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run_cli(
        [ffmpeg, "-hide_banner",
         "-framerate", f"{fps:.3f}",
         "-i", str(frames_dir / _FRAME_PATTERN),
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart",
         "-y", str(output_path)],
        desc=f"重编码 {output_path.name} @ {fps:.1f}fps",
    )


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #


def enhance_video(
    input_path: str,
    output_path: str = "",
    scale: int = 2,
    fps_target: int = 60,
) -> str:
    """视频增强主入口：超分 + 补帧，返回输出文件路径。

    管线：抽帧 → Real-ESRGAN 超分 → RIFE 补帧 → 重编码。
    任一增强工具缺失时优雅跳过该步骤，仍产出有效视频（至少经过 ffmpeg 重编码归一化）。

    Args:
        input_path: 输入视频本地路径
        output_path: 输出路径（空则落到 STORAGE_DIR/enhanced/）
        scale: 超分倍数（2/3/4），仅 Real-ESRGAN 可用时生效
        fps_target: 目标帧率（如 60），仅 RIFE 可用时生效
    Returns:
        输出视频本地路径
    """
    src = _validate_input_path(input_path)

    ffmpeg = _resolve_ffmpeg_binary()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg 不可用：未配置 FFMPEG_PATH 且 PATH 中未找到 ffmpeg。"
            "请安装 ffmpeg 或在 .env 中设置 FFMPEG_PATH。"
        )

    # 输出路径兜底
    if output_path:
        out = Path(output_path).resolve()
        if out.suffix.lower() != ".mp4":
            out = out.with_suffix(".mp4")
    else:
        out = _default_output_path(src, f"{int(time.time())}")

    # 两种增强工具都没有时，直接 ffmpeg 重编码归一化（拷贝原帧率），避免空操作
    if not is_enhance_available():
        logger.warning(
            "无任何增强工具可用（Real-ESRGAN/RIFE 均缺失），仅做 ffmpeg 重编码归一化。"
        )
        source_fps = _probe_fps(src) or 30.0
        # 直接重新编码，不改分辨率/帧率
        _run_cli(
            [ffmpeg, "-hide_banner", "-i", str(src),
             "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", "-y", str(out)],
            desc="无增强工具，仅重编码归一化",
        )
        return str(out)

    source_fps = _probe_fps(src) or 30.0

    # 临时工作目录存放抽帧/超分/补帧中间产物，用完即删
    with tempfile.TemporaryDirectory(prefix="shotflow_enhance_") as tmpdir:
        work = Path(tmpdir)
        frames_dir = work / "frames"
        esrgan_dir = work / "esrgan"
        rife_dir = work / "rife"

        # 1. 抽帧（PNG 无损，保留全部原始帧）
        _extract_frames(ffmpeg, src, frames_dir)

        # 2. Real-ESRGAN 超分（不可用则原帧透传）
        upscaled_dir = _run_realesrgan(frames_dir, esrgan_dir, scale)

        # 3. RIFE 补帧（不可用则原帧透传）
        interpolated_dir = _run_rife_interpolation(upscaled_dir, rife_dir, fps_target, source_fps)

        # 4. 按目标帧率重编码为 mp4
        # 若补帧未生效（interpolated_dir == upscaled_dir），用源帧率重编码避免时长失真
        final_fps = fps_target if interpolated_dir != upscaled_dir else source_fps
        # 归一化帧名后重编码，兼容 Real-ESRGAN / RIFE 不同命名
        normalized_dir = work / "normalized"
        _normalize_frames(interpolated_dir, normalized_dir)
        _reencode_frames(ffmpeg, normalized_dir, out, final_fps)

    logger.info("[enhance] 增强完成: %s → %s", src.name, out)
    return str(out)

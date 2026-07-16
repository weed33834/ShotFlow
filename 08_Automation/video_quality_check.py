"""video_quality_check —— 视频质量自动巡检工具。

出片后把关：分辨率 / 帧率 / 时长是否达标，画面是否黑帧、白帧、模糊、闪烁严重。
依赖 ffmpeg(ffprobe) 抽帧元数据 + OpenCV 做帧分析；二者任一缺失时，相关函数
会优雅降级（返回哨兵值，不抛异常），便于在无 GPU / 无 OpenCV 的 CI 环境里安全调用。

典型用法：
    from video_quality_check import check_video
    report = check_video("output.mp4", temp_dir="/tmp/frames")
    if report["score"] < 80:
        print("质量问题：", report["issues"])
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# 阈值集中管理，便于按项目调整；测试会用 fixture 复制/还原，避免用例间串扰。
THRESHOLDS: dict[str, float] = {
    "min_width": 1280.0,
    "min_height": 720.0,
    "target_fps": 24.0,
    "fps_tolerance": 1.0,
    "min_duration": 2.0,
    "min_sharpness": 100.0,  # Laplacian 方差低于此值视为模糊
    "flicker_max": 30.0,  # 帧间亮度波动高于此值视为闪烁严重
    "black_mean_max": 16.0,  # 平均亮度低于此值视为黑帧
    "white_mean_min": 240.0,  # 平均亮度高于此值视为白帧
}

# 各类问题对应的扣分（基础分 100，命中即扣，下限 0）
PENALTIES: dict[str, int] = {
    "resolution": 20,
    "fps": 10,
    "duration": 15,
    "sharpness": 15,
    "black": 20,
    "white": 20,
    "flicker": 15,
}


def run_ffprobe(video_path: str | os.PathLike) -> dict:
    """调用 ffprobe 读取视频元数据，返回解析后的 dict。

    失败（ffprobe 未安装 / 文件损坏 / 输出无法解析）时返回 {"error": "<原因>"}，
    调用方据此判 0 分，而不是让异常向上冒泡。
    """
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as e:
        return {"error": f"ffprobe 未安装或不可用: {e}"}
    except subprocess.CalledProcessError as e:
        return {"error": f"ffprobe 执行失败: {e.stderr or e}"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"ffprobe 输出解析失败: {e}"}


def _parse_fps(raw: str) -> float:
    """解析 ffprobe 的 avg_frame_rate（形如 '24000/1000' 或 '24'）。"""
    if not raw:
        return 0.0
    raw = str(raw).strip()
    if "/" in raw:
        try:
            num, den = raw.split("/")
            num_f, den_f = float(num), float(den)
        except ValueError:
            return 0.0
        return num_f / den_f if den_f else 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def analyze_sharpness(frame_path: str | os.PathLike) -> float:
    """计算单帧锐度（Laplacian 方差）。cv2 不可用时返回 -1（哨兵值）。"""
    try:
        import cv2
    except ImportError:
        return -1.0
    img = cv2.imread(str(frame_path))
    if img is None:
        return -1.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def analyze_brightness(frame_path: str | os.PathLike):
    """返回 (mean, is_black, is_white)。cv2 不可用时返回 (128.0, False, False)。"""
    try:
        import cv2
    except ImportError:
        return (128.0, False, False)
    img = cv2.imread(str(frame_path))
    if img is None:
        return (128.0, False, False)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean = float(gray.mean())
    is_black = mean < THRESHOLDS["black_mean_max"]
    is_white = mean > THRESHOLDS["white_mean_min"]
    return (mean, is_black, is_white)


def analyze_flicker(frame_paths: list) -> float:
    """基于帧序列平均亮度波动估算闪烁程度。不足 2 帧返回 0。

    cv2 / numpy 不可用时同样返回 0（无法评估，不报错）。
    """
    if not frame_paths or len(frame_paths) < 2:
        return 0.0
    try:
        import cv2
        import numpy as np
    except ImportError:
        return 0.0
    means: list[float] = []
    for fp in frame_paths:
        img = cv2.imread(str(fp))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        means.append(float(gray.mean()))
    if len(means) < 2:
        return 0.0
    return float(np.std(means))


def extract_frames(video_path: str | os.PathLike, temp_dir: str | os.PathLike) -> list[str]:
    """用 OpenCV 抽帧保存到 temp_dir，返回帧文件路径列表（cv2 缺失时返回空列表）。"""
    try:
        import cv2
    except ImportError:
        return []
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    paths: list[str] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out = temp_dir / f"frame_{idx:05d}.png"
        cv2.imwrite(str(out), frame)
        paths.append(str(out))
        idx += 1
    cap.release()
    return paths


def check_video(video_path: str | os.PathLike, temp_dir: str | os.PathLike) -> dict:
    """对单个视频做质量巡检，返回评分报告。

    返回字段：
        score      int   综合质量分（0-100，命中问题扣分，下限 0）
        issues     list  问题说明（中文）
        resolution str   "宽x高"
        fps        float 帧率
        duration   float 时长（秒）
        frames     int   实际分析帧数

    设计：ffprobe 失败 / 无视频流 → 直接判 0 分并给出明确原因；其余问题各自扣分。
    帧级分析仅在 OpenCV 可用且确有抽到的帧时才执行，缺失则为「跳过」而非「判失败」。
    """
    info = run_ffprobe(video_path)
    if "error" in info:
        return {
            "score": 0,
            "issues": [f"无法读取视频元数据：{info['error']}"],
            "resolution": "",
            "fps": 0.0,
            "duration": 0.0,
            "frames": 0,
        }

    streams = info.get("streams", []) or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is None:
        return {
            "score": 0,
            "issues": ["未找到视频流（可能仅为音频 / 字幕轨）"],
            "resolution": "",
            "fps": 0.0,
            "duration": 0.0,
            "frames": 0,
        }

    width = int(video_stream.get("width", 0) or 0)
    height = int(video_stream.get("height", 0) or 0)
    fps = _parse_fps(video_stream.get("avg_frame_rate", "0/1"))
    duration = float(info.get("format", {}).get("duration", 0) or 0)

    issues: list[str] = []
    score = 100

    if width < THRESHOLDS["min_width"] or height < THRESHOLDS["min_height"]:
        issues.append(
            f"分辨率过低（{width}x{height}，建议 ≥ "
            f"{int(THRESHOLDS['min_width'])}x{int(THRESHOLDS['min_height'])}）"
        )
        score -= PENALTIES["resolution"]

    if abs(fps - THRESHOLDS["target_fps"]) > THRESHOLDS["fps_tolerance"]:
        issues.append(f"帧率异常（{fps:.2f}fps，建议 {THRESHOLDS['target_fps']:.0f}fps）")
        score -= PENALTIES["fps"]

    if duration < THRESHOLDS["min_duration"]:
        issues.append(f"时长过短（{duration:.1f}s，建议 ≥ {THRESHOLDS['min_duration']:.0f}s）")
        score -= PENALTIES["duration"]

    # 帧级分析：需 OpenCV 可用且确有抽到的帧才进入（否则视为「跳过」）
    try:
        import cv2  # noqa: F401
    except ImportError:
        cv2 = None  # type: ignore[assignment]

    frames = extract_frames(video_path, temp_dir)
    if cv2 is not None and frames:
        sharpness = analyze_sharpness(frames[0])
        _mean_b, is_black, is_white = analyze_brightness(frames[0])
        flicker = analyze_flicker(frames)

        if sharpness >= 0 and sharpness < THRESHOLDS["min_sharpness"]:
            issues.append(
                f"画面锐度不足（{sharpness:.1f}，建议 ≥ {THRESHOLDS['min_sharpness']:.0f}）"
            )
            score -= PENALTIES["sharpness"]
        if is_black:
            issues.append("检测到黑帧")
            score -= PENALTIES["black"]
        if is_white:
            issues.append("检测到白帧")
            score -= PENALTIES["white"]
        if flicker > THRESHOLDS["flicker_max"]:
            issues.append(f"画面闪烁严重（波动 {flicker:.1f}）")
            score -= PENALTIES["flicker"]

        # 清理临时帧
        for fp in frames:
            try:
                os.remove(fp)
            except OSError:
                pass

    score = max(0, score)
    return {
        "score": score,
        "issues": issues,
        "resolution": f"{width}x{height}",
        "fps": fps,
        "duration": duration,
        "frames": len(frames),
    }


def main(argv=None) -> int:
    """命令行入口：video_quality_check.py <video> [temp_dir]。

    质量分 ≥ 80 返回 0，否则返回 1（便于 CI 当质量门禁）。
    """
    import sys

    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法: python video_quality_check.py <video.mp4> [temp_dir]")
        return 2
    video = argv[0]
    temp = argv[1] if len(argv) > 1 else str(Path(video).parent / ".vq_frames")
    report = check_video(video, temp)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["score"] >= 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())

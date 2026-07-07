#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频质量自动检测脚本 — 分析生成视频的基本质量指标
ShotFlow

用法: python video_quality_check.py [视频目录]
默认: 检查 05_Output/Rough_Cuts/（基于 PROJECT_ROOT）

检测项目:
1. 分辨率与帧率
2. 时长
3. 帧间差异（闪烁检测）
4. 黑帧/白帧检测
5. 模糊度检测
6. 文件完整性

输出: 06_Research/video_quality_report.md
"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from common import PROJECT_ROOT

# ==================== 配置区 ====================

DEFAULT_INPUT_DIR = PROJECT_ROOT / "05_Output" / "Rough_Cuts"
OUTPUT_FILE = PROJECT_ROOT / "06_Research" / "video_quality_report.md"

# 质量阈值
THRESHOLDS = {
    "min_resolution": 720,  # 最低高度
    "expected_fps": 24,  # 预期帧率
    "min_duration": 2.0,  # 最短时长（秒）
    "max_duration": 10.0,  # 最长时长（秒）
    "max_black_ratio": 0.1,  # 黑帧最大比例
    "max_white_ratio": 0.1,  # 白帧最大比例
    "min_sharpness": 100,  # 最低锐度（拉普拉斯方差）
    "max_flicker_score": 30,  # 最大闪烁分数
}

# ==================== 工具函数 ====================


def run_ffprobe(video_path: str) -> dict:
    """使用 ffprobe 获取视频信息。"""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}
    return {"error": "ffprobe failed"}


def extract_frames(video_path: str, output_dir: str, max_frames: int = 10) -> list:
    """提取视频帧用于分析。"""
    os.makedirs(output_dir, exist_ok=True)
    # 均匀提取 max_frames 帧
    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-vf",
        f"select='not(mod(n\\,max(1\\,floor(tb*duration/{max_frames}))))'",
        "-vsync",
        "vfr",
        "-frames:v",
        str(max_frames),
        "-y",
        os.path.join(output_dir, "frame_%03d.png"),
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except Exception:
        pass

    frames = sorted(Path(output_dir).glob("frame_*.png"))
    return [str(f) for f in frames]


def analyze_sharpness(frame_path: str) -> float:
    """计算单帧锐度（拉普拉斯方差）。"""
    try:
        import cv2

        img = cv2.imread(frame_path)
        if img is None:
            return 0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except ImportError:
        return -1  # cv2 未安装
    except Exception:
        return 0


def analyze_brightness(frame_path: str) -> tuple:
    """分析帧亮度，返回 (平均亮度, 是否黑帧, 是否白帧)。"""
    try:
        import cv2
        import numpy as np

        img = cv2.imread(frame_path)
        if img is None:
            return (0, False, False)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        is_black = mean_brightness < 10
        is_white = mean_brightness > 245
        return (mean_brightness, is_black, is_white)
    except ImportError:
        return (128, False, False)
    except Exception:
        return (128, False, False)


def analyze_flicker(frame_paths: list) -> float:
    """计算帧间亮度差异标准差作为闪烁分数。"""
    if len(frame_paths) < 2:
        return 0
    try:
        import cv2
        import numpy as np

        brightnesses = []
        for fp in frame_paths:
            img = cv2.imread(fp)
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                brightnesses.append(float(np.mean(gray)))
        if len(brightnesses) < 2:
            return 0
        return float(np.std(np.diff(brightnesses)))
    except ImportError:
        return -1
    except Exception:
        return 0


def check_video(video_path: str, temp_dir: str) -> dict:
    """检查单个视频。"""
    result = {
        "filename": os.path.basename(video_path),
        "path": video_path,
        "issues": [],
        "score": 100,
    }

    # 1. ffprobe 信息
    info = run_ffprobe(video_path)
    if "error" in info:
        result["issues"].append(f"[严重] 无法读取视频信息: {info['error']}")
        result["score"] = 0
        return result

    streams = info.get("streams", [])
    video_stream = None
    for s in streams:
        if s.get("codec_type") == "video":
            video_stream = s
            break

    if not video_stream:
        result["issues"].append("[严重] 未找到视频流")
        result["score"] = 0
        return result

    # 2. 分辨率
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    result["resolution"] = f"{width}x{height}"
    if height < THRESHOLDS["min_resolution"]:
        result["issues"].append(f"[警告] 分辨率高度 {height} 低于 {THRESHOLDS['min_resolution']}")
        result["score"] -= 20

    # 3. 帧率
    fps_str = video_stream.get("avg_frame_rate", "0/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 0
    except Exception:
        fps = 0
    result["fps"] = round(fps, 1)
    if abs(fps - THRESHOLDS["expected_fps"]) > 1:
        result["issues"].append(f"[警告] 帧率 {fps:.1f} 与预期 {THRESHOLDS['expected_fps']} 不符")
        result["score"] -= 10

    # 4. 时长
    duration = float(info.get("format", {}).get("duration", 0))
    result["duration"] = round(duration, 1)
    if duration < THRESHOLDS["min_duration"]:
        result["issues"].append(f"[警告] 时长 {duration:.1f}s 过短")
        result["score"] -= 15
    if duration > THRESHOLDS["max_duration"]:
        result["issues"].append(f"[提示] 时长 {duration:.1f}s 超过 {THRESHOLDS['max_duration']}s")

    # 5. 编码格式
    codec = video_stream.get("codec_name", "unknown")
    result["codec"] = codec

    # 6. 文件大小
    file_size = os.path.getsize(video_path)
    result["file_size_mb"] = round(file_size / 1024**2, 1)

    # 7. 帧分析（如有 cv2）
    try:
        import cv2  # noqa

        frame_dir = os.path.join(temp_dir, os.path.splitext(result["filename"])[0])
        frames = extract_frames(video_path, frame_dir, max_frames=10)

        if frames:
            # 锐度
            sharpnesses = [analyze_sharpness(f) for f in frames]
            valid_sharp = [s for s in sharpnesses if s >= 0]
            if valid_sharp:
                avg_sharpness = sum(valid_sharp) / len(valid_sharp)
                result["avg_sharpness"] = round(avg_sharpness, 1)
                if avg_sharpness < THRESHOLDS["min_sharpness"]:
                    result["issues"].append(
                        f"[警告] 锐度 {avg_sharpness:.1f} 低于 {THRESHOLDS['min_sharpness']}，可能模糊"
                    )
                    result["score"] -= 15

            # 亮度与黑白帧
            black_count = 0
            white_count = 0
            for f in frames:
                _, is_black, is_white = analyze_brightness(f)
                if is_black:
                    black_count += 1
                if is_white:
                    white_count += 1
            black_ratio = black_count / len(frames)
            white_ratio = white_count / len(frames)
            result["black_frame_ratio"] = round(black_ratio, 2)
            result["white_frame_ratio"] = round(white_ratio, 2)
            if black_ratio > THRESHOLDS["max_black_ratio"]:
                result["issues"].append(f"[警告] 黑帧比例 {black_ratio:.0%} 过高")
                result["score"] -= 20
            if white_ratio > THRESHOLDS["max_white_ratio"]:
                result["issues"].append(f"[警告] 白帧比例 {white_ratio:.0%} 过高")
                result["score"] -= 20

            # 闪烁
            flicker = analyze_flicker(frames)
            if flicker >= 0:
                result["flicker_score"] = round(flicker, 1)
                if flicker > THRESHOLDS["max_flicker_score"]:
                    result["issues"].append(
                        f"[警告] 闪烁分数 {flicker:.1f} 超过 {THRESHOLDS['max_flicker_score']}，可能闪烁严重"
                    )
                    result["score"] -= 15

            # 清理临时帧
            for f in frames:
                try:
                    os.remove(f)
                except Exception:
                    pass
    except ImportError:
        result["issues"].append(
            "[提示] 未安装 opencv-python，跳过帧分析（pip install opencv-python）"
        )

    result["score"] = max(0, result["score"])
    return result


# ==================== 主流程 ====================


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 视频质量自动检测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=str(DEFAULT_INPUT_DIR),
        help=f"视频目录（默认: {DEFAULT_INPUT_DIR}）",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    print("=" * 60)
    print("  ShotFlow — 视频质量自动检测")
    print(f"  目录: {input_dir}")
    print("=" * 60)

    if not input_dir.exists():
        print(f"[ERROR] 目录不存在: {input_dir}")
        return

    # 查找视频文件
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".gif"}
    videos = [f for f in input_dir.rglob("*") if f.suffix.lower() in video_exts]

    if not videos:
        print("[INFO] 未找到视频文件")
        return

    print(f"\n找到 {len(videos)} 个视频文件\n")

    temp_dir = PROJECT_ROOT / "06_Research" / "_temp_frames"
    results = []

    for i, video in enumerate(sorted(videos)):
        print(f"[{i+1}/{len(videos)}] {video.name}...")
        result = check_video(str(video), str(temp_dir))
        results.append(result)

        status = "✅" if result["score"] >= 80 else "⚠️" if result["score"] >= 50 else "❌"
        print(f"  分数: {result['score']} {status}")
        for issue in result["issues"]:
            print(f"  {issue}")

    # 清理临时目录
    try:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    # 生成报告
    report = []
    report.append("# ShotFlow — 视频质量检测报告\n")
    report.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"> 检测目录: `{input_dir}`")
    report.append(f"> 视频总数: {len(results)}\n")

    # 总览
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0
    passed = sum(1 for r in results if r["score"] >= 80)
    warned = sum(1 for r in results if 50 <= r["score"] < 80)
    failed = sum(1 for r in results if r["score"] < 50)

    report.append("## 总览\n")
    report.append("| 指标 | 数值 |")
    report.append("|------|------|")
    report.append(f"| 视频总数 | {len(results)} |")
    report.append(f"| 平均分数 | {avg_score:.1f} |")
    report.append(f"| ✅ 通过 (≥80) | {passed} |")
    report.append(f"| ⚠️ 警告 (50-79) | {warned} |")
    report.append(f"| ❌ 不合格 (<50) | {failed} |")
    report.append("")

    # 详细结果
    report.append("## 详细检测结果\n")
    report.append(
        "| 文件 | 分辨率 | 帧率 | 时长(s) | 编码 | 大小(MB) | 锐度 | 闪烁 | 分数 | 状态 |"
    )
    report.append(
        "|------|--------|------|---------|------|----------|------|------|------|------|"
    )
    for r in results:
        status = "✅" if r["score"] >= 80 else "⚠️" if r["score"] >= 50 else "❌"
        report.append(
            f"| {r['filename']} | {r.get('resolution', '-')} | {r.get('fps', '-')} | "
            f"{r.get('duration', '-')} | {r.get('codec', '-')} | {r.get('file_size_mb', '-')} | "
            f"{r.get('avg_sharpness', '-')} | {r.get('flicker_score', '-')} | "
            f"{r['score']} | {status} |"
        )
    report.append("")

    # 问题汇总
    all_issues = [(r["filename"], issue) for r in results for issue in r["issues"]]
    if all_issues:
        report.append("## 问题汇总\n")
        report.append("| 文件 | 问题 |")
        report.append("|------|------|")
        for filename, issue in all_issues:
            report.append(f"| {filename} | {issue} |")
        report.append("")

    # 建议
    report.append("## 建议\n")
    if failed > 0:
        report.append(f"- {failed} 个视频不合格，建议重新生成或使用可灵首尾帧替代")
    if warned > 0:
        report.append(f"- {warned} 个视频有警告，检查是否需要 Low Noise 修复或 AE 修补")
    if avg_score < 70:
        report.append(f"- 平均分数 {avg_score:.1f} 偏低，建议调整 CFG/Denoise 参数后重新生成")
    if all_issues:
        report.append("- 参考失败案例记录表记录问题，避免重复踩坑")
    report.append("")

    report_text = "\n".join(report)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n{'='*60}")
    print("  检测完成")
    print(f"  平均分数: {avg_score:.1f}")
    print(f"  通过: {passed} | 警告: {warned} | 不合格: {failed}")
    print(f"  报告: {OUTPUT_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

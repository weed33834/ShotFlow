#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可灵 2.5 Turbo 图生视频 API 调用脚本
ShotFlow — 用于生成复杂镜头/首尾帧约束视频

注意：
1. 可灵官方 API 需申请，也可通过第三方聚合平台（PiAPI、Runware 等）调用。
2. 不同平台的 endpoint、参数、鉴权方式不同，请根据实际账号修改。
3. 本脚本以常见第三方 API 格式为例，使用前请确认文档。
"""

import argparse
import base64
import os
import sys
import time
from pathlib import Path

import requests

from common import PROJECT_ROOT

# ==================== 配置区 ====================

# API 配置（请替换为实际值）
API_KEY = os.getenv("KLING_API_KEY", "your_api_key_here")
BASE_URL = os.getenv("KLING_BASE_URL", "https://api.piapi.ai")
# 其他常见 endpoint 示例：
# Runware: https://api.runware.ai/v1
# 快手可灵官方: https://api.klingai.com

# 生成参数（可通过环境变量 KLING_PROMPT 覆盖，供 render_queue.py 调用）
PROMPT = os.getenv(
    "KLING_PROMPT",
    "A woman in dark gray windbreaker walks cautiously through a ruined futuristic "
    "corridor, amber eyes scanning the environment, subtle head movement, "
    "dust particles floating in cinematic sci-fi lighting, teal and orange color grade, 24fps",
)
NEGATIVE_PROMPT = (
    "bad anatomy, deformed face, extra limbs, blurry, low quality, inconsistent character"
)
DURATION = 5  # 秒
ASPECT_RATIO = "16:9"
MODE = "pro"
VERSION = "2.5-turbo"

# 输入图片路径（可通过环境变量覆盖）
START_IMAGE_PATH = os.getenv(
    "KLING_START_IMAGE",
    str(PROJECT_ROOT / "01_Assets" / "Scenes" / "S01_04_start.png"),
)
END_IMAGE_PATH = os.getenv(
    "KLING_END_IMAGE",
    str(PROJECT_ROOT / "01_Assets" / "Scenes" / "S01_04_end.png"),
)
# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "05_Output" / "Rough_Cuts"

# ==================== 工具函数 ====================


def encode_image_to_base64(image_path: str) -> str:
    """将图片转为 base64 字符串（带 data URI 前缀）。"""
    with open(image_path, "rb") as f:
        data = f.read()
    ext = Path(image_path).suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"


def submit_task() -> str:
    """提交生成任务，返回 task_id。"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "kling-video",
        "task_type": "image_to_video",
        "input": {
            "prompt": PROMPT,
            "negative_prompt": NEGATIVE_PROMPT,
            "image": encode_image_to_base64(START_IMAGE_PATH),
            # "end_image": encode_image_to_base64(END_IMAGE_PATH),  # 如需首尾帧，取消注释
            "duration": DURATION,
            "aspect_ratio": ASPECT_RATIO,
            "mode": MODE,
            "version": VERSION,
        },
    }

    response = requests.post(
        f"{BASE_URL}/v1/task",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    print(f"[Submit] {result}")
    return result["data"]["task_id"]


def poll_task(task_id: str, interval: int = 10, max_retry: int = 60) -> str:
    """轮询任务状态，返回视频下载 URL。"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    url = f"{BASE_URL}/v1/task/{task_id}"

    for i in range(max_retry):
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        status = result["data"].get("status", "unknown")
        print(f"[Poll {i+1}/{max_retry}] status={status}")

        if status == "completed":
            return result["data"]["output"]["video_url"]
        elif status in ("failed", "error"):
            raise RuntimeError(f"Task failed: {result}")

        time.sleep(interval)

    raise TimeoutError("任务超时，请手动查询")


def download_video(video_url: str, output_path: str) -> None:
    """下载视频到本地。"""
    response = requests.get(video_url, timeout=120)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"[Download] 已保存到 {output_path}")


def validate_inputs(args) -> bool:
    """校验 API 密钥与输入图片，避免直接崩溃。"""
    if API_KEY in ("", "your_api_key_here"):
        print("[ERROR] KLING_API_KEY 未配置，请在 .env 中设置或 export KLING_API_KEY")
        return False

    start_image = Path(args.start_image)
    if not start_image.exists():
        print(f"[ERROR] 起始帧不存在: {start_image}")
        print("  提示: 先运行 batch_keyframe_gen.py 生成关键帧，或设置 KLING_START_IMAGE")
        return False
    return True


def main():
    global PROMPT, START_IMAGE_PATH, END_IMAGE_PATH

    parser = argparse.ArgumentParser(
        description="ShotFlow — 可灵 2.5 Turbo 图生视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--shot-id",
        default=os.getenv("KLING_SHOT_ID", "S01_04"),
        help="镜头编号（默认 S01_04）",
    )
    parser.add_argument(
        "--start-image",
        default=os.getenv(
            "KLING_START_IMAGE",
            str(PROJECT_ROOT / "01_Assets" / "Scenes" / "S01_04_start.png"),
        ),
        help="起始帧路径",
    )
    parser.add_argument(
        "--end-image",
        default=os.getenv(
            "KLING_END_IMAGE",
            str(PROJECT_ROOT / "01_Assets" / "Scenes" / "S01_04_end.png"),
        ),
        help="结束帧路径（可选）",
    )
    parser.add_argument(
        "--prompt",
        default=os.getenv("KLING_PROMPT", PROMPT),
        help="视频生成提示词",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印参数，不提交 API",
    )
    args = parser.parse_args()

    PROMPT = args.prompt
    START_IMAGE_PATH = args.start_image
    END_IMAGE_PATH = args.end_image

    print("[Info] 开始可灵图生视频任务...")
    print(f"[Info] shot_id={args.shot_id}, start_image={START_IMAGE_PATH}")

    if args.dry_run:
        print("\n[DRY RUN] 参数校验通过，不会调用 API")
        return

    if not validate_inputs(args):
        sys.exit(1)

    task_id = submit_task()
    print(f"[Info] task_id={task_id}")

    video_url = poll_task(task_id)
    print(f"[Info] 视频 URL: {video_url}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = OUTPUT_DIR / f"{args.shot_id}_Kling_{task_id}.mp4"
    download_video(video_url, str(output_path))


if __name__ == "__main__":
    main()

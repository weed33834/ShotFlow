#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suno AI 音乐生成 API 调用脚本
ShotFlow — 用于生成科幻氛围配乐

注意：
1. Suno 官方 API 目前为邀请制，也可通过第三方聚合平台调用。
2. 本脚本以常见第三方 API 格式为例，请根据实际账号修改 endpoint 与参数。
3. 若无法获取 API，可直接使用 Suno 网页版批量生成后下载。
"""

import argparse
import os
import sys
import time

import requests

from common import PROJECT_ROOT

# ==================== 配置区 ====================

API_KEY = os.getenv("SUNO_API_KEY", "your_api_key_here")
BASE_URL = os.getenv("SUNO_BASE_URL", "https://api.sunoaiapi.com")

OUTPUT_DIR = PROJECT_ROOT / "01_Assets" / "Audio" / "Music"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 配乐需求列表
TRACKS = [
    {
        "title": "Ruins Dawn",
        "tags": "sci-fi, cinematic, ambient, electronic, lonely, vast",
        "prompt": (
            "A slow, atmospheric sci-fi ambient track. Sparse piano notes, distant synth pads, "
            "low rumble, wind-like textures. Evokes a lone wanderer in a vast ruined city at dawn."
        ),
        "duration": 120,
    },
    {
        "title": "Core Awakening",
        "tags": "sci-fi, cinematic, orchestral electronic, mysterious, sacred",
        "prompt": (
            "Mysterious and sacred sci-fi music. Choir-like synths, pulsating electronic arpeggios, "
            "building tension. Sense of discovering an ancient alien AI core."
        ),
        "duration": 120,
    },
    {
        "title": "Echo Resolution",
        "tags": "sci-fi, cinematic, emotional, hopeful, strings",
        "prompt": (
            "Emotional sci-fi cinematic music. Warm strings, gentle piano, swelling synths. "
            "A feeling of release, acceptance, and a new beginning after a long silence."
        ),
        "duration": 120,
    },
]

# ==================== 工具函数 ====================


def submit_generation(title: str, tags: str, prompt: str, duration: int) -> str:
    """提交音乐生成任务，返回 task_id。"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "tags": tags,
        "prompt": prompt,
        "duration": duration,
        "make_instrumental": True,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/suno/generate",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    print(f"[Submit] {title}: {result}")
    return result["data"]["task_id"]


def poll_task(task_id: str, interval: int = 10, max_retry: int = 60) -> list:
    """轮询任务状态，返回音频下载链接列表。"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    url = f"{BASE_URL}/api/v1/suno/task/{task_id}"

    for i in range(max_retry):
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        status = result["data"].get("status", "unknown")
        print(f"[Poll {i+1}/{max_retry}] {task_id} status={status}")

        if status == "completed":
            return result["data"].get("audio_urls", [])
        elif status in ("failed", "error"):
            raise RuntimeError(f"Task failed: {result}")

        time.sleep(interval)

    raise TimeoutError("任务超时")


def download_audio(audio_url: str, output_path: str) -> None:
    """下载音频文件。"""
    response = requests.get(audio_url, timeout=120)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"[Download] {output_path}")


def validate_api_key() -> bool:
    """校验 API 密钥是否已配置。"""
    if API_KEY in ("", "your_api_key_here"):
        print("[ERROR] SUNO_API_KEY 未配置，请在 .env 中设置或 export SUNO_API_KEY")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — Suno AI 配乐生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--prompt",
        default=os.getenv("MUSIC_PROMPT", ""),
        help="单首提示词（为空则生成预设 TRACKS）",
    )
    parser.add_argument(
        "--title",
        default=os.getenv("MUSIC_TITLE", "Custom_Track"),
        help="单首标题",
    )
    parser.add_argument(
        "--tags",
        default=os.getenv("MUSIC_TAGS", "cinematic, sci-fi"),
        help="单首标签",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印参数，不提交 API",
    )
    args = parser.parse_args()

    if args.dry_run:
        print(
            f"[DRY RUN] title={args.title}, tags={args.tags}, prompt={args.prompt or '(全部 TRACKS)'}"
        )
        return

    if not validate_api_key():
        sys.exit(1)

    # 单首模式
    if args.prompt:
        print(f"\n[Info] 开始生成: {args.title}")
        task_id = submit_generation(args.title, args.tags, args.prompt, 120)
        audio_urls = poll_task(task_id)
        for idx, url in enumerate(audio_urls):
            ext = ".mp3" if ".mp3" in url else ".wav"
            output_path = OUTPUT_DIR / f"{args.title}_v{idx+1}{ext}"
            download_audio(url, str(output_path))
        print("\n[Info] 单首配乐生成完成")
        return

    for track in TRACKS:
        print(f"\n[Info] 开始生成: {track['title']}")
        task_id = submit_generation(
            track["title"], track["tags"], track["prompt"], track["duration"]
        )
        audio_urls = poll_task(task_id)

        for idx, url in enumerate(audio_urls):
            ext = ".mp3" if ".mp3" in url else ".wav"
            output_path = OUTPUT_DIR / f"{track['title']}_v{idx+1}{ext}"
            download_audio(url, str(output_path))

    print("\n[Info] 全部配乐生成完成")


if __name__ == "__main__":
    main()

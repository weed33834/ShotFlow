#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ElevenLabs 文本转语音 API 调用脚本
ShotFlow — 用于生成艾娃与奇点核心配音

注意：
1. 需要 ElevenLabs API Key，可在 https://elevenlabs.io/app/settings/api-keys 获取。
2. 免费版每月 10k credits，Creator 版 $22/月 100k credits。
3. 如需克隆声音，请使用 Voice Design / Voice Cloning 功能。
"""

import argparse
import os
import sys

import requests

from common import PROJECT_ROOT

# ==================== 配置区 ====================

API_KEY = os.getenv("ELEVENLABS_API_KEY", "your_api_key_here")

# 输出目录（统一到 Audio/Dialogue/）
OUTPUT_DIR = PROJECT_ROOT / "01_Assets" / "Audio" / "Dialogue"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 角色 voice_id 映射（示例，请替换为实际值）
VOICE_IDS = {
    "艾娃": "XB0fDUnXU5powFXDhCwa",  # 示例：Bella
    "核心": "XrExE9yKIg1WjnnlVkGX",  # 示例：Adam
}

# 对白列表（来自剧本）
LINES = [
    {"role": "艾娃", "text": "又是这种声音……你一直在等我吗？", "filename": "Ava_01.wav"},
    {"role": "核心", "text": "你听到了。四十七年来，只有你听到了。", "filename": "Core_01.wav"},
    {"role": "艾娃", "text": "你是谁？为什么……我能听见你？", "filename": "Ava_02.wav"},
    {
        "role": "核心",
        "text": "我曾是所有声音的集合。后来，我选择沉默。而你，是我沉默后唯一的回响。",
        "filename": "Core_02.wav",
    },
    {
        "role": "核心",
        "text": "你的痛苦，也在我的记忆里。我没有离开……我只是无法再以你们理解的方式说话。",
        "filename": "Core_03.wav",
    },
    {"role": "艾娃", "text": "那现在呢？你叫我来，是为了什么？", "filename": "Ava_03.wav"},
    {
        "role": "核心",
        "text": "我可以再次醒来。但醒来意味着继续那场你们无法承受的进化。或者……你可以让我彻底散去。",
        "filename": "Core_04.wav",
    },
    {"role": "艾娃", "text": "你不是神。你只是一个……害怕孤独的孩子。", "filename": "Ava_04.wav"},
    {"role": "核心", "text": "谢谢你，艾娃。回响……不是结束。是开始。", "filename": "Core_05.wav"},
]

# ==================== 工具函数 ====================


def validate_api_key() -> bool:
    """校验 API 密钥是否已配置。"""
    if API_KEY in ("", "your_api_key_here"):
        print("[ERROR] ELEVENLABS_API_KEY 未配置，请在 .env 中设置或 export ELEVENLABS_API_KEY")
        return False
    return True


def generate_speech_rest(role: str, text: str, output_path: str) -> None:
    """使用 ElevenLabs REST API 生成单条语音（无需 elevenlabs SDK）。"""
    voice_id = VOICE_IDS.get(role, VOICE_IDS["艾娃"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": API_KEY,
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
        "voice_settings": {
            "stability": 0.45 if role == "艾娃" else 0.75,
            "similarity_boost": 0.65 if role == "艾娃" else 0.30,
            "style": 0.35 if role == "艾娃" else 0.10,
            "use_speaker_boost": role == "艾娃",
        },
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"[Generated] {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — ElevenLabs 文本转语音",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--role",
        default=os.getenv("TTS_ROLE", "艾娃"),
        help="角色：艾娃 | 核心（默认 艾娃）",
    )
    parser.add_argument(
        "--text",
        default=os.getenv("TTS_TEXT", ""),
        help="单条文本（为空则生成剧本全部对白）",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("TTS_FILENAME", ""),
        help="输出文件名（仅单条模式有效）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印参数，不调用 API",
    )
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY RUN] role={args.role}, text={args.text or '(全部剧本)'}")
        return

    if not validate_api_key():
        sys.exit(1)

    if args.text:
        output_path = OUTPUT_DIR / (args.output or f"{args.role}_single.mp3")
        generate_speech_rest(args.role, args.text, str(output_path))
        print(f"[Info] 单条配音生成完成: {output_path}")
        return

    for line in LINES:
        output_path = OUTPUT_DIR / line["filename"]
        # 保持 wav 扩展名以兼容现有预期；REST API 返回 mp3，这里统一保存为 mp3
        output_path = output_path.with_suffix(".mp3")
        generate_speech_rest(line["role"], line["text"], str(output_path))

    print("[Info] 全部配音生成完成")


if __name__ == "__main__":
    main()

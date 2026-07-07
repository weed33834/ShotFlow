"""音频生成服务 — ElevenLabs 配音与 Suno 配乐。

对应 render_queue.py 的 run_tts_task（第 255-271 行）与 run_music_task（第 274-289 行）。
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TTS_SCRIPT = PROJECT_ROOT / "08_Automation" / "elevenlabs_tts_api.py"
MUSIC_SCRIPT = PROJECT_ROOT / "08_Automation" / "suno_music_api.py"


class AudioError(Exception):
    """音频生成异常。"""


def run_tts_task(
    text: str,
    role: str = "ava",
    filename: str = "",
) -> dict:
    """执行 ElevenLabs 配音。

    环境变量约定（沿用原脚本）：TTS_TEXT / TTS_ROLE / TTS_FILENAME
    """
    if settings.SIMULATE_MODE:
        logger.info("[模拟] TTS 任务 role=%s text=%s...", role, text[:30])
        return {
            "success": True,
            "output_path": f"01_Assets/Audio/sim_tts_{role}.wav",
            "error": "",
        }

    if not TTS_SCRIPT.exists():
        raise AudioError(f"TTS 脚本不存在: {TTS_SCRIPT}")

    env = {**os.environ, "TTS_TEXT": text, "TTS_ROLE": role}
    if filename:
        env["TTS_FILENAME"] = filename

    try:
        result = subprocess.run(
            [sys.executable, str(TTS_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "output_path": "",
            "error": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        raise AudioError("TTS 生成超时（>300s）")


def run_music_task(
    prompt: str,
    title: str = "",
    tags: str = "",
) -> dict:
    """执行 Suno 配乐。

    环境变量约定（沿用原脚本）：MUSIC_PROMPT / MUSIC_TITLE / MUSIC_TAGS
    """
    if settings.SIMULATE_MODE:
        logger.info("[模拟] 配乐任务 prompt=%s...", prompt[:30])
        return {
            "success": True,
            "output_path": "01_Assets/Audio/sim_music.wav",
            "error": "",
        }

    if not MUSIC_SCRIPT.exists():
        raise AudioError(f"配乐脚本不存在: {MUSIC_SCRIPT}")

    env = {**os.environ, "MUSIC_PROMPT": prompt}
    if title:
        env["MUSIC_TITLE"] = title
    if tags:
        env["MUSIC_TAGS"] = tags

    try:
        result = subprocess.run(
            [sys.executable, str(MUSIC_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "output_path": "",
            "error": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        raise AudioError("配乐生成超时（>600s）")

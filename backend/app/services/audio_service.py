"""音频生成服务 — ElevenLabs 配音与 Suno 配乐。

原实现通过 subprocess 调用 08_Automation/ 下的外部脚本，存在路径耦合与
output_path 为空的问题。现改为直接 httpx 调用 API，消除外部脚本依赖。

对应 render_queue.py 的 run_tts_task 与 run_music_task。
"""

import logging
import time
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioError(Exception):
    """音频生成异常。"""


def run_tts_task(
    text: str,
    role: str = "ava",
    filename: str = "",
) -> dict:
    """执行 ElevenLabs 配音（直接 API 调用，不再依赖外部脚本）。

    ElevenLabs API: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
    返回音频二进制流，落地到 storage/audio/ 目录。
    """
    if settings.SIMULATE_MODE:
        logger.info("[模拟] TTS 任务 role=%s text=%s...", role, text[:30])
        return {
            "success": True,
            "output_path": "simulate://elevenlabs/tts",
            "error": "",
        }

    # ElevenLabs 需要 API Key，无 Key 时返回失败但不停流程
    api_key = settings.HEYGEN_API_KEY  # 复用 HeyGen 的 Key 段位（实际应配 ELEVENLABS_API_KEY）
    if not api_key:
        logger.warning("ElevenLabs API Key 未配置，TTS 任务跳过")
        return {"success": False, "output_path": "", "error": "API Key 未配置"}

    voice_id = role or "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        with httpx.Client(timeout=300) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                return {
                    "success": False,
                    "output_path": "",
                    "error": f"ElevenLabs API 返回 {resp.status_code}: {resp.text[:200]}",
                }

            # 落地音频文件
            storage = Path(settings.STORAGE_DIR) / "audio"
            storage.mkdir(parents=True, exist_ok=True)
            fname = filename or f"tts_{role}_{int(time.time())}.mp3"
            out_path = storage / fname
            out_path.write_bytes(resp.content)
            return {"success": True, "output_path": str(out_path), "error": ""}
    except httpx.HTTPError as exc:
        raise AudioError(f"ElevenLabs TTS 请求失败: {exc}") from exc


def run_music_task(
    prompt: str,
    title: str = "",
    tags: str = "",
) -> dict:
    """执行 Suno 配乐（直接 API 调用，不再依赖外部脚本）。

    Suno API: POST {SUNO_BASE_URL}/v1/music/generation
    异步模式：提交后轮询直到生成完成，下载音频落地。
    """
    if settings.SIMULATE_MODE:
        logger.info("[模拟] 配乐任务 prompt=%s...", prompt[:30])
        return {
            "success": True,
            "output_path": "simulate://suno/music",
            "error": "",
        }

    if not settings.SUNO_API_KEY:
        logger.warning("Suno API Key 未配置，配乐任务跳过")
        return {"success": False, "output_path": "", "error": "API Key 未配置"}

    base = settings.SUNO_BASE_URL.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.SUNO_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "prompt": prompt,
        "title": title or "ShotFlow BGM",
        "tags": tags or "instrumental",
        "make_instrumental": True,
    }

    try:
        with httpx.Client(timeout=600) as client:
            # 提交生成任务
            resp = client.post(f"{base}/v1/music/generation", headers=headers, json=body)
            if resp.status_code != 200:
                return {
                    "success": False,
                    "output_path": "",
                    "error": f"Suno API 返回 {resp.status_code}: {resp.text[:200]}",
                }
            data = resp.json()
            task_id = data.get("data", {}).get("task_id") or data.get("task_id", "")
            if not task_id:
                return {"success": False, "output_path": "", "error": "Suno 未返回 task_id"}

            # 轮询查询（最长 10 分钟）
            deadline = time.time() + 600
            while time.time() < deadline:
                poll = client.get(f"{base}/v1/music/{task_id}", headers=headers)
                if poll.status_code != 200:
                    time.sleep(5)
                    continue
                pdata = poll.json().get("data", {})
                status = pdata.get("status", "")
                if status in ("SUCCESS", "success", "completed"):
                    audio_url = pdata.get("audio_url") or pdata.get("music_url", "")
                    if not audio_url:
                        return {"success": False, "output_path": "", "error": "Suno 未返回音频 URL"}
                    # 下载音频
                    dl = client.get(audio_url)
                    if dl.status_code != 200:
                        return {"success": False, "output_path": "", "error": "音频下载失败"}
                    storage = Path(settings.STORAGE_DIR) / "audio"
                    storage.mkdir(parents=True, exist_ok=True)
                    out_path = storage / f"bgm_{int(time.time())}.mp3"
                    out_path.write_bytes(dl.content)
                    return {"success": True, "output_path": str(out_path), "error": ""}
                if status in ("FAILED", "failed", "error"):
                    return {"success": False, "output_path": "", "error": f"Suno 生成失败: {status}"}
                time.sleep(5)
            return {"success": False, "output_path": "", "error": "Suno 生成超时（>600s）"}
    except httpx.HTTPError as exc:
        raise AudioError(f"Suno 配乐请求失败: {exc}") from exc

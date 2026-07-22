"""ASR 语音转文字服务 — 支持本地 faster-whisper 和 OpenAI Whisper API。

用途：
1. 对已有视频/音频做转录，生成字幕时间轴
2. 视频翻译配音场景的源语言转录
3. 用户上传视频后自动生成字幕
"""
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ASRResult:
    """ASR 转录结果。"""
    def __init__(self, segments: list[dict], text: str, language: str = "zh"):
        self.segments = segments  # [{"start": 0.0, "end": 2.5, "text": "..."}]
        self.text = text
        self.language = language


async def transcribe(
    audio_path: str,
    language: str = "zh",
    model_size: str = "base",
) -> ASRResult:
    """转录音频/视频文件为文字 + 时间轴。

    优先用 faster-whisper（本地），未安装时回退 OpenAI Whisper API。
    """
    if settings.SIMULATE_MODE:
        return _simulate_transcribe(audio_path, language)

    # 优先尝试本地 faster-whisper
    try:
        return await _transcribe_whisper_local(audio_path, language, model_size)
    except ImportError:
        logger.info("faster-whisper 未安装，回退 OpenAI Whisper API")
    except Exception as exc:
        logger.warning("本地 Whisper 转录失败，回退 API: %s", exc)

    # 回退 OpenAI Whisper API
    return await _transcribe_whisper_api(audio_path, language)


async def _transcribe_whisper_local(
    audio_path: str, language: str, model_size: str
) -> ASRResult:
    """用 faster-whisper 本地模型转录。"""
    # 延迟 import，未安装时不影响模块加载
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, info = model.transcribe(audio_path, language=language)
    seg_list = [
        {"start": s.start, "end": s.end, "text": s.text.strip()}
        for s in segments
    ]
    full_text = " ".join(s["text"] for s in seg_list)
    return ASRResult(seg_list, full_text, info.language)


async def _transcribe_whisper_api(
    audio_path: str, language: str
) -> ASRResult:
    """用 OpenAI Whisper API 转录（需 LLM_API_KEY）。"""
    if not settings.LLM_API_KEY:
        raise RuntimeError("Whisper API 需要 LLM_API_KEY（OpenAI 兼容）")

    url = settings.LLM_BASE_URL.rstrip("/") + "/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}

    import asyncio
    def _do_request():
        with open(audio_path, "rb") as f:
            with httpx.Client(timeout=300) as client:
                return client.post(
                    url, headers=headers,
                    files={"file": (Path(audio_path).name, f)},
                    data={"language": language},
                )
    resp = await asyncio.to_thread(_do_request)
    resp.raise_for_status()
    data = resp.json()
    text = data.get("text", "")
    # OpenAI API 返回 verbose_json 时含 segments
    segs = data.get("segments", [])
    seg_list = [
        {"start": s.get("start", 0), "end": s.get("end", 0), "text": s.get("text", "").strip()}
        for s in segs
    ] if segs else [{"start": 0, "end": 0, "text": text}]
    return ASRResult(seg_list, text, language)


def _simulate_transcribe(audio_path: str, language: str) -> ASRResult:
    """SIMULATE 模式返回占位转录结果。"""
    return ASRResult(
        segments=[{"start": 0.0, "end": 3.0, "text": "[模拟转录]这是一段示例字幕文本"}],
        text="[模拟转录]这是一段示例字幕文本",
        language=language,
    )


def asr_result_to_srt(result: ASRResult) -> str:
    """把 ASR 结果转为 SRT 字幕格式。"""
    lines = []
    for i, seg in enumerate(result.segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
    return "\n".join(lines)


def _format_srt_time(seconds: float) -> str:
    """秒数转 SRT 时间格式 HH:MM:SS,mmm。"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

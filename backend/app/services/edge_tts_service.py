"""Edge TTS 配音 + 字幕时间轴同步服务。

核心优势：用 edge-tts（免费微软 TTS）的 WordBoundary 事件，在生成音频的
同时获取逐词时间戳，实现字幕与配音的帧级同步。替代传统「先 TTS 后猜时长」
的粗放方案。

设计参考：MoneyPrinterTurbo voice.py 的 Edge TTS WordBoundary 时间戳切分。
voice 映射：child_cn / female_cn / male_cn → edge-tts 的 zh-CN-* Neural 声音。

失败时返回空结果，由编排器回退到 tencent_tts provider + 累加时长字幕。
"""

import asyncio
import logging
import os
from pathlib import Path

import edge_tts

from app.core.config import settings

logger = logging.getLogger(__name__)

# ShotFlow voice 名称 → edge-tts voice ID 映射
_VOICE_MAP = {
    "child_cn": "zh-CN-XiaoxiaoNeural",      # 童声/活泼女声
    "female_cn": "zh-CN-XiaoxiaoNeural",      # 女声
    "male_cn": "zh-CN-YunxiNeural",           # 男声
    "female_cn_yun": "zh-CN-XiaoyiNeural",    # 女声（晓伊）
    "male_cn_yun": "zh-CN-YunyangNeural",     # 男声（云扬）
    "female_cn_lia": "zh-CN-liaoning-XiaobeiNeural",  # 东北女声
    "male_cn_sha": "zh-CN-shaanxi-XiaoniNeural",      # 陕西男声
}

# WordBoundary 的 offset/duration 以 100 纳秒为单位
_HNS_PER_SECOND = 10_000_000


def _resolve_voice(voice_name: str) -> str:
    """把 ShotFlow voice 名称解析为 edge-tts voice ID，未知名称兜底女声。"""
    return _VOICE_MAP.get(voice_name, "zh-CN-XiaoxiaoNeural")


def _resolve_proxy() -> str | None:
    """从环境变量解析代理 URL，沙箱内 edge-tts 需走代理才能连微软服务。"""
    return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")


class WordBoundary:
    """单个词的时间戳信息。"""

    __slots__ = ("text", "start", "duration")

    def __init__(self, text: str, start: float, duration: float):
        self.text = text
        self.start = start
        self.duration = duration

    @property
    def end(self) -> float:
        return self.start + self.duration


class TTSResult:
    """Edge TTS 生成结果：音频文件 + 逐词时间戳。"""

    __slots__ = ("audio_path", "word_boundaries", "duration")

    def __init__(self, audio_path: str, word_boundaries: list[WordBoundary], duration: float):
        self.audio_path = audio_path
        self.word_boundaries = word_boundaries
        self.duration = duration


async def generate_tts_with_subtitles(
    text: str,
    voice: str = "child_cn",
    rate: str = "+0%",
    output_dir: str = "",
    filename: str = "",
) -> TTSResult | None:
    """用 edge-tts 生成配音音频 + 逐词时间戳。

    返回 TTSResult（含音频路径和 WordBoundary 列表），失败返回 None。
    编排器据此决定是否回退到 tencent_tts。

    参数:
        text: 要合成的文本
        voice: ShotFlow voice 名称（child_cn/female_cn/male_cn）
        rate: 语速调整（"+0%" 正常, "+20%" 加速, "-10%" 减速）
        output_dir: 音频输出目录（空则用 STORAGE_DIR/tts）
        filename: 输出文件名（空则自动生成）
    """
    if not text or not text.strip():
        logger.warning("edge-tts: 文本为空，跳过")
        return None

    edge_voice = _resolve_voice(voice)
    proxy = _resolve_proxy()

    # 输出路径
    if not output_dir:
        output_dir = str(Path(settings.STORAGE_DIR) / "tts")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    if not filename:
        import hashlib
        fname = "tts_" + hashlib.md5(text.encode()).hexdigest()[:12] + ".mp3"
    else:
        if not filename.endswith(".mp3"):
            filename += ".mp3"
        fname = filename
    audio_path = str(Path(output_dir) / fname)

    word_boundaries: list[WordBoundary] = []
    audio_data = bytearray()

    try:
        communicate = edge_tts.Communicate(
            text,
            edge_voice,
            rate=rate,
            proxy=proxy,
            boundary="WordBoundary",
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration 单位为 100 纳秒（hectonanoseconds）
                start_sec = chunk["offset"] / _HNS_PER_SECOND
                dur_sec = chunk["duration"] / _HNS_PER_SECOND
                word_boundaries.append(WordBoundary(
                    text=chunk["text"],
                    start=start_sec,
                    duration=dur_sec,
                ))
    except Exception as exc:
        logger.warning("edge-tts 生成失败，编排器将回退到 tencent_tts: %s", exc)
        return None

    if not audio_data:
        logger.warning("edge-tts: 生成的音频为空")
        return None

    # 写入音频文件
    with open(audio_path, "wb") as f:
        f.write(audio_data)

    # 总时长 = 最后一个词的结束时间
    duration = word_boundaries[-1].end if word_boundaries else 0.0

    logger.info(
        "edge-tts 成功: voice=%s text=%d字 音频=%d字节 词数=%d 时长=%.2fs",
        edge_voice, len(text), len(audio_data), len(word_boundaries), duration,
    )

    return TTSResult(
        audio_path=audio_path,
        word_boundaries=word_boundaries,
        duration=duration,
    )


def group_words_to_subtitles(
    word_boundaries: list[WordBoundary],
    max_chars_per_line: int = 12,
    pause_threshold: float = 0.3,
) -> list[dict]:
    """把逐词时间戳分组成字幕行，兼顾字数与停顿断句。

    两种断行策略并用：
    1. 字数达上限（默认 12 字，短视频字幕最佳可读长度）
    2. 词间停顿超过 pause_threshold（默认 0.3 秒，对应句号/逗号的自然停顿）

    edge-tts 的 WordBoundary 不含标点，但停顿时间反映了标点位置，
    用停顿检测替代标点匹配，更准确地切分语义单元。

    返回 [{text, start, end}] 列表，供 subtitle_service 生成 SRT。
    """
    if not word_boundaries:
        return []

    lines: list[dict] = []
    current_words: list[WordBoundary] = []
    current_len = 0
    prev_end = None

    for wb in word_boundaries:
        # 检测停顿：当前词开始时间与上一词结束时间差 > threshold → 断行
        if prev_end is not None:
            gap = wb.start - prev_end
            if gap >= pause_threshold and current_words:
                line_text = "".join(w.text for w in current_words)
                lines.append({
                    "text": line_text,
                    "start": current_words[0].start,
                    "end": current_words[-1].end,
                })
                current_words = []
                current_len = 0

        current_words.append(wb)
        current_len += len(wb.text)
        prev_end = wb.end

        # 字数达上限 → 断行
        if current_len >= max_chars_per_line:
            line_text = "".join(w.text for w in current_words)
            lines.append({
                "text": line_text,
                "start": current_words[0].start,
                "end": current_words[-1].end,
            })
            current_words = []
            current_len = 0

    # 处理剩余未断行的词
    if current_words:
        line_text = "".join(w.text for w in current_words)
        lines.append({
            "text": line_text,
            "start": current_words[0].start,
            "end": current_words[-1].end,
        })

    return lines


def generate_srt_from_word_boundaries(
    word_boundaries: list[WordBoundary],
    max_chars_per_line: int = 15,
) -> str:
    """从 WordBoundary 列表生成精确时间轴的 SRT 字幕。

    与 subtitle_service.generate_srt_from_durations 的区别：
    - 后者按累加时长估算时间戳（粗略）
    - 本方法用 TTS 引擎返回的真实时间戳（精确到毫秒）
    """
    from app.services.subtitle_service import _format_timestamp

    lines_data = group_words_to_subtitles(word_boundaries, max_chars_per_line)
    if not lines_data:
        return ""

    srt_lines: list[str] = []
    for i, line in enumerate(lines_data):
        srt_lines.append(str(i + 1))
        srt_lines.append(
            f"{_format_timestamp(line['start'])} --> {_format_timestamp(line['end'])}"
        )
        srt_lines.append(line["text"])
        srt_lines.append("")  # SRT 条目间空行

    return "\n".join(srt_lines)

"""字幕生成服务 — 根据文本与时长生成 SRT。

设计参考：MoneyPrinterTurbo voice.py 的 Edge TTS WordBoundary 时间戳切分、
NarratoAI script_subtitle.py 的程序化时间戳累加。把离散字幕文本配以
累加时间戳，输出标准 SRT，供 ffmpeg subtitles 滤镜烧录到画面。
"""

import re
import unicodedata


def _format_timestamp(seconds: float) -> str:
    """秒数 → SRT 时间戳 HH:MM:SS,mmm。

    用整数毫秒 divmod 链自然处理进位，避免浮点累加导致的 60/1000 越界。
    """
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt_from_durations(
    subtitles: list[str],
    durations: list[float] = None,
) -> str:
    """根据字幕文本列表和每条时长，生成 SRT 格式字符串。

    时长按顺序累加为起止时间戳；若 durations 缺失或条数不足，缺省每条 3 秒，
    保证每条字幕都有可读的时间区间（否则 SRT 缺时间戳会被 ffmpeg 丢弃）。
    """
    if not subtitles:
        return ""

    if not durations or len(durations) < len(subtitles):
        # 不足部分补 3 秒，避免时间戳缺失导致 SRT 条目无效
        durations = list(durations or []) + [3.0] * (len(subtitles) - len(durations or []))

    lines: list[str] = []
    current = 0.0
    for i, text in enumerate(subtitles):
        # 最小 0.1 秒，防止零时长字幕生成空区间
        dur = max(0.1, float(durations[i]))
        start = current
        end = current + dur
        lines.append(str(i + 1))
        lines.append(f"{_format_timestamp(start)} --> {_format_timestamp(end)}")
        lines.append(str(text))
        lines.append("")  # SRT 条目间用空行分隔
        current = end

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 旁白拆分（移植自 NarratoAI script_subtitle.py split_narration）
# --------------------------------------------------------------------------- #

# 匹配「到标点为止」的文本片段：句号/问号/感叹号/分号/逗号/顿号/换行均可断句
_SENTENCE_PART_RE = re.compile(r"[^。！？!?；;，,、\n]+[。！？!?；;，,、]?")

# 短视频字幕最佳可读长度：超过此字数则强制断行
_DEFAULT_MAX_CHARS = 12


def _normalize_text(text: str) -> str:
    """合并多余空白，避免换行/多空格导致拆分出空片段。"""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _remove_punctuation(text: str) -> str:
    """去除标点符号：字幕烧录时标点无视觉意义，反而占用字数。"""
    return "".join(
        char for char in str(text or "")
        if not unicodedata.category(char).startswith("P")
    )


def clean_subtitle_text(text: str) -> str:
    """规整字幕文本：先合并空白再去标点，供烧录显示用。"""
    return _normalize_text(_remove_punctuation(text))


def split_narration(text: str, max_chars: int = _DEFAULT_MAX_CHARS) -> list[str]:
    """把旁白文本拆分为适合字幕显示的短句列表。

    两级断句策略：
    1. 先按标点切分自然语义单元（句号/逗号/顿号等）
    2. 若某单元仍超 max_chars，则硬切到 max_chars 上限
    3. 相邻短单元尽量合并，凑满 max_chars 后才输出一行

    最终去除标点后返回，避免烧录时标点浪费字数。
    """
    text = _normalize_text(text)
    if not text:
        return []

    max_chars = max(1, int(max_chars or _DEFAULT_MAX_CHARS))
    parts = [m.group(0).strip() for m in _SENTENCE_PART_RE.finditer(text)]
    if not parts:
        parts = [text]

    chunks: list[str] = []
    current = ""

    def _flush_long_part(part: str) -> str:
        # 超长片段硬切到 max_chars，剩余部分继续处理
        while len(part) > max_chars:
            chunks.append(part[:max_chars].strip())
            part = part[max_chars:].strip()
        return part

    for part in parts:
        if not part:
            continue
        if len(part) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            current = _flush_long_part(part)
            continue
        # 尝试把当前片段拼接到缓冲行，凑满一行再输出
        candidate = f"{current}{part}" if current else part
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = part

    if current:
        chunks.append(current.strip())

    # 去标点后过滤空行
    return [cleaned for chunk in chunks if (cleaned := clean_subtitle_text(chunk))]

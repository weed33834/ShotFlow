"""字幕生成服务 — 根据文本与时长生成 SRT。

设计参考：MoneyPrinterTurbo voice.py 的 Edge TTS WordBoundary 时间戳切分、
NarratoAI script_subtitle.py 的程序化时间戳累加。把离散字幕文本配以
累加时间戳，输出标准 SRT，供 ffmpeg subtitles 滤镜烧录到画面。
"""


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

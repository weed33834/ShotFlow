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

# ShortGPT EDGE_TTS_VOICENAME_MAPPING 移植：ISO 语言代码 → {gender: edge-tts voice ID}
# 保留 ShortGPT 选用的区域变体（如 en→en-AU 而非 en-US），避免随意改动已验证的音色。
_EDGE_TTS_LANG_VOICES: dict[str, dict[str, str]] = {
    "en": {"male": "en-AU-WilliamNeural", "female": "en-AU-NatashaNeural"},
    "es": {"male": "es-AR-TomasNeural", "female": "es-AR-ElenaNeural"},
    "fr": {"male": "fr-CA-AntoineNeural", "female": "fr-CA-SylvieNeural"},
    "ar": {"male": "ar-AE-HamdanNeural", "female": "ar-AE-FatimaNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "pl": {"male": "pl-PL-MarekNeural", "female": "pl-PL-ZofiaNeural"},
    "it": {"male": "it-IT-DiegoNeural", "female": "it-IT-ElsaNeural"},
    "pt": {"male": "pt-BR-AntonioNeural", "female": "pt-BR-FranciscaNeural"},
    "af": {"male": "af-ZA-WillemNeural", "female": "af-ZA-AdriNeural"},
    "am": {"male": "am-ET-AmehaNeural", "female": "am-ET-MekdesNeural"},
    "az": {"male": "az-AZ-BabekNeural", "female": "az-AZ-BanuNeural"},
    "bg": {"male": "bg-BG-BorislavNeural", "female": "bg-BG-KalinaNeural"},
    "bn": {"male": "bn-BD-PradeepNeural", "female": "bn-BD-NabanitaNeural"},
    "bs": {"male": "bs-BA-GoranNeural", "female": "bs-BA-VesnaNeural"},
    "ca": {"male": "ca-ES-EnricNeural", "female": "ca-ES-JoanaNeural"},
    "cs": {"male": "cs-CZ-AntoninNeural", "female": "cs-CZ-VlastaNeural"},
    "cy": {"male": "cy-GB-AledNeural", "female": "cy-GB-NiaNeural"},
    "da": {"male": "da-DK-JeppeNeural", "female": "da-DK-ChristelNeural"},
    "el": {"male": "el-GR-NestorasNeural", "female": "el-GR-AthinaNeural"},
    "et": {"male": "et-EE-KertNeural", "female": "et-EE-AnuNeural"},
    "fa": {"male": "fa-IR-FaridNeural", "female": "fa-IR-DilaraNeural"},
    "fi": {"male": "fi-FI-HarriNeural", "female": "fi-FI-NooraNeural"},
    "fil": {"male": "fil-PH-AngeloNeural", "female": "fil-PH-BlessicaNeural"},
    "gl": {"male": "gl-ES-RoiNeural", "female": "gl-ES-SabelaNeural"},
    "gu": {"male": "gu-IN-NiranjanNeural", "female": "gu-IN-DhwaniNeural"},
    "he": {"male": "he-IL-AvriNeural", "female": "he-IL-HilaNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "hr": {"male": "hr-HR-SreckoNeural", "female": "hr-HR-GabrijelaNeural"},
    "hu": {"male": "hu-HU-TamasNeural", "female": "hu-HU-NoemiNeural"},
    "id": {"male": "id-ID-ArdiNeural", "female": "id-ID-GadisNeural"},
    "is": {"male": "is-IS-GunnarNeural", "female": "is-IS-GudrunNeural"},
    "ja": {"male": "ja-JP-KeitaNeural", "female": "ja-JP-NanamiNeural"},
    "jv": {"male": "jv-ID-DimasNeural", "female": "jv-ID-SitiNeural"},
    "ka": {"male": "ka-GE-GiorgiNeural", "female": "ka-GE-EkaNeural"},
    "kk": {"male": "kk-KZ-DauletNeural", "female": "kk-KZ-AigulNeural"},
    "km": {"male": "km-KH-PisethNeural", "female": "km-KH-SreymomNeural"},
    "kn": {"male": "kn-IN-GaganNeural", "female": "kn-IN-SapnaNeural"},
    "ko": {"male": "ko-KR-InJoonNeural", "female": "ko-KR-SunHiNeural"},
    "lo": {"male": "lo-LA-KeomanyNeural", "female": "lo-LA-ChanthavongNeural"},
    "lt": {"male": "lt-LT-LeonasNeural", "female": "lt-LT-OnaNeural"},
    "lv": {"male": "lv-LV-NilsNeural", "female": "lv-LV-EveritaNeural"},
    "mk": {"male": "mk-MK-AleksandarNeural", "female": "mk-MK-MarijaNeural"},
    "ml": {"male": "ml-IN-MidhunNeural", "female": "ml-IN-MidhunNeural"},
    "mn": {"male": "mn-MN-YesuiNeural", "female": "mn-MN-BataaNeural"},
    "mr": {"male": "mr-IN-ManoharNeural", "female": "mr-IN-AarohiNeural"},
    "ms": {"male": "ms-MY-OsmanNeural", "female": "ms-MY-YasminNeural"},
    "mt": {"male": "mt-MT-JosephNeural", "female": "mt-MT-GraceNeural"},
    "my": {"male": "my-MM-ThihaNeural", "female": "my-MM-NilarNeural"},
    "no": {"male": "nb-NO-FinnNeural", "female": "nb-NO-PernilleNeural"},
    "ne": {"male": "ne-NP-SagarNeural", "female": "ne-NP-HemkalaNeural"},
    "nl": {"male": "nl-NL-MaartenNeural", "female": "nl-NL-FennaNeural"},
    "nb": {"male": "nb-NO-FinnNeural", "female": "nb-NO-PernilleNeural"},
    "nn": {"male": "nb-NO-FinnNeural", "female": "nb-NO-PernilleNeural"},
    "ps": {"male": "ps-AF-LatifaNeural", "female": "ps-AF-GulNawazNeural"},
    "ro": {"male": "ro-RO-EmilNeural", "female": "ro-RO-AlinaNeural"},
    "ru": {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"},
    "si": {"male": "si-LK-SameeraNeural", "female": "si-LK-ThiliniNeural"},
    "sk": {"male": "sk-SK-LukasNeural", "female": "sk-SK-ViktoriaNeural"},
    "sl": {"male": "sl-SI-RokNeural", "female": "sl-SI-PetraNeural"},
    "so": {"male": "so-SO-MuuseNeural", "female": "so-SO-UbaxNeural"},
    "sq": {"male": "sq-AL-IlirNeural", "female": "sq-AL-AnilaNeural"},
    "sr": {"male": "sr-RS-NicholasNeural", "female": "sr-RS-SophieNeural"},
    "su": {"male": "su-ID-JajangNeural", "female": "su-ID-TutiNeural"},
    "sv": {"male": "sv-SE-MattiasNeural", "female": "sv-SE-SofieNeural"},
    "sw": {"male": "sw-TZ-DaudiNeural", "female": "sw-TZ-DaudiNeural"},
    "ta": {"male": "ta-IN-ValluvarNeural", "female": "ta-IN-PallaviNeural"},
    "te": {"male": "te-IN-MohanNeural", "female": "te-IN-ShrutiNeural"},
    "th": {"male": "th-TH-NiwatNeural", "female": "th-TH-PremwadeeNeural"},
    "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
    "uk": {"male": "uk-UA-OstapNeural", "female": "uk-UA-PolinaNeural"},
    "ur": {"male": "ur-PK-AsadNeural", "female": "ur-PK-UzmaNeural"},
    "uz": {"male": "uz-UZ-SardorNeural", "female": "uz-UZ-MadinaNeural"},
    "vi": {"male": "vi-VN-NamMinhNeural", "female": "vi-VN-HoaiMyNeural"},
    "zh": {"male": "zh-CN-YunxiNeural", "female": "zh-CN-XiaoxiaoNeural"},
    "zu": {"male": "zu-ZA-ThembaNeural", "female": "zu-ZA-ThandoNeural"},
}

# 从 _EDGE_TTS_LANG_VOICES 生成 {gender}_{lang} → voice ID 扁平映射
_VOICE_MAP: dict[str, str] = {}
for _lang, _genders in _EDGE_TTS_LANG_VOICES.items():
    for _gender, _voice in _genders.items():
        _VOICE_MAP[f"{_gender}_{_lang}"] = _voice

# ShotFlow 中文特有映射：比通用 female_zh/male_zh 更细分（方言/角色变体）
# 放在生成映射之后以覆盖同名 key，保留历史调用方使用的别名
_VOICE_MAP.update({
    "child_cn": "zh-CN-XiaoxiaoNeural",
    "female_cn": "zh-CN-XiaoxiaoNeural",
    "male_cn": "zh-CN-YunxiNeural",
    "female_cn_yun": "zh-CN-XiaoyiNeural",
    "male_cn_yun": "zh-CN-YunyangNeural",
    "female_cn_lia": "zh-CN-liaoning-XiaobeiNeural",
    "male_cn_sha": "zh-CN-shaanxi-XiaoniNeural",
})

# WordBoundary 的 offset/duration 以 100 纳秒为单位
_HNS_PER_SECOND = 10_000_000

# 未知 voice 的兜底值
_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


def _resolve_voice(voice_name: str) -> str:
    """把 ShotFlow voice 名称解析为 edge-tts voice ID，未知名称兜底女声。

    支持三种输入：
    1. ShotFlow 别名（child_cn / female_cn / male_cn 等）
    2. {gender}_{lang} 命名规则（female_en / male_ja / female_ko 等）
    3. 直接传入的 edge-tts 原生 voice ID（含 "Neural" 后缀）
    """
    if not voice_name:
        return _DEFAULT_VOICE
    # 直接传入 edge-tts 原生 voice ID 时原样返回
    if "Neural" in voice_name:
        return voice_name
    return _VOICE_MAP.get(voice_name, _DEFAULT_VOICE)


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

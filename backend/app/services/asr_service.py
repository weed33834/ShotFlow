"""ASR 语音转文字服务 — 支持本地 FunASR / faster-whisper 和 OpenAI Whisper API。

用途：
1. 对已有视频/音频做转录，生成字幕时间轴
2. 视频翻译配音场景的源语言转录
3. 用户上传视频后自动生成字幕

Provider 选择策略（由 ASR_PROVIDER 配置控制）：
- funasr : 优先本地 FunASR（paraformer），不可用回落 faster-whisper → OpenAI API
- whisper: 优先本地 faster-whisper，不可用回落 OpenAI API
- openai  : 强制走 OpenAI Whisper API
- auto    : FunASR → faster-whisper → OpenAI API 逐级回落（默认，最稳）

FunASR（阿里达摩院开源）中文效果优于 Whisper，且完全本地推理无 API 成本，
作为开源增强优先集成；未安装 funasr 包时自动跳过，不影响其他链路。
"""
import asyncio
import logging
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


# --------------------------------------------------------------------------- #
# FunASR 本地 Provider（paraformer 模型，中文专精）
# --------------------------------------------------------------------------- #


class FunASRProvider:
    """FunASR 本地语音识别 Provider。

    基于 funasr Python 包（pip install funasr），使用 paraformer 系列模型：
    - paraformer-zh：中文语音识别（带 VAD + 标点恢复）
    - paraformer-en：英文语音识别

    模型加载耗时较长，故按 (语言, 模型名) 缓存实例，避免每次转录重复加载。
    所有推理调用是同步阻塞的（PyTorch CPU/GPU 推理），通过 asyncio.to_thread
    放到线程池执行，不阻塞事件循环。
    """

    # 模型实例缓存：key = language，value = AutoModel 实例
    # 加载 paraformer 需下载几百 MB 权重，缓存避免重复开销
    _model_cache: dict[str, Any] = {}

    # 语言 → paraformer 模型名映射
    # 中文用 paraformer-zh（带 VAD+PUNC 出句级分段），英文用 paraformer-en
    _LANG_MODEL: dict[str, str] = {
        "zh": "paraformer-zh",
        "en": "paraformer-en",
    }

    @classmethod
    def is_available(cls) -> bool:
        """检查 funasr 包是否已安装（延迟 import，未装返回 False 不抛错）。"""
        try:
            import funasr  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_model(self, language: str) -> Any:
        """获取（或加载并缓存）指定语言的 paraformer 模型。

        中文模型额外挂载 VAD（语音活动检测）与 PUNC（标点恢复）子模型，
        以获得句级分段与可读标点；英文模型仅用 paraformer-en。
        """
        # 兜底：未知语言按中文处理（paraformer-zh 对中英混合也有一定容错）
        lang = language if language in self._LANG_MODEL else "zh"
        if lang in self._model_cache:
            return self._model_cache[lang]

        from funasr import AutoModel

        model_name = self._LANG_MODEL[lang]
        # 中文模型启用 VAD + PUNC：VAD 切句得到时间轴，PUNC 补标点提升可读性
        # 英文 paraformer-en 不强制挂 PUNC（其 PUNC 模型面向中文）
        if lang == "zh":
            model = AutoModel(
                model=model_name,
                vad_model="fsmn-vad",
                punc_model="ct-punc",
            )
        else:
            model = AutoModel(model=model_name, vad_model="fsmn-vad")
        self._model_cache[lang] = model
        return model

    async def transcribe(
        self, audio_path: str, language: str, model_size: str = ""
    ) -> ASRResult:
        """用 FunASR paraformer 本地模型转录音频。

        model_size 参数为兼容现有 transcribe() 签名保留，FunASR 模型由语言决定，忽略此参。
        """
        # 延迟 import：funasr 未安装时抛 ImportError，由上层 fallback 捕获
        from funasr import AutoModel  # noqa: F401

        model = self._get_model(language)

        # generate 是同步阻塞调用，放线程池避免卡住事件循环
        def _do_generate():
            # batch_size_s=300 表示每批最多 300 秒音频，兼顾显存与吞吐
            return model.generate(input=audio_path, batch_size_s=300)

        res = await asyncio.to_thread(_do_generate)
        return self._parse_result(res, language)

    @staticmethod
    def _parse_result(res: list[dict], language: str) -> ASRResult:
        """把 FunASR generate 返回结果解析为 ASRResult。

        FunASR 返回形如 [{"key": "...", "text": "全文", "timestamp": [[s,e],...]}]
        - text：完整识别文本（已带标点）
        - timestamp：字符/句级时间戳（毫秒），有则用于构建分段
        带分句时间戳时按句分段，否则整段返回。
        """
        if not res:
            return ASRResult([], "", language)

        # 合并所有 chunk 的文本（多段音频会返回多个 item）
        full_text_parts: list[str] = []
        segments: list[dict] = []
        for item in res:
            text = (item.get("text") or "").strip()
            if text:
                full_text_parts.append(text)
            ts = item.get("timestamp") or []
            if ts:
                # timestamp 为 [[start_ms, end_ms], ...]，转秒
                # paraformer-zh 的 timestamp 是字符级，这里取每段首尾作为整段区间
                try:
                    start_s = float(ts[0][0]) / 1000.0
                    end_s = float(ts[-1][1]) / 1000.0
                except (IndexError, TypeError, ValueError):
                    start_s, end_s = 0.0, 0.0
                segments.append({"start": start_s, "end": end_s, "text": text})

        full_text = "".join(full_text_parts)
        # 无时间戳时退化为单段，保证结构完整
        if not segments and full_text:
            segments = [{"start": 0.0, "end": 0.0, "text": full_text}]
        return ASRResult(segments, full_text, language)


# 模块级单例，供 transcribe() 调度复用模型缓存
_funasr_provider = FunASRProvider()


# --------------------------------------------------------------------------- #
# 主转录入口（带 Provider 回落链）
# --------------------------------------------------------------------------- #


async def transcribe(
    audio_path: str,
    language: str = "zh",
    model_size: str = "base",
) -> ASRResult:
    """转录音频/视频文件为文字 + 时间轴。

    按 ASR_PROVIDER 配置决定优先级，逐级回落保证可用性：
    - auto    : FunASR → faster-whisper → OpenAI API
    - funasr  : FunASR（失败回落 faster-whisper → OpenAI API）
    - whisper : faster-whisper → OpenAI API
    - openai  : OpenAI Whisper API
    """
    if settings.SIMULATE_MODE:
        return _simulate_transcribe(audio_path, language)

    # getattr 防御性读取：旧配置对象无 ASR_PROVIDER 时不崩，默认 auto
    provider = (getattr(settings, "ASR_PROVIDER", "auto") or "auto").lower()

    # 构建候选 Provider 有序列表（auto = 全链路；指定则以其为主、其余兜底）
    # 始终以 OpenAI API 作为最终兜底，保证无本地模型时仍可转录
    if provider == "funasr":
        candidates = ["funasr", "whisper", "openai"]
    elif provider == "whisper":
        candidates = ["whisper", "openai"]
    elif provider == "openai":
        candidates = ["openai"]
    else:  # auto 或未知值
        candidates = ["funasr", "whisper", "openai"]

    for cand in candidates:
        try:
            if cand == "funasr":
                if not FunASRProvider.is_available():
                    logger.info("FunASR 未安装，跳过该 Provider")
                    continue
                logger.info("使用 FunASR(paraformer) 转录: %s", audio_path)
                return await _funasr_provider.transcribe(audio_path, language, model_size)
            if cand == "whisper":
                logger.info("使用 faster-whisper 本地转录: %s", audio_path)
                return await _transcribe_whisper_local(audio_path, language, model_size)
            if cand == "openai":
                logger.info("使用 OpenAI Whisper API 转录: %s", audio_path)
                return await _transcribe_whisper_api(audio_path, language)
        except ImportError:
            # 本地依赖未安装：记录并尝试下一个候选
            logger.info("%s 依赖未安装，尝试下一个 Provider", cand)
        except Exception as exc:
            # 该 Provider 失败：记录告警并回落，不中断转录能力
            logger.warning("%s 转录失败，回落下一个 Provider: %s", cand, exc)

    # 所有候选均失败：给出明确错误，便于上层排查
    raise RuntimeError(
        f"所有 ASR Provider 均不可用（candidates={candidates}）。"
        "请安装 funasr/faster-whisper，或配置 LLM_API_KEY 走 OpenAI API。"
    )


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

"""GPT-SoVITS 语音克隆 Provider。

能力: audio（零样本/少样本语音克隆 TTS）。
接入点: GPT-SoVITS 本地 API 服务（默认 http://127.0.0.1:9880），POST /tts。
鉴权: 无（本地部署，不校验 token）。
模式: 同步请求（直接返回音频字节流）。

GPT-SoVITS 是开源语音克隆方案：传入一段参考音频 + 参考文本 + 待合成文本，
即可生成与参考音色一致的语音。适用于「用本人/角色声线批量配音」场景，
替代商用 CosyVoice / 腾讯云 TTS，零 API 成本、数据不出本机。

调用契约（GPT-SoVITS api.py 的 /tts）：
  请求体 JSON:
    {
      "text": "待合成文本",
      "text_lang": "zh",          # zh / en / ja / ko 等
      "ref_audio_path": "/path/to/ref.wav",
      "prompt_text": "参考音频对应的文本",
      "prompt_lang": "zh"
    }
  响应: audio/wav 字节流（部分版本返回 JSON 含下载 url，两种都兼容）

优雅降级：GPTSOVITS_API_URL 未配置或服务不可达时走 simulate 占位，不阻断主链路。
"""

import logging
import time
from pathlib import Path

import httpx

from app.core.config import settings
from app.services.providers.base import AssetResult, BaseProvider

logger = logging.getLogger(__name__)

# GPT-SoVITS API 服务默认地址（本地部署，端口 9880 为官方默认）
_DEFAULT_GPTSOVITS_URL = "http://127.0.0.1:9880"


class GPTSoVITSProvider(BaseProvider):
    """GPT-SoVITS 语音克隆 Provider。

    与 CosyVoiceProvider 同构：继承 BaseProvider，复用 _simulate / _download_asset。
    区别在于 GPT-SoVITS 是本地自建 API 服务，无鉴权、无异步任务轮询，
    POST /tts 直接返回音频字节流，故落盘逻辑与 TencentTtsProvider 类似（字节直写）。
    """

    name = "gptsovits"
    # 仅声明 audio 能力，与 cosyvoice / tencent_tts 对齐
    capabilities = {"audio"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # base_url 优先取注入值，其次取配置，最后用本地默认
        # 用 getattr 防御性读取，避免旧 settings 无该字段时崩溃
        configured = getattr(settings, "GPTSOVITS_API_URL", "") or ""
        self.base_url = self.base_url or configured or _DEFAULT_GPTSOVITS_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无显式 base_url 配置 或 SIMULATE：返回占位，保证全链路可验证
        # 用 getattr 防 settings 缺字段；空串视为未配置 → simulate
        configured = getattr(settings, "GPTSOVITS_API_URL", "") or ""
        if self.simulate or not configured:
            return await self._simulate(kind, params)

        if kind != "audio":
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )

        # 参数提取：兼容多种 key 命名，与 cosyvoice/tencent_tts 保持一致
        text = params.get("text", params.get("prompt", ""))
        # 参考音频路径（克隆音色必需）；为空时 GPT-SoVITS 会用默认音色
        ref_audio_path = params.get("ref_audio_path", params.get("voice", ""))
        prompt_text = params.get("prompt_text", "")
        text_lang = params.get("text_lang", "zh")
        prompt_lang = params.get("prompt_lang", "zh")

        if not text:
            return AssetResult(
                provider=self.name, url="",
                meta={"error": "缺少待合成文本 text", **params},
            )

        body = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
        }
        tts_url = self.base_url.rstrip("/") + "/tts"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(tts_url, json=body)
                resp.raise_for_status()

                # 兼容两种响应：音频字节流 / JSON(含下载 url)
                content_type = (resp.headers.get("content-type") or "").lower()
                if content_type.startswith("audio/") or not content_type.startswith("application/json"):
                    # 直接返回音频字节 → 落盘
                    audio_bytes = resp.content
                    if not audio_bytes:
                        return AssetResult(
                            provider=self.name, url="",
                            meta={"error": "GPT-SoVITS 返回空音频", **params},
                        )
                    local_path = self._save_audio_bytes(audio_bytes, params, "wav")
                    return AssetResult(
                        url=local_path,
                        provider=self.name,
                        meta={
                            "status": "done",
                            "kind": "audio",
                            "format": "wav",
                            "text_lang": text_lang,
                            **params,
                        },
                    )

                # JSON 响应：尝试提取下载 url 再下载
                data = resp.json()
                audio_url = data.get("audio_url") or data.get("url") or ""
                if not audio_url:
                    return AssetResult(
                        provider=self.name, url="",
                        meta={"error": "GPT-SoVITS 未返回音频 url", "raw": data, **params},
                    )
                # 复用基类下载能力（远程 url → 本地文件）
                task_id = params.get("task_id", "") or f"gptsovits_{int(time.time())}"
                local_path = self._download_asset(audio_url, task_id, "audio", "wav")
                return AssetResult(
                    url=local_path,
                    provider=self.name,
                    meta={"status": "done", "kind": "audio", "format": "wav", **params},
                )
        except httpx.HTTPError as exc:
            # 服务不可达 / 返回错误：返回错误资产而非抛异常，保持与其它 provider 一致的降级行为
            logger.warning("GPT-SoVITS 调用失败(%s): %s", tts_url, exc)
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"GPT-SoVITS 服务不可用: {exc}", **params},
            )

    def _save_audio_bytes(self, audio_bytes: bytes, params: dict, ext: str = "wav") -> str:
        """把 GPT-SoVITS 返回的音频字节直接落盘到本地存储。

        与 TencentTtsProvider 的字节落盘逻辑同构：按 task_id 隔离目录，
        避免不同任务产物互相覆盖。
        """
        storage_dir = getattr(settings, "STORAGE_DIR", "") or str(
            Path(__file__).resolve().parents[4] / "storage"
        )
        storage_root = Path(storage_dir)
        task_dir = storage_root / "tasks" / (params.get("task_id", "") or "default")
        task_dir.mkdir(parents=True, exist_ok=True)
        local_path = task_dir / f"{self.name}_audio_{int(time.time())}.{ext}"
        local_path.write_bytes(audio_bytes)
        return str(local_path)

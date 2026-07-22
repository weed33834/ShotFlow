"""腾讯云语音合成（TTS）Provider。

能力: audio。
接入点: 腾讯云 TTS API，host tts.tencentcloudapi.com，Action TextToVoice。
        复用与 hunyuan_image 相同的 TC3-HMAC-SHA256 签名。
鉴权: secret_id / secret_key（腾讯云 CAM 密钥）。
模式: 同步请求（返回音频 base64）。

费用备注（调研值，2026）:
- 腾讯云 TTS 精品音色约 0.3 元/万字符，标准音色更便宜；新账号可领 800 万字符免费包。
- 以腾讯云官方计费页为准。SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import base64
import datetime
import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx

from app.core.config import settings
from app.services.providers.base import AssetResult, BaseProvider

_TC_HOST = "tts.tencentcloudapi.com"
_TC_SERVICE = "tts"
_TC_REGION = "ap-guangzhou"
_TC_VERSION = "2019-08-23"
_ACTION = "TextToVoice"


def _tc_signature(secret_id: str, secret_key: str, payload: str, timestamp: int) -> str:
    """腾讯云 TC3-HMAC-SHA256 签名（与 hunyuan_image 同构）。"""
    date = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
    canonical_headers = f"content-type:application/json\nhost:{_TC_HOST}\n"
    signed_headers = "content-type;host"
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = (
        f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    credential_scope = f"{date}/{_TC_SERVICE}/tc3_request"
    string_to_sign = (
        f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )
    secret_date = hmac.new(
        ("TC3" + secret_key).encode("utf-8"), date.encode("utf-8"), hashlib.sha256
    ).digest()
    secret_service = hmac.new(secret_date, _TC_SERVICE.encode("utf-8"), hashlib.sha256).digest()
    secret_signing = hmac.new(secret_service, b"tc3_request", hashlib.sha256).digest()
    return hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


class TencentTtsProvider(BaseProvider):
    name = "tencent_tts"
    capabilities = {"audio"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 腾讯云 CAM 密钥由上层通过 kwargs 注入，基类不统一存储
        self.secret_id = kwargs.get("secret_id", "")
        self.secret_key = kwargs.get("secret_key", "")
        self.host = _TC_HOST
        self.region = _TC_REGION
        self.version = _TC_VERSION

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.secret_id:
            return await self._simulate(kind, params)

        if kind != "audio":
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )

        text = params.get("text", params.get("prompt", ""))
        timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        date = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        codec = params.get("codec", "mp3") or "mp3"
        body = {
            "Text": text,
            "SessionId": params.get("session_id", "shotflow"),
            "VoiceType": params.get("voice_type", 1001),  # 精品音色 ID
            "Codec": codec,
            "SampleRate": params.get("sample_rate", 16000),
        }
        payload = json.dumps(body, ensure_ascii=False)
        signature = _tc_signature(self.secret_id, self.secret_key, payload, timestamp)
        headers = {
            "Content-Type": "application/json",
            "Host": self.host,
            "X-TC-Action": _ACTION,
            "X-TC-Version": self.version,
            "X-TC-Region": self.region,
            "X-TC-Timestamp": str(timestamp),
            # Credential 段第二段必须是日期(YYYY-MM-DD)，早期误填 region 导致签名校验失败
            "Authorization": (
                f"TC3-HMAC-SHA256 Credential={self.secret_id}/{date}/{_TC_SERVICE}"
                f"/tc3_request, SignedHeaders=content-type;host, "
                f"Signature={signature}"
            ),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://{self.host}/", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            audio = data.get("Response", {}).get("Audio")
            if not audio:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={
                        "error": data.get("Response", {}).get("Error", "no audio"),
                        **params,
                    },
                )
            # 同步接口：base64 音频直接落盘到本地，避免返回 url="" 链路断裂
            audio_bytes = base64.b64decode(audio)
            storage_root = (
                Path(settings.STORAGE_DIR)
                if settings.STORAGE_DIR
                else Path(settings.PROJECT_ROOT) / "storage"
            )
            task_dir = storage_root / "tasks" / (params.get("task_id", "") or "default")
            task_dir.mkdir(parents=True, exist_ok=True)
            local_path = task_dir / f"{self.name}_audio_{int(time.time())}.{codec}"
            local_path.write_bytes(audio_bytes)
            return AssetResult(
                provider=self.name,
                url=str(local_path),
                meta={"status": "done", "kind": "audio", "codec": codec, **params},
            )

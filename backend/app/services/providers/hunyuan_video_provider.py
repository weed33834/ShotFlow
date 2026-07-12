"""腾讯混元视频 Provider（AI 视频生成）。

能力: video。
接入点: 腾讯云 AI 视频生成 API，复用与 hunyuan_image 相同的 TC3-HMAC-SHA256 签名。
        host 可能为 vclm.tencentcloudapi.com（AI 视频）或 aiart，以官方文档为准。
鉴权: secret_id / secret_key（腾讯云 CAM 密钥）。
模式: 异步 job（Submit → Query 轮询）。

费用备注（调研值，2026）:
- 混元视频生成按生成秒数计费，约 0.1~0.3 元/秒（不同清晰度档位不同），以腾讯云官方计费页为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import datetime
import hashlib
import hmac
import json

import httpx

from app.services.providers.base import AssetResult, BaseProvider

# host 以官方文档为准（AI 视频多为 vclm 服务）
_TC_HOST = "vclm.tencentcloudapi.com"
_TC_SERVICE = "vclm"
_TC_REGION = "ap-guangzhou"
_TC_VERSION = "2024-05-13"
# 混元视频提交 / 查询 Action（以官方文档核对为准）
_ACTION_SUBMIT = "SubmitVideoGenerationJob"
_ACTION_QUERY = "QueryVideoGenerationJob"


def _tc_signature(secret_id: str, secret_key: str, payload: str, timestamp: int) -> str:
    """腾讯云 TC3-HMAC-SHA256 签名（与 hunyuan_image 同构）。"""
    date = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
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


class HunyuanVideoProvider(BaseProvider):
    name = "hunyuan_video"
    capabilities = {"video"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.host = _TC_HOST
        self.region = _TC_REGION
        self.version = _TC_VERSION

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.secret_id:
            return await self._simulate(kind, params)

        if kind != "video":
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )

        prompt = params.get("prompt", "")
        duration = params.get("duration", 5)
        timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        body = {
            "Prompt": prompt,
            "Duration": duration,
        }
        payload = json.dumps(body, ensure_ascii=False)
        signature = _tc_signature(self.secret_id, self.secret_key, payload, timestamp)
        headers = {
            "Content-Type": "application/json",
            "Host": self.host,
            "X-TC-Action": _ACTION_SUBMIT,
            "X-TC-Version": self.version,
            "X-TC-Region": self.region,
            "X-TC-Timestamp": str(timestamp),
            "Authorization": (
                f"TC3-HMAC-SHA256 Credential={self.secret_id}/{self.region}/{_TC_SERVICE}"
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
            job_id = data.get("Response", {}).get("JobId")
            if not job_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": data.get("Response", {}).get("Error", "no job_id")},
                )
            return AssetResult(
                provider=self.name,
                url="",
                meta={"job_id": job_id, "status": "submitted", "kind": kind, **params},
            )

"""腾讯混元视频 Provider（AI 视频生成）。

能力: video。
接口: 腾讯云 AI 视频生成 API（vclm.tencentcloudapi.com），TC3-HMAC-SHA256 签名，异步 job 模式。

费用备注（调研值，2026）:
- 混元视频生成按生成秒数计费，约 0.1~0.3 元/秒，以腾讯云官方计费页为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import datetime
import hashlib
import hmac
import json

import httpx

from app.services.providers.base import AssetResult, BaseProvider

# 以腾讯云官方文档为准：https://cloud.tencent.com/document/api/1616/128602
_TC_HOST = "vclm.tencentcloudapi.com"
_TC_SERVICE = "vclm"
_TC_REGION = "ap-guangzhou"
_TC_VERSION = "2024-05-23"
_ACTION_SUBMIT = "SubmitAigcVideoJob"
_ACTION_QUERY = "DescribeAigcVideoJob"

# Status 值 → 统一状态映射（官方文档：WAIT/RUN/FAIL/DONE）
_VIDEO_STATUS_MAP = {
    "WAIT": "running",
    "RUN": "running",
    "FAIL": "failed",
    "DONE": "succeeded",
}


def _tc_signature(secret_id: str, secret_key: str, payload: str, timestamp: int) -> str:
    """腾讯云 TC3-HMAC-SHA256 签名。"""
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


def _build_headers(action: str, timestamp: int, secret_id: str, secret_key: str, payload: str) -> dict:
    """构建腾讯云 API 请求头（含 TC3 签名）。"""
    date = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
    signature = _tc_signature(secret_id, secret_key, payload, timestamp)
    return {
        "Content-Type": "application/json",
        "Host": _TC_HOST,
        "X-TC-Action": action,
        "X-TC-Version": _TC_VERSION,
        "X-TC-Region": _TC_REGION,
        "X-TC-Timestamp": str(timestamp),
        "Authorization": (
            f"TC3-HMAC-SHA256 Credential={secret_id}/{date}/{_TC_SERVICE}"
            f"/tc3_request, SignedHeaders=content-type;host, "
            f"Signature={signature}"
        ),
    }


class HunyuanVideoProvider(BaseProvider):
    name = "hunyuan_video"
    capabilities = {"video"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secret_id = kwargs.get("secret_id", "")
        self.secret_key = kwargs.get("secret_key", "")

    async def generate(self, kind: str, params: dict) -> AssetResult:
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
        # 官方文档必填字段：Vendor + Model，其他参数放 ModelParam（JSON 字符串）
        body = {
            "Vendor": "HY",
            "Model": "hunyuan-video",
            "ModelParam": json.dumps({
                "Prompt": prompt,
                "Duration": duration,
            }, ensure_ascii=False),
        }
        payload = json.dumps(body, ensure_ascii=False)
        headers = _build_headers(_ACTION_SUBMIT, timestamp, self.secret_id, self.secret_key, payload)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"https://{_TC_HOST}/", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("Response", {}).get("JobId")
            if not job_id:
                return AssetResult(
                    provider=self.name, url="",
                    meta={"error": data.get("Response", {}).get("Error", "no job_id")},
                )
            # 轮询查询视频结果
            query_body = {"JobId": job_id}
            query_payload = json.dumps(query_body, ensure_ascii=False)
            query_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            query_headers = _build_headers(
                _ACTION_QUERY, query_ts, self.secret_id, self.secret_key, query_payload
            )
            url, poll_data = await self._poll_task(
                client,
                f"https://{_TC_HOST}/",
                headers=query_headers,
                method="POST",
                json_body=query_body,
                # 官方字段为 Status（WAIT/RUN/FAIL/DONE），需映射到统一状态
                extract_status=lambda d: _VIDEO_STATUS_MAP.get(
                    d.get("Response", {}).get("Status", ""), ""
                ),
                # 官方字段为 ResultUrl
                extract_url=lambda d: d.get("Response", {}).get("ResultUrl", ""),
            )
            if not url:
                return AssetResult(
                    provider=self.name, url="",
                    meta={"error": "no video url", "job_id": job_id, **poll_data},
                )
            local_path = self._download_asset(url, job_id, "video", "mp4")
            return AssetResult(
                url=local_path,
                provider=self.name,
                meta={"job_id": job_id, "kind": kind, **poll_data, **params},
            )

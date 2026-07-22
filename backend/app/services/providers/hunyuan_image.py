"""腾讯混元生图 Provider（AI 绘画）。

能力: image / anchor（一致性锚定 — 用参考图保角色外观一致）。
接口: 腾讯云 AI 绘画 API（aiart.tencentcloudapi.com），TC3-HMAC-SHA256 签名，异步 job 模式。

费用备注（调研值，2026）:
- 混元生图按张计费，约 0.1~0.2 元/张，以腾讯云官方计费页为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import datetime
import hashlib
import hmac
import json

import httpx

from app.services.providers.base import AssetResult, BaseProvider

_TC_HOST = "aiart.tencentcloudapi.com"
_TC_SERVICE = "aiart"
_TC_REGION = "ap-guangzhou"
# 以腾讯云官方文档为准：https://cloud.tencent.com/document/api/1668/124632
_TC_VERSION = "2022-12-29"
_ACTION_SUBMIT = "SubmitTextToImageJob"
_ACTION_QUERY = "QueryTextToImageJob"

# JobStatusCode 值 → 统一状态映射（官方文档：1=等待 2=运行 4=失败 5=完成）
_JOB_STATUS_MAP = {
    "1": "running",
    "2": "running",
    "4": "failed",
    "5": "succeeded",
}


def _first_or_str(val) -> str:
    """ResultImage 可能是 url 列表或单字符串，统一取首个 url。"""
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""


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


class HunyuanImageProvider(BaseProvider):
    name = "hunyuan_image"
    capabilities = {"image", "anchor"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secret_id = kwargs.get("secret_id", "")
        self.secret_key = kwargs.get("secret_key", "")

    async def generate(self, kind: str, params: dict) -> AssetResult:
        if self.simulate or not self.secret_id:
            return await self._simulate(kind, params)

        prompt = params.get("prompt", "")
        ref_images: list[str] = params.get("ref_images", [])
        timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        body = {
            "Prompt": prompt,
            # 官方文档字段名为 Images（JSON 数组，最多 3 张参考图）
            "Images": ref_images[:3],
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
            # 轮询查询：每轮重算签名，避免长时间轮询后签名过期
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
                # 官方字段为 JobStatusCode（"1"~"5"），需映射到统一状态
                extract_status=lambda d: _JOB_STATUS_MAP.get(
                    d.get("Response", {}).get("JobStatusCode", ""), ""
                ),
                extract_url=lambda d: _first_or_str(
                    d.get("Response", {}).get("ResultImage")
                ),
            )
            if not url:
                return AssetResult(
                    provider=self.name, url="",
                    meta={"error": "no image url", "job_id": job_id, **poll_data},
                )
            local_path = self._download_asset(url, job_id, "image", "png")
            return AssetResult(
                url=local_path,
                provider=self.name,
                meta={"job_id": job_id, "kind": kind, **poll_data, **params},
            )

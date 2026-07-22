"""腾讯混元生图 3.0 Provider（AI 绘画，TokenHub 模型 hy-image-v3.0）。

能力: image / anchor（一致性锚定 —— 用参考图保角色长相一致）。
接口: 腾讯云 AI 绘画 API（aiart.tencentcloudapi.com），TC3-HMAC-SHA256 签名，异步 job 模式。
签名与调用结构已实现；具体 Action / 参数以腾讯云官方文档为准（SIMULATE 模式兜底，无需 Key 即可验证全链路）。
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
_TC_VERSION = "2023-05-30"
# 混元生图 3.0 提交 / 查询任务 Action（以官方文档核对为准）
_ACTION_SUBMIT = "SubmitTextToImageProJob"
_ACTION_QUERY = "QueryTextToImageJob"


def _first_or_str(val) -> str:
    """ResultImage 可能是 url 列表或单字符串，统一取首个 url。"""
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""


def _tc_signature(secret_id: str, secret_key: str, payload: str, timestamp: int) -> str:
    """腾讯云 TC3-HMAC-SHA256 签名。"""
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


class HunyuanImageProvider(BaseProvider):
    name = "hunyuan_image"
    capabilities = {"image", "anchor"}

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

        prompt = params.get("prompt", "")
        ref_images: list[str] = params.get("ref_images", [])
        # 真实调用（结构完整，Action 名以官方文档为准）
        timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        date = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        body = {
            "Prompt": prompt,
            # 混元生图 3.0 支持最多 3 张参考图做一致性锚定
            "InputImageUrls": ref_images[:3],
            "RspImgType": "url",
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
            job_id = data.get("Response", {}).get("JobId")
            if not job_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": data.get("Response", {}).get("Error", "no job_id")},
                )
            # 轮询查询出图结果：轮询开始时签名一次，TC3 允许 ~10min 时钟偏差，
            # 默认 300s 轮询窗口内单次签名仍有效，避免每轮重签
            query_body = {"JobId": job_id}
            query_payload = json.dumps(query_body, ensure_ascii=False)
            query_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            query_sig = _tc_signature(
                self.secret_id, self.secret_key, query_payload, query_ts
            )
            query_date = datetime.datetime.utcfromtimestamp(query_ts).strftime("%Y-%m-%d")
            query_headers = {
                "Content-Type": "application/json",
                "Host": self.host,
                "X-TC-Action": _ACTION_QUERY,
                "X-TC-Version": self.version,
                "X-TC-Region": self.region,
                "X-TC-Timestamp": str(query_ts),
                "Authorization": (
                    f"TC3-HMAC-SHA256 Credential={self.secret_id}/{query_date}/{_TC_SERVICE}"
                    f"/tc3_request, SignedHeaders=content-type;host, "
                    f"Signature={query_sig}"
                ),
            }
            url, poll_data = await self._poll_task(
                client,
                f"https://{self.host}/",
                headers=query_headers,
                method="POST",
                json_body=query_body,
                extract_status=lambda d: d.get("Response", {}).get("JobStatus", ""),
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

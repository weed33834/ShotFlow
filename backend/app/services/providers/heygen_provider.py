"""HeyGen Provider（数字人 / 对口型 / 视频生成）。

能力: lipsync / video。
接入点: https://api.heygen.com （可由 base_url 覆盖）。
鉴权: Bearer HEYGEN_API_KEY（构造时传入 api_key）。
模式: 异步（create video → poll）。

费用备注（调研值，2026）:
- HeyGen 订阅制，Creator 套餐约 29 美元/月起，按视频分钟数/额度计费；对口型 API 独立额度。
- 商用需确认订阅条款。以 HeyGen 官方定价为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import json

import httpx

from app.services.providers.base import AssetResult, BaseProvider

_HEYGEN_BASE_URL = "https://api.heygen.com"
_POLL_INTERVAL = 10
_POLL_MAX = 60


class HeygenProvider(BaseProvider):
    name = "heygen"
    capabilities = {"lipsync", "video"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _HEYGEN_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind == "video":
            return await self._create_talking_avatar(params)
        if kind == "lipsync":
            return await self._create_lipsync(params)
        return AssetResult(
            provider=self.name, url="",
            meta={"error": f"unsupported kind: {kind}", **params},
        )

    async def _create_talking_avatar(self, params: dict) -> AssetResult:
        """创建数字人视频（avatar + script）。"""
        body = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": params.get("avatar_id", ""),
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "text",
                        "input_text": params.get("prompt", ""),
                        "voice_id": params.get("voice_id", ""),
                    },
                }
            ],
            "dimension": params.get("dimension", {"width": 1280, "height": 720}),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/v2/video/generate", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            video_id = data.get("data", {}).get("video_id")
            if not video_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": "no video_id", "raw": data, **params},
                )
            return AssetResult(
                provider=self.name,
                url="",
                meta={"video_id": video_id, "status": "submitted", "kind": "video", **params},
            )

    async def _create_lipsync(self, params: dict) -> AssetResult:
        """对口型：上传视频 + 音频后提交。"""
        body = {
            "video_url": params.get("video_url", ""),
            "audio_url": params.get("audio_url", ""),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/v1/lipsync/create", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            video_id = data.get("data", {}).get("video_id") or data.get("id")
            if not video_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": "no video_id", "raw": data, **params},
                )
            return AssetResult(
                provider=self.name,
                url="",
                meta={"video_id": video_id, "status": "submitted", "kind": "lipsync", **params},
            )

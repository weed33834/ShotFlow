"""Runway Provider（Gen-3 / Gen-4 视频生成）。

能力: video。
接入点: https://api.runwayml.com/v1 （可由 base_url 覆盖）。
鉴权: Bearer RUNWAY_API_KEY（构造时传入 api_key）。
模式: 异步 task（创建 task → 轮询）。

费用备注（调研值，2026）:
- Runway 按 credits 计费，Gen-3 约 5 credits/秒（约 0.05~0.1 美元/秒），以 Runway 官方定价为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import json

import httpx

from app.services.providers.base import AssetResult, BaseProvider

_RUNWAY_BASE_URL = "https://api.runwayml.com/v1"
_POLL_INTERVAL = 5
_POLL_MAX = 120


class RunwayProvider(BaseProvider):
    name = "runway"
    capabilities = {"video"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _RUNWAY_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind != "video":
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )

        prompt = params.get("prompt", "")
        model = params.get("model", "gen3a_turbo")
        body = {
            "promptText": prompt,
            "model": model,
            "duration": params.get("duration", 5),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            # 创建视频生成任务（endpoint 以官方文档为准）
            resp = await client.post(
                f"{self.base_url}/image_to_video", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("id") or data.get("taskId") or data.get("uuid")
            if not task_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": "no task_id", "raw": data, **params},
                )
            return AssetResult(
                provider=self.name,
                url="",
                meta={
                    "task_id": task_id,
                    "status": "submitted",
                    "kind": "video",
                    "model": model,
                    **params,
                },
            )

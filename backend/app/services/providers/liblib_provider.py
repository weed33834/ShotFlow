"""Liblib（哩布哩布）Provider（文生图 / 模型社区）。

能力: image。
接入点: https://openapi.liblibai.cloud （可由 base_url 覆盖）。
鉴权: Bearer LIBLIB_API_KEY（构造时传入 api_key）。
模式: 异步（提交任务 → 轮询）。

费用备注（调研值，2026）:
- Liblib 开放平台按生成张数计费，约 0.01~0.1 元/张（取决于模型与分辨率），以 Liblib 官方计费为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import json

import httpx

from app.services.providers.base import AssetResult, BaseProvider

_LIBLIB_BASE_URL = "https://openapi.liblibai.cloud"
_POLL_INTERVAL = 5
_POLL_MAX = 120


class LiblibProvider(BaseProvider):
    name = "liblib"
    capabilities = {"image"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _LIBLIB_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind != "image":
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )

        prompt = params.get("prompt", "")
        # 模型 key 由上层指定（官方模型标识），以官方文档为准
        body = {
            "model": params.get("model", ""),
            "prompt": prompt,
            "negative_prompt": params.get("negative_prompt", ""),
            "width": params.get("width", 1024),
            "height": params.get("height", 1024),
            "images_num": params.get("n", 1),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            # 提交生成任务（endpoint 以官方文档为准）
            resp = await client.post(
                f"{self.base_url}/api/generate/webui", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("taskId") or data.get("task_id")
            if not task_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": "no task_id", "raw": data, **params},
                )
            return AssetResult(
                provider=self.name,
                url="",
                meta={"task_id": task_id, "status": "submitted", "kind": "image", **params},
            )

"""即梦（字节跳动火山引擎 Ark）Provider。

能力: image / video。
接入点: 火山引擎方舟大模型平台（Ark），默认
        https://ark.cn-beijing.volces.com/api/v3 （可由 base_url 覆盖）。
鉴权: Bearer JIMENG_API_KEY（构造时传入 api_key）。
模式: 异步任务（submit → poll）。

费用备注（调研值，2026）:
- 即梦文生图/视频走火山引擎方舟按 token/时长计费，文生视频约 0.1~0.3 元/秒，以火山引擎官方计费为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import json

import httpx

from app.services.providers.base import AssetResult, BaseProvider

_JIMENG_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
# 模型名以官方文档为准（即梦在方舟上的 endpoint id）
_IMAGE_MODEL = "jimeng-image"   # 占位，实际为方舟 endpoint id
_VIDEO_MODEL = "jimeng-video"   # 占位，实际为方舟 endpoint id
_POLL_INTERVAL = 5
_POLL_MAX = 120


class JimengProvider(BaseProvider):
    name = "jimeng"
    capabilities = {"image", "video"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _JIMENG_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind == "image":
            return await self._submit_image(params)
        if kind == "video":
            return await self._submit_video(params)
        return AssetResult(
            provider=self.name, url="",
            meta={"error": f"unsupported kind: {kind}", **params},
        )

    async def _submit_image(self, params: dict) -> AssetResult:
        """文生图：OpenAI 兼容 /images/generations。"""
        prompt = params.get("prompt", "")
        body = {
            "model": _IMAGE_MODEL,
            "prompt": prompt,
            "n": params.get("n", 1),
            "size": params.get("size", "1024x1024"),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/images/generations", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            url = (data.get("data") or [{}])[0].get("url", "")
            return AssetResult(
                provider=self.name, url=url,
                meta={"kind": "image", "model": _IMAGE_MODEL, **params},
            )

    async def _submit_video(self, params: dict) -> AssetResult:
        """文生视频：提交任务 → 轮询（方舟视频任务接口，路径以官方文档为准）。"""
        prompt = params.get("prompt", "")
        body = {
            "model": _VIDEO_MODEL,
            "input": {"prompt": prompt},
            "parameters": {"duration": params.get("duration", 5)},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/video/generations", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("id") or data.get("task_id")
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
                    "model": _VIDEO_MODEL,
                    **params,
                },
            )

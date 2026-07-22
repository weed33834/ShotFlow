"""可灵 Kling Provider。

能力: video / anchor / lipsync。
接入点: Pika/可灵聚合平台（piapi.ai）的 Kling 接口，默认
        https://api.piapi.ai （可由 base_url 覆盖）。
鉴权: Bearer KLING_API_KEY（构造时传入 api_key）。
模式: 异步 task（提交 task → 轮询 task 状态）。

费用备注（调研值，2026）:
- 可灵 Kling 1.6 标准版约 0.5~1 元/秒（按生成视频时长），大师版更贵；以平台官方计费为准。
- anchor（图生视频 / 参考图保一致性）、lipsync（对口型）均复用同一 task 体系。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import httpx

from app.services.providers.base import AssetResult, BaseProvider

_KLING_BASE_URL = "https://api.piapi.ai"
# 三种能力对应的 task 模型标识（以官方文档为准）
_TASK_MODELS = {
    "video": "kling-video",       # 文生/图生视频
    "anchor": "kling-video",      # 参考图保一致性（复用视频 + image 参数）
    "lipsync": "kling-lipsync",   # 对口型
}


def _first_url(val) -> str:
    """output.images 可能是 url 列表，统一取首个。"""
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""


class KlingProvider(BaseProvider):
    name = "kling"
    capabilities = {"video", "anchor", "lipsync"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _KLING_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind not in self.capabilities:
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )
        return await self._submit_task(kind, params)

    async def _submit_task(self, kind: str, params: dict) -> AssetResult:
        """提交 Kling task 并轮询。

        piapi.ai 的 Kling 接口结构：POST {base}/api/v1/task 提交，
        GET {base}/api/v1/task/{task_id} 查询。以下路径 / JSON 以官方文档为准。
        """
        model = _TASK_MODELS.get(kind, "kling-video")
        prompt = params.get("prompt", "")
        # 视频/锚定支持参考图；lipsync 需要 video + audio
        task_input: dict = {"prompt": prompt}
        if kind in ("video", "anchor") and params.get("ref_images"):
            task_input["image"] = params["ref_images"][0]
        if kind == "lipsync":
            task_input["video"] = params.get("video_url", "")
            task_input["audio"] = params.get("audio_url", "")

        body = {"model": model, "input": task_input}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        submit_url = f"{self.base_url}/api/v1/task"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(submit_url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("task_id") or data.get("data", {}).get("task_id")
            if not task_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": "no task_id", "raw": data, **params},
                )
            # 轮询取结果：data.status 终态后从 data.output 取 video_url 或首张图
            url, poll_data = await self._poll_task(
                client,
                f"{self.base_url}/api/v1/task/{task_id}",
                headers=headers,
                extract_status=lambda d: d.get("data", {}).get("status", ""),
                extract_url=lambda d: (
                    d.get("data", {}).get("output", {}).get("video_url", "")
                    or _first_url(d.get("data", {}).get("output", {}).get("images"))
                ),
            )
            if not url:
                return AssetResult(
                    provider=self.name, url="",
                    meta={"error": "no asset url", "task_id": task_id, **poll_data},
                )
            local_path = self._download_asset(url, task_id, "video", "mp4")
            return AssetResult(
                url=local_path,
                provider=self.name,
                meta={
                    "task_id": task_id,
                    "kind": kind,
                    "model": model,
                    **poll_data,
                    **params,
                },
            )

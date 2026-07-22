"""阿里通义万相（WanX）Provider。

能力: image / video。
接入点: 阿里云百炼 DashScope 兼容 OpenAI 的接口
        https://dashscope.aliyuncs.com/compatible-mode/v1
鉴权: Bearer DASHSCOPE_API_KEY（构造时由主理人传入 api_key 映射）。
模型: 文生图 wanx2.2-t2i；文生视频 wan2.7-t2v（异步 task 轮询）。

费用备注（调研值，2026）:
- 万相文生图: wanx2.2-t2i 约 0.08 元/张（1024 分辨率），具体以阿里云官方计费页为准。
- 万相视频生成: wan2.7-t2v 按生成秒数计费，约 0.1~0.2 元/秒，输出 720P。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

from urllib.parse import urlparse

import httpx

from app.services.providers.base import AssetResult, BaseProvider

# DashScope 兼容模式默认 base url（可被构造参数 base_url 覆盖）
_WANX_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_IMAGE_MODEL = "wanx2.2-t2i"
_VIDEO_MODEL = "wan2.7-t2v"


class WanxProvider(BaseProvider):
    name = "wanx"
    capabilities = {"image", "video"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _WANX_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind == "image":
            return await self._generate_image(params)
        if kind == "video":
            return await self._generate_video(params)
        return AssetResult(
            provider=self.name, url="",
            meta={"error": f"unsupported kind: {kind}", **params},
        )

    async def _generate_image(self, params: dict) -> AssetResult:
        """文生图：OpenAI 兼容 /images/generations，下载到本地供下游 ffmpeg 读取。"""
        prompt = params.get("prompt", "")
        size = params.get("size", "1024*1024")
        n = params.get("n", 1)
        body = {
            "model": _IMAGE_MODEL,
            "prompt": prompt,
            "n": n,
            "size": size,
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
            if not url:
                return AssetResult(
                    provider=self.name, url="",
                    meta={"error": "no image url", "raw": data, **params},
                )
            # 远程 url 落地到本地，下游 ffmpeg 需要本地路径拼接
            local_path = self._download_asset(url, params.get("task_id", "") or "wanx_img", "image", "png")
            return AssetResult(
                url=local_path,
                provider=self.name,
                meta={"kind": "image", "model": _IMAGE_MODEL, **params},
            )

    async def _generate_video(self, params: dict) -> AssetResult:
        """文生视频：提交任务 → 轮询。

        DashScope 万相视频使用任务（task）模式，先提交拿到 task_id，
        再用 /api/v1/tasks/{task_id} 轮询 output.task_status 直到终态。
        """
        prompt = params.get("prompt", "")
        duration = params.get("duration", 5)
        # 视频生成任务提交接口（以官方文档核对为准）
        submit_url = f"{self.base_url}/video/generations"
        body = {
            "model": _VIDEO_MODEL,
            "input": {"prompt": prompt},
            "parameters": {"duration": duration},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(submit_url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("output", {}).get("task_id") or data.get("task_id")
            if not task_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": "no task_id", "raw": data, **params},
                )
            # 任务查询接口与兼容模式接口同主机不同路径，从 base_url 取 host 拼装
            parsed = urlparse(self.base_url)
            poll_url = f"{parsed.scheme}://{parsed.netloc}/api/v1/tasks/{task_id}"
            url, poll_data = await self._poll_task(
                client,
                poll_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                extract_status=lambda d: d.get("output", {}).get("task_status", ""),
                extract_url=lambda d: (
                    (d.get("output", {}).get("results") or [{}])[0].get("url", "")
                ),
            )
            if not url:
                return AssetResult(
                    provider=self.name, url="",
                    meta={"error": "no video url", "task_id": task_id, **poll_data},
                )
            local_path = self._download_asset(url, task_id, "video", "mp4")
            return AssetResult(
                url=local_path,
                provider=self.name,
                meta={
                    "task_id": task_id,
                    "kind": "video",
                    "model": _VIDEO_MODEL,
                    **poll_data,
                    **params,
                },
            )

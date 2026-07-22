"""NovelAI Provider（文生图 / 二次元风格）。

能力: image。
接入点: https://api.novelai.net （可由 base_url 覆盖）。
鉴权: Bearer NOVELAI_API_KEY（订阅 Token，构造时传入 api_key）。
模式: 同步 POST，直接返回图片（zip 流，内含 png）。无异步轮询。

费用备注（调研值，2026）:
- NovelAI 采用订阅制（如 Anime 档 / 更高档），订阅内可不限量出图，以 NovelAI 官方定价为准。
- 商用需确认订阅条款。SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import io
import time
import zipfile
from pathlib import Path

import httpx

from app.core.config import settings
from app.services.providers.base import AssetResult, BaseProvider

_NOVELAI_BASE_URL = "https://api.novelai.net"
# 生成接口（以官方文档为准）
_GEN_PATH = "/ai/generate-image"


class NovelaiProvider(BaseProvider):
    name = "novelai"
    capabilities = {"image"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _NOVELAI_BASE_URL

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
        # NovelAI 图像生成请求体（字段以官方文档为准）
        body = {
            "input": prompt,
            "model": params.get("model", "nai-diffusion-4-full"),
            "parameters": {
                "width": params.get("width", 1024),
                "height": params.get("height", 1024),
                "n_samples": params.get("n", 1),
                "negative_prompt": params.get("negative_prompt", ""),
                "steps": params.get("steps", 28),
                "sampler": params.get("sampler", "k_euler_ancestral"),
                "scale": params.get("cfg_scale", 5.0),
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            # 同步返回图片（zip 二进制流，内含 png）
            resp = await client.post(
                f"{self.base_url}{_GEN_PATH}", json=body, headers=headers
            )
            resp.raise_for_status()
            content = resp.content
            # NovelAI 返回 zip 包，内含图片；解出首张 png，否则按原始内容落盘
            image_bytes = content
            if content[:4] == b"PK\x03\x04":
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    png_names = [n for n in zf.namelist() if n.lower().endswith(".png")]
                    if png_names:
                        image_bytes = zf.read(png_names[0])
            # 落盘到本地，避免返回 url="" 链路断裂
            storage_root = (
                Path(settings.STORAGE_DIR)
                if settings.STORAGE_DIR
                else Path(settings.PROJECT_ROOT) / "storage"
            )
            task_dir = storage_root / "tasks" / (params.get("task_id", "") or "default")
            task_dir.mkdir(parents=True, exist_ok=True)
            local_path = task_dir / f"{self.name}_image_{int(time.time())}.png"
            local_path.write_bytes(image_bytes)
            return AssetResult(
                provider=self.name,
                url=str(local_path),
                meta={
                    "kind": "image",
                    "status": "done",
                    "content_type": resp.headers.get("content-type", ""),
                    **params,
                },
            )

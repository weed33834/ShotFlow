"""Suno Provider（AI 音乐 / BGM 生成）。

能力: audio。
接入点: https://api.sunoaiapi.com （可由 base_url 覆盖）。
鉴权: Bearer SUNO_API_KEY（构造时传入 api_key）。
模式: 异步（提交生成任务 → 轮询获取音频 URL）。

费用备注（调研值，2026）:
- Suno 采用订阅制，Pro 套餐约 10 美元/月可商用，按生成次数/额度计费。
- 商用需确认订阅条款（订阅可商用）。以 Suno 官方定价为准。
SIMULATE 模式兜底，无需 Key 即可验证全链路。
"""

import httpx

from app.services.providers.base import AssetResult, BaseProvider

_SUNO_BASE_URL = "https://api.sunoaiapi.com"


def _record(d: dict) -> dict:
    """record 接口返回 data 为记录列表，取首条；兼容直接返回列表。"""
    data = d.get("data")
    if isinstance(data, list):
        return data[0] if data else {}
    if isinstance(data, dict):
        return data
    return {}


class SunoProvider(BaseProvider):
    name = "suno"
    capabilities = {"audio"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _SUNO_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind != "audio":
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )

        prompt = params.get("prompt", "")
        # 自定义歌词 / 风格标签
        body = {
            "prompt": prompt,
            "custom_mode": params.get("custom_mode", False),
            "instrumental": params.get("instrumental", False),
            "style": params.get("style", ""),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            # 提交音乐生成（endpoint 以官方文档为准）
            resp = await client.post(
                f"{self.base_url}/api/v1/generate", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("task_id") or data.get("id")
            if not task_id:
                return AssetResult(
                    provider=self.name,
                    url="",
                    meta={"error": "no task_id", "raw": data, **params},
                )
            # 轮询 record 接口：status 终态后取首条 audio_url
            url, poll_data = await self._poll_task(
                client,
                f"{self.base_url}/api/v1/generate/record?ids={task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                extract_status=lambda d: _record(d).get("status", ""),
                extract_url=lambda d: _record(d).get("audio_url", ""),
            )
            if not url:
                return AssetResult(
                    provider=self.name, url="",
                    meta={"error": "no audio url", "task_id": task_id, **poll_data},
                )
            local_path = self._download_asset(url, task_id, "audio", "mp3")
            return AssetResult(
                url=local_path,
                provider=self.name,
                meta={"task_id": task_id, "kind": "audio", **poll_data, **params},
            )

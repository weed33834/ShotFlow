"""CosyVoice 语音克隆 Provider。

能力: audio（语音克隆 TTS）。
接入点: 阿里云 DashScope cosyvoice API（与 wanx 同平台）。
鉴权: Bearer DASHSCOPE_API_KEY。
模式: 异步任务（submit → poll → download）。

CosyVoice 支持参考音频克隆音色：传入一段参考音频 + 文本，
生成与参考音色一致的语音。适用于"用自己的声音批量配音"场景。
"""

from urllib.parse import urlparse

import httpx

from app.services.providers.base import AssetResult, BaseProvider

# DashScope 原生 API base url（与 wanx 的兼容模式路径前缀不同）
_COSYVOICE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
_COSYVOICE_MODEL = "cosyvoice-v2"


class CosyVoiceProvider(BaseProvider):
    name = "cosyvoice"
    capabilities = {"audio"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = self.base_url or _COSYVOICE_BASE_URL

    async def generate(self, kind: str, params: dict) -> AssetResult:
        # 无 Key 或显式 SIMULATE：返回占位，保证全链路可验证
        if self.simulate or not self.api_key:
            return await self._simulate(kind, params)

        if kind != "audio":
            return AssetResult(
                provider=self.name, url="",
                meta={"error": f"unsupported kind: {kind}", **params},
            )

        text = params.get("text", params.get("prompt", ""))
        # 参考音频 url（克隆音色）或预置音色 ID；为空时由服务端用默认音色
        voice = params.get("voice", params.get("voice_id", ""))
        body = {
            "model": _COSYVOICE_MODEL,
            "input": {
                "text": text,
                "voice": voice,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # 长文本同步返回易超时，DashScope 异步任务需显式开启
            "X-DashScope-Async": "enable",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            # 提交语音合成任务（与 wanx 视频同走 DashScope 任务体系）
            submit_url = f"{self.base_url}/audio/tts"
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
            # 任务查询接口与提交接口同主机，路径为 /api/v1/tasks/{task_id}
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
                    meta={"error": "no audio url", "task_id": task_id, **poll_data},
                )
            # 远程音频落地到本地，下游 ffmpeg 需要本地路径拼接
            local_path = self._download_asset(url, task_id, "audio", "mp3")
            return AssetResult(
                url=local_path,
                provider=self.name,
                meta={
                    "task_id": task_id,
                    "kind": "audio",
                    "model": _COSYVOICE_MODEL,
                    **poll_data,
                    **params,
                },
            )

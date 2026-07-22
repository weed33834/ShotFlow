"""供应商抽象基类 + 轮询基础设施。

设计要点（学自 NarratoAI fun_asr_subtitle.py 的 poll_transcription_task）：
- 异步任务型供应商统一走 submit → poll(轮询到终态) → download(落地真实文件)
- 之前所有 provider 只 submit 不 poll，导致 url 永远为空、链路断裂
- 这里提供通用轮询循环和资产下载，各 provider 只需实现 _query_status/_extract_url
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable

import httpx
from pydantic import BaseModel

from app.core.config import settings

# 轮询默认参数（参考 NarratoAI: poll_interval=2, timeout=600）
DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_POLL_TIMEOUT = 300.0
# 成功终态（不区分大小写匹配）
SUCCESS_STATES = {"succeeded", "success", "completed", "complete", "done", "finished"}
# 失败终态
FAILED_STATES = {"failed", "error", "cancelled", "canceled", "deleted"}


class AssetResult(BaseModel):
    """供应商生成结果。url 非空视为真实可用资产。"""

    url: str = ""
    provider: str = ""
    meta: dict[str, Any] = {}
    # 任务 ID（异步 provider 轮询时回填）
    task_id: str = ""


class BaseProvider:
    """所有供应商的基类。

    子类必须实现 generate()。异步任务型供应商应调用 _poll_task() 轮询取结果，
    并用 _download_asset() 把远程 url 落地到本地存储，避免只返回 task_id 占位。
    """

    name: str = "base"

    def __init__(self, simulate: bool = False, **kwargs: Any) -> None:
        self.simulate = simulate
        self.api_key = kwargs.get("api_key", "")
        self.base_url = kwargs.get("base_url", "")

    async def generate(self, kind: str, params: dict[str, Any]) -> AssetResult:
        """生成资产。子类实现真实调用，SIMULATE 模式返回占位。"""
        if self.simulate:
            return await self._simulate(kind, params)
        raise NotImplementedError

    async def _simulate(self, kind: str, params: dict[str, Any]) -> AssetResult:
        """SIMULATE 占位——仅用于无 key 时跑通全链路，不产生真实文件。"""
        return AssetResult(
            url=f"simulate://{self.name}/{kind}",
            provider=self.name,
            meta={"simulate": True, "kind": kind, **params},
        )

    # ===== 轮询基础设施（学自 NarratoAI poll_transcription_task）=====

    async def _poll_task(
        self,
        client: httpx.AsyncClient,
        poll_url: str,
        *,
        headers: dict[str, str] | None = None,
        method: str = "GET",
        json_body: dict | None = None,
        extract_status: Callable[[dict], str] | None = None,
        extract_url: Callable[[dict], str] | None = None,
        interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_POLL_TIMEOUT,
    ) -> tuple[str, dict]:
        """通用轮询循环：循环查询直到终态或超时。

        Args:
            extract_status: 从响应 JSON 提取状态字符串的函数
            extract_url: 从响应 JSON 提取最终资产 url 的函数（终态成功时调用）
        Returns:
            (最终资产 url, 最后一次响应 JSON)
        Raises:
            RuntimeError: 超时或任务失败
        """
        deadline = time.time() + timeout
        last_data: dict = {}
        last_status = "PENDING"
        while time.time() < deadline:
            resp = await client.request(
                method, poll_url, headers=headers, json=json_body, timeout=30
            )
            resp.raise_for_status()
            last_data = resp.json()
            if extract_status:
                last_status = str(extract_status(last_data)).lower()
            if last_status in SUCCESS_STATES:
                url = extract_url(last_data) if extract_url else ""
                return url or "", last_data
            if last_status in FAILED_STATES:
                raise RuntimeError(
                    f"{self.name} 任务失败: status={last_status}, resp={last_data}"
                )
            await asyncio.sleep(interval)
        raise RuntimeError(
            f"{self.name} 轮询超时({timeout}s)，最后状态: {last_status}"
        )

    # ===== 资产下载（学自 MoneyPrinterTurbo material.save_video）=====

    def _download_asset(self, url: str, task_id: str, kind: str, ext: str = "mp4") -> str:
        """把远程资产下载到本地存储，返回本地路径。

        落地到 storage/tasks/{task_id}/{provider}_{kind}_{timestamp}.{ext}，
        避免之前 simulate:// 假字符串问题。
        """
        import os

        # STORAGE_DIR 空时兜底到项目根的 storage/ 目录
        storage_dir = settings.STORAGE_DIR or str(Path(__file__).resolve().parents[4] / "storage")
        storage_root = Path(storage_dir)
        task_dir = storage_root / "tasks" / (task_id or "default")
        task_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self.name}_{kind}_{int(time.time())}.{ext}"
        local_path = task_dir / filename
        # 同步下载（在 async 上下文里用 httpx sync 客户端，简单可靠）
        with httpx.Client(timeout=120) as dl_client:
            resp = dl_client.get(url)
            resp.raise_for_status()
            local_path.write_bytes(resp.content)
        if local_path.stat().st_size == 0:
            os.remove(local_path)
            raise RuntimeError(f"{self.name} 下载资产为空: {url}")
        return str(local_path)

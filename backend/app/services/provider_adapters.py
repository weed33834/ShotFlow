"""Provider 适配层：统一抽象本地 ComfyUI 与云端 API 视频生成 provider。

每个 adapter 实现 submit/poll/result 三段式，SIMULATE_MODE 开启时短路返回模拟结果，
保证无 GPU 的开发/测试环境可端到端跑通队列链路。

非 SIMULATE 路径：
  - ComfyUI 类 adapter（wan_i2v/hunyuan_video/ltx_video）复用 comfyui_service.submit_workflow/poll_result
  - 云端 API 类 adapter（cogvideox）抛 NotImplementedError 标记待接入（生产环境需补 API key 与工作流文件）
  - kling 包装现有 kling_service.run_kling_task
"""

import logging
import time
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)

# 任务上下文注册表：job_id -> {seed, shot_id, ...}
# SIMULATE 路径下供 result() 复现输出路径；非 SIMULATE 路径下 job_id 即 ComfyUI 真实 prompt_id
_JOB_CONTEXT: dict[str, dict] = {}


def _cleanup_job_context(job_id: str) -> None:
    """清理已完成任务的上下文，避免长跑 worker 内存泄漏。

    未知 job_id 静默忽略。在 result() 调用后由各 adapter 触发。
    """
    _JOB_CONTEXT.pop(job_id, None)


class ProviderAdapter(ABC):
    """Provider 适配器抽象基类。"""

    name: str  # provider 标识
    mode: str  # "comfyui" | "cloud_api" | "simulate"

    @abstractmethod
    def submit(self, task_type: str, prompt: str, seed: int, extra: dict) -> str:
        """提交生成任务，返回 job_id。"""

    @abstractmethod
    def poll(self, job_id: str) -> str:
        """轮询任务状态，返回 'running' | 'completed' | 'failed'。"""

    @abstractmethod
    def result(self, job_id: str) -> dict:
        """获取结果，返回 {status, output_path, ...}。"""


class _ComfyUIBaseAdapter(ProviderAdapter):
    """本地 ComfyUI 适配器基类。

    SIMULATE_MODE 短路返回模拟结果；非 SIMULATE 复用 comfyui_service.submit_workflow/poll_result。
    子类只需指定 name 与 sim_prefix；生产环境需在 comfyui_service.WORKFLOW_FILES 补对应工作流文件。
    """

    mode = "comfyui"
    name = ""
    sim_prefix = ""  # SIMULATE 模式下 job_id 与输出路径前缀

    def submit(self, task_type: str, prompt: str, seed: int, extra: dict) -> str:
        if settings.SIMULATE_MODE:
            job_id = f"{self.sim_prefix}_{seed}"
            _JOB_CONTEXT[job_id] = {"seed": seed}
            logger.info("[模拟] %s 提交 %s seed=%s", self.name, task_type, seed)
            return job_id
        # 生产环境：复用 comfyui_service 提交工作流
        from app.services.comfyui_service import submit_workflow

        prompt_id = submit_workflow(task_type, prompt, seed, extra)
        _JOB_CONTEXT[prompt_id] = {"seed": seed}
        return prompt_id

    def poll(self, job_id: str) -> str:
        if settings.SIMULATE_MODE:
            return "completed"
        from app.services.comfyui_service import ComfyUIError, poll_result

        try:
            poll_result(job_id)
            return "completed"
        except ComfyUIError:
            return "failed"

    def result(self, job_id: str) -> dict:
        if settings.SIMULATE_MODE:
            ctx = _JOB_CONTEXT.get(job_id, {})
            seed = ctx.get("seed", 0)
            _cleanup_job_context(job_id)
            return {
                "prompt_id": job_id,
                "status": "completed",
                "output_path": f"01_Assets/Scenes/{self.sim_prefix}_{seed}.mp4",
            }
        from app.services.comfyui_service import poll_result

        history = poll_result(job_id)
        output_path = ""
        outputs = history.get("outputs", {})
        for node_out in outputs.values():
            images = node_out.get("images") or node_out.get("gifs") or []
            if images:
                output_path = f"output/{images[0].get('filename', '')}"
                break
        _cleanup_job_context(job_id)
        return {"prompt_id": job_id, "status": "completed", "output_path": output_path}


class ComfyUIAdapter(_ComfyUIBaseAdapter):
    """wan_i2v 本地 ComfyUI 适配器（默认 provider，Wan2.2 I2V 14B 双专家）。"""

    name = "wan_i2v"
    sim_prefix = "sim_wan_i2v"


class HunyuanVideoAdapter(_ComfyUIBaseAdapter):
    """HunyuanVideo 本地 ComfyUI 适配器：高质量、慢。

    生产环境需在 comfyui_service.WORKFLOW_FILES 补 hunyuan 工作流文件映射。
    """

    name = "hunyuan_video"
    sim_prefix = "sim_hunyuan"


class LTXVideoAdapter(_ComfyUIBaseAdapter):
    """LTX-Video 本地 ComfyUI 适配器：轻量快速。"""

    name = "ltx_video"
    sim_prefix = "sim_ltx"


class CogVideoXAdapter(ProviderAdapter):
    """CogVideoX 云端 API 适配器：无需本地 GPU。

    生产环境需配置 API key 并实现真实 submit/poll/result 网络调用。
    """

    name = "cogvideox"
    mode = "cloud_api"
    sim_prefix = "sim_cogvideox"

    def submit(self, task_type: str, prompt: str, seed: int, extra: dict) -> str:
        if settings.SIMULATE_MODE:
            job_id = f"{self.sim_prefix}_{seed}"
            _JOB_CONTEXT[job_id] = {"seed": seed}
            logger.info("[模拟] %s 提交 %s seed=%s", self.name, task_type, seed)
            return job_id
        raise NotImplementedError("CogVideoX 云端 API 接入待实现，需配置 API key")

    def poll(self, job_id: str) -> str:
        if settings.SIMULATE_MODE:
            return "completed"
        raise NotImplementedError("CogVideoX 云端 API 接入待实现，需配置 API key")

    def result(self, job_id: str) -> dict:
        if settings.SIMULATE_MODE:
            ctx = _JOB_CONTEXT.get(job_id, {})
            seed = ctx.get("seed", 0)
            _cleanup_job_context(job_id)
            return {
                "job_id": job_id,
                "status": "completed",
                "output_path": f"01_Assets/Scenes/{self.sim_prefix}_{seed}.mp4",
            }
        raise NotImplementedError("CogVideoX 云端 API 接入待实现，需配置 API key")


class KlingAdapter(ProviderAdapter):
    """可灵云端 API 适配器：包装 kling_service.run_kling_task。

    注：当前 _dispatch 的 kling 分支仍直接调用 run_kling_task（保持向后兼容），
    此 adapter 主要用于统一注册表与未来路由收敛。
    """

    name = "kling"
    mode = "cloud_api"
    sim_prefix = "sim_kling"

    def submit(self, task_type: str, prompt: str, seed: int, extra: dict) -> str:
        shot_id = extra.get("shot_id", "")
        if settings.SIMULATE_MODE:
            job_id = f"{self.sim_prefix}_{shot_id}_{seed}"
            _JOB_CONTEXT[job_id] = {"shot_id": shot_id}
            logger.info("[模拟] %s 提交 shot=%s", self.name, shot_id)
            return job_id
        # 非 SIMULATE：kling_service 一次性同步执行，用合成 job_id 关联结果
        from app.services.kling_service import run_kling_task

        result = run_kling_task(
            shot_id=shot_id,
            prompt=prompt,
            start_image=extra.get("start_image"),
            end_image=extra.get("end_image"),
        )
        job_id = f"kling_{shot_id}_{int(time.time())}"
        _JOB_CONTEXT[job_id] = {"result": result}
        return job_id

    def poll(self, job_id: str) -> str:
        if settings.SIMULATE_MODE:
            return "completed"
        ctx = _JOB_CONTEXT.get(job_id, {})
        result = ctx.get("result", {})
        return "completed" if result.get("success") else "failed"

    def result(self, job_id: str) -> dict:
        if settings.SIMULATE_MODE:
            ctx = _JOB_CONTEXT.get(job_id, {})
            shot_id = ctx.get("shot_id", "")
            _cleanup_job_context(job_id)
            return {
                "job_id": job_id,
                "status": "completed",
                "output_path": f"05_Output/Rough_Cuts/{self.sim_prefix}_{shot_id}.mp4",
            }
        result = _JOB_CONTEXT.get(job_id, {}).get("result", {"status": "failed"})
        _cleanup_job_context(job_id)
        return result


# Provider 注册表（工厂）
_PROVIDER_REGISTRY: dict[str, ProviderAdapter] = {}


def register_adapter(adapter: ProviderAdapter) -> None:
    """注册 adapter。"""
    _PROVIDER_REGISTRY[adapter.name] = adapter


def get_adapter(provider_name: str) -> ProviderAdapter:
    """按名取 adapter，不存在抛 ValueError。

    调用方在 extra.provider 缺失时应默认传 "wan_i2v"。
    """
    if provider_name not in _PROVIDER_REGISTRY:
        raise ValueError(f"未知 provider: {provider_name}")
    return _PROVIDER_REGISTRY[provider_name]


def available_providers() -> list[str]:
    """返回所有已注册 provider 名。"""
    return list(_PROVIDER_REGISTRY.keys())


# 模块加载时注册全部 adapter（wan_i2v + hunyuan_video + ltx_video + cogvideox + kling）
register_adapter(ComfyUIAdapter())
register_adapter(HunyuanVideoAdapter())
register_adapter(LTXVideoAdapter())
register_adapter(CogVideoXAdapter())
register_adapter(KlingAdapter())

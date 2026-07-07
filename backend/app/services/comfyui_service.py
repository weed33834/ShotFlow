"""ComfyUI 生成服务 — 封装工作流提交与轮询。

逻辑提取自 08_Automation/render_queue.py 的 run_comfyui_task（第 179-230 行），
改为可被 Celery 任务调用的函数形式，并支持模拟模式。

不改动原脚本；此处为独立实现，便于单元测试与错误处理。
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

# 仓库根目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_DIR = PROJECT_ROOT / "03_Workflows" / "api"

# task_type -> 工作流文件名映射
WORKFLOW_FILES = {
    "keyframe": "Flux_Character_Consistency_api.json",
    "video_i2v": "Wan22_Dual_Expert_Video_api.json",
    "video_t2v": "Wan22_Dual_Expert_Video_api.json",
}


class ComfyUIError(Exception):
    """ComfyUI 调用异常。"""


def _load_workflow(task_type: str) -> dict:
    """加载工作流 API JSON。"""
    filename = WORKFLOW_FILES.get(task_type)
    if not filename:
        raise ComfyUIError(f"不支持的任务类型: {task_type}")
    path = WORKFLOW_DIR / filename
    if not path.exists():
        raise ComfyUIError(f"工作流文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _inject_params(workflow: dict, prompt: str, seed: int, extra: dict) -> dict:
    """向工作流注入提示词与 seed（对应 render_queue.py 第 194-204 行）。"""
    import copy

    wf = copy.deepcopy(workflow)
    for node_data in wf.values():
        if node_data.get("class_type") == "CLIPTextEncode":
            node_data["inputs"]["text"] = prompt
            break
    for node_data in wf.values():
        if node_data.get("class_type") in ("KSampler", "KSamplerAdvanced"):
            node_data["inputs"]["seed"] = seed
    return wf


def build_workflow(task_type: str, prompt: str, seed: int, extra: dict) -> dict:
    """构建可提交的 ComfyUI 工作流：优先用 YAML 参数化注入，无配置则回退硬编码注入。

    YAML 驱动路径：从 03_Workflows/workflows.yaml 取该 task_type 的参数定义，将
    prompt/seed/extra 合并后按 node_class + node_input 注入对应节点。这样非程序员
    改 YAML 即可调整生成参数（steps/cfg/frames/fps/负向提示词等），无需改 Python 代码。
    注入前先调 validate_params 做必填/类型/范围校验，非法参数直接抛错，避免把
    坏参数送到 ComfyUI 浪费 GPU 后才失败。

    回退路径：task_type 无 YAML 配置时，用 _inject_params 仅注入 prompt + seed
    （保持向后兼容）。

    Args:
        task_type: keyframe / video_i2v / video_t2v
        prompt: 正向提示词
        seed: 采样种子
        extra: 附加参数（与 prompt/seed 合并后按 YAML 定义选择性注入）

    Returns:
        可直接提交给 ComfyUI /prompt 接口的完整工作流字典

    Raises:
        ValueError: 参数校验失败（必填缺失/类型不符/超范围）。抛 ValueError 而非
            ComfyUIError，使其被 queue_service.classify_error 归为 invalid_prompt
            （不可重试），避免对永久性参数错误无谓重试浪费 GPU。
    """
    from app.services.workflow_config_service import (
        get_workflow_by_task_type,
        inject_params,
        validate_params,
    )

    wf_config = get_workflow_by_task_type(task_type)
    if wf_config:
        params = {"prompt": prompt, "seed": seed, **(extra or {})}
        errors = validate_params(wf_config, params)
        if errors:
            # 抛 ValueError 让 classify_error 归为 invalid_prompt（不可重试），
            # 避免对永久性参数错误无谓重试浪费 GPU。
            raise ValueError(f"参数校验失败: {', '.join(errors)}")
        return inject_params(wf_config, params)
    # 回退：无 YAML 配置时仅注入 prompt + seed
    workflow = _load_workflow(task_type)
    return _inject_params(workflow, prompt, seed, extra)


def submit_workflow(task_type: str, prompt: str, seed: int, extra: dict) -> str:
    """提交工作流到 ComfyUI，返回 prompt_id。

    Args:
        task_type: keyframe / video_i2v / video_t2v
        prompt: 正向提示词
        seed: 采样种子
        extra: 附加参数（预留扩展）

    Returns:
        ComfyUI 返回的 prompt_id
    """
    workflow = build_workflow(task_type, prompt, seed, extra)
    payload = {"prompt": workflow}
    resp = requests.post(f"{settings.COMFYUI_URL}/prompt", json=payload, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json().get("prompt_id")
    if not prompt_id:
        raise ComfyUIError("ComfyUI 未返回 prompt_id")
    logger.info("已提交 ComfyUI 任务 prompt_id=%s", prompt_id)
    return prompt_id


def poll_result(prompt_id: str, timeout_seconds: int = 1800, interval: int = 5) -> dict:
    """轮询 ComfyUI 历史接口直到任务完成或超时。

    对应 render_queue.py 第 213-230 行的轮询逻辑。

    Args:
        prompt_id: submit_workflow 返回的 id
        timeout_seconds: 最大等待秒数（默认 30 分钟）
        interval: 轮询间隔秒数

    Returns:
        ComfyUI history 中该 prompt_id 的完整状态字典

    Raises:
        ComfyUIError: 生成失败或超时
    """
    deadline = time.time() + timeout_seconds
    url = f"{settings.COMFYUI_URL}/history/{prompt_id}"
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            history = resp.json()
            if prompt_id in history:
                status = history[prompt_id].get("status", {})
                if status.get("completed"):
                    return history[prompt_id]
                if status.get("status_str") == "error":
                    raise ComfyUIError(f"ComfyUI 生成失败: {status}")
        except requests.RequestException as e:
            logger.warning("轮询 ComfyUI 异常，将重试: %s", e)
        time.sleep(interval)
    raise ComfyUIError(f"ComfyUI 生成超时 prompt_id={prompt_id}")


def run_comfyui_task(
    task_type: str, prompt: str, seed: int | None = None, extra: Optional[dict] = None
) -> dict:
    """端到端执行一个 ComfyUI 任务（提交 + 轮询）。

    模拟模式下直接返回模拟结果，不调用 ComfyUI。

    Returns:
        包含 prompt_id / status / output_path 的字典
    """
    extra = extra or {}
    if settings.SIMULATE_MODE:
        logger.info("[模拟] ComfyUI 任务 %s prompt=%s...", task_type, prompt[:40])
        return {
            "prompt_id": f"sim_{int(time.time())}",
            "status": "completed",
            "output_path": f"01_Assets/Scenes/sim_{task_type}_{seed}.png",
        }

    seed = seed if seed is not None else int(time.time()) % 100000
    prompt_id = submit_workflow(task_type, prompt, seed, extra)
    result = poll_result(prompt_id)
    # 输出路径解析：从 history 中提取（ComfyUI 结构较复杂，这里取第一个输出文件）
    output_path = ""
    outputs = result.get("outputs", {})
    for node_out in outputs.values():
        images = node_out.get("images") or node_out.get("gifs") or []
        if images:
            output_path = f"output/{images[0].get('filename', '')}"
            break
    return {"prompt_id": prompt_id, "status": "completed", "output_path": output_path}

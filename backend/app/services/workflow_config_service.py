"""ComfyUI 工作流 YAML 参数化加载器。

从 03_Workflows/workflows.yaml 加载工作流参数定义，支持：
  - 按 name / task_type 查询
  - 参数注入到工作流 JSON（按 node_class + node_input 定位节点）
  - 参数校验（类型、范围、必填）

非程序员通过编辑 YAML 即可调整生成参数，无需改 Python 代码。
"""

import copy
import json
import logging
from typing import Any, Optional

import yaml
from app.core.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

YAML_PATH = PROJECT_ROOT / "03_Workflows" / "workflows.yaml"

# 参数类型 -> Python 类型
_TYPE_MAP = {
    "text": str,
    "integer": int,
    "float": (int, float),
    "boolean": bool,
}


class WorkflowConfigError(Exception):
    """工作流配置异常。"""


# 模块级缓存：避免热路径每次请求都读盘解析 YAML。
# 缓存按 mtime 失效——YAML 文件被修改后下次调用自动重载。
_yaml_cache: tuple[float, list[dict]] = (0.0, [])


def _load_yaml() -> list[dict]:
    """加载 YAML 配置，返回工作流列表（带 mtime 缓存）。"""
    global _yaml_cache
    try:
        mtime = YAML_PATH.stat().st_mtime if YAML_PATH.exists() else 0.0
    except OSError:
        mtime = 0.0
    if mtime == _yaml_cache[0]:
        return _yaml_cache[1]
    if not YAML_PATH.exists():
        logger.warning("工作流配置不存在: %s", YAML_PATH)
        _yaml_cache = (0.0, [])
        return []
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    workflows = data.get("workflows", [])
    _yaml_cache = (mtime, workflows)
    return workflows


def list_workflows() -> list[dict]:
    """列出所有工作流配置。"""
    return _load_yaml()


def get_workflow(name: str) -> Optional[dict]:
    """按名称获取工作流配置。"""
    for wf in _load_yaml():
        if wf.get("name") == name:
            return wf
    return None


def get_workflow_by_task_type(task_type: str) -> Optional[dict]:
    """按任务类型获取工作流配置。"""
    for wf in _load_yaml():
        if wf.get("task_type") == task_type:
            return wf
    return None


def validate_params(workflow: dict, params: dict) -> list[str]:
    """校验参数，返回错误信息列表（空列表表示通过）。

    校验项：
      - required 参数必须存在
      - 类型匹配
      - min/max 范围
    """
    errors: list[str] = []
    for spec in workflow.get("parameters", []):
        key = spec["key"]
        val = params.get(key)
        if val is None or val == "":
            if spec.get("required"):
                errors.append(f"参数 {key} 必填")
            continue
        expected_type = _TYPE_MAP.get(spec.get("type"), str)
        if not isinstance(val, expected_type):
            errors.append(f"参数 {key} 类型应为 {spec.get('type')}")
            continue
        if "min" in spec and isinstance(val, (int, float)) and val < spec["min"]:
            errors.append(f"参数 {key} 不能小于 {spec['min']}")
        if "max" in spec and isinstance(val, (int, float)) and val > spec["max"]:
            errors.append(f"参数 {key} 不能大于 {spec['max']}")
    return errors


def inject_params(workflow: dict, params: dict) -> dict:
    """将参数注入工作流 JSON，返回新的工作流字典。

    按 node_class + node_input 定位节点并赋值。
    node_index 用于区分同 class 的多个节点（如正向/负向 CLIPTextEncode）。
    """
    file_path = PROJECT_ROOT / workflow["file_path"]
    if not file_path.exists():
        raise WorkflowConfigError(f"工作流文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        wf_json = json.load(f)

    wf = copy.deepcopy(wf_json)
    for spec in workflow.get("parameters", []):
        key = spec["key"]
        if key not in params:
            continue
        target_class = spec.get("node_class")
        target_input = spec.get("node_input")
        target_index = spec.get("node_index", 0)
        if not target_class or not target_input:
            continue
        matched = 0
        for node_data in wf.values():
            if not isinstance(node_data, dict):
                continue
            if node_data.get("class_type") == target_class:
                if matched == target_index:
                    inputs = node_data.setdefault("inputs", {})
                    inputs[target_input] = params[key]
                    break
                matched += 1
    return wf


def get_default_params(workflow: dict) -> dict[str, Any]:
    """获取工作流所有参数的默认值。"""
    defaults = {}
    for spec in workflow.get("parameters", []):
        if "default" in spec:
            defaults[spec["key"]] = spec["default"]
    return defaults

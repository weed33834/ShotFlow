"""ShortGPT 编辑步骤 JSON 模板加载。

移植自 ShortGPT editing_framework/editing_steps/，每个 JSON 文件描述一个
编辑步骤的图层结构（type/z/inputs/parameters/actions），供渲染管线按名称加载
并填充参数后执行。

模板中 font 路径引用 "fonts/xxx.ttf"，实际解析时从 app/fonts/ 目录定位。
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent
_FONT_DIR = _TEMPLATE_DIR.parent / "fonts"


def list_templates() -> list[str]:
    """返回所有可用模板名称（不含 .json 后缀）。"""
    return sorted(p.stem for p in _TEMPLATE_DIR.glob("*.json"))


def load_template(name: str) -> dict[str, Any]:
    """按名称加载编辑步骤 JSON 模板，返回解析后的字典。

    name 可含或不含 .json 后缀。找不到时抛 FileNotFoundError。
    """
    stem = name.removesuffix(".json")
    path = _TEMPLATE_DIR / f"{stem}.json"
    if not path.exists():
        raise FileNotFoundError(f"编辑步骤模板不存在: {name}（查找路径: {path}）")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_font_path(font_ref: str) -> str:
    """把模板中的 "fonts/xxx.ttf" 引用解析为 app/fonts/ 下的绝对路径。

    ShortGPT 模板用相对路径引用字体，这里统一转为绝对路径，
    避免 CWD 不同时找不到字体文件。
    """
    if not font_ref:
        return ""
    p = Path(font_ref)
    # 已经是绝对路径且存在
    if p.is_absolute() and p.exists():
        return str(p)
    # 取文件名在 app/fonts/ 下查找
    candidate = _FONT_DIR / p.name
    if candidate.exists():
        return str(candidate)
    # 回退：原样返回（调用方自行处理）
    return font_ref

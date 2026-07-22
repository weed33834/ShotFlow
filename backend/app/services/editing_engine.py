"""ShortGPT 式编辑引擎 — 消费 editing_steps JSON 模板，翻译为 ffmpeg 滤镜操作。

每个 JSON 模板描述一个编辑图层（caption/watermark/background_music 等），
包含 type（text/audio/video）、z（层级）、parameters（默认值）、actions（操作列表）。
本引擎把模板参数填充后翻译为 ffmpeg -filter_complex 参数，应用到输入视频上。

与 ffmpeg_service 的关系：
- ffmpeg_service 负责"拼接 + 混音 + 字幕"的主合成管线
- editing_engine 负责"后处理增强"：加水印、加字幕特效、调音量等
- 编排器 S5 组装后可选调用 editing_engine 做后处理
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.editing_steps import load_template, resolve_font_path, list_templates
from app.services.ffmpeg_service import _resolve_ffmpeg_binary, _run_ffmpeg, _find_font

logger = logging.getLogger(__name__)

# 支持 apply 的 action 类型 → 处理函数映射
# 不支持的 action 静默跳过（保证健壮性）
_SUPPORTED_ACTIONS = {
    "set_time_start",
    "set_time_end",
    "screen_position",
    "loop_background_music",
    "normalize_audio",
    "volume_percentage",
}


def apply_editing_step(
    input_path: str,
    step_name: str,
    params: dict[str, Any] | None = None,
    output_path: str = "",
) -> str:
    """对视频应用单个编辑步骤（JSON 模板驱动），返回输出文件路径。

    Args:
        input_path: 输入视频路径
        step_name: editing_steps 模板名（如 make_caption, show_watermark）
        params: 模板参数（覆盖默认值），如 {"text": "Hello", "url": "/path/to/music.mp3"}
        output_path: 输出路径（空则自动生成）
    Returns:
        输出文件路径
    """
    template = load_template(step_name)
    params = params or {}

    # 模板顶层 key 就是步骤名（如 "caption"、"background_music"）
    step_key = next(iter(template))
    step_def = template[step_key]

    # 合并参数：模板默认值 < 用户传入参数
    merged = dict(step_def.get("parameters", {}))
    merged.update(params)
    # 解析字体路径
    if "font" in merged:
        merged["font"] = resolve_font_path(merged["font"])

    step_type = step_def.get("type", "")
    actions = step_def.get("actions", [])

    if not output_path:
        out_dir = Path(settings.STORAGE_DIR) / "edited"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"edit_{step_name}_{Path(input_path).stem}.mp4")

    if step_type == "text":
        return _apply_text_layer(input_path, step_def, merged, actions, output_path)
    elif step_type == "audio":
        return _apply_audio_layer(input_path, step_def, merged, actions, output_path)
    elif step_type == "video":
        return _apply_video_layer(input_path, step_def, merged, actions, output_path)
    else:
        logger.warning("未知编辑步骤类型: %s，跳过", step_type)
        return input_path


def apply_editing_steps(
    input_path: str,
    steps: list[dict[str, Any]],
) -> str:
    """按顺序对视频应用多个编辑步骤。

    Args:
        input_path: 输入视频路径
        steps: [{"name": "make_caption", "params": {...}}, ...]
    Returns:
        最终输出文件路径
    """
    current = input_path
    for step in steps:
        name = step.get("name", "")
        params = step.get("params", {})
        if not name:
            continue
        try:
            current = apply_editing_step(current, name, params)
        except Exception as exc:
            logger.warning("编辑步骤 %s 失败，跳过: %s", name, exc)
    return current


def _apply_text_layer(
    input_path: str,
    step_def: dict,
    params: dict,
    actions: list,
    output_path: str,
) -> str:
    """应用文本图层（字幕/水印）— 翻译为 drawtext 滤镜。"""
    text = params.get("text", "")
    if not text:
        logger.warning("文本图层无 text 参数，跳过")
        return input_path

    fontfile = params.get("font", "")
    if not fontfile:
        fontfile = _find_font()

    font_size = params.get("font_size", 48)
    color = params.get("color", "white")
    stroke_width = params.get("stroke_width", 2)
    stroke_color = params.get("stroke_color", "black")

    # 解析 screen_position action 得到位置
    x_expr = "(w-text_w)/2"
    y_expr = "(h-text_h)/2"
    for action in actions:
        if action.get("type") == "screen_position":
            pos = action.get("param", {}).get("pos", "center")
            x_expr, y_expr = _resolve_position(pos)

    # 时间范围（set_time_start / set_time_end）
    enable_expr = ""
    for action in actions:
        if action.get("type") == "set_time_start":
            t = action.get("param")
            if t is not None:
                enable_expr = f"gte(t,{t})"
        if action.get("type") == "set_time_end":
            t = action.get("param")
            if t is not None:
                if enable_expr:
                    enable_expr += f"*lte(t,{t})"
                else:
                    enable_expr = f"lte(t,{t})"

    # 写入临时文件避免 text= 转义问题
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        text_file = f.name

    font_part = f"fontfile='{fontfile}':" if fontfile else ""
    escaped_text_file = text_file.replace("\\", "\\\\").replace(":", "\\:")
    drawtext = (
        f"drawtext={font_part}textfile='{escaped_text_file}':"
        f"fontcolor={color}:fontsize={font_size}:"
        f"borderw={stroke_width}:bordercolor={stroke_color}:"
        f"x={x_expr}:y={y_expr}"
    )
    if enable_expr:
        drawtext += f":enable='{enable_expr}'"

    _run_ffmpeg([
        "-i", input_path,
        "-vf", drawtext,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-y", output_path,
    ], desc=f"编辑步骤 text: {step_def.get('caption', step_def)}")

    # 清理临时文件
    Path(text_file).unlink(missing_ok=True)
    return output_path


def _apply_audio_layer(
    input_path: str,
    step_def: dict,
    params: dict,
    actions: list,
    output_path: str,
) -> str:
    """应用音频图层（背景音乐）— 翻译为 amix 滤镜。"""
    bgm_url = params.get("url", "")
    if not bgm_url or not Path(bgm_url).exists():
        logger.warning("音频图层无有效 url，跳过")
        return input_path

    volume_pct = params.get("volume_percentage", 30)
    # 音量百分比转 0-1 比例
    volume_ratio = volume_pct / 100.0 if isinstance(volume_pct, (int, float)) else 0.3

    # amix 混音：原音频 + BGM，normalize=0 防音量稀释
    _run_ffmpeg([
        "-i", input_path,
        "-i", bgm_url,
        "-filter_complex",
        f"[1:a]volume={volume_ratio}[bgm];[0:a][bgm]amix=inputs=2:duration=first:normalize=0[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-y", output_path,
    ], desc="编辑步骤 audio: background_music")
    return output_path


def _apply_video_layer(
    input_path: str,
    step_def: dict,
    params: dict,
    actions: list,
    output_path: str,
) -> str:
    """应用视频图层（叠加视频/动画）— 翻译为 overlay 滤镜。"""
    overlay_url = params.get("url", "")
    if not overlay_url or not Path(overlay_url).exists():
        logger.warning("视频图层无有效 url，跳过")
        return input_path

    # 简单 overlay：叠加视频到主视频右下角
    _run_ffmpeg([
        "-i", input_path,
        "-i", overlay_url,
        "-filter_complex",
        "[0:v][1:v]overlay=W-w-20:H-h-20[vout]",
        "-map", "[vout]",
        "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-y", output_path,
    ], desc="编辑步骤 video: overlay")
    return output_path


def _resolve_position(pos) -> tuple[str, str]:
    """把 screen_position 的 pos 参数翻译为 drawtext 的 x/y 表达式。

    pos 可以是字符串（"center"/"top"/"bottom"）或列表（["center", 0.7]）。
    """
    if isinstance(pos, str):
        positions = {
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "top": ("(w-text_w)/2", "40"),
            "bottom": ("(w-text_w)/2", "h-text_h-40"),
            "top_left": ("40", "40"),
            "top_right": ("w-text_w-40", "40"),
            "bottom_left": ("40", "h-text_h-40"),
            "bottom_right": ("w-text_w-40", "h-text_h-40"),
        }
        return positions.get(pos, positions["center"])
    if isinstance(pos, list) and len(pos) >= 2:
        x_map = {"center": "(w-text_w)/2", "left": "40", "right": "w-text_w-40"}
        y_val = pos[1]
        # 如果 y 是 0-1 的浮点数，按比例定位
        if isinstance(y_val, (int, float)) and 0 <= y_val <= 1:
            y_expr = f"h*{y_val}-text_h/2"
        else:
            y_expr = str(y_val)
        x_expr = x_map.get(str(pos[0]), "(w-text_w)/2")
        return (x_expr, y_expr)
    return ("(w-text_w)/2", "(h-text_h)/2")


def get_available_steps() -> list[dict[str, Any]]:
    """返回所有可用编辑步骤及其参数定义，供前端/智能体查询。"""
    result = []
    for name in list_templates():
        try:
            template = load_template(name)
            step_key = next(iter(template))
            step_def = template[step_key]
            result.append({
                "name": name,
                "type": step_def.get("type", ""),
                "z": step_def.get("z", 0),
                "parameters": step_def.get("parameters", {}),
                "actions": [a.get("type", "") for a in step_def.get("actions", [])],
            })
        except Exception:
            continue
    return result

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键帧批量生成脚本 — 通过 ComfyUI API 批量提交提示词
ShotFlow

用法:
    1. 启动 ComfyUI: cd ~/ComfyUI && python main.py --listen
    2. 运行本脚本: python batch_keyframe_gen.py

注意:
    - 需要先在 ComfyUI 中加载 Flux_Character_Consistency.json 并保存为 API 格式
    - 将 API 格式 JSON 放到 03_Workflows/api/ 目录下
    - 本脚本读取提示词汇总表，逐条提交到 ComfyUI API
"""

import argparse
import copy
import json
import os
import time
from pathlib import Path

import requests

from common import PROJECT_ROOT

# ==================== 配置区 ====================

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

# 工作流 API 格式 JSON 路径（需在 ComfyUI 中保存为 API 格式）
WORKFLOW_API_JSON = PROJECT_ROOT / "03_Workflows" / "api" / "Flux_Character_Consistency_api.json"

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "01_Assets" / "Scenes"

# 艾娃角色锚点
AVA_ANCHOR = (
    "Ava, 28-year-old woman, short dark hair, amber eyes, light scar under right eye, "
    "cybernetic neural interface glowing on back of neck, dark gray patched windbreaker "
    "(right shoulder patch), black turtleneck, dark cargo pants, scuffed military boots, "
    "glowing orange bracelet on left wrist, weathered data terminal at waist"
)

# 负面提示词
NEGATIVE_PROMPT = (
    "bad anatomy, deformed face, extra limbs, extra fingers, blurry, low quality, "
    "inconsistent character, different person, mutated hands, watermark, text, "
    "plastic skin, oversaturated, cartoon, anime"
)

# 氛围词
ATMOSPHERE = (
    "cinematic sci-fi lighting, film grain, teal and orange color grade, "
    "dust particles in air, volumetric light, depth of field, 8K, highly detailed"
)

# ==================== 关键帧列表 ====================

KEYFRAMES = [
    {
        "id": "S01_01",
        "scene": "废墟大全景",
        "prompt": f"Vast ruined futuristic city at dawn, collapsed highway bridges, overturned vehicles half-buried in sand, crumbling skyscrapers covered in vines and rust, thick clouds with golden light beams piercing through, {ATMOSPHERE}",
        "has_ava": False,
    },
    {
        "id": "S01_02",
        "scene": "艾娃走出废墟",
        "prompt": f"{AVA_ANCHOR}, walking slowly out from behind massive concrete debris, left hand reaching toward data terminal at waist, cautious expression, looking around, ruined city background, morning light, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S01_03",
        "scene": "艾娃眼部特写",
        "prompt": f"Extreme close-up of Ava's eyes, amber pupils contracting, expression shifting from confusion to alertness, breath forming white mist in cold air, short dark hair framing face, light scar under right eye visible, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S01_04_start",
        "scene": "艾娃走向飞船-起始",
        "prompt": f"{AVA_ANCHOR}, walking away from camera toward distant crashed spaceship, ruined city landscape, morning light, wide shot from behind, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S01_04_end",
        "scene": "艾娃走向飞船-结束",
        "prompt": f"{AVA_ANCHOR}, standing at side angle near crashed spaceship hull, looking up at massive rusted spacecraft, ruined city background, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S02_01",
        "scene": "艾娃仰望飞船",
        "prompt": f"{AVA_ANCHOR}, standing before massive crashed spaceship, looking up, ship hull covered in rust and vines, neural interface on neck beginning to glow faint orange, low angle shot, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S02_02",
        "scene": "颈后接口特写",
        "prompt": f"Extreme close-up of back of Ava's neck, cybernetic neural interface, orange-red light pulsing beneath skin like heartbeat, short dark hair pushed aside, skin texture detail, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S02_03",
        "scene": "触碰飞船外壳",
        "prompt": f"{AVA_ANCHOR}, reaching hand to touch spaceship hull, fingertips grazing cold rusted metal, dust falling, medium close-up, handheld camera feel, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S02_04",
        "scene": "飞船面板亮起",
        "prompt": f"Close-up of damaged spaceship hull panel, cracked metal surface suddenly illuminating with faint orange glow, responding to touch, dust particles, {ATMOSPHERE}",
        "has_ava": False,
    },
    {
        "id": "S02_05_start",
        "scene": "舱门打开-起始",
        "prompt": f"{AVA_ANCHOR}, standing before closed spaceship hatch door, hesitation, dark corridor visible beyond, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S02_05_end",
        "scene": "舱门打开-结束",
        "prompt": f"{AVA_ANCHOR}, stepping into spaceship interior through open hatch, dark deep corridor ahead, faint orange light from within, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S03_01",
        "scene": "飞船内部走廊",
        "prompt": f"Long corridor inside crashed spaceship, broken screens and exposed cables on both sides, at the end a glowing spherical device floating in mid-air, cracked core with orange light pulsing, data streams on walls, {ATMOSPHERE}",
        "has_ava": False,
    },
    {
        "id": "S03_02",
        "scene": "艾娃沿走廊前行",
        "prompt": f"{AVA_ANCHOR}, walking down spaceship corridor toward glowing core, wrist bracelet and neck interface glowing brighter, illuminating tense side profile, broken screens around, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S03_03",
        "scene": "右手握拳特写",
        "prompt": f"Close-up of Ava's right hand, slightly trembling, clenching into fist, scuffed military jacket sleeve visible, orange glow from interface reflecting on skin, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S03_04_start",
        "scene": "艾娃站在核心前-起始",
        "prompt": f"{AVA_ANCHOR}, standing before massive cracked spherical core, orange light breathing inside, data streams flowing on walls, wide shot, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S03_04_end",
        "scene": "艾娃站在核心前-结束",
        "prompt": f"{AVA_ANCHOR}, standing closer to core, core light intensifying, data streams forming star map around her, wide shot from different angle, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S03_05",
        "scene": "艾娃震惊抬头",
        "prompt": f"{AVA_ANCHOR}, shocked expression, looking up searching for source of voice, medium close-up, orange core light on face, fear and curiosity in eyes, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S03_06",
        "scene": "核心光芒增强",
        "prompt": f"{AVA_ANCHOR}, face illuminated by intense orange light from core, eyes showing mix of fear and desire, slow push-in, cracked core in background glowing brighter, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S04_01",
        "scene": "记忆碎片蒙太奇",
        "prompt": f"Surreal montage of memory fragments: childhood room with warm light, blurred faces of parents, blinding surgical light, glittering city skyline before the silence, dreamlike superimposition, {ATMOSPHERE}",
        "has_ava": False,
    },
    {
        "id": "S04_02",
        "scene": "艾娃闭眼流泪",
        "prompt": f"{AVA_ANCHOR}, eyes tightly closed, single tear rolling down cheek, neural interface flashing intensely, orange light pulsing, extreme close-up, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S04_03_start",
        "scene": "艾娃跪在核心前-起始",
        "prompt": f"{AVA_ANCHOR}, kneeling before core, hands holding head, core light gently wrapping around her like embrace, medium shot, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S04_03_end",
        "scene": "艾娃跪在核心前-结束",
        "prompt": f"{AVA_ANCHOR}, kneeling, looking up at core with exhausted expression, core light softening, data streams calming, medium shot, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S05_01",
        "scene": "星图展开",
        "prompt": f"Vast space inside spaceship, data streams converging into giant star map, countless glowing points each representing dormant singularity node, {AVA_ANCHOR} small figure in center, epic scale, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S05_02",
        "scene": "艾娃站起悬手",
        "prompt": f"{AVA_ANCHOR}, slowly standing up, hand hovering above core surface without touching, tense expression, medium close-up, handheld, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S05_03",
        "scene": "悲伤微笑触碰核心",
        "prompt": f"{AVA_ANCHOR}, sad smile on face, hand gently placed on core surface, orange light rippling from contact point, close-up, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S05_04_start",
        "scene": "核心光芒扩散-起始",
        "prompt": f"{AVA_ANCHOR}, hand on core, core light shifting from orange to soft blue-white, wide shot, data streams expanding outward, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S05_04_end",
        "scene": "核心光芒扩散-结束",
        "prompt": f"Blue-white light spreading across entire ruined city, dormant machines awakening with low resonance, epic wide shot, {AVA_ANCHOR} silhouette in light, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S05_05",
        "scene": "艾娃走出飞船",
        "prompt": f"{AVA_ANCHOR}, walking out of spaceship, ruined city still desolate but clouds parting, single beam of sunlight falling on her, neck interface no longer glowing, peaceful expression, full shot, {ATMOSPHERE}",
        "has_ava": True,
    },
    {
        "id": "S05_06",
        "scene": "无人机上升大全景",
        "prompt": f"Aerial view rising slowly, tiny figure of woman walking through vast ruined city, morning light spreading across horizon, faint electronic resonance in wind, epic scale, {ATMOSPHERE}",
        "has_ava": False,
    },
]

# ==================== ComfyUI API 工具函数 ====================


def load_workflow_template() -> dict:
    """加载工作流 API 格式 JSON 模板。"""
    if not WORKFLOW_API_JSON.exists():
        raise FileNotFoundError(
            f"工作流 API JSON 未找到: {WORKFLOW_API_JSON}\n"
            "请在 ComfyUI 中加载工作流后，通过 Save (API Format) 保存。"
        )
    with open(WORKFLOW_API_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def submit_prompt(workflow: dict, prompt_text: str, negative_text: str, seed: int) -> str:
    """提交提示词到 ComfyUI，返回 prompt_id。"""
    # 查找正面/负面提示词节点
    prompt_node_ids = []
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "CLIPTextEncode":
            prompt_node_ids.append(node_id)

    # 假设第一个是正面，第二个是负面（根据工作流实际结构调整）
    if len(prompt_node_ids) >= 2:
        workflow[prompt_node_ids[0]]["inputs"]["text"] = prompt_text
        workflow[prompt_node_ids[1]]["inputs"]["text"] = negative_text
    elif len(prompt_node_ids) == 1:
        workflow[prompt_node_ids[0]]["inputs"]["text"] = prompt_text

    # 设置 seed
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") in ("KSampler", "KSamplerAdvanced"):
            node_data["inputs"]["seed"] = seed

    # 设置输出文件名前缀
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "SaveImage":
            node_data["inputs"]["filename_prefix"] = f"SF_{seed}"

    payload = {"prompt": workflow}
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    return result.get("prompt_id")


def check_status(prompt_id: str, interval: int = 5, max_retry: int = 120) -> bool:
    """轮询任务状态。"""
    url = f"{COMFYUI_URL}/history/{prompt_id}"
    for i in range(max_retry):
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        history = response.json()
        if prompt_id in history:
            status = history[prompt_id].get("status", {})
            if status.get("completed", False):
                return True
            if status.get("status_str") == "error":
                raise RuntimeError(f"生成失败: {status}")
        time.sleep(interval)
    raise TimeoutError("生成超时")


def download_result(prompt_id: str, output_dir: str, filename: str) -> None:
    """从 ComfyUI 下载生成的图片。"""
    url = f"{COMFYUI_URL}/history/{prompt_id}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    history = response.json()

    if prompt_id not in history:
        raise RuntimeError("未找到生成结果")

    outputs = history[prompt_id].get("outputs", {})
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for img in node_output["images"]:
                img_url = f"{COMFYUI_URL}/view?filename={img['filename']}&subfolder={img.get('subfolder', '')}&type={img.get('type', 'output')}"
                img_response = requests.get(img_url, timeout=60)
                img_response.raise_for_status()
                output_path = Path(output_dir) / filename
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                print(f"  [Downloaded] {output_path}")
                return

    raise RuntimeError("未找到图片输出")


# ==================== 主流程 ====================


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 关键帧批量生成（ComfyUI API）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印关键帧列表，不提交 ComfyUI",
    )
    parser.add_argument(
        "--comfyui-url",
        default=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"),
        help="ComfyUI 服务地址（默认 http://127.0.0.1:8188）",
    )
    args = parser.parse_args()

    global COMFYUI_URL
    COMFYUI_URL = args.comfyui_url

    print("=" * 60)
    print("  ShotFlow — 关键帧批量生成")
    print(f"  总计 {len(KEYFRAMES)} 张关键帧")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] 以下关键帧将被生成：")
        for kf in KEYFRAMES:
            print(f"  {kf['id']} — {kf['scene']}")
        print(f"\n[DRY RUN] 输出目录: {OUTPUT_DIR}")
        print("[DRY RUN] 不执行实际提交")
        return

    # 检查 ComfyUI 连接
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        response.raise_for_status()
        print("[OK] ComfyUI 连接正常")
    except Exception as e:
        print(f"[ERROR] 无法连接 ComfyUI ({COMFYUI_URL}): {e}")
        return

    # 加载工作流模板
    try:
        workflow_template = load_workflow_template()
        print("[OK] 工作流模板已加载")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 批量生成
    success_count = 0
    fail_count = 0

    for i, kf in enumerate(KEYFRAMES):
        print(f"\n[{i+1}/{len(KEYFRAMES)}] {kf['id']} — {kf['scene']}")

        seed = 1000 + i  # 固定 seed 便于复现

        try:
            # 深拷贝工作流模板
            workflow = copy.deepcopy(workflow_template)

            prompt_id = submit_prompt(workflow, kf["prompt"], NEGATIVE_PROMPT, seed)
            print(f"  [Submitted] prompt_id={prompt_id}")

            check_status(prompt_id)
            print("  [Completed]")

            filename = f"SF_{kf['id']}_v01.png"
            download_result(prompt_id, str(OUTPUT_DIR), filename)

            success_count += 1
        except Exception as e:
            print(f"  [FAILED] {e}")
            fail_count += 1

        # 间隔避免过载
        time.sleep(2)

    # 汇总
    print("\n" + "=" * 60)
    print("  批量生成完成")
    print(f"  成功: {success_count}/{len(KEYFRAMES)}")
    print(f"  失败: {fail_count}/{len(KEYFRAMES)}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

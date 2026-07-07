#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分镜到视频流水线脚本 — 通过 ComfyUI API 批量提交 Wan2.2 I2V 生成
ShotFlow

用法:
    1. 启动 ComfyUI: cd ~/ComfyUI && python main.py --listen
    2. 运行本脚本: python storyboard_to_video.py

功能:
    - 读取 01_Assets/Scenes/ 下的关键帧图片
    - 逐镜头提交到 Wan2.2 I2V 工作流
    - 自动下载生成的视频到 05_Output/Rough_Cuts/
    - 记录生成日志到 06_Research/video_gen_log.csv
"""

import argparse
import copy
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

from common import PROJECT_ROOT

# ==================== 配置区 ====================

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

# 工作流 API 格式 JSON 路径
WORKFLOW_API_JSON = PROJECT_ROOT / "03_Workflows" / "api" / "Wan22_Dual_Expert_Video_api.json"

# 输入输出目录
KEYFRAME_DIR = PROJECT_ROOT / "01_Assets" / "Scenes"
OUTPUT_DIR = PROJECT_ROOT / "05_Output" / "Rough_Cuts"
LOG_FILE = PROJECT_ROOT / "06_Research" / "video_gen_log.csv"

# ==================== 镜头列表 ====================

# 标准镜头（使用 Wan2.2 I2V）
WAN_SHOTS = [
    {
        "id": "S01_02",
        "keyframe": "SF_S01_02_v01.png",
        "duration": 5,
        "prompt": "Ava walking cautiously through ruined city, looking around, morning light, dust particles, subtle head movement, cinematic sci-fi",
    },
    {
        "id": "S01_03",
        "keyframe": "SF_S01_03_v01.png",
        "duration": 3,
        "prompt": "Extreme close-up of Ava's amber eyes, pupils contracting, expression shifting from confusion to alertness, breath mist, subtle movement",
    },
    {
        "id": "S02_01",
        "keyframe": "SF_S02_01_v01.png",
        "duration": 5,
        "prompt": "Ava standing before massive crashed spaceship, looking up slowly, neural interface beginning to glow, low angle, dust falling",
    },
    {
        "id": "S02_02",
        "keyframe": "SF_S02_02_v01.png",
        "duration": 3,
        "prompt": "Close-up of neck neural interface, orange light pulsing like heartbeat, subtle skin movement, glowing intensifying",
    },
    {
        "id": "S02_03",
        "keyframe": "SF_S02_03_v01.png",
        "duration": 4,
        "prompt": "Ava reaching hand to touch spaceship hull, fingertips grazing metal, dust falling, slow movement, handheld feel",
    },
    {
        "id": "S02_04",
        "keyframe": "SF_S02_04_v01.png",
        "duration": 5,
        "prompt": "Damaged spaceship panel illuminating with orange glow, light spreading across cracked metal surface, dust particles reacting",
    },
    {
        "id": "S03_01",
        "keyframe": "SF_S03_01_v01.png",
        "duration": 5,
        "prompt": "Slow forward push through spaceship corridor toward glowing core, broken screens flickering, data streams flowing on walls",
    },
    {
        "id": "S03_02",
        "keyframe": "SF_S03_02_v01.png",
        "duration": 4,
        "prompt": "Ava walking down corridor, bracelet and interface glowing brighter, tense side profile, slow steady pace",
    },
    {
        "id": "S03_03",
        "keyframe": "SF_S03_03_v01.png",
        "duration": 3,
        "prompt": "Close-up of right hand trembling then clenching into fist, orange glow reflecting on skin, subtle movement",
    },
    {
        "id": "S03_05",
        "keyframe": "SF_S03_05_v01.png",
        "duration": 4,
        "prompt": "Ava shocked expression, looking up searching, orange light on face, fear and curiosity, slight head movement",
    },
    {
        "id": "S03_06",
        "keyframe": "SF_S03_06_v01.png",
        "duration": 5,
        "prompt": "Ava face illuminated by intensifying orange light, slow push-in, core glowing brighter in background, eyes reflecting light",
    },
    {
        "id": "S04_01",
        "keyframe": "SF_S04_01_v01.png",
        "duration": 4,
        "prompt": "Surreal memory fragments flashing, childhood room, surgical light, city skyline, dreamlike superimposition, fast cuts",
    },
    {
        "id": "S04_02",
        "keyframe": "SF_S04_02_v01.png",
        "duration": 3,
        "prompt": "Ava eyes closed, tear rolling down cheek, neural interface flashing, orange light pulsing, subtle trembling",
    },
    {
        "id": "S05_01",
        "keyframe": "SF_S05_01_v01.png",
        "duration": 5,
        "prompt": "Data streams converging into giant star map, glowing points appearing, Ava small figure in center, epic slow reveal",
    },
    {
        "id": "S05_02",
        "keyframe": "SF_S05_02_v01.png",
        "duration": 4,
        "prompt": "Ava slowly standing up, hand hovering above core, tense expression, handheld, subtle body movement",
    },
    {
        "id": "S05_03",
        "keyframe": "SF_S05_03_v01.png",
        "duration": 5,
        "prompt": "Ava sad smile, hand gently placed on core, orange light rippling from contact, emotional moment",
    },
    {
        "id": "S05_05",
        "keyframe": "SF_S05_05_v01.png",
        "duration": 5,
        "prompt": "Ava walking out of spaceship, clouds parting, sunlight beam falling on her, peaceful expression, slow walk",
    },
]

# 纯场景镜头（使用 Wan2.2 T2V，无输入图）
T2V_SHOTS = [
    {
        "id": "S01_01",
        "keyframe": None,
        "duration": 5,
        "prompt": "Vast ruined futuristic city at dawn, collapsed bridges, crumbling skyscrapers, golden light beams through clouds, dust particles, epic aerial descent",
    },
    {
        "id": "S05_06",
        "keyframe": None,
        "duration": 5,
        "prompt": "Aerial view rising slowly, tiny figure walking through vast ruined city, morning light spreading, epic scale, faint electronic resonance",
    },
]

# 复杂镜头（使用可灵 API，不在此脚本处理，仅记录）
KLING_SHOTS = [
    "S01_04",
    "S02_05",
    "S03_04",
    "S04_03",
    "S05_04",
]

# ==================== 工具函数 ====================


def load_workflow_template() -> dict:
    """加载工作流 API 格式 JSON。"""
    if not WORKFLOW_API_JSON.exists():
        raise FileNotFoundError(
            f"工作流 API JSON 未找到: {WORKFLOW_API_JSON}\n"
            "请在 ComfyUI 中加载 Wan22 工作流后保存为 API 格式。"
        )
    with open(WORKFLOW_API_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_image(image_path: str) -> str:
    """上传图片到 ComfyUI，返回文件名。"""
    filename = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        files = {"image": (filename, f, "image/png")}
        response = requests.post(f"{COMFYUI_URL}/upload/image", files=files, timeout=60)
    response.raise_for_status()
    result = response.json()
    return result.get("name", filename)


def submit_i2v_prompt(
    workflow: dict, image_name: str, prompt_text: str, seed: int, frames: int
) -> str:
    """提交 I2V 生成任务。"""
    # 设置 LoadImage 节点
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "LoadImage":
            node_data["inputs"]["image"] = image_name

    # 设置提示词
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "CLIPTextEncode":
            node_data["inputs"]["text"] = prompt_text
            break  # 只改第一个（正面提示词）

    # 设置 seed 和帧数
    for node_id, node_data in workflow.items():
        cls = node_data.get("class_type", "")
        inputs = node_data["inputs"]
        # 设置 seed（仅采样器节点）
        if cls in ("KSampler", "KSamplerAdvanced", "WanVideoSampler"):
            inputs["seed"] = seed
        # 设置帧数（仅目标视频生成节点）
        if cls in ("KSampler", "KSamplerAdvanced", "WanVideoSampler"):
            if "length" in inputs:
                inputs["length"] = frames
        if cls in ("WanImageToVideo", "WanTextToVideo"):
            if "length" in inputs:
                inputs["length"] = frames
        # 仅对已知视频相关节点设置 frames，避免误改其他节点
        if cls in (
            "WanImageToVideo",
            "WanTextToVideo",
            "VideoCombine",
            "SaveAnimatedWEBP",
            "SaveVideo",
        ):
            if "frames" in inputs:
                inputs["frames"] = frames

    # 设置输出文件名
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") in ("VideoCombine", "SaveAnimatedWEBP", "SaveVideo"):
            if "filename_prefix" in node_data["inputs"]:
                node_data["inputs"]["filename_prefix"] = f"SF_Shot_{seed}"

    payload = {"prompt": workflow}
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
    response.raise_for_status()
    return response.json().get("prompt_id")


def submit_t2v_prompt(workflow: dict, prompt_text: str, seed: int, frames: int) -> str:
    """提交 T2V 生成任务（无输入图）。"""
    # 禁用 LoadImage 节点：标记 _meta 为禁用或移除输入，避免 T2V 误用图片
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "LoadImage":
            # 安全做法：禁用该节点
            node_data["inputs"]["image"] = ""

    # 设置提示词
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "CLIPTextEncode":
            node_data["inputs"]["text"] = prompt_text
            break

    for node_id, node_data in workflow.items():
        cls = node_data.get("class_type", "")
        inputs = node_data["inputs"]
        # 设置 seed（仅采样器节点）
        if cls in ("KSampler", "KSamplerAdvanced", "WanVideoSampler"):
            inputs["seed"] = seed
        # 设置帧数（仅目标视频生成节点）
        if cls in ("KSampler", "KSamplerAdvanced", "WanVideoSampler"):
            if "length" in inputs:
                inputs["length"] = frames
        if cls in ("WanImageToVideo", "WanTextToVideo"):
            if "length" in inputs:
                inputs["length"] = frames
        # 仅对已知视频相关节点设置 frames，避免误改其他节点
        if cls in (
            "WanImageToVideo",
            "WanTextToVideo",
            "VideoCombine",
            "SaveAnimatedWEBP",
            "SaveVideo",
        ):
            if "frames" in inputs:
                inputs["frames"] = frames

    for node_id, node_data in workflow.items():
        if node_data.get("class_type") in ("VideoCombine", "SaveAnimatedWEBP", "SaveVideo"):
            if "filename_prefix" in node_data["inputs"]:
                node_data["inputs"]["filename_prefix"] = f"SF_Shot_{seed}"

    payload = {"prompt": workflow}
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
    response.raise_for_status()
    return response.json().get("prompt_id")


def check_status(prompt_id: str, interval: int = 10, max_retry: int = 180) -> bool:
    """轮询任务状态（视频生成较慢，放宽超时）。"""
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
    raise TimeoutError("视频生成超时（30分钟）")


def download_video(prompt_id: str, output_dir: str, filename: str) -> str:
    """下载生成的视频。

    注意：Wan22 工作流可能输出 .webp 格式（SaveAnimatedWEBP 节点），
    但此处统一以 .mp4 命名。如需在剪辑软件中使用，可能需要用 ffmpeg 转码：
    ffmpeg -i input.webp -c:v libx264 output.mp4
    """
    url = f"{COMFYUI_URL}/history/{prompt_id}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    history = response.json()

    if prompt_id not in history:
        raise RuntimeError("未找到生成结果")

    outputs = history[prompt_id].get("outputs", {})
    for node_id, node_output in outputs.items():
        for key in ("gifs", "videos", "images"):
            if key in node_output:
                for item in node_output[key]:
                    file_url = f"{COMFYUI_URL}/view?filename={item['filename']}&subfolder={item.get('subfolder', '')}&type={item.get('type', 'output')}"
                    vid_response = requests.get(file_url, timeout=300)
                    vid_response.raise_for_status()
                    output_path = Path(output_dir) / filename
                    with open(output_path, "wb") as f:
                        f.write(vid_response.content)
                    return str(output_path)

    raise RuntimeError("未找到视频输出")


def log_generation(
    log_file: str,
    shot_id: str,
    tool: str,
    prompt: str,
    seed: int,
    status: str,
    output_file: str,
    duration_sec: float,
    note: str,
):
    """记录生成日志到 CSV。"""
    log_path = Path(log_file)
    file_exists = log_path.is_file()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                [
                    "timestamp",
                    "shot_id",
                    "tool",
                    "prompt",
                    "seed",
                    "status",
                    "output_file",
                    "duration_sec",
                    "note",
                ]
            )
        writer.writerow(
            [
                datetime.now().isoformat(),
                shot_id,
                tool,
                prompt[:200],
                seed,
                status,
                output_file,
                f"{duration_sec:.1f}",
                note,
            ]
        )


# ==================== 主流程 ====================


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 分镜到视频流水线（Wan2.2 I2V/T2V）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印镜头列表，不提交 ComfyUI",
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
    print("  ShotFlow — 分镜到视频流水线")
    print(f"  Wan2.2 I2V 镜头: {len(WAN_SHOTS)}")
    print(f"  Wan2.2 T2V 镜头: {len(T2V_SHOTS)}")
    print(f"  可灵镜头（需单独运行 kling_video_api.py）: {len(KLING_SHOTS)}")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] 以下镜头将被生成：")
        for shot in WAN_SHOTS:
            print(f"  [I2V] {shot['id']} — {shot['keyframe']} — {shot['prompt'][:50]}...")
        for shot in T2V_SHOTS:
            print(f"  [T2V] {shot['id']} — {shot['prompt'][:50]}...")
        print(f"\n[DRY RUN] 输出目录: {OUTPUT_DIR}")
        print("[DRY RUN] 不执行实际提交")
        return

    # 检查连接
    try:
        requests.get(f"{COMFYUI_URL}/system_stats", timeout=5).raise_for_status()
        print("[OK] ComfyUI 连接正常")
    except Exception as e:
        print(f"[ERROR] 无法连接 ComfyUI: {e}")
        return

    # 加载工作流
    try:
        workflow_template = load_workflow_template()
        print("[OK] 工作流模板已加载")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    success_count = 0
    fail_count = 0

    # --- I2V 镜头 ---
    for i, shot in enumerate(WAN_SHOTS):
        print(f"\n[I2V {i+1}/{len(WAN_SHOTS)}] {shot['id']}")

        keyframe_path = KEYFRAME_DIR / shot["keyframe"]
        if not keyframe_path.exists():
            print(f"  [SKIP] 关键帧不存在: {keyframe_path}")
            log_generation(
                str(LOG_FILE),
                shot["id"],
                "Wan2.2_I2V",
                shot["prompt"],
                0,
                "skipped",
                "",
                0,
                "关键帧不存在",
            )
            continue

        seed = 2000 + i
        frames = shot["duration"] * 24  # 24fps
        start_time = time.time()

        try:
            workflow = copy.deepcopy(workflow_template)
            image_name = upload_image(str(keyframe_path))
            print(f"  [Uploaded] {image_name}")

            prompt_id = submit_i2v_prompt(workflow, image_name, shot["prompt"], seed, frames)
            print(f"  [Submitted] prompt_id={prompt_id}")

            check_status(prompt_id, interval=10, max_retry=180)
            print("  [Completed]")

            filename = f"SF_{shot['id']}_Wan_v01.mp4"
            download_video(prompt_id, str(OUTPUT_DIR), filename)

            elapsed = time.time() - start_time
            log_generation(
                str(LOG_FILE),
                shot["id"],
                "Wan2.2_I2V",
                shot["prompt"],
                seed,
                "success",
                filename,
                elapsed,
                "",
            )
            success_count += 1

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  [FAILED] {e}")
            log_generation(
                str(LOG_FILE),
                shot["id"],
                "Wan2.2_I2V",
                shot["prompt"],
                seed,
                "failed",
                "",
                elapsed,
                str(e),
            )
            fail_count += 1

    # --- T2V 镜头 ---
    for i, shot in enumerate(T2V_SHOTS):
        print(f"\n[T2V {i+1}/{len(T2V_SHOTS)}] {shot['id']}")

        seed = 3000 + i
        frames = shot["duration"] * 24
        start_time = time.time()

        try:
            workflow = copy.deepcopy(workflow_template)
            prompt_id = submit_t2v_prompt(workflow, shot["prompt"], seed, frames)
            print(f"  [Submitted] prompt_id={prompt_id}")

            check_status(prompt_id, interval=10, max_retry=180)
            print("  [Completed]")

            filename = f"SF_{shot['id']}_WanT2V_v01.mp4"
            download_video(prompt_id, str(OUTPUT_DIR), filename)

            elapsed = time.time() - start_time
            log_generation(
                str(LOG_FILE),
                shot["id"],
                "Wan2.2_T2V",
                shot["prompt"],
                seed,
                "success",
                filename,
                elapsed,
                "",
            )
            success_count += 1

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  [FAILED] {e}")
            log_generation(
                str(LOG_FILE),
                shot["id"],
                "Wan2.2_T2V",
                shot["prompt"],
                seed,
                "failed",
                "",
                elapsed,
                str(e),
            )
            fail_count += 1

    # --- 汇总 ---
    print("\n" + "=" * 60)
    print("  视频生成完成")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  可灵镜头待手动生成: {len(KLING_SHOTS)} 个 ({', '.join(KLING_SHOTS)})")
    print(f"  日志: {LOG_FILE}")
    print(f"  输出: {OUTPUT_DIR}")
    print("=" * 60)
    print("\n下一步: 运行 kling_video_api.py 生成复杂镜头")


if __name__ == "__main__":
    main()

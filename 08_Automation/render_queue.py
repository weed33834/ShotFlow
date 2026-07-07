#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渲染队列管理器 — 管理批量生成任务的队列、优先级与重试
ShotFlow

.. deprecated::
    本脚本已被后端 ``app.services.queue_service`` 取代（基于 Celery + PostgreSQL，
    支持状态机/优先级/崩溃恢复/错误分类重试）。新项目请通过后端 API 提交与管理渲染任务。
    本文件保留作为历史参考与离线批处理回退方案，不再积极维护。

用法:
    python render_queue.py add <shot_id> <type> <prompt>     # 添加任务
    python render_queue.py list                               # 查看队列
    python render_queue.py run                                # 执行队列
    python render_queue.py status                             # 查看状态
    python render_queue.py retry                              # 重试失败任务

任务类型: keyframe | video_i2v | video_t2v | kling | tts | music
队列文件: 06_Research/render_queue.json
"""

import json
import os
import subprocess
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

from common import PROJECT_ROOT

# ==================== 配置区 ====================

QUEUE_FILE = PROJECT_ROOT / "06_Research" / "render_queue.json"
LOG_FILE = PROJECT_ROOT / "06_Research" / "render_queue_log.csv"

MAX_RETRY = 3
RETRY_DELAY = 10  # 秒

# ==================== 队列管理 ====================


def load_queue() -> dict:
    """加载队列文件。"""
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tasks": [], "completed": [], "failed": []}


def save_queue(queue: dict):
    """保存队列文件。"""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def add_task(shot_id: str, task_type: str, prompt: str, priority: int = 0, extra: dict = None):
    """添加任务到队列。"""
    queue = load_queue()
    task = {
        "id": f"{shot_id}_{task_type}_{int(time.time())}",
        "shot_id": shot_id,
        "type": task_type,
        "prompt": prompt,
        "priority": priority,
        "status": "pending",
        "retry_count": 0,
        "created_at": datetime.now().isoformat(),
        "extra": extra or {},
    }
    queue["tasks"].append(task)
    # 按优先级排序（数字大的先执行）
    queue["tasks"].sort(key=lambda t: t["priority"], reverse=True)
    save_queue(queue)
    print(f"[Added] {task['id']}")


def list_tasks():
    """列出队列中的任务。"""
    queue = load_queue()
    pending = [t for t in queue["tasks"] if t["status"] == "pending"]
    running = [t for t in queue["tasks"] if t["status"] == "running"]
    completed = queue.get("completed", [])
    failed = queue.get("failed", [])

    print(f"\n{'='*60}")
    print("  渲染队列状态")
    print(f"{'='*60}")
    print(f"  待执行: {len(pending)}")
    print(f"  执行中: {len(running)}")
    print(f"  已完成: {len(completed)}")
    print(f"  已失败: {len(failed)}")

    if pending:
        print("\n  --- 待执行任务 ---")
        for t in pending[:20]:
            print(f"  [{t['priority']}] {t['id']} | {t['type']} | {t['prompt'][:50]}...")
        if len(pending) > 20:
            print(f"  ... 还有 {len(pending)-20} 个任务")

    if running:
        print("\n  --- 执行中 ---")
        for t in running:
            print(f"  {t['id']} | {t['type']}")

    if failed:
        print("\n  --- 失败任务 ---")
        for t in failed[:10]:
            print(f"  {t['id']} | 重试 {t['retry_count']} 次 | {t.get('error', '')[:60]}")

    print()


def run_queue():
    """执行队列中的待执行任务。"""
    queue = load_queue()
    pending = [t for t in queue["tasks"] if t["status"] == "pending"]

    if not pending:
        print("[Info] 队列为空，无待执行任务")
        return

    print(f"\n[Info] 开始执行 {len(pending)} 个任务\n")

    for task in pending:
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()
        save_queue(queue)

        print(f"[Running] {task['id']} ({task['type']})")
        success = execute_task(task)

        if success:
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            queue["tasks"] = [t for t in queue["tasks"] if t["id"] != task["id"]]
            queue["completed"].append(task)
            print("  [OK] 完成\n")
        else:
            task["retry_count"] += 1
            if task["retry_count"] >= MAX_RETRY:
                task["status"] = "failed"
                task["failed_at"] = datetime.now().isoformat()
                queue["tasks"] = [t for t in queue["tasks"] if t["id"] != task["id"]]
                queue["failed"].append(task)
                print("  [FAIL] 达到最大重试次数，移入失败队列\n")
            else:
                task["status"] = "pending"
                print(f"  [RETRY] 将在 {RETRY_DELAY}s 后重试 ({task['retry_count']}/{MAX_RETRY})\n")
                time.sleep(RETRY_DELAY)

        save_queue(queue)


def execute_task(task: dict) -> bool:
    """执行单个任务，返回是否成功。"""
    task_type = task["type"]

    try:
        if task_type == "keyframe":
            # 关键帧生成通过 ComfyUI API
            return run_comfyui_task(task, "Flux_Character_Consistency_api.json")
        elif task_type == "video_i2v":
            return run_comfyui_task(task, "Wan22_Dual_Expert_Video_api.json")
        elif task_type == "video_t2v":
            return run_comfyui_task(task, "Wan22_Dual_Expert_Video_api.json", is_t2v=True)
        elif task_type == "kling":
            return run_kling_task(task)
        elif task_type == "tts":
            return run_tts_task(task)
        elif task_type == "music":
            return run_music_task(task)
        else:
            print(f"  [ERROR] 未知任务类型: {task_type}")
            return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        task["error"] = str(e)
        return False


def run_comfyui_task(task: dict, workflow_file: str, is_t2v: bool = False) -> bool:
    """通过 ComfyUI API 执行生成任务。"""
    import requests

    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    workflow_path = PROJECT_ROOT / "03_Workflows" / "api" / workflow_file

    if not workflow_path.exists():
        print(f"  [ERROR] 工作流文件不存在: {workflow_path}")
        return False

    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    # 设置提示词
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "CLIPTextEncode":
            node_data["inputs"]["text"] = task["prompt"]
            break

    # 设置 seed
    seed = task.get("extra", {}).get("seed", int(time.time()) % 100000)
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") in ("KSampler", "KSamplerAdvanced"):
            node_data["inputs"]["seed"] = seed

    # 提交
    payload = {"prompt": workflow}
    resp = requests.post(f"{comfyui_url}/prompt", json=payload, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json().get("prompt_id")
    print(f"  [Submitted] prompt_id={prompt_id}")

    # 轮询
    for i in range(360):  # 最多等 30 分钟
        time.sleep(5)
        resp = requests.get(f"{comfyui_url}/history/{prompt_id}", timeout=10)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id in history:
            status = history[prompt_id].get("status", {})
            if status.get("completed"):
                print("  [Completed] 生成成功")
                return True
            if status.get("status_str") == "error":
                print(f"  [ERROR] 生成失败: {status}")
                task["error"] = json.dumps(status)
                return False

    print("  [TIMEOUT] 生成超时")
    task["error"] = "timeout"
    return False


def run_kling_task(task: dict) -> bool:
    """执行可灵视频生成。"""
    script = Path(__file__).resolve().parent / "kling_video_api.py"
    project_root = Path(__file__).resolve().parent.parent
    shot_id = task.get("shot_id", "S01_04")
    env = {
        **os.environ,
        "KLING_PROMPT": task.get("prompt", ""),
        "KLING_SHOT_ID": shot_id,
        "KLING_START_IMAGE": str(project_root / "01_Assets" / "Scenes" / f"{shot_id}_start.png"),
        "KLING_END_IMAGE": str(project_root / "01_Assets" / "Scenes" / f"{shot_id}_end.png"),
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    return result.returncode == 0


def run_tts_task(task: dict) -> bool:
    """执行 ElevenLabs 配音。"""
    script = Path(__file__).resolve().parent / "elevenlabs_tts_api.py"
    env = {**os.environ, "TTS_TEXT": task.get("prompt", "")}
    # 从 extra 中读取角色与文件名
    if task.get("extra", {}).get("role"):
        env["TTS_ROLE"] = task["extra"]["role"]
    if task.get("extra", {}).get("filename"):
        env["TTS_FILENAME"] = task["extra"]["filename"]
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    return result.returncode == 0


def run_music_task(task: dict) -> bool:
    """执行 Suno 配乐。"""
    script = Path(__file__).resolve().parent / "suno_music_api.py"
    env = {**os.environ, "MUSIC_PROMPT": task.get("prompt", "")}
    if task.get("extra", {}).get("title"):
        env["MUSIC_TITLE"] = task["extra"]["title"]
    if task.get("extra", {}).get("tags"):
        env["MUSIC_TAGS"] = task["extra"]["tags"]
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    return result.returncode == 0


def retry_failed():
    """重试失败的任务。"""
    queue = load_queue()
    failed = queue.get("failed", [])
    if not failed:
        print("[Info] 没有失败任务")
        return

    print(f"\n[Info] 将 {len(failed)} 个失败任务重新加入队列\n")
    for task in failed:
        task["status"] = "pending"
        task["retry_count"] = 0
        task["error"] = ""
        queue["tasks"].append(task)
    queue["failed"] = []
    save_queue(queue)
    print("[OK] 已重新入队，运行 'run' 执行")


def show_status():
    """显示队列状态摘要。"""
    queue = load_queue()
    pending = len([t for t in queue["tasks"] if t["status"] == "pending"])
    running = len([t for t in queue["tasks"] if t["status"] == "running"])
    completed = len(queue.get("completed", []))
    failed = len(queue.get("failed", []))
    total = pending + running + completed + failed

    pct = (completed / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)

    print(f"\n  渲染队列: [{bar}] {pct:.1f}%")
    print(f"  待执行: {pending} | 执行中: {running} | 完成: {completed} | 失败: {failed}")
    print(f"  总计: {total}\n")


# ==================== 主流程 ====================


def print_usage():
    print("用法:")
    print("  python render_queue.py add <shot_id> <type> <prompt> [--priority N]")
    print("  python render_queue.py list")
    print("  python render_queue.py run")
    print("  python render_queue.py status")
    print("  python render_queue.py retry")
    print("")
    print("任务类型: keyframe | video_i2v | video_t2v | kling | tts | music")


def main():
    warnings.warn(
        "render_queue.py 已被后端 app.services.queue_service 取代，"
        "建议通过后端 API 提交与管理渲染任务。本脚本保留作为离线回退方案，不再积极维护。",
        DeprecationWarning,
        stacklevel=2,
    )
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_usage()
        return

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 5:
            print("用法: python render_queue.py add <shot_id> <type> <prompt> [--priority N]")
            return
        shot_id = sys.argv[2]
        task_type = sys.argv[3]
        prompt = sys.argv[4]
        priority = 0
        if "--priority" in sys.argv:
            idx = sys.argv.index("--priority")
            priority = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 0
        add_task(shot_id, task_type, prompt, priority)

    elif cmd == "list":
        list_tasks()

    elif cmd == "run":
        run_queue()

    elif cmd == "status":
        show_status()

    elif cmd == "retry":
        retry_failed()

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()

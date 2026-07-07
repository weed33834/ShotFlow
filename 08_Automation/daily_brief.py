#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日站会简报生成脚本 — 自动汇总项目状态，生成站会简报
ShotFlow

用法: python daily_brief.py
输出: 控制台打印 + 07_Team/daily_briefs/YYYY-MM-DD.md
"""

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

from common import PROJECT_ROOT

# ==================== 配置区 ====================

# 把 backend/ 加入路径，以便复用 app 包的 SessionLocal / RenderTask
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

CHECKLIST_FILE = PROJECT_ROOT / "07_Team" / "templates" / "progress_checklist.zh.md"
QUEUE_FILE = PROJECT_ROOT / "06_Research" / "render_queue.json"
GEN_LOG_FILE = PROJECT_ROOT / "06_Research" / "video_gen_log.csv"
FAILURE_LOG_FILE = PROJECT_ROOT / "06_Research" / "failure_cases.md"
BRIEF_DIR = PROJECT_ROOT / "07_Team" / "daily_briefs"

# ==================== 工具函数 ====================


def parse_checklist(filepath: Path) -> dict:
    """解析检查清单。"""
    if not filepath.exists():
        return {}

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    sections = {}
    current_section = None
    for line in content.split("\n"):
        section_match = re.match(r"^##+\s+(.+)", line)
        if section_match:
            current_section = section_match.group(1).strip()
            sections[current_section] = {"total": 0, "done": 0, "pending": []}
            continue
        if current_section:
            if re.match(r"^\s*- \[x\]", line):
                sections[current_section]["total"] += 1
                sections[current_section]["done"] += 1
            elif re.match(r"^\s*- \[ \]", line):
                sections[current_section]["total"] += 1
                # 提取任务描述
                task_text = re.sub(r"^\s*- \[ \]\s*", "", line).strip()
                if task_text:
                    sections[current_section]["pending"].append(task_text)
    return sections


def _empty_queue_stats() -> dict:
    """队列统计的空结构，保证 DB 与 JSON 回退返回一致字段。"""
    return {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0,
        "today_failed": [],  # 今日失败任务明细
        "today_completed": [],  # 今日完成任务明细
    }


def parse_render_queue(filepath: Path) -> dict:
    """解析渲染队列（JSON 回退方案，旧版 render_queue.json）。"""
    stats = _empty_queue_stats()
    if not filepath.exists():
        return stats
    with open(filepath, "r", encoding="utf-8") as f:
        queue = json.load(f)
    tasks = queue.get("tasks", [])
    stats["pending"] = len([t for t in tasks if t.get("status") == "pending"])
    stats["running"] = len([t for t in tasks if t.get("status") == "running"])
    stats["completed"] = len(queue.get("completed", []))
    stats["failed"] = len(queue.get("failed", []))
    # 旧 JSON 无时间戳与 cancelled，明细留空
    return stats


def load_render_queue_from_db() -> dict:
    """从 PostgreSQL render_tasks 表读取队列状态。

    统计各状态任务数，并列出今日失败/完成的任务明细。
    """
    from app.db.session import SessionLocal
    from app.models.pipeline import RenderTask
    from sqlalchemy import func, select

    stats = _empty_queue_stats()
    today = date.today()
    today_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(today, time.max, tzinfo=timezone.utc)

    with SessionLocal() as db:
        # 按状态聚合计数
        rows = db.execute(
            select(RenderTask.status, func.count(RenderTask.id)).group_by(RenderTask.status)
        ).all()
        for status, cnt in rows:
            if status in stats:
                stats[status] = cnt

        # 今日失败任务（DateTime 字段需用范围查询）
        failed_tasks = (
            db.execute(
                select(RenderTask)
                .where(RenderTask.failed_at >= today_start, RenderTask.failed_at <= today_end)
                .order_by(RenderTask.id.desc())
            )
            .scalars()
            .all()
        )
        for t in failed_tasks:
            stats["today_failed"].append(
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "prompt": t.prompt or "",
                    "error": t.error or "",
                }
            )

        # 今日完成任务
        done_tasks = (
            db.execute(
                select(RenderTask)
                .where(RenderTask.completed_at >= today_start, RenderTask.completed_at <= today_end)
                .order_by(RenderTask.id.desc())
            )
            .scalars()
            .all()
        )
        for t in done_tasks:
            stats["today_completed"].append(
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "prompt": t.prompt or "",
                }
            )

    return stats


def load_render_queue() -> tuple:
    """加载渲染队列：优先读 DB，不可用则回退 JSON 并打印警告。

    返回 (stats_dict, source)，source 为 "db" 或 "json"。
    """
    try:
        return load_render_queue_from_db(), "db"
    except Exception as e:  # noqa: BLE001 — 回退场景需兜底所有异常
        print(f"[警告] DB 不可用，回退到 JSON 队列 ({QUEUE_FILE.name}): {e}")
        return parse_render_queue(QUEUE_FILE), "json"


def parse_gen_log(filepath: Path) -> dict:
    """解析视频生成日志。"""
    if not filepath.exists():
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0}
    total = success = failed = skipped = 0
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            status = row.get("status", "")
            if status == "success":
                success += 1
            elif status == "failed":
                failed += 1
            elif status == "skipped":
                skipped += 1
    return {"total": total, "success": success, "failed": failed, "skipped": skipped}


def count_assets() -> dict:
    """统计当前资产数量。"""
    assets = {}
    # 关键帧
    scene_dir = PROJECT_ROOT / "01_Assets" / "Scenes"
    assets["keyframes"] = len(list(scene_dir.glob("*.png"))) if scene_dir.exists() else 0
    # 视频
    video_dir = PROJECT_ROOT / "05_Output" / "Rough_Cuts"
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    assets["videos"] = (
        len([f for f in video_dir.rglob("*") if f.suffix.lower() in video_exts])
        if video_dir.exists()
        else 0
    )
    # 音频
    audio_dir = PROJECT_ROOT / "01_Assets" / "Audio"
    audio_exts = {".wav", ".mp3"}
    assets["audio"] = (
        len([f for f in audio_dir.rglob("*") if f.suffix.lower() in audio_exts])
        if audio_dir.exists()
        else 0
    )
    # 最终成片
    final_dir = PROJECT_ROOT / "05_Output" / "Final"
    assets["final"] = (
        len([f for f in final_dir.rglob("*") if f.suffix.lower() in video_exts])
        if final_dir.exists()
        else 0
    )
    return assets


# ==================== 主流程 ====================


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 每日站会简报生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印到控制台，不写入 07_Team/daily_briefs/YYYY-MM-DD.md",
    )
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print("  ShotFlow — 每日站会简报")
    print(f"  日期: {today}")
    print("=" * 60)

    # 1. 检查清单进度
    checklist = parse_checklist(CHECKLIST_FILE)
    total_done = sum(s["done"] for s in checklist.values())
    total_tasks = sum(s["total"] for s in checklist.values())
    overall_pct = (total_done / total_tasks * 100) if total_tasks > 0 else 0

    # 2. 渲染队列（优先 DB，不可用回退 JSON）
    queue, queue_source = load_render_queue()
    print(f"[队列数据源] {queue_source.upper()}")

    # 3. 生成日志
    gen_log = parse_gen_log(GEN_LOG_FILE)

    # 4. 资产统计
    assets = count_assets()

    # 5. 待办任务（取检查清单中未完成项）
    all_pending = []
    for section, stats in checklist.items():
        for task in stats.get("pending", []):
            all_pending.append((section, task))

    # 生成简报文本
    brief = []
    brief.append(f"# 每日站会简报 — {today}\n")
    brief.append(f"> 生成时间: {now_str}\n")

    # 整体进度
    brief.append("## 一、整体进度\n")
    bar_len = 30
    filled = int(bar_len * overall_pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    brief.append(f"```\n{bar} {overall_pct:.1f}% ({total_done}/{total_tasks})\n```\n")

    # 各阶段进度
    brief.append("## 二、各阶段进度\n")
    brief.append("| 阶段 | 完成 | 总数 | 进度 |")
    brief.append("|------|------|------|------|")
    for section, stats in checklist.items():
        pct = (stats["done"] / stats["total"] * 100) if stats["total"] > 0 else 0
        brief.append(f"| {section} | {stats['done']} | {stats['total']} | {pct:.0f}% |")
    brief.append("")

    # 资产统计
    brief.append("## 三、资产统计\n")
    brief.append("| 资产类型 | 当前数量 | 目标 | 状态 |")
    brief.append("|----------|----------|------|------|")
    brief.append(
        f"| 场景关键帧 | {assets['keyframes']} | 29 | {'✅' if assets['keyframes'] >= 29 else '⏳'} |"
    )
    brief.append(
        f"| 原始视频 | {assets['videos']} | 24 | {'✅' if assets['videos'] >= 24 else '⏳'} |"
    )
    brief.append(
        f"| 音频素材 | {assets['audio']} | 15+ | {'✅' if assets['audio'] >= 15 else '⏳'} |"
    )
    brief.append(f"| 最终成片 | {assets['final']} | 1 | {'✅' if assets['final'] >= 1 else '⏳'} |")
    brief.append("")

    # 渲染队列
    brief.append("## 四、渲染队列\n")
    brief.append(f"- 待执行: {queue['pending']}")
    brief.append(f"- 执行中: {queue['running']}")
    brief.append(f"- 已完成: {queue['completed']}")
    brief.append(f"- 已失败: {queue['failed']}")
    brief.append(f"- 已取消: {queue['cancelled']}")
    brief.append("")

    # 今日失败任务明细
    if queue.get("today_failed"):
        brief.append("### 今日失败任务\n")
        for t in queue["today_failed"]:
            err = (t.get("error") or "").strip().replace("\n", " ")
            if len(err) > 120:
                err = err[:120] + "..."
            prompt = (t.get("prompt") or "").strip().replace("\n", " ")
            if len(prompt) > 60:
                prompt = prompt[:60] + "..."
            label = prompt or "(无 prompt)"
            brief.append(f"- #{t['id']} [{t['task_type']}] {label}")
            brief.append(f"  - 错误: {err or '(无错误信息)'}")
        brief.append("")

    # 今日完成任务明细
    if queue.get("today_completed"):
        brief.append("### 今日完成任务\n")
        for t in queue["today_completed"][:20]:
            prompt = (t.get("prompt") or "").strip().replace("\n", " ")
            if len(prompt) > 60:
                prompt = prompt[:60] + "..."
            label = prompt or "(无 prompt)"
            brief.append(f"- #{t['id']} [{t['task_type']}] {label}")
        if len(queue["today_completed"]) > 20:
            brief.append(f"\n... 还有 {len(queue['today_completed']) - 20} 条已完成任务")
        brief.append("")

    # 生成日志
    if gen_log["total"] > 0:
        brief.append("## 五、生成日志\n")
        brief.append(f"- 总任务: {gen_log['total']}")
        brief.append(f"- 成功: {gen_log['success']}")
        brief.append(f"- 失败: {gen_log['failed']}")
        brief.append(f"- 跳过: {gen_log['skipped']}")
        success_rate = gen_log["success"] / gen_log["total"] * 100 if gen_log["total"] > 0 else 0
        brief.append(f"- 成功率: {success_rate:.1f}%")
        brief.append("")

    # 今日待办（取前 10 项未完成任务）
    brief.append("## 六、今日待办（优先）\n")
    if all_pending:
        for i, (section, task) in enumerate(all_pending[:10], 1):
            brief.append(f"{i}. [{section}] {task}")
        if len(all_pending) > 10:
            brief.append(f"\n... 还有 {len(all_pending) - 10} 项待办")
    else:
        brief.append("所有任务已完成！🎉")
    brief.append("")

    # 站会模板
    brief.append("## 七、站会发言模板\n")
    brief.append("```")
    brief.append("昨日完成:")
    brief.append("  - [填写完成的任务]")
    brief.append("")
    brief.append("今日计划:")
    brief.append("  - [填写今日计划]")
    brief.append("")
    brief.append("阻塞/风险:")
    brief.append("  - [填写阻塞项，无则填'无']")
    brief.append("```")
    brief.append("")

    brief_text = "\n".join(brief)

    # 打印到控制台
    print(brief_text)

    if args.dry_run:
        print("\n[DRY RUN] 不写入文件")
        return

    # 保存文件
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    brief_file = BRIEF_DIR / f"{today}.md"
    with open(brief_file, "w", encoding="utf-8") as f:
        f.write(brief_text)

    print(f"\n{'='*60}")
    print(f"  简报已保存: {brief_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

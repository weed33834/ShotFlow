#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产盘点与进度看板脚本 — 扫描项目目录，生成资产清单与进度报告
ShotFlow

用法: python asset_dashboard.py
输出: 06_Research/asset_dashboard.md
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

from common import PROJECT_ROOT

# ==================== 配置区 ====================

OUTPUT_FILE = PROJECT_ROOT / "06_Research" / "asset_dashboard.md"
CHECKLIST_FILE = PROJECT_ROOT / "07_Team" / "templates" / "progress_checklist.zh.md"

# 资产目录配置
ASSET_DIRS = {
    "角色图片": PROJECT_ROOT / "01_Assets" / "Characters",
    "场景关键帧": PROJECT_ROOT / "01_Assets" / "Scenes",
    "音频素材": PROJECT_ROOT / "01_Assets" / "Audio",
    "剧本文档": PROJECT_ROOT / "02_Scripts",
    "工作流JSON": PROJECT_ROOT / "03_Workflows",
    "SOP文档": PROJECT_ROOT / "04_SOP",
    "粗剪版本": PROJECT_ROOT / "05_Output" / "Rough_Cuts",
    "最终成片": PROJECT_ROOT / "05_Output" / "Final",
    "调研文档": PROJECT_ROOT / "06_Research",
    "团队文档": PROJECT_ROOT / "07_Team",
    "自动化脚本": PROJECT_ROOT / "08_Automation",
}

# 文件类型统计
EXT_CATEGORIES = {
    "图片": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
    "视频": [".mp4", ".avi", ".mov", ".mkv", ".webm", ".gif"],
    "音频": [".wav", ".mp3", ".flac", ".aac", ".ogg"],
    "文档": [".md", ".txt", ".pdf", ".docx"],
    "代码": [".py", ".sh", ".json", ".yaml", ".yml", ".toml"],
    "模型": [".safetensors", ".ckpt", ".pt", ".bin", ".gguf"],
    "配置": [".gitignore", ".gitattributes", ".env"],
}

# ==================== 工具函数 ====================


def get_dir_size(path: Path) -> int:
    """递归计算目录大小。"""
    total = 0
    if path.exists():
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    return total


def count_files_by_ext(path: Path) -> dict:
    """按扩展名统计文件数。"""
    counts = {}
    if path.exists():
        for entry in path.rglob("*"):
            if entry.is_file():
                ext = entry.suffix.lower()
                counts[ext] = counts.get(ext, 0) + 1
    return counts


def categorize_files(ext_counts: dict) -> dict:
    """将扩展名归类到大类。"""
    categories = {cat: 0 for cat in EXT_CATEGORIES}
    for ext, count in ext_counts.items():
        for cat, exts in EXT_CATEGORIES.items():
            if ext in exts:
                categories[cat] += count
                break
        else:
            categories.setdefault("其他", 0)
            categories["其他"] = categories.get("其他", 0) + count
    return categories


def parse_checklist_progress(filepath: Path) -> dict:
    """解析检查清单，统计完成进度。"""
    if not filepath.exists():
        return {}

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 按阶段统计
    sections = {}
    current_section = None
    for line in content.split("\n"):
        # 匹配章节标题
        section_match = re.match(r"^##+\s+(.+)", line)
        if section_match:
            current_section = section_match.group(1).strip()
            sections[current_section] = {"total": 0, "done": 0}
            continue

        # 匹配复选框
        if current_section:
            if re.match(r"^\s*- \[x\]", line):
                sections[current_section]["total"] += 1
                sections[current_section]["done"] += 1
            elif re.match(r"^\s*- \[ \]", line):
                sections[current_section]["total"] += 1

    return sections


def format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


# ==================== 主流程 ====================


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 资产盘点与进度看板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印到控制台，不写入 06_Research/asset_dashboard.md",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  ShotFlow — 资产盘点与进度看板")
    print("=" * 60)

    # 1. 目录资产统计
    print("\n[1/3] 扫描目录资产...")
    dir_stats = {}
    total_size = 0
    total_files = 0

    for name, dir_path in ASSET_DIRS.items():
        size = get_dir_size(dir_path)
        ext_counts = count_files_by_ext(dir_path)
        file_count = sum(ext_counts.values())
        categories = categorize_files(ext_counts)
        dir_stats[name] = {
            "path": str(dir_path.relative_to(PROJECT_ROOT)),
            "size": size,
            "files": file_count,
            "categories": categories,
            "ext_counts": ext_counts,
        }
        total_size += size
        total_files += file_count
        print(f"  {name}: {file_count} 文件, {format_size(size)}")

    # 2. 检查清单进度
    print("\n[2/3] 解析检查清单进度...")
    checklist = parse_checklist_progress(CHECKLIST_FILE)
    for section, stats in checklist.items():
        pct = (stats["done"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {section}: {stats['done']}/{stats['total']} ({pct:.0f}%)")

    # 3. 生成报告
    print("\n[3/3] 生成报告...")

    report = []
    report.append("# ShotFlow — 资产盘点与进度看板\n")
    report.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 总览
    report.append("## 一、总览\n")
    report.append("| 指标 | 数值 |")
    report.append("|------|------|")
    report.append(f"| 总文件数 | {total_files} |")
    report.append(f"| 总体积 | {format_size(total_size)} |")
    report.append(f"| 资产目录数 | {len(ASSET_DIRS)} |")

    # 检查清单进度
    total_done = sum(s["done"] for s in checklist.values())
    total_tasks = sum(s["total"] for s in checklist.values())
    overall_pct = (total_done / total_tasks * 100) if total_tasks > 0 else 0
    report.append(f"| 检查清单完成 | {total_done}/{total_tasks} ({overall_pct:.0f}%) |")
    report.append("")

    # 进度条
    bar_len = 30
    filled = int(bar_len * overall_pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    report.append(f"```\n整体进度: [{bar}] {overall_pct:.1f}%\n```\n")

    # 各目录详情
    report.append("## 二、各目录资产详情\n")
    report.append("| 目录 | 路径 | 文件数 | 体积 | 图片 | 视频 | 音频 | 文档 | 代码 |")
    report.append("|------|------|--------|------|------|------|------|------|------|")
    for name, stats in dir_stats.items():
        cats = stats["categories"]
        report.append(
            f"| {name} | `{stats['path']}` | {stats['files']} | {format_size(stats['size'])} | "
            f"{cats.get('图片', 0)} | {cats.get('视频', 0)} | {cats.get('音频', 0)} | "
            f"{cats.get('文档', 0)} | {cats.get('代码', 0)} |"
        )
    report.append("")

    # 检查清单分阶段
    report.append("## 三、检查清单进度（分阶段）\n")
    report.append("| 阶段 | 完成 | 总数 | 进度 |")
    report.append("|------|------|------|------|")
    for section, stats in checklist.items():
        pct = (stats["done"] / stats["total"] * 100) if stats["total"] > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        report.append(f"| {section} | {stats['done']} | {stats['total']} | {bar} {pct:.0f}% |")
    report.append("")

    # 关键资产检查
    report.append("## 四、关键资产就绪检查\n")
    report.append("| 资产 | 状态 |")
    report.append("|------|------|")

    key_assets = [
        ("完整剧本", PROJECT_ROOT / "02_Scripts" / "script_and_worldbuilding.md"),
        ("详细分镜表", PROJECT_ROOT / "02_Scripts" / "detailed_storyboard.md"),
        ("关键帧提示词", PROJECT_ROOT / "02_Scripts" / "keyframe_prompts.md"),
        ("角色圣经模板", PROJECT_ROOT / "02_Scripts" / "character_bible_template.md"),
        ("Flux 工作流 JSON", PROJECT_ROOT / "03_Workflows" / "Flux_Character_Consistency.json"),
        ("Wan2.2 工作流 JSON", PROJECT_ROOT / "03_Workflows" / "Wan22_Dual_Expert_Video.json"),
        ("节点连接说明", PROJECT_ROOT / "03_Workflows" / "comfyui_node_connections.md"),
        ("SOP 操作手册", PROJECT_ROOT / "04_SOP" / "sop_shotflow.md"),
        ("后期制作规范", PROJECT_ROOT / "04_SOP" / "postproduction.md"),
        ("音频制作规范", PROJECT_ROOT / "04_SOP" / "audio_production.md"),
        ("ComfyUI 部署脚本", PROJECT_ROOT / "08_Automation" / "deploy_comfyui.sh"),
        ("关键帧批量生成", PROJECT_ROOT / "08_Automation" / "batch_keyframe_gen.py"),
        ("视频流水线", PROJECT_ROOT / "08_Automation" / "storyboard_to_video.py"),
        ("可灵 API 脚本", PROJECT_ROOT / "08_Automation" / "kling_video_api.py"),
        ("ElevenLabs 脚本", PROJECT_ROOT / "08_Automation" / "elevenlabs_tts_api.py"),
        ("Suno 脚本", PROJECT_ROOT / "08_Automation" / "suno_music_api.py"),
        ("预飞行检查", PROJECT_ROOT / "08_Automation" / "preflight_check.py"),
        ("Git 初始化", PROJECT_ROOT / "08_Automation" / "init_git.sh"),
        (".gitignore", PROJECT_ROOT / ".gitignore"),
        ("项目计划书", PROJECT_ROOT / "07_Team" / "templates" / "project_proposal.zh.md"),
        ("检查清单", PROJECT_ROOT / "07_Team" / "templates" / "progress_checklist.zh.md"),
        ("教师评审表", PROJECT_ROOT / "07_Team" / "templates" / "instructor_review_template.zh.md"),
        ("周报模板", PROJECT_ROOT / "07_Team" / "templates" / "weekly_report_template.zh.md"),
        ("总结报告模板", PROJECT_ROOT / "07_Team" / "templates" / "summary_report_template.zh.md"),
    ]

    ready_count = 0
    for name, path in key_assets:
        exists = path.exists()
        if exists:
            ready_count += 1
        report.append(f"| {name} | {'✅ 已就绪' if exists else '❌ 缺失'} |")

    report.append(
        f"\n**关键资产就绪率**: {ready_count}/{len(key_assets)} ({ready_count/len(key_assets)*100:.0f}%)\n"
    )

    # 待生成资产
    report.append("## 五、待生成资产（实机执行后产生）\n")
    report.append("| 资产类型 | 预期数量 | 当前数量 | 状态 |")
    report.append("|----------|----------|----------|------|")

    scene_keyframes = dir_stats.get("场景关键帧", {}).get("categories", {}).get("图片", 0)
    report.append(
        f"| 场景关键帧 | 29 | {scene_keyframes} | {'✅' if scene_keyframes >= 29 else '⏳ 待生成'} |"
    )

    rough_videos = dir_stats.get("粗剪版本", {}).get("categories", {}).get("视频", 0)
    report.append(
        f"| 原始视频片段 | 24 | {rough_videos} | {'✅' if rough_videos >= 24 else '⏳ 待生成'} |"
    )

    audio_files = dir_stats.get("音频素材", {}).get("files", 0)
    report.append(
        f"| 音频素材 | 15+ | {audio_files} | {'✅' if audio_files >= 15 else '⏳ 待生成'} |"
    )

    final_videos = dir_stats.get("最终成片", {}).get("categories", {}).get("视频", 0)
    report.append(
        f"| 最终成片 | 1 | {final_videos} | {'✅' if final_videos >= 1 else '⏳ 待生成'} |"
    )

    report.append("")

    report_text = "\n".join(report)

    if args.dry_run:
        print("\n[DRY RUN] 以下报告内容不会写入文件：")
        print(report_text)
        return

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n[OK] 报告已保存: {OUTPUT_FILE}")
    print(f"     整体进度: {overall_pct:.1f}%")
    print(f"     关键资产: {ready_count}/{len(key_assets)} 就绪")


if __name__ == "__main__":
    main()

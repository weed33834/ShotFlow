#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 性能基准测试脚本
ShotFlow — 测试 Flux / Wan2.2 在本机的生成速度与显存占用

用法:
    cd ~/ComfyUI
    source venv/bin/activate
    python <项目根目录>/08_Automation/benchmark.py

    或从任意目录运行（推荐）:
    python 08_Automation/benchmark.py

输出:
    06_Research/benchmark_results.md
"""

import argparse
import os
import sys
from datetime import datetime

from common import PROJECT_ROOT

# ==================== 配置区 ====================

OUTPUT_FILE = PROJECT_ROOT / "06_Research" / "benchmark_results.md"
ITERATIONS = 3  # 每项测试重复次数


def safe_input(prompt: str) -> str:
    """容错的 input()，在非交互/CI 环境返回空字符串。"""
    try:
        return input(prompt).strip()
    except (EOFError, OSError):
        print("  [非交互环境，使用默认值 N/A]")
        return ""


# ==================== 工具函数 ====================


def get_gpu_info() -> dict:
    """获取 GPU 信息。"""
    import torch  # 延迟导入，避免无 GPU 环境下 import 失败

    info = {
        "gpu_name": torch.cuda.get_device_name(0),
        "total_vram_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
    }
    return info


def get_vram_usage() -> dict:
    """获取当前显存使用。"""
    import torch

    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3
    return {"allocated_gb": round(allocated, 2), "reserved_gb": round(reserved, 2)}


def format_results_table(results: list) -> str:
    """将结果格式化为 Markdown 表格。"""
    lines = []
    lines.append("| 测试项 | 显存占用(GB) | 平均耗时(s) | 吞吐量 | 备注 |")
    lines.append("|--------|-------------|------------|--------|------|")
    for r in results:
        lines.append(
            f"| {r['name']} | {r['vram_gb']} | {r['avg_time']:.1f} | "
            f"{r.get('throughput', '-')} | {r.get('note', '')} |"
        )
    return "\n".join(lines)


# ==================== 基准测试 ====================


def benchmark_flux_image(gpu_info: dict) -> dict:
    """测试 Flux.1 Kontext 出图性能（模拟）。"""
    print("\n[Benchmark] Flux.1 Kontext 出图...")
    print("  注意: 此为模拟测试，实际需在 ComfyUI 中运行。")
    print("  请手动记录以下指标:")
    print("  - 加载模型后显存占用")
    print("  - 生成 1 张 1024x1024 图片的耗时")
    print("  - 生成 4 张 batch 的耗时")

    # 手动填写区
    model_load_vram = safe_input("  模型加载后显存占用 (GB): ") or "N/A"
    single_time = safe_input("  单张生成耗时 (秒): ") or "N/A"
    batch_time = safe_input("  4 张 batch 耗时 (秒): ") or "N/A"

    return {
        "name": "Flux.1 Kontext FP8 (1024x1024, 24 steps)",
        "vram_gb": model_load_vram,
        "avg_time": float(single_time) if single_time.replace(".", "").isdigit() else 0,
        "throughput": f"batch4: {batch_time}s" if batch_time != "N/A" else "-",
        "note": f"单张 {single_time}s",
    }


def benchmark_wan_video(gpu_info: dict) -> dict:
    """测试 Wan2.2 I2V 视频生成性能（模拟）。"""
    print("\n[Benchmark] Wan2.2 I2V 14B FP8 视频生成...")
    print("  注意: 此为模拟测试，实际需在 ComfyUI 中运行。")
    print("  请手动记录以下指标:")

    model_load_vram = safe_input("  模型加载后显存占用 (GB): ") or "N/A"
    gen_480p_time = safe_input("  480P 5秒视频生成耗时 (秒): ") or "N/A"
    gen_720p_time = safe_input("  720P 5秒视频生成耗时 (秒): ") or "N/A"

    return {
        "name": "Wan2.2 I2V 14B FP8 (5s, 24fps)",
        "vram_gb": model_load_vram,
        "avg_time": float(gen_720p_time) if gen_720p_time.replace(".", "").isdigit() else 0,
        "throughput": f"480P: {gen_480p_time}s",
        "note": f"720P: {gen_720p_time}s",
    }


def benchmark_kling_api() -> dict:
    """记录可灵 API 响应时间（手动）。"""
    print("\n[Benchmark] 可灵 2.5 Turbo API...")
    api_time = safe_input("  API 从提交到返回视频的平均耗时 (秒): ") or "N/A"

    return {
        "name": "可灵 2.5 Turbo API (5s 视频)",
        "vram_gb": "0 (云端)",
        "avg_time": float(api_time) if api_time.replace(".", "").isdigit() else 0,
        "throughput": "-",
        "note": "云端生成，不占用本地显存",
    }


# ==================== 主流程 ====================


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 性能基准测试（需要 PyTorch + CUDA）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印环境信息，不运行耗时基准测试",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  ShotFlow — 性能基准测试")
    print("=" * 50)

    try:
        import torch
    except ImportError:
        print("[ERROR] PyTorch 未安装，无法运行基准测试。")
        print("        请按 CUDA 版本安装: https://pytorch.org")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("[ERROR] CUDA 不可用，无法运行基准测试。")
        sys.exit(1)

    gpu_info = get_gpu_info()
    print(f"\n[GPU] {gpu_info['gpu_name']}")
    print(f"[VRAM] {gpu_info['total_vram_gb']:.1f} GB")
    print(f"[PyTorch] {gpu_info['torch_version']}")
    print(f"[CUDA] {gpu_info['cuda_version']}")

    if args.dry_run:
        print("\n[DRY RUN] 环境检测通过，不执行耗时基准测试")
        return

    if not sys.stdin.isatty():
        print("\n[ERROR] 非交互环境检测到。")
        print("        完整基准测试需要手动输入显存/耗时数据，无法在 CI 或管道中运行。")
        print("        请加 --dry-run 仅打印环境信息，或在交互式终端中运行。")
        sys.exit(1)

    results = []
    results.append(benchmark_flux_image(gpu_info))
    results.append(benchmark_wan_video(gpu_info))
    results.append(benchmark_kling_api())

    # 生成报告
    report = f"""# ShotFlow — 性能基准测试报告

> 测试日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 测试人: _______________

## 硬件环境

| 项目 | 内容 |
|------|------|
| GPU | {gpu_info['gpu_name']} |
| 显存 | {gpu_info['total_vram_gb']:.1f} GB |
| PyTorch | {gpu_info['torch_version']} |
| CUDA | {gpu_info['cuda_version']} |

## 测试结果

{format_results_table(results)}

## 分析与建议

- **Flux 出图**: _______________
- **Wan2.2 视频**: _______________
- **可灵 API**: _______________
- **瓶颈判断**: _______________
- **优化方向**: _______________

## 结论

- [ ] 本地 RTX 4090 可满足 Flux 出图需求
- [ ] 本地 RTX 4090 可满足 Wan2.2 720P 视频生成需求
- [ ] 需要云端算力辅助
- [ ] 可灵 API 响应时间可接受

---

> 本报告由技术总监填写，作为算力规划的依据。
"""

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n[OK] 报告已保存到 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

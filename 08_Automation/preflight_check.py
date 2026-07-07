#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预飞行环境检查脚本 — 在开始任何生成任务前运行，验证环境就绪
ShotFlow

用法: python preflight_check.py
退出码: 0=全部通过, 1=有警告, 2=有致命错误
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from common import PROJECT_ROOT

# ==================== 配置区 ====================

COMFYUI_DIR = Path(os.getenv("COMFYUI_DIR", os.path.expanduser("~/ComfyUI")))

# 需要检查的模型文件
REQUIRED_MODELS = {
    "Flux.1 Kontext FP8": "models/diffusion_models/flux1-kontext-dev-fp8.safetensors",
    "Wan2.2 I2V High Noise FP8": "models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
    "Wan2.2 I2V Low Noise FP8": "models/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
    "Wan2.2 VAE": "models/vae/wan_2.2_vae.safetensors",
    "UMT5 XXL FP8": "models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
}

# 需要检查的 API 密钥
REQUIRED_API_KEYS = {
    "KLING_API_KEY": "可灵视频生成",
    "ELEVENLABS_API_KEY": "ElevenLabs 配音",
    "SUNO_API_KEY": "Suno 配乐（可选）",
}

# 需要检查的软件
REQUIRED_SOFTWARE = [
    ("python3", "Python 3"),
    ("git", "Git"),
    ("ffmpeg", "FFmpeg"),
]

# 需要检查的 Python 包（显示名 -> import 名）
REQUIRED_PACKAGES = [
    ("torch", "torch"),
    ("requests", "requests"),
    ("Pillow", "PIL"),
]

# 最低硬件要求
MIN_VRAM_GB = 24
MIN_RAM_GB = 32
MIN_DISK_GB = 100

# ==================== 检查函数 ====================


class CheckResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []

    def error(self, msg):
        self.errors.append(msg)
        print(f"  [FAIL] {msg}")

    def warning(self, msg):
        self.warnings.append(msg)
        print(f"  [WARN] {msg}")

    def ok(self, msg):
        self.passed.append(msg)
        print(f"  [OK]   {msg}")

    def exit_code(self):
        if self.errors:
            return 2
        elif self.warnings:
            return 1
        return 0


def check_gpu(result: CheckResult):
    """检查 GPU。"""
    print("\n[1/9] 检查 GPU...")
    try:
        import torch

        if not torch.cuda.is_available():
            result.error("CUDA 不可用，无法运行 GPU 任务")
            return
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        result.ok(f"GPU: {gpu_name} ({vram:.1f} GB)")
        if vram < MIN_VRAM_GB:
            result.warning(f"显存 {vram:.1f}GB 低于推荐 {MIN_VRAM_GB}GB，Wan2.2 可能需要 offload")
        torch_version = torch.__version__
        cuda_version = torch.version.cuda
        result.ok(f"PyTorch {torch_version}, CUDA {cuda_version}")
    except ImportError:
        result.error("PyTorch 未安装")


def check_ram(result: CheckResult):
    """检查内存（跨平台）。"""
    print("\n[2/9] 检查内存...")
    import platform

    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        ram_kb = int(line.split()[1])
                        ram_gb = ram_kb / 1024**2
                        break
        elif system == "Windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            ram_gb = stat.ullTotalPhys / 1024**3
        elif system == "Darwin":
            import subprocess

            output = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            ram_gb = int(output.strip()) / 1024**3
        else:
            result.warning(f"不支持的系统: {system}，跳过内存检查")
            return

        result.ok(f"内存: {ram_gb:.1f} GB")
        if ram_gb < MIN_RAM_GB:
            result.warning(f"内存 {ram_gb:.1f}GB 低于推荐 {MIN_RAM_GB}GB")
    except Exception as e:
        result.warning(f"无法检查内存: {e}")


def check_disk(result: CheckResult):
    """检查磁盘空间。"""
    print("\n[3/9] 检查磁盘空间...")
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)
        free_gb = usage.free / 1024**3
        total_gb = usage.total / 1024**3
        result.ok(f"磁盘: {free_gb:.1f} GB 可用 / {total_gb:.1f} GB 总计")
        if free_gb < MIN_DISK_GB:
            result.warning(f"可用空间 {free_gb:.1f}GB 低于推荐 {MIN_DISK_GB}GB（视频素材占用大）")
    except Exception as e:
        result.warning(f"无法检查磁盘空间: {e}")


def check_software(result: CheckResult):
    """检查必需软件。"""
    print("\n[4/9] 检查软件...")
    for cmd, name in REQUIRED_SOFTWARE:
        path = shutil.which(cmd)
        if path:
            try:
                version = subprocess.check_output(
                    [cmd, "--version"], capture_output=True, text=True, timeout=5
                )
                version_str = version.strip().split("\n")[0][:60]
                result.ok(f"{name}: {version_str}")
            except Exception:
                result.ok(f"{name}: 已安装 ({path})")
        else:
            result.error(f"{name} 未安装（命令: {cmd}）")


def check_packages(result: CheckResult):
    """检查 Python 包。"""
    print("\n[5/9] 检查 Python 包...")
    for pkg_name, import_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
            result.ok(f"Python 包: {pkg_name}")
        except ImportError:
            result.error(f"Python 包未安装: {pkg_name}（pip install {pkg_name}）")


def check_comfyui(result: CheckResult):
    """检查 ComfyUI 安装。"""
    print("\n[6/9] 检查 ComfyUI...")
    if not COMFYUI_DIR.exists():
        result.error(f"ComfyUI 目录不存在: {COMFYUI_DIR}")
        return

    main_py = COMFYUI_DIR / "main.py"
    if main_py.exists():
        result.ok(f"ComfyUI 已安装: {COMFYUI_DIR}")
    else:
        result.error(f"ComfyUI main.py 未找到: {main_py}")
        return

    # 检查 ComfyUI-Manager
    manager_dir = COMFYUI_DIR / "custom_nodes" / "ComfyUI-Manager"
    if manager_dir.exists():
        result.ok("ComfyUI-Manager 已安装")
    else:
        result.warning("ComfyUI-Manager 未安装")

    # 检查 ComfyUI 是否运行
    import requests

    try:
        resp = requests.get("http://127.0.0.1:8188/system_stats", timeout=3)
        if resp.status_code == 200:
            result.ok("ComfyUI 服务正在运行 (port 8188)")
        else:
            result.warning(f"ComfyUI 服务响应异常 (HTTP {resp.status_code})")
    except Exception:
        result.warning("ComfyUI 服务未运行（启动: cd ~/ComfyUI && python main.py --listen）")


def check_models(result: CheckResult):
    """检查模型文件。"""
    print("\n[7/9] 检查模型文件...")
    if not COMFYUI_DIR.exists():
        result.warning("ComfyUI 目录不存在，跳过模型检查")
        return

    for name, rel_path in REQUIRED_MODELS.items():
        model_path = COMFYUI_DIR / rel_path
        if model_path.exists():
            size_gb = model_path.stat().st_size / 1024**3
            result.ok(f"{name}: {size_gb:.1f} GB")
        else:
            result.error(f"模型缺失: {name} ({rel_path})")


def check_api_keys(result: CheckResult):
    """检查 API 密钥。"""
    print("\n[8/9] 检查 API 密钥...")
    for key_name, description in REQUIRED_API_KEYS.items():
        value = os.getenv(key_name, "")
        if value and value != "your_api_key_here":
            result.ok(f"{key_name}: 已配置 ({description})")
        else:
            optional = "可选" in description
            if optional:
                result.warning(f"{key_name}: 未配置 ({description})")
            else:
                result.error(f"{key_name}: 未配置 ({description})")


def check_project_structure(result: CheckResult):
    """检查项目目录结构。"""
    print("\n[9/9] 检查项目目录结构...")
    required_dirs = [
        "01_Assets/Characters",
        "01_Assets/Scenes",
        "01_Assets/Audio",
        "02_Scripts",
        "03_Workflows",
        "04_SOP",
        "05_Output/Rough_Cuts",
        "05_Output/Final",
        "06_Research",
        "07_Team",
        "08_Automation",
    ]
    for d in required_dirs:
        dir_path = PROJECT_ROOT / d
        if dir_path.exists():
            result.ok(f"目录: {d}/")
        else:
            result.error(f"目录缺失: {d}/")


# ==================== 主流程 ====================


def main():
    parser = argparse.ArgumentParser(
        description="ShotFlow — 预飞行环境检查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只执行非环境依赖的检查（项目结构、API 密钥格式），跳过 GPU/模型检查",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  ShotFlow — 预飞行环境检查")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  项目路径: {PROJECT_ROOT}")
    print(f"  ComfyUI 路径: {COMFYUI_DIR}")
    print("=" * 60)

    result = CheckResult()

    if args.dry_run:
        print("\n[DRY RUN] 只检查项目结构与 API 密钥配置")
        check_api_keys(result)
        check_project_structure(result)
        print("\n  [DRY RUN] 跳过 GPU/内存/磁盘/软件/模型检查")
        print(
            f"\n  通过: {len(result.passed)} | 警告: {len(result.warnings)} | 错误: {len(result.errors)}"
        )
        sys.exit(result.exit_code())

    check_gpu(result)
    check_ram(result)
    check_disk(result)
    check_software(result)
    check_packages(result)
    check_comfyui(result)
    check_models(result)
    check_api_keys(result)
    check_project_structure(result)

    # 汇总
    print("\n" + "=" * 60)
    print("  检查结果汇总")
    print("=" * 60)
    print(f"  通过: {len(result.passed)}")
    print(f"  警告: {len(result.warnings)}")
    print(f"  错误: {len(result.errors)}")

    if result.errors:
        print("\n  [致命错误]")
        for e in result.errors:
            print(f"    - {e}")

    if result.warnings:
        print("\n  [警告]")
        for w in result.warnings:
            print(f"    - {w}")

    if not result.errors and not result.warnings:
        print("\n  *** 所有检查通过，可以开始生成任务！ ***")
    elif not result.errors:
        print("\n  有警告但无致命错误，可以谨慎开始。")

    print("=" * 60)

    # 生成报告文件
    report_path = PROJECT_ROOT / "06_Research" / "preflight_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 预飞行检查报告\n\n")
        f.write(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**结果**: {'通过' if not result.errors else '失败'}\n\n")
        f.write("| 类别 | 数量 |\n|------|------|\n")
        f.write(f"| 通过 | {len(result.passed)} |\n")
        f.write(f"| 警告 | {len(result.warnings)} |\n")
        f.write(f"| 错误 | {len(result.errors)} |\n\n")
        if result.errors:
            f.write("## 致命错误\n\n")
            for e in result.errors:
                f.write(f"- {e}\n")
        if result.warnings:
            f.write("\n## 警告\n\n")
            for w in result.warnings:
                f.write(f"- {w}\n")

    print(f"\n报告已保存: {report_path}")

    sys.exit(result.exit_code())


if __name__ == "__main__":
    main()

"""FFmpeg 硬件加速检测 — 合并自 NarratoAI ffmpeg_utils.py + ffmpeg_detector.py。

核心功能：
- 按平台和 GPU 厂商确定硬件加速优先级（HWACCEL_PRIORITY）
- 编码器映射（ENCODER_MAPPING）
- GPU 厂商检测（detect_gpu_vendor）
- 实际编码测试验证（test_hwaccel_method）
- 缓存检测结果，支持重置和强制软件编码

设计变更（相对 NarratoAI 原版）：
- loguru → logging
- 硬编码 "ffmpeg" → 从 settings.FFMPEG_PATH 解析，回退到 PATH
- 合并两个文件为单文件，裁剪冗余的 Windows 平台特定分支
- 去除 emoji 日志和 __main__ 测试块
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# 硬件加速优先级配置（按平台和 GPU 类型）
HWACCEL_PRIORITY: dict[str, dict[str, list[str]]] = {
    "windows": {
        "nvidia": ["cuda", "nvenc", "d3d11va", "dxva2"],
        "amd": ["d3d11va", "dxva2", "amf"],
        "intel": ["qsv", "d3d11va", "dxva2"],
        "unknown": ["d3d11va", "dxva2"],
    },
    "darwin": {
        "apple": ["videotoolbox"],
        "nvidia": ["cuda", "videotoolbox"],
        "amd": ["videotoolbox"],
        "intel": ["videotoolbox"],
        "unknown": ["videotoolbox"],
    },
    "linux": {
        "nvidia": ["cuda", "nvenc", "vaapi"],
        "amd": ["vaapi", "amf"],
        "intel": ["qsv", "vaapi"],
        "unknown": ["vaapi"],
    },
}

# 编码器映射：硬件加速方法 → 对应 H.264 编码器名称
ENCODER_MAPPING: dict[str, str] = {
    "cuda": "h264_nvenc",
    "nvenc": "h264_nvenc",
    "videotoolbox": "h264_videotoolbox",
    "qsv": "h264_qsv",
    "vaapi": "h264_vaapi",
    "amf": "h264_amf",
    # D3D11VA/DXVA2 仅用于解码，编码仍走 libx264
    "d3d11va": "libx264",
    "dxva2": "libx264",
    "software": "libx264",
}


# --------------------------------------------------------------------------- #
# ffmpeg 二进制解析（与 ffmpeg_service 保持一致，避免循环引用）
# --------------------------------------------------------------------------- #


def _resolve_ffmpeg_binary() -> str:
    """解析 ffmpeg 二进制路径：优先 settings.FFMPEG_PATH，否则 PATH 查找。"""
    if settings.FFMPEG_PATH:
        p = Path(settings.FFMPEG_PATH)
        if p.exists():
            return str(p)
        logger.warning("配置的 FFMPEG_PATH 不存在: %s，回退到 PATH 查找", settings.FFMPEG_PATH)
    return shutil.which("ffmpeg") or ""


# --------------------------------------------------------------------------- #
# 全局检测结果缓存
# --------------------------------------------------------------------------- #

_FFMPEG_HW_ACCEL_INFO: dict[str, Any] = {
    "available": False,
    "type": None,
    "encoder": None,
    "hwaccel_args": [],
    "message": "",
    "is_dedicated_gpu": False,
    "fallback_available": False,
    "fallback_encoder": None,
    "platform": None,
    "gpu_vendor": None,
    "tested_methods": [],
}


# --------------------------------------------------------------------------- #
# GPU 厂商检测
# --------------------------------------------------------------------------- #


def detect_gpu_vendor() -> str:
    """检测 GPU 厂商，返回 nvidia / amd / intel / apple / unknown。"""
    system = platform.system().lower()
    try:
        if system == "darwin":
            if platform.machine().lower() in ("arm64", "aarch64"):
                return "apple"
            gpu_info = _get_macos_gpu_info().lower()
            if "nvidia" in gpu_info:
                return "nvidia"
            if "amd" in gpu_info or "radeon" in gpu_info:
                return "amd"
            return "intel"
        elif system == "linux":
            gpu_info = _get_linux_gpu_info().lower()
            if "nvidia" in gpu_info:
                return "nvidia"
            if "amd" in gpu_info or "radeon" in gpu_info:
                return "amd"
            if "intel" in gpu_info:
                return "intel"
        elif system == "windows":
            gpu_info = _get_windows_gpu_info().lower()
            if "nvidia" in gpu_info or "geforce" in gpu_info or "quadro" in gpu_info:
                return "nvidia"
            if "amd" in gpu_info or "radeon" in gpu_info:
                return "amd"
            if "intel" in gpu_info:
                return "intel"
    except Exception as e:
        logger.debug("检测 GPU 厂商失败: %s", e)
    return "unknown"


def _get_windows_gpu_info() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-WmiObject Win32_VideoController | Select-Object Name | Format-List"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", text=True, check=False,
        )
        if not result.stdout.strip():
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", text=True, check=False,
            )
        return result.stdout
    except Exception as e:
        logger.warning("获取 Windows 显卡信息失败: %s", e)
        return "Unknown GPU"


def _get_macos_gpu_info() -> str:
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        if result.returncode == 0:
            return result.stdout
        if platform.machine().lower() in ("arm64", "aarch64"):
            return "Apple Silicon GPU"
        return "Intel Mac GPU"
    except Exception as e:
        logger.debug("获取 macOS GPU 信息失败: %s", e)
        return "unknown"


def _get_linux_gpu_info() -> str:
    try:
        result = subprocess.run(
            "lspci -v -nn | grep -i 'vga\\|display'",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, shell=True, check=False,
        )
        if result.stdout:
            return result.stdout
        result = subprocess.run(
            "glxinfo | grep -i 'vendor\\|renderer'",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, shell=True, check=False,
        )
        if result.stdout:
            return result.stdout
        return "Unknown GPU"
    except Exception as e:
        logger.warning("获取 Linux 显卡信息失败: %s", e)
        return "Unknown GPU"


# --------------------------------------------------------------------------- #
# VAAPI 设备查找
# --------------------------------------------------------------------------- #


def _find_vaapi_device() -> str | None:
    """查找可用的 VAAPI 渲染设备路径。"""
    possible_devices = [
        "/dev/dri/renderD128",
        "/dev/dri/renderD129",
        "/dev/dri/card0",
        "/dev/dri/card1",
    ]
    binary = _resolve_ffmpeg_binary()
    if not binary:
        return None
    for device in possible_devices:
        if not os.path.exists(device):
            continue
        try:
            test_cmd = subprocess.run(
                [binary, "-hide_banner", "-loglevel", "error",
                 "-hwaccel", "vaapi", "-vaapi_device", device,
                 "-f", "lavfi", "-i", "color=black:size=64x64:duration=0.1",
                 "-f", "null", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            if test_cmd.returncode == 0:
                logger.debug("找到可用的 VAAPI 设备: %s", device)
                return device
        except Exception:
            pass
    return None


# --------------------------------------------------------------------------- #
# 测试视频生成与清理
# --------------------------------------------------------------------------- #


def _create_test_video() -> str:
    """创建临时测试视频供硬件加速编码测试用。"""
    binary = _resolve_ffmpeg_binary()
    if not binary:
        return "/dev/null" if os.name != "nt" else "NUL"
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp_path = tmp.name
        tmp.close()
        subprocess.run(
            [binary, "-y", "-f", "lavfi", "-i",
             "color=black:size=320x240:duration=1",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "1", tmp_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return tmp_path
    except Exception as e:
        logger.debug("创建测试视频失败: %s", e)
        return "/dev/null" if os.name != "nt" else "NUL"


def _cleanup_test_video(path: str) -> None:
    try:
        if path not in ("/dev/null", "NUL") and os.path.exists(path):
            os.unlink(path)
    except Exception as e:
        logger.debug("清理测试视频失败: %s", e)


# --------------------------------------------------------------------------- #
# 核心检测逻辑
# --------------------------------------------------------------------------- #


def test_hwaccel_method(method: str, test_input: str) -> bool:
    """实际测试特定硬件加速方法是否可用（编码测试，非仅检查列表）。"""
    binary = _resolve_ffmpeg_binary()
    if not binary:
        return False
    try:
        cmd = [binary, "-hide_banner", "-loglevel", "error"]
        if method == "cuda":
            cmd += ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        elif method == "nvenc":
            cmd += ["-hwaccel", "cuda"]
        elif method == "videotoolbox":
            cmd += ["-hwaccel", "videotoolbox"]
        elif method == "qsv":
            cmd += ["-hwaccel", "qsv"]
        elif method == "vaapi":
            render_device = _find_vaapi_device()
            if render_device:
                cmd += ["-hwaccel", "vaapi", "-vaapi_device", render_device]
            else:
                cmd += ["-hwaccel", "vaapi"]
        elif method == "d3d11va":
            cmd += ["-hwaccel", "d3d11va"]
        elif method == "dxva2":
            cmd += ["-hwaccel", "dxva2"]
        elif method == "amf":
            cmd += ["-hwaccel", "auto"]
        else:
            return False
        cmd += ["-i", test_input, "-f", "null", "-t", "0.1", "-"]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=10,
        )
        if result.returncode == 0:
            logger.debug("硬件加速方法 %s 测试成功", method)
            return True
        logger.debug("硬件加速方法 %s 测试失败: %s", method, result.stderr[:200])
        return False
    except subprocess.TimeoutExpired:
        logger.debug("硬件加速方法 %s 测试超时", method)
        return False
    except Exception as e:
        logger.debug("硬件加速方法 %s 测试异常: %s", method, e)
        return False


def detect_hardware_acceleration() -> dict[str, Any]:
    """检测系统可用的硬件加速器，使用渐进式检测和智能降级。

    流程：检测 GPU 厂商 → 按平台优先级列表逐一实际测试 → 记录首个成功方法。
    结果缓存在全局 _FFMPEG_HW_ACCEL_INFO，避免重复检测。
    """
    global _FFMPEG_HW_ACCEL_INFO

    if _FFMPEG_HW_ACCEL_INFO["type"] is not None:
        return _FFMPEG_HW_ACCEL_INFO

    binary = _resolve_ffmpeg_binary()
    if not binary:
        _FFMPEG_HW_ACCEL_INFO["message"] = "FFmpeg 不可用"
        return _FFMPEG_HW_ACCEL_INFO

    system = platform.system().lower()
    gpu_vendor = detect_gpu_vendor()
    _FFMPEG_HW_ACCEL_INFO["platform"] = system
    _FFMPEG_HW_ACCEL_INFO["gpu_vendor"] = gpu_vendor
    logger.debug("检测硬件加速 - 平台: %s, GPU: %s", system, gpu_vendor)

    # 获取 FFmpeg 支持的硬件加速器列表
    try:
        hwaccels_result = subprocess.run(
            [binary, "-hide_banner", "-hwaccels"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        supported_hwaccels = (
            hwaccels_result.stdout.lower()
            if hwaccels_result.returncode == 0 else ""
        )
    except Exception:
        supported_hwaccels = ""

    test_input = _create_test_video()
    try:
        priority_list = (
            HWACCEL_PRIORITY.get(system, {}).get(gpu_vendor, [])
            or HWACCEL_PRIORITY.get(system, {}).get("unknown", [])
        )
        logger.debug("硬件加速测试优先级: %s", priority_list)

        for method in priority_list:
            # nvenc 可能不在 -hwaccels 列表中（它是编码器而非解码方法）
            if method not in supported_hwaccels and method != "nvenc":
                continue
            _FFMPEG_HW_ACCEL_INFO["tested_methods"].append(method)
            if not test_hwaccel_method(method, test_input):
                continue

            # 找到可用的硬件加速方法
            _FFMPEG_HW_ACCEL_INFO["available"] = True
            _FFMPEG_HW_ACCEL_INFO["type"] = method
            _FFMPEG_HW_ACCEL_INFO["encoder"] = ENCODER_MAPPING.get(method, "libx264")

            if method == "cuda":
                _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = [
                    "-hwaccel", "cuda", "-hwaccel_output_format", "cuda"
                ]
            elif method == "nvenc":
                # 纯 NVENC 编码器：不添加解码 hwaccel 参数，避免滤镜链兼容问题
                _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = []
            elif method == "videotoolbox":
                _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = ["-hwaccel", "videotoolbox"]
            elif method == "qsv":
                _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = ["-hwaccel", "qsv"]
            elif method == "vaapi":
                render_device = _find_vaapi_device()
                if render_device:
                    _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = [
                        "-hwaccel", "vaapi", "-vaapi_device", render_device
                    ]
                else:
                    _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = ["-hwaccel", "vaapi"]
            elif method in ("d3d11va", "dxva2"):
                _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = ["-hwaccel", method]
            elif method == "amf":
                _FFMPEG_HW_ACCEL_INFO["hwaccel_args"] = ["-hwaccel", "auto"]

            _FFMPEG_HW_ACCEL_INFO["is_dedicated_gpu"] = gpu_vendor in ("nvidia", "amd")
            _FFMPEG_HW_ACCEL_INFO["message"] = f"使用 {method} 硬件加速 ({gpu_vendor} GPU)"
            logger.info("硬件加速检测成功: %s (%s)", method, gpu_vendor)
            break

        if not _FFMPEG_HW_ACCEL_INFO["available"]:
            _FFMPEG_HW_ACCEL_INFO["fallback_available"] = True
            _FFMPEG_HW_ACCEL_INFO["fallback_encoder"] = "libx264"
            _FFMPEG_HW_ACCEL_INFO["message"] = (
                f"未找到可用的硬件加速，使用软件编码 (平台: {system}, GPU: {gpu_vendor})"
            )
            logger.debug("未检测到硬件加速，使用软件编码")
    finally:
        _cleanup_test_video(test_input)

    return _FFMPEG_HW_ACCEL_INFO


# --------------------------------------------------------------------------- #
# 公共查询接口
# --------------------------------------------------------------------------- #


def is_ffmpeg_hwaccel_available() -> bool:
    """检查是否有可用的硬件加速。"""
    if _FFMPEG_HW_ACCEL_INFO["type"] is None:
        detect_hardware_acceleration()
    return _FFMPEG_HW_ACCEL_INFO["available"]


def get_ffmpeg_hwaccel_type() -> str | None:
    """获取硬件加速类型，不支持时返回 None。"""
    if _FFMPEG_HW_ACCEL_INFO["type"] is None:
        detect_hardware_acceleration()
    return _FFMPEG_HW_ACCEL_INFO["type"] if _FFMPEG_HW_ACCEL_INFO["available"] else None


def get_ffmpeg_hwaccel_encoder() -> str | None:
    """获取硬件加速编码器，不支持时返回 None。"""
    if _FFMPEG_HW_ACCEL_INFO["type"] is None:
        detect_hardware_acceleration()
    return _FFMPEG_HW_ACCEL_INFO["encoder"] if _FFMPEG_HW_ACCEL_INFO["available"] else None


def get_ffmpeg_hwaccel_args() -> list[str]:
    """获取硬件加速参数列表（用于 ffmpeg -i 之前）。"""
    if _FFMPEG_HW_ACCEL_INFO["type"] is None:
        detect_hardware_acceleration()
    return list(_FFMPEG_HW_ACCEL_INFO["hwaccel_args"])


def get_ffmpeg_hwaccel_info() -> dict[str, Any]:
    """获取完整的硬件加速信息字典。"""
    if _FFMPEG_HW_ACCEL_INFO["type"] is None:
        detect_hardware_acceleration()
    return dict(_FFMPEG_HW_ACCEL_INFO)


def get_optimal_ffmpeg_encoder() -> str:
    """获取最优编码器：优先硬件加速编码器，否则 libx264。"""
    if _FFMPEG_HW_ACCEL_INFO["type"] is None:
        detect_hardware_acceleration()
    if _FFMPEG_HW_ACCEL_INFO["available"]:
        return _FFMPEG_HW_ACCEL_INFO["encoder"]
    if _FFMPEG_HW_ACCEL_INFO["fallback_available"]:
        return _FFMPEG_HW_ACCEL_INFO["fallback_encoder"] or "libx264"
    return "libx264"


# --------------------------------------------------------------------------- #
# 控制
# --------------------------------------------------------------------------- #


def force_software_encoding() -> None:
    """强制使用软件编码，禁用硬件加速。"""
    global _FFMPEG_HW_ACCEL_INFO
    _FFMPEG_HW_ACCEL_INFO.update({
        "available": False,
        "type": "software",
        "encoder": "libx264",
        "hwaccel_args": [],
        "message": "强制使用软件编码",
        "is_dedicated_gpu": False,
        "fallback_available": True,
        "fallback_encoder": "libx264",
    })
    logger.info("已强制切换到软件编码模式")


def reset_hwaccel_detection() -> None:
    """重置检测结果，强制下次调用时重新检测。"""
    global _FFMPEG_HW_ACCEL_INFO
    _FFMPEG_HW_ACCEL_INFO = {
        "available": False,
        "type": None,
        "encoder": None,
        "hwaccel_args": [],
        "message": "",
        "is_dedicated_gpu": False,
        "fallback_available": False,
        "fallback_encoder": None,
        "platform": None,
        "gpu_vendor": None,
        "tested_methods": [],
    }
    logger.info("硬件加速检测已重置，将重新检测")


# --------------------------------------------------------------------------- #
# FFmpeg 引擎发现（移植自 ffmpeg_detector.py，用于诊断）
# --------------------------------------------------------------------------- #


def _parse_hwaccels(output: str) -> list[str]:
    """解析 `ffmpeg -hwaccels` 输出为方法名列表。"""
    values: list[str] = []
    for line in output.splitlines():
        item = line.strip().lower()
        if not item or item.startswith("hardware acceleration"):
            continue
        if re.fullmatch(r"[a-z0-9_]+", item):
            values.append(item)
    return sorted(set(values))


def _parse_ffmpeg_table_names(output: str) -> set[str]:
    """解析 `ffmpeg -encoders` / `ffmpeg -filters` 输出为名称集合。"""
    names: set[str] = set()
    for line in output.splitlines():
        match = re.match(r"\s*[A-Z.]{2,}\s+([A-Za-z0-9_]+)\b", line)
        if match:
            names.add(match.group(1).lower())
    return names


def _run_optional(
    args: list[str], timeout: int = 15, max_output_chars: int = 1200,
) -> tuple[bool, str]:
    """执行命令，返回 (是否成功, 输出文本)，异常不抛出。"""
    try:
        result = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as exc:
        return False, str(exc)
    output = "\n".join(part for part in (result.stderr, result.stdout) if part)
    if max_output_chars > 0:
        output = output[-max_output_chars:]
    return result.returncode == 0, output


def _hardware_candidates() -> list[tuple[str, str, list[str]]]:
    """按当前平台返回硬件编码候选列表 (type, encoder, encoder_args)。"""
    system = platform.system().lower()
    if system == "darwin":
        return [
            ("videotoolbox", "h264_videotoolbox", ["-c:v", "h264_videotoolbox", "-q:v", "65"]),
        ]
    if system == "windows":
        return [
            ("nvenc", "h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "fast"]),
            ("qsv", "h264_qsv", ["-c:v", "h264_qsv", "-preset", "fast"]),
            ("amf", "h264_amf", ["-c:v", "h264_amf"]),
        ]
    return [
        ("nvenc", "h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "fast"]),
        ("qsv", "h264_qsv", ["-vf", "format=nv12", "-c:v", "h264_qsv"]),
        ("vaapi", "h264_vaapi", ["-vf", "format=nv12,hwupload", "-c:v", "h264_vaapi"]),
    ]


def detect_hardware_encoding(ffmpeg_path: str, encoders: set[str]) -> dict[str, Any]:
    """对指定 ffmpeg 二进制进行硬件编码实际测试，返回首个通过的方法。"""
    tested: list[dict[str, Any]] = []
    for accel_type, encoder, encoder_args in _hardware_candidates():
        if encoder.lower() not in encoders:
            tested.append({
                "type": accel_type, "encoder": encoder,
                "available": False,
                "message": "Encoder not listed by this FFmpeg build",
            })
            continue
        cmd = [
            ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=duration=0.5:size=128x72:rate=15",
            "-frames:v", "5", *encoder_args, "-pix_fmt", "yuv420p",
            "-f", "null", "-",
        ]
        ok, message = _run_optional(cmd, timeout=18)
        tested.append({
            "type": accel_type, "encoder": encoder,
            "available": ok,
            "message": "Hardware encode test passed" if ok else message,
        })
        if ok:
            return {
                "available": True, "type": accel_type, "encoder": encoder,
                "message": "Hardware encode test passed", "tested": tested,
            }
    return {
        "available": False, "type": None, "encoder": None,
        "message": "No hardware encoder passed the runtime test", "tested": tested,
    }


def validate_ffmpeg_engine(ffmpeg_path: str) -> dict[str, Any]:
    """对指定 ffmpeg 路径进行完整能力检测（版本/编码器/滤镜/硬件加速/字幕烧录）。"""
    path = str(Path(ffmpeg_path).expanduser().resolve())
    report: dict[str, Any] = {
        "path": path,
        "ffmpeg_available": False,
        "version_line": "",
        "hwaccels": [],
        "hardware_acceleration": {
            "available": False, "type": None, "encoder": None,
            "message": "", "tested": [],
        },
        "software_encoder_available": False,
        "errors": [],
    }

    available, version_output = _run_optional([path, "-version"], timeout=8)
    report["ffmpeg_available"] = available
    if not available:
        report["errors"].append("FFmpeg is not executable or failed -version")
        return report
    report["version_line"] = (version_output.splitlines()[0] if version_output else "")

    ok, hwaccel_output = _run_optional(
        [path, "-hide_banner", "-hwaccels"], timeout=10, max_output_chars=0,
    )
    if ok:
        report["hwaccels"] = _parse_hwaccels(hwaccel_output)
    else:
        report["errors"].append(f"Failed to list hwaccels: {hwaccel_output}")

    ok, encoders_output = _run_optional(
        [path, "-hide_banner", "-encoders"], timeout=10, max_output_chars=0,
    )
    encoders = _parse_ffmpeg_table_names(encoders_output) if ok else set()
    report["software_encoder_available"] = "libx264" in encoders

    report["hardware_acceleration"] = detect_hardware_encoding(path, encoders)
    return report

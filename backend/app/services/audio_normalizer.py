"""音频响度标准化工具 — 移植自 NarratoAI audio_normalizer.py。

使用 FFmpeg loudnorm 滤镜进行两遍式 LUFS 标准化，保证混音时各轨响度一致。
当 loudnorm 不可用时，回退到 pydub 的简单 dBFS 标准化。

设计变更（相对 NarratoAI 原版）：
- loguru → logging
- moviepy / pydub / numpy 改为可选导入，缺失时跳过对应功能而非崩溃
- 硬编码 "ffmpeg" → 从 settings.FFMPEG_PATH 解析
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# 可选依赖：moviepy / pydub / numpy 缺失时跳过 RMS 分析和简单标准化
try:
    from moviepy import AudioFileClip  # noqa: F401

    _HAS_MOVIEPY = True
except ImportError:
    _HAS_MOVIEPY = False

try:
    from pydub import AudioSegment

    _HAS_PYDUB = True
except ImportError:
    _HAS_PYDUB = False

try:
    import numpy as np  # noqa: F401

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _resolve_ffmpeg_binary() -> str:
    """解析 ffmpeg 二进制路径：优先 settings.FFMPEG_PATH，否则 PATH 查找。"""
    if settings.FFMPEG_PATH:
        p = Path(settings.FFMPEG_PATH)
        if p.exists():
            return str(p)
    return shutil.which("ffmpeg") or ""


class AudioNormalizer:
    """音频响度分析和标准化工具。"""

    def __init__(self):
        self.target_lufs = -23.0  # 广播标准目标响度 (LUFS)
        self.max_peak = -1.0      # 最大峰值 (dBFS)

    def analyze_audio_lufs(self, audio_path: str) -> Optional[float]:
        """使用 FFmpeg loudnorm 滤镜分析音频的 LUFS 响度。

        返回 input_i（整体响度），分析失败返回 None。
        """
        if not os.path.exists(audio_path):
            logger.error("音频文件不存在: %s", audio_path)
            return None

        binary = _resolve_ffmpeg_binary()
        if not binary:
            logger.error("ffmpeg 不可用，无法分析 LUFS")
            return None

        try:
            cmd = [
                binary, "-hide_banner", "-nostats",
                "-i", audio_path,
                "-af", "loudnorm=I=-23:TP=-1:LRA=7:print_format=json",
                "-f", "null", "-",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False,
            )

            # loudnorm 的 JSON 输出在 stderr 中
            stderr_lines = result.stderr.split("\n")
            json_start = False
            json_lines: list[str] = []
            for line in stderr_lines:
                if line.strip() == "{":
                    json_start = True
                if json_start:
                    json_lines.append(line)
                if line.strip() == "}":
                    break

            if json_lines:
                loudness_data = json.loads("\n".join(json_lines))
                input_i = float(loudness_data.get("input_i", 0))
                logger.info(
                    "音频 %s 的 LUFS: %s",
                    os.path.basename(audio_path), input_i,
                )
                return input_i
        except Exception as e:
            logger.error("分析音频 LUFS 失败: %s", e)

        return None

    def get_audio_rms(self, audio_path: str) -> Optional[float]:
        """计算音频的 RMS 值作为响度的简单估计。

        依赖 pydub + numpy，缺失时返回 None。
        """
        if not (_HAS_PYDUB and _HAS_NUMPY):
            logger.debug("pydub 或 numpy 不可用，跳过 RMS 分析")
            return None
        try:
            import numpy as _np
            audio = AudioSegment.from_file(audio_path)
            samples = _np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            rms = _np.sqrt(_np.mean(samples ** 2))
            if rms > 0:
                rms_db = 20 * _np.log10(rms / (2 ** 15))
                return rms_db
            return -60.0  # 静音
        except Exception as e:
            logger.error("计算音频 RMS 失败: %s", e)
            return None

    def normalize_audio_lufs(
        self, input_path: str, output_path: str,
        target_lufs: Optional[float] = None,
    ) -> bool:
        """使用 FFmpeg loudnorm 滤镜两遍式标准化音频响度。

        第一遍分析响度参数，第二遍用 measured 值进行线性标准化。
        失败时回退到 pydub 简单标准化。
        """
        if target_lufs is None:
            target_lufs = self.target_lufs

        binary = _resolve_ffmpeg_binary()
        if not binary:
            logger.error("ffmpeg 不可用，无法标准化音频")
            return False

        try:
            # 第一遍：分析
            analyze_cmd = [
                binary, "-hide_banner", "-nostats",
                "-i", input_path,
                "-af", f"loudnorm=I={target_lufs}:TP={self.max_peak}:LRA=7:print_format=json",
                "-f", "null", "-",
            ]
            analyze_result = subprocess.run(
                analyze_cmd, capture_output=True, text=True, check=False,
            )

            stderr_lines = analyze_result.stderr.split("\n")
            json_start = False
            json_lines: list[str] = []
            for line in stderr_lines:
                if line.strip() == "{":
                    json_start = True
                if json_start:
                    json_lines.append(line)
                if line.strip() == "}":
                    break

            if not json_lines:
                logger.warning("无法获取音频分析数据，使用简单标准化")
                return self._simple_normalize(input_path, output_path)

            loudness_data = json.loads("\n".join(json_lines))

            # 第二遍：应用标准化（用第一遍的 measured 值做线性校正）
            normalize_cmd = [
                binary, "-y", "-hide_banner",
                "-i", input_path,
                "-af", (
                    f"loudnorm=I={target_lufs}:TP={self.max_peak}:LRA=7:"
                    f'measured_I={loudness_data["input_i"]}:'
                    f'measured_LRA={loudness_data["input_lra"]}:'
                    f'measured_TP={loudness_data["input_tp"]}:'
                    f'measured_thresh={loudness_data["input_thresh"]}'
                ),
                "-ar", "44100",  # 统一采样率
                "-ac", "2",      # 统一为立体声
                output_path,
            ]
            subprocess.run(
                normalize_cmd, capture_output=True, text=True, check=True,
            )
            logger.info("音频标准化完成: %s", output_path)
            return True

        except subprocess.CalledProcessError as e:
            logger.error("FFmpeg 标准化失败: %s", e)
            return self._simple_normalize(input_path, output_path)
        except Exception as e:
            logger.error("音频标准化失败: %s", e)
            return False

    def _simple_normalize(self, input_path: str, output_path: str) -> bool:
        """pydub 简单 dBFS 标准化（loudnorm 不可用时的兜底）。

        依赖 pydub，缺失时返回 False。
        """
        if not _HAS_PYDUB:
            logger.error("pydub 不可用，无法执行简单标准化")
            return False
        try:
            audio = AudioSegment.from_file(input_path)
            target_dBFS = -20.0
            change_in_dBFS = target_dBFS - audio.dBFS
            normalized_audio = audio.apply_gain(change_in_dBFS)
            normalized_audio.export(output_path, format="mp3", bitrate="128k")
            logger.info("简单音频标准化完成: %s", output_path)
            return True
        except Exception as e:
            logger.error("简单音频标准化失败: %s", e)
            return False

    def calculate_volume_adjustment(
        self, tts_path: str, original_path: str,
    ) -> Tuple[float, float]:
        """计算 TTS 和原声的音量调整系数，使它们达到相似响度。

        返回 (TTS 音量系数, 原声音量系数)，分析失败时返回默认值。
        """
        tts_lufs = self.analyze_audio_lufs(tts_path)
        original_lufs = self.analyze_audio_lufs(original_path)

        # LUFS 分析失败时用 RMS 兜底
        if tts_lufs is None:
            tts_lufs = self.get_audio_rms(tts_path)
        if original_lufs is None:
            original_lufs = self.get_audio_rms(original_path)

        if tts_lufs is None or original_lufs is None:
            logger.warning("无法分析音频响度，使用默认音量设置")
            return 0.7, 1.0

        target_lufs = -20.0
        tts_adjustment = 10 ** ((target_lufs - tts_lufs) / 20)
        original_adjustment = 10 ** ((target_lufs - original_lufs) / 20)

        # 限制调整范围，避免过度放大
        tts_adjustment = max(0.1, min(2.0, tts_adjustment))
        original_adjustment = max(0.1, min(3.0, original_adjustment))

        logger.info(
            "音量调整建议 - TTS: %.2f, 原声: %.2f",
            tts_adjustment, original_adjustment,
        )
        return tts_adjustment, original_adjustment


def normalize_audio_for_mixing(
    audio_path: str, output_dir: str,
    target_lufs: float = -20.0,
) -> Optional[str]:
    """为音频混合准备标准化的音频文件。

    对输入音频进行 LUFS 标准化，输出到指定目录。
    失败时返回 None，调用方应使用原始音频。
    """
    if not audio_path or not os.path.exists(audio_path):
        return None

    normalizer = AudioNormalizer()
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{base_name}_normalized.mp3")

    if normalizer.normalize_audio_lufs(audio_path, output_path, target_lufs):
        return output_path
    return None

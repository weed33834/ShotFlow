"""可灵视频生成服务 — 封装对 08_Automation/kling_video_api.py 的调用。

对应 render_queue.py 的 run_kling_task（第 233-252 行），
改为函数形式，返回结构化结果，便于 Celery 任务处理。
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
KLING_SCRIPT = PROJECT_ROOT / "08_Automation" / "kling_video_api.py"


class KlingError(Exception):
    """可灵调用异常。"""


def run_kling_task(
    shot_id: str,
    prompt: str,
    start_image: Optional[str] = None,
    end_image: Optional[str] = None,
) -> dict:
    """执行可灵视频生成。

    通过环境变量向 kling_video_api.py 传参（沿用原脚本约定）：
        KLING_PROMPT / KLING_SHOT_ID / KLING_START_IMAGE / KLING_END_IMAGE

    Returns:
        {success, output_path, error, returncode}
    """
    if settings.SIMULATE_MODE:
        logger.info("[模拟] 可灵任务 shot=%s prompt=%s...", shot_id, prompt[:40])
        return {
            "success": True,
            "output_path": f"05_Output/Rough_Cuts/sim_kling_{shot_id}.mp4",
            "error": "",
            "returncode": 0,
        }

    if not KLING_SCRIPT.exists():
        raise KlingError(f"可灵脚本不存在: {KLING_SCRIPT}")

    env = {
        **os.environ,
        "KLING_PROMPT": prompt,
        "KLING_SHOT_ID": shot_id,
    }
    if start_image:
        env["KLING_START_IMAGE"] = start_image
    if end_image:
        env["KLING_END_IMAGE"] = end_image

    try:
        result = subprocess.run(
            [sys.executable, str(KLING_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "output_path": "",
            "error": result.stderr[-500:] if result.stderr else "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise KlingError("可灵生成超时（>600s）")

"""service 层测试 — 模拟模式下不依赖外部服务。"""

from app.services.audio_service import run_music_task, run_tts_task
from app.services.comfyui_service import run_comfyui_task
from app.services.kling_service import run_kling_task


def test_comfyui_simulate_mode():
    """模拟模式下 ComfyUI 任务直接返回成功。"""
    result = run_comfyui_task(task_type="keyframe", prompt="Ava walking", seed=12345)
    assert result["status"] == "completed"
    assert "output_path" in result
    assert result["prompt_id"].startswith("sim_")


def test_kling_simulate_mode():
    """模拟模式下可灵任务直接返回成功。"""
    result = run_kling_task(shot_id="S01_04", prompt="complex shot")
    assert result["success"] is True
    assert "output_path" in result


def test_tts_simulate_mode():
    """模拟模式下 TTS 任务直接返回成功。"""
    result = run_tts_task(text="我要找到奇点核心", role="ava")
    assert result["success"] is True


def test_music_simulate_mode():
    """模拟模式下配乐任务直接返回成功。"""
    result = run_music_task(prompt="melancholic ambient", title="Echo Theme")
    assert result["success"] is True

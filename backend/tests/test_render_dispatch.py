"""渲染任务分发测试 — 验证 extra.provider 路由到对应 adapter。

SIMULATE_MODE 下所有 adapter 短路返回模拟结果，端到端可跑。
"""

import pytest
from app.models.pipeline import RenderTask
from app.tasks.render_tasks import _dispatch


def _make_task(db_session, task_type="video_i2v", extra=None):
    """造一个 running 态 RenderTask，extra 由调用方指定。"""
    task = RenderTask(
        task_type=task_type,
        prompt="测试镜头",
        status="running",
        extra=extra or {},
    )
    db_session.add(task)
    db_session.commit()
    return task


def test_dispatch_with_provider_extra(db_session):
    """extra.provider=hunyuan_video 时走对应 adapter，返回 sim_hunyuan 路径。"""
    task = _make_task(
        db_session,
        task_type="video_i2v",
        extra={"provider": "hunyuan_video", "seed": 7},
    )
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    assert "hunyuan" in result["output_path"]


def test_dispatch_default_provider(db_session):
    """extra 无 provider 时默认 wan_i2v。"""
    task = _make_task(db_session, task_type="video_i2v", extra={"seed": 1})
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    assert "wan_i2v" in result["output_path"]


def test_dispatch_unknown_provider_raises(db_session):
    """extra.provider=unknown 时 _dispatch 抛 ValueError。"""
    task = _make_task(
        db_session,
        task_type="video_i2v",
        extra={"provider": "unknown"},
    )
    with pytest.raises(ValueError):
        _dispatch(db_session, task)


def test_dispatch_keyframe_stays_on_comfyui(db_session):
    """keyframe 不走 provider 路由，仍由 comfyui_service 处理（向后兼容）。"""
    task = _make_task(db_session, task_type="keyframe", extra={"seed": 42})
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    assert result["prompt_id"].startswith("sim_")
    # keyframe 走 comfyui_service SIMULATE 路径，输出 .png（与原行为一致）
    assert result["output_path"].endswith(".png")


def test_dispatch_video_t2v_via_adapter(db_session):
    """video_t2v 同样走 adapter 路由（默认 wan_i2v）。"""
    task = _make_task(db_session, task_type="video_t2v", extra={"seed": 9})
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    assert "wan_i2v" in result["output_path"]


def test_dispatch_provider_failure_raises(db_session, monkeypatch):
    """显式 provider 的 adapter.poll 返回 failed 时 _dispatch 抛 RuntimeError（不回退）。

    显式 provider 路径：用户明确指定，失败直接抛交由 mark_failed 处理，不擅自换 provider。
    （自动选择路径的失败回退由 test_phase2_integration 覆盖。）
    """
    from app.services.provider_adapters import get_adapter

    adapter = get_adapter("wan_i2v")
    monkeypatch.setattr(adapter, "poll", lambda job_id: "failed")
    task = _make_task(
        db_session,
        task_type="video_i2v",
        extra={"seed": 1, "provider": "wan_i2v"},  # 显式指定，失败不回退
    )
    with pytest.raises(RuntimeError, match="执行失败"):
        _dispatch(db_session, task)

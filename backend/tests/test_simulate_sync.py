"""SIMULATE 模式、无 Celery broker 时，enqueue_task 应退化为进程内同步执行。

这是零依赖本地开发/演示的关键能力：仅 uvicorn + SQLite 即可跑通渲染队列，
无需 Redis / Celery worker。验证见 app/services/queue_service.py:_dispatch_to_celery。
"""

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.pipeline import RenderTask
from app.models.project import Project
from app.schemas.pipeline import RenderTaskCreate
from app.services.queue_service import enqueue_task


def test_enqueue_simulate_runs_synchronously_without_broker(db_session, monkeypatch):
    """无 broker 时 SIMULATE 任务应直接 completed（进度 100，无错误）。"""
    import app.db.session as db_mod
    import app.tasks.render_tasks as render_tasks_mod
    from app.tasks import render_tasks as rt

    # 让后台任务打开的 SessionLocal 与测试会话共享同一内存库，
    # 否则 SQLite 内存库各自独立，run_render_task.run 看不到刚创建的 task。
    shared_engine = db_session.get_bind()
    SharedSessionLocal = sessionmaker(bind=shared_engine, autoflush=False, future=True)
    monkeypatch.setattr(db_mod, "SessionLocal", SharedSessionLocal)
    monkeypatch.setattr(render_tasks_mod, "SessionLocal", SharedSessionLocal)

    # 模拟 broker 不可达：让 .delay 抛异常，触发 _dispatch_to_celery 的 SIMULATE 同步回退。
    # 覆盖 conftest 中让 .delay 返回假结果的默认 mock（默认 mock 用于"异步派发"类用例）。
    def _delay_raises(*args, **kwargs):
        raise RuntimeError("Celery broker 不可达（测试模拟）")

    monkeypatch.setattr(rt.run_render_task, "delay", _delay_raises)

    project = Project(title="SIM测试项目", status="pre_production")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = enqueue_task(
        db_session,
        RenderTaskCreate(
            task_type="keyframe",
            prompt="测试镜头",
            project_id=project.id,
            extra={"seed": 1},
        ),
    )
    assert task.status == "completed"
    assert task.progress == 100
    assert task.error == ""


def test_enqueue_simulate_non_keyframe_also_completes(db_session, monkeypatch):
    """video_i2v 等走 provider 路由的任务在 SIMULATE 下同样同步完成。"""
    import app.db.session as db_mod
    import app.tasks.render_tasks as render_tasks_mod
    from app.tasks import render_tasks as rt

    shared_engine = db_session.get_bind()
    SharedSessionLocal = sessionmaker(bind=shared_engine, autoflush=False, future=True)
    monkeypatch.setattr(db_mod, "SessionLocal", SharedSessionLocal)
    monkeypatch.setattr(render_tasks_mod, "SessionLocal", SharedSessionLocal)

    # 同上：模拟 broker 不可达，触发 SIMULATE 同步回退
    def _delay_raises(*args, **kwargs):
        raise RuntimeError("Celery broker 不可达（测试模拟）")

    monkeypatch.setattr(rt.run_render_task, "delay", _delay_raises)

    project = Project(title="SIM测试项目2", status="pre_production")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = enqueue_task(
        db_session,
        RenderTaskCreate(
            task_type="video_i2v",
            prompt="飞船起飞",
            project_id=project.id,
            extra={"seed": 3},
        ),
    )
    assert task.status == "completed"
    assert "wan_i2v" in (task.extra or {}).get("output_path", "")

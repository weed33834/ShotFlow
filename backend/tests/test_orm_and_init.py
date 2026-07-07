"""ORM 模型与 init_db 测试 — 模块 E + G。"""

import os

import pytest

# ===== 模块 E：Shot 复合唯一约束 =====


def test_shot_project_code_unique(db_session):
    """同项目内 shot_code 唯一，跨项目可重复。"""
    from app.models.production import Shot
    from app.models.project import Project

    p1 = Project(title="项目1", subtitle="P1", status="planning")
    p2 = Project(title="项目2", subtitle="P2", status="planning")
    db_session.add_all([p1, p2])
    db_session.commit()

    # 同项目同 shot_code 应违反唯一约束
    db_session.add(Shot(project_id=p1.id, shot_code="S01_01"))
    db_session.commit()
    db_session.add(Shot(project_id=p1.id, shot_code="S01_01"))
    with pytest.raises(Exception):  # IntegrityError 或其子类
        db_session.commit()
    db_session.rollback()

    # 跨项目同 shot_code 允许
    db_session.add(Shot(project_id=p2.id, shot_code="S01_01"))
    db_session.commit()


# ===== 模块 E：RenderTask relationship =====


def test_render_task_relationship_to_shot(db_session):
    """RenderTask 应能通过 relationship 导航到 Shot/Project。"""
    from app.models.pipeline import RenderTask
    from app.models.production import Shot
    from app.models.project import Project

    p = Project(title="关系测试", subtitle="rel", status="planning")
    db_session.add(p)
    db_session.commit()
    s = Shot(project_id=p.id, shot_code="S99_01")
    db_session.add(s)
    db_session.commit()
    t = RenderTask(project_id=p.id, shot_id=s.id, task_type="video_i2v")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)

    # relationship 导航
    assert t.shot is not None
    assert t.shot.shot_code == "S99_01"
    assert t.project is not None
    assert t.project.title == "关系测试"


# ===== 模块 G：init_db.py 用 2.0 风格 select =====


def test_init_db_seed_uses_select_style(capsys, monkeypatch):
    """init_db.py --seed 应使用 SQLAlchemy 2.0 select 风格而非 legacy Query。

    通过 AST 解析检查不含 db.query() 调用（legacy API 在 2.0 产生 deprecation warning）。
    """
    import ast

    init_db_path = os.path.join(os.path.dirname(__file__), "..", "init_db.py")
    with open(init_db_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    # 收集所有 db.query(...) 调用
    query_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                node.func.attr == "query"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "db"
            ):
                query_calls.append(node.lineno)
    assert (
        not query_calls
    ), f"init_db.py 第 {query_calls} 行仍使用 legacy db.query()，应改为 select() 风格"
    # 同时确认已使用 select() 风格
    source = open(init_db_path, encoding="utf-8").read()
    assert "select(" in source, "init_db.py 应使用 select() 风格"


# ===== 模块 G：db session pool_recycle（PostgreSQL）=====


def test_pg_engine_has_pool_recycle():
    """PostgreSQL 引擎应配置 pool_recycle 避免长连接被服务端断开。"""
    # 检查 _build_engine 在 PG 场景下带 pool_recycle
    import inspect

    from app.db import session as session_mod

    source = inspect.getsource(session_mod._build_engine)
    assert "pool_recycle" in source, "PG 引擎未配置 pool_recycle"


# ===== 模块 G：enqueue_task 派发失败标记 failed =====


def test_enqueue_task_marks_failed_on_dispatch_error(db_session, monkeypatch):
    """enqueue_task 派发 Celery 失败时应将任务标记为 failed，而非静默滞留 pending。"""
    from app.models.pipeline import RenderTask
    from app.services import queue_service as qs

    # 构造一个 failed 任务（retry_task 仅对 failed/cancelled 重试）
    task = RenderTask(
        task_type="video_i2v",
        prompt="test",
        status="failed",
        priority=0,
        error="previous error",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    task_id = task.id

    # 模拟 run_render_task.delay 抛异常（如 Redis 不可达）
    class _Boom:
        def delay(self, *a, **k):
            raise RuntimeError("redis connection refused")

    monkeypatch.setattr(qs, "run_render_task", _Boom())

    # 重新派发应捕获异常并标记 failed
    qs.retry_task(db_session, task_id)
    db_session.refresh(task)
    # 派发失败后任务应标记为 failed，而非滞留 pending
    assert task.status == "failed"
    assert "dispatch" in task.error_class or "派发" in task.error or task.error_class

"""测试夹具 — 使用 SQLite 内存数据库隔离测试。

注意：DATABASE_URL 必须在导入 app.db.session 之前指向 SQLite，
否则模块加载时会按生产默认值尝试构建 PostgreSQL 引擎并失败。
所以这里先把环境变量钉到 SQLite，再 import 应用代码。
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
# 测试用固定密钥，避免触发生产环境的默认密钥拦截（config._guard_secret_key）
os.environ.setdefault("SECRET_KEY", "ci-test-secret-not-for-production-use")

import app.models  # noqa: F401  # 注册所有模型
import pytest
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

_SEED_ADMIN_USERNAME = "ci_admin"
_SEED_ADMIN_PASSWORD = "ci-admin-pass"
_SEED_ADMIN_EMAIL = "ci_admin@shotflow.test"


@pytest.fixture()
def db_session():
    """提供独立的 SQLite 内存会话。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, future=True)
    Base.metadata.create_all(engine)
    session = TestingSession()
    # 预种子一个超级管理员，供测试通过管理员权限创建其他用户
    admin = User(
        username=_SEED_ADMIN_USERNAME,
        email=_SEED_ADMIN_EMAIL,
        hashed_password=hash_password(_SEED_ADMIN_PASSWORD),
        full_name="CI Admin",
        role="admin",
        is_superuser=True,
    )
    session.add(admin)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _mock_celery_delay(monkeypatch):
    """测试环境 mock Celery 派发，避免真实连接 Redis broker。

    默认让 run_render_task.delay 返回假 AsyncResult（含 .id）。
    patch 的是 delay 方法本身，单个测试可再 monkeypatch 同一目标让 delay 抛异常
    或返回不同 id，后执行的 patch 会覆盖本默认值。
    """
    from app.tasks import render_tasks

    class _FakeAsyncResult:
        id = "fake-celery-task-id"

    def _fake_delay(*args, **kwargs):
        return _FakeAsyncResult()

    monkeypatch.setattr(render_tasks.run_render_task, "delay", _fake_delay)


@pytest.fixture()
def client(db_session):
    """提供 FastAPI TestClient，数据库依赖被替换为测试会话。"""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_admin_headers(client):
    """返回种子管理员的 Authorization 头。"""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": _SEED_ADMIN_USERNAME, "password": _SEED_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

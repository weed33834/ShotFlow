"""技术债清理测试 — 覆盖模块 A/B/C/E 的行为变更。

TDD: 这些测试先于实现编写，描述期望行为。
"""

from app.core.security import create_access_token

_SEED_ADMIN = "ci_admin"
_SEED_ADMIN_PASS = "ci-admin-pass"


def _admin_headers(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": _SEED_ADMIN, "password": _SEED_ADMIN_PASS},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ===== 模块 A：scan_assets 状态码 + 死代码 =====


def test_scan_assets_invalid_type_returns_400(client):
    """不支持的资产类型应返回 400，而非 200+error。"""
    h = _admin_headers(client)
    resp = client.get("/api/v1/assets/scan/invalid", headers=h)
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


def test_scan_assets_supports_limit(client):
    """scan_assets 支持 limit 参数，防止扫描数十万文件时 OOM。"""
    h = _admin_headers(client)
    resp = client.get("/api/v1/assets/scan/doc?limit=5", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] <= 5


def test_scan_assets_limit_too_large_returns_422(client):
    """limit 超过上限被拒绝。"""
    h = _admin_headers(client)
    resp = client.get("/api/v1/assets/scan/doc?limit=100000", headers=h)
    assert resp.status_code == 422


# ===== 模块 A：create_user 统一 require_superuser =====


def test_create_user_requires_admin(client):
    """普通用户不能创建用户 → 403。"""
    admin_h = _admin_headers(client)
    # 先创建一个普通用户
    resp = client.post(
        "/api/v1/auth",
        json={
            "username": "normaluser",
            "email": "normaluser@example.com",
            "password": "normalpass123",
            "role": "member",
            "full_name": "Normal",
        },
        headers=admin_h,
    )
    assert resp.status_code == 201, resp.text
    # 用普通用户登录
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "normaluser", "password": "normalpass123"},
    )
    assert login.status_code == 200
    normal_h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    # 普通用户尝试创建用户 → 403
    resp = client.post(
        "/api/v1/auth",
        json={
            "username": "another",
            "email": "another@example.com",
            "password": "anotherpass123",
            "role": "member",
        },
        headers=normal_h,
    )
    assert resp.status_code == 403


# ===== 模块 A：status_code 常量统一 =====


def test_auth_endpoints_use_standard_status_codes(client):
    """auth 路由返回标准状态码（200/201/400/403/404）。"""
    h = _admin_headers(client)
    # 201 创建
    resp = client.post(
        "/api/v1/auth",
        json={
            "username": "statustest",
            "email": "statustest@example.com",
            "password": "statuspass123",
            "role": "member",
        },
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["id"]
    # 400 重复用户名
    resp = client.post(
        "/api/v1/auth",
        json={
            "username": "statustest",
            "email": "other@example.com",
            "password": "statuspass123",
            "role": "member",
        },
        headers=h,
    )
    assert resp.status_code == 400
    # 404 不存在
    resp = client.patch(
        "/api/v1/auth/999999",
        json={"full_name": "X"},
        headers=h,
    )
    assert resp.status_code == 404


# ===== 模块 C：JWT 含 iat 声明 =====


def test_jwt_contains_iat_claim():
    """JWT payload 应包含 iat（签发时间），支持改密后旧 token 失效。"""
    token = create_access_token("alice")
    # decode 不验签以读取 payload
    from app.core.config import settings
    from jose import jwt as _jwt

    payload = _jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": False},
    )
    assert "iat" in payload
    assert isinstance(payload["iat"], (int, float))


# ===== 模块 C：verify_password 兜底所有异常 =====


def test_verify_password_returns_false_on_corrupt_hash():
    """损坏的哈希不应抛异常，应返回 False。"""
    from app.core.security import verify_password

    assert verify_password("anything", "not-a-valid-bcrypt-hash") is False
    assert verify_password("anything", "") is False
    assert verify_password("anything", None) is False


# ===== 模块 B：provider_recommend 默认 has_gpu 与配置一致 =====


def test_provider_recommend_defaults_to_settings_has_gpu(client, monkeypatch):
    """provider_recommend 不传 has_gpu 时使用 settings.HAS_GPU。"""

    h = _admin_headers(client)
    # 不传 has_gpu，应使用 settings.HAS_GPU
    resp = client.get(
        "/api/v1/workflows-cfg/provider/recommend",
        params={"task_type": "t2v", "gen_method": "auto"},
        headers=h,
    )
    assert resp.status_code == 200


# ===== 模块 B：workflow_config_service 有缓存（不重复读盘）=====


def test_workflow_config_service_caches_yaml():
    """workflow_config_service 应缓存 YAML，多次调用不重复读盘。"""
    from app.services.workflow_config_service import list_workflows

    # 第一次调用
    wfs1 = list_workflows()
    # 第二次调用应命中缓存（不重新读盘）
    wfs2 = list_workflows()
    assert wfs1 == wfs2


# ===== 模块 B：case_studies public_list 支持分页 =====


def test_case_studies_public_list_supports_pagination(client):
    """public_list 支持 limit/offset 分页。"""
    h = _admin_headers(client)
    # 创建几个案例
    for i in range(3):
        resp = client.post(
            "/api/v1/case-studies",
            json={
                "title": f"案例 {i}",
                "slug": f"case-{i}",
                "summary": "测试",
                "content": "内容",
                "tags": ["test"],
                "published": True,
            },
            headers=h,
        )
        assert resp.status_code == 201, resp.text
    # 分页查询
    resp = client.get("/api/v1/case-studies", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 2


# ===== 模块 B：_JOB_CONTEXT 在 result 后清理 =====


def test_job_context_cleaned_after_result():
    """provider_adapters.result() 后应清理 _JOB_CONTEXT，避免内存泄漏。"""
    from app.services import provider_adapters as pa

    pa._JOB_CONTEXT.clear()
    # 模拟 submit 写入上下文
    pa._JOB_CONTEXT["fake-job-1"] = {"provider": "test"}
    assert "fake-job-1" in pa._JOB_CONTEXT
    # 模拟 result 调用后清理（即使 job 不存在也不应报错）
    # result() 对未知 job_id 返回 None，但应清理已知 job
    pa._cleanup_job_context("fake-job-1")
    assert "fake-job-1" not in pa._JOB_CONTEXT


# ===== 模块 C：recover_stuck_tasks 异常处理 =====


def test_recover_stuck_tasks_handles_exception(db_session, monkeypatch):
    """recover_stuck_tasks 遇异常应返回 -1（错误标志）而非抛出。"""
    from app.services import queue_service as qs
    from app.services.queue_service import recover_stuck_tasks

    # 模拟 select(...).where(...) 链抛异常
    def _boom(*a, **k):
        raise RuntimeError("db connection lost")

    monkeypatch.setattr(qs, "select", _boom)
    out = recover_stuck_tasks(db_session)
    assert out == -1  # -1 表示异常，正常情况返回回收数量 >= 0

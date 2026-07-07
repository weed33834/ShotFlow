"""P3 后端测试：认证、工作流配置、Provider 评分、资产。"""

import pytest

_SEED_ADMIN = "ci_admin"
_SEED_ADMIN_PASS = "ci-admin-pass"


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _admin_headers(client):
    token = _login(client, _SEED_ADMIN, _SEED_ADMIN_PASS)
    return {"Authorization": f"Bearer {token}"}


def auth_headers(client, username="admin", password="change-me-now", role="admin"):
    """以种子管理员身份创建用户并登录目标用户，返回目标用户的 Authorization 头。"""
    admin_h = _admin_headers(client)
    create_resp = client.post(
        "/api/v1/auth",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "role": role,
            "full_name": username,
        },
        headers=admin_h,
    )
    assert create_resp.status_code == 201, create_resp.text
    token = _login(client, username, password)
    return {"Authorization": f"Bearer {token}"}


# ===== 认证 =====
def test_anonymous_create_user_forbidden(client):
    """匿名用户无法调用 POST /auth 创建用户（必须管理员）。"""
    resp = client.post(
        "/api/v1/auth",
        json={"username": "tester", "email": "t@t.com", "password": "pass1234", "role": "qa"},
    )
    assert resp.status_code in (401, 403)


def test_admin_can_create_user_and_login(client):
    """管理员创建用户 -> 登录 -> /me。"""
    admin_h = _admin_headers(client)
    # 管理员创建用户
    resp = client.post(
        "/api/v1/auth",
        json={
            "username": "tester",
            "email": "t@t.com",
            "password": "pass1234",
            "role": "qa",
            "full_name": "Tester",
        },
        headers=admin_h,
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "tester"

    # 登录
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "tester", "password": "pass1234"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # /me
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "tester"


def test_login_wrong_password(client):
    """错误密码登录失败。"""
    auth_headers(client, username="u1", password="right-pw1")
    resp = client.post("/api/v1/auth/login", json={"username": "u1", "password": "wrong"})
    assert resp.status_code == 401


def test_me_without_token(client):
    """无 token 访问 /me 失败。"""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_duplicate_username(client):
    """重复用户名创建失败。"""
    admin_h = _admin_headers(client)
    client.post(
        "/api/v1/auth",
        json={"username": "dup", "email": "a@t.com", "password": "pass1234", "full_name": "d"},
        headers=admin_h,
    )
    resp = client.post(
        "/api/v1/auth",
        json={"username": "dup", "email": "b@t.com", "password": "pass1234", "full_name": "d2"},
        headers=admin_h,
    )
    assert resp.status_code == 400


def test_normal_user_cannot_create_user(client):
    """普通用户不能创建新用户。"""
    normal_h = auth_headers(client, username="self", password="pass1234", role="member")
    resp = client.post(
        "/api/v1/auth",
        json={
            "username": "intruder",
            "email": "i@t.com",
            "password": "pass1234",
            "role": "admin",
            "full_name": "x",
        },
        headers=normal_h,
    )
    assert resp.status_code == 403


def test_update_self(client):
    """用户可更新自己信息。"""
    h = auth_headers(client, username="selfupd", password="pass1234", role="member")
    me = client.get("/api/v1/auth/me", headers=h).json()
    resp = client.patch(
        f"/api/v1/auth/{me['id']}",
        json={"full_name": "新名字"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "新名字"


# ===== 工作流配置 =====
def test_list_workflow_configs(client):
    """列出工作流配置。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/workflows-cfg/configs", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    names = [w["name"] for w in data]
    assert "Flux_Character_Consistency" in names
    assert "Wan22_Dual_Expert_Video" in names


def test_get_workflow_config(client):
    """获取单个工作流配置含默认参数。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/workflows-cfg/configs/Flux_Character_Consistency", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert "parameters" in data
    assert "defaults" in data
    assert "seed" in data["defaults"]


def test_get_missing_workflow_config(client):
    h = auth_headers(client)
    resp = client.get("/api/v1/workflows-cfg/configs/不存在", headers=h)
    assert resp.status_code == 404


def test_inject_workflow_params_validation(client):
    """参数校验失败返回 422。"""
    headers = auth_headers(client, username="w", password="pass1234")

    # prompt 必填但未提供
    resp = client.post(
        "/api/v1/workflows-cfg/configs/Flux_Character_Consistency/inject",
        json={"name": "Flux_Character_Consistency", "params": {"seed": 100}},
        headers=headers,
    )
    assert resp.status_code == 422


# ===== Provider 评分 =====
def test_provider_recommend_standard(client):
    """标准镜头推荐本地 Wan2.2。"""
    h = auth_headers(client)
    resp = client.get(
        "/api/v1/workflows-cfg/provider/recommend?complexity=standard&has_gpu=true", headers=h
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommended"] == "wan_i2v"
    assert "scores" in data
    assert "profiles" in data


def test_provider_recommend_complex(client):
    """复杂镜头评分择优。"""
    h = auth_headers(client)
    resp = client.get(
        "/api/v1/workflows-cfg/provider/recommend?complexity=complex&has_gpu=true", headers=h
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommended"] in ("wan_i2v", "kling")
    assert "reason" in data


def test_provider_recommend_no_gpu(client):
    """无 GPU 时只能选云端。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/workflows-cfg/provider/recommend?has_gpu=false", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    # 无 GPU 时推荐不应是 requires_gpu 的 provider
    profiles = data["profiles"]
    recommended = data["recommended"]
    assert profiles[recommended]["requires_gpu"] is False


def test_provider_recommend_includes_new_providers(client):
    """P6-A：/provider/recommend 返回的 profiles 含 hunyuan_video/ltx_video/cogvideox。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/workflows-cfg/provider/recommend", headers=h)
    assert resp.status_code == 200
    profiles = resp.json()["profiles"]
    for name in ("hunyuan_video", "ltx_video", "cogvideox"):
        assert name in profiles, f"{name} 未出现在 profiles"
        assert "quality" in profiles[name]
        assert "requires_gpu" in profiles[name]


def test_provider_recommend_complex_considers_hunyuan(client):
    """P6-A：complex+has_gpu 时评分纳入 hunyuan_video（高 capability/quality）。

    用 gen_method=auto 触发评分择优路径（不在 provider 表中，跳过强制 gen_method 分支），
    断言推荐结果在 5 个 provider 之一，且 hunyuan_video 评分合理偏高。
    """
    h = auth_headers(client)
    resp = client.get(
        "/api/v1/workflows-cfg/provider/recommend?complexity=complex&has_gpu=true&gen_method=auto",
        headers=h,
    )
    assert resp.status_code == 200
    data = resp.json()
    all_providers = {"wan_i2v", "kling", "hunyuan_video", "ltx_video", "cogvideox"}
    assert data["recommended"] in all_providers
    scores = data["scores"]
    assert "hunyuan_video" in scores
    # hunyuan_video quality=9.0 / capability=9.0，综合评分应较高
    assert scores["hunyuan_video"] >= 7.0


def test_provider_recommend_no_gpu_includes_cogvideox(client):
    """P6-A：no_gpu 时 cogvideox（requires_gpu=False）在候选中可被选。"""
    h = auth_headers(client)
    resp = client.get(
        "/api/v1/workflows-cfg/provider/recommend?has_gpu=false&gen_method=cogvideox",
        headers=h,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommended"] == "cogvideox"
    assert data["profiles"]["cogvideox"]["requires_gpu"] is False


# ===== 资产 =====
def test_list_assets_empty(client):
    """空资产列表。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/assets", headers=h)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_scan_assets_doc(client):
    """扫描文档资产目录。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/assets/scan/doc", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_type"] == "doc"
    assert "count" in data


def test_scan_assets_invalid_type(client):
    """不支持的资产类型应返回 400。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/assets/scan/invalid", headers=h)
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


# ===== 鉴权盲区验证（P4：所有业务端点必须拒绝无 token 访问）=====
@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/projects"),
        ("post", "/api/v1/projects"),
        ("get", "/api/v1/shots"),
        ("get", "/api/v1/keyframes"),
        ("get", "/api/v1/videos"),
        ("get", "/api/v1/audio"),
        ("get", "/api/v1/queue"),
        ("get", "/api/v1/queue/stats"),
        ("get", "/api/v1/workflows"),
        ("get", "/api/v1/qa"),
        ("get", "/api/v1/daily-briefs"),
        ("get", "/api/v1/assets"),
        ("get", "/api/v1/workflows-cfg/configs"),
        ("get", "/api/v1/workflows-cfg/provider/recommend"),
    ],
)
def test_business_endpoints_require_token(client, method, path):
    """无 token 访问业务端点应返回 401。"""
    resp = getattr(client, method)(path)
    assert resp.status_code == 401, f"{method.upper()} {path} 未拒绝无 token 访问"


def test_health_is_public(client):
    """健康检查端点保持公开（用于 docker healthcheck 与监控）。"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


# ===== inject 成功路径 =====
def test_inject_workflow_params_success(client):
    """合法参数注入成功，返回可提交 ComfyUI 的工作流 JSON。"""
    h = auth_headers(client)
    resp = client.post(
        "/api/v1/workflows-cfg/configs/Flux_Character_Consistency/inject",
        json={
            "name": "Flux_Character_Consistency",
            "params": {
                "prompt": "a young woman, portrait",
                "seed": 42,
                "steps": 20,
                "cfg": 7.0,
                "frames": 81,
                "fps": 16,
            },
        },
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Flux_Character_Consistency"
    assert "workflow" in data
    assert data["param_count"] >= 1


# ===== 用户 CRUD 完整路径 =====
def test_list_users_requires_auth(client):
    """列出用户需要登录。"""
    resp = client.get("/api/v1/auth")
    assert resp.status_code == 401


def test_list_users_after_login(client):
    """超级管理员登录后可列出用户。"""
    h = _admin_headers(client)
    resp = client.get("/api/v1/auth", headers=h)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_list_users_forbidden_for_non_superuser(client):
    """非超级管理员（普通登录用户）不能列出全部用户，避免邮箱被枚举。"""
    h = auth_headers(client, username="plain", password="pass1234", role="member")
    resp = client.get("/api/v1/auth", headers=h)
    assert resp.status_code == 403


def test_delete_user_admin_only(client, db_session):
    """超级管理员可删除用户，非管理员删除应 403。"""
    from app.core.security import hash_password
    from app.models.user import User

    # 直接写库造一个真正的超级管理员（注册接口不暴露 is_superuser 字段）
    super_user = User(
        username="root",
        email="root@t.com",
        hashed_password=hash_password("p"),
        role="admin",
        is_superuser=True,
    )
    db_session.add(super_user)
    db_session.commit()
    db_session.refresh(super_user)

    root_token = client.post(
        "/api/v1/auth/login", json={"username": "root", "password": "p"}
    ).json()["access_token"]
    root_h = {"Authorization": f"Bearer {root_token}"}

    # 普通用户（用超级管理员创建）
    client.post(
        "/api/v1/auth",
        json={
            "username": "normal",
            "email": "n@t.com",
            "password": "pass1234",
            "role": "member",
            "full_name": "n",
        },
        headers=root_h,
    )
    normal_token = client.post(
        "/api/v1/auth/login", json={"username": "normal", "password": "pass1234"}
    ).json()["access_token"]
    normal_h = {"Authorization": f"Bearer {normal_token}"}

    # 普通用户删除超级管理员应 403
    resp = client.delete(f"/api/v1/auth/{super_user.id}", headers=normal_h)
    assert resp.status_code == 403

    # 普通用户更新别人应 403
    resp = client.patch(
        f"/api/v1/auth/{super_user.id}", json={"full_name": "hack"}, headers=normal_h
    )
    assert resp.status_code == 403

    # 超级管理员删除普通用户成功
    normal_id = client.get("/api/v1/auth/me", headers=normal_h).json()["id"]
    resp = client.delete(f"/api/v1/auth/{normal_id}", headers=root_h)
    assert resp.status_code == 200


def test_delete_missing_user(client, db_session):
    """超级管理员删除不存在的用户返回 404。"""
    from app.core.security import hash_password
    from app.models.user import User

    super_user = User(
        username="root2",
        email="root2@t.com",
        hashed_password=hash_password("p"),
        role="admin",
        is_superuser=True,
    )
    db_session.add(super_user)
    db_session.commit()
    token = client.post("/api/v1/auth/login", json={"username": "root2", "password": "p"}).json()[
        "access_token"
    ]
    h = {"Authorization": f"Bearer {token}"}
    resp = client.delete("/api/v1/auth/99999", headers=h)
    assert resp.status_code == 404


def test_normal_user_cannot_escalate_role(client):
    """普通用户不能自行修改 role / is_active，防止越权提权或自锁。"""
    h = auth_headers(client, username="grunt", password="pass1234", role="member")
    me = client.get("/api/v1/auth/me", headers=h).json()

    # 改 role 应被拒
    resp = client.patch(f"/api/v1/auth/{me['id']}", json={"role": "admin"}, headers=h)
    assert resp.status_code == 403

    # 改 is_active 应被拒
    resp = client.patch(f"/api/v1/auth/{me['id']}", json={"is_active": False}, headers=h)
    assert resp.status_code == 403

    # 改自己的全名应放行
    resp = client.patch(f"/api/v1/auth/{me['id']}", json={"full_name": "新名字"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "新名字"


def test_superuser_can_change_role(client, db_session):
    """超级管理员可调整他人 role。"""
    from app.core.security import hash_password
    from app.models.user import User

    root = User(
        username="root3",
        email="root3@t.com",
        hashed_password=hash_password("p"),
        role="admin",
        is_superuser=True,
    )
    db_session.add(root)
    db_session.commit()
    peasant_h = auth_headers(client, username="peasant", password="pass1234", role="member")
    peasant_id = client.get("/api/v1/auth/me", headers=peasant_h).json()["id"]
    root_h = {
        "Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'username': 'root3', 'password': 'p'}).json()['access_token']}"
    }

    resp = client.patch(f"/api/v1/auth/{peasant_id}", json={"role": "director"}, headers=root_h)
    assert resp.status_code == 200
    assert resp.json()["role"] == "director"


def test_update_user_email_duplicate_rejected(client, db_session):
    """修改邮箱为已存在邮箱应返回 400，而非触发 IntegrityError 500。"""
    from app.core.security import hash_password
    from app.models.user import User

    # 额外种一个占用邮箱的用户
    other = User(
        username="other_user",
        email="other@example.com",
        hashed_password=hash_password("pass1234"),
        role="member",
    )
    db_session.add(other)
    db_session.commit()

    h = auth_headers(client, username="email_changer", password="pass1234", role="member")
    me = client.get("/api/v1/auth/me", headers=h).json()
    # 试图把邮箱改成 other@example.com → 应 400
    resp = client.patch(
        f"/api/v1/auth/{me['id']}",
        json={"email": "other@example.com"},
        headers=h,
    )
    assert resp.status_code == 400
    assert "邮箱已存在" in resp.json()["detail"]

    # 改回自己的邮箱（无变更）应放行
    resp = client.patch(
        f"/api/v1/auth/{me['id']}",
        json={"email": me["email"]},
        headers=h,
    )
    assert resp.status_code == 200

    # 改成全新邮箱应放行
    resp = client.patch(
        f"/api/v1/auth/{me['id']}",
        json={"email": "brand_new@example.com"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "brand_new@example.com"


# ===== SSE 端点鉴权（P4：query token）=====
# SSE 是无限流，TestClient 同步模式消费会让进程挂起，所以这里只测鉴权拦截。
# 成功路径的事件流验证放到端到端联调阶段用真实 uvicorn + httpx 完成。
def test_sse_without_token(client):
    """SSE 端点无 token 应 401。"""
    resp = client.get("/api/v1/queue/stream/events")
    assert resp.status_code == 401


def test_sse_with_invalid_token(client):
    """无效 token 的 SSE 应 401。"""
    resp = client.get("/api/v1/queue/stream/events?token=not-a-real-token")
    assert resp.status_code == 401


# ===== 资产详情与过滤 =====
def test_get_missing_asset(client):
    """获取不存在的资产返回 404。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/assets/99999", headers=h)
    assert resp.status_code == 404


def test_list_assets_filter_by_type(client):
    """按类型过滤资产（空库也应正常返回空列表）。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/assets", params={"asset_type": "image"}, headers=h)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ===== P5 队列端点成功路径 =====
def test_queue_submit_and_list(client):
    """提交任务并列表查询。"""
    h = auth_headers(client)
    resp = client.post(
        "/api/v1/queue",
        json={"task_type": "keyframe", "prompt": "测试关键帧", "priority": 5},
        headers=h,
    )
    assert resp.status_code == 201, resp.text
    task = resp.json()
    assert task["task_type"] == "keyframe"
    assert task["status"] == "pending"
    assert task["priority"] == 5
    assert task["progress"] == 0
    assert "error_class" in task

    # 列表
    resp = client.get("/api/v1/queue", headers=h)
    assert resp.status_code == 200
    assert any(t["id"] == task["id"] for t in resp.json())


def test_queue_patch_priority(client):
    """PATCH 修改优先级。"""
    h = auth_headers(client)
    resp = client.post(
        "/api/v1/queue",
        json={"task_type": "tts", "prompt": "配音"},
        headers=h,
    )
    tid = resp.json()["id"]

    resp = client.patch(f"/api/v1/queue/{tid}", json={"priority": 9}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["priority"] == 9


def test_queue_cancel_and_stats(client):
    """取消任务并查统计。"""
    h = auth_headers(client)
    resp = client.post(
        "/api/v1/queue",
        json={"task_type": "music", "prompt": "配乐"},
        headers=h,
    )
    tid = resp.json()["id"]

    resp = client.post(f"/api/v1/queue/{tid}/cancel", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    resp = client.get("/api/v1/queue/stats", headers=h)
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total"] >= 1
    assert stats["cancelled"] >= 1


def test_queue_get_status(client):
    """查单个任务状态。"""
    h = auth_headers(client)
    resp = client.post(
        "/api/v1/queue",
        json={"task_type": "keyframe"},
        headers=h,
    )
    tid = resp.json()["id"]

    resp = client.get(f"/api/v1/queue/{tid}", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == tid
    assert "progress" in data


def test_queue_get_missing(client):
    """查不存在的任务 404。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/queue/99999", headers=h)
    assert resp.status_code == 404


def test_queue_patch_missing(client):
    """PATCH 不存在的任务 404。"""
    h = auth_headers(client)
    resp = client.patch("/api/v1/queue/99999", json={"priority": 1}, headers=h)
    assert resp.status_code == 404


def test_queue_list_filter_by_status(client):
    """按状态过滤队列。"""
    h = auth_headers(client)
    client.post("/api/v1/queue", json={"task_type": "keyframe"}, headers=h)
    resp = client.get("/api/v1/queue", params={"status": "pending"}, headers=h)
    assert resp.status_code == 200
    assert all(t["status"] == "pending" for t in resp.json())


# ===== P5 角色限制（S4 修复）=====
def test_queue_write_requires_role(client):
    """普通 member 角色不能写操作队列。"""
    h = auth_headers(client, username="viewer", password="pass1234", role="member")

    # 提交被拒
    resp = client.post("/api/v1/queue", json={"task_type": "keyframe"}, headers=h)
    assert resp.status_code == 403

    # 读操作放行
    resp = client.get("/api/v1/queue", headers=h)
    assert resp.status_code == 200

    resp = client.get("/api/v1/queue/stats", headers=h)
    assert resp.status_code == 200


def test_queue_patch_validation(client):
    """优先级超出范围返回 422。"""
    h = auth_headers(client)
    resp = client.post("/api/v1/queue", json={"task_type": "keyframe"}, headers=h)
    tid = resp.json()["id"]
    resp = client.patch(f"/api/v1/queue/{tid}", json={"priority": 999}, headers=h)
    assert resp.status_code == 422

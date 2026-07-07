"""健康检查与根路由测试。"""

_SEED_ADMIN = "ci_admin"
_SEED_ADMIN_PASS = "ci-admin-pass"


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _admin_h(client):
    return {"Authorization": f"Bearer {_login(client, _SEED_ADMIN, _SEED_ADMIN_PASS)}"}


def auth_headers(client, username="admin", password="change-me-now", role="admin"):
    """以种子管理员身份创建用户，返回目标用户的 Authorization 头。"""
    admin_h = _admin_h(client)
    cr = client.post(
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
    assert cr.status_code == 201, cr.text
    return {"Authorization": f"Bearer {_login(client, username, password)}"}


def test_root(client):
    """根路径返回服务信息。"""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "app" in data
    assert "docs" in data


def test_create_and_list_project(client):
    """创建项目后应能在列表中查到。"""
    h = auth_headers(client)
    resp = client.post("/api/v1/projects", json={"title": "测试项目"}, headers=h)
    assert resp.status_code == 201
    created = resp.json()
    assert created["title"] == "测试项目"

    resp = client.get("/api/v1/projects", headers=h)
    assert resp.status_code == 200
    assert any(p["title"] == "测试项目" for p in resp.json())


def test_get_project(client):
    """按 ID 获取项目详情。"""
    h = auth_headers(client)
    resp = client.post("/api/v1/projects", json={"title": "详情测试"}, headers=h)
    pid = resp.json()["id"]
    resp = client.get(f"/api/v1/projects/{pid}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["title"] == "详情测试"


def test_get_missing_project(client):
    """不存在的项目应返回 404。"""
    h = auth_headers(client)
    resp = client.get("/api/v1/projects/999999", headers=h)
    assert resp.status_code == 404


def test_delete_project(client):
    """删除项目后应不可再查。"""
    h = auth_headers(client)
    resp = client.post("/api/v1/projects", json={"title": "删除测试"}, headers=h)
    pid = resp.json()["id"]
    resp = client.delete(f"/api/v1/projects/{pid}", headers=h)
    assert resp.status_code == 200
    resp = client.get(f"/api/v1/projects/{pid}", headers=h)
    assert resp.status_code == 404

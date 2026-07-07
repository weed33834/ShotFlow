"""API 集成测试 — 覆盖 P1 新增端点。"""

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


def test_shot_crud(client):
    """镜头 CRUD。"""
    h = auth_headers(client)
    proj = client.post("/api/v1/projects", json={"title": "镜头测试项目"}, headers=h).json()
    pid = proj["id"]

    # 创建
    resp = client.post(
        "/api/v1/shots",
        json={"project_id": pid, "shot_code": "S01_01", "scene": "废墟", "duration": 5.0},
        headers=h,
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]
    assert resp.json()["shot_code"] == "S01_01"

    # 列表（按项目过滤）
    resp = client.get(f"/api/v1/shots?project_id={pid}", headers=h)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 详情
    resp = client.get(f"/api/v1/shots/{sid}", headers=h)
    assert resp.status_code == 200

    # 更新
    resp = client.patch(f"/api/v1/shots/{sid}", json={"duration": 8.0}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["duration"] == 8.0

    # 删除
    resp = client.delete(f"/api/v1/shots/{sid}", headers=h)
    assert resp.status_code == 200
    assert client.get(f"/api/v1/shots/{sid}", headers=h).status_code == 404


def test_keyframe_crud(client):
    """关键帧 CRUD。"""
    h = auth_headers(client)
    proj = client.post("/api/v1/projects", json={"title": "关键帧项目"}, headers=h).json()
    shot = client.post(
        "/api/v1/shots", json={"project_id": proj["id"], "shot_code": "S02_01"}, headers=h
    ).json()

    resp = client.post(
        "/api/v1/keyframes",
        json={"shot_id": shot["id"], "label": "S02_01", "prompt": "Ava at ship", "seed": 999},
        headers=h,
    )
    assert resp.status_code == 201
    assert resp.json()["seed"] == 999
    assert resp.json()["status"] == "pending"

    resp = client.get(f"/api/v1/keyframes?shot_id={shot['id']}", headers=h)
    assert len(resp.json()) == 1


def test_video_and_dialogue_crud(client):
    """视频片段与对白 CRUD。"""
    h = auth_headers(client)
    proj = client.post("/api/v1/projects", json={"title": "视频项目"}, headers=h).json()
    shot = client.post(
        "/api/v1/shots", json={"project_id": proj["id"], "shot_code": "S03_01"}, headers=h
    ).json()

    # 视频
    resp = client.post(
        "/api/v1/videos", json={"shot_id": shot["id"], "provider": "wan_i2v"}, headers=h
    )
    assert resp.status_code == 201
    vid = resp.json()["id"]
    assert client.get(f"/api/v1/videos/{vid}", headers=h).status_code == 200

    # 对白
    resp = client.post(
        "/api/v1/audio",
        json={"shot_id": shot["id"], "role": "ava", "text": "我听到了回响"},
        headers=h,
    )
    assert resp.status_code == 201
    did = resp.json()["id"]
    assert client.get(f"/api/v1/audio/{did}", headers=h).status_code == 200


def test_queue_submit_and_query(client, monkeypatch):
    """提交渲染任务并查询状态。

    用 monkeypatch 把 Celery 派发替换为 no-op，避免依赖 Redis。
    """
    h = auth_headers(client)

    class _FakeAsyncResult:
        id = "fake-celery-id"

    monkeypatch.setattr(
        "app.tasks.render_tasks.run_render_task.delay",
        lambda *a, **kw: _FakeAsyncResult(),
    )

    resp = client.post(
        "/api/v1/queue",
        json={"task_type": "keyframe", "prompt": "Ava walking", "priority": 5},
        headers=h,
    )
    assert resp.status_code == 201
    task = resp.json()
    assert task["task_type"] == "keyframe"
    assert task["status"] == "pending"
    assert task["celery_task_id"] == "fake-celery-id"
    tid = task["id"]

    # 查询状态
    resp = client.get(f"/api/v1/queue/{tid}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["id"] == tid

    # 取消
    resp = client.post(f"/api/v1/queue/{tid}/cancel", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # 重试
    resp = client.post(f"/api/v1/queue/{tid}/retry", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_queue_stats(client, monkeypatch):
    """队列统计端点。"""
    h = auth_headers(client)
    monkeypatch.setattr(
        "app.tasks.render_tasks.run_render_task.delay",
        lambda *a, **kw: type("R", (), {"id": "x"})(),
    )
    client.post("/api/v1/queue", json={"task_type": "keyframe", "prompt": "a"}, headers=h)
    client.post("/api/v1/queue", json={"task_type": "tts", "prompt": "b"}, headers=h)

    resp = client.get("/api/v1/queue/stats", headers=h)
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total"] == 2
    assert stats["pending"] == 2


def test_queue_list_filters(client, monkeypatch):
    """队列列表按状态/类型过滤。"""
    h = auth_headers(client)
    monkeypatch.setattr(
        "app.tasks.render_tasks.run_render_task.delay",
        lambda *a, **kw: type("R", (), {"id": "x"})(),
    )
    client.post("/api/v1/queue", json={"task_type": "keyframe", "prompt": "a"}, headers=h)
    client.post("/api/v1/queue", json={"task_type": "tts", "prompt": "b"}, headers=h)

    resp = client.get("/api/v1/queue?task_type=keyframe", headers=h)
    assert resp.status_code == 200
    assert all(t["task_type"] == "keyframe" for t in resp.json())


def test_workflow_qa_daily_crud(client):
    """工作流、质检、日报 CRUD。"""
    h = auth_headers(client)
    # 工作流
    resp = client.post(
        "/api/v1/workflows",
        json={"name": "Flux_Test", "file_path": "03_Workflows/test.json"},
        headers=h,
    )
    assert resp.status_code == 201

    # 日报
    resp = client.post(
        "/api/v1/daily-briefs",
        json={"brief_date": "2026-07-02", "author": "小李", "content": "完成 P1"},
        headers=h,
    )
    assert resp.status_code == 201

    # 质检
    proj = client.post("/api/v1/projects", json={"title": "QA项目"}, headers=h).json()
    shot = client.post(
        "/api/v1/shots", json={"project_id": proj["id"], "shot_code": "S04_01"}, headers=h
    ).json()
    resp = client.post(
        "/api/v1/qa",
        json={"shot_id": shot["id"], "severity": "warning", "defects": [{"type": "flicker"}]},
        headers=h,
    )
    assert resp.status_code == 201


def test_queue_404(client):
    """查询不存在的任务返回 404。"""
    h = auth_headers(client)
    assert client.get("/api/v1/queue/999999", headers=h).status_code == 404
    assert client.post("/api/v1/queue/999999/retry", headers=h).status_code == 404
    assert client.post("/api/v1/queue/999999/cancel", headers=h).status_code == 404

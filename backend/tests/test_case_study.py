"""P6-B 用户案例展示区测试：公开浏览 + 登录管理。"""

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


def _create(client, headers, slug, status="published", tags=None, **extra):
    """通过 API 创建案例并返回响应 json。"""
    payload = {
        "title": f"案例-{slug}",
        "slug": slug,
        "summary": "一句话摘要",
        "content_md": "# 正文",
        "cover_image": "/covers/a.png",
        "author": "张三",
        "status": status,
        "tags": tags if tags is not None else [],
        "meta": {},
    }
    payload.update(extra)
    resp = client.post("/api/v1/case-studies", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===== 公开端点 =====
def test_public_list_only_published(client):
    """公开列表仅返回 published，不含 draft/archived。"""
    h = _admin_h(client)
    _create(client, h, "pub-one", status="published")
    _create(client, h, "draft-one", status="draft")
    _create(client, h, "arch-one", status="archived")

    resp = client.get("/api/v1/case-studies")
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()]
    assert "pub-one" in slugs
    assert "draft-one" not in slugs
    assert "arch-one" not in slugs


def test_public_get_by_slug(client):
    """公开详情按 slug 返回已发布案例。"""
    h = _admin_h(client)
    _create(client, h, "detail-pub", status="published", author="李四")
    resp = client.get("/api/v1/case-studies/detail-pub")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "detail-pub"
    assert data["author"] == "李四"
    assert data["status"] == "published"


def test_public_get_unpublished_404(client):
    """draft 案例对公开访问返回 404。"""
    h = _admin_h(client)
    _create(client, h, "hidden-draft", status="draft")
    resp = client.get("/api/v1/case-studies/hidden-draft")
    assert resp.status_code == 404


def test_public_get_missing_404(client):
    """不存在的 slug 返回 404。"""
    resp = client.get("/api/v1/case-studies/no-such-slug")
    assert resp.status_code == 404


def test_public_list_filter_by_tag(client):
    """?tag= 按标签过滤。"""
    h = _admin_h(client)
    _create(client, h, "tag-a", status="published", tags=["AIGC", "短片"])
    _create(client, h, "tag-b", status="published", tags=["广告"])
    resp = client.get("/api/v1/case-studies?tag=AIGC")
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()]
    assert "tag-a" in slugs
    assert "tag-b" not in slugs


# ===== 鉴权 =====
def test_create_requires_auth(client):
    """无 token POST 创建返回 401。"""
    resp = client.post("/api/v1/case-studies", json={"title": "t", "slug": "s"})
    assert resp.status_code == 401


def test_admin_list_requires_auth(client):
    """无 token GET /admin/list 返回 401。"""
    resp = client.get("/api/v1/case-studies/admin/list")
    assert resp.status_code == 401


# ===== 管理端 CRUD =====
def test_create_case_study(client):
    """登录后创建案例，返回 201 + 完整字段。"""
    h = _admin_h(client)
    resp = client.post(
        "/api/v1/case-studies",
        json={
            "title": "全字段案例",
            "slug": "full-case",
            "summary": "摘要",
            "content_md": "## md",
            "cover_image": "/c.png",
            "author": "王五",
            "status": "draft",
            "tags": ["AIGC"],
            "meta": {"video": "https://x"},
            "project_id": None,
        },
        headers=h,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] > 0
    assert data["slug"] == "full-case"
    assert data["status"] == "draft"
    assert data["tags"] == ["AIGC"]
    assert data["meta"] == {"video": "https://x"}
    assert data["author"] == "王五"
    assert data["project_id"] is None
    assert "created_at" in data and "updated_at" in data


def test_create_duplicate_slug_400(client):
    """重复 slug 返回 400。"""
    h = _admin_h(client)
    _create(client, h, "dup-slug", status="draft")
    resp = client.post(
        "/api/v1/case-studies",
        json={"title": "另一个", "slug": "dup-slug"},
        headers=h,
    )
    assert resp.status_code == 400


def test_admin_list_includes_all_status(client):
    """管理列表含 draft/published/archived。"""
    h = _admin_h(client)
    _create(client, h, "adm-pub", status="published")
    _create(client, h, "adm-draft", status="draft")
    _create(client, h, "adm-arch", status="archived")
    resp = client.get("/api/v1/case-studies/admin/list", headers=h)
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()]
    assert {"adm-pub", "adm-draft", "adm-arch"} <= set(slugs)


def test_update_case_study(client):
    """登录后 PATCH 更新字段。"""
    h = _admin_h(client)
    case = _create(client, h, "upd-me", status="draft")
    resp = client.patch(
        f"/api/v1/case-studies/{case['id']}",
        json={"status": "published", "summary": "更新后的摘要", "tags": ["新"]},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "published"
    assert data["summary"] == "更新后的摘要"
    assert data["tags"] == ["新"]


def test_update_missing_404(client):
    """PATCH 不存在 id 返回 404。"""
    h = _admin_h(client)
    resp = client.patch(
        "/api/v1/case-studies/99999",
        json={"title": "x"},
        headers=h,
    )
    assert resp.status_code == 404


def test_delete_case_study(client):
    """登录后 DELETE 成功。"""
    h = _admin_h(client)
    case = _create(client, h, "del-me", status="draft")
    resp = client.delete(f"/api/v1/case-studies/{case['id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # 删除后公开详情 404
    resp2 = client.get("/api/v1/case-studies/del-me")
    assert resp2.status_code == 404


def test_delete_missing_404(client):
    """DELETE 不存在 id 返回 404。"""
    h = _admin_h(client)
    resp = client.delete("/api/v1/case-studies/99999", headers=h)
    assert resp.status_code == 404

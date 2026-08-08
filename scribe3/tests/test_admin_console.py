"""管理台：账号 CRUD、跨账号作品、审计、权限。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from scribe3.auth.users import create_user, ensure_bootstrap_users, is_admin


SECRET = "test-admin-console-secret-32bytes-xx"


@pytest.fixture()
def admin_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SCRIBE3_AUTH_ENABLED", "1")
    monkeypatch.setenv("SCRIBE3_SESSION_SECRET", SECRET)
    monkeypatch.setenv("SCRIBE3_AUTH_DB", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("SCRIBE3_LEGACY_OWNER", "admin")
    monkeypatch.setenv("SCRIBE3_ADMIN_USERS", "admin")
    monkeypatch.setenv("SCRIBE3_BOOTSTRAP_USERS", "admin:admin-pass-99,alice:alice-pass-99")
    monkeypatch.delenv("SCRIBE3_API_TOKEN", raising=False)
    ensure_bootstrap_users()
    assert is_admin("admin")
    yield tmp_path


@pytest.fixture()
def client(admin_env, monkeypatch):
    # Fake work registry in-memory for admin works APIs
    registry: dict = {}

    def list_works_admin(*, owner=None, archived="all", q=None, url=None):
        out = []
        for slug, m in registry.items():
            is_arch = m.get("archived") is True
            if archived == "active" and is_arch:
                continue
            if archived == "archived" and not is_arch:
                continue
            eff = m.get("owner_user_id") or "admin"
            if owner and eff != owner:
                continue
            if q and q not in (m.get("title") or "") and q not in slug:
                continue
            out.append({
                "slug": slug,
                "title": m["title"],
                "owner_user_id": m.get("owner_user_id"),
                "effective_owner": eff,
                "archived": is_arch,
            })
        return out

    def create_work(title, slug=None, url=None, owner_user_id=None):
        import uuid
        slug = slug or ("book_" + uuid.uuid4().hex[:8])
        registry[slug] = {
            "title": title,
            "owner_user_id": owner_user_id,
            "archived": False,
        }
        return {"slug": slug, "title": title, "owner_user_id": owner_user_id}

    def set_work_owner(slug, owner_user_id, url=None):
        if slug not in registry:
            raise ValueError(f"作品不存在: {slug}")
        registry[slug]["owner_user_id"] = owner_user_id
        m = registry[slug]
        return {
            "slug": slug,
            "title": m["title"],
            "owner_user_id": owner_user_id,
            "archived": m.get("archived"),
        }

    def archive_work(slug, url=None):
        if slug not in registry:
            raise ValueError(f"作品不存在: {slug}")
        registry[slug]["archived"] = True

    def restore_work(slug, url=None):
        if slug not in registry:
            raise ValueError(f"作品不存在: {slug}")
        registry[slug]["archived"] = False

    def delete_work(slug, url=None):
        if slug not in registry or not registry[slug].get("archived"):
            raise ValueError("请先移入废弃箱再永久删除")
        del registry[slug]

    def rename_work(slug, title, url=None):
        if slug not in registry:
            raise ValueError(f"作品不存在: {slug}")
        registry[slug]["title"] = title

    monkeypatch.setattr("scribe3.store.core_preamble.list_works_admin", list_works_admin)
    monkeypatch.setattr("scribe3.store.core_preamble.create_work", create_work)
    monkeypatch.setattr("scribe3.store.core_preamble.set_work_owner", set_work_owner)
    monkeypatch.setattr("scribe3.store.core_preamble.archive_work", archive_work)
    monkeypatch.setattr("scribe3.store.core_preamble.restore_work", restore_work)
    monkeypatch.setattr("scribe3.store.core_preamble.delete_work", delete_work)
    monkeypatch.setattr("scribe3.store.core_preamble.rename_work", rename_work)

    from scribe3.auth.admin_routes import router as admin_router
    from scribe3.auth.routes import router as auth_router
    from fastapi import FastAPI
    from scribe3.auth.middleware import install_l1_auth

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(admin_router)
    install_l1_auth(app)
    return TestClient(app), registry


def _login(c, user, pw):
    r = c.post("/auth/login", json={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return r


def test_author_forbidden_admin_api(client):
    c, _ = client
    _login(c, "alice", "alice-pass-99")
    r = c.get("/admin/summary")
    assert r.status_code == 403


def test_admin_user_crud_and_audit(client):
    c, _ = client
    _login(c, "admin", "admin-pass-99")
    me = c.get("/auth/me").json()
    assert me["is_admin"] is True

    r = c.post("/admin/users", json={
        "username": "bob",
        "password": "bob-pass-99",
        "role": "author",
        "display_name": "鲍勃",
    })
    assert r.status_code == 200, r.text
    assert r.json()["username"] == "bob"

    r = c.get("/admin/users")
    assert r.status_code == 200
    names = {u["username"] for u in r.json()["items"]}
    assert {"admin", "alice", "bob"} <= names

    r = c.patch("/admin/users/bob", json={"status": "disabled", "note": "temp"})
    assert r.status_code == 200
    assert r.json()["status"] == "disabled"

    r = c.post("/admin/users/bob/password", json={"password": "new-bob-99"})
    assert r.status_code == 200

    r = c.post("/admin/users/bob/force-logout")
    assert r.status_code == 200

    r = c.delete("/admin/users/bob?confirm_username=bob")
    assert r.status_code == 200

    audit = c.get("/admin/audit").json()
    actions = {a["action"] for a in audit["items"]}
    assert "user.create" in actions
    assert "user.delete" in actions


def test_admin_works_lifecycle(client):
    c, reg = client
    _login(c, "admin", "admin-pass-99")
    r = c.post("/admin/works", json={
        "title": "测试书甲",
        "owner_user_id": "alice",
    })
    assert r.status_code == 200, r.text
    slug = r.json()["slug"]

    r = c.get("/admin/works?owner=alice")
    assert r.status_code == 200
    assert any(w["slug"] == slug for w in r.json()["items"])

    r = c.post(f"/admin/works/{slug}/transfer", json={"new_owner": "admin"})
    assert r.status_code == 200
    assert r.json()["owner_user_id"] == "admin"

    r = c.post(f"/admin/works/{slug}/archive")
    assert r.status_code == 200

    r = c.request(
        "DELETE",
        f"/admin/works/{slug}/purge",
        json={"confirm_title": "测试书甲"},
    )
    assert r.status_code == 200, r.text
    assert slug not in reg


def test_cannot_delete_last_admin(client):
    c, _ = client
    _login(c, "admin", "admin-pass-99")
    # demote path: only one admin
    r = c.patch("/admin/users/admin", json={"role": "author"})
    assert r.status_code == 422

"""L1 session auth + work ownership — drives shipped auth modules and HTTP entry."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scribe3.auth.ownership import (
    effective_owner,
    filter_works_for_user,
    user_owns_work,
)
from scribe3.auth.passwords import hash_password, verify_password
from scribe3.auth.session import issue_session_token, parse_session_token
from scribe3.auth.users import authenticate, create_user, ensure_bootstrap_users


SECRET = b"test-session-secret-for-l1-isolation-32b"


@pytest.fixture()
def auth_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SCRIBE3_AUTH_ENABLED", "1")
    monkeypatch.setenv("SCRIBE3_SESSION_SECRET", SECRET.decode())
    monkeypatch.setenv("SCRIBE3_AUTH_DB", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("SCRIBE3_LEGACY_OWNER", "admin")
    monkeypatch.delenv("SCRIBE3_API_TOKEN", raising=False)
    monkeypatch.delenv("SCRIBE3_BOOTSTRAP_USERS", raising=False)
    yield tmp_path


class TestPasswordAndSession:
    def test_hash_verify_roundtrip(self):
        h = hash_password("s3cret!")
        assert h.startswith("pbkdf2_sha256$")
        assert verify_password("s3cret!", h)
        assert not verify_password("wrong", h)

    def test_session_issue_parse(self):
        tok = issue_session_token("alice", secret=SECRET)
        data = parse_session_token(tok, secret=SECRET)
        assert data is not None
        assert data.username == "alice"

    def test_session_rejects_tamper_and_expiry(self):
        tok = issue_session_token("alice", secret=SECRET)
        assert parse_session_token(tok + "x", secret=SECRET) is None
        # expired
        tok2 = issue_session_token("alice", now=1_000_000, secret=SECRET)
        assert parse_session_token(tok2, now=1_000_000 + 10**9, secret=SECRET) is None


class TestOwnershipPure:
    def test_effective_owner_and_filter(self):
        rows = [
            {"slug": "a", "title": "A", "owner_user_id": "alice"},
            {"slug": "b", "title": "B", "owner_user_id": "bob"},
            {"slug": "legacy", "title": "L", "owner_user_id": None},
        ]
        assert effective_owner(rows[2]) == "admin"
        assert user_owns_work("alice", rows[0])
        assert not user_owns_work("alice", rows[1])
        assert user_owns_work("admin", rows[2])
        only_alice = filter_works_for_user(rows, "alice")
        assert [r["slug"] for r in only_alice] == ["a"]
        only_admin = filter_works_for_user(rows, "admin")
        assert [r["slug"] for r in only_admin] == ["legacy"]


class TestUsersBootstrap:
    def test_bootstrap_and_authenticate(self, auth_env, monkeypatch):
        monkeypatch.setenv("SCRIBE3_BOOTSTRAP_USERS", "alice:pw-a,bob:pw-b")
        created = ensure_bootstrap_users()
        assert set(created) == {"alice", "bob"}
        assert authenticate("alice", "pw-a")
        assert not authenticate("alice", "wrong")
        assert authenticate("bob", "pw-b")
        # second call does not duplicate
        assert ensure_bootstrap_users() == []


@pytest.fixture()
def client_auth(auth_env, monkeypatch):
    """TestClient against real app with L1 auth on; isolation via monkeypatched registry."""
    monkeypatch.setenv("SCRIBE3_BOOTSTRAP_USERS", "alice:alice-pass,bob:bob-pass")
    # Import after env so settings paths are isolated (conftest already sets settings db)
    import scribe3.app as A

    # In-memory work registry for ownership middleware + list/create
    registry: dict[str, dict] = {}

    def fake_list_works():
        from scribe3.auth.context import current_owner_filter
        from scribe3.auth.ownership import filter_works_for_user

        rows = [
            {
                "slug": s,
                "title": m["title"],
                "owner_user_id": m.get("owner_user_id"),
            }
            for s, m in registry.items()
            if not m.get("archived")
        ]
        return filter_works_for_user(rows, current_owner_filter.get())

    def fake_create_work(title, slug=None, url=None, owner_user_id=None):
        from scribe3.auth.context import current_user_id
        import uuid

        owner = owner_user_id or current_user_id.get()
        slug = slug or ("book_" + uuid.uuid4().hex[:8])
        registry[slug] = {"title": title, "owner_user_id": owner, "archived": False}
        return {"slug": slug, "title": title, "owner_user_id": owner}

    def fake_get_work_row(slug, url=None):
        m = registry.get(slug)
        if not m:
            return None
        return {
            "slug": slug,
            "title": m["title"],
            "owner_user_id": m.get("owner_user_id"),
            "archived": m.get("archived"),
        }

    monkeypatch.setattr(A, "list_works", fake_list_works)
    monkeypatch.setattr(A, "create_work", fake_create_work)
    # ownership module used by middleware
    import scribe3.auth.ownership as own

    monkeypatch.setattr(own, "get_work_row", fake_get_work_row)

    ensure_bootstrap_users()
    return TestClient(A.app), registry


class TestHttpAuthAndIsolation:
    def test_protected_without_session_401(self, client_auth):
        client, _ = client_auth
        r = client.get("/works")
        assert r.status_code == 401
        assert "authentication" in r.json()["detail"].lower()

    def test_login_fail_and_success_session(self, client_auth):
        client, _ = client_auth
        bad = client.post("/auth/login", json={"username": "alice", "password": "nope"})
        assert bad.status_code == 401

        ok = client.post("/auth/login", json={"username": "alice", "password": "alice-pass"})
        assert ok.status_code == 200
        assert ok.json()["username"] == "alice"
        assert "s3_session" in ok.cookies

        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == "alice"

        works = client.get("/works")
        assert works.status_code == 200
        assert works.json() == [] or isinstance(works.json(), list)

    def test_ab_work_isolation(self, client_auth):
        client, registry = client_auth

        # Alice creates a work
        ca = client.post("/auth/login", json={"username": "alice", "password": "alice-pass"})
        assert ca.status_code == 200
        created = client.post("/works", json={"title": "Alice Book"})
        assert created.status_code == 200
        slug_a = created.json()["slug"]
        assert created.json()["owner_user_id"] == "alice"
        assert slug_a in registry

        listed_a = client.get("/works").json()
        assert any(w["slug"] == slug_a for w in listed_a)

        # Switch to Bob (new client jar)
        client_b = TestClient(client.app)
        assert client_b.post(
            "/auth/login", json={"username": "bob", "password": "bob-pass"}
        ).status_code == 200

        listed_b = client_b.get("/works").json()
        assert all(w["slug"] != slug_a for w in listed_b)

        # Bob cannot access Alice work via ?work= (ownership choke; before store I/O)
        denied = client_b.get("/entities", params={"work": slug_a})
        assert denied.status_code == 403
        assert "denied" in denied.json()["detail"].lower()

        # Bob cannot mutate Alice work via /works/{slug}
        denied_path = client_b.patch(f"/works/{slug_a}", json={"title": "stolen"})
        assert denied_path.status_code == 403

        # Alice still lists her book (ownership allow on collection already proven)
        listed_a2 = client.get("/works").json()
        assert any(w["slug"] == slug_a for w in listed_a2)

    def test_health_public(self, client_auth):
        client, _ = client_auth
        # /health may be on extracted router
        r = client.get("/health")
        assert r.status_code in (200, 503, 500)  # process may lack deps; not 401
        assert r.status_code != 401

"""Task 13: REST 世界写紧急开关 SCRIBE3_EMERGENCY_REST_WRITE。

默认关 → 世界状态 REST 写 403；显式开 → 可写(或业务 422，但非 403)。
conftest autouse 默认钉 '1'，保证存量 test_app 写路径不炸；本文件显式关/开覆盖。
"""
import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3 import settings as S


def _client(store):
    A.set_store(store)
    return TestClient(A.app)


def test_post_characters_forbidden_when_emergency_rest_write_off(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    S.invalidate_cache()
    assert S.get_setting("SCRIBE3_EMERGENCY_REST_WRITE") is False

    c = _client(store)
    r = c.post("/characters?work=main", json={"name": "关闸角色", "backstory": "不应落库"})
    assert r.status_code == 403, r.text
    body = r.json()
    assert body["detail"] == "REST world write disabled; use dialogue + MCP approval"
    # 确认未写入
    names = [e["name"] for e in c.get("/entities?work=main").json()]
    assert "关闸角色" not in names


def test_post_characters_allowed_when_emergency_rest_write_on(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "1")
    S.invalidate_cache()
    assert S.get_setting("SCRIBE3_EMERGENCY_REST_WRITE") is True

    c = _client(store)
    r = c.post("/characters?work=main", json={"name": "开闸角色", "backstory": "可写"})
    # 业务成功 200/201，或校验失败 422——但绝不能是开关 403
    assert r.status_code != 403, r.text
    assert r.status_code in (200, 201, 422), r.text
    if r.status_code in (200, 201):
        names = [e["name"] for e in c.get("/entities?work=main").json()]
        assert "开闸角色" in names


def test_get_characters_not_blocked_when_off(store, monkeypatch):
    """读路径(GET)在开关关闭时仍放行。"""
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    S.invalidate_cache()
    c = _client(store)
    r = c.get("/entities?work=main")
    assert r.status_code == 200


def test_save_chapter_not_blocked_when_off(store, monkeypatch):
    """正文存盘路径不属于世界写拦截清单。"""
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    S.invalidate_cache()
    c = _client(store)
    # 无章时可能 404/422/400，但不得 403
    r = c.post("/save-chapter?work=main", json={"seq": 1, "content": "正文"})
    assert r.status_code != 403, r.text


def test_capabilities_reports_emergency_rest_write(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    S.invalidate_cache()
    c = _client(store)
    flags = c.get("/capabilities").json()["flags"]
    assert "emergency_rest_write" in flags
    assert flags["emergency_rest_write"] is False

    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "1")
    S.invalidate_cache()
    flags = c.get("/capabilities").json()["flags"]
    assert flags["emergency_rest_write"] is True


def test_author_session_clip_allowed_when_rest_world_write_off(store, monkeypatch):
    """作者私人剪藏不经世界写闸；POST /materials 仍 403。"""
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    S.invalidate_cache()
    c = _client(store)

    blocked = c.post("/materials?work=main", json={
        "title": "应被闸", "body": "x", "kind": "snippet",
    })
    assert blocked.status_code == 403, blocked.text

    r = c.post("/author/session-clips?work=main", json={
        "body": "城墙上霜白如骨",
        "kind": "snippet",
        "origin_label": "主编会话",
        "scope_label": "选区",
        "chapter_seq": 3,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    assert data.get("id")
    assert data.get("kind") == "snippet"
    assert "会话摘录" in (data.get("source") or "")

    mats = c.get("/materials?work=main&kind=snippet").json()
    rows = mats if isinstance(mats, list) else (mats.get("items") or [])
    ids = {str(m.get("id")) for m in rows}
    assert str(data["id"]) in ids


def test_author_session_clip_rejects_empty_and_coerces_kind(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    S.invalidate_cache()
    c = _client(store)
    empty = c.post("/author/session-clips?work=main", json={"body": "  "})
    assert empty.status_code == 422, empty.text
    # inbox-looking kind → coerced to snippet
    r = c.post("/author/session-clips?work=main", json={
        "body": "备忘一句", "kind": "needs_human",
    })
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "snippet"

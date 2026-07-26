"""存档业务:作品废弃箱 / 章节软归档 / emergency 闸放行 / 过滤器。"""
from __future__ import annotations

import os

import pytest

import scribe3.app as A
from scribe3.store.core_preamble import (
    archive_work, archived_works, create_work, delete_work, list_works, restore_work,
)

from .test_app import _client


def test_chapter_archive_restore_paths_not_world_write_gated():
    """章节软归档/恢复不得被 emergency REST 世界写闸 403。"""
    assert A._is_rest_world_write_path("/chapters/3/archive") is False
    assert A._is_rest_world_write_path("/chapters/12/restore") is False
    # 永久删除与 meta 写仍在闸内
    assert A._is_rest_world_write_path("/chapters/3") is True
    assert A._is_rest_world_write_path("/chapters") is True


def test_chapter_archive_allowed_when_emergency_off(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    import scribe3.settings as S
    S.invalidate_cache()
    store.save_chapter(5, "正文。", title="五")
    c = _client(store)
    r = c.post("/chapters/5/archive?work=main", json={"reason": "支线"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "archived"
    r2 = c.post("/chapters/5/restore?work=main")
    assert r2.status_code == 200, r2.text


def test_archive_work_missing_raises():
    with pytest.raises(ValueError, match="不存在"):
        archive_work("__no_such_work_for_archive__")


def test_restore_work_missing_raises():
    with pytest.raises(ValueError, match="不存在"):
        restore_work("__no_such_work_for_restore__")


def test_archive_work_idempotent_and_roundtrip():
    slug = create_work("存档审查临时书")["slug"]
    try:
        archive_work(slug)
        archive_work(slug)  # 幂等
        assert any(w["slug"] == slug for w in archived_works())
        assert all(w["slug"] != slug for w in list_works())
        restore_work(slug)
        restore_work(slug)  # 幂等
        assert any(w["slug"] == slug for w in list_works())
    finally:
        try:
            archive_work(slug)
            delete_work(slug)
        except Exception:
            pass


def test_archive_chapter_idempotent(store):
    store.save_chapter(8, "x", title="八")
    assert store.archive_chapter(8, "一") is True
    assert store.archive_chapter(8, "二") is True
    assert store.restore_chapter(8) is True
    assert store.restore_chapter(8) is True

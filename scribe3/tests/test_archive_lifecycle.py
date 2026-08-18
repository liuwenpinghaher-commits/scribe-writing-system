"""存档业务:作品废弃箱 / 章节软归档 / emergency 闸放行 / 过滤器。

作品注册表函数(create_work/archive_work/…)的 url 默认读 SCRIBE3_SURREAL_URL
(生产 8001)。CI 与本地单测必须显式传 store fixture 的 url,写法对齐
test_work_lifecycle.py——绝不可连默认生产端口。
"""
from __future__ import annotations

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


def test_archive_work_missing_raises(store):
    with pytest.raises(ValueError, match="不存在"):
        archive_work("__no_such_work_for_archive__", url=store.url)


def test_restore_work_missing_raises(store):
    with pytest.raises(ValueError, match="不存在"):
        restore_work("__no_such_work_for_restore__", url=store.url)


def test_archive_work_idempotent_and_roundtrip(store):
    slug = create_work("存档审查临时书", url=store.url)["slug"]
    try:
        archive_work(slug, url=store.url)
        archive_work(slug, url=store.url)  # 幂等
        assert any(w["slug"] == slug for w in archived_works(url=store.url))
        assert all(w["slug"] != slug for w in list_works(url=store.url))
        restore_work(slug, url=store.url)
        restore_work(slug, url=store.url)  # 幂等
        assert any(w["slug"] == slug for w in list_works(url=store.url))
    finally:
        try:
            archive_work(slug, url=store.url)
            delete_work(slug, url=store.url)
        except Exception:
            pass


def test_archive_chapter_idempotent(store):
    store.save_chapter(8, "x", title="八")
    assert store.archive_chapter(8, "一") is True
    assert store.archive_chapter(8, "二") is True
    assert store.restore_chapter(8) is True
    assert store.restore_chapter(8) is True


def test_restore_version_writes_back_without_old_craft_gate(store, monkeypatch):
    """恢复通道不再走已删工艺闸，正文直接写回。"""
    store.save_chapter(9, "旧稿正文AAA", title="九")
    vid = store.add_chapter_version(9, "历史版本BBB", label="v1", kind="checkpoint")
    store.save_chapter(9, "当前稿CCC", title="九")
    monkeypatch.setattr(A, "_enqueue_ingest", lambda bg, work, seq: True)

    c = _client(store)
    r = c.post("/chapters/9/restore-version?work=main", json={
        "version_id": vid, "label": "从存档恢复", "reingest": False,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "restored"
    ch = store.get_chapter(9)
    assert "历史版本BBB" in (ch.get("prose") or "")


def test_restore_version_path_not_world_write_gated():
    assert A._is_rest_world_write_path("/chapters/3/restore-version") is False


def test_archived_works_retention_metadata(store):
    """废弃箱附保留期提示字段(不自动 purge)。"""
    slug = create_work("保留期提示临时书", url=store.url)["slug"]
    try:
        archive_work(slug, url=store.url)
        rows = [w for w in archived_works(url=store.url) if w["slug"] == slug]
        assert rows
        w = rows[0]
        assert "retention_days" in w
        assert "days_in_trash" in w
        assert "purge_recommended" in w
        assert isinstance(w["retention_days"], int)
    finally:
        try:
            delete_work(slug, url=store.url)
        except Exception:
            pass

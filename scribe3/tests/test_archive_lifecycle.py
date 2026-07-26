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


def test_restore_version_skips_craft_gate_and_leaves_checkpoint(store, monkeypatch):
    """版本恢复专用通道:跳过工艺门、留审计版、可排 ingest。"""
    from scribe3.verify_craft_compliance import evaluate_save_craft_gate

    store.save_chapter(9, "旧稿正文AAA", title="九")
    vid = store.add_chapter_version(9, "历史版本BBB", label="v1", kind="checkpoint")
    store.save_chapter(9, "当前稿CCC", title="九")  # 当前已偏离

    # 若走普通 save-chapter 且 craft gate 全挡,恢复会 409;专用通道必须成功
    def _block_all(*a, **kw):
        return {"allowed": False, "code": "craft_gate", "detail": "should not block restore"}
    monkeypatch.setattr(
        "scribe3.verify_craft_compliance.evaluate_save_craft_gate", _block_all, raising=False)

    enq = []
    monkeypatch.setattr(A, "_enqueue_ingest", lambda bg, work, seq: enq.append(seq) or True)

    c = _client(store)
    r = c.post("/chapters/9/restore-version?work=main", json={
        "version_id": vid, "label": "从存档恢复", "reingest": True,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "restored"
    assert body.get("reingest_enqueued") is True
    assert enq == [9]
    ch = store.get_chapter(9)
    assert "历史版本BBB" in (ch.get("prose") or "")
    # 版本史应出现恢复审计点
    labels = [v.get("label") for v in store.list_chapter_versions(9)]
    assert any("恢复" in (lb or "") for lb in labels)


def test_restore_version_path_not_world_write_gated():
    assert A._is_rest_world_write_path("/chapters/3/restore-version") is False


def test_archived_works_retention_metadata():
    """废弃箱附保留期提示字段(不自动 purge)。"""
    slug = create_work("保留期提示临时书")["slug"]
    try:
        archive_work(slug)
        rows = [w for w in archived_works() if w["slug"] == slug]
        assert rows
        w = rows[0]
        assert "retention_days" in w
        assert "days_in_trash" in w
        assert "purge_recommended" in w
        assert isinstance(w["retention_days"], int)
    finally:
        try:
            delete_work(slug)
        except Exception:
            pass

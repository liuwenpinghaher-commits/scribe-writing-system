"""CAS 真库五断言。无 Surreal 二进制则跳过，不在本机硬起库。"""
from __future__ import annotations

import os

import pytest

from scribe3.outline_status import intro_text_changed
from scribe3.tests.conftest import SURREAL_BIN

pytestmark = pytest.mark.skipif(
    not (SURREAL_BIN and os.path.isfile(SURREAL_BIN)),
    reason="no SurrealDB 3.x binary",
)


def test_cas_stale_freezes_and_bumps_rev(store):
    store.save_chapter(1, "", title="一")
    store.update_chapter_meta(1, {"outline_status": "stale", "outline_rev": 0})
    out = store.cas_refreeze_chapter(1)
    assert out["ok"] is True
    assert out["idempotent"] is False
    assert out["outline_status"] == "frozen"
    assert out["outline_rev"] == 1
    ch = store.get_chapter(1)
    assert ch["outline_status"] == "frozen"
    assert int(ch["outline_rev"] or 0) == 1


def test_cas_frozen_is_idempotent(store):
    store.save_chapter(1, "", title="一")
    store.update_chapter_meta(1, {"outline_status": "frozen", "outline_rev": 4})
    out = store.cas_refreeze_chapter(1)
    assert out["ok"] is True
    assert out["idempotent"] is True
    assert out["outline_rev"] == 4
    again = store.cas_refreeze_chapter(1)
    assert again["idempotent"] is True
    assert again["outline_rev"] == 4


def test_cas_volume_skips_archived(store):
    vid = store.add_volume("卷一", sort_order=0)
    store.create_chapter(title="活", volume_id=vid)
    store.create_chapter(title="档", volume_id=vid)
    store.update_chapter_meta(1, {"outline_status": "stale"})
    store.update_chapter_meta(2, {"outline_status": "stale"})
    assert store.archive_chapter(2, "测") is True
    out = store.cas_refreeze_volume(vid)
    assert 1 in out["seqs"]
    assert 2 not in out["seqs"]
    assert store.get_chapter(1)["outline_status"] == "frozen"
    assert store.get_chapter(2).get("archived") is True


def test_cas_missing_chapter(store):
    out = store.cas_refreeze_chapter(40404)
    assert out["ok"] is False
    assert out["code"] == "chapter_missing"


def test_ws_only_intro_does_not_count_as_change():
    assert intro_text_changed("华山成核", "  华山成核  ") is False
    assert intro_text_changed("华山成核", "华山成核那一夜") is True

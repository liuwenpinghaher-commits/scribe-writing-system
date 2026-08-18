"""R8 W3/W5/W8/W9: 存稿走定稿门 + span preview + unattended check."""
from __future__ import annotations

import os

from fastapi import BackgroundTasks, HTTPException

from scribe3.revise_span import resolve_span, run_span_revise
from scribe3.unattended_scene import (
    UNATTENDED_PARK_REASON,
    unattended_park_artifact,
    unattended_scene_ok,
)


def test_danger_draft_without_env_is_not_skip_400(monkeypatch):
    os.environ.pop("SCRIBE3_ALLOW_SKIP_GATES", None)
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "0")
    from scribe3.tests.test_finalize_gate import FakeStore, _install_fake_store
    from scribe3.api.models import SaveChapterReq
    st = FakeStore()
    A = _install_fake_store(monkeypatch, st)
    try:
        out = A.save_chapter(
            SaveChapterReq(seq=1, prose="甲乙丙丁" * 30, title="一", danger_draft=True),
            BackgroundTasks(), work="test")
        assert out["status"] == "saved"
    except HTTPException as e:
        assert e.status_code != 400


def test_unattended_park_is_human_string():
    art = unattended_park_artifact({"ok": False, "missing": ["narrative_contract"]})
    assert isinstance(art["pilot_park"], str)
    assert art["pilot_park"] is not True
    assert "场面合同" in art["pilot_park"]
    assert art["pilot_park"] == UNATTENDED_PARK_REASON
    assert art["missing"] == ["narrative_contract"]


def test_restore_finalize_raise_does_not_persist(monkeypatch):
    from scribe3.tests.test_finalize_gate import FakeStore, _install_fake_store
    st = FakeStore()
    st.save_chapter(9, "当前稿CCC", title="九")
    A = _install_fake_store(monkeypatch, st)
    monkeypatch.setattr(A, "_chapter_op_busy", lambda *a, **k: False, raising=False)
    # 恢复通道不再走工艺闸；这里只确认不会因旧模块缺失而崩，且正文能改。
    from scribe3.api.models import RestoreVersionReq
    out = A.restore_chapter_version(
        9, RestoreVersionReq(prose="历史版本BBB", reingest=False),
        BackgroundTasks(), work="test")
    assert out["status"] == "restored"
    assert (st.get_chapter(9) or {}).get("prose") == "历史版本BBB"


def test_save_handler_saves_when_finalize_off(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "0")
    from scribe3.tests.test_finalize_gate import FakeStore, _install_fake_store
    from scribe3.api.models import SaveChapterReq
    st = FakeStore()
    A = _install_fake_store(monkeypatch, st)
    out = A.save_chapter(
        SaveChapterReq(seq=5, prose="他走了一整夜什么也没想明白。" * 20, title="五"),
        BackgroundTasks(), work="test")
    assert out["status"] == "saved"


def test_no_10000_char_floor_in_author_path():
    from scribe3.unattended_scene import unattended_scene_ok as fn
    r = fn({"narrative_contract": {
        "desire": "灰七要守住真匙并挨过夜审点名",
        "obstacle": "冷锅婆堵门讨剩下的半炉香债",
        "turn": "他先交出半炉热灰换今晚过关",
        "cost": "脚印被点破侧门今夜碰不得",
        "bindings": {"evidence_must_show": ["账簿勾了一笔"]},
    }})
    assert r["char_floor"] is None
    assert r["ok"] is True


def test_unattended_missing_contract_not_ok():
    r = unattended_scene_ok({"synopsis": "x" * 800})
    assert r["ok"] is False
    assert "narrative_contract" in r["missing"]


def test_resolve_span_quote_preview_only():
    prose = "冷锅婆说香债过期了。灰七把门开一条缝。"
    s, e, sel = resolve_span(prose, quote="香债过期了")
    assert sel == "香债过期了"
    out = run_span_revise(
        selected=sel,
        instruction="改短一点",
        complete_fn=lambda prompt, system=None: "债过期了",
    )
    assert out["applied"] is False
    assert out["replaced"] == "债过期了"
    assert "diff" in out
    assert "persist" not in out

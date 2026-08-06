"""写作导演 P0 · WorkflowSnapshot 纯函数 + HTTP。"""
from __future__ import annotations

import pytest

from scribe3.director import build_workflow_snapshot, PILOT_LABELS
from scribe3.pilot import write_state


class MiniStore:
    def __init__(self):
        self.intent = {"reader_feeling": "沉重而暖", "red_lines": "不美化"}
        self.chapters = [
            {"seq": 1, "title": "一", "synopsis": "x", "prose": ""},
            {"seq": 2, "title": "二", "synopsis": "", "prose": ""},
        ]
        self._pilot = {}
        self.chars = [{"id": "role:沈砚", "name": "沈砚"}]

    def get_intent(self):
        return dict(self.intent)

    def chapters_lite(self):
        return [dict(c) for c in self.chapters]

    def list_chapters(self):
        return self.chapters_lite()

    def get_chapter(self, seq):
        for c in self.chapters:
            if int(c["seq"]) == int(seq):
                return dict(c)
        return {}

    def list_characters(self):
        return list(self.chars)

    def max_chapter(self):
        return max(int(c["seq"]) for c in self.chapters)

    def _query(self, q, params=None):
        seq = int((params or {}).get("seq") or 0)
        row = self._pilot.get(seq) or {
            "pilot_state": "idle", "pilot_state_at": None, "pilot_parked": "",
        }
        return [dict(row)]

    def _execute_write(self, q, params=None):
        seq = int((params or {}).get("seq") or 0)
        p = self._pilot.setdefault(seq, {
            "pilot_state": "idle", "pilot_state_at": None, "pilot_parked": "",
        })
        if "pilot_state" in (params or {}) or "$s" in q:
            if params and "s" in params:
                p["pilot_state"] = params["s"]
            if params and "t" in params:
                p["pilot_state_at"] = params["t"]
            if params and "p" in params:
                p["pilot_parked"] = params["p"]


def test_snapshot_no_total_score_and_has_core_keys():
    st = MiniStore()
    write_state(st, 1, "outline_proposed")
    snap = build_workflow_snapshot(st, work="demo", seq=1)
    assert "total_score" not in snap
    assert "composite_score" not in snap
    assert snap["work"] == "demo"
    assert snap["journey"]["stations"]
    assert snap["chapter_lane"]["pilot_state"] == "outline_proposed"
    assert snap["chapter_lane"]["pilot_state_label"] == PILOT_LABELS["outline_proposed"]
    assert snap["next_step"]["id"] == "approve_outline"
    assert "第1章" in snap["suggested_prompt"] or "1" in snap["suggested_prompt"]
    assert snap["ui_directive"]["phase"] == "outline"
    assert snap["ui_directive"]["node"]["ref"] == 1
    assert snap["ui_directive"]["right_tab"] == "chief"
    assert any(s["status"] == "current" for s in snap["journey"]["stations"])


def test_snapshot_picks_first_non_finalized():
    st = MiniStore()
    write_state(st, 1, "finalized")
    write_state(st, 2, "idle")
    snap = build_workflow_snapshot(st, work="demo")
    assert snap["chapter_lane"]["seq"] == 2
    assert snap["next_step"]["id"] == "start_outline"


def test_snapshot_no_chapters_guides_intent_or_chapter():
    st = MiniStore()
    st.chapters = []
    st.chars = []
    st.intent = {}
    snap = build_workflow_snapshot(st, work="empty")
    assert snap["chapter_lane"] is None
    assert snap["next_step"]["id"] in ("set_intent", "add_chapter")


def test_http_workflow_snapshot(monkeypatch):
    import scribe3.app as A
    from fastapi.testclient import TestClient
    st = MiniStore()
    write_state(st, 1, "beats_ready")
    A.set_store(st, work="test")
    monkeypatch.setattr(A, "_store_for", lambda w="main": st, raising=False)
    c = TestClient(A.app)
    r = c.get("/workflow/snapshot?work=test&seq=1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chapter_lane"]["pilot_state"] == "beats_ready"
    assert body["next_step"]["title"]
    assert "total_score" not in body


def test_snapshot_next_step_for_five_pilot_states():
    """Continue samples: ≥5 distinct pilot_state values each yield next_step + suggested_prompt."""
    st = MiniStore()
    states = [
        "idle",
        "outline_proposed",
        "beats_ready",
        "deduced",
        "delivered",
    ]
    seen_ids = []
    for s in states:
        write_state(st, 1, s)
        snap = build_workflow_snapshot(st, work="demo", seq=1)
        assert snap["chapter_lane"]["pilot_state"] == s
        assert snap["next_step"]["id"], s
        assert snap["suggested_prompt"], s
        assert snap["ui_directive"]["right_tab"] == "chief"
        seen_ids.append((s, snap["next_step"]["id"]))
    assert len({s for s, _ in seen_ids}) >= 5
    # continue-like: each state has a usable how_chat / title
    for s, nid in seen_ids:
        snap = build_workflow_snapshot(st, work="demo", seq=1)
        write_state(st, 1, s)
        snap = build_workflow_snapshot(st, work="demo", seq=1)
        assert snap["next_step"].get("title") or snap["next_step"].get("how_chat")

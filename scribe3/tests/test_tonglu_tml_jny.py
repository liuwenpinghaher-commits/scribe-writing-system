"""时间线 TML-02~08 + 旅程 JNY-04~08。不起 Surreal。"""
from __future__ import annotations

import inspect
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tml_05_story_axis_uses_between():
    from scribe3.store.events import EventsMixin
    from scribe3.store.promises import PromisesMixin
    from scribe3.store.characters import CharactersMixin
    from scribe3.store.codex_ext import CodexExtMixin

    ev = inspect.getsource(EventsMixin._all_events_bulk)
    assert "story_chapter >= $lo" in ev
    assert "story_chapter <= $hi" in ev
    tl = inspect.getsource(EventsMixin.timeline)
    assert "ch_from" in tl and "axis=axis" in tl
    assert "faction_event" in tl
    pr = inspect.getsource(PromisesMixin.list_promises)
    assert "setup_chapter >= $lo" in pr
    cs = inspect.getsource(CharactersMixin._all_char_states_bulk)
    assert "chapter >= $lo" in cs
    rel = inspect.getsource(CodexExtMixin._all_relations)
    assert "since_chapter >= $lo" in rel


def test_tml_08_faction_timeline_items():
    from scribe3.store.events import EventsMixin

    class St(EventsMixin):
        def max_chapter(self):
            return 10

        def get_intent(self):
            return {}

        def _ev_chapter_map(self):
            return {}

        def _all_events_bulk(self, *a, **k):
            return []

        def list_promises(self, **k):
            return []

        def _all_char_states_bulk(self, *a, **k):
            return []

        def _all_relations(self, *a, **k):
            return []

        def list_factions(self):
            return [{"name": "青叶门", "timeline": [{"chapter": 3, "event": "开山"}]}]

    items = St().timeline(1, 10)
    fac = [i for i in items if i["kind"] == "faction_event"]
    assert len(fac) == 1
    assert fac[0]["chapter"] == 3
    assert "开山" in fac[0]["label"]
    assert fac[0]["refs"]["faction"] == "青叶门"


def test_tml_04_memory_denial_uses_facts_at():
    src = (ROOT / "scribe3/api/routers/write.py").read_text(encoding="utf-8")
    assert "facts_at(seq)" in src
    assert "[:16]" in src


def test_tml_frontend_jump_promise_causal_highlight():
    tl = (ROOT / "scribe3/web/src/views/TimelineView.jsx").read_text(encoding="utf-8")
    assert "跳到这章" in tl
    assert "timeline-jump" in tl
    assert "兑现" in tl and "弃置" in tl and "标障眼法" in tl
    assert "advancePromise" in tl
    assert "tl-causal" in tl
    assert "vis-highlighted" in tl
    assert "afterDraw" in tl or "changed" in tl
    craft = (ROOT / "scribe3/web/src/lib/timelineCraft.js").read_text(encoding="utf-8")
    assert "jumpWindowForChapter" in craft
    assert "relatedVisIds" in craft
    assert "causalArcsFromItems" in craft


def test_jny_08_stall_levels():
    from scribe3.pilot import (
        STALL_CRITICAL_SECONDS,
        STALL_SECONDS,
        compute_stall_level,
    )

    now = time.time()
    assert compute_stall_level("drafting", now - 10, "", now=now) == "none"
    assert compute_stall_level("drafting", now - STALL_SECONDS - 10, "", now=now) == "warning"
    assert compute_stall_level(
        "drafting", now - STALL_CRITICAL_SECONDS - 10, "", now=now,
    ) == "critical"
    assert compute_stall_level("drafting", now - STALL_CRITICAL_SECONDS - 10, "作者停一下", now=now) == "parked"
    assert compute_stall_level("delivered", now - STALL_CRITICAL_SECONDS - 10, "", now=now) == "none"


def test_jny_04_05_waiting_approval_and_domain():
    from scribe3.director import WAITING_APPROVAL_STATES, attach_next_domain, build_workflow_snapshot

    assert "outline_proposed" in WAITING_APPROVAL_STATES
    assert attach_next_domain({"id": "set_intent"})["domain"] == "intent.northstar"
    assert attach_next_domain({"id": "start_outline"})["domain"] == "chapter.outline"
    assert attach_next_domain({"id": "unpark"}, "draft")["domain"] == "chapter.draft"

    class St:
        def get_intent(self):
            return {"reader_feeling": "先冷后烫", "red_lines": "不泄密"}

        def chapters_lite(self):
            return [{"seq": 1, "title": "一"}]

        def list_characters(self):
            return [{"name": "柳岸青"}]

        def list_motifs(self):
            return [{"name": "灯"}, {"name": "债"}, {"name": "炉"}]

        def get_pilot_state_fields(self, seq):
            return {"pilot_state": "outline_proposed", "pilot_parked": ""}

        def set_pilot_state(self, *a, **k):
            return None

        def count_canon_debt(self):
            return {"total": 0, "high": 0}

        def list_canon_candidates(self, **k):
            return []

    snap = build_workflow_snapshot(St(), work="book", seq=1)
    assert snap["waiting_approval"] is True
    assert snap["chapter_lane"]["waiting_approval"] is True
    assert snap["next_step"]["id"] == "approve_outline"
    assert snap["next_step"]["domain"] == "chapter.outline"
    pipe = snap["chapter_lane"]["pipeline"]
    cur = next(p for p in pipe if p["status"] == "current")
    assert cur["needs_author"] is True


def test_jny_frontend_approval_backoff_rollback():
    jv = (ROOT / "scribe3/web/src/views/JourneyView.jsx").read_text(encoding="utf-8")
    assert "等待你审批" in jv
    assert "journey-waiting-approval" in jv
    assert "journey-stall-critical" in jv
    assert "journey-parked" in jv
    cap = (ROOT / "scribe3/web/src/WorkflowCapsule.jsx").read_text(encoding="utf-8")
    assert "isStale" in cap or "stale" in cap
    assert "48000" in cap
    assert "domainHintFromNext" in cap or "next_step?.domain" in cap
    rb = (ROOT / "scribe3/web/src/lib/pilotRollback.js").read_text(encoding="utf-8")
    assert "被打回" in rb
    assert "domainHintFromNext" in rb
    assert "set_intent" in rb and "intent.northstar" in rb

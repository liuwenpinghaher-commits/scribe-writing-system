"""待审正典业务链合同：讨论捕获 → 分类入队 → 批入正典（无 Surreal 子进程）。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scribe3.memory_capture import MemoryCapture, turn_event, classify


class _FakePendingStore:
    """最小 store：pending 队列 + fact 落库。"""

    def __init__(self):
        self.db_name = "test"
        self.events = {}
        self.claims = []
        self.facts = []
        self.entities = {"role:jia": SimpleNamespace(id="role:jia", name="甲", kind="character")}
        self._claim_i = 0
        self.messages = []

    def enqueue_memory_event(self, event_id, work, event_type, payload, thread_id=None):
        self.events[event_id] = {
            "event_id": event_id, "work": work, "event_type": event_type,
            "payload": payload, "thread_id": thread_id, "status": "pending",
            "attempts": 0,
        }

    def get_memory_event(self, event_id):
        return self.events.get(event_id)

    def begin_processing_event(self, event_id):
        e = self.events[event_id]
        e["status"] = "processing"
        e["attempts"] = int(e.get("attempts") or 0) + 1

    def mark_event_complete(self, event_id):
        self.events[event_id]["status"] = "complete"

    def mark_event_failed(self, event_id, err):
        self.events[event_id]["status"] = "failed"
        self.events[event_id]["error"] = err

    def count_memory_events(self, **kw):
        return 0

    def reclaim_stale_processing_events(self, **kw):
        return 0

    def claim_pending_events(self, **kw):
        return []

    def characters(self):
        return list(self.entities.values())

    def all_entities(self):
        return list(self.entities.values())

    def list_places(self):
        return []

    def entity(self, eid):
        return self.entities.get(eid)

    def add_entity(self, e):
        self.entities[e.id] = e
        return e

    def add_pending_authority_claim(self, work, text, **kw):
        self._claim_i += 1
        cid = f"c{self._claim_i}"
        self.claims.append({
            "id": cid, "work": work, "text": text, "status": "pending", **kw,
        })
        return cid

    def list_pending_authority_claims(self, work=None, status="pending"):
        out = self.claims
        if work:
            out = [c for c in out if c.get("work") == work]
        if status:
            out = [c for c in out if c.get("status") == status]
        return out

    def resolve_pending_authority_claim(self, claim_id, decision, **kw):
        # 委托真实逻辑需要完整 store；此处测 capture 入队即可
        raise NotImplementedError

    def add_memory_item(self, **kw):
        return "mem:1"

    def add_chat_message(self, **kw):
        self.messages.append(kw)

    def maybe_autotitle_thread(self, *a, **k):
        return None


def test_classify_identity_to_canonical_claim():
    d = classify("甲的真实身份是细作", None, entity_hits=["role:jia"], risk_hit=True)
    assert d.route == "canonical_claim"


def test_capture_turn_routes_to_pending_queue():
    st = _FakePendingStore()
    cap = MemoryCapture(st)
    # domain signals need list of entities for anti-lookup
    r = cap.capture_event(turn_event(
        "甲的真实身份是细作",
        event_id="turn:t1", work="test", thread_id="th1",
        classification="canonical",  # explicit if heuristic needs it
        entity="role:jia", attribute="identity", value="细作",
    ))
    assert r.get("status") == "complete"
    claims = st.list_pending_authority_claims(work="test", status="pending")
    assert len(claims) >= 1
    assert "真实身份" in claims[0]["text"] or claims[0].get("value") == "细作"


def test_chat_turn_log_captures_on_discuss_user(monkeypatch):
    """讨论咽喉点 user 落库后必须触发捕获（待审正典生产入口）。"""
    from scribe3.api.services import thread_helpers as th

    calls = []

    def _cap(store, **kw):
        calls.append(kw)

    monkeypatch.setattr(th, "_capture_turn_memory", _cap)
    # also rebind name used inside class method when resolved from module
    st = _FakePendingStore()
    log = th._ChatTurnLog(
        st, user_text="乙真名是鬼宿", chapter=2, stage="discuss", thread_id="th-d",
    )
    with log:
        pass
    assert st.messages and st.messages[0]["role"] == "user"
    assert calls, "讨论 user 必须调用 _capture_turn_memory"
    assert calls[0]["text"] == "乙真名是鬼宿"
    assert calls[0]["chapter"] == 2
    assert calls[0]["turn_id"] == log.turn_id


def test_capture_turn_memory_flag_and_call(monkeypatch):
    from scribe3.api.services import thread_helpers as th
    from scribe3.api import app_impl as core

    monkeypatch.setattr(core, "_flag_enabled", lambda k: True)
    st = _FakePendingStore()
    seen = []

    class _Cap:
        def __init__(self, store):
            self.store = store

        def capture_event(self, ev):
            seen.append(ev)
            return {"status": "complete"}

    monkeypatch.setattr("scribe3.memory_capture.MemoryCapture", _Cap)
    th._capture_turn_memory(
        st, work="test", thread_id="t", turn_id="abc", text="真实身份是内鬼", chapter=1,
    )
    assert len(seen) == 1
    assert seen[0].payload.get("text") == "真实身份是内鬼"

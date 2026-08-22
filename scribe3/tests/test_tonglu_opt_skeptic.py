"""Skeptic-fix round: drive real endpoints, no Surreal subprocess."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from scribe3.advisory_ttl import accept_advisory, mark_advisory_pending
from scribe3.canon_apply_store import apply_item_to_store
from scribe3.canon_loop import _undo_applied
from scribe3.degrade_state import persist_degraded_chapter_state
from scribe3.discussion_quality import validate_discussion_claims
from scribe3.ingest_integrity import heal_ingest_if_needed, load_ingest_checkpoint
from scribe3.live import _normalize_live_note
from scribe3.playbook.context import build_ctx, prev_chapter_state
from scribe3.playbook.memory_store import MemoryPlaybookStore, clear_frozen_for_seq
from scribe3.playbook.prompts import _iron_head, play_generate
from scribe3.promise_overdue_gate import check_overdue_hard
from scribe3.store.canon_candidates import candidate_is_expired
from scribe3.store.materials import rank_materials_hybrid


def _client(monkeypatch, st, work="main"):
    import scribe3.app as A
    import scribe3.api.app_impl as impl
    A.set_store(st, work=work)
    monkeypatch.setattr(A, "_store_for", lambda w="main": st, raising=False)
    monkeypatch.setattr(impl, "_store_for", lambda w="main": st, raising=False)
    return TestClient(A.app)


class _PilotStore:
    def __init__(self):
        self.pilot = {
            3: {"pilot_state": "checked", "pilot_parked": "full_check blocking"},
        }
        self.rows = {
            "chapter_draft": [{"seq": 3, "status": "frozen", "text": "旧稿"}],
            "chapter_state": [],
            "duty_card": [],
            "chapter_play": [],
            "chapter_contract": [],
            "chapter_deduce": [],
        }

    def get_pilot_state_fields(self, seq):
        return dict(self.pilot.get(int(seq), {}))

    def set_pilot_state(self, seq, state, parked="", *, at=None):
        self.pilot[int(seq)] = {"pilot_state": state, "pilot_parked": parked}


def test_dir_03_reset_step_force_rollback_changes_state(monkeypatch):
    from scribe3.api.models import PilotApproveReq
    m = PilotApproveReq(seq=3, force_rollback=True, to_state="drafting")
    assert m.force_rollback is True
    assert m.to_state == "drafting"
    st = _PilotStore()
    c = _client(monkeypatch, st)
    r = c.post(
        "/pilot/reset-step",
        json={"seq": 3, "force_rollback": True, "to_state": "drafting"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["force_rollback"] is True
    assert body["state"] == "drafting"
    assert st.get_pilot_state_fields(3)["pilot_state"] == "drafting"
    assert all(rec.get("status") != "frozen" for rec in st.rows["chapter_draft"])


def test_dir_01_execute_false_roundtrip(monkeypatch):
    class St:
        pass

    st = St()
    c = _client(monkeypatch, st)
    r = c.post(
        "/orchestration/proposal/apply",
        json={
            "proposal": {"ops": [{"tool": "s3_add_item", "args": {"name": "铜炉"}}]},
            "decision": "approve",
            "execute": False,
        },
    )
    assert r.status_code == 200, r.text
    pid = r.json()["proposal"]["id"]
    got = c.get(f"/orchestration/proposal/{pid}")
    assert got.status_code == 200, got.text
    assert got.json()["id"] == pid
    assert got.json()["ops"]


def test_dir_04_live_sse_three_event_shapes(monkeypatch):
    import scribe3.api.app_impl as impl

    async def fake_live_stream(*_a, **_k):
        yield 'retry: 3000\ndata: {"table": "_init"}\n\n'
        yield 'data: {"table": "chapter", "action": "UPDATE", "id": "chapter:1"}\n\n'
        yield 'data: {"table": "promise", "action": "CREATE", "id": "promise:p1"}\n\n'
        yield 'data: {"table": "faction", "action": "DELETE", "id": "faction:x"}\n\n'

    monkeypatch.setattr(impl, "live_stream", fake_live_stream)
    c = TestClient(impl.app)
    with c.stream("GET", "/live?work=main") as resp:
        assert resp.status_code == 200
        text = b"".join(resp.iter_bytes()).decode("utf-8", errors="replace")
    assert '"table": "_init"' in text or '"table":"_init"' in text
    assert "chapter" in text and "UPDATE" in text
    assert "promise" in text and "CREATE" in text
    assert "faction" in text and "DELETE" in text
    create = _normalize_live_note("chapter", {"action": "CREATE", "id": "chapter:2"})
    update = _normalize_live_note("promise", {"type": "UPDATE", "record": "promise:p"})
    delete = _normalize_live_note("faction", {"op": "DELETE", "thing": "faction:x"})
    assert create.get("action") == "CREATE" and create.get("id")
    assert update.get("action") == "UPDATE" and update.get("id")
    assert delete.get("action") == "DELETE" and delete.get("id")


def test_dir_05_overdue_blocker_roundtrip():
    from fastapi import HTTPException
    from scribe3.api.routers.write import _reject_overdue_hard

    rows = [
        {"status": "open", "kind": "promise", "setup_chapter": 1, "payoff_max": 3},
        {"status": "open", "kind": "promise", "setup_chapter": 1, "payoff_max": 3},
        {"status": "open", "kind": "promise", "setup_chapter": 1, "payoff_max": 3},
    ]

    class St:
        def open_promises(self):
            return [p for p in rows if p["status"] == "open"]

        def max_chapter(self):
            return 10

        def get_intent(self):
            return {}

    st = St()
    hit = check_overdue_hard(st)
    assert hit and hit["blocking"] is True
    raised = False
    try:
        _reject_overdue_hard(st)
    except HTTPException as e:
        raised = True
        assert e.status_code == 409
    assert raised
    rows[0]["status"] = "closed"
    assert check_overdue_hard(st) is None
    _reject_overdue_hard(st)


def test_dir_05_motif_blocker_clears_after_seed():
    from scribe3.bible_motifs import evaluate_motif_gap
    from scribe3.director import build_workflow_snapshot

    class St:
        def __init__(self):
            self.motifs = []

        def list_motifs(self):
            return list(self.motifs)

        def get_intent(self):
            return {"reader_feeling": "先冷后烫", "red_lines": "不泄密"}

        def chapters_lite(self):
            return []

        def list_characters(self):
            return [{"name": "柳岸青"}]

        def characters(self):
            return [{"name": "柳岸青"}]

        def count_canon_debt(self):
            return {"total": 0, "high": 0}

        def list_canon_candidates(self, **k):
            return []

    st = St()
    assert evaluate_motif_gap(st)["ok"] is False
    snap = build_workflow_snapshot(st, work="motif-block")
    assert any(b.get("code") == "bible_motifs" for b in snap["blockers"])
    st.motifs = [{"name": "灯与债"}, {"name": "替与真名"}, {"name": "应到之声"}]
    assert evaluate_motif_gap(st)["ok"] is True
    snap2 = build_workflow_snapshot(st, work="motif-block")
    assert not any(b.get("code") == "bible_motifs" for b in snap2["blockers"])


def test_ded_08_prev_state_reads_degraded():
    st = MemoryPlaybookStore()
    persist_degraded_chapter_state(
        st, 1, prev={"place": "华山", "characters": [{"name": "柳岸青", "gender": "男"}]},
        reason="extract_fail",
    )
    prev = prev_chapter_state(st, 2)
    assert prev
    assert prev.get("degraded") is True or prev.get("place") == "华山"
    assert prev.get("place") == "华山"


def test_ded_04_patch_undo_restores_old_value():
    class St:
        def __init__(self):
            self.factions = {"衔尾蛇": {"name": "衔尾蛇", "note": "旧"}}

        def get_faction(self, name):
            row = self.factions.get(name)
            return dict(row) if row else None

        def add_faction(self, name, **kw):
            cur = dict(self.factions.get(name) or {"name": name})
            cur.update(kw)
            self.factions[name] = cur

        def delete_faction(self, name):
            self.factions.pop(name, None)

    st = St()
    rec = apply_item_to_store(st, {
        "module": "faction", "op": "patch", "target": "衔尾蛇",
        "field": "note", "after": "新", "layer": "L2",
    })
    assert rec.get("before", {}).get("note") == "旧"
    assert st.factions["衔尾蛇"]["note"] == "新"
    assert _undo_applied(st, rec) is True
    assert st.factions["衔尾蛇"]["note"] == "旧"
    rec_add = apply_item_to_store(st, {
        "module": "faction", "op": "add", "target": "新帮",
        "after": {"name": "新帮"}, "layer": "L2",
    })
    assert "新帮" in st.factions
    assert _undo_applied(st, rec_add) is True
    assert "新帮" not in st.factions


def test_dir_12_13_letter_and_grid_in_build_ctx(monkeypatch):
    from scribe3.experience import state as exp_state
    from scribe3.tests.test_playbook_context_guides import _Both

    exp_state.clear_work("main")
    exp_state.set_scene_grid("main", 2, {
        "goal": "按回碎片", "conflict": "观测不肯松", "disaster": "体温涨价",
        "reaction": "他咬牙", "dilemma": "交还是按", "decision": "按回去",
        "source": "author",
    })
    world = _Both()
    world.db_name = "main"
    ctx = build_ctx(world, 2)
    assert "按回" in str(ctx.get("scene_grid") or "")
    assert ctx.get("revision_letter_digest")
    head = _iron_head(ctx)
    assert "问诊" in head or "戏格" in head
    play = play_generate({**ctx, "duty": {"must_happen": "按回", "bill": "一层皮"}})
    assert "问诊" in play or "戏格" in play


class _IngestCrashStore:
    """purge 后第一次写炸，留下 checkpoint；第二次写成功。"""

    def __init__(self):
        self.purged: list[int] = []
        self.applied: list[tuple[int, str]] = []
        self._ingest_checkpoints: dict = {}
        self.fail_once = True

    def apply_schema(self):
        return None

    def close(self):
        return None

    def purge_ingest(self, seq):
        self.purged.append(int(seq))
        self.applied = [row for row in self.applied if row[0] != int(seq)]

    def add_fact(self, *a, **k):
        return None

    def add_knowledge(self, *a, **k):
        return None

    def add_event(self, *a, **k):
        return None

    def events_at(self, seq):
        return []


def test_ded_03_apply_delta_fail_then_heal_uses_saved_delta(monkeypatch):
    """apply 在 purge 之后炸 → 检查点留下 delta → heal 不另传 delta 也能救回。"""
    import pytest
    from scribe3.ingest import apply_delta
    from scribe3.ingest_integrity import ingest_needs_replay, load_ingest_checkpoint

    st = _IngestCrashStore()
    calls = {"n": 0}

    def fake_body(store, delta, seq, open_promises):
        calls["n"] += 1
        if store.fail_once:
            store.fail_once = False
            raise RuntimeError("midway after purge")
        n = 0
        for it in delta.get("learned") or []:
            store.applied.append((int(seq), str(it.get("fact") or "")))
            n += 1
        return n

    monkeypatch.setattr("scribe3.ingest._apply_delta_body", fake_body)
    delta = {"learned": [{"who": "柳岸青", "fact": "炉还亮着"}]}
    with pytest.raises(RuntimeError, match="midway after purge"):
        apply_delta(st, delta, 7)
    assert st.purged == [7]
    assert st.applied == []
    cp = load_ingest_checkpoint(st, 7)
    assert ingest_needs_replay(cp) is True
    assert (cp.get("delta") or {}).get("learned")[0]["fact"] == "炉还亮着"

    n = heal_ingest_if_needed(st, 7)  # 只用留下的 delta
    assert n == 1
    assert st.applied == [(7, "炉还亮着")]
    assert ingest_needs_replay(load_ingest_checkpoint(st, 7)) is False


def test_ded_03_store_for_connect_heals_saved_delta(monkeypatch):
    """连库新生 store 会扫 needs_replay 并用留下的 delta 重放。"""
    import pytest
    import scribe3.api.app_impl as impl
    from scribe3.ingest import apply_delta
    from scribe3.ingest_integrity import ingest_needs_replay, load_ingest_checkpoint

    st = _IngestCrashStore()

    def fake_body(store, delta, seq, open_promises):
        if store.fail_once:
            store.fail_once = False
            raise RuntimeError("midway after purge")
        n = 0
        for it in delta.get("learned") or []:
            store.applied.append((int(seq), str(it.get("fact") or "")))
            n += 1
        return n

    monkeypatch.setattr("scribe3.ingest._apply_delta_body", fake_body)
    with pytest.raises(RuntimeError):
        apply_delta(st, {"learned": [{"who": "柳岸青", "fact": "炉还亮着"}]}, 8)
    assert ingest_needs_replay(load_ingest_checkpoint(st, 8)) is True

    impl._stores.clear()
    monkeypatch.setattr(impl, "SurrealStore", lambda *a, **k: st)
    got = impl._store_for("heal-connect")
    assert got is st
    assert st.applied == [(8, "炉还亮着")]
    assert ingest_needs_replay(load_ingest_checkpoint(st, 8)) is False


def test_ded_03_lifespan_heals_cached_store(monkeypatch):
    """进程启动时扫已缓存 store 上的 needs_replay。"""
    import asyncio
    import pytest
    import scribe3.api.app_impl as impl
    from scribe3.ingest import apply_delta
    from scribe3.ingest_integrity import ingest_needs_replay, load_ingest_checkpoint

    st = _IngestCrashStore()

    def fake_body(store, delta, seq, open_promises):
        if store.fail_once:
            store.fail_once = False
            raise RuntimeError("midway after purge")
        n = 0
        for it in delta.get("learned") or []:
            store.applied.append((int(seq), str(it.get("fact") or "")))
            n += 1
        return n

    monkeypatch.setattr("scribe3.ingest._apply_delta_body", fake_body)
    with pytest.raises(RuntimeError):
        apply_delta(st, {"learned": [{"who": "柳岸青", "fact": "炉还亮着"}]}, 9)

    impl.set_store(st, work="heal-life")
    monkeypatch.setattr(impl, "_startup_gateway_guard", lambda: None)
    monkeypatch.setattr(impl, "_close_cached_stores", lambda: None)

    async def exercise():
        async with impl._app_lifespan(impl.app):
            pass

    asyncio.run(exercise())
    assert st.applied == [(9, "炉还亮着")]
    assert ingest_needs_replay(load_ingest_checkpoint(st, 9)) is False


def test_ded_12_health_reads_three_systems(monkeypatch):
    class St:
        def get_frozen(self, table, seq):
            if table == "chapter_draft":
                return {"status": "frozen", "review": {"verdict": "pass"}}
            return None

        def post_analysis_summary(self, seq, prose=None):
            return {"present": True, "verdict": "advisory", "fp_match": True}

        def get_chapter_review_row(self, local):
            return {"coverage": 0.8, "verdict": "pass"}

        def list_motif_instances(self, seq):
            return []

    c = _client(monkeypatch, St())
    r = c.get("/chapters/3/health")
    assert r.status_code == 200, r.text
    h = r.json()
    assert h["post_check_verdict"] == "advisory"
    assert h["review_coverage"] == 0.8
    assert h["playbook_status"]


def test_jny_03_ledger_station_on_all_finalized():
    from scribe3.director import build_workflow_snapshot

    class St:
        def get_intent(self):
            return {"reader_feeling": "先冷后烫", "red_lines": "不泄密"}

        def chapters_lite(self):
            return [{"seq": 1, "title": "一"}, {"seq": 2, "title": "二"}]

        def list_characters(self):
            return [{"name": "柳岸青"}]

        def characters(self):
            return [{"name": "柳岸青"}]

        def list_motifs(self):
            return [{"name": "灯"}, {"name": "债"}, {"name": "炉"}]

        def get_pilot_state_fields(self, seq):
            return {"pilot_state": "finalized", "pilot_parked": ""}

        def set_pilot_state(self, *a, **k):
            return None

        def count_canon_debt(self):
            return {"total": 0, "high": 0}

        def list_canon_candidates(self, **k):
            return []

        def list_promises(self):
            return []

    snap = build_workflow_snapshot(St(), work="book", seq=2)
    assert snap["journey"]["current_station"] == "ledger"
    assert snap["ledger"]["congrats"] == "恭喜完成"
    assert snap["next_step"]["id"] == "book_complete"
    assert snap["journey"].get("focus_chapter") == 2


def test_prm_06_seed_keeps_reason():
    from scribe3.experience.choice_seed import promote_seed_payload
    payload = promote_seed_payload({
        "id": "s1", "text": "井里那口钟迟早要响", "seq": 2,
        "detail": "因为钟还没响", "evidence": "他听见井底一声闷响",
    })
    assert payload["resolution"]
    assert payload["clues"]
    assert payload["evidence"]


def test_mat_06_07_ref_kind_and_hybrid_rank():
    from scribe3.store.materials import rank_materials_hybrid
    items = [
        {"title": "别的", "body": "无关"},
        {"title": "铜炉夜话", "body": "炉火"},
    ]
    ranked = rank_materials_hybrid("铜炉", items)
    assert ranked[0]["title"] == "铜炉夜话"


def test_ded_09_discussion_flags_contradiction():
    flags = validate_discussion_claims(
        "柳岸青不是这本书的人，并无此人",
        {"characters": ["柳岸青"], "world_rules": {"大遮蔽": {}}},
    )
    assert any(f["code"] == "contradict_character" for f in flags)


def test_ded_11_advisory_accept_and_expire():
    class St:
        def __init__(self):
            self.saved = None

        def save_chapter(self, seq, prose):
            self.saved = (seq, prose)

    st = St()
    mark_advisory_pending(4, "待确认的稿", [{"message": "可改收束"}])
    out = accept_advisory(st, 4)
    assert out["ok"] is True
    assert st.saved == (4, "待确认的稿")
    rec = mark_advisory_pending(5, "过期稿", ttl_hours=0)
    rec["expires_at"] = 1
    out2 = accept_advisory(st, 5)
    assert out2["ok"] is False
    assert out2["code"] == "expired"


def test_ded_13_candidate_ttl():
    assert candidate_is_expired({"created_at": 1}, now_ts=1 + 31 * 86400) is True
    assert candidate_is_expired({"created_at": 1_700_000_000}, now_ts=1_700_000_100) is False


def test_cdx_13_extract_prompt_has_schema_keys():
    from scribe3.canon_extract import _llm_extract
    seen = {}

    def complete(prompt):
        seen["p"] = prompt
        return "{}"

    _llm_extract("正文里柳岸青按回碎片。", complete, known_character_names=["柳岸青"])
    assert "schema" in seen["p"]
    assert "character" in seen["p"]


def test_ded_14_supersede_emits_fact_invalidation():
    from scribe3.store.facts_knowledge import FactsKnowledgeMixin
    import inspect
    src = inspect.getsource(FactsKnowledgeMixin.supersede_fact)
    assert '_emit_cache_invalidation("fact"' in src


def test_atl_06_live_members_drop_archived():
    from scribe3.api.services.write_assemble_blocks import _live_known_members

    class St:
        def characters(self):
            return [{"name": "柳岸青"}]

    row = {"known_members": ["柳岸青", "已死的人"]}
    assert _live_known_members(St(), row) == ["柳岸青"]


def test_clear_frozen_helper():
    st = MemoryPlaybookStore()
    st.rows["chapter_draft"].append({"seq": 2, "status": "frozen", "text": "x"})
    clear_frozen_for_seq(st, 2)
    assert st.rows["chapter_draft"][0]["status"] == "superseded"

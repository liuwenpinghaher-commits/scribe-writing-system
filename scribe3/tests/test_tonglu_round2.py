"""铜炉下一轮实施 Spec：阻断项 + 新发现 P0/P1 + 补齐。不起 Surreal。"""
from __future__ import annotations

import inspect
import threading
import time
from pathlib import Path

from scribe3.advisory_ttl import (
    accept_advisory,
    check_advisory_pending,
    mark_advisory_pending,
)
from scribe3.canon_loop import _undo_applied
from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
from scribe3.context_snapshot import snapshot_clear, snapshot_get_or_set
from scribe3.feature_flags import FLAG_REGISTRY, flag_truthy, get_flag
from scribe3.inbox_dismiss import dismiss_inbox_item, filter_inbox, is_dismissed
from scribe3.ingest import grep_back_verify
from scribe3.journey_precheck import journey_precheck_block
from scribe3.motif_craft import schedule_motifs
from scribe3.pending_proposals import get_pending_proposal, save_pending_proposal


ROOT = Path(__file__).resolve().parents[2]


class MemStore:
    """共享 dict 后端，模拟两个 Worker 打同一份库。"""

    def __init__(self, bag=None):
        self.bag = bag if bag is not None else {}
        self.saved = None
        self.motif_updates = []
        self.facts_deleted = []
        self.knowledge_forgot = []
        self.rev = {}
        self._lock = threading.Lock()

    def _execute_write(self, surql, vars=None):
        vars = vars or {}
        s = surql.lower()
        if "advisory_pending" in s:
            seq = int(vars.get("seq") or 0)
            if s.strip().startswith("delete"):
                self.bag.pop(("adv", seq), None)
                return
            self.bag[("adv", seq)] = dict(vars)
            return
        if "inbox_dismissed" in s:
            self.bag[("dis", vars.get("id"))] = True
            return
        if "pending_proposal" in s:
            self.bag[("prop", vars.get("pid"))] = vars.get("p")
            return
        if "update chapter" in s and "where" in s:
            seq = int(vars.get("seq") or 0)
            expected = vars.get("expected")
            with self._lock:
                got = self.rev.get(seq, 0)
                if expected is not None and int(got) != int(expected):
                    return
                self.rev[seq] = got + 1
                self.bag[("ch", seq)] = {"seq": seq, "prose": vars.get("prose"), "rev": self.rev[seq]}
            return
        if "upsert type::record('chapter'" in s or "upsert type::record(\"chapter\"" in s:
            seq = int(vars.get("seq") or 0)
            with self._lock:
                self.rev[seq] = self.rev.get(seq, 0) + 1
                self.bag[("ch", seq)] = {"seq": seq, "prose": vars.get("prose"), "rev": self.rev[seq]}

    def _query(self, surql, vars=None):
        vars = vars or {}
        s = surql.lower()
        if "advisory_pending" in s:
            seq = int(vars.get("seq") or 0)
            rec = self.bag.get(("adv", seq))
            if not rec:
                return []
            return [{
                "seq": seq,
                "advisory_id": rec.get("aid"),
                "prose": rec.get("prose"),
                "items": rec.get("items"),
                "status": rec.get("st"),
                "marked_at": rec.get("ma"),
                "expires_at": rec.get("ex"),
            }]
        if "inbox_dismissed" in s and "select" in s:
            if "item_id=$id" in s or "record('inbox_dismissed'" in s:
                iid = vars.get("id")
                return [{"item_id": iid}] if self.bag.get(("dis", iid)) else []
            return [{"item_id": k[1]} for k in self.bag if k[0] == "dis"]
        if "pending_proposal" in s:
            pid = vars.get("pid")
            if pid:
                raw = self.bag.get(("prop", pid))
                return [{"payload": raw, "status": "pending"}] if raw else []
            out = []
            for k, v in self.bag.items():
                if k[0] == "prop":
                    out.append({"payload": v, "status": "pending"})
            return out
        if "update chapter" in s or "update type::record('chapter'" in s:
            seq = int(vars.get("seq") or 0)
            expected = vars.get("expected")
            with self._lock:
                got = self.rev.get(seq)
                if got is None:
                    return []
                if expected is not None and int(got) != int(expected):
                    return []
                self.rev[seq] = int(got) + 1
                row = {"seq": seq, "prose": vars.get("prose"), "rev": self.rev[seq]}
                self.bag[("ch", seq)] = row
                return [row]
        return []

    def save_chapter(self, seq, prose, title="", focalizer=None, _today=None, expected_version=None):
        if expected_version is not None:
            rows = self._query(
                "UPDATE chapter SET prose=$prose WHERE seq=$seq AND rev=$expected RETURN AFTER",
                {"seq": seq, "prose": prose, "expected": expected_version},
            )
            if not rows:
                raise ValueError("chapter_conflict")
            self.saved = (seq, prose)
            return
        self._execute_write("UPSERT type::record('chapter',$seq) SET prose=$prose", {"seq": seq, "prose": prose})
        self.saved = (seq, prose)

    def get_chapter(self, seq):
        return self.bag.get(("ch", seq))

    def update_motif(self, mid, fields):
        self.motif_updates.append((mid, dict(fields)))

    def delete_fact(self, oid):
        self.facts_deleted.append(oid)
        return True

    def forget_knowledge(self, knower, eid, until=0):
        self.knowledge_forgot.append((knower, eid, until))

    def get_intent(self):
        return self.bag.get("intent") or {}

    def list_motifs(self):
        return self.bag.get("motifs") or []


def test_b01_advisory_persists_across_workers():
    bag = {}
    w1, w2 = MemStore(bag), MemStore(bag)
    mark_advisory_pending(7, "好稿", [{"m": "收束"}], store=w1)
    rec = check_advisory_pending(7, store=w2)
    assert rec and rec["prose"] == "好稿"
    out = accept_advisory(w2, 7)
    assert out["ok"] is True
    assert w2.saved == (7, "好稿")


def test_b01_advisory_survives_process_cache_expiry():
    from scribe3.advisory_ttl import get_advisory_pending
    bag = {}
    st = MemStore(bag)
    mark_advisory_pending(8, "还在", store=st)
    time.sleep(1.05)
    rec = get_advisory_pending(8, store=st)
    assert rec and rec["prose"] == "还在"


def test_b02_save_chapter_cas_one_wins():
    st = MemStore()
    st.rev[3] = 1
    st.bag[("ch", 3)] = {"seq": 3, "rev": 1, "prose": "旧"}
    err = []

    def writer(prose):
        try:
            st.save_chapter(3, prose, expected_version=1)
        except ValueError as e:
            err.append(str(e))

    t1 = threading.Thread(target=writer, args=("甲",))
    t2 = threading.Thread(target=writer, args=("乙",))
    t1.start(); t2.start(); t1.join(); t2.join()
    assert st.rev[3] == 2
    assert err.count("chapter_conflict") == 1


def test_b03_motif_phase_persists():
    from scribe3.motif_craft import apply_motif_advances
    st = MemStore()
    motifs = [{"id": "灯与债", "phase": "seed", "name": "灯与债"}]
    out = schedule_motifs(motifs, {"灯与债": [1, 2, 3]}, 4, store=st)
    assert out["rows"][0]["phase"] == "echo"
    assert st.motif_updates == []
    assert apply_motif_advances(out.get("advances"), st) == 1
    assert st.motif_updates and st.motif_updates[0][1]["phase"] == "echo"


def test_n01_snapshot_clear_prevents_cross_chapter():
    snapshot_clear()
    a = snapshot_get_or_set("seq5", lambda: "五")
    assert a == "五"
    snapshot_clear()
    b = snapshot_get_or_set("seq5", lambda: "六")
    assert b == "六"


def test_n01_write_entries_call_snapshot_clear():
    from scribe3.playbook.pipeline import run_stage
    from scribe3.api.routers.write import chat_write, chat_write_post
    from scribe3.api.routers.chapters import loop_chapter
    from scribe3.api.routers.pilot_inbox import pilot_step
    assert "snapshot_clear" in inspect.getsource(run_stage)
    assert "snapshot_clear" in inspect.getsource(chat_write)
    assert "snapshot_clear" in inspect.getsource(chat_write_post)
    assert "snapshot_clear" in inspect.getsource(loop_chapter)
    assert "snapshot_clear" in inspect.getsource(pilot_step)


def test_n02_letter_grid_in_l2_t3():
    from scribe3.context_budget import L2_DROP_TIER
    assert "revision_letter_digest" in L2_DROP_TIER["T3"]
    assert "scene_grid" in L2_DROP_TIER["T3"]


def test_n03_hint_replaces_not_appends():
    src = Path(ROOT / "scribe3/playbook/pipeline.py").read_text(encoding="utf-8")
    assert 'hint[0] = "换个角度：贴着另一个在场的人看见的那一面，重写这一场。"' in src
    assert 'hint[0] + " 换个角度' not in src
    assert '(hint[0] + " 换个角度' not in src


def test_n04_journey_precheck_default_on_and_three_gates():
    entry = next(f for f in FLAG_REGISTRY if f.name == "SCRIBE3_JOURNEY_PRECHECK")
    assert entry.default == "1"
    st = MemStore()
    st.bag["intent"] = {}
    st.bag["motifs"] = []
    import os
    os.environ["SCRIBE3_JOURNEY_PRECHECK"] = "1"
    try:
        block = journey_precheck_block(st)
        assert block and block["code"] == "journey_precheck"
        st.bag["intent"] = {"north_star": "今晚必须按回碎片"}
        st.bag["motifs"] = [{"id": "灯"}]
        assert journey_precheck_block(st) is None
    finally:
        os.environ["SCRIBE3_JOURNEY_PRECHECK"] = "0"
    from scribe3.api.routers.write import chat_write, chat_write_post
    from scribe3.api.routers.chapters import loop_chapter
    assert "journey_precheck_block" in inspect.getsource(chat_write)
    assert "journey_precheck_block" in inspect.getsource(chat_write_post)
    assert "journey_precheck_block" in inspect.getsource(loop_chapter)


def test_n05_inbox_dismiss_db_ssot():
    bag = {}
    a, b = MemStore(bag), MemStore(bag)
    dismiss_inbox_item(a, "needs_human:9")
    assert is_dismissed(b, "needs_human:9")
    items = filter_inbox(b, [{"id": "needs_human:9"}, {"id": "lesson:1"}])
    assert [i["id"] for i in items] == ["lesson:1"]


def test_n06_pending_proposal_no_setattr():
    st = MemStore()
    rec = save_pending_proposal(st, {"summary": "改设定"})
    assert rec["id"]
    assert not hasattr(st, "_pending_proposals")
    got = get_pending_proposal(MemStore(st.bag), rec["id"])
    assert got and got["summary"] == "改设定"


def test_n07_lock_ttl_20min():
    from scribe3.api.routers.write import _lock_chapter_run
    assert inspect.signature(_lock_chapter_run).parameters["ttl_seconds"].default == 1200


def test_n08_live_import_guard():
    import scribe3.live as L
    assert hasattr(L, "AsyncSurreal")
    src = Path(L.__file__).read_text(encoding="utf-8")
    assert "except ImportError" in src


def test_n09_quality_ttl_2s_and_invalidate():
    from scribe3.api.routers import quality as Q
    assert Q._QUALITY_TTL_SEC == 2.0
    Q._QUALITY_TTL[("main", 1)] = (0.0, {"old": True})
    Q.invalidate_quality_cache("main")
    assert ("main", 1) not in Q._QUALITY_TTL
    from scribe3.store.chapters import ChaptersMixin
    assert "invalidate_quality_cache" in inspect.getsource(ChaptersMixin.save_chapter)


def test_n10_undo_fact_and_knowledge():
    st = MemStore()
    assert _undo_applied(st, {"kind": "fact", "oid": "fact:x"}) is True
    assert st.facts_deleted == ["fact:x"]
    assert _undo_applied(st, {"kind": "knowledge", "entity_id": "fact:y", "knower_id": "role:甲"}) is True
    assert st.knowledge_forgot


def test_n11_n12_frontend_wires():
    tl = (ROOT / "scribe3/web/src/views/TimelineView.jsx").read_text(encoding="utf-8")
    assert "因果根已保存" in tl
    assert "保存失败" in tl
    lr = (ROOT / "scribe3/web/src/lib/liveRefresh.js").read_text(encoding="utf-8")
    assert "_reconnect" in lr


def test_s2_cleanup_and_thicken_lock():
    from scribe3.store.connection import ConnectionMixin
    src = inspect.getsource(ConnectionMixin._cleanup_record_refs)
    assert "about_entities" in src
    assert "proposition" in src
    from scribe3.stage_generate import thicken_stage
    assert "acquire_chapter_lock" in inspect.getsource(thicken_stage)
    mcp = (ROOT / "scribe3/mcp/tools_write.py").read_text(encoding="utf-8")
    assert "_object_impact" in mcp or "record_lifecycle_impact" in mcp
    assert "delete_faction" in mcp


def test_s3_learned_unverified_and_reject_hash():
    out = grep_back_verify(
        {"learned": [{"who": "柳岸青", "fact": "炉火在夜里还亮着而且债没有散"}]},
        "正文里没有那几个字。",
    )
    learned = out["delta"]["learned"][0]
    assert learned.get("unverified") is True
    assert learned.get("confidence") == "unverified"
    from scribe3.ingest import _apply_delta_body
    src = inspect.getsource(_apply_delta_body)
    assert "unverified" in src
    from scribe3.store.canon_candidates import CanonCandidatesMixin
    assert "entity_hash" in inspect.getsource(CanonCandidatesMixin.add_canon_candidate)


def test_s3_s4_flags_and_audit():
    assert next(f for f in FLAG_REGISTRY if f.name == "SCRIBE3_GRAPH_RELATION_RECALL").default == "1"
    assert next(f for f in FLAG_REGISTRY if f.name == "SCRIBE3_VOLUME_LEDGER").default == "1"
    assert next(f for f in FLAG_REGISTRY if f.name == "SCRIBE3_DUTY_SUMMARY_LOOKBACK").default == "3"
    assert next(f for f in FLAG_REGISTRY if f.name == "SCRIBE3_DEFAULT_WORK").default == "main"
    design = next(f for f in FLAG_REGISTRY if f.name == "SCRIBE3_DESIGN_BOOK")
    assert "deprecated" in design.description.lower()
    from scribe3.iceberg import codex_thicken_gate_enabled
    assert "append_audit" in inspect.getsource(codex_thicken_gate_enabled)
    from scribe3.orchestration.proposal import apply_proposal_ops
    assert "proposal_reject" in inspect.getsource(apply_proposal_ops)
    src = Path(ROOT / "scribe3/api/app_impl.py").read_text(encoding="utf-8")
    assert "get_flag(\"SCRIBE3_DEFAULT_WORK\")" in src or "get_flag('SCRIBE3_DEFAULT_WORK')" in src


def test_s3_advance_promise_knows_and_cron():
    from scribe3.store.promises import PromisesMixin
    assert "add_knowledge" in inspect.getsource(PromisesMixin.advance_promise)
    from scribe3.agent_crons import check_overdue_promises, build_agent_crons_response
    class St:
        pass
    # count_open_overdue will fail-soft
    r = check_overdue_promises(St())
    assert "overdue" in r
    jobs = build_agent_crons_response()["jobs"]
    assert any(j.get("name") == "check_overdue_promises" for j in jobs)


def test_s5_journey_and_atlas_and_write_layout():
    jv = (ROOT / "scribe3/web/src/views/JourneyView.jsx").read_text(encoding="utf-8")
    assert "chapterPulse" in jv
    assert "pilotStatus" in jv
    assert "chapterStage" in jv
    assert "promisesLedger" in jv
    assert "quality_stalled" in jv
    assert "s3-live" in jv
    nd = (ROOT / "scribe3/web/src/views/atlas/NodeDetail.jsx").read_text(encoding="utf-8")
    assert "addCharState" in nd
    assert "标记状态变化" in nd
    wl = (ROOT / "scribe3/web/src/WriteLayout.jsx").read_text(encoding="utf-8")
    assert "s3-chapter-phase-hint" in wl
    api = (ROOT / "scribe3/web/src/api.js").read_text(encoding="utf-8")
    assert "orchGetProposal" in api
    assert "addCharState" in api
    card = (ROOT / "scribe3/web/src/WriteProposalCard.jsx").read_text(encoding="utf-8")
    assert "orchGetProposal" in card


def test_s3_10_blocker_bidirectional_gate():
    from scribe3.promise_overdue_gate import overdue_hard_block, OVERDUE_HARD_THRESHOLD
    three = overdue_hard_block(3)
    assert three is not None
    two = overdue_hard_block(2)
    if OVERDUE_HARD_THRESHOLD <= 2:
        assert two is not None
    else:
        assert two is None


def test_man_03_and_mat_03_still_in_cleanup():
    from scribe3.store.chapters import ChaptersMixin
    assert "canon_candidate" in inspect.getsource(ChaptersMixin.delete_chapter_permanent)
    from scribe3.store.motifs import MotifsMixin
    assert "待补充" in inspect.getsource(MotifsMixin.add_motif)
    from scribe3.store.chapters import ChaptersMixin as C
    assert "chapter_conflict" in inspect.getsource(C.save_chapter)
    assert "WHERE" in inspect.getsource(C.save_chapter) and "rev=$expected" in inspect.getsource(C.save_chapter)


def test_migration_165_idempotent_text():
    text = (ROOT / "scribe3/migrations/165_tonglu_round2.surql").read_text(encoding="utf-8")
    assert "IF NOT EXISTS" in text
    assert "inbox_dismissed" in text
    assert "entity_hash" in text

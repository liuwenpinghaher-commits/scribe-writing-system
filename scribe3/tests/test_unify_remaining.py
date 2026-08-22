"""统一度剩余项：对照聚合、预算、错误形状、限知、渲染、规划门。不启 Surreal。"""
from __future__ import annotations

from scribe3.http_errors import error_body, shape_http_detail
from scribe3.prompt_renderer import render_slots, shadow_equal
from scribe3.quality_gate import from_existing, gate_result
from scribe3.recall_service import (
    _BUDGET_BY_TAG,
    _SHADOW_RING,
    budget_for,
    record_shadow_stat,
    shadow_diff,
    summarize_recall_shadow,
)
from scribe3.write_commit import commit_if_approved


def test_budget_by_tag_is_single_source():
    assert budget_for("playbook_codex") == 800
    assert budget_for("volume_intro") == 400
    assert budget_for("ledger") == 900
    assert "playbook_codex" in _BUDGET_BY_TAG
    from scribe3.playbook import context as ctx
    assert ctx._CODEX_BUDGET == budget_for("playbook_codex")
    assert ctx._VOLUME_INTRO_BUDGET == budget_for("volume_intro")


def test_recall_shadow_aggregates_by_path():
    _SHADOW_RING.clear()
    record_shadow_stat({"ok": True, "path": "playbook", "threshold_ok": True, "secret_leak_count": 0})
    record_shadow_stat({"ok": True, "path": "playbook", "threshold_ok": False, "secret_leak_count": 0})
    record_shadow_stat({"ok": True, "path": "discuss", "threshold_ok": True, "secret_leak_count": 0})
    out = summarize_recall_shadow()
    assert out["by_path"]["playbook"]["n"] == 2
    assert out["by_path"]["playbook"]["threshold_ok_rate"] == 0.5
    assert out["by_path"]["discuss"]["threshold_ok_rate"] == 1.0


def test_shadow_vector_channel_recorded(monkeypatch):
    monkeypatch.setenv("SCRIBE3_RECALL_SHADOW_VECTOR", "1")
    monkeypatch.setenv("SCRIBE3_RECALL_SHADOW_VECTOR_SYNC", "1")

    class St:
        def facts_at(self, seq):
            return [{"entity_id": "role:柳岸青", "attribute": "身体", "value": "四十二度不是病是标价"}]

        def hybrid_recall(self, q, chapter, k=8):
            return [{"entity_id": "role:柳岸青", "attribute": "身体", "value": "四十二度不是病是标价"}]

    rec = shadow_diff(St(), 1, "role:柳岸青", "柳岸青 / 身体：四十二度不是病是标价", query="柳岸青", path="playbook")
    assert rec.get("ok") is True
    assert "hybrid" in (rec.get("channels") or []) or "facts_at" in (rec.get("channels") or [])


def test_as_playbook_store_reuses_mem():
    from scribe3.stage_generate import _PLAYBOOK_STORES, _as_playbook_store

    class St:
        pass

    st = St()
    a = _as_playbook_store(st)
    b = _as_playbook_store(st)
    assert a is b
    assert _PLAYBOOK_STORES.get(st) is a
    assert getattr(st, "_playbook_mem", None) is None


def test_http_error_shape_lock():
    body = error_body("stage_gone", "这一站拆了", http=410)
    assert set(body) >= {"code", "message"}
    assert body["code"] == "stage_gone"
    shaped = shape_http_detail("炸了")
    assert shaped["code"] == "http_error"
    assert "炸了" in shaped["message"]
    shaped2 = shape_http_detail({"code": "x", "message": "人话"})
    assert shaped2 == {"code": "x", "message": "人话"}


def test_plan_volumes_accept_and_decline():
    calls = []
    out = commit_if_approved("s3_plan_volumes", False, lambda: calls.append("w") or {"volumes": 1})
    assert out["status"] == "declined"
    assert calls == []
    out2 = commit_if_approved("s3_plan_volumes", True, lambda: {"volumes": 2, "planned": True})
    assert out2["status"] == "written"
    assert out2.get("volumes") == 2
    out3 = commit_if_approved(
        "s3_plan_chapter_accounts", False,
        lambda: {"volume_id": "v1"},
    )
    assert out3["status"] == "declined"


def test_join_uses_prompt_renderer_markers(monkeypatch):
    from scribe3.context_budget import join_generation_segments
    from scribe3.feature_flags import flag_truthy as _orig

    pieces = [
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】甲"},
        {"name": "drama_contract", "layer": "redline", "text": "【戏剧合同】乙"},
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】丙"},
    ]

    def _on(name):
        if name == "SCRIBE3_PROMPT_RENDERER":
            return True
        return _orig(name)

    monkeypatch.setattr("scribe3.feature_flags.flag_truthy", _on)
    joined_on, _rep = join_generation_segments(list(pieces), v2=True)
    assert "【event_drive】" in joined_on
    assert "事件驱动" in joined_on
    assert joined_on.index("事件驱动") < joined_on.index("戏剧合同") < joined_on.index("最终提醒")

    def _off(name):
        if name == "SCRIBE3_PROMPT_RENDERER":
            return False
        return _orig(name)

    monkeypatch.setattr("scribe3.feature_flags.flag_truthy", _off)
    joined_off, _rep2 = join_generation_segments(list(pieces), v2=True)
    assert "【event_drive】" not in joined_off
    assert "事件驱动" in joined_off
    assert joined_off.index("事件驱动") < joined_off.index("戏剧合同") < joined_off.index("最终提醒")


def test_judge_adds_gate_shape():
    from scribe3.playbook.judge import _normalize
    raw = _normalize({
        "verdict": "fail",
        "answers": [{"q": 1, "answer": "no", "evidence": "原句", "reason": "没发生"}],
        "opinion": "今晚那件事没落在纸上",
    })
    from scribe3.quality_gate import from_existing
    g = from_existing({
        "ok": raw["verdict"] == "pass",
        "code": raw["verdict"],
        "message": raw["opinion"],
        "hits": raw["answers"],
    })
    assert g["ok"] is False
    assert g["code"] == "fail"
    assert g["hits"]


def test_prompt_renderer_and_quality_shape():
    text = render_slots({"duty": "今晚按回碎片", "play": ""})
    assert "【duty】" in text
    assert "今晚按回碎片" in text
    assert "<prompt>" in text
    assert shadow_equal("a  b", "a b")
    g = gate_result(ok=False, code="leak", message="拆穿了", hits=[{"word": "锁眼"}])
    assert g["ok"] is False and g["code"] == "leak" and g["hits"]
    wrapped = from_existing({"ok": True, "issues": []})
    assert wrapped["ok"] is True
    assert "hits" in wrapped


def test_visible_to_strips_secret():
    from scribe3.epistemic import visible_to

    class F:
        def __init__(self, id, secret=False):
            self.id = id
            self.secret = secret

    class St:
        def facts_at(self, n):
            return [F("fact:a"), F("fact:secret", secret=True)]

    ids = visible_to(St(), "book", 1, "author")
    assert "fact:a" in ids
    assert "fact:secret" not in ids


def test_beats_write_legacy_flag_registered():
    from scribe3.feature_flags import FLAG_REGISTRY, flag_truthy, get_all_flags
    names = {f.name for f in FLAG_REGISTRY}
    for k in (
        "SCRIBE3_BEATS_WRITE_LEGACY",
        "SCRIBE3_HTTP_ERRORS_UNIFIED",
        "SCRIBE3_PROMPT_RENDERER",
        "SCRIBE3_QUALITY_GATE_UNIFIED",
        "SCRIBE3_EPISTEMIC_ORACLE",
        "SCRIBE3_RECALL_SHADOW_VECTOR",
        "SCRIBE3_RECALL_SHADOW_VECTOR_SYNC",
        "SCRIBE3_RECALL_PLAYBOOK",
        "SCRIBE3_RECALL_DISCUSS",
    ):
        assert k in names
    flags = get_all_flags()
    assert flags["SCRIBE3_RECALL_PLAYBOOK"]["default"] == "1"
    assert flags["SCRIBE3_RECALL_DISCUSS"]["default"] == "1"
    assert flags["SCRIBE3_PROMPT_RENDERER"]["default"] == "1"
    assert flags["SCRIBE3_QUALITY_GATE_UNIFIED"]["default"] == "1"
    assert flags["SCRIBE3_EPISTEMIC_ORACLE"]["default"] == "1"
    assert flags["SCRIBE3_HTTP_ERRORS_UNIFIED"]["default"] == "1"
    assert flag_truthy("SCRIBE3_RECALL_PLAYBOOK") is True


def test_dropped_chapter_fields_gated_in_source():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "store" / "chapters.py").read_text(encoding="utf-8")
    assert "SCRIBE3_BEATS_WRITE_LEGACY" in src
    assert "beats" in src


def test_record_shadow_stat_emits_observe():
    from scribe3.pipeline_recorder import FlightRecorder
    from scribe3.pipeline_trace import TraceBuffer, bind_trace_buffer, reset_trace_buffer

    buf = TraceBuffer()
    buf.recorder = FlightRecorder(work="t", chapter=1, kind="write", trace_id="ab" * 16, enabled=True)
    tok = bind_trace_buffer(buf)
    try:
        record_shadow_stat({
            "ok": True, "path": "playbook", "threshold_ok": True,
            "secret_leak_count": 0, "legacy_len": 12, "tag": "recall_shadow",
        })
        tags = [((e.get("payload") or {}).get("tag")) for e in buf.recorder.events]
        kinds = [e.get("kind") for e in buf.recorder.events]
        assert "recall_shadow" in tags
        assert "observe" in kinds
    finally:
        reset_trace_buffer(tok)


def test_debug_recall_shadow_has_window():
    from scribe3.api.routers.misc_routes import get_debug_recall_shadow
    out = get_debug_recall_shadow()
    assert "window" in out
    assert "持久化" in out["window"] or "进程" in out["window"]


def test_pipeline_events_tag_filter():
    from scribe3.api.routers.misc_routes import get_debug_pipeline_events

    class St:
        def __init__(self):
            self.kwargs = None

        def list_pipeline_events(self, **k):
            self.kwargs = k
            rows = [
                {"seq": 1, "kind": "observe", "payload": {"tag": "recall_shadow"}},
                {"seq": 2, "kind": "observe", "payload": {"tag": "other"}},
                {"seq": 3, "kind": "observe", "payload": {"tag": "recall_shadow"}},
            ]
            want = str(k.get("tag") or "").strip()
            if want:
                rows = [r for r in rows if (r.get("payload") or {}).get("tag") == want]
            return rows[: int(k.get("limit") or 200)]

    import scribe3.api.app_impl as core
    orig = getattr(core, "_store_for", None)
    st = St()
    core._store_for = lambda work: st
    try:
        plain = get_debug_pipeline_events(limit=10)
        assert plain["ok"] is True
        assert st.kwargs.get("tag") in (None, "")
        tagged = get_debug_pipeline_events(tag="recall_shadow", limit=10)
        assert tagged["count"] == 2
        assert all(i["payload"]["tag"] == "recall_shadow" for i in tagged["items"])
        assert tagged["truncated"] is False
        cut = get_debug_pipeline_events(tag="recall_shadow", limit=1)
        assert cut["count"] == 1
        assert cut["truncated"] is True
        assert cut["next_seq"] == cut["items"][-1]["seq"]
    finally:
        if orig is not None:
            core._store_for = orig


def test_recall_never_leaks_secret():
    from scribe3.ontology import Fact
    from scribe3.recall_service import pack_text, recall

    class St:
        def facts_at(self, n):
            return [
                Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1, secret=False),
                Fact("fact:坐标密", "role:柳岸青", "秘密", "看不见场核坐标", 1, secret=True),
            ]

    pack = recall(St(), chapter=1, focalizer="chief", query="柳岸青")
    text = pack_text(pack)
    assert "看不见场核坐标" not in text
    assert all(not h.secret for h in pack.hits)


def test_epistemic_allow_empty_keeps_hits(monkeypatch):
    from scribe3.ontology import Fact
    from scribe3.recall_service import recall

    class St:
        def facts_at(self, n):
            return [Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1)]

    notes = []
    monkeypatch.setattr(
        "scribe3.pipeline_trace_hooks.note_guide_missing",
        lambda n, **k: notes.append(n),
    )
    monkeypatch.setattr("scribe3.epistemic.visible_to", lambda *a, **k: [])
    _SHADOW_RING.clear()
    pack = recall(St(), chapter=1, focalizer="role:柳岸青", query="柳岸青 体温")
    assert pack.hits
    assert "看不见场核坐标" not in "".join(h.value for h in pack.hits)
    assert any(r.get("allow_empty") for r in _SHADOW_RING)
    assert "recall_epistemic_allow_empty" in notes


def test_epistemic_fail_closed_drops_layer(monkeypatch):
    from scribe3.ontology import Fact
    from scribe3.recall_service import recall

    class St:
        def facts_at(self, n):
            return [
                Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1),
                Fact("fact:坐标密", "role:柳岸青", "秘密", "看不见场核坐标", 1, secret=True),
            ]

    notes = []
    monkeypatch.setattr(
        "scribe3.pipeline_trace_hooks.note_guide_missing",
        lambda n, **k: notes.append(n),
    )

    def boom(*_a, **_k):
        raise RuntimeError("visible_to exploded")

    monkeypatch.setattr("scribe3.epistemic.visible_to", boom)
    pack = recall(St(), chapter=1, focalizer="role:柳岸青", query="柳岸青")
    assert any("四十二度" in h.value for h in pack.hits)
    assert all("看不见场核坐标" not in h.value for h in pack.hits)
    assert "recall_epistemic_fail_closed" in notes


def test_epistemic_no_silent_skip_in_source():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "recall_service.py").read_text(encoding="utf-8")
    assert "recall epistemic skip" not in src
    assert "recall_epistemic_fail_closed" in src
    assert "recall_epistemic_allow_empty" in src


def test_shadow_legacy_len_from_old_path():
    from scribe3.playbook.context import build_ctx
    from scribe3.tests.test_playbook_context_guides import _FrozenOnly, _World

    _SHADOW_RING.clear()
    ctx = build_ctx(_World(), 1, focalizer="role:柳岸青", playbook=_FrozenOnly())
    assert ctx["codex_recall"]
    rows = [r for r in _SHADOW_RING if r.get("path") == "playbook"]
    assert rows
    assert int(rows[0].get("legacy_len") or 0) > 0


def test_join_records_prompt_renderer_shadow(monkeypatch):
    from scribe3.context_budget import join_generation_segments
    from scribe3.feature_flags import flag_truthy as _orig

    def _on(name):
        if name == "SCRIBE3_PROMPT_RENDERER":
            return True
        return _orig(name)

    monkeypatch.setattr("scribe3.feature_flags.flag_truthy", _on)
    _SHADOW_RING.clear()
    join_generation_segments([
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】甲"},
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】丙"},
    ], v2=True)
    rows = [r for r in _SHADOW_RING if r.get("path") == "prompt_renderer"]
    assert rows
    assert "prompt_renderer_equal" in rows[0]


def test_codex_recall_empty_notes_when_facts_exist(monkeypatch):
    from scribe3.ontology import Fact
    from scribe3.playbook.context import playbook_codex_recall

    notes = []
    monkeypatch.setattr(
        "scribe3.pipeline_trace_hooks.note_guide_missing",
        lambda n, **k: notes.append(n),
    )

    class St:
        def facts_at(self, n):
            return [Fact("fact:x", "role:别人", "身份", "无关路人甲", 1)]

        def list_world_rules(self, category=None):
            return []

    playbook_codex_recall(
        St(), 1, "role:柳岸青",
        rows=[{"title": "华山成核", "synopsis": "按回碎片"}],
    )
    assert "codex_recall_empty" in notes


def test_review_runner_adds_gate_shape():
    from scribe3.review.runner import run_chapter_review

    class St:
        def get_chapter(self, seq):
            return {"prose": "墙比他想象中湿。", "focalizer": "role:柳岸青"}

        def facts_at(self, n):
            return []

    out = run_chapter_review(store=St(), work="t", seq=1, mode="deterministic")
    assert "gate" in out
    assert "ok" in out["gate"]
    assert "hits" in out["gate"]
    assert out["gate"]["code"] == "review"


def test_update_volume_sql_returns_before():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "store" / "chapters.py").read_text(encoding="utf-8")
    start = src.index("def update_volume")
    end = src.index("def ", start + 1)
    block = src[start:end]
    assert "RETURN BEFORE" in block
    assert "RETURN BEFORE intro" not in block
    assert "self._execute_write(" in block


def test_observe_emit_fail_leaves_note(monkeypatch):
    notes = []
    monkeypatch.setattr(
        "scribe3.pipeline_trace_hooks.note_guide_missing",
        lambda n, **k: notes.append(n),
    )

    class Boom:
        def emit(self, *a, **k):
            raise RuntimeError("emit down")

    _SHADOW_RING.clear()
    n0 = len(_SHADOW_RING)
    record_shadow_stat({
        "ok": True, "path": "playbook", "threshold_ok": True, "secret_leak_count": 0,
    }, recorder=Boom())
    assert "recall_shadow_observe_persist_fail" in notes
    assert len(_SHADOW_RING) >= n0 + 1
    assert any(r.get("persist_fail") for r in _SHADOW_RING)


def test_async_vector_shadow_uses_captured_recorder(monkeypatch):
    import time
    from scribe3.feature_flags import flag_truthy as _orig
    from scribe3.pipeline_recorder import FlightRecorder
    from scribe3.pipeline_trace import TraceBuffer, bind_trace_buffer, reset_trace_buffer

    def _ft(name):
        if name == "SCRIBE3_RECALL_SHADOW_VECTOR":
            return True
        if name == "SCRIBE3_RECALL_SHADOW_VECTOR_SYNC":
            return False
        return _orig(name)

    monkeypatch.setattr("scribe3.feature_flags.flag_truthy", _ft)

    class St:
        def facts_at(self, seq):
            return [{"entity_id": "role:柳岸青", "attribute": "身体", "value": "四十二度不是病是标价"}]

        def hybrid_recall(self, q, chapter, k=8):
            return [{"entity_id": "role:柳岸青", "attribute": "身体", "value": "四十二度不是病是标价"}]

    buf = TraceBuffer()
    buf.recorder = FlightRecorder(work="t", chapter=1, kind="write", trace_id="cd" * 16, enabled=True)
    tok = bind_trace_buffer(buf)
    try:
        rec = shadow_diff(
            St(), 1, "role:柳岸青", "柳岸青 / 身体：四十二度不是病是标价",
            query="柳岸青", path="playbook",
        )
        assert rec.get("ok") is True
        found = False
        for _ in range(80):
            paths = [((e.get("payload") or {}).get("path") or "") for e in buf.recorder.events]
            if any(str(p).endswith(":vector") for p in paths):
                found = True
                break
            time.sleep(0.02)
        assert found
    finally:
        reset_trace_buffer(tok)


def test_mcp_ingest_return_forwards_applied():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "mcp" / "tools_write.py").read_text(encoding="utf-8")
    start = src.index("def s3_ingest_chapter")
    end = src.index("\n@mcp.tool", start)
    block = src[start:end]
    assert '"applied": applied' in block or '"applied": ing.get("applied")' in block


def test_reveal_rejects_character_focalizer():
    from scribe3.ontology import Fact
    from scribe3.recall_service import recall

    class St:
        def facts_at(self, n):
            return [Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1)]

    try:
        recall(St(), chapter=1, focalizer="role:柳岸青", query="柳岸青", reveal=True)
        assert False, "should reject"
    except ValueError as exc:
        assert "reveal" in str(exc)


def test_reveal_empty_query_returns_empty():
    from scribe3.ontology import Fact
    from scribe3.recall_service import pack_text, recall

    class St:
        def facts_at(self, n):
            return [
                Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1),
                Fact("fact:密", "role:柳岸青", "秘密", "看不见场核坐标", 1, secret=True),
            ]

    pack = recall(St(), chapter=1, focalizer="", query="", reveal=True)
    assert pack.hits == []
    pack2 = recall(St(), chapter=1, focalizer="", query="柳岸青", reveal=True)
    text = pack_text(pack2)
    assert "四十二度" in text
    assert "〔秘〕" in text
    assert "看不见场核坐标" in text
    pack3 = recall(St(), chapter=1, focalizer="chief", query="柳岸青", reveal=False)
    assert "〔秘〕" not in pack_text(pack3)
    assert "看不见场核坐标" not in pack_text(pack3)


def test_pack_text_secret_prefix():
    from scribe3.recall_service import RecallHit, RecallPack, pack_text
    pub = RecallHit("role:柳岸青", "身体", "四十二度不是病是标价", "facts_at")
    sec = RecallHit("role:柳岸青", "秘密", "看不见场核坐标", "facts_at", secret=True)
    text = pack_text(RecallPack(hits=[pub, sec]))
    assert "柳岸青 / 身体：四十二度不是病是标价" in text
    assert "〔秘〕柳岸青 / 秘密：看不见场核坐标" in text
    assert text.splitlines()[1].startswith("柳岸青")


def test_shadow_diff_reveal_keeps_secret():
    from scribe3.ontology import Fact
    from scribe3.recall_service import shadow_diff

    class St:
        def facts_at(self, n):
            return [
                Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1),
                Fact("fact:密", "role:柳岸青", "秘密", "看不见场核坐标", 1, secret=True),
            ]

    hid = shadow_diff(St(), 1, "", "x", reveal=False)
    shown = shadow_diff(St(), 1, "", "x", reveal=True)
    assert shown.get("ok") is True
    assert int(shown.get("shadow_len") or 0) >= int(hid.get("shadow_len") or 0)


def test_chapter_codex_empty_line_filters():
    from scribe3.api.routers.write import chapter_codex_empty_line
    line = "本章没对上设定条目"
    ev_ok = {"chapter": 2, "payload": {"name": "codex_recall_empty", "source": "playbook"}, "trace_id": "aa"}
    assert chapter_codex_empty_line([ev_ok], 2, "aa") == line
    assert chapter_codex_empty_line([ev_ok], 1, "aa") == ""
    discuss = {"chapter": 2, "payload": {"name": "codex_recall_empty", "source": "discuss"}}
    assert chapter_codex_empty_line([discuss], 2, "") == ""
    discuss_tag = {
        "chapter": 2,
        "payload": {"name": "codex_recall_empty", "budget_tag": "discuss_codex"},
    }
    assert chapter_codex_empty_line([discuss_tag], 2, "") == ""
    plain = {"chapter": 2, "payload": {"name": "codex_recall_empty"}}
    assert chapter_codex_empty_line([plain], 2, "") == line
    other_run = {"chapter": 2, "payload": {"name": "codex_recall_empty", "source": "playbook"}, "trace_id": "bb"}
    assert chapter_codex_empty_line([other_run], 2, "aa") == ""
    zero = {"chapter": 0, "payload": {"name": "codex_recall_empty", "source": "playbook"}}
    assert chapter_codex_empty_line([zero], 2, "") == ""


def test_applied_minus_one_not_learned_copy():
    src = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "api" / "services" / "ingest_bg.py").read_text(encoding="utf-8")
    assert 'r.get("parse_failed") or r.get("applied") == -1' in src
    assert "学到了 {applied} 条设定" in src


def test_judge_vcode_prefers_gate():
    from scribe3.playbook.pipeline import _judge_vcode
    assert _judge_vcode({"ok": True, "code": "pass", "verdict": "fail"}) == "pass"
    assert _judge_vcode({"ok": False, "code": "needs_human", "verdict": "pass"}) == "needs_human"
    assert _judge_vcode({"verdict": "pass"}) == "pass"
    assert _judge_vcode({"verdict": "needs_human"}) == "needs_human"
    assert _judge_vcode({}) == "pass"
    assert _judge_vcode(None) == "pass"


def test_quality_eval_shape_adds_gate():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "quality" / "api.py").read_text(encoding="utf-8")
    start = src.index("def _shape_evaluation")
    end = src.index("\n@quality_eval_router", start)
    block = src[start:end]
    assert "from_existing" in block
    assert "quality_eval" in block
    assert "dimensions_deprecated" in block

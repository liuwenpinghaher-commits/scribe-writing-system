"""P2 scheme pillars — drive shipped helpers only (no Surreal/FastAPI required)."""
from __future__ import annotations

import os
from pathlib import Path


def test_chapter_lock_contention_and_release():
    from scribe3.chapter_lock import (
        InMemoryLockStore,
        acquire_chapter_lock,
        release_chapter_lock,
        chapter_target,
    )
    from scribe3.concurrency_lock import distributed_lock_enabled

    work, seq = "main", 42
    r1 = acquire_chapter_lock("loop", work, seq)
    assert r1.ok and r1.status == "acquired"
    assert r1.chapter_key == chapter_target(work, seq)
    r2 = acquire_chapter_lock("loop", work, seq)
    assert not r2.ok and r2.status == "busy"
    release_chapter_lock("loop", work, seq)
    r3 = acquire_chapter_lock("loop", work, seq)
    assert r3.ok
    release_chapter_lock("loop", work, seq)

    # ingest / repair kinds
    assert acquire_chapter_lock("ingest", work, 7).ok
    assert not acquire_chapter_lock("ingest", work, 7).ok
    release_chapter_lock("ingest", work, 7)

    # store-backed when distributed flag on
    os.environ["SCRIBE3_DISTRIBUTED_LOCK"] = "1"
    try:
        assert distributed_lock_enabled() is True
        store = InMemoryLockStore()
        a = acquire_chapter_lock("repair", "w", 1, store=store)
        b = acquire_chapter_lock("repair", "w", 1, store=store)
        assert a.ok and not b.ok and b.status == "busy"
        release_chapter_lock("repair", "w", 1, store=store)
        assert acquire_chapter_lock("repair", "w", 1, store=store).ok
        release_chapter_lock("repair", "w", 1, store=store)
    finally:
        os.environ.pop("SCRIBE3_DISTRIBUTED_LOCK", None)

    # flag-off process-local still refuses re-entry
    assert not distributed_lock_enabled()
    assert acquire_chapter_lock("loop", "x", 9).ok
    assert not acquire_chapter_lock("loop", "x", 9).ok
    release_chapter_lock("loop", "x", 9)


def test_soft_activation_drops_soft_keeps_redline():
    from scribe3.soft_activation import apply_soft_activation, soft_activation_enabled

    pieces = [
        {"name": "drama_contract", "text": "戏：必须留下"},
        {"name": "brief_must", "text": "压力必须"},
        {"name": "final_reminder", "text": "【最终提醒】限知"},
        {"name": "material_recall", "text": "无关素材拉拉杂杂"},
        {"name": "codex", "text": "设定百科全书很长"},
        {"name": "reference_craft", "text": "参考写法无关主题"},
        {"name": "material_recall", "text": "命中关键词龙渊的素材"},
    ]
    # flag off → all kept
    os.environ["SCRIBE3_SOFT_ACTIVATION"] = "0"
    kept0, rep0 = apply_soft_activation(pieces, activation_keys=["龙渊"], force=False)
    assert len(kept0) == len(pieces)
    assert rep0["mode"] == "passthrough"

    os.environ["SCRIBE3_SOFT_ACTIVATION"] = "1"
    try:
        assert soft_activation_enabled() is True
        kept, rep = apply_soft_activation(pieces, activation_keys=["龙渊"], force=True)
        names = [p["name"] for p in kept]
        assert "drama_contract" in names
        assert "brief_must" in names
        assert "final_reminder" in names
        # 未命中 soft 丢弃；命中保留
        assert names.count("material_recall") == 1
        assert any("龙渊" in (p.get("text") or "") for p in kept if p["name"] == "material_recall")
        assert "codex" not in names or "codex" in rep["dropped"]
        assert "reference_craft" in rep["dropped"]
        assert "drama_contract" in rep["kept_redline"]
        # 红线不得因激活键缺失被丢
        empty_keys, rep2 = apply_soft_activation(
            [{"name": "drama_contract", "text": "铁律"},
             {"name": "material_recall", "text": "无键时 soft 默认保留"}],
            activation_keys=[],
            force=True,
        )
        assert any(p["name"] == "drama_contract" for p in empty_keys)
    finally:
        os.environ.pop("SCRIBE3_SOFT_ACTIVATION", None)


def test_soft_precheck_and_literary_distill():
    from scribe3.soft_precheck import soft_precheck_plan
    from scribe3.literary_distill import literary_distill, DISTILL_FORBIDDEN_KPIS
    from pathlib import Path

    empty = soft_precheck_plan({"beats": []})
    assert empty["hard_park"] is False
    assert empty["finding_count"] >= 1
    assert any(f["code"] == "beats_empty" for f in empty["findings"])

    holes = soft_precheck_plan({
        "beats": [
            {"text": "抵达城门", "goal": "进城", "conflict": ""},
            {"goal": "", "conflict": "", "text": "短"},
        ],
    })
    assert holes["hard_park"] is False
    codes = {f["code"] for f in holes["findings"]}
    assert "empty_conflict" in codes or "beat_thin" in codes

    recap = (
        "主角与敌对峙，最终了结旧怨。\n\n"
        "她付出了左臂的代价，伤口未愈。\n\n"
        "态度改变：她决定不再逃避真相。"
    )
    d = literary_distill(recap)
    assert d["raw"] == recap
    assert len(d["bullets"]) >= 2
    kinds = {b["kind"] for b in d["bullets"]}
    assert kinds & {"paid_off", "open_cost", "attitude", "beat"}
    assert d["control"]["uses_tokens_saved"] is False
    assert d["audit"]["not_a_kpi"] == "tokens_saved"
    assert "tokens_saved" in DISTILL_FORBIDDEN_KPIS
    # 源码控制路径不出现 tokens_saved 作开关
    src = Path("scribe3/literary_distill.py").read_text(encoding="utf-8")
    assert "if" not in src or "tokens_saved" not in src.split("def literary_distill")[1].split("return")[0]
    # 更硬：控制 dict 写死 False
    assert "uses_tokens_saved" in src and "False" in src


def test_event_graph_adjacency_and_linked_pair():
    from scribe3.event_graph import build_event_adjacency, graph_one_hop, graph_linked_pair

    g = build_event_adjacency(
        events=[
            {"id": "e1"},
            {"id": "e2", "leads_to": "e3"},
            {"id": "e3"},
        ],
        promises=[{"id": "p1", "event_id": "e1"}],
    )
    assert g["edge_count"] >= 1
    assert "e1" in g["nodes"]
    hop = graph_one_hop(g, ["e1"])
    assert isinstance(hop, list)
    # e1 序列 leads_to e2；e2 leads_to e3
    hop2 = graph_one_hop(g, ["e2"])
    assert "e3" in hop2
    pair = graph_linked_pair(g, "e2", "e3")
    assert pair["linked"] is True
    assert pair["forward"] is True
    assert "leads_to" in pair["relations"] or pair["linked"]


def test_p2_flags_registered():
    from scribe3.feature_flags import get_all_flags, flag_truthy
    flags = get_all_flags()
    for name in (
        "SCRIBE3_SOFT_ACTIVATION",
        "SCRIBE3_SOFT_PRECHECK",
        "SCRIBE3_LITERARY_DISTILL",
        "SCRIBE3_DISTRIBUTED_LOCK",
    ):
        assert name in flags
    assert flag_truthy("SCRIBE3_SOFT_ACTIVATION") is True  # 产品 soft 默认开


def test_app_impl_wires_chapter_lock_source():
    """结构：_acquire_op_mutex 调用 shipped chapter_lock。"""
    src = Path("scribe3/api/app_impl.py").read_text(encoding="utf-8")
    assert "acquire_chapter_lock" in src
    assert "release_chapter_lock" in src
    wa = Path("scribe3/api/services/write_assemble.py").read_text(encoding="utf-8")
    assert "apply_soft_activation" in wa


if __name__ == "__main__":
    import traceback
    failed = []
    for name, fn in list(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print("PASS", name)
        except Exception as e:
            print("FAIL", name, e)
            traceback.print_exc()
            failed.append(name)
    print("SUMMARY failed=", failed)
    raise SystemExit(1 if failed else 0)

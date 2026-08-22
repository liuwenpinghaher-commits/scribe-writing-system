"""Storyline fusion SL1–SL5：驱动真实 shipped 函数（无 Surreal / 无全量 pytest 依赖）。"""
from __future__ import annotations

import os
import sys

# 允许从 repo 根直接 python -m pytest 或 python this file
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_craft_only_roundtrip_memory_store():
    from scribe3.storyline_store import (
        clear_for_tests,
        create_storyline,
        delete_storyline,
        get_storyline,
        list_storylines,
        update_storyline,
    )

    clear_for_tests()
    row = create_storyline(
        "ut_work",
        title="弧一",
        notes="应可注入",
        craft_only=True,
        chapter_seqs=[1, 2],
    )
    assert row["craft_only"] is True
    assert row["notes"] == "应可注入"
    sid = row["id"]

    row2 = update_storyline(
        "ut_work",
        sid,
        craft_only=False,
        notes="机密",
        arc_kind="secret",
    )
    assert row2 is not None
    assert row2["craft_only"] is False
    assert row2["notes"] == "机密"
    assert row2["arc_kind"] == "secret"

    # 缺字段读作 true
    from scribe3.storyline_store import _BY_WORK, _LOCK

    with _LOCK:
        _BY_WORK["ut_work"][sid].pop("craft_only", None)
    got = get_storyline("ut_work", sid)
    assert got is not None
    assert got["craft_only"] is True

    assert delete_storyline("ut_work", sid) is True
    assert list_storylines("ut_work") == []


def test_inject_omit_and_craft_only_filter():
    from scribe3.storyline_inject_polish import build_storyline_feed_context

    chapters = [
        {
            "seq": 1,
            "title": "一",
            "synopsis": "代价：命",
            "beats": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
        },
        {"seq": 2, "title": "二", "synopsis": "乙"},
        {"seq": 5, "title": "五", "synopsis": "远"},  # 窗口外
    ]
    storylines = [
        {
            "id": "sl_ok",
            "title": "主线",
            "arc_kind": "main",
            "chapter_seqs": [1, 2],
            "notes": "公开弧注",
            "craft_only": True,
        },
        {
            "id": "sl_secret",
            "title": "秘线",
            "arc_kind": "secret",
            "chapter_seqs": [1],
            "notes": "机密勿进",
            "craft_only": False,
        },
    ]
    feed = build_storyline_feed_context(
        focus_seq=1,
        chapters=chapters,
        storylines=storylines,
        open_promises=[{"text": "伏笔甲", "setup_chapter": 1}],
        promise_mode="omit",
        window=2,
    )
    text = feed["segment"]["text"]
    assert "开放伏笔：" not in text
    assert "公开弧注" in text
    assert "机密勿进" not in text
    assert feed["promise_mode"] == "omit"
    assert feed["fed"] is True
    assert 5 not in feed["window_seqs"]
    assert 1 in feed["window_seqs"]
    assert "sl_ok" in feed["craft_only_injected_ids"]
    assert "sl_secret" in feed["craft_only_skipped"]
    assert feed["segment"]["audit"]["has_open_promise_body"] is False


def test_segment_builder_default_omit_empty_promises():
    from scribe3.storyline_inject_polish import build_storyline_inject_segment

    seg = build_storyline_inject_segment(
        focus_seq=3,
        open_promise_texts=["不该出现"],
        promise_mode="omit",
    )
    assert "开放伏笔：" not in seg["text"]
    assert "焦点章：第3章" in seg["text"]
    assert seg["promise_mode"] == "omit"


def test_craft_ruler_uncomputed_not_fake_half():
    from scribe3.craft_ruler import craft_ruler_report

    rep = craft_ruler_report([{"emotion": -2}, {"emotion": 0}, {"emotion": 3}])
    dims = rep.get("core_dimensions") or []
    assert dims, "expected CORE_DIMENSIONS dims"
    ee = [d for d in dims if d.get("key") == "emotional_effect"]
    others = [d for d in dims if d.get("key") != "emotional_effect"]
    assert ee and ee[0].get("source") == "craft_ruler.dtw"
    assert isinstance(ee[0].get("score"), (int, float))
    for d in others:
        assert d.get("score") is None, d
        assert d.get("source") == "uncomputed", d


def test_registry_four_tuple_storyline_polish():
    from scribe3.context_budget import L2_DROP_TIER, generation_physical_order_names
    from scribe3.injection_registry import SEGMENT_REGISTRY

    names = {s.name for s in SEGMENT_REGISTRY}
    assert "storyline_polish" in names
    meta = next(s for s in SEGMENT_REGISTRY if s.name == "storyline_polish")
    assert meta.tier == "L3"
    order = generation_physical_order_names()
    assert "storyline_polish" in order
    assert order.index("storyline_polish") == order.index("reference_craft") + 1
    assert "storyline_polish" in L2_DROP_TIER["T3"]


def test_default_focus_and_overlay_and_causal_refs():
    from scribe3.storyline_project import (
        default_focus_seq,
        focus_causal_refs,
        project_arc_overlay,
    )

    chapters = [
        {"seq": 1, "title": "", "synopsis": ""},
        {"seq": 2, "title": "有题", "synopsis": ""},
        {"seq": 4, "synopsis": "有梗概"},
    ]
    assert default_focus_seq(chapters) == 4

    ov = project_arc_overlay(
        [{"id": "a", "title": "弧", "arc_kind": "main", "chapter_seqs": [2, 4]}],
        [{"seq": 2, "phase": "outline"}, {"seq": 4, "phase": "beats"}],
    )
    assert ov["rows"][0]["arcs"][0]["title"] == "弧"
    assert ov["rows"][1]["arc_titles"] == ["弧"]

    refs = focus_causal_refs(
        focus_seq=2,
        causal_payload={"no_event_data": False, "violations": []},
        open_promise_count=1,
    )
    assert refs["causal"]["state"] == "complete"
    refs2 = focus_causal_refs(
        focus_seq=2,
        causal_payload={"no_event_data": True, "violations": []},
    )
    assert refs2["causal"]["state"] == "no-data"


def test_fail_soft_storyline_meta_shape_and_promise_hint_flag():
    """flag PROMISE_HINT default off; segment audit fields present."""
    from scribe3.feature_flags import get_flag
    from scribe3.storyline_inject_polish import (
        build_storyline_inject_segment,
        promise_hint_enabled,
    )

    assert get_flag("SCRIBE3_STORYLINE_PROMISE_HINT") in ("0", "false", "off", "")
    assert promise_hint_enabled() is False
    seg = build_storyline_inject_segment(
        focus_seq=1,
        promise_mode="hint_only",
        open_promise_count=3,
    )
    # 旗关：不输出计数行
    assert "未收线伏笔" not in seg["text"]


def test_assemble_writes_storyline_inject_key_fail_soft(monkeypatch=None):
    """轻量：budget_report 可承载 fail-soft storyline_inject 形状。"""
    from scribe3.api.services import write_assemble as wa

    rep = {
        "storyline_inject": {
            "fed": False,
            "promise_mode": "omit",
            "applied": False,
            "enabled": True,
            "error": "boom",
        }
    }
    wa._store_write_budget_report(rep)
    got = wa.get_last_write_budget_report()
    assert "storyline_inject" in got
    assert got["storyline_inject"]["promise_mode"] == "omit"
    assert got["storyline_inject"].get("fed") is False


def test_prepare_write_storyline_inject_fail_soft_never_raises():
    """热路径助手：feed 抛错时仍返回 meta（fed=false + error），不抛。"""
    from scribe3 import storyline_inject_polish as sip

    class Boom:
        def chapters_lite(self):
            raise RuntimeError("chapters_lite boom")

    # store 本身炸仍 fail-soft
    out = sip.prepare_write_storyline_inject(Boom(), chapter=1, work="ut")
    assert "meta" in out and "text" in out
    assert out["meta"].get("promise_mode") == "omit"
    # chapters 炸 → 空章仍可 fed（feed 成功）或 error；关键：不抛
    assert isinstance(out["meta"], dict)

    # 强制 feed 抛错
    real = sip.build_storyline_feed_context

    def _boom(**kw):
        raise RuntimeError("feed explode")

    sip.build_storyline_feed_context = _boom  # type: ignore
    try:
        out2 = sip.prepare_write_storyline_inject(
            type("St", (), {"chapters_lite": lambda self: [{"seq": 1, "synopsis": "a"}]})(),
            chapter=1,
            work="ut",
        )
        assert out2["meta"]["fed"] is False
        assert out2["meta"].get("error")
        assert "explode" in str(out2["meta"]["error"])
        assert out2["text"] == ""
        assert out2["meta"]["promise_mode"] == "omit"
    finally:
        sip.build_storyline_feed_context = real  # type: ignore


def test_prepare_write_happy_path_omit_and_craft_only():
    from scribe3.storyline_inject_polish import prepare_write_storyline_inject

    class St:
        def chapters_lite(self):
            return [{"seq": 1, "title": "一", "synopsis": "代价：命", "beats": [{"text": "a"}]}]

        def list_storylines(self):
            return [
                {
                    "id": "ok",
                    "title": "主",
                    "chapter_seqs": [1],
                    "notes": "公开注",
                    "craft_only": True,
                },
                {
                    "id": "sec",
                    "title": "秘",
                    "chapter_seqs": [1],
                    "notes": "机密",
                    "craft_only": False,
                },
            ]

        def open_promises(self):
            return [{"text": "伏笔甲", "setup_chapter": 1}]

    out = prepare_write_storyline_inject(St(), chapter=1, work="ut")
    assert out["meta"]["fed"] is True
    assert out["meta"]["promise_mode"] == "omit"
    assert out["meta"]["applied"] is True
    assert "开放伏笔：" not in out["text"]
    assert "公开注" in out["text"]
    assert "机密" not in out["text"]


def test_storyline_crud_endpoints_memory_path():
    """驱动真实 product_backlog 端点（memory 降级），含 craft_only 与 DELETE。"""
    from scribe3.api.routers import product_backlog as pb
    from scribe3.storyline_store import clear_for_tests, get_storyline
    import scribe3.api.app_impl as core

    clear_for_tests()
    old = getattr(core, "_store_for", None)

    def _raise_store(work="main"):
        raise RuntimeError("no surreal in unit")

    core._store_for = _raise_store  # type: ignore
    try:
        created = pb.storyline_create_ep(
            {
                "title": "端点弧",
                "notes": "n1",
                "craft_only": False,
                "chapter_seqs": [1],
                "work": "ep_ut",
            },
            work="ep_ut",
        )
        assert created.get("id")
        assert created.get("craft_only") is False
        sid = created["id"]
        patched = pb.storyline_patch_ep(
            sid,
            {"craft_only": True, "notes": "应注入", "arc_kind": "side", "work": "ep_ut"},
            work="ep_ut",
        )
        assert patched["craft_only"] is True
        assert patched["notes"] == "应注入"
        assert patched["arc_kind"] == "side"
        # inject preview use_store：无 store 时仍 omit
        prev = pb.storyline_inject_preview_ep(
            {"focus_seq": 1, "use_store": 0, "promise_mode": "omit", "open_promises": ["x"]},
            work="ep_ut",
        )
        assert "开放伏笔：" not in (prev.get("text") or "")
        deleted = pb.storyline_delete_ep(sid, work="ep_ut")
        assert deleted.get("ok") is True
        assert get_storyline("ep_ut", sid) is None
    finally:
        if old is not None:
            core._store_for = old


def test_storyline_hub_has_overlay_and_focus_refs():
    from scribe3.api.routers import product_backlog as pb
    from scribe3.storyline_store import clear_for_tests, create_storyline
    import scribe3.api.app_impl as core

    clear_for_tests()
    create_storyline("hub2", title="T", chapter_seqs=[1], notes="x", craft_only=True)

    class St:
        def chapters_lite(self):
            return [
                {"seq": 1, "title": "一", "synopsis": "代价：生死"},
                {"seq": 2, "title": "二", "beats": [{"conflict": "x"}]},
            ]

        def open_promises(self):
            return [{"setup_chapter": 1, "text": "坑"}]

        def list_storylines(self):
            return [
                {
                    "id": "s1",
                    "title": "T",
                    "chapter_seqs": [1],
                    "arc_kind": "main",
                    "craft_only": True,
                }
            ]

        def events_at(self, ch):
            return []

    old = getattr(core, "_store_for", None)
    core._store_for = lambda work="main": St()  # type: ignore
    try:
        pack = pb.storyline_hub_ep(work="hub2")
        assert pack.get("overlay")
        assert pack.get("focus_seq") in (1, 2)
        assert "causal" in (pack.get("refs") or {})
        assert (pack["refs"]["causal"] or {}).get("state") in (
            "no-data",
            "complete",
            "violations",
        )
        rows = (pack.get("overlay") or {}).get("rows") or []
        assert any((r.get("arcs") or r.get("arc_titles")) for r in rows) or pack.get(
            "storylines"
        )
    finally:
        if old is not None:
            core._store_for = old


def test_app_impl_write_path_rebind_ready():
    """rebind 后写路径必需全局齐全（防 package-C NameError 回归）。"""
    import scribe3.api.app_impl as app_impl
    from scribe3.api.services.write_assemble import (
        WRITE_ASSEMBLE_REBIND_NAMES,
        assert_write_assemble_rebind_ready,
    )

    if hasattr(app_impl, "_rebind_services"):
        app_impl._rebind_services()
    # 本包白名单必须全在 app_impl
    missing_local = [
        n for n in WRITE_ASSEMBLE_REBIND_NAMES if n not in app_impl.__dict__
    ]
    assert not missing_local, f"rebind missing: {missing_local}"
    # v1 函数 globals 必须能解析关键符号
    assem = app_impl._assemble_write_instructions_v1
    for name in (
        "generation_forbidden_source_kinds",
        "_record_write_soft_fail",
        "_store_write_budget_report",
        "_pressure_drive_write_block",
    ):
        assert name in assem.__globals__, name
    # 跨模块 external 至少应有 final_reminder
    assert "_final_reminder" in assem.__globals__ or "_final_reminder" in app_impl.__dict__
    # 自检 API
    if hasattr(app_impl, "assert_write_path_rebind_ready"):
        miss = app_impl.assert_write_path_rebind_ready()
        # external 可能因命名空间检查用 globals() 含 external: 前缀
        hard = [m for m in miss if not str(m).startswith("external:")]
        assert not hard, hard


def test_phase_of_uses_progress_not_just_synopsis():
    from scribe3.storyline_project import _phase_of
    assert _phase_of({"synopsis": "有大纲", "beats": [{"text": "拍"}]}) == "beats"
    assert _phase_of({"synopsis": "有大纲", "scene_truth": "真相一段"}) == "deduce"
    assert _phase_of({"synopsis": "有大纲", "has_prose": True}) == "final"
    assert _phase_of({"synopsis": "只有大纲"}) == "outline"


if __name__ == "__main__":
    # 无 pytest 时直接跑
    test_craft_only_roundtrip_memory_store()
    test_inject_omit_and_craft_only_filter()
    test_segment_builder_default_omit_empty_promises()
    test_craft_ruler_uncomputed_not_fake_half()
    test_registry_four_tuple_storyline_polish()
    test_default_focus_and_overlay_and_causal_refs()
    test_fail_soft_storyline_meta_shape_and_promise_hint_flag()
    test_assemble_writes_storyline_inject_key_fail_soft()
    test_prepare_write_storyline_inject_fail_soft_never_raises()
    test_prepare_write_happy_path_omit_and_craft_only()
    test_storyline_crud_endpoints_memory_path()
    test_storyline_hub_has_overlay_and_focus_refs()
    test_app_impl_write_path_rebind_ready()
    print("ALL_STORYLINE_FUSION_OK")

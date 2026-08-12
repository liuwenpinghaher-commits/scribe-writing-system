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
    """轻量：mock 组装路径上的 feed 异常仍应写入 storyline_inject 键——测预算报告写入形状。"""
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
    print("ALL_STORYLINE_FUSION_OK")

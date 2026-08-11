"""延期产品 backlog pure 单测（宿主轻 · 无 Surreal/FastAPI）。"""
from __future__ import annotations

import os
from pathlib import Path


def test_wave0_flags_registered():
    from scribe3.feature_flags import get_all_flags, flag_truthy
    flags = get_all_flags()
    for name in (
        "SCRIBE3_STORYLINE_UI",
        "SCRIBE3_MULTI_HOP_GRAPH",
        "SCRIBE3_STAGE_MACHINE",
        "SCRIBE3_PARALLEL_DEDUCE",
        "SCRIBE3_AGENT_CRON_UI",
        "SCRIBE3_BENCHMARK_LIB",
        "SCRIBE3_STORYLINE_INJECT",
        "SCRIBE3_SOFT_ACTIVATION",
        "SCRIBE3_SOFT_PRECHECK",
        "SCRIBE3_LITERARY_DISTILL",
    ):
        assert name in flags
        # 产品 soft 默认开；硬门仍关
        assert flag_truthy(name) is True, name
    assert flag_truthy("SCRIBE3_STAGE_MACHINE_HARD") is False


def test_multi_hop_graph():
    from scribe3.event_graph import build_event_adjacency, graph_k_hop
    from scribe3.novel_first_surface import event_graph_surface

    g = build_event_adjacency(events=[
        {"id": "a"},
        {"id": "b", "causal_in": [("a", "enables")]},
        {"id": "c", "causal_in": [("b", "enables")]},
    ])
    h = graph_k_hop(g, ["a"], k=2, max_nodes=32)
    assert "c" in h["nodes"]
    assert h["k"] == 2
    assert any(e["dst"] == "b" for e in h["edges"])

    os.environ["SCRIBE3_MULTI_HOP_GRAPH"] = "1"
    try:
        surf = event_graph_surface(
            events=[{"id": "a"}, {"id": "b", "leads_to": "c"}, {"id": "c"}],
            seed_id="a",
            k=2,
        )
        assert surf["k"] == 2
        assert surf["multi_hop"] is not None
        assert "c" in surf["multi_hop"]["nodes"] or len(surf["multi_hop"]["nodes"]) >= 2
    finally:
        os.environ.pop("SCRIBE3_MULTI_HOP_GRAPH", None)


def test_chapter_stage_soft():
    from scribe3.chapter_stage import transition, next_phase, stage_from_chapter_dict
    assert next_phase("outline") == "beats"
    r = transition("outline", "to_final")
    assert r["hard_park"] is False
    assert "skipped_phase" in r["advisories"] or r["next"] == "final"
    # soft：仍给 next
    assert r["next"] in ("final", "outline", "beats", "deduce", "draft")
    os.environ["SCRIBE3_STAGE_MACHINE_HARD"] = "1"
    try:
        r2 = transition("outline", "to_final", hard=True)
        assert r2["blocked"] is True or r2["ok"] is False
    finally:
        os.environ.pop("SCRIBE3_STAGE_MACHINE_HARD", None)
    assert stage_from_chapter_dict({"prose": "很长" * 20}) == "draft"


def test_gantt_and_emotion():
    from scribe3.storyline_project import project_gantt_rows, project_emotion_curve
    chapters = [
        {"seq": 1, "title": "开", "synopsis": "stakes: 生死", "plan": {"beats": [{"conflict": "战"}]}},
        {"seq": 2, "title": "中", "prose": "x" * 600},
    ]
    g = project_gantt_rows(chapters)
    assert g["count"] == 2
    assert g["rows"][0]["stakes_hint"] == "present"
    assert g["not_a_score"] == "literary_quality"
    e = project_emotion_curve(chapters)
    assert e["count"] == 2
    assert 0 <= e["points"][0]["tension"] <= 1
    assert "非文学" in e["disclaimer"] or "启发式" in e["disclaimer"]


def test_benchmark_and_inject():
    from scribe3.benchmark_lib import (
        upsert_benchmark, list_benchmarks, delete_benchmark, clear_benchmarks_for_tests,
    )
    from scribe3.storyline_inject_polish import build_storyline_inject_segment
    clear_benchmarks_for_tests()
    row = upsert_benchmark({"title": "样例", "notes": "n", "tags": ["t"]})
    assert row["id"]
    assert any(x["title"] == "样例" for x in list_benchmarks())
    assert delete_benchmark(row["id"]) is True
    seg = build_storyline_inject_segment(
        focus_seq=1,
        gantt_rows=[{"seq": 1, "phase": "draft"}],
        open_promise_texts=["刀未还"],
        emotion_point={"label": "高", "tension": 0.8},
    )
    assert "故事线" in seg["text"] or seg["text"]
    assert seg["control"]["uses_tokens_saved"] is False
    assert seg["audit"]["redline_safe"] is True


def test_parallel_deduce_and_crons():
    from scribe3.parallel_deduce import build_parallel_deduce_plan
    from scribe3.agent_crons import (
        parse_crons_yaml, load_cron_catalog, set_cron_enabled, clear_cron_overrides_for_tests,
    )
    plan = build_parallel_deduce_plan(3, ["甲", "乙", "丙"], max_parallel=2)
    assert len(plan["runs"]) == 2
    assert plan["runs"][0]["profile"] == "scribe3_deduce_preview"
    assert plan["runs"][0]["api_env"] == "HERMES_DEDUCE_PREVIEW_RUNS_API"
    assert plan["dry_run"] is True
    assert plan["execute"] is False

    jobs = parse_crons_yaml(
        'jobs:\n  - name: scribe3-daily-digest\n    schedule: "0 8 * * *"\n    no_agent: true\n'
    )
    assert jobs and jobs[0]["name"] == "scribe3-daily-digest"
    clear_cron_overrides_for_tests()
    # 仓库 yaml 若存在
    cat = load_cron_catalog()
    assert isinstance(cat, list)
    r = set_cron_enabled("scribe3-daily-digest", False)
    assert r["enabled"] is False


def test_routes_and_ui_artifacts():
    src = Path("scribe3/api/routers/product_backlog.py").read_text(encoding="utf-8")
    for p in (
        "/storyline/gantt",
        "/storyline/emotion-curve",
        "/chapters/{seq}/stage",
        "/chapters/{seq}/deduce/parallel",
        "/agent-crons",
        "/benchmarks",
        "/storyline/inject-preview",
    ):
        assert p in src
    app = Path("scribe3/app.py").read_text(encoding="utf-8")
    assert "product_backlog_router" in app
    for f in (
        "scribe3/web/src/views/StorylineHub.jsx",
        "scribe3/web/src/views/EventGraphPanel.jsx",
        "scribe3/web/src/views/BenchmarkLibrary.jsx",
        "docs/guides/2026-08-11-deferred-product-backlog.md",
    ):
        assert Path(f).is_file(), f
    # 导航接线：DetailPane + AppRail + Overview
    dp = Path("scribe3/web/src/DetailPane.jsx").read_text(encoding="utf-8")
    assert "storyline" in dp and "benchmarks" in dp and "event-graph" in dp
    rail = Path("scribe3/web/src/AppRail.jsx").read_text(encoding="utf-8")
    assert "storyline" in rail
    ov = Path("scribe3/web/src/views/OverviewView.jsx").read_text(encoding="utf-8")
    assert "overview-open-storyline" in ov


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

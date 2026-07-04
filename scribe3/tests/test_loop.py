"""北极星方案任务4 · 修复环编排层 TDD(纯逻辑,全 stub,零 store/LLM)。

蓝图 §3-①:blocking→自动 regenerate≤2轮/advisory→待批清单(绝不自动重写)/
pass→ingest;判据全外部信号;降级不 pass(没查≠没病);journal 每步留痕;
旧稿每轮留版本;2 轮仍 blocking→needs_human,正文不落库不 ingest。
"""
import pytest

from scribe3.loop import (MAX_REGEN_ROUNDS, build_regen_constraints,
                          run_chapter_loop, triage)
from scribe3.pipeline_journal import PipelineJournal


def _post(leaks=None, issues=None, grade=None, degraded_stages=None,
          leaks_degraded=False, punct=None):
    p = {"leaks": leaks or [], "issues": issues or [],
         "degraded_stages": degraded_stages or [],
         "leaks_degraded": leaks_degraded, "punct_suggestions": punct or []}
    if grade:
        p["ai_grade"] = {"grade": grade, "gates_hit": ["A", "C"]}
    return p


# ===== triage:四条 blocking 判据 =====

def test_triage_leak_is_blocking():
    t = triage(_post(leaks=[{"marker": "治眼", "fact_id": "fact:治眼"}]))
    assert t["verdict"] == "blocking"
    assert t["blocking"][0]["detector"] == "find_leaks"
    assert "治眼" in t["blocking"][0]["quote"]


def test_triage_degeneration_blocking_vs_advisory():
    hard = {"type": "degeneration", "message": "逐句复读", "text": "他走了。他走了。",
            "meta": {"severity": "blocking", "kind": "sentence_loop"}}
    soft = {"type": "degeneration", "message": "疑似截断", "text": "",
            "meta": {"severity": "advisory", "kind": "truncated"}}
    assert triage(_post(issues=[hard]))["verdict"] == "blocking"
    assert triage(_post(issues=[soft]))["verdict"] == "advisory"


def test_triage_ai_grade_heavy_blocking_medium_not():
    assert triage(_post(grade="heavy"))["verdict"] == "blocking"
    assert triage(_post(grade="medium"))["verdict"] == "pass"


def test_triage_s1_blocking_s2_advisory():
    s1 = {"type": "discipline", "message": "双高潮", "text": "",
          "meta": {"severity": "S1"}}
    s2 = {"type": "discipline", "message": "轻微", "text": "",
          "meta": {"severity": "S2"}}
    assert triage(_post(issues=[s1]))["verdict"] == "blocking"
    assert triage(_post(issues=[s2]))["verdict"] == "advisory"


def test_triage_degraded_never_pass():
    """假绿防护:泄密检测降级/关键 stage 降级 → 干净响应也只能 advisory。"""
    assert triage(_post(leaks_degraded=True))["verdict"] == "advisory"
    assert triage(_post(degraded_stages=["aggregate_ai_grade"]))["verdict"] == "advisory"


def test_triage_clean_pass():
    t = triage(_post())
    assert t["verdict"] == "pass" and t["blocking"] == []


# ===== build_regen_constraints:三元组模板 =====

def test_constraints_triplet_and_round_diff():
    b = [{"detector": "find_leaks", "kind": "leak", "quote": "治眼",
          "note": "帧外私密破绽词(fact=fact:治眼)"}]
    c1 = build_regen_constraints(b, next_attempt=1)
    assert "[find_leaks]" in c1 and "治眼" in c1 and "疑惧" in c1, "三元组:检测器+引文+祈使约束"
    c2 = build_regen_constraints(b, next_attempt=2, prior_summary="第 1 稿硬伤:find_leaks×1")
    assert c1 != c2 and "第 1 稿硬伤" in c2, "第 2 轮必须与第 1 轮 prompt 不同"
    assert build_regen_constraints([], 1) == ""


def test_constraints_capped_at_12():
    b = [{"detector": "find_degeneration", "kind": "x", "quote": f"q{i}", "note": "n"}
         for i in range(20)]
    c = build_regen_constraints(b, 1)
    assert "另有 8 条" in c


# ===== run_chapter_loop:三路径 + 上限 + 留痕 =====

def _wire(tmp_path, posts, gen_log=None, fin_log=None):
    gen_log = gen_log if gen_log is not None else []
    fin_log = fin_log if fin_log is not None else []

    def gen(attempt, constraints):
        gen_log.append(constraints)
        return f"第{attempt}稿散文"

    def pc(prose):
        return posts.pop(0)

    def pv(prose, attempt, verdict):
        return f"v{attempt}"

    def fin(prose):
        fin_log.append(prose)
        return {"ingested": True}

    j = PipelineJournal(tmp_path / "loop.json")
    return dict(generate=gen, post_check=pc, persist_version=pv, finalize=fin, journal=j), j, gen_log, fin_log


def test_loop_clean_pass_direct_ingest(tmp_path):
    deps, j, gen_log, fin_log = _wire(tmp_path, [_post()])
    res = run_chapter_loop(chapter=3, **deps)
    assert res["verdict"] == "pass"
    assert len(gen_log) == 1 and len(fin_log) == 1
    assert res["ingest"] == {"ingested": True}
    assert j.should_skip("ch3_a0_generate") and j.should_skip("ch3_a0_post_check")
    assert j.should_skip("ch3_ingest")
    assert res["rounds"][0]["version_id"] == "v0"


def test_loop_blocking_regen_then_pass(tmp_path):
    posts = [_post(leaks=[{"marker": "治眼", "fact_id": "fact:治眼"}]), _post()]
    deps, j, gen_log, fin_log = _wire(tmp_path, posts)
    res = run_chapter_loop(chapter=4, **deps)
    assert res["verdict"] == "pass"
    assert len(gen_log) == 2
    assert gen_log[0] == "" and "治眼" in gen_log[1] and "[find_leaks]" in gen_log[1], \
        "回炉轮必须携带 findings 负面约束"
    assert len(res["rounds"]) == 2
    assert res["rounds"][0]["verdict"] == "blocking" and res["rounds"][1]["verdict"] == "pass"


def test_loop_two_rounds_still_blocking_needs_human(tmp_path):
    leak = _post(leaks=[{"marker": "治眼", "fact_id": "fact:治眼"}])
    posts = [leak, dict(leak), dict(leak)]
    deps, j, gen_log, fin_log = _wire(tmp_path, posts)
    res = run_chapter_loop(chapter=5, **deps)
    assert res["verdict"] == "needs_human"
    assert len(gen_log) == 1 + MAX_REGEN_ROUNDS, "初写1次+回炉硬上限2次,绝不多跑"
    assert fin_log == [], "needs_human 绝不 ingest(防污染本体)"
    assert j.should_skip("ch5_needs_human"), "needs_human 标记落 journal 供审计"
    assert gen_log[1] != gen_log[2], "两轮回炉 prompt 必须不同(防同参复跑)"


def test_loop_advisory_no_rewrite_no_ingest(tmp_path):
    soft = {"type": "discipline", "message": "轻微", "text": "", "meta": {"severity": "S3"}}
    deps, j, gen_log, fin_log = _wire(tmp_path, [_post(issues=[soft])])
    res = run_chapter_loop(chapter=6, **deps)
    assert res["verdict"] == "advisory"
    assert len(gen_log) == 1, "advisory 绝不自动重写(宪法条款)"
    assert fin_log == [], "advisory 不自动 ingest,人批后走既有链路"
    assert res["advisory_count"] >= 1
    assert res["advisory_items"] and res["advisory_items"][0]["message"], \
        "清单本体必须在响应里(蓝图:建议清单呈给作者,不能只给数量)"


def test_loop_persist_failure_does_not_break(tmp_path):
    deps, j, gen_log, fin_log = _wire(tmp_path, [_post()])

    def boom(prose, attempt, verdict):
        raise RuntimeError("version store down")

    deps["persist_version"] = boom
    res = run_chapter_loop(chapter=7, **deps)
    assert res["verdict"] == "pass", "留版失败降级不阻断编排(fail-soft)"
    assert res["rounds"][0]["version_id"] is None

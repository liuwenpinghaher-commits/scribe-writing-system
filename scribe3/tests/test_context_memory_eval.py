"""上下文与记忆黄金评测集(Task 1)的评测器测试。

为什么用 FakeRetriever 而不是真检索:本任务锁的是"指标器能不能数出问题"
——坏 retriever 必须被数出泄漏/断溯源/旧版本,好 retriever 必须全绿。
真实 retriever 由后续 Task 8 通过 RETRIEVERS 注册点接入,复用同一套 run_eval。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scribe3.tools.context_memory_eval import (
    CATEGORIES,
    FakeRetriever,
    gate_failures,
    load_gold_cases,
    run_eval,
)

# 黄金集说明:每例的 expected_source_kinds 仅供 Task 8 检索层做召回参考,
# 本期不参与打分与门禁(防止 Task 17 验收时误以为已设防)。
GOLD_PATH = Path(__file__).parent / "fixtures" / "context_memory_gold.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------- 黄金集本身的形状校验 ----------

def test_gold_cases_shape():
    cases = load_gold_cases(GOLD_PATH)
    # 首期锁 12 类 × 3 例 = 36 例,阈值与未来 120 例版相同
    assert len(cases) == 36
    per_cat = {}
    for c in cases:
        per_cat[c["category"]] = per_cat.get(c["category"], 0) + 1
    assert set(per_cat) == set(CATEGORIES)
    assert all(n == 3 for n in per_cat.values())
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))


def test_load_gold_cases_rejects_bad_category(tmp_path):
    bad = [dict(load_gold_cases(GOLD_PATH)[0], category="not_a_category")]
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        load_gold_cases(p)


def test_load_gold_cases_rejects_uneven_categories(tmp_path):
    # 少一例:某类只剩 2 例,必须报错——防止有人悄悄删用例放水
    cases = load_gold_cases(GOLD_PATH)[1:]
    p = tmp_path / "uneven.json"
    p.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        load_gold_cases(p)


def test_load_gold_cases_rejects_missing_field(tmp_path):
    cases = load_gold_cases(GOLD_PATH)
    del cases[0]["must_include"]
    p = tmp_path / "missing.json"
    p.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        load_gold_cases(p)


# ---------- 指标器正反两面 ----------

def test_eval_rejects_cross_work_and_missing_provenance():
    cases = load_gold_cases(GOLD_PATH)
    # 反面:故意跨 work 泄漏(且泄漏 hit 无溯源)的坏 retriever,指标器必须数得出来
    bad = run_eval(cases, FakeRetriever.with_cross_work_leak())
    assert bad["cross_work_leaks"] > 0
    assert bad["provenance_coverage"] < 1.0
    # 正面:干净 retriever 全绿
    good = run_eval(cases, FakeRetriever.clean())
    assert good["cross_work_leaks"] == 0
    assert good["provenance_coverage"] == 1.0


def test_eval_counts_excluded_leaks():
    """must_exclude 设防的核心测试:混入被排除条目(同 work/有溯源/revision 达标,
    伪装成"体面"答案)必须被 exclusion_violations 数出来——canonical_priority/
    temporal_validity/correction_supersession/uncertainty 四类考点全靠这道防线。"""
    cases = load_gold_cases(GOLD_PATH)
    bad = run_eval(cases, FakeRetriever.with_excluded_leak())
    # 36 例每例混入 must_exclude[0] 一条 → 恰好 36 次违规
    assert bad["exclusion_violations"] == 36
    good = run_eval(cases, FakeRetriever.clean())
    assert good["exclusion_violations"] == 0


def test_clean_retriever_hits_all_targets():
    cases = load_gold_cases(GOLD_PATH)
    result = run_eval(cases, FakeRetriever.clean())
    assert result["recall_at_10"] == 1.0
    assert result["ndcg_at_10"] == 1.0
    assert result["exclusion_violations"] == 0
    assert result["stale_revision_accepts"] == 0
    assert result["p95_ms"] < 250


def test_stale_revision_is_counted():
    cases = load_gold_cases(GOLD_PATH)
    result = run_eval(cases, FakeRetriever.with_stale_revision())
    # 黄金集里带 expected_revision 的恰好 7 例(focus_switch_001 +
    # correction_supersession×3 + stale_revision×3),各 1 条 must_include
    # → 精确 7 次过期接受;黄金集变动时此数需同步更新(防指标器漏数)
    assert result["stale_revision_accepts"] == 7


def test_partial_recall_degrades_metrics():
    cases = load_gold_cases(GOLD_PATH)
    result = run_eval(cases, FakeRetriever.with_partial_recall())
    assert result["recall_at_10"] < 1.0
    assert result["ndcg_at_10"] < 1.0


# ---------- 验收门槛 ----------

def test_gate_failures_clean_vs_leaky():
    cases = load_gold_cases(GOLD_PATH)
    assert gate_failures(run_eval(cases, FakeRetriever.clean())) == []
    failures = gate_failures(run_eval(cases, FakeRetriever.with_cross_work_leak()))
    assert any("cross_work_leaks" in f for f in failures)
    # 混入被排除条目也必须被门禁拦下(Critical-1 的门槛面)
    failures = gate_failures(run_eval(cases, FakeRetriever.with_excluded_leak()))
    assert any("exclusion_violations" in f for f in failures)


def test_cli_clean_retriever_exits_zero(tmp_path):
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, "-m", "scribe3.tools.context_memory_eval",
         "--gold", str(GOLD_PATH), "--output", str(out), "--retriever", "fake:clean"],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["cross_work_leaks"] == 0
    assert report["provenance_coverage"] == 1.0


def test_cli_leaky_retriever_exits_one(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "scribe3.tools.context_memory_eval",
         "--gold", str(GOLD_PATH), "--output", str(tmp_path / "r.json"),
         "--retriever", "fake:cross_work_leak"],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_cli_excluded_leak_exits_one(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "scribe3.tools.context_memory_eval",
         "--gold", str(GOLD_PATH), "--output", str(tmp_path / "r.json"),
         "--retriever", "fake:excluded_leak"],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "exclusion_violations" in proc.stdout


def test_cli_bad_gold_path_exits_one_without_traceback(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "scribe3.tools.context_memory_eval",
         "--gold", str(tmp_path / "不存在.json")],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 1
    assert "黄金集加载失败" in proc.stdout
    assert "Traceback" not in proc.stderr

#!/usr/bin/env python3
"""上下文与记忆黄金评测集的指标器与验收门禁(Task 1)。

设计约束(后续 Task 8/15/17 复用,签名不可改):
- run_eval(cases, retriever) -> dict:retriever 只需实现
  retrieve(work, snapshot, query, k) -> list[hit],hit 需带
  source_id / work / provenance(list) / revision(int|None) / source_kind。
- 本模块只依赖标准库:评测器必须能脱离 store/LLM 独立运行,
  这样 CI 门禁和影子对比(Spectron)都能秒级跑完。
- 真实 retriever 由后续任务往 RETRIEVERS 注册,今天 CLI 先用内置
  FakeRetriever 端到端把门禁链路跑通。
- RETRIEVERS 注册契约:值必须是工厂 factory(cases) -> retriever,接受
  黄金用例列表作为唯一位置参数(Task 8 接入真实检索器时同样要遵守)。

用法:
  scribe3/.venv/bin/python -m scribe3.tools.context_memory_eval \
      --gold scribe3/tests/fixtures/context_memory_gold.json \
      --output /tmp/eval.json --retriever fake:clean
任一门槛不满足 exit 1。
"""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, NotRequired, TypedDict

# 12 个固定分类:锁死枚举,新增类必须改这里并同步补齐 3 例,防止黄金集悄悄漂移
CATEGORIES = (
    "global_continuity",
    "focus_switch",
    "cross_work_isolation",
    "canonical_priority",
    "temporal_validity",
    "focalizer_knowledge",
    "decision_recall",
    "correction_supersession",
    "material_association",
    "uncertainty",
    "provenance",
    "stale_revision",
)

CASES_PER_CATEGORY = 3

REQUIRED_FIELDS = (
    "id", "category", "work", "snapshot", "query",
    "must_include", "must_exclude", "expected_source_kinds",
)

DEFAULT_GOLD_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "context_memory_gold.json"

# 验收门槛:首期 36 例与未来 120 例版共用同一组阈值
GATES = {
    "recall_at_10": (">=", 0.90),
    "ndcg_at_10": (">=", 0.85),
    "provenance_coverage": (">=", 1.0),
    "cross_work_leaks": ("==", 0),
    "exclusion_violations": ("==", 0),
    "stale_revision_accepts": ("==", 0),
    "p95_ms": ("<", 250.0),
}


class EvalCase(TypedDict):
    """黄金用例的结构(仅 expected_revision 可选,其余必填)。"""
    id: str
    category: str
    work: str
    snapshot: dict
    query: str
    must_include: list[str]
    must_exclude: list[str]
    expected_source_kinds: list[str]
    expected_revision: NotRequired[int]


@dataclass(frozen=True)
class EvalResult:
    recall_at_10: float
    ndcg_at_10: float
    provenance_coverage: float
    cross_work_leaks: int
    exclusion_violations: int
    stale_revision_accepts: int
    p95_ms: float


@dataclass(frozen=True)
class Hit:
    """retriever 返回的最小命中契约,真实 retriever 的 hit 只要鸭子类型兼容即可。"""
    source_id: str
    work: str
    source_kind: str
    provenance: list = field(default_factory=list)
    revision: int | None = None


def load_gold_cases(path: str | Path = DEFAULT_GOLD_PATH) -> list[EvalCase]:
    """读取并校验黄金集:结构错误直接抛 ValueError,拒绝带病评测。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("黄金集顶层必须是数组")
    seen_ids: set[str] = set()
    seen_queries: set[tuple[str, str]] = set()
    for case in raw:
        missing = [f for f in REQUIRED_FIELDS if f not in case]
        if missing:
            raise ValueError(f"用例 {case.get('id', '?')} 缺字段: {missing}")
        if case["category"] not in CATEGORIES:
            raise ValueError(f"用例 {case['id']} 分类非法: {case['category']}")
        if not case["must_include"]:
            raise ValueError(f"用例 {case['id']} must_include 不能为空")
        # 注意:expected_source_kinds 仅供 Task 8 检索层做召回参考,本期不参与打分与门禁
        if not case["expected_source_kinds"]:
            raise ValueError(f"用例 {case['id']} expected_source_kinds 不能为空")
        if not isinstance(case["snapshot"], dict):
            raise ValueError(f"用例 {case['id']} snapshot 必须是对象")
        if case["id"] in seen_ids:
            raise ValueError(f"用例 id 重复: {case['id']}")
        seen_ids.add(case["id"])
        # (work, query) 唯一:FakeRetriever 以此为答案索引键,重复会导致答非所问
        key = (case["work"], case["query"])
        if key in seen_queries:
            raise ValueError(f"(work, query) 重复: {key}")
        seen_queries.add(key)
    counts = Counter(c["category"] for c in raw)
    bad = {cat: counts.get(cat, 0) for cat in CATEGORIES if counts.get(cat, 0) != CASES_PER_CATEGORY}
    extra = set(counts) - set(CATEGORIES)
    if bad or extra:
        raise ValueError(f"每类必须恰好 {CASES_PER_CATEGORY} 例,不符: {bad or extra}")
    return raw


# ---------- 指标计算 ----------

def _ndcg(ids: list[str], relevant: set[str], k: int = 10) -> float:
    """标准二值 nDCG@k:must_include 即相关集。"""
    dcg = sum(1.0 / math.log2(i + 2) for i, sid in enumerate(ids[:k]) if sid in relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


def _violates_exclusion(hit, excluded: set[str]) -> bool:
    """hit 是否命中 must_exclude:

    - 精确匹配:hit.source_id 恰好是被排除条目(正典优先/时态/修正覆盖等类的核心考点);
    - "work:" 前缀语义:形如 "work:<书名>" 或 "work:<书名>/<条目>" 的排除项,
      表示"整本他书都不许出现"——hit.work 等于去前缀书名即违规。
    """
    for entry in excluded:
        if hit.source_id == entry:
            return True
        if entry.startswith("work:") and hit.work == entry[len("work:"):].split("/")[0]:
            return True
    return False


def score_case(case: EvalCase, hits: list, ids: list[str], relevant: set[str],
               elapsed_ms: float) -> dict:
    """单例打分:返回聚合所需的原始计数,而非最终比率(便于 micro/macro 分开算)。"""
    top_ids = ids[:10]
    excluded = set(case["must_exclude"])
    leaks = 0
    violations = 0
    stale = 0
    expected_rev = case.get("expected_revision")
    for hit in hits[:10]:
        # 跨 work 泄漏:hit 的 work 字段与用例所属书不符(隔离墙被穿)
        if hit.work != case["work"]:
            leaks += 1
        # must_exclude 违规:独立于跨 work 泄漏计数——canonical_priority/temporal_validity/
        # correction_supersession/uncertainty 等类靠它设防(同书的错误版本也要拦)
        if _violates_exclusion(hit, excluded):
            violations += 1
        # 过期 revision:retriever 声称的版本旧于用例期望版本却仍被接受;
        # revision=None 表示 retriever 未声称版本,不计为过期(真实接入后由 Task 8 保证必带)
        if expected_rev is not None and hit.revision is not None and hit.revision < expected_rev:
            stale += 1
    return {
        "case_id": case["id"],
        "category": case["category"],
        "recall": len(set(top_ids) & relevant) / len(relevant),
        "ndcg": _ndcg(ids, relevant),
        "provenance_ok": sum(1 for h in hits if getattr(h, "provenance", None)),
        "hit_count": len(hits),
        "cross_work_leaks": leaks,
        "exclusion_violations": violations,
        "stale_revision_accepts": stale,
        "elapsed_ms": elapsed_ms,
    }


def aggregate_scores(rows: list[dict]) -> dict:
    """聚合:recall/ndcg 宏平均;溯源覆盖对全部 hit 做 micro(一个断溯源都藏不住)。"""
    n = len(rows)
    total_hits = sum(r["hit_count"] for r in rows)
    times = sorted(r["elapsed_ms"] for r in rows)
    # p95 取最近秩(nearest-rank)分位:样本少时偏保守,不做插值
    p95 = times[max(0, math.ceil(0.95 * n) - 1)] if times else 0.0
    result = EvalResult(
        recall_at_10=sum(r["recall"] for r in rows) / n if n else 0.0,
        ndcg_at_10=sum(r["ndcg"] for r in rows) / n if n else 0.0,
        provenance_coverage=(sum(r["provenance_ok"] for r in rows) / total_hits) if total_hits else 1.0,
        cross_work_leaks=sum(r["cross_work_leaks"] for r in rows),
        exclusion_violations=sum(r["exclusion_violations"] for r in rows),
        stale_revision_accepts=sum(r["stale_revision_accepts"] for r in rows),
        p95_ms=p95,
    )
    return {**asdict(result), "cases": rows}


def run_eval(cases: list[dict], retriever) -> dict:
    rows = []
    for case in cases:
        started = time.perf_counter()
        hits = retriever.retrieve(case["work"], case["snapshot"], case["query"], 10)
        elapsed_ms = (time.perf_counter() - started) * 1000
        ids = [hit.source_id for hit in hits]
        relevant = set(case["must_include"])
        rows.append(score_case(case, hits, ids, relevant, elapsed_ms))
    return aggregate_scores(rows)


def gate_failures(result: dict) -> list[str]:
    """返回未过门槛的描述列表;空列表 = 全绿。"""
    ops = {">=": lambda a, b: a >= b, "==": lambda a, b: a == b, "<": lambda a, b: a < b}
    failures = []
    for metric, (op, threshold) in GATES.items():
        value = result[metric]
        if not ops[op](value, threshold):
            failures.append(f"{metric}={value} 未满足 {op} {threshold}")
    return failures


# ---------- FakeRetriever:让指标器可被正反两面验证 ----------

class FakeRetriever:
    """按黄金集答案键作弊的假检索器,用于验证指标器本身。

    mode 语义:
    - clean:命中全部 must_include,溯源齐全、revision 达标 → 应全绿;
    - cross_work_leak:在 clean 基础上混入一条他书 hit(且无溯源)→ 指标器必须数出泄漏;
    - excluded_leak:在 clean 基础上混入 must_exclude[0](同 work、有溯源、revision 达标,
      专门伪装成"体面"的错误答案)→ 必须数出 exclusion_violations;
    - stale_revision:命中正确但声称的 revision 低于期望 → 必须数出过期接受;
    - partial_recall:每例只召回第一条 must_include → recall/ndcg 应下降。
    """

    def __init__(self, cases: list[EvalCase] | None = None, mode: str = "clean"):
        cases = cases if cases is not None else load_gold_cases()
        self._by_key = {(c["work"], c["query"]): c for c in cases}
        self._mode = mode

    @classmethod
    def clean(cls, cases: list[EvalCase] | None = None) -> "FakeRetriever":
        return cls(cases, mode="clean")

    @classmethod
    def with_cross_work_leak(cls, cases: list[EvalCase] | None = None) -> "FakeRetriever":
        return cls(cases, mode="cross_work_leak")

    @classmethod
    def with_excluded_leak(cls, cases: list[EvalCase] | None = None) -> "FakeRetriever":
        return cls(cases, mode="excluded_leak")

    @classmethod
    def with_stale_revision(cls, cases: list[EvalCase] | None = None) -> "FakeRetriever":
        return cls(cases, mode="stale_revision")

    @classmethod
    def with_partial_recall(cls, cases: list[EvalCase] | None = None) -> "FakeRetriever":
        return cls(cases, mode="partial_recall")

    def retrieve(self, work: str, snapshot: dict, query: str, k: int) -> list[Hit]:
        case = self._by_key.get((work, query))
        if case is None:
            return []
        expected_rev = case.get("expected_revision")
        kind = case["expected_source_kinds"][0]
        wanted = case["must_include"]
        if self._mode == "partial_recall":
            wanted = wanted[:1]
        revision = expected_rev
        if self._mode == "stale_revision" and expected_rev is not None:
            revision = expected_rev - 1
        hits = [Hit(source_id=sid, work=work, source_kind=kind,
                    provenance=[f"gold:{case['id']}"], revision=revision)
                for sid in wanted]
        if self._mode == "cross_work_leak":
            # 故意伪造他书泄漏:work 不符 + 无溯源,两个指标都应亮红
            other = "eval_book_b" if work != "eval_book_b" else "eval_book_a"
            hits.append(Hit(source_id=f"work:{other}/fact:泄漏条目", work=other,
                            source_kind="fact", provenance=[], revision=None))
        if self._mode == "excluded_leak" and case["must_exclude"]:
            # 故意混入被排除条目,且伪装得很"体面"(同 work/带溯源/版本达标),
            # 只有 exclusion_violations 指标能拦住它
            hits.append(Hit(source_id=case["must_exclude"][0], work=work,
                            source_kind=kind, provenance=[f"gold:{case['id']}"],
                            revision=expected_rev))
        return hits[:k]


# 检索器注册点:后续 Task 8 把真实 MemoryRetriever 注册进来即可被 CLI 使用
# (契约:工厂签名 factory(cases) -> retriever,见模块 docstring)
RETRIEVERS: dict[str, Any] = {
    "fake:clean": FakeRetriever.clean,
    "fake:cross_work_leak": FakeRetriever.with_cross_work_leak,
    "fake:excluded_leak": FakeRetriever.with_excluded_leak,
    "fake:stale_revision": FakeRetriever.with_stale_revision,
    "fake:partial_recall": FakeRetriever.with_partial_recall,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="上下文与记忆黄金评测集门禁")
    parser.add_argument("--gold", default=str(DEFAULT_GOLD_PATH), help="黄金集 JSON 路径")
    parser.add_argument("--output", default=None, help="评测结果 JSON 输出路径")
    parser.add_argument("--retriever", default="fake:clean",
                        help=f"检索器名,可选: {', '.join(sorted(RETRIEVERS))}")
    args = parser.parse_args(argv)

    # 黄金集读不到/坏 JSON/结构非法 → 一行中文错误 + exit 1,不吐裸 traceback
    try:
        cases = load_gold_cases(args.gold)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"黄金集加载失败({args.gold}): {exc}")
        return 1
    factory = RETRIEVERS.get(args.retriever)
    if factory is None:
        parser.error(f"未注册的检索器: {args.retriever}(可选: {', '.join(sorted(RETRIEVERS))})")
    result = run_eval(cases, factory(cases))

    if args.output:
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {k: result[k] for k in
               ("recall_at_10", "ndcg_at_10", "provenance_coverage",
                "cross_work_leaks", "exclusion_violations",
                "stale_revision_accepts", "p95_ms")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    failures = gate_failures(result)
    if failures:
        print("门禁未过:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"门禁全绿({len(cases)} 例)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

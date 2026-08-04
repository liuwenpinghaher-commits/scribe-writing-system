"""默认定稿门闩 · 纯策略,零 app/store import。

契约(写作方案强制闭环 · 门A / KR1):
  · 默认写路径:post-check(或确定性等价链)→ triage → blocking 禁落 final;
  · advisory 不自动改写(本模块只裁决落库,从不改 prose);
  · pass 允许落库;
  · danger_draft 显式旁路,默认关;
  · 检测降级不得假绿 pass(复用 loop.triage)。

与工艺门闩(evaluate_save_craft_gate)正交:工艺管脚手架齐套,本门管质控三分流。
"""
from __future__ import annotations

import os
from typing import Any


def finalize_gate_env_enabled() -> bool:
    """SCRIBE3_FINALIZE_GATE 默认开启(1);测试 conftest 钉 0。"""
    v = os.environ.get("SCRIBE3_FINALIZE_GATE", "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def evaluate_finalize_gate(
    post: dict | None,
    *,
    danger_draft: bool = False,
    skip: bool = False,
) -> dict[str, Any]:
    """据 post-check 同构结果裁决是否允许正文定稿落库。

    返回::
        {
          allowed: bool,
          code: str,           # ok | advisory_accepted | blocked | danger_bypass | skipped | no_post
          verdict: str,        # pass | advisory | blocking | skipped | danger_bypass
          triage: dict,        # loop.triage 原样(或空)
          detail: str,
          blocking: list,
          advisory_items: list,
        }

    策略:
      · skip / 环境关 → allowed,不跑 triage
      · danger_draft → 始终 allowed(显式危险旁路),仍附 triage 供 UI 警示
      · post 缺失且门开启 → 不允许(fail-closed:没查≠放行)
      · triage blocking → 不允许
      · advisory → 允许(人点存正文=已审阅待批项;本门绝不改写)
      · pass → 允许
    """
    empty_triage: dict[str, Any] = {
        "verdict": "skipped", "blocking": [], "advisory_count": 0,
        "advisory_items": [], "degraded_stages": [], "leaks": [],
    }
    if skip or not finalize_gate_env_enabled():
        return {
            "allowed": True, "code": "skipped", "verdict": "skipped",
            "triage": empty_triage, "detail": "finalize gate off or skip",
            "blocking": [], "advisory_items": [],
        }

    triage: dict[str, Any] = empty_triage
    if post is not None:
        from scribe3.loop import triage as _triage
        triage = _triage(post)

    if danger_draft:
        return {
            "allowed": True, "code": "danger_bypass",
            "verdict": "danger_bypass",
            "triage": triage,
            "detail": "危险草稿旁路:已跳过定稿门闩,正文仍可能带 blocking/advisory",
            "blocking": list(triage.get("blocking") or []),
            "advisory_items": list(triage.get("advisory_items") or []),
        }

    if post is None:
        return {
            "allowed": False, "code": "no_post", "verdict": "blocking",
            "triage": empty_triage,
            "detail": "定稿门闩开启但未提供 post-check 结果,fail-closed 阻断",
            "blocking": [{"detector": "finalize_gate", "kind": "no_post",
                          "quote": "", "note": "缺少 post-check"}],
            "advisory_items": [],
        }

    verdict = str(triage.get("verdict") or "pass")
    blocking = list(triage.get("blocking") or [])
    advisory_items = list(triage.get("advisory_items") or [])

    if verdict == "blocking":
        return {
            "allowed": False, "code": "blocked", "verdict": "blocking",
            "triage": triage,
            "detail": "定稿门闩:blocking 质控未清,默认禁止落 final(可显式 danger_draft)",
            "blocking": blocking, "advisory_items": advisory_items,
        }
    if verdict == "advisory":
        return {
            "allowed": True, "code": "advisory_accepted", "verdict": "advisory",
            "triage": triage,
            "detail": "定稿门闩:advisory 待批项随人审存稿放行(本门不改写正文)",
            "blocking": [], "advisory_items": advisory_items,
        }
    return {
        "allowed": True, "code": "ok", "verdict": "pass",
        "triage": triage,
        "detail": "定稿门闩:pass",
        "blocking": [], "advisory_items": [],
    }


def build_deterministic_post(
    prose: str,
    *,
    leaks: list | None = None,
    leaks_degraded: bool = False,
    issues: list | None = None,
    punct_suggestions: list | None = None,
    ai_grade: dict | None = None,
    degraded_stages: list | None = None,
    visible_chars: int | None = None,
) -> dict[str, Any]:
    """拼装与 /post-check 同构、可供 triage 消费的最小 post 字典(纯确定性)。

    调用方负责跑 find_leaks / find_degeneration / aggregate_ai_grade 等检测器;
    本函数只做结构装配,便于单测与存稿门闩共用。
    """
    post: dict[str, Any] = {
        "leaks": list(leaks or []),
        "leaks_degraded": bool(leaks_degraded),
        "issues": list(issues or []),
        "punct_suggestions": list(punct_suggestions or []),
        "degraded_stages": list(degraded_stages or []),
    }
    if ai_grade is not None:
        post["ai_grade"] = ai_grade
    if visible_chars is None:
        visible_chars = len("".join((prose or "").split()))
    post["visible_chars"] = int(visible_chars)
    return post


def check_finalize_for_save(
    st,
    seq: int,
    prose: str,
    *,
    focalizer: str | None = None,
    danger_draft: bool = False,
    skip: bool = False,
) -> dict[str, Any]:
    """生产定稿路径共用的 pre-persist 门闩(KR1 单源)。

    由 /save-chapter、select_finalize、s3_save_chapter、dedup/polish 等 final 覆写
    路径调用。返回 evaluate_finalize_gate 同构 dict;调用方据 allowed 决定是否落库。
    """
    if skip or not finalize_gate_env_enabled():
        return evaluate_finalize_gate(None, danger_draft=False, skip=True)
    post = collect_deterministic_post_for_prose(
        prose, st=st, seq=seq, focalizer=focalizer or None)
    return evaluate_finalize_gate(post, danger_draft=bool(danger_draft), skip=False)


def build_ingest_status_row(
    ch_seq: int,
    ch: dict | None,
    *,
    pending: bool = False,
) -> dict[str, Any]:
    """单章 ingest 状态行(KR3 诚实语义 · 纯函数)。

    - ok 仅当 status==ok 且非 pending
    - failed 当 status∈{failed,parse_failed} 且非 pending
    - pending 优先于落库 status 展示
    """
    ch = ch or {}
    stt = ch.get("ingest_status")
    err = ch.get("ingest_error") or ""
    is_pending = bool(pending)
    ok = (stt == "ok") and not is_pending
    failed = (not is_pending) and stt in ("failed", "parse_failed")
    return {
        "seq": int(ch_seq),
        "ingest_status": "pending" if is_pending else (stt or "unknown"),
        "ingest_error": "" if is_pending else err,
        "ok": ok,
        "failed": failed,
        "pending": is_pending,
    }


def collect_deterministic_post_for_prose(
    prose: str,
    *,
    st=None,
    seq: int | None = None,
    focalizer: str | None = None,
) -> dict[str, Any]:
    """对正文跑可离线确定性检测,返回 triage 可用的 post 字典。

    与完整 /post-check 相比:不打 LLM(discipline/setting 等),专供存稿门闩与单测。
    fail-soft:单项失败记入 degraded_stages,不抛。
    """
    issues: list[dict] = []
    degraded: list[str] = []
    leaks: list = []
    leaks_degraded = False
    ai_grade = None

    try:
        from scribe3.critique import find_degeneration
        for h in find_degeneration(prose or "") or []:
            sev = str((h.get("severity") or h.get("meta", {}).get("severity") or "advisory"))
            issues.append({
                "type": "degeneration",
                "message": str(h.get("message") or h.get("kind") or "degeneration")[:160],
                "text": str(h.get("text") or h.get("quote") or "")[:80],
                "meta": {"severity": sev, "kind": h.get("kind") or "degeneration"},
            })
    except Exception:
        degraded.append("find_degeneration")

    try:
        from scribe3.critique import quality_flags, aggregate_ai_grade
        flags = quality_flags(prose or "")
        ai_grade = aggregate_ai_grade(flags, prose or "")
    except Exception:
        degraded.append("aggregate_ai_grade")

    if focalizer and st is not None and seq is not None:
        try:
            from scribe3.verify import find_leaks_for_chapter as find_leaks
            leaks = list(find_leaks(prose or "", st, focalizer, int(seq)) or [])
        except Exception:
            leaks_degraded = True
            degraded.append("find_leaks")

    return build_deterministic_post(
        prose,
        leaks=leaks,
        leaks_degraded=leaks_degraded,
        issues=issues,
        ai_grade=ai_grade,
        degraded_stages=degraded,
    )

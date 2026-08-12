"""章级 density_trace 持久化（G1b · 修 scorecard null 根因）。

只保留 last + prev 两帧；fail-soft；不伪造 provenance=0。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

_log = logging.getLogger("scribe3.density_trace_store")

_DENSITY_KEYS = (
    "provenance_in_prompt_tokens",
    "audit_meta_share",
    "drama_core_share",
    "envelope_canon_share",
    "envelope_recent_share",
    "meta_segments_share",
)


def _num(v: Any) -> float | int | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except Exception:
        return None


def slim_density_trace(dt: dict | None) -> dict[str, Any] | None:
    """抽取可持久化字段。"""
    if not isinstance(dt, dict) or not dt:
        return None
    out: dict[str, Any] = {}
    for k in _DENSITY_KEYS:
        if k in dt:
            out[k] = dt.get(k)
    if not out and "provenance_in_prompt_tokens" not in dt:
        # 至少保留硬字段键
        if "provenance_in_prompt" in dt:
            out["provenance_in_prompt_tokens"] = (
                1 if dt.get("provenance_in_prompt") else 0
            )
    if not out:
        return None
    out["captured_at"] = time.time()
    out["source"] = dt.get("source") or "write_assemble"
    return out


def density_delta(curr: dict | None, prev: dict | None) -> dict[str, Any] | None:
    """相对基线；缺任一帧 → None。"""
    if not isinstance(curr, dict) or not isinstance(prev, dict):
        return None
    delta: dict[str, Any] = {}
    for k in (
        "audit_meta_share",
        "drama_core_share",
        "envelope_canon_share",
        "envelope_recent_share",
        "meta_segments_share",
        "provenance_in_prompt_tokens",
    ):
        a, b = _num(curr.get(k)), _num(prev.get(k))
        if a is None or b is None:
            delta[k] = None
        else:
            delta[k] = round(float(a) - float(b), 6)
    if all(v is None for v in delta.values()):
        return None
    return delta


def ensure_density_fields(st) -> None:
    if st is None or not hasattr(st, "ensure_density_trace_fields"):
        return
    try:
        st.ensure_density_trace_fields()
    except Exception:
        pass


def load_density_pair(st, seq: int) -> tuple[dict | None, dict | None]:
    """返回 (last, prev)。"""
    if st is None or not hasattr(st, "get_density_trace_fields"):
        return None, None
    try:
        r = st.get_density_trace_fields(int(seq)) or {}
        if not r:
            return None, None
        last = prev = None
        raw = r.get("density_trace_json")
        if raw:
            last = json.loads(raw) if isinstance(raw, str) else raw
        raw_p = r.get("density_trace_prev_json")
        if raw_p:
            prev = json.loads(raw_p) if isinstance(raw_p, str) else raw_p
        if not isinstance(last, dict):
            last = None
        if not isinstance(prev, dict):
            prev = None
        return last, prev
    except Exception as e:
        _log.debug("load_density_pair fail-soft: %s", e)
        return None, None


def upsert_density_trace(st, seq: int, density_trace: dict | None) -> dict[str, Any]:
    """写入 last，把旧 last 推到 prev。返回 {ok, last, prev, delta}。"""
    slim = slim_density_trace(density_trace)
    if slim is None:
        return {"ok": False, "reason": "empty_trace"}
    if st is None:
        return {"ok": False, "reason": "no_store", "last": slim}
    ensure_density_fields(st)
    old_last, _old_prev = load_density_pair(st, int(seq))
    prev = old_last  # 旧 last → prev
    delta = density_delta(slim, prev)
    try:
        if hasattr(st, "set_density_trace_fields"):
            st.set_density_trace_fields(
                int(seq),
                cur_json=json.dumps(slim, ensure_ascii=False),
                prev_json=(json.dumps(prev, ensure_ascii=False) if prev else None),
            )
        return {
            "ok": True,
            "last": slim,
            "prev": prev,
            "delta": delta,
        }
    except Exception as e:
        _log.warning("upsert_density_trace seq=%s fail-soft: %s", seq, e)
        return {
            "ok": False,
            "reason": str(e)[:120],
            "last": slim,
            "prev": prev,
            "delta": delta,
        }


def resolve_density_for_scorecard(
    st, seq: int, *, memory_report: dict | None = None,
) -> tuple[dict | None, dict | None]:
    """scorecard 用：(density, density_delta)。

    优先 memory_report 派生；否则持久化 last；delta 相对 prev。
    """
    curr = None
    if isinstance(memory_report, dict) and memory_report:
        # budget_report 可能只有 domain_lengths
        if "audit_meta_share" in memory_report or "provenance_in_prompt_tokens" in memory_report:
            curr = slim_density_trace(memory_report)
        elif memory_report.get("domain_lengths"):
            try:
                from scribe3.injection_registry import density_trace_for_segments
                curr = slim_density_trace(
                    density_trace_for_segments(
                        domain_lengths=memory_report.get("domain_lengths"),
                        order_indices=memory_report.get("order_indices"),
                    )
                )
            except Exception:
                curr = None
    last, prev = load_density_pair(st, int(seq)) if st is not None else (None, None)
    if curr is None:
        curr = last
        delta = density_delta(curr, prev) if curr else None
    else:
        # 内存 curr 相对持久化 last（上一帧）
        delta = density_delta(curr, last if last else prev)
    return curr, delta

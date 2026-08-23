"""N-04：开写前检查北极星与母题。pilot / loop / chat_write 共用。"""
from __future__ import annotations

from typing import Any


def journey_precheck_block(st: Any) -> dict[str, Any] | None:
    """未立北极星或母题时返回阻断字典；旗关或检查失败 fail-open 返回 None。"""
    try:
        from scribe3.feature_flags import flag_truthy
        if not flag_truthy("SCRIBE3_JOURNEY_PRECHECK"):
            return None
        intent = st.get_intent() if hasattr(st, "get_intent") else {}
        ns = str((intent or {}).get("north_star") or (intent or {}).get("premise") or "").strip()
        motifs = st.list_motifs() if hasattr(st, "list_motifs") else []
        if not ns or len(motifs or []) < 1:
            return {
                "code": "journey_precheck",
                "message": "还没立北极星或母题，先走完旅程再开写",
            }
    except Exception:
        return None
    return None

"""续写仪式 · 快照来自真实 store 字段。"""
from __future__ import annotations

import hashlib
from typing import Any


def build_continue_snapshot(st, seq: int, *, work: str = "main") -> dict[str, Any]:
    """从 store 只读字段构建续写快照(禁止 LLM 编造状态)。"""
    ch: dict = {}
    try:
        ch = st.get_chapter(int(seq)) or {}
    except Exception:
        ch = {}
    prose = ch.get("prose") or ""
    prose_hash = hashlib.sha256(prose.encode("utf-8")).hexdigest()[:16] if prose else ""
    focalizer = ch.get("focalizer") or ""

    open_promises: list[dict] = []
    overdue: list[dict] = []
    try:
        if hasattr(st, "promises_with_lifecycle"):
            for p in st.promises_with_lifecycle(max_chapter=int(seq)) or []:
                if (p.get("status") or "open") != "open":
                    continue
                row = {"text": (p.get("text") or "")[:60],
                       "setup_chapter": p.get("setup_chapter")}
                open_promises.append(row)
                if (p.get("window") or {}).get("state") == "overdue":
                    overdue.append(row)
        elif hasattr(st, "open_promises"):
            for p in st.open_promises() or []:
                open_promises.append({
                    "text": (p.get("text") or "")[:60],
                    "setup_chapter": p.get("setup_chapter"),
                })
    except Exception:
        pass

    open_loops: list = []
    try:
        if hasattr(st, "open_loops"):
            open_loops = list(st.open_loops() or [])[:8]
    except Exception:
        pass

    char_state: dict | None = None
    try:
        if focalizer and hasattr(st, "get_char_state"):
            char_state = st.get_char_state(focalizer, int(seq))
        elif focalizer and hasattr(st, "char_state_at"):
            char_state = st.char_state_at(focalizer, int(seq))
    except Exception:
        char_state = None

    tail = prose[-200:] if prose else ""

    return {
        "work": work,
        "seq": int(seq),
        "focalizer": focalizer,
        "prose_hash": prose_hash,
        "prose_tail": tail,
        "open_promises": open_promises[:8],
        "overdue_promises": overdue[:5],
        "open_loops": open_loops,
        "char_state": char_state,
        "source": "store_fields",
        "note": "状态来自库字段,非 LLM 编造",
    }


def continue_block_text(snapshot: dict | None) -> str:
    """写入 write_assemble 的摘要块。"""
    if not snapshot:
        return ""
    lines = [
        "\n\n## 续写状态快照(接笔用,勿无视)",
        f"- 章:{snapshot.get('seq')} 焦点:{snapshot.get('focalizer') or '—'}",
        f"- 正文戳:{snapshot.get('prose_hash') or '—'}",
    ]
    ops = snapshot.get("open_promises") or []
    if ops:
        bits = "；".join(
            f"第{p.get('setup_chapter')}章:{(p.get('text') or '')[:24]}"
            for p in ops[:5])
        lines.append(f"- 开着的承诺:{bits}")
    ov = snapshot.get("overdue_promises") or []
    if ov:
        lines.append(f"- 超期承诺:{len(ov)} 条,优先处理")
    tail = (snapshot.get("prose_tail") or "").strip()
    if tail:
        lines.append(f"- 近文尾句:{tail[:120].replace(chr(10), ' ')}")
    lines.append("- 续写须承接上列状态,勿重置人物情绪/伤情/未了之事。")
    return "\n".join(lines)


def reread_allowed(
    *,
    require_reread: bool,
    acked: bool,
    is_generate: bool = True,
) -> dict[str, Any]:
    """硬模式:require 且未 ack 时禁止 generate;草稿存可放行。"""
    if not require_reread:
        return {"allowed": True, "code": "require_off"}
    if not is_generate:
        return {"allowed": True, "code": "draft_ok"}
    if acked:
        return {"allowed": True, "code": "acked"}
    return {
        "allowed": False,
        "code": "reread_required",
        "detail": "续写硬模式:请确认已重读近文并 ack 后再生成",
    }

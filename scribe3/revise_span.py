"""R8 W3: span revise preview only — never persist."""
from __future__ import annotations

import difflib
from typing import Any

from scribe3.story_constraint_prompt import format_story_constraint_block, span_revise_system


def resolve_span(prose: str, *, quote: str = "", start: int | None = None, end: int | None = None) -> tuple[int, int, str]:
    body = prose or ""
    if quote:
        i = body.find(quote)
        if i < 0:
            raise ValueError("quote_not_found")
        return i, i + len(quote), quote
    if start is None or end is None:
        raise ValueError("span_unspecified")
    s, e = int(start), int(end)
    if s < 0 or e > len(body) or s >= e:
        raise ValueError("span_out_of_range")
    return s, e, body[s:e]


def make_unified_diff(old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            (old or "").splitlines(keepends=True) or [""],
            (new or "").splitlines(keepends=True) or [""],
            fromfile="old",
            tofile="new",
        )
    )


def run_span_revise(
    *,
    selected: str,
    instruction: str,
    contract: dict | None = None,
    complete_fn=None,
) -> dict[str, Any]:
    """Preview only. applied is always False."""
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        fn = hermes_complete
    else:
        fn = complete_fn
    sys_txt = span_revise_system()
    extra = format_story_constraint_block(contract)  # 仅场面头
    if extra:
        sys_txt = sys_txt + "\n" + extra
    user = f"选区：\n{selected}\n\n改法：{instruction or '改成更像人说话的一句'}\n只输出改后选区。"
    replaced = fn(user, system=sys_txt)
    if not isinstance(replaced, str) or not replaced.strip():
        raise RuntimeError("llm_empty")
    replaced = replaced.strip()
    return {
        "replaced": replaced,
        "diff": make_unified_diff(selected, replaced),
        "applied": False,
        "mode": "span",
    }

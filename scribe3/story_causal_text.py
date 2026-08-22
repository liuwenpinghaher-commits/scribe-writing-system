"""前因后果注入正文：禁止把内部 event id 喂给模型。纯函数，无 I/O。"""
from __future__ import annotations

import re

_EVENT_TOKEN = re.compile(
    r"^(?:event:)?(?:⟨)?i\d[\w\-:.⟩]*$|"
    r"^event:[A-Za-z0-9_\-⟨⟩:]+$|"
    r"^⟨i\d[^⟩]*⟩$"
)
_CHAPTER_PREFIX = re.compile(r"^第\d+章\s*")


def is_internal_event_id(text: str) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    check = _CHAPTER_PREFIX.sub("", raw).strip()
    if check.startswith("event:"):
        return True
    return bool(_EVENT_TOKEN.match(check) or _EVENT_TOKEN.match(raw))


def humanize_causal_body(text: str) -> str:
    """丢掉 event:i5-0 / ⟨i5-0⟩ 这类行；留下章标题人话。"""
    kept: list[str] = []
    for line in (text or "").splitlines():
        payload = line.lstrip("- ").strip()
        if not payload:
            continue
        # 「第3章 event:i5-0」整行丢掉
        tail = _CHAPTER_PREFIX.sub("", payload).strip()
        if is_internal_event_id(payload) or is_internal_event_id(tail):
            continue
        if "event:" in payload and len(re.sub(r"\s+", "", tail)) < 48:
            continue
        kept.append(line if line.startswith("-") else f"- {payload}")
    return "\n".join(kept)

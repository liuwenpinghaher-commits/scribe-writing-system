"""注入内容指纹去重（O10 · 强于 40 字子串）。"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any


def inject_dedup_fingerprint_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_INJECT_DEDUP") or "1").strip().lower()
    return raw not in ("0", "false", "off", "no", "dual", "legacy")


def content_fingerprint(text: str) -> str:
    """归一化指纹：去空白+小写后 SHA256 前 32 hex。"""
    normalized = re.sub(r"\s+", "", (text or "").lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def deduplicate_paragraphs(
    texts: list[str],
    *,
    min_chars: int = 20,
) -> tuple[list[str], dict[str, Any]]:
    """跨段段落去重。返回 (kept_texts, report)。"""
    seen: set[str] = set()
    kept: list[str] = []
    dropped = 0
    for text in texts:
        if not text:
            kept.append(text)
            continue
        paras = text.split("\n\n")
        unique: list[str] = []
        for para in paras:
            if len(para.strip()) < min_chars:
                unique.append(para)
                continue
            fp = content_fingerprint(para)
            if fp in seen:
                dropped += 1
                continue
            seen.add(fp)
            unique.append(para)
        kept.append("\n\n".join(unique))
    return kept, {
        "mode": "fingerprint" if inject_dedup_fingerprint_enabled() else "legacy_pass",
        "dropped_paragraphs": dropped,
        "fingerprints_seen": len(seen),
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
    }


def is_duplicate_text(a: str, b: str) -> bool:
    """两段是否视为重复（指纹相等）。"""
    if not inject_dedup_fingerprint_enabled():
        return (a or "")[:40] == (b or "")[:40] and bool(a)
    return content_fingerprint(a) == content_fingerprint(b) and bool((a or "").strip())

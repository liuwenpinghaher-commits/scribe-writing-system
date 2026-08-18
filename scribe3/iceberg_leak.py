"""冰山落库破绽词：与 secret_guard 词表对齐。纯函数，无 I/O。"""
from __future__ import annotations

import json
from typing import Any

ICEBERG_LEAK_WORDS = ("锁眼", "匙孔", "门芯")


class PersistIcebergLeak(ValueError):
    """persist 前扫到破绽词，调用方应 422。"""

    def __init__(self, hits: list[dict[str, str]]):
        self.hits = hits
        words = sorted({h.get("word") or "" for h in hits if h.get("word")})
        super().__init__("冰山层不得写破绽词：" + "、".join(w for w in words if w))


def find_iceberg_leak_words(text: str | None) -> list[str]:
    src = text or ""
    return [w for w in ICEBERG_LEAK_WORDS if w in src]


def _beat_blob(beats: Any) -> str:
    chunks: list[str] = []
    gcd_keys = (
        "goal", "conflict", "turn", "choice", "cost", "underwater",
        "dilemma", "decision", "hook", "text", "body",
    )
    if isinstance(beats, list):
        for b in beats:
            if isinstance(b, dict):
                chunks.append(" ".join(str(b.get(k) or "") for k in gcd_keys))
            else:
                chunks.append(str(b or ""))
    elif isinstance(beats, dict):
        chunks.append(json.dumps(beats, ensure_ascii=False))
    elif beats:
        chunks.append(str(beats))
    return "\n".join(chunks)


def _spine_blob(spine: Any) -> str:
    if not spine:
        return ""
    if isinstance(spine, str):
        return spine
    if isinstance(spine, dict):
        bits = []
        for k, v in spine.items():
            if k.startswith("_") or k == "forbid":
                continue
            if isinstance(v, list):
                bits.append(" ".join(
                    str(it.get("delta") or it.get("id") or it) if isinstance(it, dict) else str(it)
                    for it in v
                ))
            else:
                bits.append(str(v or ""))
        return "\n".join(bits)
    return str(spine)


def _deduction_blob(deds: Any) -> str:
    chunks: list[str] = []
    if isinstance(deds, list):
        for d in deds:
            if isinstance(d, dict):
                chunks.append(str(
                    d.get("text") or d.get("prose") or d.get("projection") or ""
                ))
            else:
                chunks.append(str(d or ""))
    elif isinstance(deds, dict):
        chunks.append(json.dumps(deds, ensure_ascii=False))
    elif deds:
        chunks.append(str(deds))
    return "\n".join(chunks)


def scan_persist_fields_for_leaks(fields: dict | None) -> list[dict[str, str]]:
    """扫将要落库的大纲/节拍/演绎/草稿。返回 [{field, word}]，空=干净。"""
    src = fields if isinstance(fields, dict) else {}
    hits: list[dict[str, str]] = []
    def _without_forbid_lines(text: str) -> str:
        return "\n".join(
            ln for ln in str(text or "").splitlines()
            if not ln.lstrip().startswith("禁令")
        )

    blobs = {
        "synopsis": _without_forbid_lines(str(src.get("synopsis") or "")),
        "chapter_spine": _spine_blob(src.get("chapter_spine")),
        "beats": _beat_blob(src.get("beats")),
        "scene_truth": str(src.get("scene_truth") or ""),
        "deductions": _deduction_blob(src.get("deductions")),
        "draft": str(src.get("draft") or ""),
    }
    for field, blob in blobs.items():
        if not blob:
            continue
        for word in find_iceberg_leak_words(blob):
            hits.append({"field": field, "word": word})
    return hits


def reject_persist_leaks(fields: dict | None) -> None:
    hits = scan_persist_fields_for_leaks(fields)
    if hits:
        raise PersistIcebergLeak(hits)

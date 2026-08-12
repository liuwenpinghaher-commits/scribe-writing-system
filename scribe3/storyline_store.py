"""GAP-16：独立 Storyline 数据模型（进程内 + 可选 store 落盘 JSON 字段）。

实体：storyline 有 id/title/arc_kind/chapter_seqs/notes；可编辑。
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

_LOCK = threading.Lock()
# work -> {id: storyline_dict}
_BY_WORK: dict[str, dict[str, dict[str, Any]]] = {}


def _new_id() -> str:
    return "sl_" + uuid.uuid4().hex[:10]


def list_storylines(work: str = "main") -> list[dict[str, Any]]:
    with _LOCK:
        return list((_BY_WORK.get(work) or {}).values())


def get_storyline(work: str, sid: str) -> dict[str, Any] | None:
    with _LOCK:
        return dict((_BY_WORK.get(work) or {}).get(sid) or {}) or None


def create_storyline(
    work: str,
    *,
    title: str,
    arc_kind: str = "main",
    chapter_seqs: list[int] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    sid = _new_id()
    row = {
        "id": sid,
        "work": work,
        "title": (title or "").strip() or "未命名故事线",
        "arc_kind": (arc_kind or "main").strip() or "main",
        "chapter_seqs": [int(x) for x in (chapter_seqs or [])],
        "notes": notes or "",
        "updated_at": time.time(),
        "editable": True,
    }
    with _LOCK:
        _BY_WORK.setdefault(work, {})[sid] = row
    return dict(row)


def update_storyline(
    work: str,
    sid: str,
    *,
    title: str | None = None,
    arc_kind: str | None = None,
    chapter_seqs: list[int] | None = None,
    notes: str | None = None,
) -> dict[str, Any] | None:
    with _LOCK:
        bucket = _BY_WORK.setdefault(work, {})
        row = bucket.get(sid)
        if not row:
            return None
        if title is not None:
            row["title"] = title.strip() or row["title"]
        if arc_kind is not None:
            row["arc_kind"] = arc_kind.strip() or row["arc_kind"]
        if chapter_seqs is not None:
            row["chapter_seqs"] = [int(x) for x in chapter_seqs]
        if notes is not None:
            row["notes"] = notes
        row["updated_at"] = time.time()
        return dict(row)


def delete_storyline(work: str, sid: str) -> bool:
    with _LOCK:
        bucket = _BY_WORK.get(work) or {}
        return bucket.pop(sid, None) is not None


def link_chapter(work: str, sid: str, seq: int) -> dict[str, Any] | None:
    with _LOCK:
        row = (_BY_WORK.get(work) or {}).get(sid)
        if not row:
            return None
        seqs = list(row.get("chapter_seqs") or [])
        s = int(seq)
        if s not in seqs:
            seqs.append(s)
            seqs.sort()
        row["chapter_seqs"] = seqs
        row["updated_at"] = time.time()
        return dict(row)


def clear_for_tests() -> None:
    with _LOCK:
        _BY_WORK.clear()

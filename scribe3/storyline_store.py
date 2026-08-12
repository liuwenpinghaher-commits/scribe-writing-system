"""GAP-16 / SL1：独立 Storyline 数据模型（进程内 + 可选 store 落盘）。

实体：id/title/arc_kind/chapter_seqs/notes/craft_only；可编辑。
craft_only 默认 true；仅 true 时 notes 可进写路径 inject。
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


def _normalize_craft_only(raw: Any, *, default: bool = True) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return default


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["craft_only"] = _normalize_craft_only(out.get("craft_only"), default=True)
    return out


def list_storylines(work: str = "main") -> list[dict[str, Any]]:
    with _LOCK:
        return [_public_row(r) for r in (_BY_WORK.get(work) or {}).values()]


def get_storyline(work: str, sid: str) -> dict[str, Any] | None:
    with _LOCK:
        row = (_BY_WORK.get(work) or {}).get(sid)
        return _public_row(row) if row else None


def create_storyline(
    work: str,
    *,
    title: str,
    arc_kind: str = "main",
    chapter_seqs: list[int] | None = None,
    notes: str = "",
    craft_only: bool | None = None,
) -> dict[str, Any]:
    sid = _new_id()
    row = {
        "id": sid,
        "work": work,
        "title": (title or "").strip() or "未命名故事线",
        "arc_kind": (arc_kind or "main").strip() or "main",
        "chapter_seqs": [int(x) for x in (chapter_seqs or [])],
        "notes": notes or "",
        "craft_only": _normalize_craft_only(craft_only, default=True),
        "updated_at": time.time(),
        "editable": True,
    }
    with _LOCK:
        _BY_WORK.setdefault(work, {})[sid] = row
    return _public_row(row)


def update_storyline(
    work: str,
    sid: str,
    *,
    title: str | None = None,
    arc_kind: str | None = None,
    chapter_seqs: list[int] | None = None,
    notes: str | None = None,
    craft_only: bool | None = None,
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
        if craft_only is not None:
            row["craft_only"] = _normalize_craft_only(craft_only, default=True)
        row["updated_at"] = time.time()
        return _public_row(row)


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
        return _public_row(row)


def clear_for_tests() -> None:
    with _LOCK:
        _BY_WORK.clear()

"""Storyline Surreal 持久化 mixin（GAP-16 / SL1 craft_only）。"""
from __future__ import annotations

import time
import uuid
from typing import Any


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


class StorylineStoreMixin:
    """挂在 SurrealStore 上的 storyline CRUD。"""

    def list_storylines(self) -> list[dict[str, Any]]:
        try:
            rows = self._query(
                "SELECT * FROM storyline ORDER BY updated_at DESC;"
            ) or []
            return [self._storyline_row(r) for r in rows if isinstance(r, dict)]
        except Exception:
            return []

    def get_storyline(self, sid: str) -> dict[str, Any] | None:
        try:
            rows = self._query(
                "SELECT * FROM type::record('storyline', $id);",
                {"id": _bare_id(sid)},
            ) or []
            if rows and isinstance(rows[0], dict):
                return self._storyline_row(rows[0])
        except Exception:
            pass
        return None

    def create_storyline(
        self,
        *,
        title: str,
        arc_kind: str = "main",
        chapter_seqs: list[int] | None = None,
        notes: str = "",
        craft_only: bool | None = None,
    ) -> dict[str, Any]:
        sid = "sl_" + uuid.uuid4().hex[:10]
        seqs = [int(x) for x in (chapter_seqs or [])]
        co = _normalize_craft_only(craft_only, default=True)
        try:
            self._execute_write(
                "CREATE type::record('storyline', $id) SET "
                "title=$t, arc_kind=$k, chapter_seqs=$cs, notes=$n, "
                "craft_only=$co, updated_at=time::now();",
                {
                    "id": sid,
                    "t": (title or "").strip() or "未命名故事线",
                    "k": (arc_kind or "main").strip() or "main",
                    "cs": seqs,
                    "n": notes or "",
                    "co": co,
                },
            )
        except Exception:
            return {
                "id": sid,
                "title": (title or "").strip() or "未命名故事线",
                "arc_kind": arc_kind or "main",
                "chapter_seqs": seqs,
                "notes": notes or "",
                "craft_only": co,
                "updated_at": time.time(),
                "editable": True,
                "persisted": False,
            }
        row = self.get_storyline(sid) or {
            "id": sid,
            "title": title,
            "arc_kind": arc_kind,
            "chapter_seqs": seqs,
            "notes": notes,
            "craft_only": co,
            "editable": True,
            "persisted": True,
        }
        row["persisted"] = True
        row["craft_only"] = _normalize_craft_only(row.get("craft_only"), default=co)
        return row

    def update_storyline(
        self,
        sid: str,
        *,
        title: str | None = None,
        arc_kind: str | None = None,
        chapter_seqs: list[int] | None = None,
        notes: str | None = None,
        craft_only: bool | None = None,
    ) -> dict[str, Any] | None:
        cur = self.get_storyline(sid)
        if not cur:
            return None
        nt = title if title is not None else cur.get("title")
        nk = arc_kind if arc_kind is not None else cur.get("arc_kind")
        ncs = chapter_seqs if chapter_seqs is not None else cur.get("chapter_seqs") or []
        nn = notes if notes is not None else cur.get("notes")
        nco = (
            _normalize_craft_only(craft_only, default=True)
            if craft_only is not None
            else _normalize_craft_only(cur.get("craft_only"), default=True)
        )
        try:
            self._execute_write(
                "UPDATE type::record('storyline', $id) SET "
                "title=$t, arc_kind=$k, chapter_seqs=$cs, notes=$n, "
                "craft_only=$co, updated_at=time::now();",
                {
                    "id": _bare_id(sid),
                    "t": nt,
                    "k": nk,
                    "cs": list(ncs),
                    "n": nn,
                    "co": nco,
                },
            )
        except Exception:
            return None
        return self.get_storyline(sid)

    def link_storyline_chapter(self, sid: str, seq: int) -> dict[str, Any] | None:
        cur = self.get_storyline(sid)
        if not cur:
            return None
        seqs = list(cur.get("chapter_seqs") or [])
        s = int(seq)
        if s not in seqs:
            seqs.append(s)
            seqs.sort()
        return self.update_storyline(sid, chapter_seqs=seqs)

    def delete_storyline(self, sid: str) -> bool:
        try:
            self._execute_write(
                "DELETE type::record('storyline', $id);",
                {"id": _bare_id(sid)},
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _storyline_row(r: dict[str, Any]) -> dict[str, Any]:
        rid = r.get("id") or r.get("storyline_id") or ""
        if hasattr(rid, "__str__"):
            rid = str(rid)
        if ":" in rid:
            rid = rid.split(":", 1)[-1]
        return {
            "id": rid,
            "title": r.get("title") or "",
            "arc_kind": r.get("arc_kind") or "main",
            "chapter_seqs": list(r.get("chapter_seqs") or []),
            "notes": r.get("notes") or "",
            "craft_only": _normalize_craft_only(r.get("craft_only"), default=True),
            "updated_at": r.get("updated_at"),
            "editable": True,
            "persisted": True,
        }


def _bare_id(sid: str) -> str:
    s = str(sid or "")
    return s.split(":", 1)[-1] if ":" in s else s

"""SurrealStore mixin: author story_move cards (seed cards stay in repo JSON)."""
from __future__ import annotations

import json
from typing import Any


class StoryMovesMixin:
    def ensure_story_move_table(self) -> None:
        try:
            self._raw_query("DEFINE TABLE IF NOT EXISTS story_move SCHEMALESS;")
        except Exception:
            pass

    def list_author_story_moves(self) -> list[dict[str, Any]]:
        self.ensure_story_move_table()
        rows = self._query("SELECT * FROM story_move") or []
        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            slug = str(r.get("slug") or "").strip()
            if not slug:
                continue
            rec = dict(r)
            rec["slug"] = slug
            rec["origin"] = rec.get("origin") or "author"
            rec["status"] = rec.get("status") or "pending"
            if isinstance(rec.get("formula_json"), str):
                try:
                    rec["formula"] = json.loads(rec["formula_json"])
                except Exception:
                    rec["formula"] = {}
            if isinstance(rec.get("aliases"), str):
                try:
                    rec["aliases"] = json.loads(rec["aliases"])
                except Exception:
                    rec["aliases"] = []
            out.append(rec)
        return out

    def upsert_author_story_move(self, card: dict[str, Any]) -> None:
        self.ensure_story_move_table()
        slug = str((card or {}).get("slug") or "").strip()
        if not slug:
            raise ValueError("slug required")
        formula = card.get("formula") if isinstance(card.get("formula"), dict) else {}
        aliases = card.get("aliases") if isinstance(card.get("aliases"), list) else []
        self._execute_write(
            "UPSERT type::record('story_move', $id) SET slug=$slug, name=$name, "
            "one_liner=$ol, formula_family=$ff, formula_json=$fj, straight_line=$sl, "
            "aliases=$al, status=$st, origin=$og, usage=$us",
            {
                "id": slug,
                "slug": slug,
                "name": str(card.get("name") or "")[:16],
                "ol": str(card.get("one_liner") or "")[:40],
                "ff": str(card.get("formula_family") or ""),
                "fj": json.dumps(formula, ensure_ascii=False),
                "sl": str(card.get("straight_line") or ""),
                "al": json.dumps(aliases, ensure_ascii=False),
                "st": str(card.get("status") or "pending"),
                "og": str(card.get("origin") or "author"),
                "us": str(card.get("usage") or ""),
            },
        )

    def set_story_move_status(self, slug: str, status: str) -> bool:
        self.ensure_story_move_table()
        s = (slug or "").strip()
        if not s:
            return False
        rows = self._query(
            "SELECT slug FROM type::record('story_move', $id) LIMIT 1", {"id": s}
        ) or []
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('story_move', $id) SET status=$st",
            {"id": s, "st": status},
        )
        return True

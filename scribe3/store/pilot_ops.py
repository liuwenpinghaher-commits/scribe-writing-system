"""SurrealStore mixin: pilot / idea public APIs (EH-05 / PR-EH-7a).

Routers must not call ``_query`` / ``_execute_write`` directly.
"""
from __future__ import annotations

from typing import Any


class PilotOpsMixin:
    """Pilot steer / state / inbox idea helpers."""

    def append_pilot_steer(self, seq: int, text: str, *, max_len: int = 2000) -> None:
        """追加 pilot_steer，帽 max_len。"""
        prev = ""
        try:
            ch = self.get_chapter(int(seq)) or {}
            prev = str(ch.get("pilot_steer") or "")
        except Exception:
            prev = ""
        t = (text or "").strip()
        if not t:
            return
        merged = ((prev + "\n") if prev else "") + t
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET pilot_steer=$s",
            {"seq": int(seq), "s": merged[-int(max_len):]},
        )

    def clear_pilot_fields(self, seq: int) -> None:
        """退出 pilot：清 state/parked/card/steer。"""
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET pilot_state=NONE, pilot_state_at=NONE, "
            "pilot_parked=NONE, pilot_card=NONE, pilot_steer=NONE",
            {"seq": int(seq)},
        )

    def list_pilot_parked_seqs(self) -> list[int]:
        rows = self._query(
            "SELECT seq, pilot_parked FROM chapter:.. WHERE pilot_parked != NONE"
        ) or []
        out: list[int] = []
        for rr in rows:
            if (rr.get("pilot_parked") or "").strip():
                try:
                    out.append(int(rr.get("seq")))
                except (TypeError, ValueError):
                    pass
        return out

    def list_pilot_chapter_rows(self) -> list[dict[str, Any]]:
        return list(
            self._query(
                "SELECT seq, pilot_state, pilot_parked, pilot_card, synopsis FROM chapter:.. "
                "WHERE pilot_state != NONE ORDER BY seq"
            )
            or []
        )

    def create_idea(
        self,
        *,
        text: str,
        route_kind: str,
        target_seq: int | None,
        note: str,
        status: str,
        question: str | None = None,
    ) -> None:
        self._execute_write(
            "CREATE idea SET text=$t, route_kind=$k, target_seq=$sq, note=$n, status=$st_, "
            "question=$q, created_at=time::now()",
            {
                "t": text,
                "k": route_kind,
                "sq": target_seq,
                "n": note or "",
                "st_": status,
                "q": question,
            },
        )

    def set_idea_status(self, idea_id: str, status: str = "done") -> None:
        self._execute_write(
            "UPDATE type::record('idea',$id) SET status=$st",
            {"id": idea_id, "st": status},
        )

    def set_idea_question(self, idea_id: str, question: str) -> None:
        self._execute_write(
            "UPDATE type::record('idea',$id) SET question=$q",
            {"id": idea_id, "q": question},
        )

    def list_inbox_ideas(self) -> list[dict[str, Any]]:
        return list(
            self._query(
                "SELECT meta::id(id) AS id, text, route_kind, note, status, question "
                "FROM idea WHERE status IN ['pending_approval', 'unclear']"
            )
            or []
        )

    def set_chapter_stage_state(self, seq: int, stage_state: dict) -> bool:
        """stage_state 持久化（product_backlog advance）。"""
        if hasattr(self, "update_chapter_meta"):
            return bool(self.update_chapter_meta(int(seq), {"stage_state": stage_state}))
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET stage_state=$ss",
            {"seq": int(seq), "ss": stage_state},
        )
        return True

    def get_proposition_archived(self, local: str) -> bool:
        rows = self._query(
            "SELECT archived FROM type::record('proposition',$local) LIMIT 1",
            {"local": local},
        ) or []
        return bool(rows and rows[0].get("archived"))

    def get_character_archive_row(self, local: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT meta::id(id) AS local, name, backstory, backstory_secret, aliases, personality_tags, "
            "importance, appearance, personality_detail, abilities, weaknesses, "
            "first_appearance, surface_goal, deep_need, internal_conflict, fear, archived FROM "
            "type::record('character',$local) LIMIT 1",
            {"local": local},
        ) or []
        return rows[0] if rows else None

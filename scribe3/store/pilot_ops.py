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

    # ── P1-2：业务模块公共读/写（pilot / pulse / ingest / audit）──

    def get_pilot_state_fields(self, seq: int) -> dict[str, Any]:
        """pilot.read_state 用：窄字段 pilot_state / at / parked。"""
        rows = self._query(
            "SELECT pilot_state, pilot_state_at, pilot_parked FROM type::record('chapter',$seq)",
            {"seq": int(seq)},
        ) or []
        return rows[0] if rows else {}

    def set_pilot_state(self, seq: int, state: str, parked: str = "", *, at: int | None = None) -> None:
        import time as _time
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET pilot_state=$s, pilot_state_at=$t, pilot_parked=$p",
            {
                "seq": int(seq),
                "s": state,
                "t": int(at if at is not None else _time.time()),
                "p": parked or "",
            },
        )

    def set_pilot_parked(self, seq: int, parked: str) -> None:
        """仅写 pilot_parked（连写异常停靠等，不改 pilot_state）。"""
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET pilot_parked=$p",
            {"seq": int(seq), "p": parked or ""},
        )

    def get_chapter_quality_fields(self, seq: int) -> dict[str, Any]:
        """pulse 质量维：ingest_status / error / qc_issues。"""
        rows = self._query(
            "SELECT ingest_status, ingest_error, qc_issues FROM type::record('chapter',$seq)",
            {"seq": int(seq)},
        ) or []
        return rows[0] if rows else {}

    def get_chapter_ingest_prose_fp(self, seq: int) -> str | None:
        rows = self._query(
            "SELECT ingest_prose_fp, ingest_status FROM type::record('chapter', $seq)",
            {"seq": int(seq)},
        ) or []
        if not rows:
            return None
        return (rows[0].get("ingest_prose_fp") or "").strip() or None

    def find_active_learned_fact_local(self, fact_text: str) -> str | None:
        """ingest learned 去重：attribute=获知 且 value 完全相等。"""
        needle = (fact_text or "").strip()
        if not needle:
            return None
        rows = self._query(
            "SELECT meta::id(id) AS local, value FROM proposition "
            "WHERE attribute = '获知' AND valid_to IS NONE"
        ) or []
        for r in rows:
            if (r.get("value") or "").strip() == needle:
                return str(r["local"])
        return None

    def reader_knows_exists(self, proposition_ref: str) -> bool:
        rows = self._query(
            "SELECT proposition FROM reader_knows WHERE proposition = $p",
            {"p": proposition_ref},
        ) or []
        return bool(rows)

    def purge_audit_events_older_than(self, days: int) -> None:
        d = max(1, int(days))
        self._execute_write(
            f"DELETE audit_event WHERE at < time::now() - {d}d;",
            {},
        )

    def query_audit_events(
        self,
        *,
        table: str | None = None,
        kind: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(500, int(limit or 50)))
        if table and kind:
            rows = self._query(
                "SELECT * FROM audit_event WHERE source_table=$t AND kind=$k "
                f"ORDER BY at DESC LIMIT {lim};",
                {"t": table, "k": kind},
            ) or []
        elif table:
            rows = self._query(
                "SELECT * FROM audit_event WHERE source_table=$t "
                f"ORDER BY at DESC LIMIT {lim};",
                {"t": table},
            ) or []
        elif kind:
            rows = self._query(
                "SELECT * FROM audit_event WHERE kind=$k "
                f"ORDER BY at DESC LIMIT {lim};",
                {"k": kind},
            ) or []
        else:
            rows = self._query(
                f"SELECT * FROM audit_event ORDER BY at DESC LIMIT {lim};",
            ) or []
        return [r for r in rows if isinstance(r, dict)]

    def upsert_bridge_proposition(
        self,
        *,
        local: str | None,
        entity_id: str,
        attribute: str,
        value: str,
        source: str,
    ) -> str:
        """codex_secret_bridge：CREATE 或 UPDATE 桥接命题，返回 local id。"""
        if local:
            self._execute_write(
                "UPDATE type::record('proposition', $local) SET value=$val, secret=true, source=$src",
                {"local": local, "val": value, "src": source},
            )
            return local
        self._execute_write(
            "CREATE proposition SET entity_id=$eid, attribute=$attr, value=$val, "
            "valid_from=1, secret=true, source=$src",
            {"eid": entity_id, "attr": attribute, "val": value, "src": source},
        )
        return ""

    def delete_bridge_proposition(self, local: str) -> None:
        self._execute_write(
            "DELETE type::record('proposition', $local)",
            {"local": local},
        )

    def find_bridge_proposition_local(
        self, entity_id: str, attribute: str, source: str
    ) -> str | None:
        rows = self._query(
            "SELECT meta::id(id) AS local FROM proposition "
            "WHERE entity_id=$eid AND attribute=$attr AND source=$src LIMIT 1",
            {"eid": entity_id, "attr": attribute, "src": source},
        ) or []
        return rows[0]["local"] if rows else None

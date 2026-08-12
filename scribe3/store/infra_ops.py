"""SurrealStore mixin: infra ops for lease / cache_watch (private-call zero for adapters)."""
from __future__ import annotations

from typing import Any


class InfraOpsMixin:
    """ingest_lease · chapter lease fields · cache_watch 公开 API。"""

    def ensure_ingest_lease_table(self) -> None:
        self._raw_query("DEFINE TABLE IF NOT EXISTS ingest_lease SCHEMALESS;")
        for field, typ in (
            ("work", "option<string>"),
            ("seq", "option<int>"),
            ("owner", "option<string>"),
            ("until", "option<float>"),
            ("state", "option<string>"),
            ("heartbeat_at", "option<float>"),
        ):
            try:
                self._raw_query(
                    f"DEFINE FIELD IF NOT EXISTS {field} ON ingest_lease TYPE {typ};"
                )
            except Exception:
                pass

    def get_ingest_lease_row(self, lease_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT owner AS o, until AS u FROM type::record('ingest_lease', $id)",
            {"id": lease_id},
        ) or []
        return rows[0] if rows else None

    def upsert_ingest_lease_row(
        self, lease_id: str, *, work: str, seq: int, owner: str, until: float
    ) -> None:
        self._execute_write(
            "UPSERT type::record('ingest_lease', $id) SET "
            "work=$w, seq=$s, owner=$o, until=$u, state='leased', heartbeat_at=$u",
            {
                "id": lease_id,
                "w": work,
                "s": int(seq),
                "o": owner,
                "u": float(until),
            },
        )

    def clear_ingest_lease_row(self, lease_id: str, owner: str) -> None:
        self._execute_write(
            "UPDATE type::record('ingest_lease', $id) SET "
            "owner=NONE, until=0, state='idle' "
            "WHERE owner = $o",
            {"id": lease_id, "o": owner},
        )

    def create_only_ingest_lease(
        self, lease_id: str, *, work: str, seq: int, owner: str, until: float
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('ingest_lease', $id) SET "
            "work=$w, seq=$s, owner=$o, until=$u, state='leased', heartbeat_at=$u",
            {
                "id": lease_id,
                "w": work,
                "s": int(seq),
                "o": owner,
                "u": float(until),
            },
        )

    def cas_update_ingest_lease(
        self, lease_id: str, *, work: str, seq: int, owner: str, until: float, now: float
    ) -> None:
        self._execute_write(
            "UPDATE type::record('ingest_lease', $id) SET "
            "owner=$o, until=$u, state='leased', heartbeat_at=$u, work=$w, seq=$s "
            "WHERE owner = NONE OR owner = NONE OR until = NONE "
            "OR until < $now OR until <= $now OR owner = $o OR owner = ''",
            {
                "id": lease_id,
                "w": work,
                "s": int(seq),
                "o": owner,
                "u": float(until),
                "now": float(now),
            },
        )

    def ensure_chapter_lease_fields(self) -> None:
        try:
            self._raw_query(
                "DEFINE FIELD IF NOT EXISTS ingest_lease_owner ON chapter TYPE option<string>;"
            )
            self._raw_query(
                "DEFINE FIELD IF NOT EXISTS ingest_lease_until ON chapter TYPE option<float>;"
            )
        except Exception:
            pass

    def get_chapter_lease_fields(self, seq: int) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT ingest_lease_owner AS o, ingest_lease_until AS u "
            "FROM type::record('chapter',$seq)",
            {"seq": int(seq)},
        ) or []
        return rows[0] if rows else None

    def set_chapter_lease_fields(self, seq: int, owner: str, until: float) -> None:
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET "
            "ingest_lease_owner=$o, ingest_lease_until=$u",
            {"seq": int(seq), "o": owner, "u": float(until)},
        )

    def clear_chapter_lease_fields(self, seq: int, owner: str) -> None:
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET "
            "ingest_lease_owner=NONE, ingest_lease_until=NONE "
            "WHERE ingest_lease_owner = $o",
            {"seq": int(seq), "o": owner},
        )

    def cas_update_chapter_lease(
        self, seq: int, *, owner: str, until: float, now: float
    ) -> None:
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET "
            "ingest_lease_owner=$o, ingest_lease_until=$u "
            "WHERE ingest_lease_owner = NONE OR ingest_lease_owner = NONE "
            "OR ingest_lease_until = NONE OR ingest_lease_until < $now "
            "OR ingest_lease_until <= $now OR ingest_lease_owner = $o "
            "OR ingest_lease_owner = ''",
            {
                "seq": int(seq),
                "o": owner,
                "u": float(until),
                "now": float(now),
            },
        )

    def delete_cache_watch_older_than(self, age_seconds: int) -> None:
        age = max(60, int(age_seconds or 3600))
        self._execute_write(
            f"DELETE cache_watch WHERE at < time::now() - {age}s;",
            {},
        )

    def delete_cache_watch_older_than_created_at(self, age_seconds: int) -> None:
        age = max(60, int(age_seconds or 3600))
        self._raw_query(
            f"DELETE cache_watch WHERE created_at < time::now() - {age}s;"
        )

    def create_cache_watch_row(self, table_name: str, work: str = "") -> None:
        self._execute_write(
            "CREATE cache_watch SET table_name=$t, work=$w;",
            {"t": str(table_name), "w": work or ""},
        )

"""SurrealStore mixin: write_run_card 读写。"""
from __future__ import annotations

from typing import Any


class RunCardOpsMixin:
    def create_only_write_run_card(self, run_id: str, fields: dict[str, Any]) -> None:
        self._execute_write(
            "CREATE ONLY type::record('write_run_card', $run_id) SET "
            "run_id=$run_id, work=$work, chapter=$chapter, kind=$kind, "
            "phase=$phase, request_id=$request_id, manifest_id=$manifest_id, "
            "actual_input_hash=$actual_input_hash, outcome_id=$outcome_id, "
            "outcome_status=$outcome_status, outcome_usage=$outcome_usage, "
            "assemble_ok=$assemble_ok, verdict=$verdict, summary=$summary, "
            "rows=$rows, quality=$quality, facts=$facts, caps=$caps, l2=$l2, "
            "density=$density, quality_flags=$quality_flags, schema_ver=$schema_ver",
            {"run_id": run_id, **fields},
        )

    def get_write_run_card(self, run_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT * FROM write_run_card WHERE run_id=$run_id LIMIT 1",
            {"run_id": run_id},
        ) or []
        return rows[0] if rows else None

    def get_write_run_card_by_request(
        self, request_id: str, kind: str = "write",
    ) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT * FROM write_run_card WHERE request_id=$rid AND kind=$kind "
            "ORDER BY created_at DESC LIMIT 1",
            {"rid": request_id, "kind": kind},
        ) or []
        return rows[0] if rows else None

    def list_write_run_cards(
        self,
        *,
        chapter: int | None = None,
        kind: str | None = None,
        verdict: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(100, int(limit or 20)))
        wheres: list[str] = []
        params: dict[str, Any] = {}
        if chapter is not None:
            wheres.append("chapter=$chapter")
            params["chapter"] = int(chapter)
        if kind:
            wheres.append("kind=$kind")
            params["kind"] = str(kind)
        if verdict:
            wheres.append("verdict=$verdict")
            params["verdict"] = str(verdict)
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        rows = self._query(
            f"SELECT * FROM write_run_card {where} ORDER BY created_at DESC LIMIT {lim}",
            params,
        ) or []
        return [r for r in rows if isinstance(r, dict)]

    def update_write_run_card_outcome(
        self,
        request_id: str,
        *,
        outcome_id: str | None,
        status: str | None,
        usage: dict | None,
        kind: str = "write",
    ) -> None:
        self._execute_write(
            "UPDATE write_run_card SET outcome_id=$oid, outcome_status=$st, "
            "outcome_usage=$usage WHERE request_id=$rid AND kind=$kind",
            {
                "oid": outcome_id,
                "st": status,
                "usage": usage,
                "rid": request_id,
                "kind": kind,
            },
        )

    def purge_write_run_cards_older_than(self, days: int) -> None:
        d = max(1, int(days))
        self._execute_write(
            f"DELETE write_run_card WHERE created_at < time::now() - {d}d;",
            {},
        )

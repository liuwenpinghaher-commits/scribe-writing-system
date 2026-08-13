"""SurrealStore mixin: pipeline_chain / pipeline_span。"""
from __future__ import annotations

from typing import Any


_CHAIN_SET = (
    "trace_id=$trace_id, work=$work, chapter=$chapter, kind=$kind, phase=$phase, "
    "status=$status, cursor_step_key=$cursor_step_key, headline=$headline, "
    "started_at=$started_at, ended_at=$ended_at, duration_ms=$duration_ms, "
    "span_count=$span_count, red_count=$red_count, manifest_id=$manifest_id, "
    "actual_input_hash=$actual_input_hash, outcome_id=$outcome_id, "
    "outcome_status=$outcome_status, outcome_usage=$outcome_usage, "
    "contrast_run_id=$contrast_run_id, contrast_summary=$contrast_summary, "
    "notes=$notes, schema_ver=$schema_ver"
)

_SPAN_SET = (
    "span_id=$span_id, parent_span_id=$parent_span_id, trace_id=$trace_id, "
    "work=$work, chapter=$chapter, kind=$kind, step_key=$step_key, "
    "step_title=$step_title, layer=$layer, tier=$tier, zone=$zone, "
    "status=$status, expected=$expected, expected_reason=$expected_reason, "
    "actual=$actual, actual_reason=$actual_reason, verdict=$verdict, "
    "input=$input, compute=$compute, output=$output, timing=$timing, "
    "events=$events, quality=$quality, error=$error, links=$links, "
    "schema_ver=$schema_ver"
)


class PipelineTraceOpsMixin:
    def create_only_pipeline_chain(self, trace_id: str, fields: dict[str, Any]) -> None:
        payload = {"trace_id": trace_id, **fields}
        self._execute_write(
            "CREATE ONLY type::record('pipeline_chain', $trace_id) SET " + _CHAIN_SET,
            payload,
        )

    def insert_pipeline_spans(self, rows: list[dict[str, Any]]) -> None:
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            sid = str(row.get("span_id") or "")
            if not sid:
                continue
            self._execute_write(
                "CREATE ONLY type::record('pipeline_span', $span_id) SET " + _SPAN_SET,
                dict(row),
            )

    def update_pipeline_chain(self, trace_id: str, fields: dict[str, Any]) -> None:
        if not fields:
            return
        sets = ", ".join(f"{k}=${k}" for k in fields)
        self._execute_write(
            f"UPDATE pipeline_chain SET {sets} WHERE trace_id=$trace_id",
            {"trace_id": trace_id, **fields},
        )

    def update_pipeline_span(self, span_id: str, fields: dict[str, Any]) -> None:
        if not fields:
            return
        sets = ", ".join(f"{k}=${k}" for k in fields)
        self._execute_write(
            f"UPDATE pipeline_span SET {sets} WHERE span_id=$span_id",
            {"span_id": span_id, **fields},
        )

    def get_pipeline_chain(self, trace_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT * FROM pipeline_chain WHERE trace_id=$trace_id LIMIT 1",
            {"trace_id": trace_id},
        ) or []
        return rows[0] if rows else None

    def get_pipeline_chain_by_contrast(self, run_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT * FROM pipeline_chain WHERE contrast_run_id=$rid LIMIT 1",
            {"rid": run_id},
        ) or []
        return rows[0] if rows else None

    def list_pipeline_chains(
        self,
        *,
        chapter: int | None = None,
        kind: str | None = None,
        status: str | None = None,
        since=None,
        until=None,
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
        if status:
            wheres.append("status=$status")
            params["status"] = str(status)
        if since:
            wheres.append("created_at >= $since")
            params["since"] = since
        if until:
            wheres.append("created_at <= $until")
            params["until"] = until
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        rows = self._query(
            f"SELECT * FROM pipeline_chain {where} ORDER BY created_at DESC LIMIT {lim}",
            params,
        ) or []
        return [r for r in rows if isinstance(r, dict)]

    def list_pipeline_spans(
        self,
        *,
        trace_id: str | None = None,
        step_key: str | None = None,
        status: str | None = None,
        chapter: int | None = None,
        layer: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(200, int(limit or 50)))
        wheres: list[str] = []
        params: dict[str, Any] = {}
        if trace_id:
            wheres.append("trace_id=$trace_id")
            params["trace_id"] = str(trace_id)
        if step_key:
            wheres.append("step_key=$step_key")
            params["step_key"] = str(step_key)
        if status:
            wheres.append("status=$status")
            params["status"] = str(status)
        if chapter is not None:
            wheres.append("chapter=$chapter")
            params["chapter"] = int(chapter)
        if layer:
            wheres.append("layer=$layer")
            params["layer"] = str(layer)
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        rows = self._query(
            f"SELECT * FROM pipeline_span {where} ORDER BY created_at ASC LIMIT {lim}",
            params,
        ) or []
        return [r for r in rows if isinstance(r, dict)]

    def neighbor_traces(
        self, *, work: str, chapter: int, kind: str, created_at,
    ) -> dict[str, Any]:
        prev = self._query(
            "SELECT trace_id FROM pipeline_chain WHERE work=$w AND chapter=$c "
            "AND kind=$k AND created_at < $ts ORDER BY created_at DESC LIMIT 1",
            {"w": work, "c": int(chapter), "k": kind, "ts": created_at},
        ) or []
        nxt = self._query(
            "SELECT trace_id FROM pipeline_chain WHERE work=$w AND chapter=$c "
            "AND kind=$k AND created_at > $ts ORDER BY created_at ASC LIMIT 1",
            {"w": work, "c": int(chapter), "k": kind, "ts": created_at},
        ) or []
        return {
            "prev_trace_id": (prev[0].get("trace_id") if prev else None),
            "next_trace_id": (nxt[0].get("trace_id") if nxt else None),
        }

    def purge_pipeline_traces_older_than(self, days: int) -> dict[str, Any]:
        d = max(1, int(days))
        self._execute_write(
            f"DELETE pipeline_span WHERE created_at < time::now() - {d}d;",
            {},
        )
        self._execute_write(
            f"DELETE pipeline_chain WHERE created_at < time::now() - {d}d;",
            {},
        )
        return {"ok": True, "ttl_days": d}

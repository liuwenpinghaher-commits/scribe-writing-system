"""SurrealStore mixin: pipeline_chain / pipeline_span。"""
from __future__ import annotations

import logging
from typing import Any

from scribe3.pipeline_trace import CHAIN_PATCH_KEYS

_log = logging.getLogger("scribe3.pipeline_trace")

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


def _intersect_chain_fields(fields: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (fields or {}).items():
        if k in CHAIN_PATCH_KEYS:
            out[k] = v
        elif k != "trace_id":
            _log.warning("pipeline_chain drop unknown key %s", k)
    return out


def _rejected_column(exc: BaseException, keys: list[str]) -> str | None:
    msg = str(exc)
    for k in sorted(keys, key=len, reverse=True):
        if k and k in msg:
            return k
    if "fail_reasons" in keys:
        return "fail_reasons"
    return None


class PipelineTraceOpsMixin:
    def _exec_chain_write(
        self, payload: dict[str, Any], *, create: bool, trace_id: str,
    ) -> None:
        remaining = dict(payload)
        if create:
            if not str(trace_id or "").strip():
                raise ValueError("trace_id required")
            remaining["trace_id"] = str(trace_id)
        dropped: set[str] = set()
        while remaining:
            if create:
                remaining["trace_id"] = str(trace_id)
                keys = list(remaining.keys())
                sets = ", ".join(f"{k}=${k}" for k in keys)
                sql = (
                    "CREATE ONLY type::record('pipeline_chain', $trace_id) SET "
                    + sets
                )
                params = dict(remaining)
            else:
                keys = [k for k in remaining if k != "trace_id"]
                if not keys:
                    return
                sets = ", ".join(f"{k}=${k}" for k in keys)
                sql = f"UPDATE pipeline_chain SET {sets} WHERE trace_id=$trace_id"
                params = {"trace_id": trace_id, **{k: remaining[k] for k in keys}}
            try:
                self._execute_write(sql, params)
                return
            except Exception as e:
                candidates = [k for k in keys if k != "trace_id"]
                drop = _rejected_column(e, candidates)
                if drop is None or drop == "trace_id" or drop in dropped:
                    raise
                dropped.add(drop)
                remaining.pop(drop, None)
                _log.warning(
                    "pipeline_chain column rejected, retry without %s: %s", drop, e,
                )
                if create and "trace_id" not in remaining:
                    remaining["trace_id"] = str(trace_id)
                if create and set(remaining.keys()) <= {"trace_id"}:
                    raise

    def create_only_pipeline_chain(self, trace_id: str, fields: dict[str, Any]) -> None:
        tid = str(trace_id or "").strip()
        if not tid:
            raise ValueError("trace_id required")
        payload = _intersect_chain_fields(fields)
        payload["trace_id"] = tid
        self._exec_chain_write(payload, create=True, trace_id=tid)

    def insert_pipeline_logs(self, rows: list[dict[str, Any]]) -> None:
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            lid = str(row.get("log_id") or "")
            if not lid:
                continue
            self._execute_write(
                "CREATE ONLY type::record('pipeline_log', $log_id) SET "
                "log_id=$log_id, trace_id=$trace_id, span_id=$span_id, seq=$seq, "
                "ts=$ts, level=$level, step_key=$step_key, step_title=$step_title, "
                "layer=$layer, code=$code, message=$message, attrs=$attrs, "
                "work=$work, chapter=$chapter, kind=$kind, schema_ver=$schema_ver",
                dict(row),
            )

    def list_pipeline_logs(
        self,
        *,
        work: str | None = None,
        trace_id: str | None = None,
        step_key: str | None = None,
        code: str | None = None,
        empty: bool | None = None,
        since=None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        wh: list[str] = []
        params: dict[str, Any] = {"lim": max(1, min(int(limit), 500))}
        if work:
            wh.append("work=$w")
            params["w"] = work
        if trace_id:
            wh.append("trace_id=$tid")
            params["tid"] = trace_id
        if step_key:
            wh.append("step_key=$sk")
            params["sk"] = step_key
        if code:
            wh.append("code=$cd")
            params["cd"] = code
        if empty is True:
            wh.append("attrs.empty = true")
        elif empty is False:
            wh.append("attrs.empty = false")
        if since is not None:
            wh.append("created_at >= $since")
            params["since"] = since
        where = (" WHERE " + " AND ".join(wh)) if wh else ""
        rows = self._query(
            "SELECT * FROM pipeline_log" + where + " ORDER BY ts ASC LIMIT $lim",
            params,
        ) or []
        return [r for r in rows if isinstance(r, dict)]

    def _insert_recorder_rows(self, table: str, rows: list[dict[str, Any]], id_key: str) -> None:
        packed = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            rid = str(row.get(id_key) or row.get("id") or "")
            if not rid:
                continue
            clean = {k: v for k, v in row.items() if not str(k).startswith("_") and k != "created_at"}
            clean["id"] = rid
            ts = clean.get("ts")
            if isinstance(ts, str) and "T" in ts:
                try:
                    from datetime import datetime, timezone
                    raw = ts.replace("Z", "+00:00")
                    clean["ts"] = datetime.fromisoformat(raw)
                    if clean["ts"].tzinfo is None:
                        clean["ts"] = clean["ts"].replace(tzinfo=timezone.utc)
                except Exception:
                    clean.pop("ts", None)
            packed.append(clean)
        if not packed:
            return
        # 分包：事件 32、工件 8
        chunk = 8 if table == "pipeline_artifact" else 32
        for i in range(0, len(packed), chunk):
            part = packed[i:i + chunk]
            try:
                self._execute_write(
                    f"INSERT IGNORE INTO {table} $rows RETURN NONE",
                    {"rows": part},
                )
                continue
            except Exception:
                pass
            for r in part:
                try:
                    self._execute_write(
                        f"CREATE ONLY type::record('{table}', $id) CONTENT $r",
                        {"id": r["id"], "r": r},
                    )
                except Exception:
                    continue

    def insert_pipeline_events(self, rows: list[dict[str, Any]]) -> None:
        self._insert_recorder_rows("pipeline_event", rows, "event_id")

    def insert_pipeline_artifacts(self, rows: list[dict[str, Any]]) -> None:
        self._insert_recorder_rows("pipeline_artifact", rows, "artifact_id")

    def list_pipeline_events(
        self,
        *,
        work: str | None = None,
        trace_id: str | None = None,
        step_key: str | None = None,
        kind: str | None = None,
        empty: bool | None = None,
        since=None,
        after_seq: int | None = None,
        limit: int = 200,
        tag: str | None = None,
        chapter: int | None = None,
    ) -> list[dict[str, Any]]:
        cap = 2048 if trace_id else 500
        lim = max(1, min(int(limit or 200), cap))
        wh: list[str] = []
        params: dict[str, Any] = {"lim": lim}
        if work:
            wh.append("work=$w")
            params["w"] = work
        if trace_id:
            wh.append("trace_id=$tid")
            params["tid"] = trace_id
        if step_key:
            wh.append("step_key=$sk")
            params["sk"] = step_key
        if kind:
            wh.append("kind=$kd")
            params["kd"] = kind
        if empty is True:
            wh.append("empty = true")
        elif empty is False:
            wh.append("empty = false")
        if since is not None:
            wh.append("created_at >= $since")
            params["since"] = since
        if after_seq is not None:
            wh.append("seq > $aseq")
            params["aseq"] = int(after_seq)
        if chapter is not None:
            wh.append("chapter=$ch")
            params["ch"] = int(chapter)
        want_tag = str(tag or "").strip()
        if want_tag:
            wh.append("payload.tag = $ptag")
            params["ptag"] = want_tag
        where = (" WHERE " + " AND ".join(wh)) if wh else ""
        rows = self._query(
            "SELECT * FROM pipeline_event" + where + " ORDER BY seq ASC LIMIT $lim",
            params,
        ) or []
        return [r for r in rows if isinstance(r, dict)]

    def count_pipeline_events(self, **kw) -> int:
        rows = self.list_pipeline_events(**{**kw, "limit": 2048})
        return len(rows)

    def list_pipeline_artifacts(
        self,
        *,
        work: str | None = None,
        trace_id: str | None = None,
        kind: str | None = None,
        name: str | None = None,
        after_id: str | None = None,
        limit: int = 256,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit or 256), 256))
        wh: list[str] = []
        params: dict[str, Any] = {"lim": lim}
        if work:
            wh.append("work=$w")
            params["w"] = work
        if trace_id:
            wh.append("trace_id=$tid")
            params["tid"] = trace_id
        if kind:
            wh.append("kind=$kd")
            params["kd"] = kind
        if name:
            wh.append("name=$nm")
            params["nm"] = name
        where = (" WHERE " + " AND ".join(wh)) if wh else ""
        rows = self._query(
            "SELECT * FROM pipeline_artifact" + where + " ORDER BY created_at ASC LIMIT $lim",
            params,
        ) or []
        return [r for r in rows if isinstance(r, dict)]

    def get_pipeline_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT * FROM pipeline_artifact WHERE artifact_id=$id LIMIT 1",
            {"id": artifact_id},
        ) or []
        return rows[0] if rows else None

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
        payload = _intersect_chain_fields(fields)
        payload.pop("trace_id", None)
        if not payload:
            return
        self._exec_chain_write(payload, create=False, trace_id=str(trace_id))

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
            f"DELETE pipeline_log WHERE created_at < time::now() - {d}d;",
            {},
        )
        self._execute_write(
            f"DELETE pipeline_span WHERE created_at < time::now() - {d}d;",
            {},
        )
        self._execute_write(
            f"DELETE pipeline_chain WHERE created_at < time::now() - {d}d;",
            {},
        )
        return {"ok": True, "ttl_days": d}

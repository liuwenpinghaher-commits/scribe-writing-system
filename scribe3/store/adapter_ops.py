"""SurrealStore mixin: remaining adapter-facing public APIs (stats/lease/quality/health)."""
from __future__ import annotations

from typing import Any


class AdapterOpsMixin:
    """业务适配层用的窄公开 API，避免适配器直接 _query / _execute_write。"""

    # ── health ──────────────────────────────────────────────
    def ping(self) -> Any:
        rows = self._query("RETURN 1")
        return rows

    # ── stats views ─────────────────────────────────────────
    def stats_chapter_count_view(self) -> list[dict]:
        return list(self._query("SELECT n FROM stats_chapter_count;") or [])

    def count_chapters_group(self) -> list[dict]:
        return list(self._query("SELECT count() AS n FROM chapter GROUP ALL;") or [])

    def stats_open_promises_view(self) -> list[dict]:
        return list(self._query("SELECT n FROM stats_open_promises;") or [])

    def count_open_promises_group(self) -> list[dict]:
        return list(
            self._query(
                "SELECT count() AS n FROM promise WHERE status = 'open' GROUP ALL;"
            )
            or []
        )

    def stats_total_words_view(self) -> list[dict]:
        return list(self._query("SELECT total_words FROM stats_total_words;") or [])

    def sum_chapter_word_counts(self) -> list[dict]:
        return list(
            self._query(
                "SELECT math::sum(qc_word_count) AS total_words FROM chapter GROUP ALL;"
            )
            or []
        )

    def stats_phase_distribution_view(self) -> list[dict]:
        return list(self._query("SELECT stage, n FROM stats_phase_distribution;") or [])

    # ── knowledge frame ─────────────────────────────────────
    def knowledge_frame_fn(self, knower_id: str, chapter: int) -> list:
        return list(
            self._query(
                "RETURN fn::knowledge_frame($k, $ch);",
                {"k": knower_id, "ch": int(chapter)},
            )
            or []
        )

    # ── chapter quality / ingest fields ─────────────────────
    def get_chapter_ingest_status_fields(self, seq: int) -> dict[str, Any]:
        try:
            rows = self._query(
                "SELECT ingest_status, ingest_error, ingest_message "
                "FROM type::record('chapter',$seq)",
                {"seq": int(seq)},
            ) or []
        except Exception:
            rows = self._query(
                "SELECT ingest_status, ingest_error FROM type::record('chapter',$seq)",
                {"seq": int(seq)},
            ) or []
        row = rows[0] if rows else {}
        if row and not row.get("ingest_message"):
            row["ingest_message"] = row.get("ingest_error") or ""
        return row

    def set_chapter_ingest_status(
        self, seq: int, status: str, err: str = "", *, prose_fp: str | None = None
    ) -> None:
        msg = (err or "")[:200]
        params = {"seq": int(seq), "st": status, "er": msg}
        # 兼容期双写 ingest_error + ingest_message；第十一轮删 ingest_error 列后只写 ingest_message。
        # SurrealDB $st/$er 是绑定参数，不是字符串拼接。
        sets = "ingest_status=$st, ingest_error=$er, ingest_message=$er"
        if prose_fp and status == "ok":
            params["fp"] = prose_fp[:32]
            sets += ", ingest_prose_fp=$fp"
        try:
            self._execute_write(
                f"UPDATE type::record('chapter',$seq) SET {sets}",
                params,
            )
            return
        except Exception:
            self._raw_query(
                "DEFINE FIELD IF NOT EXISTS ingest_prose_fp ON chapter TYPE option<string>;"
            )
            self._raw_query(
                "DEFINE FIELD IF NOT EXISTS ingest_message ON chapter TYPE option<string>;"
            )
            self._execute_write(
                f"UPDATE type::record('chapter',$seq) SET {sets}",
                params,
            )

    def ensure_ingest_hold_fields(self) -> None:
        for field, typ in (
            ("ingest_hold_reason", "option<string>"),
            ("ingest_confirm_token", "option<string>"),
            ("ingest_hold_prose_fp", "option<string>"),
            ("ingest_hold_until", "option<float>"),
        ):
            try:
                self._raw_query(
                    f"DEFINE FIELD IF NOT EXISTS {field} ON chapter TYPE {typ};"
                )
            except Exception:
                pass

    def write_chapter_ingest_hold(
        self,
        seq: int,
        *,
        reason: str,
        token: str,
        prose_fp: str,
        until: float,
        status: str = "held",
    ) -> None:
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET "
            "ingest_hold_reason=$r, ingest_confirm_token=$t, "
            "ingest_hold_prose_fp=$fp, ingest_hold_until=$u, ingest_status=$st",
            {
                "seq": int(seq),
                "r": reason[:120],
                "t": token[:64],
                "fp": prose_fp[:32],
                "u": float(until),
                "st": status,
            },
        )

    def clear_chapter_ingest_hold(self, seq: int) -> None:
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET "
            "ingest_hold_reason=NONE, ingest_confirm_token=NONE, "
            "ingest_hold_until=NONE",
            {"seq": int(seq)},
        )

    # ── density trace ───────────────────────────────────────
    def ensure_density_trace_fields(self) -> None:
        try:
            self._raw_query(
                "DEFINE FIELD IF NOT EXISTS density_trace_json ON chapter TYPE option<string>;"
            )
            self._raw_query(
                "DEFINE FIELD IF NOT EXISTS density_trace_prev_json ON chapter TYPE option<string>;"
            )
        except Exception:
            pass

    def get_density_trace_fields(self, seq: int) -> dict[str, Any]:
        rows = self._query(
            "SELECT density_trace_json, density_trace_prev_json "
            "FROM type::record('chapter',$s)",
            {"s": int(seq)},
        ) or []
        return rows[0] if rows else {}

    def set_density_trace_fields(
        self, seq: int, *, cur_json: str | None, prev_json: str | None
    ) -> None:
        self._execute_write(
            "UPDATE type::record('chapter',$s) SET "
            "density_trace_json=$cur, density_trace_prev_json=$prev",
            {"s": int(seq), "cur": cur_json, "prev": prev_json},
        )

    # ── inflight lock table ─────────────────────────────────
    def create_inflight_lock(
        self, rid: str, *, work: str, seq: int, op: str, ttl: int
    ) -> None:
        self._execute_write(
            "CREATE type::record('inflight', $rid) CONTENT {"
            " work: $work, seq: $seq, op: $op, ttl_seconds: $ttl"
            "};",
            {"rid": rid, "work": work, "seq": int(seq), "op": op, "ttl": int(ttl)},
        )

    def delete_inflight_lock(self, rid: str) -> None:
        self._execute_write(
            "DELETE type::record('inflight', $rid);",
            {"rid": rid},
        )

    def cleanup_stale_inflight_locks(self) -> list:
        return list(
            self._query(
                "DELETE FROM inflight WHERE started_at IS NOT NONE "
                "AND time::now() - started_at > 5m RETURN BEFORE;"
            )
            or []
        )

    # ── chapter review ──────────────────────────────────────
    def upsert_chapter_review(
        self,
        local: str,
        *,
        work: str,
        seq: int,
        prose_fp: str,
        mode: str,
        issues: Any,
        coverage: Any,
        degraded: Any,
        model_id: str,
    ) -> None:
        self._execute_write(
            "UPSERT type::record('chapter_review', $local) SET "
            "work=$work, seq=$seq, prose_fp=$fp, mode=$mode, "
            "issues_json=$issues, coverage=$cov, degraded=$deg, "
            "model_id=$mid, created_at=time::now()",
            {
                "local": local,
                "work": work,
                "seq": int(seq),
                "fp": prose_fp,
                "mode": mode,
                "issues": issues,
                "cov": coverage,
                "deg": degraded,
                "mid": model_id,
            },
        )

    def get_chapter_review_row(self, local: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT * FROM type::record('chapter_review', $local) LIMIT 1",
            {"local": local},
        ) or []
        return rows[0] if rows else None

    # ── chapter_reader_ack（dual-lamp 人读确认）────────────────
    def upsert_reader_ack(
        self,
        work: str,
        seq: int,
        *,
        prose_fp: str,
        note: str = "",
        user_id: str | None = None,
        kind: str = "reader",
        contract_fp: str | None = None,
    ) -> dict[str, Any]:
        kind = (kind or "reader").strip() or "reader"
        if kind not in ("reader", "story"):
            kind = "reader"
        local = f"{work}_{int(seq)}_{kind}"
        self._execute_write(
            "UPSERT type::record('chapter_reader_ack', $local) SET "
            "work=$work, seq=$seq, prose_fp=$fp, note=$note, "
            "user_id=$uid, kind=$kind, contract_fp=$cfp, updated_at=time::now()",
            {
                "local": local,
                "work": work,
                "seq": int(seq),
                "fp": prose_fp,
                "note": (note or "")[:200],
                "uid": user_id or "",
                "kind": kind,
                "cfp": (contract_fp or "")[:32],
            },
        )
        return self.get_reader_ack(work, int(seq), kind=kind) or {
            "work": work, "seq": int(seq), "prose_fp": prose_fp, "note": note,
            "kind": kind, "contract_fp": contract_fp or "",
        }

    def get_reader_ack(self, work: str, seq: int, kind: str = "reader") -> dict[str, Any] | None:
        kind = (kind or "reader").strip() or "reader"
        local = f"{work}_{int(seq)}_{kind}"
        try:
            rows = self._query(
                "SELECT * FROM type::record('chapter_reader_ack', $local) LIMIT 1",
                {"local": local},
            ) or []
        except Exception:
            rows = []
        if rows:
            return rows[0]
        if kind == "reader":
            legacy = f"{work}_{int(seq)}"
            try:
                rows = self._query(
                    "SELECT * FROM type::record('chapter_reader_ack', $local) LIMIT 1",
                    {"local": legacy},
                ) or []
            except Exception:
                return None
            return rows[0] if rows else None
        return None

    # ── promise delete ──────────────────────────────────────
    def promise_exists(self, pid: str) -> bool:
        rows = self._query(
            "SELECT id FROM type::record('promise',$pid) LIMIT 1",
            {"pid": pid},
        ) or []
        return bool(rows)

    def delete_promise_record(self, pid: str) -> None:
        self._execute_write(
            "DELETE type::record('promise',$pid)",
            {"pid": pid},
        )

    # ── pilot card / steer ──────────────────────────────────
    def get_pilot_card(self, seq: int) -> Any:
        rows = self._query(
            "SELECT pilot_card FROM type::record('chapter',$seq)",
            {"seq": int(seq)},
        ) or []
        return (rows[0].get("pilot_card") if rows else None)

    def set_pilot_card(self, seq: int, card: Any) -> None:
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET pilot_card=$c",
            {"seq": int(seq), "c": card},
        )

    def get_pilot_steer(self, seq: int) -> str:
        rows = self._query(
            "SELECT pilot_steer FROM type::record('chapter',$seq)",
            {"seq": int(seq)},
        ) or []
        return str(((rows[0] if rows else {}).get("pilot_steer") or "")).strip()

    def get_chapter_qc_and_pilot_card(self, seq: int) -> dict[str, Any]:
        rows = self._query(
            "SELECT qc_issues, pilot_card FROM type::record('chapter',$seq)",
            {"seq": int(seq)},
        ) or []
        return rows[0] if rows else {}

    def clear_chapter_prose_for_redraft(self, seq: int) -> None:
        """SCHEMAFULL prose 是 string，不可 SET NONE；空串才合法。"""
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET prose=$p, draft=$p, qc_word_count=0",
            {"seq": int(seq), "p": ""},
        )

    # ── changefeed ──────────────────────────────────────────
    def show_table_changes(self, table: str, since_lit: str, *, limit: int = 50) -> list:
        if not str(table).replace("_", "").isalnum():
            return []
        lim = max(1, min(200, int(limit or 50)))
        q = f"SHOW CHANGES FOR TABLE {table} SINCE {since_lit} LIMIT {lim};"
        return list(self._query(q) or [])

    # ── quality / reference (API-facing) ────────────────────
    def list_reference_fingerprints(self, reference_work_id: str) -> list[dict]:
        return list(
            self._query(
                "SELECT fingerprint_id, reference_work_id, revision, source_hash, status, fingerprint, "
                "provider, model, provider_request_id, usage FROM reference_fingerprint "
                "WHERE reference_work_id=$rid ORDER BY revision DESC",
                {"rid": reference_work_id},
            )
            or []
        )

    def get_reference_work_meta(self, reference_work_id: str) -> dict | None:
        rows = self._query(
            "SELECT reference_work_id, work, title, source_hash, import_revision, status "
            "FROM reference_work WHERE reference_work_id=$rid "
            "ORDER BY import_revision DESC LIMIT 1",
            {"rid": reference_work_id},
        ) or []
        return rows[0] if rows else None

    def list_reference_works_for_work(self, work: str) -> list[dict]:
        return list(
            self._query(
                "SELECT reference_work_id, work, title, source_hash, import_revision, status "
                "FROM reference_work WHERE work=$work ORDER BY import_revision DESC",
                {"work": work},
            )
            or []
        )

    def get_reference_work_for_fingerprint(self, reference_work_id: str) -> dict | None:
        rows = self._query(
            "SELECT id, reference_work_id, source_hash, import_revision "
            "FROM reference_work WHERE reference_work_id=$rid "
            "ORDER BY import_revision DESC LIMIT 1",
            {"rid": reference_work_id},
        ) or []
        return rows[0] if rows else None

    def get_reference_source_text(self, reference_work_id: str) -> dict | None:
        rows = self._query(
            "SELECT source_text, import_revision FROM reference_work "
            "WHERE reference_work_id=$rid ORDER BY import_revision DESC LIMIT 1",
            {"rid": reference_work_id},
        ) or []
        return rows[0] if rows else None

    def latest_chapter_version_ids(self, seq: int) -> list[str]:
        rows = self._query(
            "SELECT VALUE id FROM chapter_version WHERE seq=$seq "
            "ORDER BY created_at DESC LIMIT 1",
            {"seq": int(seq)},
        ) or []
        return [str(rid) for rid in rows]

    def latest_quality_job_id_for_seq(self, seq: int) -> str | None:
        snapshot_rows = self._query(
            "SELECT VALUE snapshot FROM quality_snapshot_member "
            "WHERE chapter_version IN "
            "(SELECT VALUE id FROM chapter_version WHERE seq=$seq)",
            {"seq": int(seq)},
        ) or []
        snapshots = [s for s in snapshot_rows if s is not None]
        if not snapshots:
            return None
        job_rows = self._query(
            "SELECT job_id, created_at FROM quality_job WHERE snapshot IN $snapshots "
            "ORDER BY created_at DESC LIMIT 1",
            {"snapshots": snapshots},
        ) or []
        return job_rows[0]["job_id"] if job_rows else None

    def list_reference_craft_uses(self, work: str, chapter: int) -> list[dict]:
        return list(
            self._query(
                "SELECT chapter, request_id, manifest_id, reference_fingerprint_ids, mechanism_ids, created_at "
                "FROM reference_craft_use WHERE work=$work AND chapter=$chapter "
                "ORDER BY created_at DESC",
                {"work": work, "chapter": int(chapter)},
            )
            or []
        )

    def latest_approved_contract_ref(self, work: str) -> dict | None:
        rows = self._query(
            "SELECT contract_id, revision FROM quality_contract_revision "
            "WHERE work=$work AND approved=true ORDER BY revision DESC LIMIT 1",
            {"work": work},
        ) or []
        return rows[0] if rows else None

    def count_active_chapters(self) -> int:
        rows = self._query(
            "SELECT count() AS n FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL;"
        ) or []
        if rows and isinstance(rows[0], dict):
            return int(rows[0].get("n") or 0)
        return 0

    def first_active_chapter_seq(self) -> int | None:
        rows = self._query(
            "SELECT seq FROM chapter "
            "WHERE archived = NONE OR archived != true ORDER BY seq LIMIT 1;"
        ) or []
        if rows:
            return int(rows[0]["seq"])
        return None

    def list_voice_evolution_flags(self) -> list[dict]:
        return list(
            self._query(
                "SELECT meta::id(id) AS id, character, trigger_chapter, ingest_seq, status "
                "FROM voice_evolution_flag"
            )
            or []
        )

    def set_voice_flag_character(self, local_id: str, character: str) -> None:
        self._execute_write(
            "UPDATE type::record('voice_evolution_flag',$id) SET character=$c",
            {"id": local_id, "c": character},
        )

    def archive_stale_none_voice_flags(self) -> None:
        self._execute_write(
            "UPDATE voice_evolution_flag SET status='done' "
            "WHERE ingest_seq IS NONE AND status='open'",
            {},
        )

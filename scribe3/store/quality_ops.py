"""SurrealStore mixin: QualityStore domain public APIs (quality/store zero private)."""
from __future__ import annotations

from typing import Any


class QualityOpsMixin:
    """质量域表读写；QualityStore 适配器只应调用本 mixin，不直接 _query/_execute_write。"""

    # ── contract ────────────────────────────────────────────
    def create_only_quality_contract_revision(
        self, record_id: str, *, key: str, contract_id: str, work: str,
        revision: int, payload: dict,
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('quality_contract_revision',$record_id) SET "
            "contract_key=$key, contract_id=$contract_id, work=$work, revision=$revision, "
            "payload=$payload, approved=false, approval_version=0",
            {
                "record_id": record_id, "key": key, "contract_id": contract_id,
                "work": work, "revision": revision, "payload": payload,
            },
        )

    def create_only_reference_target(
        self, record_id: str, *, target_key: str, contract_revision: Any,
        ordinal: int, payload: dict,
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('reference_target',$record_id) SET "
            "target_key=$target_key, contract_revision=$contract_revision, "
            "ordinal=$ordinal, payload=$payload",
            {
                "record_id": record_id, "target_key": target_key,
                "contract_revision": contract_revision, "ordinal": ordinal,
                "payload": payload,
            },
        )

    def get_quality_contract_row(self, contract_id: str, revision: int) -> dict | None:
        rows = self._query(
            "SELECT payload, approved FROM quality_contract_revision "
            "WHERE contract_id=$contract_id AND revision=$revision LIMIT 1",
            {"contract_id": contract_id, "revision": revision},
        ) or []
        return rows[0] if rows else None

    def list_reference_targets_for_contract(
        self, contract_id: str, revision: int,
    ) -> list[dict]:
        return list(
            self._query(
                "SELECT payload, ordinal FROM reference_target WHERE contract_revision = "
                "(SELECT VALUE id FROM quality_contract_revision WHERE contract_id=$contract_id "
                "AND revision=$revision LIMIT 1)[0] ORDER BY ordinal",
                {"contract_id": contract_id, "revision": revision},
            )
            or []
        )

    def approve_quality_contract_cas(self, contract_id: str, revision: int) -> list:
        return list(
            self._query(
                "UPDATE quality_contract_revision SET approved=true, approval_version += 1, "
                "approved_at=time::now() WHERE contract_id=$contract_id AND revision=$revision "
                "AND approved=false AND approval_version=0 RETURN AFTER",
                {"contract_id": contract_id, "revision": revision},
            )
            or []
        )

    # ── reference work / fingerprint ────────────────────────
    def create_only_reference_work(
        self, record_id: str, *, key: str, source_text: str, fields: dict,
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('reference_work',$record_id) SET "
            "reference_key=$key, reference_work_id=$reference_work_id, work=$work, "
            "title=$title, source_hash=$source_hash, import_revision=$import_revision, "
            "status=$status, source_text=$source_text",
            {"record_id": record_id, "key": key, "source_text": source_text, **fields},
        )

    def get_reference_work_source_text_by_id(self, record_id: str) -> dict | None:
        rows = self._query(
            "SELECT source_text FROM type::record('reference_work',$record_id) LIMIT 1",
            {"record_id": record_id},
        ) or []
        return rows[0] if rows else None

    def update_reference_work_source_text(self, record_id: str, source_text: str) -> None:
        self._execute_write(
            "UPDATE type::record('reference_work',$record_id) SET source_text=$source_text",
            {"record_id": record_id, "source_text": source_text},
        )

    def get_reference_work_revision_row(
        self, reference_work_id: str, import_revision: int,
    ) -> dict | None:
        rows = self._query(
            "SELECT reference_work_id, work, title, source_hash, import_revision, status "
            "FROM reference_work WHERE reference_work_id=$reference_work_id "
            "AND import_revision=$import_revision LIMIT 1",
            {"reference_work_id": reference_work_id, "import_revision": import_revision},
        ) or []
        return rows[0] if rows else None

    def get_reference_work_by_hash(
        self, reference_work_id: str, source_hash: str,
    ) -> dict | None:
        rows = self._query(
            "SELECT id, source_hash, import_revision FROM reference_work WHERE "
            "reference_work_id=$reference_work_id AND source_hash=$source_hash "
            "ORDER BY import_revision DESC LIMIT 1",
            {"reference_work_id": reference_work_id, "source_hash": source_hash},
        ) or []
        return rows[0] if rows else None

    def create_only_reference_fingerprint(
        self, record_id: str, *, fingerprint_id: str, reference_work: Any, fields: dict,
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('reference_fingerprint',$record_id) SET "
            "fingerprint_id=$fingerprint_id, reference_work=$reference_work, "
            "reference_work_id=$reference_work_id, revision=$revision, "
            "source_hash=$source_hash, status=$status, fingerprint=$fingerprint, "
            "provider=$provider, model=$model, provider_request_id=$provider_request_id, "
            "usage=$usage",
            {
                "record_id": record_id, "fingerprint_id": fingerprint_id,
                "reference_work": reference_work, **fields,
            },
        )

    def get_reference_fingerprint_row(self, fingerprint_id: str) -> dict | None:
        rows = self._query(
            "SELECT fingerprint_id, reference_work_id, revision, source_hash, status, fingerprint, "
            "provider, model, provider_request_id, usage "
            "FROM reference_fingerprint WHERE fingerprint_id=$fingerprint_id LIMIT 1",
            {"fingerprint_id": fingerprint_id},
        ) or []
        return rows[0] if rows else None

    def list_reference_work_ids_for_work(self, work: str) -> list:
        return list(
            self._query(
                "SELECT VALUE reference_work_id FROM reference_work WHERE work=$work",
                {"work": work},
            )
            or []
        )

    def list_approved_fingerprints_for_ids(self, reference_ids: list) -> list[dict]:
        return list(
            self._query(
                "SELECT fingerprint_id, reference_work_id, revision, source_hash, status, fingerprint, "
                "provider, model, provider_request_id, usage "
                "FROM reference_fingerprint WHERE status='approved' "
                "AND reference_work_id IN $reference_ids ORDER BY revision DESC",
                {"reference_ids": list(reference_ids)},
            )
            or []
        )

    def list_reference_work_titles(self, work: str) -> list[dict]:
        return list(
            self._query(
                "SELECT reference_work_id, title FROM reference_work WHERE work=$work",
                {"work": work},
            )
            or []
        )

    def create_only_reference_craft_use(
        self, record_id: str, *, use_id: str, work: str, chapter: int,
        request_id: str, manifest_id: str, fingerprint_ids: list, mechanism_ids: list,
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('reference_craft_use',$record_id) SET "
            "use_id=$use_id, work=$work, chapter=$chapter, request_id=$request_id, "
            "manifest_id=$manifest_id, reference_fingerprint_ids=$fingerprint_ids, "
            "mechanism_ids=$mechanism_ids",
            {
                "record_id": record_id, "use_id": use_id, "work": work,
                "chapter": chapter, "request_id": request_id, "manifest_id": manifest_id,
                "fingerprint_ids": fingerprint_ids, "mechanism_ids": mechanism_ids,
            },
        )

    def get_reference_craft_use_row(self, record_id: str) -> dict | None:
        rows = self._query(
            "SELECT use_id, work, chapter, request_id, manifest_id, "
            "reference_fingerprint_ids, mechanism_ids "
            "FROM type::record('reference_craft_use',$record_id) LIMIT 1",
            {"record_id": record_id},
        ) or []
        return rows[0] if rows else None

    # ── snapshot ────────────────────────────────────────────
    def create_only_quality_snapshot(
        self, record_id: str, *, snapshot_id: str, work: str,
        snapshot_hash: str, member_count: int,
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('quality_snapshot',$record_id) SET "
            "snapshot_id=$snapshot_id, work=$work, snapshot_hash=$snapshot_hash, "
            "member_count=$member_count",
            {
                "record_id": record_id, "snapshot_id": snapshot_id, "work": work,
                "snapshot_hash": snapshot_hash, "member_count": member_count,
            },
        )

    def create_only_quality_snapshot_member(
        self, record_id: str, *, member_key: str, snapshot: Any,
        ordinal: int, chapter_version: Any, content_hash: str,
    ) -> None:
        self._execute_write(
            "CREATE ONLY type::record('quality_snapshot_member',$record_id) SET "
            "member_key=$member_key, snapshot=$snapshot, ordinal=$ordinal, "
            "chapter_version=$chapter_version, content_hash=$content_hash",
            {
                "record_id": record_id, "member_key": member_key, "snapshot": snapshot,
                "ordinal": ordinal, "chapter_version": chapter_version,
                "content_hash": content_hash,
            },
        )

    def bump_chapter_version_quality_ref(self, vid: str) -> None:
        self._execute_write(
            "UPDATE type::record('chapter_version',$vid) SET "
            "quality_snapshot_ref_count += 1",
            {"vid": vid},
        )

    def get_quality_snapshot_row(self, snapshot_id: str) -> dict | None:
        rows = self._query(
            "SELECT snapshot_id, work, snapshot_hash, member_count FROM quality_snapshot "
            "WHERE snapshot_id=$snapshot_id LIMIT 1",
            {"snapshot_id": snapshot_id},
        ) or []
        return rows[0] if rows else None

    def list_quality_snapshot_members(self, snapshot: Any) -> list[dict]:
        return list(
            self._query(
                "SELECT (IF chapter_version IS NONE THEN NONE ELSE <string>chapter_version END) "
                "AS chapter_version_id, content_hash, ordinal "
                "FROM quality_snapshot_member WHERE snapshot=$snapshot ORDER BY ordinal",
                {"snapshot": snapshot},
            )
            or []
        )

    def queue_quality_snapshot_guard(
        self, chapter_version: Any, content_hash: str,
    ) -> None:
        self._execute_write(
            "LET $current = (SELECT prose FROM $chapter_version); "
            "IF array::len($current) != 1 OR "
            "crypto::sha256($current[0].prose) != $content_hash "
            "{ THROW 'quality_snapshot_drift' }",
            {"chapter_version": chapter_version, "content_hash": content_hash},
        )

    # ── job ─────────────────────────────────────────────────
    def create_only_quality_job(self, params: dict) -> None:
        self._execute_write(
            "CREATE ONLY type::record('quality_job',$record_id) SET job_id=$job_id, "
            "idempotency_key=$idempotency_key, work=$work, snapshot=$snapshot, "
            "snapshot_id=$snapshot_id, contract_revision=$contract_revision_record, "
            "contract_id=$contract_id, contract_revision_number=$contract_revision, "
            "rubric_revision=$rubric_revision, "
            "reference_fingerprints=$reference_fingerprints, "
            "reference_fingerprint_ids=$reference_fingerprint_ids, "
            "model_config=$model_settings, "
            "actual_input_hash=$actual_input_hash, request_id=$request_id, "
            "manifest_id=$manifest_id, provider_request_id=$provider_request_id, "
            "provider_model=$provider_model, provider_usage=$provider_usage, "
            "execution_status='queued', execution_attempts=0, execution_error_code=NONE, "
            "execution_error_message=NONE, execution_started_at=NONE, execution_finished_at=NONE",
            params,
        )

    def get_quality_job_by_idempotency(self, idempotency_key: str) -> dict | None:
        rows = self._query(
            "SELECT job_id, idempotency_key, work, snapshot.snapshot_id AS snapshot_id, "
            "contract_revision.contract_id AS contract_id, "
            "contract_revision.revision AS contract_revision, rubric_revision, "
            "reference_fingerprints.fingerprint_id AS reference_fingerprint_ids, "
            "model_config AS model_settings, actual_input_hash, request_id, manifest_id, "
            "provider_request_id, provider_model, provider_usage FROM quality_job "
            "WHERE idempotency_key=$idempotency_key LIMIT 1",
            {"idempotency_key": idempotency_key},
        ) or []
        return rows[0] if rows else None

    def get_quality_job_idempotency_key(self, job_id: str) -> str | None:
        rows = self._query(
            "SELECT idempotency_key FROM quality_job WHERE job_id=$job_id LIMIT 1",
            {"job_id": job_id},
        ) or []
        if not rows:
            return None
        return rows[0].get("idempotency_key")

    def get_quality_job_status_row(self, job_id: str) -> dict | None:
        rows = self._query(
            "SELECT job_id, execution_status, execution_attempts, execution_error_code, "
            "execution_error_message, execution_started_at, execution_finished_at "
            "FROM quality_job WHERE job_id=$job_id LIMIT 1",
            {"job_id": job_id},
        ) or []
        return rows[0] if rows else None

    def start_quality_job(self, job_id: str, attempts: int) -> None:
        self._execute_write(
            "UPDATE type::record('quality_job',$job_id) SET execution_status='running', "
            "execution_attempts=$attempts, execution_error_code=NONE, execution_error_message=NONE, "
            "execution_started_at=time::now(), execution_finished_at=NONE",
            {"job_id": job_id, "attempts": attempts},
        )

    def count_quality_judgments_for_job(self, job: Any) -> int:
        rows = self._query(
            "SELECT count() AS count FROM quality_judgment WHERE job=$job GROUP ALL",
            {"job": job},
        ) or []
        return int((rows[0].get("count") if rows else 0) or 0)

    def finish_quality_job(self, job_id: str) -> None:
        self._execute_write(
            "UPDATE type::record('quality_job',$job_id) SET execution_status='completed', "
            "execution_error_code=NONE, execution_error_message=NONE, execution_finished_at=time::now()",
            {"job_id": job_id},
        )

    def fail_quality_job(
        self, job_id: str, *, status: str, error_code: str, error_message: str,
    ) -> None:
        self._execute_write(
            "UPDATE type::record('quality_job',$job_id) SET execution_status=$status, "
            "execution_error_code=$error_code, execution_error_message=$error_message, "
            "execution_finished_at=time::now()",
            {
                "job_id": job_id, "status": status,
                "error_code": str(error_code)[:80],
                "error_message": str(error_message)[:300],
            },
        )

    def recover_stale_quality_job(self, job_id: str, started_at: Any) -> None:
        self._execute_write(
            "UPDATE type::record('quality_job',$job_id) SET execution_status='retryable_failed', "
            "execution_error_code='worker_lost', "
            "execution_error_message='后台执行超过时限，已释放为可重试状态', "
            "execution_finished_at=time::now() "
            "WHERE execution_status='running' AND execution_started_at=$started_at",
            {"job_id": job_id, "started_at": started_at},
        )

    # ── judgments / verdicts ────────────────────────────────
    def get_context_outcome_for_judgment(self, outcome_id: str) -> dict | None:
        rows = self._query(
            "SELECT outcome_id, request_id, manifest_id, actual_input_hash, status, provider, "
            "model, provider_request_id, usage FROM context_outcome_trace "
            "WHERE outcome_id=$outcome_id LIMIT 1",
            {"outcome_id": outcome_id},
        ) or []
        return rows[0] if rows else None

    def create_only_quality_axis_judgment(
        self, table: str, record_id: str, fields: dict,
    ) -> None:
        if table not in ("quality_judgment", "quality_author_judgment"):
            raise ValueError(f"unsupported judgment table: {table}")
        if table == "quality_judgment":
            self._execute_write(
                "CREATE ONLY type::record('quality_judgment',$record_id) SET "
                "judgment_id=$judgment_id, job=$job, job_id=$job_id, unit=$unit, "
                "unit_id=$unit_id, dimension=$dimension, evaluator_kind=$evaluator_kind, "
                "payload=$payload, context_outcome=$context_outcome, "
                "outcome_id=$outcome_id, request_id=$request_id, manifest_id=$manifest_id, "
                "actual_input_hash=$actual_input_hash, provider=$provider, model=$model, "
                "provider_request_id=$provider_request_id, usage=$usage",
                {"record_id": record_id, **fields},
            )
        else:
            self._execute_write(
                "CREATE ONLY type::record('quality_author_judgment',$record_id) SET "
                "judgment_id=$judgment_id, job=$job, job_id=$job_id, unit=$unit, "
                "unit_id=$unit_id, dimension=$dimension, evaluator_kind='author', payload=$payload",
                {"record_id": record_id, **fields},
            )

    def create_only_quality_author_verdict(self, record_id: str, fields: dict) -> None:
        self._execute_write(
            "CREATE ONLY type::record('quality_author_verdict',$record_id) SET "
            "verdict_id=$verdict_id, job=$job, job_id=$job_id, unit=$unit, unit_id=$unit_id, "
            "dimension=$dimension, revision=$revision, decision=$decision, reason=$reason, "
            "payload=$payload",
            {"record_id": record_id, **fields},
        )

    def query_quality_author_verdicts(
        self, job: Any, unit: Any | None = None,
    ) -> list[dict]:
        query = (
            "SELECT verdict_id, job_id, unit_id, dimension, revision, decision, reason, payload "
            "FROM quality_author_verdict WHERE job=$job"
        )
        params: dict[str, Any] = {"job": job}
        if unit is not None:
            query += " AND unit=$unit"
            params["unit"] = unit
        query += " ORDER BY dimension, revision DESC"
        return list(self._query(query, params) or [])

    def query_quality_axis_rows(
        self, table: str, job: Any, unit: Any | None = None,
    ) -> list[dict]:
        if table not in ("quality_judgment", "quality_author_judgment"):
            raise ValueError(f"unsupported judgment table: {table}")
        query = (
            f"SELECT payload, outcome_id, request_id, manifest_id, actual_input_hash, "
            f"provider, model, provider_request_id, usage, dimension, evaluator_kind "
            f"FROM {table} WHERE job=$job"
        )
        params: dict[str, Any] = {"job": job}
        if unit is not None:
            query += " AND unit=$unit"
            params["unit"] = unit
        query += " ORDER BY dimension, evaluator_kind"
        return list(self._query(query, params) or [])

    def query_quality_author_judgment_payloads(
        self, job: Any, unit: Any | None = None,
    ) -> list[dict]:
        query = "SELECT payload, dimension FROM quality_author_judgment WHERE job=$job"
        params: dict[str, Any] = {"job": job}
        if unit is not None:
            query += " AND unit=$unit"
            params["unit"] = unit
        query += " ORDER BY dimension"
        return list(self._query(query, params) or [])

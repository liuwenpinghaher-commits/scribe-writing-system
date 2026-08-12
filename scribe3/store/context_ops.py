"""SurrealStore mixin: Creative Context OS tables (ContextStore adapter)."""
from __future__ import annotations

from typing import Any


class ContextOpsMixin:
    """context_policy_snapshot / context_manifest / context_outcome_trace 公开读写。"""

    def create_only_context_policy_snapshot(self, snapshot_id: str, fields: dict[str, Any]) -> None:
        self._execute_write(
            "CREATE ONLY type::record('context_policy_snapshot', $snapshot_id) "
            "SET policy_snapshot_id=$snapshot_id, policy_key=$policy_key, "
            "policy_version=$policy_version, schema_hash=$schema_hash, payload=$payload",
            {"snapshot_id": snapshot_id, **fields},
        )

    def get_context_policy_snapshot_row(self, snapshot_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT policy_snapshot_id, policy_key, policy_version, schema_hash, payload "
            "FROM type::record('context_policy_snapshot', $snapshot_id)",
            {"snapshot_id": snapshot_id},
        ) or []
        return rows[0] if rows else None

    def create_only_context_manifest(self, manifest_id: str, payload: dict[str, Any]) -> None:
        self._execute_write(
            "CREATE ONLY type::record('context_manifest', $manifest_id) SET "
            "manifest_id=$manifest_id, manifest_version=$manifest_version, "
            "request_id=$request_id, task_kind=$task_kind, policy_key=$policy_key, "
            "policy_version=$policy_version, policy_schema_hash=$policy_schema_hash, "
            "navigation_snapshot_id=$navigation_snapshot_id, snapshot_hash=$snapshot_hash, "
            "envelope_hash=$envelope_hash, actual_input_hash=$actual_input_hash, "
            "actual_input_bytes=$actual_input_bytes, manifest_hash=$manifest_hash",
            {"manifest_id": manifest_id, **payload},
        )

    def create_only_context_manifest_source(self, record_id: str, fields: dict[str, Any]) -> None:
        self._execute_write(
            "CREATE ONLY type::record('context_manifest_source', $record_id) SET "
            "manifest_id=$manifest_id, source_ref=$source_ref, block=$block, "
            "source_id=$source_id, source_kind=$source_kind, work=$work, "
            "revision=$revision, included=$included, masked=$masked, "
            "reason_code=$reason_code, content_digest=$content_digest",
            {"record_id": record_id, **fields},
        )

    def get_context_manifest_row(self, manifest_id: str) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT manifest_version, request_id, task_kind, policy_key, policy_version, "
            "policy_schema_hash, "
            "navigation_snapshot_id, snapshot_hash, envelope_hash, actual_input_hash, "
            "actual_input_bytes, manifest_hash FROM context_manifest "
            "WHERE manifest_id=$manifest_id LIMIT 1",
            {"manifest_id": manifest_id},
        ) or []
        return rows[0] if rows else None

    def list_context_manifest_sources(self, manifest_id: str) -> list[dict[str, Any]]:
        return list(
            self._query(
                "SELECT source_ref, block, source_id, source_kind, work, revision, included, "
                "masked, reason_code, "
                "content_digest FROM context_manifest_source WHERE manifest_id=$manifest_id "
                "ORDER BY source_ref ASC",
                {"manifest_id": manifest_id},
            )
            or []
        )

    def create_only_context_outcome(self, payload: dict[str, Any]) -> None:
        self._execute_write(
            "CREATE ONLY type::record('context_outcome_trace', $outcome_id) SET "
            "outcome_id=$outcome_id, request_id=$request_id, manifest_id=$manifest_id, "
            "actual_input_hash=$actual_input_hash, status=$status, provider=$provider, "
            "model=$model, provider_request_id=$provider_request_id, "
            "transport_provider=$transport_provider, "
            "transport_request_id=$transport_request_id, "
            "reasoning_provider=$reasoning_provider, reasoning_model=$reasoning_model, "
            "reasoning_request_id=$reasoning_request_id, usage=$usage, "
            "output_hash=$output_hash, error=$error, created_at=type::datetime($created_at)",
            payload,
        )

    def get_context_outcome_row(
        self, request_id: str, manifest_id: str, actual_input_hash: str
    ) -> dict[str, Any] | None:
        rows = self._query(
            "SELECT outcome_id, request_id, manifest_id, actual_input_hash, status, provider, "
            "model, provider_request_id, transport_provider, transport_request_id, "
            "reasoning_provider, reasoning_model, reasoning_request_id, "
            "usage, output_hash, error, "
            "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at "
            "FROM context_outcome_trace "
            "WHERE request_id=$request_id AND manifest_id=$manifest_id "
            "AND actual_input_hash=$actual_input_hash LIMIT 1",
            {
                "request_id": request_id,
                "manifest_id": manifest_id,
                "actual_input_hash": actual_input_hash,
            },
        ) or []
        return rows[0] if rows else None

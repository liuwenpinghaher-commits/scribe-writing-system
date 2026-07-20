"""Creative Context OS 的 SurrealDB 窄存储适配器。"""
from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

from scribe3.context_manifest import ContextManifest, ContextManifestSource
from scribe3.context_outcome import ContextOutcomeTrace
from scribe3.store import _redact_run_trace_secrets

if TYPE_CHECKING:
    from scribe3.store import SurrealStore


class ContextStore:
    """只包装调用方注入的 ``SurrealStore``，不拥有连接或业务正文。"""

    def __init__(self, store: "SurrealStore"):
        self._store = store

    @staticmethod
    def _policy_snapshot_id(policy_version: str) -> str:
        return sha256(policy_version.encode("utf-8")).hexdigest()

    @staticmethod
    def _source_ref(manifest_id: str, ordinal: int) -> str:
        return f"{manifest_id}:{ordinal:06d}"

    @staticmethod
    def _source_record_id(source_ref: str) -> str:
        return sha256(source_ref.encode("utf-8")).hexdigest()

    def save_manifest(self, manifest: ContextManifest) -> ContextManifest:
        """同一 Manifest 重放幂等；主记录、策略版本和全部来源同事务创建。"""
        manifest_id = manifest.manifest_hash
        existing = self.get_manifest(manifest_id)
        if existing is not None:
            if existing != manifest:
                raise ValueError(f"manifest_id '{manifest_id}' 与既有当前真相冲突")
            return existing

        policy_snapshot_id = self._policy_snapshot_id(manifest.policy_version)
        payload = manifest.model_dump(mode="json")
        policy_exists = bool(self._store._query(
            "SELECT policy_snapshot_id FROM context_policy_snapshot "
            "WHERE policy_snapshot_id=$policy_snapshot_id LIMIT 1",
            {"policy_snapshot_id": policy_snapshot_id},
        ))
        with self._store.transaction():
            if not policy_exists:
                self._store._execute_write(
                    "CREATE type::record('context_policy_snapshot', $policy_snapshot_id) "
                    "SET policy_snapshot_id=$policy_snapshot_id, policy_version=$policy_version",
                    {"policy_snapshot_id": policy_snapshot_id,
                     "policy_version": manifest.policy_version},
                )
            self._store._execute_write(
                "CREATE type::record('context_manifest', $manifest_id) SET "
                "manifest_id=$manifest_id, manifest_version=$manifest_version, "
                "request_id=$request_id, task_kind=$task_kind, policy_version=$policy_version, "
                "navigation_snapshot_id=$navigation_snapshot_id, snapshot_hash=$snapshot_hash, "
                "envelope_hash=$envelope_hash, actual_input_hash=$actual_input_hash, "
                "actual_input_bytes=$actual_input_bytes, manifest_hash=$manifest_hash",
                {"manifest_id": manifest_id, **payload},
            )
            for ordinal, source in enumerate(manifest.sources):
                source_ref = self._source_ref(manifest_id, ordinal)
                self._store._execute_write(
                    "CREATE type::record('context_manifest_source', $record_id) SET "
                    "manifest_id=$manifest_id, source_ref=$source_ref, block=$block, "
                    "source_id=$source_id, source_kind=$source_kind, work=$work, "
                    "revision=$revision, masked=$masked, reason_code=$reason_code, "
                    "content_digest=$content_digest",
                    {"record_id": self._source_record_id(source_ref),
                     "manifest_id": manifest_id, "source_ref": source_ref,
                     **source.model_dump(mode="json")},
                )
        return manifest

    def get_manifest(self, manifest_id: str) -> ContextManifest | None:
        """按不可变 manifest id 读回，不返回任何提示词正文。"""
        rows = self._store._query(
            "SELECT manifest_version, request_id, task_kind, policy_version, "
            "navigation_snapshot_id, snapshot_hash, envelope_hash, actual_input_hash, "
            "actual_input_bytes, manifest_hash FROM context_manifest "
            "WHERE manifest_id=$manifest_id LIMIT 1",
            {"manifest_id": manifest_id},
        )
        if not rows:
            return None
        sources = self._store._query(
            "SELECT source_ref, block, source_id, source_kind, work, revision, masked, reason_code, "
            "content_digest FROM context_manifest_source WHERE manifest_id=$manifest_id "
            "ORDER BY source_ref ASC",
            {"manifest_id": manifest_id},
        )
        return ContextManifest.model_validate({
            **rows[0],
            "sources": tuple(ContextManifestSource.model_validate(source) for source in sources),
        })

    def save_outcome(self, outcome: ContextOutcomeTrace) -> ContextOutcomeTrace:
        """Outcome 必须精确绑定已存 Manifest 的 request/id/input-hash 三元组。"""
        manifest = self.get_manifest(outcome.manifest_id)
        if manifest is None or (
            manifest.request_id,
            manifest.manifest_hash,
            manifest.actual_input_hash,
        ) != (
            outcome.request_id,
            outcome.manifest_id,
            outcome.actual_input_hash,
        ):
            raise ValueError("Outcome 三元组未绑定到既有 Manifest")

        # Outcome error 是不可信上游文本：先查本库权威 secret 值，再用 ai_run_trace
        # 同一 redactor 清除认证头/cookie/api_key 与故事秘密。查询失败必须向上抛，不能
        # 以空集合降级到 fail-open；任何 DB 写入都发生在这一步之后。
        secret_values = self._store._secret_proposition_values()
        persisted = outcome.model_copy(update={
            "error": _redact_run_trace_secrets(outcome.error, secret_values),
        })
        existing = self.get_outcome(
            persisted.request_id, persisted.manifest_id, persisted.actual_input_hash)
        if existing is not None:
            if existing.model_dump(exclude={"created_at"}) != persisted.model_dump(
                exclude={"created_at"}
            ):
                raise ValueError("Outcome 三元组与既有当前真相冲突")
            return existing
        payload = persisted.model_dump(mode="json")
        with self._store.transaction():
            self._store._execute_write(
                "CREATE type::record('context_outcome_trace', $outcome_id) SET "
                "outcome_id=$outcome_id, request_id=$request_id, manifest_id=$manifest_id, "
                "actual_input_hash=$actual_input_hash, status=$status, provider=$provider, "
                "model=$model, provider_request_id=$provider_request_id, usage=$usage, "
                "output_hash=$output_hash, error=$error, created_at=type::datetime($created_at)",
                payload,
            )
        return persisted

    def get_outcome(self, request_id: str, manifest_id: str,
                    actual_input_hash: str) -> ContextOutcomeTrace | None:
        """以三元组定位 Outcome，防止把相同 request 的不同实际输入混读。"""
        rows = self._store._query(
            "SELECT outcome_id, request_id, manifest_id, actual_input_hash, status, provider, "
            "model, provider_request_id, usage, output_hash, error, "
            "<string> created_at AS created_at FROM context_outcome_trace "
            "WHERE request_id=$request_id AND manifest_id=$manifest_id "
            "AND actual_input_hash=$actual_input_hash LIMIT 1",
            {"request_id": request_id, "manifest_id": manifest_id,
             "actual_input_hash": actual_input_hash},
        )
        return ContextOutcomeTrace.model_validate(rows[0]) if rows else None

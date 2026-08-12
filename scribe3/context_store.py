"""Creative Context OS 的 SurrealDB 窄存储适配器。"""
from __future__ import annotations

from hashlib import sha256
import json
import time
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
    def _policy_snapshot_id(policy_version: str, policy_key: str | None = None) -> str:
        # 091 已发布的稳定 ID 是 sha256(policy_version)，且同时建了
        # policy_version UNIQUE 索引。保持该 ID 才能让 093 回填后的首次新写
        # 复用旧行；policy_key/schema_hash/payload 仍会逐字段比较防漂移。
        return sha256(policy_version.encode("utf-8")).hexdigest()

    @staticmethod
    def _source_ref(manifest_id: str, ordinal: int) -> str:
        return f"{manifest_id}:{ordinal:06d}"

    @staticmethod
    def _source_record_id(source_ref: str) -> str:
        return sha256(source_ref.encode("utf-8")).hexdigest()

    @staticmethod
    def _retry_read(loader, attempts: int = 4):
        for attempt in range(attempts):
            value = loader()
            if value is not None:
                return value
            if attempt + 1 < attempts:
                time.sleep(0.01 * (attempt + 1))
        return None

    def _ensure_policy_snapshot(self, manifest: ContextManifest) -> None:
        from scribe3.context_policy import ContextPolicy

        policy = ContextPolicy.by_version(manifest.policy_version)
        if (
            manifest.policy_key != policy.policy_key
            or manifest.policy_schema_hash != policy.schema_hash
        ):
            raise ValueError("Manifest 的 Policy 绑定与注册表当前真相不一致")
        snapshot_id = self._policy_snapshot_id(policy.version, policy.policy_key)
        expected = {
            "policy_snapshot_id": snapshot_id,
            "policy_key": policy.policy_key,
            "policy_version": policy.version,
            "schema_hash": policy.schema_hash,
            "payload": policy.safe_payload(),
        }
        try:
            self._store.create_only_context_policy_snapshot(snapshot_id, expected)
            return
        except Exception as conflict:
            existing = self._retry_read(lambda: self._policy_snapshot(snapshot_id))
            if existing is None:
                raise conflict
            if existing != expected:
                raise ValueError(
                    "policy snapshot 同 key/version 与既有安全 schema 冲突"
                ) from conflict

    def _policy_snapshot(self, snapshot_id: str) -> dict | None:
        return self._store.get_context_policy_snapshot_row(snapshot_id)

    def save_manifest(self, manifest: ContextManifest) -> ContextManifest:
        """原子创建；唯一冲突后有限读回，同内容幂等、异内容显式失败。"""
        manifest.verify_hash()
        manifest_id = manifest.manifest_hash
        self._ensure_policy_snapshot(manifest)
        payload = manifest.model_dump(mode="json")
        try:
            with self._store.transaction():
                self._store.create_only_context_manifest(manifest_id, payload)
                for ordinal, source in enumerate(manifest.sources):
                    source_ref = self._source_ref(manifest_id, ordinal)
                    self._store.create_only_context_manifest_source(
                        self._source_record_id(source_ref),
                        {
                            "manifest_id": manifest_id,
                            "source_ref": source_ref,
                            **source.model_dump(mode="json"),
                        },
                    )
        except Exception as conflict:
            existing = self._retry_read(lambda: self.get_manifest(manifest_id))
            if existing is None:
                raise conflict
            if existing != manifest:
                raise ValueError(
                    f"manifest_id '{manifest_id}' 与既有当前真相冲突"
                ) from conflict
            return existing
        return manifest

    def get_manifest(self, manifest_id: str) -> ContextManifest | None:
        """按不可变 manifest id 读回，不返回任何提示词正文。"""
        row = self._store.get_context_manifest_row(manifest_id)
        if not row:
            return None
        sources = self._store.list_context_manifest_sources(manifest_id)
        return ContextManifest.model_validate({
            **row,
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
        redacted_error = _redact_run_trace_secrets(outcome.error, secret_values)
        if redacted_error is not None and not isinstance(redacted_error, str):
            redacted_error = json.dumps(
                redacted_error, ensure_ascii=False, sort_keys=True,
            )
        if isinstance(redacted_error, str):
            # 截断必须发生在完整递归脱敏之后，避免把 token/秘密截成
            # 新的、无法被正则识别的明文片段。
            redacted_error = redacted_error[:500]
        persisted = outcome.model_copy(update={
            "error": redacted_error,
        })
        payload = persisted.model_dump(mode="json")
        try:
            with self._store.transaction():
                self._store.create_only_context_outcome(payload)
        except Exception as conflict:
            existing = self._retry_read(lambda: self.get_outcome(
                persisted.request_id, persisted.manifest_id,
                persisted.actual_input_hash,
            ))
            if existing is None:
                raise conflict
            if existing.model_dump(exclude={"created_at"}) != persisted.model_dump(
                exclude={"created_at"}
            ):
                raise ValueError("Outcome 三元组与既有当前真相冲突") from conflict
            return existing
        return persisted

    def get_outcome(self, request_id: str, manifest_id: str,
                    actual_input_hash: str) -> ContextOutcomeTrace | None:
        """以三元组定位 Outcome，防止把相同 request 的不同实际输入混读。"""
        row = self._store.get_context_outcome_row(
            request_id, manifest_id, actual_input_hash,
        )
        return ContextOutcomeTrace.model_validate(row) if row else None

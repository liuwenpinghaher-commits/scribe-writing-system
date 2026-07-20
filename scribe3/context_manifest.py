"""不含正文的 Creative Context 输入清单。"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

from scribe3.context_models import ContextEnvelope, ContextRequest, ContextSource
from scribe3.context_policy import ContextPolicy


class ContextManifestSource(BaseModel):
    """一个已选入来源的可审计摘要；刻意没有正文 text 字段。"""

    model_config = ConfigDict(frozen=True)

    block: str
    source_id: str
    source_kind: str
    work: str
    revision: str | None = None
    masked: bool = False
    reason_code: Literal[
        "unspecified", "secret_masked", "borrow_not_fact", "superseded_by_canonical",
    ] = "unspecified"
    content_digest: str

    @classmethod
    def from_source(cls, block: str, source: ContextSource) -> "ContextManifestSource":
        if not source.content_digest:
            raise ValueError(f"选入来源缺少 content_digest: {source.source_id}")
        return cls(
            block=block,
            source_id=source.source_id,
            source_kind=source.source_kind,
            work=source.work,
            revision=source.revision,
            masked=source.masked,
            reason_code=_reason_code(source.reason),
            content_digest=source.content_digest,
        )


class ContextManifest(BaseModel):
    """不可变的输入配方与实际 UTF-8 输入指纹，永不携带提示词正文。"""

    model_config = ConfigDict(frozen=True)

    manifest_version: str = "creative-context-manifest.v1"
    request_id: str
    task_kind: str
    policy_version: str
    navigation_snapshot_id: str
    snapshot_hash: str
    envelope_hash: str
    sources: tuple[ContextManifestSource, ...]
    actual_input_hash: str
    actual_input_bytes: int
    manifest_hash: str


def _input_bytes(rendered_input: str | bytes) -> bytes:
    if isinstance(rendered_input, str):
        return rendered_input.encode("utf-8")
    if isinstance(rendered_input, bytes):
        try:
            rendered_input.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("rendered_input bytes 必须是有效 UTF-8") from exc
        return rendered_input
    raise TypeError("rendered_input 必须是 str 或 UTF-8 bytes")


def _manifest_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reason_code(reason: str) -> Literal[
    "unspecified", "secret_masked", "borrow_not_fact", "superseded_by_canonical",
]:
    """将来源自由说明降为允许公开的稳定审计码。"""
    known = {"secret_masked", "borrow_not_fact", "superseded_by_canonical"}
    return reason if reason in known else "unspecified"


def build_context_manifest(
    request: ContextRequest,
    policy: ContextPolicy,
    envelope: ContextEnvelope,
    rendered_input: str | bytes,
) -> ContextManifest:
    """从已组装 envelope 与最终输入字节构建不含正文的 immutable manifest。"""
    resolved = ContextPolicy.for_task(request.task_kind)
    if policy != resolved or request.policy_version != resolved.version:
        raise ValueError("请求任务类型与策略版本不匹配")
    # 注册表对象是唯一策略权威；绝不让同 version 的调用方对象替代其裁决。
    resolved.validate_envelope(envelope)

    sources = tuple(
        ContextManifestSource.from_source(block.name, source)
        for block in envelope.blocks
        for source in block.sources
    )
    actual = _input_bytes(rendered_input)
    actual_hash = hashlib.sha256(actual).hexdigest()
    payload = {
        "manifest_version": "creative-context-manifest.v1",
        "request_id": request.request_id,
        "task_kind": request.task_kind,
        "policy_version": policy.version,
        "navigation_snapshot_id": request.navigation_snapshot_id,
        "snapshot_hash": envelope.snapshot.context_hash,
        "envelope_hash": envelope.envelope_hash,
        "sources": [source.model_dump(mode="json") for source in sources],
        "actual_input_hash": actual_hash,
        "actual_input_bytes": len(actual),
    }
    return ContextManifest(**payload, manifest_hash=_manifest_hash(payload))

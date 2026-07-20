"""参考作品导入与分层指纹生成服务。"""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, TYPE_CHECKING

from scribe3.material_import import parse_to_markdown
from scribe3.quality.store import (
    QualityStore,
    ReferenceFingerprintRecord,
    ReferenceWorkRecord,
)

if TYPE_CHECKING:
    from scribe3.store import SurrealStore

_FINGERPRINT_REQUIRED_FIELDS = (
    "local_mechanisms",
    "cross_chapter_aggregation",
    "full_book_fingerprint",
    "evidence",
    "counter_evidence",
    "transferable_mechanisms",
    "non_copyable_elements",
    "applicable_scope",
)


class ReferenceService:
    def __init__(self, store: "SurrealStore"):
        self._store = store
        self._quality = QualityStore(store)

    def import_reference(
        self,
        *,
        work: str,
        title: str,
        text: str | None = None,
        file_src: str | None = None,
        converter=None,
    ) -> ReferenceWorkRecord:
        if text is None and file_src is None:
            raise ValueError("必须提供 text 或 file_src")
        if text is None:
            text = parse_to_markdown(file_src, converter=converter)
        source_hash = sha256(text.encode("utf-8")).hexdigest()
        record = ReferenceWorkRecord(
            reference_work_id=sha256(f"{work}:{title}:{source_hash}".encode()).hexdigest()[:24],
            work=work,
            title=title,
            source_hash=source_hash,
            import_revision=1,
            status="imported",
        )
        return self._quality.save_reference_work(record)

    def generate_fingerprint(
        self,
        *,
        reference_work_id: str,
        llm,
    ) -> ReferenceFingerprintRecord:
        works = self._store._query(
            "SELECT id, reference_work_id, source_hash, import_revision "
            "FROM reference_work WHERE reference_work_id=$rid "
            "ORDER BY import_revision DESC LIMIT 1",
            {"rid": reference_work_id},
        )
        if not works:
            raise ValueError(f"参考作品不存在: {reference_work_id}")
        work_row = works[0]

        ref_text = self._get_reference_text(reference_work_id)

        messages = [
            {"role": "system", "content": (
                "你是一位文学分析专家。分析以下参考作品，返回 JSON 对象，包含：\n"
                "- local_mechanisms: 局部机制数组\n"
                "- cross_chapter_aggregation: 跨章聚合描述\n"
                "- full_book_fingerprint: 全书指纹描述\n"
                "- evidence: 证据数组 [{quote, location}]\n"
                "- counter_evidence: 反证数组 [{quote, location}]\n"
                "- transferable_mechanisms: 可迁移机制数组\n"
                "- non_copyable_elements: 不可复制要素数组\n"
                "- applicable_scope: 适用范围\n"
                "只返回 JSON，不要其他文字。"
            )},
            {"role": "user", "content": ref_text[:12000]},
        ]
        result = llm.complete(messages)
        content = (result.content or "").strip()
        if not content:
            raise ValueError("LLM 返回空响应，无法生成指纹")

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            payload = json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"LLM 响应不是有效 JSON: {exc}") from exc

        missing = [f for f in _FINGERPRINT_REQUIRED_FIELDS if f not in payload]
        if missing:
            raise ValueError(f"指纹 JSON 缺少必需字段: {', '.join(missing)}")

        record = ReferenceFingerprintRecord(
            reference_work_id=reference_work_id,
            revision=1,
            source_hash=work_row["source_hash"],
            status="pending_review",
            fingerprint=payload,
        )
        return self._quality.save_reference_fingerprint(record)

    def approve_fingerprint(
        self,
        *,
        fingerprint_id: str,
        corrections: dict[str, Any] | None = None,
    ) -> ReferenceFingerprintRecord:
        existing = self._quality._get_fingerprint(fingerprint_id)
        if existing is None:
            raise ValueError(f"指纹不存在: {fingerprint_id}")
        final_payload = corrections if corrections is not None else dict(existing.fingerprint)
        new_record = ReferenceFingerprintRecord(
            reference_work_id=existing.reference_work_id,
            revision=existing.revision + 1,
            source_hash=existing.source_hash,
            status="approved",
            fingerprint=final_payload,
        )
        return self._quality.save_reference_fingerprint(new_record)

    def _get_reference_text(self, reference_work_id: str) -> str:
        rows = self._store._query(
            "SELECT title, source_hash, import_revision FROM reference_work "
            "WHERE reference_work_id=$rid ORDER BY import_revision DESC LIMIT 1",
            {"rid": reference_work_id},
        )
        if not rows:
            return ""
        return f"参考作品: {rows[0].get('title', '')}\n\n(正文按 source_hash 绑定)"

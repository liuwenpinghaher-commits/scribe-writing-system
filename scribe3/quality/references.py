"""参考作品导入与分层指纹生成服务。"""
from __future__ import annotations

import json
from hashlib import sha256
from numbers import Real
from typing import Any, Mapping, TYPE_CHECKING

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

# TokenPlan 的 qwen3.8-max-preview 会进行强制思考，指纹生成不能继承普通写作
# 路径的 600 秒超时、3 次重试与无输出上限。显式 JSON 模式与该受限预算让一次
# 失败在可解释的时间内返回给作者；不发送 thinking=disabled（该模型会拒绝它）。
FINGERPRINT_MAX_TOKENS = 1200
FINGERPRINT_TIMEOUT_SECONDS = 120
FINGERPRINT_RETRY_COUNT = 1


def _observed_provider_metadata(result: Any) -> dict[str, Any]:
    """提取真实补全回执；不从配置、默认值或伪造 fake 推导任何审计字段。"""
    identity = getattr(result, "identity", None)
    provider = getattr(identity, "provider", None)
    model = getattr(result, "model", None)
    response_id = getattr(result, "response_id", None)
    raw_usage = getattr(result, "usage", None)
    usage = {
        str(key): value
        for key, value in raw_usage.items()
        if isinstance(key, str) and isinstance(value, Real) and not isinstance(value, bool)
    } if isinstance(raw_usage, Mapping) else None
    return {
        "provider": provider.strip() if isinstance(provider, str) and provider.strip() else None,
        "model": model.strip() if isinstance(model, str) and model.strip() else None,
        "provider_request_id": (
            response_id.strip() if isinstance(response_id, str) and response_id.strip() else None
        ),
        "usage": usage or None,
    }


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
        return self._quality.save_reference_work(record, source_text=text)

    def list_references(self, *, work: str) -> tuple[ReferenceWorkRecord, ...]:
        """仅返回当前作品的可展示元数据；参考原文不离开服务层。"""
        rows = self._store._query(
            "SELECT reference_work_id, work, title, source_hash, import_revision, status "
            "FROM reference_work WHERE work=$work ORDER BY import_revision DESC",
            {"work": work},
        )
        return tuple(ReferenceWorkRecord.model_validate(row) for row in rows)

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
        result = llm.complete(
            messages,
            max_tokens=FINGERPRINT_MAX_TOKENS,
            timeout_seconds=FINGERPRINT_TIMEOUT_SECONDS,
            retry_count=FINGERPRINT_RETRY_COUNT,
            response_format={"type": "json_object"},
            hard_deadline=True,
        )
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
            **_observed_provider_metadata(result),
        )
        return self._quality.save_reference_fingerprint(record)

    def approve_fingerprint(
        self,
        *,
        fingerprint_id: str,
        corrections: dict[str, Any] | None = None,
        expected_reference_work_id: str | None = None,
    ) -> ReferenceFingerprintRecord:
        existing = self._quality._get_fingerprint(fingerprint_id)
        if existing is None:
            raise ValueError(f"指纹不存在: {fingerprint_id}")
        if (expected_reference_work_id is not None
                and existing.reference_work_id != expected_reference_work_id):
            raise ValueError("指纹不属于该参考作品")
        final_payload = corrections if corrections is not None else dict(existing.fingerprint)
        new_record = ReferenceFingerprintRecord(
            reference_work_id=existing.reference_work_id,
            revision=existing.revision + 1,
            source_hash=existing.source_hash,
            status="approved",
            fingerprint=final_payload,
            provider=existing.provider,
            model=existing.model,
            provider_request_id=existing.provider_request_id,
            usage=existing.usage,
        )
        return self._quality.save_reference_fingerprint(new_record)

    def _get_reference_text(self, reference_work_id: str) -> str:
        rows = self._store._query(
            "SELECT source_text, import_revision FROM reference_work "
            "WHERE reference_work_id=$rid ORDER BY import_revision DESC LIMIT 1",
            {"rid": reference_work_id},
        )
        if not rows:
            return ""
        source_text = (rows[0].get("source_text") or "").strip()
        if not source_text:
            raise ValueError("参考作品原文缺失；请重新导入同一文本以补齐指纹输入")
        return source_text

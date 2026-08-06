"""参考作品（技法标尺）导入与分层指纹生成服务。"""
from __future__ import annotations

import json
from hashlib import sha256
from numbers import Real
from typing import Any, Mapping, TYPE_CHECKING

from scribe3.material_import import parse_to_markdown
from scribe3.quality.segments import (
    PASTE_MAX_CHARS,
    SEGMENT_TARGET_CHARS,
    ReferenceSegment,
    segment_reference_text,
    total_chars,
)
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
MAP_MAX_TOKENS = 600


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


def _llm_complete_kwargs(*, max_tokens: int = FINGERPRINT_MAX_TOKENS) -> dict[str, Any]:
    return {
        "max_tokens": max_tokens,
        "timeout_seconds": FINGERPRINT_TIMEOUT_SECONDS,
        "retry_count": FINGERPRINT_RETRY_COUNT,
        "response_format": {"type": "json_object"},
        "hard_deadline": True,
    }


def _parse_json_object(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("LLM 返回空响应，无法生成指纹")
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            raise ValueError("no object")
        payload = json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"LLM 响应不是有效 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("指纹 JSON 必须是对象")
    return payload


def _merge_list_field(maps: list[dict[str, Any]], key: str) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for item in maps:
        for value in item.get(key) or []:
            token = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
            if token in seen:
                continue
            seen.add(token)
            out.append(value)
    return out


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
        paste: bool = False,
    ) -> ReferenceWorkRecord:
        if text is None and file_src is None:
            raise ValueError("必须提供 text 或 file_src")
        if text is None:
            text = parse_to_markdown(file_src, converter=converter)
        text = (text or "").strip()
        if not text:
            raise ValueError("导入内容为空")
        if paste and len(text) > PASTE_MAX_CHARS:
            raise ValueError(
                f"粘贴路径最长 {PASTE_MAX_CHARS} 字符；整书请使用文件上传（技法标尺导入）"
            )
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

    def list_approved_fingerprints_for_ui(self, *, work: str) -> list[dict[str, Any]]:
        """质量评价/契约选择器用：已批准指纹 + 标题预览，不含原文。"""
        records = self._quality.approved_reference_fingerprints(work)
        titles = self._quality.reference_titles(work)
        rows: list[dict[str, Any]] = []
        for record in records:
            mechanisms = record.fingerprint.get("transferable_mechanisms") or []
            preview = [
                str(m).strip() for m in mechanisms
                if isinstance(m, str) and str(m).strip()
            ][:6]
            rows.append({
                "fingerprint_id": record.fingerprint_id,
                "reference_work_id": record.reference_work_id,
                "title": titles.get(record.reference_work_id, ""),
                "revision": record.revision,
                "status": record.status,
                "transferable_mechanisms_preview": preview,
                "full_book_fingerprint": (
                    str(record.fingerprint.get("full_book_fingerprint") or "")[:200]
                ),
            })
        return rows

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
        segments = segment_reference_text(ref_text, target_chars=SEGMENT_TARGET_CHARS)
        if not segments:
            raise ValueError("参考作品原文为空，无法生成指纹")

        map_payloads, meta = self._map_segments(llm, segments)
        payload = self._reduce_fingerprint(llm, map_payloads, segments, meta)
        missing = [f for f in _FINGERPRINT_REQUIRED_FIELDS if f not in payload]
        if missing:
            raise ValueError(f"指纹 JSON 缺少必需字段: {', '.join(missing)}")

        # 分析元数据进入 fingerprint 对象，供 UI/测试证明多段覆盖；不替代必填字段。
        payload = dict(payload)
        payload["analysis_meta"] = meta

        record = ReferenceFingerprintRecord(
            reference_work_id=reference_work_id,
            revision=1,
            source_hash=work_row["source_hash"],
            status="pending_review",
            fingerprint=payload,
            **meta.get("provider_metadata") or {},
        )
        return self._quality.save_reference_fingerprint(record)

    def _map_segments(
        self, llm, segments: tuple[ReferenceSegment, ...],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        map_payloads: list[dict[str, Any]] = []
        provider_metadata: dict[str, Any] = {}
        for segment in segments:
            messages = [
                {"role": "system", "content": (
                    "你是文学技法分析专家。只分析给定片段，返回 JSON 对象，包含：\n"
                    "- local_mechanisms: 本段可观察的局部机制字符串数组\n"
                    "- evidence: [{quote, location}] 短引文与位置\n"
                    "- counter_evidence: [{quote, location}]\n"
                    "不要输出全书结论。只返回 JSON。"
                )},
                {"role": "user", "content": (
                    f"片段序号 {segment.index + 1}/{len(segments)} "
                    f"(digest={segment.digest}):\n\n{segment.text}"
                )},
            ]
            result = llm.complete(messages, **_llm_complete_kwargs(max_tokens=MAP_MAX_TOKENS))
            if not provider_metadata:
                provider_metadata = _observed_provider_metadata(result)
            try:
                mapped = _parse_json_object(result.content or "")
            except ValueError:
                mapped = {
                    "local_mechanisms": [],
                    "evidence": [],
                    "counter_evidence": [],
                    "map_error": True,
                }
            mapped["_segment_index"] = segment.index
            mapped["_segment_digest"] = segment.digest
            map_payloads.append(mapped)

        meta = {
            "pipeline": "map_reduce",
            "segment_count": len(segments),
            "segment_digests": [s.digest for s in segments],
            "chars_analyzed": total_chars(segments),
            "map_calls": len(map_payloads),
            "provider_metadata": provider_metadata,
        }
        return map_payloads, meta

    def _reduce_fingerprint(
        self,
        llm,
        map_payloads: list[dict[str, Any]],
        segments: tuple[ReferenceSegment, ...],
        meta: dict[str, Any],
    ) -> dict[str, Any]:
        # 单段且较短：仍走 reduce，但把 map 结果 + 全文交给 reduce，避免双次丢信息。
        local_mechs = _merge_list_field(map_payloads, "local_mechanisms")
        evidence = _merge_list_field(map_payloads, "evidence")
        counter = _merge_list_field(map_payloads, "counter_evidence")
        map_digest = {
            "segment_count": len(segments),
            "local_mechanisms": local_mechs[:40],
            "evidence": evidence[:20],
            "counter_evidence": counter[:20],
            "segment_digests": [s.digest for s in segments],
            "chars_analyzed": meta.get("chars_analyzed"),
        }
        # reduce 输入是结构化 map 结果，不是原文切片——避免把 12k 截断伪装成全书。
        messages = [
            {"role": "system", "content": (
                "你是一位文学分析专家。根据各片段 map 结果汇总全书技法指纹，返回 JSON：\n"
                "- local_mechanisms: 局部机制数组（合并并去重）\n"
                "- cross_chapter_aggregation: 跨章/跨段聚合描述\n"
                "- full_book_fingerprint: 全书指纹描述\n"
                "- evidence: 证据数组 [{quote, location}]\n"
                "- counter_evidence: 反证数组 [{quote, location}]\n"
                "- transferable_mechanisms: 可迁移机制数组（抽象方法，禁止仿写措辞）\n"
                "- non_copyable_elements: 不可复制要素数组（专名、原句、独特设定）\n"
                "- applicable_scope: 适用范围\n"
                "只返回 JSON，不要其他文字。"
            )},
            {"role": "user", "content": json.dumps(map_digest, ensure_ascii=False)},
        ]
        result = llm.complete(messages, **_llm_complete_kwargs())
        # 用 reduce 的供应商元数据覆盖（若 map 未记录）
        reduce_meta = _observed_provider_metadata(result)
        if any(reduce_meta.values()):
            meta["provider_metadata"] = reduce_meta
        payload = _parse_json_object(result.content or "")
        # 若模型漏掉 local，用 map 合并结果兜底
        if not payload.get("local_mechanisms") and local_mechs:
            payload["local_mechanisms"] = local_mechs
        if not payload.get("evidence") and evidence:
            payload["evidence"] = evidence
        if not payload.get("counter_evidence") and counter:
            payload["counter_evidence"] = counter
        return payload

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

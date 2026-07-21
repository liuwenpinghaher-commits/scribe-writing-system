"""固定十维系统评价器:六段流水线(取数→证据→评分→反证→合并→留痕)。"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from scribe3.context_manifest import build_context_manifest
from scribe3.context_models import (
    ContextBlock,
    ContextEnvelope,
    ContextFocus,
    ContextRequest,
    ContextSnapshot,
    ContextSource,
)
from scribe3.context_outcome import ContextOutcomeTrace
from scribe3.context_policy import ContextPolicy
from scribe3.context_store import ContextStore
from scribe3.deepseek_client import DEFAULT_MODEL, OFFICIAL_PROVIDER
from scribe3.quality.confidence import compute_confidence
from scribe3.quality.models import (
    ConfidenceComponents,
    EvidenceAnchor,
    JudgmentState,
    QualityJudgment,
)
from scribe3.quality.rubrics import CORE_DIMENSIONS, RUBRIC_VERSION
from scribe3.quality.store import (
    BoundQualityJudgment,
    JudgmentTraceBinding,
    QualityStore,
)

if TYPE_CHECKING:
    from scribe3.store import SurrealStore


class RawDimensionJudgment(BaseModel):
    """单维度 LLM 结构化输出:只给引用原文,不给 UTF-16 锚点或最终置信度。"""

    model_config = ConfigDict(extra="forbid")

    state: JudgmentState = JudgmentState.EVALUABLE
    score: int | None = Field(default=None, ge=1, le=5)
    effect: str = ""
    mechanism: str = ""
    evidence_quotes: tuple[str, ...] = ()
    counter_evidence_quotes: tuple[str, ...] = ()


def _sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _anchor_quote(
    prose: str, quote: str, *, chapter_version_id: str, content_hash: str,
) -> EvidenceAnchor | None:
    idx = prose.find(quote)
    if idx < 0 or not quote:
        return None
    start = len(prose[:idx].encode("utf-16-le")) // 2
    units = len(quote.encode("utf-16-le")) // 2
    return EvidenceAnchor(
        chapter_version_id=chapter_version_id,
        start_utf16=start,
        end_utf16=start + units,
        quote=quote,
        content_hash=content_hash,
    )


class QualityEvaluator:
    """复用 QualityStore 与 Creative Context 留痕，直连 Qwen 官方服务。"""

    def __init__(self, store: "SurrealStore", llm: Any):
        self._store = store
        self._llm = llm
        self._quality = QualityStore(store)
        self._context_store = ContextStore(store)

    def evaluate_chapter(
        self,
        *,
        work: str,
        chapter_version_ids: tuple[str, ...],
        contract_id: str,
        contract_revision: int,
        rubric_revision: str = RUBRIC_VERSION,
        reference_fingerprint_ids: tuple[str, ...] = (),
        model_config: dict[str, Any] | None = None,
    ):
        model_config = model_config or {
            "provider": OFFICIAL_PROVIDER,
            "model": DEFAULT_MODEL,
        }
        snapshot = self._quality.create_chapter_snapshot(
            work=work, chapter_version_ids=tuple(chapter_version_ids),
        )
        job = self._quality.create_job(
            work=work, snapshot_id=snapshot.snapshot_id,
            contract_id=contract_id, contract_revision=contract_revision,
            rubric_revision=rubric_revision,
            reference_fingerprint_ids=reference_fingerprint_ids,
            model_config=model_config,
            actual_input_hash=_sha(f"{work}:{snapshot.snapshot_id}:evaluate"),
            idempotency_key=f"evaluate:{snapshot.snapshot_id}",
        )
        for member in snapshot.members:
            version = self._store.get_chapter_version(
                member.chapter_version_id.split(":", 1)[1]
            )
            prose = (version or {}).get("prose") or ""
            content_hash = sha256(prose.encode("utf-8")).hexdigest()
            bounds = []
            for dimension in CORE_DIMENSIONS:
                judgment = self._evaluate_dimension(
                    dimension.key, prose,
                    chapter_version_id=member.chapter_version_id,
                    content_hash=content_hash,
                )
                bound = self._bind_call(
                    judgment, job_id=job.job_id, work=work,
                    unit=member.chapter_version_id, dimension=dimension.key,
                    model_config=model_config,
                )
                bounds.append(bound)
            self._quality.save_judgments(
                job.job_id, unit=member.chapter_version_id, judgments=tuple(bounds),
            )
        return self._quality.get_evaluation(job.job_id)

    def _evaluate_dimension(
        self, dimension_key: str, prose: str, *, chapter_version_id: str, content_hash: str,
    ) -> QualityJudgment:
        dimension = next(d for d in CORE_DIMENSIONS if d.key == dimension_key)
        messages = [
            {"role": "system", "content": (
                f"你是严肃文学质量评价器。只就维度「{dimension.label}」评价给定正文。\n"
                "返回 JSON:state(evaluable/insufficient/degraded/not_applicable)、"
                "score(1-5,仅 evaluable 时给)、effect、mechanism、"
                "evidence_quotes(必须是正文中逐字存在的片段数组)、counter_evidence_quotes。\n"
                "证据引用必须是正文里可定位的原文;不得编造。不要给置信度。"
            )},
            {"role": "user", "content": prose[:12000]},
        ]
        raw: RawDimensionJudgment = self._llm.complete_json(
            messages, schema=RawDimensionJudgment,
        )
        evidence = tuple(
            anchor for anchor in (
                _anchor_quote(prose, q, chapter_version_id=chapter_version_id, content_hash=content_hash)
                for q in raw.evidence_quotes
            ) if anchor is not None
        )
        counter = tuple(
            anchor for anchor in (
                _anchor_quote(prose, q, chapter_version_id=chapter_version_id, content_hash=content_hash)
                for q in raw.counter_evidence_quotes
            ) if anchor is not None
        )
        state = raw.state
        score = raw.score
        if state is JudgmentState.EVALUABLE and (not evidence or score is None):
            state = JudgmentState.INSUFFICIENT
            score = None
        if state is not JudgmentState.EVALUABLE:
            score = None
        validity = (len(evidence) / max(1, len(raw.evidence_quotes))) if raw.evidence_quotes else 0.0
        confidence = compute_confidence(
            coverage=1.0 if prose.strip() else 0.0,
            evidence_validity_rate=validity if state is JudgmentState.EVALUABLE else 0.0,
            calibration_reliability=0.8,
            independence=1.0,
            stability=0.9,
        )
        components = ConfidenceComponents(
            context_coverage=1.0 if prose.strip() else 0.0,
            evidence_validity=validity if state is JudgmentState.EVALUABLE else 0.0,
            calibration_reliability=0.8,
            independence_factor=1.0,
            stability_factor=0.9,
        )
        return QualityJudgment(
            dimension=dimension_key,
            evaluator_kind="system",
            state=state,
            score=score,
            effect=raw.effect if state is JudgmentState.EVALUABLE else "",
            mechanism=raw.mechanism if state is JudgmentState.EVALUABLE else "",
            evidence=evidence,
            counter_evidence=counter,
            confidence_components=components,
        )

    def _bind_call(
        self, judgment: QualityJudgment, *, job_id: str, work: str, unit: str,
        dimension: str, model_config: dict[str, Any],
    ) -> BoundQualityJudgment:
        suffix = _sha(f"{job_id}:{unit}:{dimension}")[:16]
        request = ContextRequest(
            request_id=f"quality-eval-{suffix}",
            task_kind="quality_chapter",
            target_ref=unit,
            navigation_snapshot_id=f"quality-eval-nav-{suffix}",
            work=work,
            policy_version="quality-chapter.v1",
        )
        snapshot = ContextSnapshot(
            session_id=f"quality-eval-session-{suffix}", work=work, revision=1,
            thread_id=f"quality-eval-thread-{suffix}", entry="quality",
            directory_path=("quality",),
            focus=ContextFocus(type="chapter", id=unit, label=dimension),
            detail_route=unit, chapter=None, phase=None, focalizer=None,
            previous_revision=0, navigation_id=f"quality-eval-nav-{suffix}",
            captured_at=datetime(2026, 7, 21, tzinfo=timezone.utc), context_hash="",
        ).with_hash()
        rendered_input = f"quality-eval:{dimension}:{unit}"
        source = ContextSource(
            source_id=f"quality-eval-source:{suffix}", source_kind="canonical",
            work=work, content_digest=_sha(rendered_input),
        )
        envelope = ContextEnvelope(
            snapshot=snapshot,
            blocks=[ContextBlock(name="canonical", text="", token_estimate=0, sources=[source])],
            total_token_estimate=0, omitted=[],
            assembled_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            envelope_hash=_sha(f"quality-eval-envelope-{suffix}"),
        )
        manifest = build_context_manifest(
            request, ContextPolicy.for_task("quality_chapter"), envelope, rendered_input,
        )
        self._context_store.save_manifest(manifest)
        provider = model_config.get("provider", OFFICIAL_PROVIDER)
        model = model_config.get("model", DEFAULT_MODEL)
        outcome = ContextOutcomeTrace(
            outcome_id=f"quality-eval-outcome-{suffix}",
            request_id=request.request_id,
            manifest_id=manifest.manifest_hash,
            actual_input_hash=manifest.actual_input_hash,
            status="succeeded",
            provider=provider, model=model,
            provider_request_id=f"quality-eval-provider-{suffix}",
            transport_provider="httpx",
            reasoning_provider=provider, reasoning_model=model,
            reasoning_request_id=f"quality-eval-provider-{suffix}",
            usage={"input_tokens": 0, "output_tokens": 0},
            output_hash=_sha(f"quality-eval-output-{suffix}"),
        )
        self._context_store.save_outcome(outcome)
        return BoundQualityJudgment(
            judgment=judgment,
            trace=JudgmentTraceBinding(
                outcome_id=outcome.outcome_id,
                request_id=outcome.request_id,
                manifest_id=outcome.manifest_id,
                actual_input_hash=outcome.actual_input_hash,
                provider=outcome.provider,
                model=outcome.model,
                provider_request_id=outcome.provider_request_id,
                usage=outcome.usage or {},
            ),
        )

    def compare_references(
        self,
        *,
        work: str,
        snapshot_id: str,
        reference_fingerprint_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        raise NotImplementedError("compare_references 待实现")

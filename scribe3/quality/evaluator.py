"""固定十维系统评价器:六段流水线(取数→证据→评分→反证→合并→留痕)。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, TYPE_CHECKING
from uuid import uuid4

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

# 质量判断需要短而可核验的 JSON 证据，不应继承正文生成的 600 秒超时。
# TokenPlan 的 qwen3.8-flash 禁止显式关闭思考；发送该字段会收到 HTTP 400，
# 因此这里不传 thinking，让供应商按模型约束处理，失败仍如实上抛给作者重试。
QUALITY_MAX_TOKENS = 800
# 十维质量判断是固定合同与量表下的结构化裁决，不是创作采样。显式低温可降低
# Qwen 在已启用 JSON Schema 时仍偏离成自然语言说明、反复触发 JSON 修复的概率。
QUALITY_TEMPERATURE = 0.0
# 真实长文质量任务已证实：强制思考会偶发超过 120 秒。180 秒是针对单维的
# 有限硬截止，既覆盖合法慢推理，又不退回通用 600 秒无限体验。
QUALITY_TIMEOUT_SECONDS = 180
# 保留一次仅覆盖连接/5xx 的传输重试；同时允许一次 JSON 修复，避免 TokenPlan
# 偶发忽略结构化输出要求时整轮二十轴被无效文本击穿。任何修复后仍不合 schema 的
# 响应仍立即失败，绝不伪造质量完成。
QUALITY_RETRY_COUNT = 1
# 真实 TokenPlan 已出现连续两次非 JSON、第三次同一契约成功的偶发波动；
# 保持调用有界的前提下，给第三次独立结构化请求一次恢复机会。
QUALITY_MAX_REPAIRS = 2
# TokenPlan 在四路长思考请求下会持续出现连接失败；两路保留并行度，同时让真实
# 质量闭环优先于吞吐。恢复窗口由此常量推导，避免把合法慢作业误判为 worker 丢失。
QUALITY_MAX_CONCURRENCY = 2
# 供应商实现若无视底层 socket close，也不得把质量作业永远留在 running。
# 这个宽限只覆盖调度和异常传播；实际 HTTP 截止仍由客户端的 hard_deadline 控制。
QUALITY_TASK_DEADLINE_GRACE_SECONDS = 5.0


def quality_task_deadline_seconds() -> float:
    """覆盖首轮与全部 JSON 修复的单维 Future 截止。"""
    return (QUALITY_MAX_REPAIRS + 1) * (
        QUALITY_TIMEOUT_SECONDS + QUALITY_TASK_DEADLINE_GRACE_SECONDS
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
        """同步兼容入口；新调用方应先 ``prepare_job`` 再后台 ``execute_job``。"""
        job = self.prepare_job(
            work=work, chapter_version_ids=chapter_version_ids,
            contract_id=contract_id, contract_revision=contract_revision,
            rubric_revision=rubric_revision,
            reference_fingerprint_ids=reference_fingerprint_ids,
            model_config=model_config,
        )
        return self.execute_job(job.job_id)

    def prepare_job(
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
        """冻结评价输入并幂等创建 queued 作业，不发起任何模型调用。"""
        model_config = model_config or {
            "provider": OFFICIAL_PROVIDER,
            "model": DEFAULT_MODEL,
        }
        # 评价 job 的可重试边界是完整的评价真相，而不只是正文快照：同一冻结
        # 正文在新合同、参考指纹、量表或模型下必须产生新的不可变 job；完全相同
        # 的输入才复用 job，以便中断后的作者重试延续同一业务评价。
        reference_fingerprint_ids = tuple(sorted(set(reference_fingerprint_ids)))
        snapshot = self._quality.create_chapter_snapshot(
            work=work, chapter_version_ids=tuple(chapter_version_ids),
        )
        evaluation_input = {
            "work": work,
            "snapshot_id": snapshot.snapshot_id,
            "contract_id": contract_id,
            "contract_revision": contract_revision,
            "rubric_revision": rubric_revision,
            "reference_fingerprint_ids": reference_fingerprint_ids,
            "model_config": model_config,
        }
        actual_input_hash = _sha(json.dumps(
            evaluation_input, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ))
        job = self._quality.create_job(
            work=work, snapshot_id=snapshot.snapshot_id,
            contract_id=contract_id, contract_revision=contract_revision,
            rubric_revision=rubric_revision,
            reference_fingerprint_ids=reference_fingerprint_ids,
            model_config=model_config,
            actual_input_hash=actual_input_hash,
            idempotency_key=f"evaluate:{actual_input_hash}",
        )
        return job

    def execute_job(self, job_id: str):
        """执行既有冻结作业；所有模型调用成功后才一次性暴露 judgment。"""
        job = self._quality.get_job(job_id)
        snapshot = self._quality.get_snapshot(job.snapshot_id)
        model_config = job.model_settings
        expected_bounds = len(snapshot.members) * len(CORE_DIMENSIONS) * (
            2 if job.reference_fingerprint_ids else 1
        )
        existing = self._quality.get_evaluation(job.job_id)
        if len(existing.system_reference_judgments) == expected_bounds:
            return existing
        self._quality.start_job(job.job_id)
        # ``job_id`` 代表同一冻结快照的业务评价，必须保持幂等；一次实际模型
        # 调用则是独立、不可变的审计尝试。这样中断前已落库的 outcome 会保留，
        # 但不会与作者发起的重试争用相同的 manifest/outcome 三元组。
        attempt_id = uuid4().hex
        try:
            safe_reference_brief = self._safe_reference_brief(job.reference_fingerprint_ids)
            calls: list[tuple[Any, str, str, str, str]] = []
            for member in snapshot.members:
                version = self._store.get_chapter_version(
                    member.chapter_version_id.split(":", 1)[1]
                )
                prose = (version or {}).get("prose") or ""
                content_hash = sha256(prose.encode("utf-8")).hexdigest()
                calls.extend(
                    (member, "system", dimension.key, prose, content_hash)
                    for dimension in CORE_DIMENSIONS
                )
                if safe_reference_brief is not None:
                    calls.extend(
                        (member, "reference", dimension.key, prose, content_hash)
                        for dimension in CORE_DIMENSIONS
                    )

                # 模型调用彼此独立，最多四路并发以缩短作者等待；数据库留痕仍在主线程
                # 按稳定顺序完成，避免共用 Surreal client 出现并发写入或审计次序漂移。
            def invoke(call: tuple[Any, str, str, str, str]):
                member, kind, dimension_key, prose, content_hash = call
                if kind == "reference":
                    return self._evaluate_reference_dimension(
                        dimension_key, prose, chapter_version_id=member.chapter_version_id,
                        content_hash=content_hash, safe_reference_brief=safe_reference_brief,
                    )
                return self._evaluate_dimension(
                    dimension_key, prose, chapter_version_id=member.chapter_version_id,
                    content_hash=content_hash,
                )

            executor = ThreadPoolExecutor(max_workers=min(QUALITY_MAX_CONCURRENCY, len(calls)))
            futures = [executor.submit(invoke, call) for call in calls]
            try:
                per_task_deadline = quality_task_deadline_seconds()
                results = [future.result(timeout=per_task_deadline) for future in futures]
            except FutureTimeoutError as exc:
                for future in futures:
                    future.cancel()
                raise TimeoutError("质量维度调用超过硬截止") from exc
            except Exception:
                for future in futures:
                    future.cancel()
                raise
            finally:
                # ``wait=True`` 会在不遵守 client hard_deadline 的第三方 transport 上无限
                # 等待，从而留下永远 running 的 job。已开始的线程自行收尾；它们不能写库。
                executor.shutdown(wait=False, cancel_futures=True)

            bounds_by_member: dict[str, list[BoundQualityJudgment]] = {
                member.chapter_version_id: [] for member in snapshot.members
            }
            for (member, kind, dimension_key, _prose, _content_hash), (judgment, provider_result) in zip(calls, results):
                bound = self._bind_call(
                    judgment, job_id=job.job_id, work=job.work,
                    unit=member.chapter_version_id, dimension=dimension_key,
                    model_config=model_config, provider_result=provider_result,
                    task_kind="reference_compare" if kind == "reference" else "quality_chapter",
                    attempt_id=attempt_id,
                )
                bounds_by_member[member.chapter_version_id].append(bound)

            for member in snapshot.members:
                self._quality.save_judgments(
                    job.job_id, unit=member.chapter_version_id,
                    judgments=tuple(bounds_by_member[member.chapter_version_id]),
                )
            self._quality.finish_job(job.job_id)
        except Exception as exc:
            self._quality.fail_job(job.job_id, type(exc).__name__, str(exc), retryable=True)
            raise
        return self._quality.get_evaluation(job.job_id)

    def _reference_bounds(
        self,
        *,
        work: str,
        job_id: str,
        prose: str,
        chapter_version_id: str,
        content_hash: str,
        reference_fingerprint_ids: tuple[str, ...],
        model_config: dict[str, Any],
        attempt_id: str,
    ) -> tuple[BoundQualityJudgment, ...]:
        """把作者批准的安全技法摘要映射为章节参考轴，绝不读取参考原文。"""
        if not reference_fingerprint_ids:
            return ()
        brief = self._safe_reference_brief(reference_fingerprint_ids)
        assert brief is not None
        return tuple(
            self._bind_call(
                judgment,
                job_id=job_id, work=work, unit=chapter_version_id,
                dimension=dimension.key, model_config=model_config,
                provider_result=provider_result,
                task_kind="reference_compare",
                attempt_id=attempt_id,
            )
            for dimension in CORE_DIMENSIONS
            for judgment, provider_result in [self._evaluate_reference_dimension(
                dimension.key, prose, chapter_version_id=chapter_version_id,
                content_hash=content_hash, safe_reference_brief=brief,
            )]
        )

    def _safe_reference_brief(
        self, reference_fingerprint_ids: tuple[str, ...],
    ) -> str | None:
        """读取已批准指纹的可迁移摘要；此步骤必须在主线程完成。"""
        if not reference_fingerprint_ids:
            return None
        safe_fingerprints = []
        for fingerprint_id in reference_fingerprint_ids:
            record = self._quality._get_fingerprint(fingerprint_id)
            if record is None:
                raise ValueError(f"参考指纹不存在: {fingerprint_id}")
            if record.status != "approved":
                raise ValueError(f"参考指纹未获作者批准: {fingerprint_id}")
            safe_fingerprints.append({
                "fingerprint_id": record.fingerprint_id,
                "transferable_mechanisms": record.fingerprint.get("transferable_mechanisms", []),
                "non_copyable_elements": record.fingerprint.get("non_copyable_elements", []),
                "applicable_scope": record.fingerprint.get("applicable_scope", ""),
                "full_book_fingerprint": record.fingerprint.get("full_book_fingerprint", ""),
            })
        return json.dumps(safe_fingerprints, ensure_ascii=False, sort_keys=True)

    def _complete_dimension(self, messages: list[dict[str, Any]]):
        controls = {
            "max_tokens": QUALITY_MAX_TOKENS,
            "temperature": QUALITY_TEMPERATURE,
            "timeout_seconds": QUALITY_TIMEOUT_SECONDS,
            "retry_count": QUALITY_RETRY_COUNT,
        }
        detailed = getattr(self._llm, "complete_json_with_result", None)
        if callable(detailed):
            return detailed(
                messages, schema=RawDimensionJudgment,
                max_repairs=QUALITY_MAX_REPAIRS, hard_deadline=True, **controls,
            )
        return self._llm.complete_json(
            messages, schema=RawDimensionJudgment,
            max_repairs=QUALITY_MAX_REPAIRS, **controls,
        ), None

    def _evaluate_reference_dimension(
        self,
        dimension_key: str,
        prose: str,
        *,
        chapter_version_id: str,
        content_hash: str,
        safe_reference_brief: str,
    ) -> tuple[QualityJudgment, Any | None]:
        dimension = next(d for d in CORE_DIMENSIONS if d.key == dimension_key)
        messages = [
            {"role": "system", "content": (
                f"你是文学技法比较评价器。只就维度「{dimension.label}」评价给定正文。\n"
                "参考信息只含作者批准的可迁移技法与不可复制边界；不得评价、复述或模仿"
                "参考作品原文、人物、情节或专有表达。只判断本章是否以自身表达实现该类机制。\n"
                "返回 JSON:state(evaluable/insufficient/degraded/not_applicable)、"
                "score(1-5,仅 evaluable 时给)、effect、mechanism、"
                "evidence_quotes(必须是正文中逐字存在的片段数组)、counter_evidence_quotes。"
            )},
            {"role": "user", "content": f"批准技法摘要：{safe_reference_brief}\n\n正文：{prose[:12000]}"},
        ]
        raw, provider_result = self._complete_dimension(messages)
        evidence = tuple(
            anchor for anchor in (
                _anchor_quote(prose, quote, chapter_version_id=chapter_version_id,
                              content_hash=content_hash)
                for quote in raw.evidence_quotes
            ) if anchor is not None
        )
        counter = tuple(
            anchor for anchor in (
                _anchor_quote(prose, quote, chapter_version_id=chapter_version_id,
                              content_hash=content_hash)
                for quote in raw.counter_evidence_quotes
            ) if anchor is not None
        )
        state, score = raw.state, raw.score
        if state is JudgmentState.EVALUABLE and (not evidence or score is None):
            state, score = JudgmentState.INSUFFICIENT, None
        if state is not JudgmentState.EVALUABLE:
            score = None
        validity = len(evidence) / max(1, len(raw.evidence_quotes))
        components = ConfidenceComponents(
            context_coverage=1.0 if prose.strip() else 0.0,
            evidence_validity=validity if state is JudgmentState.EVALUABLE else 0.0,
            calibration_reliability=0.8,
            independence_factor=1.0,
            stability_factor=0.9,
        )
        return QualityJudgment(
            dimension=dimension_key, evaluator_kind="reference", state=state,
            score=score, effect=raw.effect if state is JudgmentState.EVALUABLE else "",
            mechanism=raw.mechanism if state is JudgmentState.EVALUABLE else "",
            evidence=evidence, counter_evidence=counter,
            confidence_components=components,
        ), provider_result

    def _evaluate_dimension(
        self, dimension_key: str, prose: str, *, chapter_version_id: str, content_hash: str,
    ) -> tuple[QualityJudgment, Any | None]:
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
        raw, provider_result = self._complete_dimension(messages)
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
        ), provider_result

    def _bind_call(
        self, judgment: QualityJudgment, *, job_id: str, work: str, unit: str,
        dimension: str, model_config: dict[str, Any], provider_result: Any | None = None,
        task_kind: str = "quality_chapter",
        attempt_id: str,
    ) -> BoundQualityJudgment:
        suffix = _sha(f"{task_kind}:{job_id}:{unit}:{dimension}:{attempt_id}")[:16]
        request = ContextRequest(
            request_id=f"quality-eval-{suffix}",
            task_kind=task_kind,
            target_ref=unit,
            navigation_snapshot_id=f"quality-eval-nav-{suffix}",
            work=work,
            policy_version=ContextPolicy.for_task(task_kind).version,
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
            request, ContextPolicy.for_task(task_kind), envelope, rendered_input,
        )
        self._context_store.save_manifest(manifest)
        # ``model_config`` is an execution intention, not provider evidence.  In
        # particular, injected test clients can exercise the judgment pipeline
        # without ever issuing a TokenPlan request.  Never turn that intention
        # into a fabricated provider/model/transport trace.
        identity = getattr(provider_result, "identity", None)
        provider = getattr(identity, "provider", None)
        provider = provider.strip() if isinstance(provider, str) and provider.strip() else None
        model = getattr(provider_result, "model", None)
        model = model.strip() if isinstance(model, str) and model.strip() else None
        response_id = getattr(provider_result, "response_id", None)
        response_id = (
            response_id.strip()
            if isinstance(response_id, str) and response_id.strip()
            else None
        )
        transport = getattr(identity, "transport", None)
        transport = transport.strip() if isinstance(transport, str) and transport.strip() else None
        raw_usage = getattr(provider_result, "usage", None)
        usage = {
            str(key): value for key, value in (raw_usage or {}).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        } or None
        outcome = ContextOutcomeTrace(
            outcome_id=f"quality-eval-outcome-{suffix}",
            request_id=request.request_id,
            manifest_id=manifest.manifest_hash,
            actual_input_hash=manifest.actual_input_hash,
            status="succeeded",
            provider=provider, model=model,
            provider_request_id=response_id,
            transport_provider=transport,
            reasoning_provider=provider, reasoning_model=model,
            reasoning_request_id=response_id,
            usage=usage,
            output_hash=_sha(judgment.model_dump_json()),
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
                usage=outcome.usage,
            ),
        )

    def compare_references(
        self,
        *,
        work: str,
        snapshot_id: str,
        reference_fingerprint_ids: tuple[str, ...],
        job_id: str | None = None,
        model_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if job_id is None:
            raise ValueError("参考比较必须绑定既有质量作业 job_id")
        snapshot = self._quality.get_snapshot(snapshot_id)
        config = model_config or {
            "provider": OFFICIAL_PROVIDER,
            "model": DEFAULT_MODEL,
        }
        attempt_id = uuid4().hex
        compared: dict[str, tuple[BoundQualityJudgment, ...]] = {}
        for member in snapshot.members:
            version = self._store.get_chapter_version(
                member.chapter_version_id.split(":", 1)[1]
            ) or {}
            compared[member.chapter_version_id] = self._reference_bounds(
                work=work, job_id=job_id, prose=str(version.get("prose") or ""),
                chapter_version_id=member.chapter_version_id,
                content_hash=member.content_hash,
                reference_fingerprint_ids=reference_fingerprint_ids,
                model_config=config,
                attempt_id=attempt_id,
            )
        return compared

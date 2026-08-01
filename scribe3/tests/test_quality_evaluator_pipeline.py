"""Task 5/验收: 质量评价器六段流水线端到端 RED 测试(真实 SurrealDB + 注入 DeepSeek)。"""
import hashlib
import threading
import time

import pytest

from scribe3.quality.evaluator import QualityEvaluator, RawDimensionJudgment
from scribe3.quality.models import JudgmentState
from scribe3.quality.rubrics import CORE_DIMENSIONS, RUBRIC_VERSION
from scribe3.quality.store import QualityStore
from scribe3.deepseek_client import CompletionResult, ProviderIdentity


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


PROSE = "井沿的水声停了。老范没有回头。铜炉里的火慢慢矮下去。"
QUOTE = "水声停了"


def _approved_contract(store):
    from scribe3.quality.models import (
        DimensionWeight, QualityContractRevision, SuccessCriterion,
    )
    quality = QualityStore(store)
    contract = QualityContractRevision(
        contract_id="contract:eval", work=store.db_name, revision=1,
        primary_genre="长篇悬疑", overlay_genres=(), target_readers="成年读者",
        reading_context="连续阅读", core_promise="让读者跟随人物穿过真相",
        intended_experience=("不安",), emotional_arc=("疑惧",),
        theme_questions=("真相是否值得代价",),
        success_criteria=tuple(
            SuccessCriterion(key=k, text=f"{k}-c")
            for k in ("character", "relationship", "structure", "language", "originality")
        ),
        dimension_weights=tuple(
            DimensionWeight(dimension=d.key, weight=1.0) for d in CORE_DIMENSIONS
        ),
        evaluation_milestones=("chapter",), completion_criteria=("十维均有判断",),
    )
    quality.save_contract_revision(contract)
    quality.approve_contract("contract:eval", 1, expected_approved=False)


def _approved_reference_fingerprint(store):
    from scribe3.quality.store import ReferenceFingerprintRecord, ReferenceWorkRecord

    quality = QualityStore(store)
    work = ReferenceWorkRecord(
        reference_work_id="reference:eval", work=store.db_name,
        title="潮汐叙事技法样本", source_hash=_sha("参考文本"),
        import_revision=1, status="imported",
    )
    quality.save_reference_work(work, source_text="参考文本")
    draft = ReferenceFingerprintRecord(
        reference_work_id=work.reference_work_id, revision=1,
        source_hash=work.source_hash, status="pending_review",
        fingerprint={
            "local_mechanisms": ["以环境声响中断制造动作压力"],
            "cross_chapter_aggregation": "每章都以选择推动秘密揭示",
            "full_book_fingerprint": "克制的悬疑推进",
            "evidence": [], "counter_evidence": [],
            "transferable_mechanisms": ["声音变化先于人物反应"],
            "non_copyable_elements": ["原作人物、情节与原句"],
            "applicable_scope": "悬疑场景开端",
        },
    )
    quality.save_reference_fingerprint(draft)
    return quality.save_reference_fingerprint(ReferenceFingerprintRecord(
        reference_work_id=draft.reference_work_id, revision=2,
        source_hash=draft.source_hash, status="approved", fingerprint=draft.fingerprint,
    ))


class ScriptedDeepSeek:
    def __init__(self):
        self.calls = 0

    def complete_json(self, messages, *, schema, **kwargs):
        self.calls += 1
        return RawDimensionJudgment(
            state=JudgmentState.EVALUABLE,
            score=4,
            effect="声音中断制造因果压力",
            mechanism="先停水声，后人物不回头",
            evidence_quotes=(QUOTE,),
            counter_evidence_quotes=(),
        )


@pytest.fixture
def evaluator(store):
    return QualityEvaluator(store, ScriptedDeepSeek())


def test_evaluate_chapter_produces_ten_anchored_system_judgments(store, evaluator):
    _approved_contract(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

    evaluation = evaluator.evaluate_chapter(
        work=store.db_name,
        chapter_version_ids=(version_id,),
        contract_id="contract:eval",
        contract_revision=1,
    )

    system = evaluation.system_reference_judgments
    assert evaluation.job.model_settings == {
        "provider": "qwen",
        "model": "qwen3.8-max-preview",
    }
    assert len(system) == len(CORE_DIMENSIONS)
    dims = {bound.judgment.dimension for bound in system}
    assert dims == {d.key for d in CORE_DIMENSIONS}
    for bound in system:
        judgment = bound.judgment
        assert judgment.evaluator_kind == "system"
        assert judgment.state is JudgmentState.EVALUABLE
        assert judgment.score == 4
        assert judgment.evidence, "每个可评价判断必须有原文证据"
        anchor = judgment.evidence[0]
        assert anchor.quote == QUOTE
        assert anchor.content_hash == _sha(PROSE)
        raw = PROSE.encode("utf-16-le")
        located = raw[anchor.start_utf16 * 2:anchor.end_utf16 * 2].decode("utf-16-le")
        assert located == QUOTE
        assert bound.trace.outcome_id, "判断必须绑定真实 ContextOutcome"
        assert bound.trace.provider is None
        assert bound.trace.model is None
        rows = store._query(
            "SELECT provider, model, reasoning_provider, reasoning_model "
            "FROM context_outcome_trace WHERE outcome_id=$outcome_id",
            {"outcome_id": bound.trace.outcome_id},
        )
        assert rows == [{
            "provider": None,
            "model": None,
            "reasoning_provider": None,
            "reasoning_model": None,
        }]


def test_evaluate_chapter_reads_back_through_get_evaluation(store, evaluator):
    _approved_contract(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
    evaluation = evaluator.evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )
    reread = QualityStore(store).get_evaluation(evaluation.job.job_id)
    assert len(reread.system_reference_judgments) == len(CORE_DIMENSIONS)
    assert reread.units[0].prose == PROSE


def test_evaluate_chapter_marks_job_completed_only_after_all_axes_are_saved(store, evaluator):
    _approved_contract(store)
    fingerprint = _approved_reference_fingerprint(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

    evaluation = evaluator.evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
        reference_fingerprint_ids=(fingerprint.fingerprint_id,),
    )

    status = QualityStore(store).get_job_status(evaluation.job.job_id)
    assert status.status == "completed"
    assert status.attempts == 1
    assert len(evaluation.system_reference_judgments) == len(CORE_DIMENSIONS) * 2


def test_execute_job_never_persists_partial_bounds_when_one_dimension_fails(store):
    """后台重试前不得把同一次冻结评价的半成品暴露给作者。"""
    _approved_contract(store)
    fingerprint = _approved_reference_fingerprint(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

    class FailingClient:
        def __init__(self):
            self.calls = 0

        def complete_json(self, _messages, *, schema, **_kwargs):
            self.calls += 1
            if self.calls == 3:
                raise RuntimeError("模拟维度调用中断")
            return RawDimensionJudgment(
                state=JudgmentState.EVALUABLE, score=4,
                effect="声音中断制造因果压力", mechanism="先停水声，后人物不回头",
                evidence_quotes=(QUOTE,),
            )

    evaluator = QualityEvaluator(store, FailingClient())
    job = evaluator.prepare_job(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
        reference_fingerprint_ids=(fingerprint.fingerprint_id,),
    )

    with pytest.raises(RuntimeError, match="模拟维度调用中断"):
        evaluator.execute_job(job.job_id)

    reread = QualityStore(store).get_evaluation(job.job_id)
    status = QualityStore(store).get_job_status(job.job_id)
    assert reread.system_reference_judgments == ()
    assert status.status == "retryable_failed"


def test_execute_job_does_not_remain_running_when_a_provider_call_ignores_deadline(store, monkeypatch):
    """线程池不得因不可协作 provider 把后台作业永久卡在 running。"""
    import scribe3.quality.evaluator as evaluator_module

    _approved_contract(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
    monkeypatch.setattr(evaluator_module, "QUALITY_TIMEOUT_SECONDS", 0.03)
    monkeypatch.setattr(evaluator_module, "QUALITY_RETRY_COUNT", 1)
    monkeypatch.setattr(evaluator_module, "QUALITY_TASK_DEADLINE_GRACE_SECONDS", 0.01)

    class DeadlineIgnoringClient:
        def complete_json(self, _messages, *, schema, **_kwargs):
            time.sleep(0.40)
            return RawDimensionJudgment(
                state=JudgmentState.EVALUABLE, score=4,
                effect="声音中断制造因果压力", mechanism="先停水声，后人物不回头",
                evidence_quotes=(QUOTE,),
            )

    evaluator = QualityEvaluator(store, DeadlineIgnoringClient())
    job = evaluator.prepare_job(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="超过硬截止"):
        evaluator.execute_job(job.job_id)

    assert time.monotonic() - started < 0.17
    assert QualityStore(store).get_job_status(job.job_id).status == "retryable_failed"
    assert QualityStore(store).get_evaluation(job.job_id).system_reference_judgments == ()


def test_evaluate_chapter_runs_independent_dimensions_with_bounded_parallelism(store):
    _approved_contract(store)

    class CountingClient:
        def __init__(self):
            self._lock = threading.Lock()
            self.inflight = 0
            self.max_inflight = 0

        def complete_json(self, _messages, *, schema, **_kwargs):
            with self._lock:
                self.inflight += 1
                self.max_inflight = max(self.max_inflight, self.inflight)
            try:
                time.sleep(0.02)
                return RawDimensionJudgment(
                    state=JudgmentState.EVALUABLE, score=4,
                    effect="声音中断制造因果压力", mechanism="先停水声，后人物不回头",
                    evidence_quotes=(QUOTE,),
                )
            finally:
                with self._lock:
                    self.inflight -= 1

    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
    client = CountingClient()
    evaluation = QualityEvaluator(store, client).evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )

    assert len(evaluation.system_reference_judgments) == len(CORE_DIMENSIONS)
    assert 2 <= client.max_inflight <= 4


def test_evaluate_chapter_generates_anchored_reference_axis_for_approved_fingerprint(store, evaluator):
    _approved_contract(store)
    fingerprint = _approved_reference_fingerprint(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

    evaluation = evaluator.evaluate_chapter(
        work=store.db_name,
        chapter_version_ids=(version_id,),
        contract_id="contract:eval",
        contract_revision=1,
        reference_fingerprint_ids=(fingerprint.fingerprint_id,),
    )

    references = [
        bound for bound in evaluation.system_reference_judgments
        if bound.judgment.evaluator_kind == "reference"
    ]
    assert len(references) == len(CORE_DIMENSIONS)
    assert all(bound.judgment.evidence for bound in references)
    assert all(bound.judgment.evidence[0].quote == QUOTE for bound in references)


def test_evaluate_chapter_persists_real_provider_metadata_when_client_exposes_it(store):
    _approved_contract(store)

    class TokenPlanClient:
        def complete_json_with_result(self, messages, *, schema, **kwargs):
            judgment = RawDimensionJudgment(
                state=JudgmentState.EVALUABLE, score=4,
                effect="声音中断制造因果压力", mechanism="先停水声后不回头",
                evidence_quotes=(QUOTE,),
            )
            completion = CompletionResult(
                content="{...}", model="qwen3.8-max-preview",
                usage={"prompt_tokens": 17, "completion_tokens": 11, "total_tokens": 28},
                finish_reason="stop",
                identity=ProviderIdentity(
                    provider="qwen", api_base="https://token-plan.example/v1",
                    model="qwen3.8-max-preview", official=True, transport="httpx",
                ),
                response_id="chatcmpl-real-quality-call",
            )
            return judgment, completion

        def complete_json(self, *args, **kwargs):
            raise AssertionError("评价器必须优先读取真实 complete_json_with_result 元数据")

    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
    evaluation = QualityEvaluator(store, TokenPlanClient()).evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )

    bound = evaluation.system_reference_judgments[0]
    assert bound.trace.provider == "qwen"
    assert bound.trace.model == "qwen3.8-max-preview"
    assert bound.trace.provider_request_id == "chatcmpl-real-quality-call"
    assert bound.trace.usage == {"prompt_tokens": 17, "completion_tokens": 11, "total_tokens": 28}


def test_evaluate_chapter_bounds_each_quality_model_call(store):
    """十维评价须限时限输出，且不得向 TokenPlan 发送不被支持的禁思考参数。"""
    _approved_contract(store)
    calls = []

    class BoundedTokenPlanClient:
        def complete_json_with_result(self, messages, *, schema, **kwargs):
            calls.append(kwargs)
            return RawDimensionJudgment(
                state=JudgmentState.EVALUABLE, score=4,
                effect="声音中断制造因果压力", mechanism="先停水声后不回头",
                evidence_quotes=(QUOTE,),
            ), None

    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
    QualityEvaluator(store, BoundedTokenPlanClient()).evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )

    assert len(calls) == len(CORE_DIMENSIONS)
    assert all(call["max_tokens"] == 800 for call in calls)
    assert all("thinking" not in call for call in calls)
    # 真实 TokenPlan 强制思考的长文评价已出现超过 120 秒的正常响应；180 秒仍是
    # 可审计的有限硬截止，避免把慢推理误报为传输失败。
    assert all(call["timeout_seconds"] == 180 for call in calls)
    assert all(call["retry_count"] == 1 for call in calls)
    assert all(call["max_repairs"] == 2 for call in calls)
    # 质量判断是固定量表的结构化裁决，而非创作采样。低温可减少 Qwen 在
    # 已声明 JSON Schema 后仍输出自然语言说明、耗尽整个重试窗口的概率。
    assert all(call["temperature"] == 0.0 for call in calls)


def test_quality_task_deadline_covers_all_structured_json_attempts():
    """外层 Future 不能在 JSON 修复预算耗尽前抢先判定维度超时。"""
    from scribe3.quality.evaluator import quality_task_deadline_seconds

    assert quality_task_deadline_seconds() == 555


def test_evaluate_chapter_marks_provider_metadata_unavailable_without_fabricating_it(store, evaluator):
    """旧式 fake 只验证判断逻辑，绝不能被包装成一次真实 TokenPlan 调用。"""
    _approved_contract(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

    evaluation = evaluator.evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )

    for bound in evaluation.system_reference_judgments:
        assert bound.trace.provider is None
        assert bound.trace.model is None
        assert bound.trace.provider_request_id is None
        assert bound.trace.usage is None
        rows = store._query(
            "SELECT provider, model, provider_request_id, transport_provider, "
            "reasoning_provider, reasoning_model, reasoning_request_id, usage "
            "FROM context_outcome_trace WHERE outcome_id=$outcome_id",
            {"outcome_id": bound.trace.outcome_id},
        )
        assert rows == [{
            "provider": None, "model": None, "provider_request_id": None,
            "transport_provider": None, "reasoning_provider": None,
            "reasoning_model": None, "reasoning_request_id": None, "usage": None,
        }]


def test_retry_after_interrupted_evaluation_uses_a_new_outcome_attempt(store):
    """半完成作业留下的 outcome 不得阻止作者重新创建同一冻结快照的评价。"""
    _approved_contract(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

    class InterruptedClient:
        calls = 0

        def complete_json(self, messages, *, schema, **kwargs):
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("模拟网络中断")
            return RawDimensionJudgment(
                state=JudgmentState.EVALUABLE, score=4,
                effect="首次请求的判断", mechanism="首次机制",
                evidence_quotes=(QUOTE,),
            )

    class RetryClient:
        def complete_json(self, messages, *, schema, **kwargs):
            return RawDimensionJudgment(
                state=JudgmentState.EVALUABLE, score=5,
                effect="重试后的独立判断", mechanism="重试机制",
                evidence_quotes=(QUOTE,),
            )

    with pytest.raises(RuntimeError, match="模拟网络中断"):
        QualityEvaluator(store, InterruptedClient()).evaluate_chapter(
            work=store.db_name, chapter_version_ids=(version_id,),
            contract_id="contract:eval", contract_revision=1,
        )

    evaluation = QualityEvaluator(store, RetryClient()).evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )

    assert len(evaluation.system_reference_judgments) == len(CORE_DIMENSIONS)
    assert {bound.judgment.score for bound in evaluation.system_reference_judgments} == {5}


def test_evaluate_chapter_creates_a_new_job_when_contract_revision_changes(store, evaluator):
    """同一冻结正文换合同修订是新的评价真相，不能与旧 job 冲突或复用。"""
    _approved_contract(store)
    quality = QualityStore(store)
    first_contract = quality.get_contract("contract:eval", 1)
    quality.save_contract_revision(first_contract.model_copy(update={"revision": 2}))
    quality.approve_contract("contract:eval", 2, expected_approved=False)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

    first = evaluator.evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )
    second = evaluator.evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=2,
    )

    assert second.job.job_id != first.job.job_id
    assert second.job.contract_revision == 2
    assert len(second.system_reference_judgments) == len(CORE_DIMENSIONS)


def test_author_judgment_merges_three_axes(store, evaluator):
    _approved_contract(store)
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
    evaluation = evaluator.evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )
    from scribe3.quality.confidence import merge_three_axes
    index = merge_three_axes(author=5, system=4, reference=None, weights=(0.50, 0.30, 0.20))
    assert index is not None and 0 <= index <= 5


def test_evidence_that_cannot_be_anchored_degrades_dimension(store):
    _approved_contract(store)

    class BadDeepSeek:
        def complete_json(self, messages, *, schema, **kwargs):
            return RawDimensionJudgment(
                state=JudgmentState.EVALUABLE, score=4,
                effect="e", mechanism="m",
                evidence_quotes=("正文里根本不存在的句子",),
            )

    evaluator = QualityEvaluator(store, BadDeepSeek())
    version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
    evaluation = evaluator.evaluate_chapter(
        work=store.db_name, chapter_version_ids=(version_id,),
        contract_id="contract:eval", contract_revision=1,
    )
    states = {b.judgment.dimension: b.judgment.state for b in evaluation.system_reference_judgments}
    assert all(state is not JudgmentState.EVALUABLE for state in states.values()), \
        "无法锚定证据的维度不得声称可评价"

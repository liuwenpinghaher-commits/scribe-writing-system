"""Task 5/验收: 质量评价器六段流水线端到端 RED 测试(真实 SurrealDB + 注入 DeepSeek)。"""
import hashlib

import pytest

from scribe3.quality.evaluator import QualityEvaluator, RawDimensionJudgment
from scribe3.quality.models import JudgmentState
from scribe3.quality.rubrics import CORE_DIMENSIONS, RUBRIC_VERSION
from scribe3.quality.store import QualityStore


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
        assert bound.trace.provider == "qwen"
        assert bound.trace.model == "qwen3.8-max-preview"
        rows = store._query(
            "SELECT provider, model, reasoning_provider, reasoning_model "
            "FROM context_outcome_trace WHERE outcome_id=$outcome_id",
            {"outcome_id": bound.trace.outcome_id},
        )
        assert rows == [{
            "provider": "qwen",
            "model": "qwen3.8-max-preview",
            "reasoning_provider": "qwen",
            "reasoning_model": "qwen3.8-max-preview",
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

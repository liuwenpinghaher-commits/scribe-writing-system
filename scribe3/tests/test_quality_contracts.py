from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from scribe3.quality.models import (
    ConfidenceComponents,
    DecisionWeights,
    EvidenceAnchor,
    JudgmentState,
    LLMJudgmentPayload,
    QualityContractRevision,
    QualityJudgment,
    ReferenceMode,
    ReferenceTarget,
    ThreeAxisDecision,
    decision_index,
)
from scribe3.quality.rubrics import CORE_DIMENSIONS, QualityAnchor, QualityDimension


EXPECTED_DIMENSIONS = (
    ("coherence_causality", "连贯性与因果"),
    ("character_truth", "人物真实性"),
    ("scene_necessity", "场景必要性"),
    ("structure_pacing", "结构与节奏"),
    ("suspense_payoff", "悬念与兑现"),
    ("emotional_effect", "情绪效力"),
    ("reading_experience", "阅读体验"),
    ("language_voice", "语言与声音"),
    ("theme_subtext", "主题与潜台词"),
    ("originality", "原创性"),
)


def _anchor() -> EvidenceAnchor:
    return EvidenceAnchor(
        chapter_version_id="chapter_version:quality-1",
        start_utf16=4,
        end_utf16=9,
        quote="他没有回头",
        content_hash="a" * 64,
    )


def _judgment(*, score: int = 4, evaluator_kind: str = "system") -> QualityJudgment:
    return QualityJudgment(
        dimension="coherence_causality",
        evaluator_kind=evaluator_kind,
        state=JudgmentState.EVALUABLE,
        score=score,
        effect="人物的选择产生了清晰且不可替代的后果。",
        mechanism="前置承诺、现场选择与代价形成连续因果链。",
        evidence=(_anchor(),),
        confidence_components=ConfidenceComponents(
            context_coverage=1.0,
            evidence_validity=1.0,
            calibration_reliability=0.9,
            independence_factor=0.8,
            stability_factor=0.9,
        ),
    )


def _full_contract(**overrides) -> QualityContractRevision:
    payload = {
        "contract_id": "quality_contract:book-a",
        "work": "book-a",
        "revision": 1,
        "primary_genre": "推理",
        "overlay_genres": ("历史", "文学"),
        "custom_genre_description": "以地方工艺史承载封闭空间推理",
        "target_readers": "偏好人物驱动推理的成年读者",
        "reading_context": "连续阅读，每章约三千字",
        "core_promise": "每次真相推进都同时改变人物关系。",
        "intended_experience": ("好奇", "不安", "释然"),
        "emotional_arc": ("低压怀疑", "关系破裂", "代价后的和解"),
        "theme_questions": ("真相是否必然带来自由？",),
        "allowed_ambiguities": ("最终动机允许两种解读",),
        "prohibited_preaching": ("不得由旁白直接总结道德答案",),
        "success_criteria": {
            "character": "关键选择来自人物既有欲望与恐惧",
            "relationship": "关系变化必须由行动而非解释触发",
            "structure": "每章推进调查或改变嫌疑结构",
            "language": "克制、具体、避免抽象评语",
            "originality": "工艺机制参与因果而非仅作装饰",
        },
        "non_negotiables": ("限知视角不泄露凶手内心",),
        "allowed_tradeoffs": ("允许慢节奏换取人物余韵",),
        "dimension_weights": {key: 1.0 for key, _label in EXPECTED_DIMENSIONS},
        "weights": DecisionWeights(),
        "reference_targets": (),
        "evaluation_milestones": ("chapter", "volume", "book"),
        "attention_budget": {"blocking": -1, "major": 5, "ordinary": 10},
        "completion_criteria": ("全部核心承诺有正文证据", "无未覆盖硬风险"),
        "approved": False,
    }
    payload.update(overrides)
    return QualityContractRevision(**payload)


def test_core_dimensions_are_fixed_and_ordered() -> None:
    assert tuple((item.key, item.label) for item in CORE_DIMENSIONS) == EXPECTED_DIMENSIONS
    assert len({item.key for item in CORE_DIMENSIONS}) == 10


def test_every_dimension_has_actionable_observations_and_five_level_anchors() -> None:
    for dimension in CORE_DIMENSIONS:
        assert len(dimension.observations) >= 4
        assert {anchor.level for anchor in dimension.anchors} == {1, 2, 3, 4, 5}
        assert all(anchor.text.strip() for anchor in dimension.anchors)
        assert "证据" in dimension.anchors[3].text
        assert "不可轻易替代" in dimension.anchors[4].text


def test_dimension_anchors_are_deeply_immutable() -> None:
    dimension = copy.deepcopy(CORE_DIMENSIONS[0])
    with pytest.raises(TypeError):
        dimension.anchors[0] = dimension.anchors[0]


def test_dimension_rejects_duplicate_or_extra_anchor_levels() -> None:
    anchors = tuple(CORE_DIMENSIONS[0].anchors) + (
        QualityAnchor(level=5, text="重复第五级"),
    )
    with pytest.raises(ValidationError):
        QualityDimension(
            key="coherence_causality",
            label="连贯性与因果",
            observations=("事实", "时间", "因果", "结果"),
            anchors=anchors,
        )


@pytest.mark.parametrize("score", [0, 6])
def test_evaluable_score_must_use_five_level_scale(score: int) -> None:
    with pytest.raises(ValidationError):
        _judgment(score=score)


def test_confidence_components_are_persisted_and_conservatively_combined() -> None:
    judgment = _judgment()
    dumped = judgment.model_dump()
    assert dumped["confidence_components"] == {
        "context_coverage": 1.0,
        "evidence_validity": 1.0,
        "calibration_reliability": 0.9,
        "independence_factor": 0.8,
        "stability_factor": 0.9,
    }
    assert "confidence" not in dumped
    assert judgment.confidence == pytest.approx(0.8)
    assert QualityJudgment.model_validate(dumped) == judgment


@pytest.mark.parametrize("forged_field", ["confidence", "confidence_components"])
def test_llm_payload_cannot_inject_service_confidence(forged_field: str) -> None:
    payload = {
        "dimension": "coherence_causality",
        "state": "evaluable",
        "score": 4,
        "effect": "选择产生明确后果",
        "mechanism": "承诺、选择和代价形成因果链",
        "evidence": (_anchor().model_dump(),),
        "counter_evidence": (),
        "uncertainty_reasons": (),
        forged_field: 1.0 if forged_field == "confidence" else {
            "context_coverage": 1.0,
            "evidence_validity": 1.0,
            "calibration_reliability": 1.0,
            "independence_factor": 1.0,
            "stability_factor": 1.0,
        },
    }
    with pytest.raises(ValidationError):
        LLMJudgmentPayload.model_validate(payload)


def test_service_constructs_judgment_from_llm_payload_and_observed_confidence() -> None:
    llm_payload = LLMJudgmentPayload(
        dimension="coherence_causality",
        state=JudgmentState.EVALUABLE,
        score=4,
        effect="选择产生明确后果",
        mechanism="承诺、选择和代价形成因果链",
        evidence=(_anchor(),),
        uncertainty_reasons=("相邻章证据尚未纳入",),
    )
    components = ConfidenceComponents(
        context_coverage=0.9,
        evidence_validity=1.0,
        calibration_reliability=0.8,
        independence_factor=0.6,
        stability_factor=0.9,
    )
    judgment = llm_payload.to_judgment(
        evaluator_kind="system",
        confidence_components=components,
    )
    assert judgment.confidence_components == components
    assert judgment.confidence == pytest.approx(0.6)


def test_llm_payload_cannot_be_converted_to_author_judgment() -> None:
    payload = LLMJudgmentPayload(
        dimension="coherence_causality",
        state=JudgmentState.EVALUABLE,
        score=4,
        effect="选择产生明确后果",
        mechanism="承诺、选择和代价形成因果链",
        evidence=(_anchor(),),
    )
    with pytest.raises(ValueError, match="system 或 reference"):
        payload.to_judgment(
            evaluator_kind="author",
            confidence_components=ConfidenceComponents(
                context_coverage=1.0,
                evidence_validity=1.0,
                calibration_reliability=1.0,
                independence_factor=1.0,
                stability_factor=1.0,
            ),
        )


@pytest.mark.parametrize(
    "state",
    [
        JudgmentState.NOT_APPLICABLE,
        JudgmentState.INSUFFICIENT,
        JudgmentState.DEGRADED,
        JudgmentState.CONFLICTED,
    ],
)
def test_non_evaluable_states_cannot_carry_a_score(state: JudgmentState) -> None:
    payload = _judgment().model_dump(exclude_computed_fields=True)
    payload.update(state=state, score=3)
    with pytest.raises(ValidationError):
        QualityJudgment.model_validate(payload)


@pytest.mark.parametrize("field", ["effect", "mechanism", "evidence"])
def test_evaluable_judgment_requires_effect_mechanism_and_evidence(field: str) -> None:
    payload = _judgment().model_dump(exclude_computed_fields=True)
    payload[field] = () if field == "evidence" else ""
    with pytest.raises(ValidationError):
        QualityJudgment.model_validate(payload)


def test_reference_target_accepts_four_modes_only() -> None:
    for mode in ReferenceMode:
        target = ReferenceTarget(
            reference_work_id="reference_work:favorite-1",
            dimension="language_voice",
            mode=mode,
            intensity=0.7,
            mechanism="用节制的动作承载人物关系变化",
            difference_requirement="人物配置与关键意象必须不同",
        )
        assert target.mode is mode
    with pytest.raises(ValidationError):
        ReferenceTarget(
            reference_work_id="reference_work:favorite-1",
            dimension="language_voice",
            mode="copy",
            intensity=0.7,
            mechanism="照搬",
            difference_requirement="无",
        )


def test_default_weights_keep_author_above_each_machine_axis() -> None:
    weights = DecisionWeights()
    assert weights.author == pytest.approx(0.50)
    assert weights.system == pytest.approx(0.30)
    assert weights.reference == pytest.approx(0.20)
    assert weights.author > weights.system
    assert weights.author > weights.reference


@pytest.mark.parametrize(
    "values",
    [
        {"author": 0.4, "system": 0.4, "reference": 0.2},
        {"author": 0.4, "system": 0.2, "reference": 0.4},
        {"author": 0.6, "system": 0.3, "reference": 0.2},
    ],
)
def test_invalid_decision_weights_are_rejected(values: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        DecisionWeights(**values)


def test_author_absence_does_not_create_a_machine_only_decision_index() -> None:
    assert decision_index(
        author=None,
        system=_judgment(score=4, evaluator_kind="system"),
        reference=_judgment(score=3, evaluator_kind="reference"),
        weights=DecisionWeights(),
    ) is None


def test_decision_index_combines_three_axes_without_total_score_field() -> None:
    author = _judgment(score=5, evaluator_kind="author")
    system = _judgment(score=4, evaluator_kind="system")
    reference = _judgment(score=3, evaluator_kind="reference")
    result = decision_index(
        author=author,
        system=system,
        reference=reference,
        weights=DecisionWeights(),
    )
    assert result == pytest.approx(4.3)
    assert "total_score" not in QualityJudgment.model_fields
    assert "total_score" not in DecisionWeights.model_fields


def test_decision_index_requires_same_dimension_and_evaluable_axes() -> None:
    reference = _judgment(score=3, evaluator_kind="reference").model_copy(
        update={"dimension": "originality"}
    )
    with pytest.raises(ValueError, match="同一维度"):
        decision_index(
            author=_judgment(score=5, evaluator_kind="author"),
            system=_judgment(score=4, evaluator_kind="system"),
            reference=reference,
            weights=DecisionWeights(),
        )


@pytest.mark.parametrize(
    "missing_axis",
    ["author", "system", "reference"],
)
def test_decision_index_requires_all_three_axes(missing_axis: str) -> None:
    axes = {
        "author": _judgment(score=5, evaluator_kind="author"),
        "system": _judgment(score=4, evaluator_kind="system"),
        "reference": _judgment(score=3, evaluator_kind="reference"),
    }
    axes[missing_axis] = None
    assert decision_index(**axes, weights=DecisionWeights()) is None


@pytest.mark.parametrize(
    "state",
    [
        JudgmentState.NOT_APPLICABLE,
        JudgmentState.INSUFFICIENT,
        JudgmentState.DEGRADED,
        JudgmentState.CONFLICTED,
    ],
)
def test_decision_index_rejects_non_evaluable_axes(state: JudgmentState) -> None:
    payload = _judgment(score=4, evaluator_kind="system").model_dump(
        exclude_computed_fields=True
    )
    payload.update(state=state, score=None, effect="", mechanism="", evidence=())
    assert decision_index(
        author=_judgment(score=5, evaluator_kind="author"),
        system=QualityJudgment.model_validate(payload),
        reference=_judgment(score=3, evaluator_kind="reference"),
        weights=DecisionWeights(),
    ) is None


def test_decision_index_rejects_evaluator_axis_impersonation() -> None:
    with pytest.raises(ValueError, match="评价来源"):
        decision_index(
            author=_judgment(score=5, evaluator_kind="system"),
            system=_judgment(score=4, evaluator_kind="system"),
            reference=_judgment(score=3, evaluator_kind="reference"),
            weights=DecisionWeights(),
        )


def test_three_axis_decision_rejects_index_without_author() -> None:
    with pytest.raises(ValidationError):
        ThreeAxisDecision(
            dimension="coherence_causality",
            author=None,
            system=_judgment(score=4, evaluator_kind="system"),
            reference=_judgment(score=3, evaluator_kind="reference"),
            decision_index=4.0,
        )


def test_three_axis_decision_rejects_wrong_slot_and_cross_dimension() -> None:
    with pytest.raises(ValidationError):
        ThreeAxisDecision(
            dimension="coherence_causality",
            author=_judgment(score=5, evaluator_kind="system"),
            system=_judgment(score=4, evaluator_kind="system"),
            reference=_judgment(score=3, evaluator_kind="reference"),
        )


def test_three_axis_decision_rejects_cross_dimension_axis() -> None:
    wrong_reference = _judgment(score=3, evaluator_kind="reference").model_copy(
        update={"dimension": "originality"}
    )
    with pytest.raises(ValidationError):
        ThreeAxisDecision(
            dimension="coherence_causality",
            author=_judgment(score=5, evaluator_kind="author"),
            system=_judgment(score=4, evaluator_kind="system"),
            reference=wrong_reference,
        )


def test_three_axis_decision_has_no_index_for_non_evaluable_axis() -> None:
    payload = _judgment(score=4, evaluator_kind="system").model_dump(
        exclude_computed_fields=True
    )
    payload.update(
        state=JudgmentState.INSUFFICIENT,
        score=None,
        effect="",
        mechanism="",
        evidence=(),
    )
    decision = ThreeAxisDecision(
        dimension="coherence_causality",
        author=_judgment(score=5, evaluator_kind="author"),
        system=QualityJudgment.model_validate(payload),
        reference=_judgment(score=3, evaluator_kind="reference"),
    )
    assert decision.decision_index is None


def test_three_axis_decision_dump_round_trips_without_derived_fields() -> None:
    decision = ThreeAxisDecision(
        dimension="coherence_causality",
        author=_judgment(score=5, evaluator_kind="author"),
        system=_judgment(score=4, evaluator_kind="system"),
        reference=_judgment(score=3, evaluator_kind="reference"),
    )
    dumped = decision.model_dump()
    assert "decision_index" not in dumped
    assert decision.decision_index == pytest.approx(4.3)
    assert ThreeAxisDecision.model_validate(dumped) == decision


def test_quality_contract_carries_every_author_quality_decision_field() -> None:
    dimension_weights = {key: 1.0 for key, _label in EXPECTED_DIMENSIONS}
    contract = _full_contract(dimension_weights=dimension_weights)
    dumped = contract.model_dump()
    for field in (
        "work",
        "primary_genre",
        "overlay_genres",
        "custom_genre_description",
        "reading_context",
        "emotional_arc",
        "theme_questions",
        "allowed_ambiguities",
        "prohibited_preaching",
        "success_criteria",
        "allowed_tradeoffs",
        "dimension_weights",
        "evaluation_milestones",
        "attention_budget",
        "completion_criteria",
    ):
        assert field in dumped
    assert {item.dimension for item in contract.dimension_weights} == set(dimension_weights)


def test_quality_contract_nested_collections_are_deeply_immutable() -> None:
    contract = _full_contract()
    with pytest.raises(TypeError):
        contract.dimension_weights[0] = contract.dimension_weights[0]
    with pytest.raises(TypeError):
        contract.success_criteria[0] = contract.success_criteria[0]


def test_quality_contract_requires_all_ten_dimension_weights() -> None:
    with pytest.raises(ValidationError):
        QualityContractRevision(
            contract_id="quality_contract:book-a",
            work="book-a",
            revision=1,
            primary_genre="推理",
            target_readers="成年读者",
            reading_context="连续阅读",
            core_promise="关系随真相改变",
            intended_experience=("好奇",),
            emotional_arc=("怀疑", "确认"),
            theme_questions=("真相意味着什么？",),
            success_criteria={
                "character": "选择可信",
                "relationship": "关系由行动改变",
                "structure": "结构有因果推进",
                "language": "语言服务声音",
                "originality": "机制形成变奏",
            },
            dimension_weights={"coherence_causality": 1.0},
            evaluation_milestones=("chapter",),
            completion_criteria=("核心承诺有证据",),
        )


def test_quality_contract_requires_all_five_success_criteria() -> None:
    dimension_weights = {key: 1.0 for key, _label in EXPECTED_DIMENSIONS}
    with pytest.raises(ValidationError):
        QualityContractRevision(
            contract_id="quality_contract:book-a",
            work="book-a",
            revision=1,
            primary_genre="推理",
            target_readers="成年读者",
            reading_context="连续阅读",
            core_promise="关系随真相改变",
            intended_experience=("好奇",),
            emotional_arc=("怀疑", "确认"),
            theme_questions=("真相意味着什么？",),
            success_criteria={"character": "选择可信"},
            dimension_weights=dimension_weights,
            evaluation_milestones=("chapter",),
            completion_criteria=("核心承诺有证据",),
        )


def test_evidence_anchor_rejects_utf16_length_mismatch_and_blank_identity() -> None:
    with pytest.raises(ValidationError):
        EvidenceAnchor(
            chapter_version_id="chapter_version:1",
            start_utf16=4,
            end_utf16=10,
            quote="短",
            content_hash="a" * 64,
        )
    with pytest.raises(ValidationError):
        EvidenceAnchor(
            chapter_version_id="   ",
            start_utf16=0,
            end_utf16=1,
            quote=" ",
            content_hash="a" * 64,
        )


def test_evidence_anchor_counts_non_bmp_as_two_utf16_units() -> None:
    anchor = EvidenceAnchor(
        chapter_version_id="chapter_version:emoji",
        start_utf16=2,
        end_utf16=5,
        quote="😀中",
        content_hash="b" * 64,
    )
    assert anchor.end_utf16 - anchor.start_utf16 == 3


def test_quality_contract_rejects_blank_content() -> None:
    with pytest.raises(ValidationError):
        _full_contract(work="   ")


def test_quality_contract_rejects_non_finite_dimension_weight() -> None:
    dimension_weights = {key: 1.0 for key, _label in EXPECTED_DIMENSIONS}
    dimension_weights["originality"] = float("inf")
    with pytest.raises(ValidationError):
        _full_contract(dimension_weights=dimension_weights)

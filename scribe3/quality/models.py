"""质量合同、证据、三轴判断与参考目标的纯数据合同。"""
from __future__ import annotations

import math
from enum import Enum
from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


QualityDimensionKey = Literal[
    "coherence_causality",
    "character_truth",
    "scene_necessity",
    "structure_pacing",
    "suspense_payoff",
    "emotional_effect",
    "reading_experience",
    "language_voice",
    "theme_subtext",
    "originality",
]
EvaluatorKind = Literal["author", "system", "reference", "human_reader"]
NonBlankStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
FiniteUnitFloat = Annotated[
    float,
    Field(ge=0, le=1, allow_inf_nan=False),
]
_DIMENSION_KEY_ORDER = (
    "coherence_causality",
    "character_truth",
    "scene_necessity",
    "structure_pacing",
    "suspense_payoff",
    "emotional_effect",
    "reading_experience",
    "language_voice",
    "theme_subtext",
    "originality",
)
_DIMENSION_KEYS = set(_DIMENSION_KEY_ORDER)
_SUCCESS_CRITERIA_KEY_ORDER = (
    "character",
    "relationship",
    "structure",
    "language",
    "originality",
)
_SUCCESS_CRITERIA_KEYS = set(_SUCCESS_CRITERIA_KEY_ORDER)


class JudgmentState(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT = "insufficient"
    DEGRADED = "degraded"
    CONFLICTED = "conflicted"
    EVALUABLE = "evaluable"


class ReferenceMode(str, Enum):
    CLOSE = "close"
    INSPIRED = "inspired"
    CONTRAST = "contrast"
    AVOID = "avoid"


class EvidenceAnchor(BaseModel):
    """绑定不可变章节版本的 UTF-16 原文证据。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_version_id: NonBlankStr
    start_utf16: int = Field(ge=0)
    end_utf16: int = Field(gt=0)
    quote: NonBlankStr
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_range(self) -> "EvidenceAnchor":
        if self.end_utf16 <= self.start_utf16:
            raise ValueError("证据结束位置必须大于开始位置")
        quote_utf16_units = len(self.quote.encode("utf-16-le")) // 2
        if self.end_utf16 - self.start_utf16 != quote_utf16_units:
            raise ValueError("证据 UTF-16 范围必须与引用文本长度一致")
        return self


class DecisionWeights(BaseModel):
    """作者权重必须高于任一机器来源，三轴合计固定为1。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    author: float = Field(default=0.50, gt=0, le=1, allow_inf_nan=False)
    system: float = Field(default=0.30, ge=0, lt=1, allow_inf_nan=False)
    reference: float = Field(default=0.20, ge=0, lt=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_author_priority(self) -> "DecisionWeights":
        if not math.isclose(
            self.author + self.system + self.reference,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("作者、系统和参考权重之和必须为1")
        if self.author <= self.system or self.author <= self.reference:
            raise ValueError("作者权重必须高于任一单独机器来源")
        return self


class ReferenceTarget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_work_id: NonBlankStr
    dimension: QualityDimensionKey
    mode: ReferenceMode
    intensity: FiniteUnitFloat
    mechanism: NonBlankStr
    difference_requirement: NonBlankStr


class ConfidenceComponents(BaseModel):
    """只能由服务端可观测信号构造的最终置信度分量。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    context_coverage: FiniteUnitFloat
    evidence_validity: FiniteUnitFloat
    calibration_reliability: FiniteUnitFloat
    independence_factor: FiniteUnitFloat
    stability_factor: FiniteUnitFloat

    @property
    def value(self) -> float:
        return min(
            self.context_coverage,
            self.evidence_validity,
            self.calibration_reliability,
            self.independence_factor,
            self.stability_factor,
        )


class QualityJudgment(BaseModel):
    """单个评价来源对一个维度的判断，不承载小说总分。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: QualityDimensionKey
    evaluator_kind: EvaluatorKind
    state: JudgmentState
    score: int | None = Field(default=None, ge=1, le=5)
    effect: str = ""
    mechanism: str = ""
    evidence: tuple[EvidenceAnchor, ...] = ()
    counter_evidence: tuple[EvidenceAnchor, ...] = ()
    confidence_components: ConfidenceComponents

    @model_validator(mode="after")
    def validate_state_payload(self) -> "QualityJudgment":
        if self.state is JudgmentState.EVALUABLE:
            if self.score is None:
                raise ValueError("可评价判断必须提供五级分数")
            if not self.effect.strip() or not self.mechanism.strip() or not self.evidence:
                raise ValueError("可评价判断必须提供效果、机制和原文证据")
        elif self.score is not None:
            raise ValueError("非可评价状态不得携带分数")
        return self

    @property
    def confidence(self) -> float:
        """保守组合可观测信号，不接受模型自报概率。"""
        return self.confidence_components.value


class LLMJudgmentPayload(BaseModel):
    """LLM 原始结构化输出；有意不接受任何最终置信度字段。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: QualityDimensionKey
    state: JudgmentState
    score: int | None = Field(default=None, ge=1, le=5)
    effect: str = ""
    mechanism: str = ""
    evidence: tuple[EvidenceAnchor, ...] = ()
    counter_evidence: tuple[EvidenceAnchor, ...] = ()
    uncertainty_reasons: tuple[NonBlankStr, ...] = ()

    @model_validator(mode="after")
    def validate_state_payload(self) -> "LLMJudgmentPayload":
        if self.state is JudgmentState.EVALUABLE:
            if self.score is None:
                raise ValueError("可评价的 LLM 结果必须提供五级分数")
            if not self.effect.strip() or not self.mechanism.strip() or not self.evidence:
                raise ValueError("可评价的 LLM 结果必须提供效果、机制和原文证据")
        elif self.score is not None:
            raise ValueError("非可评价的 LLM 结果不得携带分数")
        return self

    def to_judgment(
        self,
        *,
        evaluator_kind: Literal["system", "reference"],
        confidence_components: ConfidenceComponents,
    ) -> QualityJudgment:
        if evaluator_kind not in {"system", "reference"}:
            raise ValueError("LLM 结果只能转换为 system 或 reference 判断")
        return QualityJudgment(
            dimension=self.dimension,
            evaluator_kind=evaluator_kind,
            state=self.state,
            score=self.score,
            effect=self.effect,
            mechanism=self.mechanism,
            evidence=self.evidence,
            counter_evidence=self.counter_evidence,
            confidence_components=confidence_components,
        )


class AttentionBudget(BaseModel):
    """每个修订层默认全部展示 blocking，并限制软问题数量。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    blocking: Literal[-1] = -1
    major: int = Field(default=5, ge=0)
    ordinary: int = Field(default=10, ge=0)


class SuccessCriterion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: Literal["character", "relationship", "structure", "language", "originality"]
    text: NonBlankStr


class DimensionWeight(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: QualityDimensionKey
    weight: float = Field(gt=0, allow_inf_nan=False)


class QualityContractRevision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_id: NonBlankStr
    work: NonBlankStr
    revision: int = Field(ge=1)
    primary_genre: NonBlankStr
    overlay_genres: tuple[NonBlankStr, ...] = Field(default=(), max_length=3)
    custom_genre_description: str = ""
    target_readers: NonBlankStr
    reading_context: NonBlankStr
    core_promise: NonBlankStr
    intended_experience: tuple[NonBlankStr, ...] = Field(min_length=1)
    emotional_arc: tuple[NonBlankStr, ...] = Field(min_length=1)
    theme_questions: tuple[NonBlankStr, ...] = Field(min_length=1)
    allowed_ambiguities: tuple[NonBlankStr, ...] = ()
    prohibited_preaching: tuple[NonBlankStr, ...] = ()
    success_criteria: tuple[SuccessCriterion, ...]
    non_negotiables: tuple[NonBlankStr, ...] = ()
    allowed_tradeoffs: tuple[NonBlankStr, ...] = ()
    dimension_weights: tuple[DimensionWeight, ...]
    weights: DecisionWeights = Field(default_factory=DecisionWeights)
    reference_targets: tuple[ReferenceTarget, ...] = ()
    evaluation_milestones: tuple[
        Literal["scene", "chapter", "volume", "book"], ...
    ] = Field(min_length=1)
    attention_budget: AttentionBudget = Field(default_factory=AttentionBudget)
    completion_criteria: tuple[NonBlankStr, ...] = Field(min_length=1)
    approved: bool = False

    @field_validator("success_criteria", mode="before")
    @classmethod
    def normalize_success_criteria(cls, value):
        if isinstance(value, Mapping):
            return tuple(
                {"key": key, "text": value[key]}
                for key in _SUCCESS_CRITERIA_KEY_ORDER
                if key in value
            ) + tuple(
                {"key": key, "text": text}
                for key, text in value.items()
                if key not in _SUCCESS_CRITERIA_KEYS
            )
        return value

    @field_validator("dimension_weights", mode="before")
    @classmethod
    def normalize_dimension_weights(cls, value):
        if isinstance(value, Mapping):
            return tuple(
                {"dimension": key, "weight": value[key]}
                for key in _DIMENSION_KEY_ORDER
                if key in value
            ) + tuple(
                {"dimension": key, "weight": weight}
                for key, weight in value.items()
                if key not in _DIMENSION_KEYS
            )
        return value

    @model_validator(mode="after")
    def validate_complete_quality_contract(self) -> "QualityContractRevision":
        dimension_keys = [item.dimension for item in self.dimension_weights]
        if set(dimension_keys) != _DIMENSION_KEYS or len(dimension_keys) != 10:
            raise ValueError("质量合同必须为固定十维逐项设置权重")
        success_keys = [item.key for item in self.success_criteria]
        if set(success_keys) != _SUCCESS_CRITERIA_KEYS or len(success_keys) != 5:
            raise ValueError("质量合同必须完整声明五类成功标准")
        unique_sequences = (
            self.overlay_genres,
            self.intended_experience,
            self.emotional_arc,
            self.theme_questions,
            self.allowed_ambiguities,
            self.prohibited_preaching,
            self.non_negotiables,
            self.allowed_tradeoffs,
            self.evaluation_milestones,
            self.completion_criteria,
        )
        if any(len(values) != len(set(values)) for values in unique_sequences):
            raise ValueError("质量合同列表字段不得包含重复值")
        return self


class ThreeAxisDecision(BaseModel):
    """同一维度三轴的并列结果；index 不是跨维度总分。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: QualityDimensionKey
    author: QualityJudgment | None
    system: QualityJudgment | None
    reference: QualityJudgment | None
    weights: DecisionWeights = Field(default_factory=DecisionWeights)

    @model_validator(mode="after")
    def validate_axes(self) -> "ThreeAxisDecision":
        for slot, axis in (
            ("author", self.author),
            ("system", self.system),
            ("reference", self.reference),
        ):
            if axis is None:
                continue
            if axis.evaluator_kind != slot:
                raise ValueError(f"{slot} 槽位的评价来源不匹配")
            if axis.dimension != self.dimension:
                raise ValueError("三轴容器与判断必须属于同一维度")
        return self

    @property
    def decision_index(self) -> float | None:
        return decision_index(
            author=self.author,
            system=self.system,
            reference=self.reference,
            weights=self.weights,
        )


def decision_index(
    *,
    author: QualityJudgment | None,
    system: QualityJudgment | None,
    reference: QualityJudgment | None,
    weights: DecisionWeights,
) -> float | None:
    """只在作者参与且三轴均可评价时计算同维度修订排序指数。"""
    axes = (author, system, reference)
    if any(axis is None for axis in axes):
        return None
    present = tuple(axis for axis in axes if axis is not None)
    if len({axis.dimension for axis in present}) != 1:
        raise ValueError("三轴判断必须属于同一维度")
    expected_kinds = ("author", "system", "reference")
    if tuple(axis.evaluator_kind for axis in present) != expected_kinds:
        raise ValueError("三轴评价来源必须依次为 author、system、reference")
    if any(axis.state is not JudgmentState.EVALUABLE or axis.score is None for axis in present):
        return None
    return (
        present[0].score * weights.author
        + present[1].score * weights.system
        + present[2].score * weights.reference
    )

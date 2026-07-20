"""固定十维质量量表的版本化注册表。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scribe3.quality.models import NonBlankStr, QualityDimensionKey


class QualityAnchor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    level: Literal[1, 2, 3, 4, 5]
    text: NonBlankStr


class QualityDimension(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: QualityDimensionKey
    label: NonBlankStr
    observations: tuple[NonBlankStr, ...] = Field(min_length=4)
    anchors: tuple[QualityAnchor, ...]

    @model_validator(mode="after")
    def validate_five_levels(self) -> "QualityDimension":
        if (
            len(self.anchors) != 5
            or {anchor.level for anchor in self.anchors} != {1, 2, 3, 4, 5}
        ):
            raise ValueError("质量维度必须且只能定义1至5级锚点")
        return self


RUBRIC_VERSION = "core-ten.v1"

_FIVE_LEVEL_ANCHORS = (
    QualityAnchor(level=1, text="文本选择明显损害本书合同目标或目标阅读效果。"),
    QualityAnchor(level=2, text="局部功能成立，但存在会实质削弱合同目标的缺口。"),
    QualityAnchor(level=3, text="完成基本叙事功能，尚未形成鲜明、稳定的作品效果。"),
    QualityAnchor(level=4, text="选择有效，并有可定位原文证据说明效果与作用机制。"),
    QualityAnchor(
        level=5,
        text="高度有效；证据、机制及删除或替换后的损失表明该效果不可轻易替代。",
    ),
)


def _dimension(
    key: QualityDimensionKey,
    label: str,
    *observations: str,
) -> QualityDimension:
    return QualityDimension(
        key=key,
        label=label,
        observations=tuple(observations),
        anchors=_FIVE_LEVEL_ANCHORS,
    )

CORE_DIMENSIONS: tuple[QualityDimension, ...] = (
    _dimension(
        "coherence_causality", "连贯性与因果",
        "事实、时间、空间与状态是否前后一致",
        "行动是否由已建立的欲望、信息和条件触发",
        "结果是否改变后续可用选择而非被下一段遗忘",
        "偶然、误导与留白是否仍保留可追溯因果",
    ),
    _dimension(
        "character_truth", "人物真实性",
        "欲望、恐惧、认知与当下选择是否相互解释",
        "人物是否以自己的策略行动而非替情节搬运信息",
        "转变是否由累积压力、选择和代价推动",
        "不同人物的语言、注意力与错误方式是否可区分",
    ),
    _dimension(
        "scene_necessity", "场景必要性",
        "入场状态、欲望、阻力和风险是否具体",
        "场内策略是否发生变化并产生转折",
        "退出状态是否不同于入场状态且付出代价",
        "删除或合并本场是否会损失不可替代的因果或体验",
    ),
    _dimension(
        "structure_pacing", "结构与节奏",
        "场景与章节是否服务当前结构目的",
        "信息、行动、反应与余韵的分配是否符合目标体验",
        "转折间距和篇幅是否与重要性匹配",
        "支线是否改变主线压力而非只延迟推进",
    ),
    _dimension(
        "suspense_payoff", "悬念与兑现",
        "问题、承诺、线索和风险是否被读者清楚感知",
        "信息释放是否改变假设而非只累加谜面",
        "误导是否公平且能在回看时成立",
        "兑现是否回应前置承诺并带来新的后果",
    ),
    _dimension(
        "emotional_effect", "情绪效力",
        "目标情绪是否由具体情境和人物选择触发",
        "情绪是否经过铺垫、升级、转折与余波",
        "身体、感官、行动和留白是否替代抽象情绪标签",
        "情绪强度是否与人物关系和事件代价相称",
    ),
    _dimension(
        "reading_experience", "阅读体验",
        "叙事理解是否清晰且不消除有意歧义",
        "注意力是否集中在本段最重要的变化上",
        "读者是否有条件投入人物目标与风险",
        "空间、时间和行动是否形成叙事临场感",
    ),
    _dimension(
        "language_voice", "语言与声音",
        "词汇、句法、节奏和意象是否服务本书声音合同",
        "叙述者、POV与人物对白是否保持可区分的注意方式",
        "抽象评语、套语、重复和过度解释是否削弱文本",
        "关键句式与意象是否在语境中必要而非装饰",
    ),
    _dimension(
        "theme_subtext", "主题与潜台词",
        "主题是否通过选择、后果和反复变化显现",
        "人物说出的内容与真正欲望之间是否存在有效张力",
        "留白和歧义是否受作品证据支撑",
        "文本是否避免由旁白替读者总结唯一道德答案",
    ),
    _dimension(
        "originality", "原创性",
        "人物配置、因果组合和核心意象是否具有本书特异性",
        "参考机制是否经过迁移而非复制表达或情节表面",
        "文本是否避开通用套路、惯用AI表达和可替换桥段",
        "主动对照、类型变奏和作品自身规则是否形成统一效果",
    ),
)

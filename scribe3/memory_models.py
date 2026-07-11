"""统一记忆系统 · 候选与检索结果合同(Task 8)。

为什么单独一个纯模型文件:和 context_models 同理——检索层(memory_retrieval)、
组装器(Task 7 context_assembler)、未来的捕获管线(Task 9)都以这些类型为公共语言。
保持零业务依赖(不 import store/llm/embed),任何一端都能安全引用。

核心不变量:
- MemoryCandidate 是【检索单元】,不是存储行:一条候选可能同时被多个通道命中
  (channels/channel_ranks 记录来路),rrf_score/final_score 是融合与打分的中间态。
- source_kind 六值里 canonical 特殊:它来自现有领域表(proposition/promise 等),
  observed_at 恒 None、不衰减、冲突裁决里恒胜;其余五类是【经验性】记忆,来自 memory_item。
- MemoryCandidate 非 frozen:fuse 过程要就地回填 channels/ranks/score,故意保持可变。
- RetrievalResult 把"选入"与"被正典压制"分开留痕(rejected 带 reason),让裁剪可审计。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# 六类记忆强度:canonical=正典(领域表直查),其余为经验性(memory_item)。
SourceKind = Literal[
    "canonical", "working", "episodic", "procedural", "reference", "uncertainty",
]


class MemoryCandidate(BaseModel):
    """一次检索里的候选。字段照抄计划 Task 8 规格(第 854-868 行)。

    Task 7 retriever 协议消费的鸭子类型即以此为准:
    source_kind / source_id / text / work / provenance(+ confidence/importance/observed_at/linked_ids)。
    """

    source_kind: SourceKind
    source_id: str
    text: str
    work: str
    channels: set[str] = Field(default_factory=set)           # 命中它的通道集
    channel_ranks: dict[str, int] = Field(default_factory=dict)  # 各通道内的位次(1 起)
    rrf_score: float = 0.0
    final_score: float = 0.0
    confidence: float = 1.0
    importance: int = 2
    pinned: bool = False
    # final_score 衰减用;canonical 可为 None(正典不按时间衰减)
    observed_at: datetime | None = None
    # 与 focus 关联加权用:命中当前焦点实体则 focus_bonus
    linked_ids: set[str] = Field(default_factory=set)
    # 溯源 + 冲突判据:每项含 entity/attribute/secret/supersedes 等(canonical 携 entity/attribute)
    provenance: list[dict] = Field(default_factory=list)


class RejectedCandidate(BaseModel):
    """被冲突裁决拒绝的候选 + 原因(如 conflicts_with_canonical)。"""

    candidate: MemoryCandidate
    reason: str


class RetrievalQuery(BaseModel):
    """一次检索请求。snapshot 传 ContextSnapshot.canonical_payload()(dict),
    避免检索层反向依赖 context_models。"""

    work: str
    snapshot: dict = Field(default_factory=dict)
    query: str = ""
    k: int = 24
    focus_ids: set[str] = Field(default_factory=set)
    now: datetime | None = None


class RetrievalResult(BaseModel):
    """检索最终产物。selected 已按 final_score 降序;rejected 记正典压制等淘汰。

    telemetry(I-1/I-2 可观测化):把"未接线"从静默变可见——
    - unconflictable_count:缺 (entity,attribute) provenance 的 episodic 候选数
      → 正典压制对它们【静默失效】(需 Task 9 捕获回填 entity/attribute 才生效);
    - unlinked_count:缺 linked_ids 的经验候选数 → focus_bonus 对它们恒 0
      (需 Task 9 回填 linked_ids 才生效)。
    生产接线后应观察这两个计数随捕获管线补齐而下降。"""

    selected: list[MemoryCandidate] = Field(default_factory=list)
    rejected: list[RejectedCandidate] = Field(default_factory=list)
    unconflictable_count: int = 0
    unlinked_count: int = 0

    @property
    def candidates(self) -> list[MemoryCandidate]:
        """选入候选(等价于 selected),供 assembler 直接消费。"""
        return self.selected

    @property
    def ids(self) -> list[str]:
        """选入候选的 source_id(按 final_score 降序)。"""
        return [c.source_id for c in self.selected]

    @property
    def selected_ids(self) -> list[str]:
        """与 ids 同义,冲突场景下强调"经压制后仍选入"的语义。"""
        return [c.source_id for c in self.selected]

    @property
    def channels(self) -> set[str]:
        """本次检索所有选入候选实际命中的通道并集。"""
        out: set[str] = set()
        for c in self.selected:
            out |= c.channels
        return out

    def by_id(self, source_id: str) -> MemoryCandidate | None:
        """按 source_id 取候选:先查选入,再查被拒(便于审计被压制项)。"""
        for c in self.selected:
            if c.source_id == source_id:
                return c
        for r in self.rejected:
            if r.candidate.source_id == source_id:
                return r.candidate
        return None

"""校验层 · 兜底判官(查询,不是主防线)。

find_leaks:限知渲染已在生成前结构性防住 POV 泄露;这是第二道 POV 修订 pass——
  扫散文里是否冒出了 focalizer 帧外某私密的破绽词。craft 验证:别指望初稿自律,
  可靠层是检测 pass(+ 精修)。
causal_complete:把"连贯性"从噪声大的 LLM 评审,前移成可跑的结构查询。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from scribe3.knowledge import project_frame
from scribe3.ontology import World


@dataclass
class Leak:
    fact_id: str
    marker: str                                    # 命中的破绽词
    subject: str                                   # 私密属于谁
    range: tuple[int, int] | None = field(default=None)  # prose 字符 offset [start,end) (F-05)


@dataclass
class CausalViolation:
    event_id: str
    reason: str


def find_leaks(prose: str, world: World, focalizer: str, chapter: int) -> list[Leak]:
    """扫 focalizer 视角散文里冒出的【帧外私密】破绽词。focalizer 自己知道的不算。
    F-05: 用 re.finditer 定位每处 marker 在 prose 中的字符 offset,存入 Leak.range。
    """
    frame = project_frame(world, focalizer, chapter)
    leaks: list[Leak] = []
    for f in world.facts_at(chapter):
        if not f.secret or frame.knows(f.id):
            continue
        for m in (f.leak_markers or [f.value]):
            if not m:
                continue
            # 用 finditer 找第一处命中,白送 offset
            match = next(re.finditer(re.escape(m), prose), None)
            if match:
                leaks.append(Leak(f.id, m, f.entity_id, range=(match.start(), match.end())))
                break
    return leaks


def causal_complete(world: World, chapter: int) -> list[CausalViolation]:
    """每事件须 motivated_by_goal 非空；非首事件须有因果入边，或有可审计的新场景根理由。"""
    evs = sorted(world.events_at(chapter), key=lambda e: e.id)
    viols: list[CausalViolation] = []
    for i, ev in enumerate(evs):
        if not ev.motivated_by_goal:
            viols.append(CausalViolation(ev.id, "missing motivated_by_goal"))
        if not ev.causal_in and i > 0 and not (ev.causal_root_reason or "").strip():
            viols.append(CausalViolation(ev.id, "missing causal_in (非首事件须有因果入边)"))
    return viols

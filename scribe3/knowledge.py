"""认知层 · 知识帧投影 + 看见即知道。

范式核心:**限知渲染 = 渲染前按 focalizer 投影出他的知识帧,只把帧喂生成。**
帧里没有的事,物理上进不了 prompt(test_render 证)。判官只兜底,不是主防线。
"""
from __future__ import annotations

from dataclasses import dataclass

from scribe3.ontology import Event, Fact, KnowledgeEdge, World


@dataclass
class KnowledgeFrame:
    """某 knower 截至某章【知道】的事实集。renderer 只能看见这些。"""
    knower_id: str
    chapter: int
    facts: list[Fact]

    def knows(self, fact_id: str) -> bool:
        return any(f.id == fact_id for f in self.facts)


def project_frame(world: World, knower_id: str, chapter: int) -> KnowledgeFrame:
    """投影 knower 在 chapter 的知识帧。
    knower='world' → 全知真相(一致性裁判);否则 = 有 KnowledgeEdge 的事实。"""
    facts_now = world.facts_at(chapter)
    if knower_id == "world":
        return KnowledgeFrame("world", chapter, list(facts_now))
    known_ids = {
        k.proposition_id for k in world.knowledge
        if k.knower_id == knower_id and k.polarity
        and k.since_chapter <= chapter
        and (k.until_chapter is None or k.until_chapter > chapter)
    }
    return KnowledgeFrame(knower_id, chapter,
                          [f for f in facts_now if f.id in known_ids])


def witnesses_of(event: Event) -> set[str]:
    """在场者 = 事件的全部参与者(切片:participants 的 entity 值;含 WITNESS 角色槽)。"""
    return {v for v in event.participants.values() if v}


def see_event(world: World, event: Event) -> list[KnowledgeEdge]:
    """看见即知道:在场目击者获知本事件每条 effect;不在场者不获知(无知是默认)。"""
    new_edges: list[KnowledgeEdge] = []
    for fid in event.effects:
        for w in witnesses_of(event):
            edge = KnowledgeEdge(w, fid, since_chapter=event.story_time, acquired_via="saw")
            world.add_knowledge(edge)
            new_edges.append(edge)
    return new_edges

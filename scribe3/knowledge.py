"""认知层 · 知识帧投影 + 看见即知道。

范式核心:**限知渲染 = 渲染前按 focalizer 投影出他的知识帧,只把帧喂生成。**
帧里没有的事,物理上进不了 prompt。判官只兜底,不是主防线。
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


def project_frame(world: World, knower_id: str, chapter: int, edges=None) -> KnowledgeFrame:
    """投影 knower 在 chapter 的知识帧。
    knower='world' → 全知真相(一致性裁判);否则 = 有 KnowledgeEdge 的事实。
    edges: 可选预加载的知识边列表(避免 dramatic_irony 重复全扫,去 N+1)。"""
    facts_now = world.facts_at(chapter)
    if knower_id == "world":
        return KnowledgeFrame("world", chapter, list(facts_now))
    if edges is None:
        edges = world.load_knowledge() if hasattr(world, "load_knowledge") else world.knowledge
    known_ids = {
        k.proposition_id for k in edges
        if k.knower_id == knower_id and k.polarity
        and k.since_chapter <= chapter
        and (k.until_chapter is None or k.until_chapter > chapter)
    }
    return KnowledgeFrame(knower_id, chapter,
                          [f for f in facts_now if f.id in known_ids])


def dramatic_irony(world, focalizer: str, chapter: int) -> list[Fact]:
    """戏剧反讽点 = KNOWS(reader,F) ∧ ¬KNOWS(focalizer,F)。
    返回读者已知、而视角角色尚不知的事实(可计算查询,非人脑事后判断)。"""
    edges = world.load_knowledge() if hasattr(world, "load_knowledge") else world.knowledge
    reader = project_frame(world, "reader", chapter, edges=edges)
    foc_ids = {f.id for f in project_frame(world, focalizer, chapter, edges=edges).facts}
    return [f for f in reader.facts if f.id not in foc_ids]


def witnesses_of(event: Event) -> set[str]:
    """在场者 = 事件的全部参与者(切片:participants 的 entity 值;含 WITNESS 角色槽)。"""
    return {v for v in event.participants.values() if v}


def see_event(world: World, event: Event,
              ingest_seq: int | None = None) -> list[KnowledgeEdge]:
    """看见即知道:在场目击者获知本事件每条 effect;不在场者不获知(无知是默认)。

    ingest_seq:由 store.add_event(ingest 路径)透传,供 purge_ingest 幂等清理;
    手动/MCP 不传 → 边的 ingest_seq=NONE,不受 purge 影响。
    """
    new_edges: list[KnowledgeEdge] = []
    for fid in event.effects:
        for w in witnesses_of(event):
            edge = KnowledgeEdge(w, fid, since_chapter=event.story_time, acquired_via="saw")
            # SurrealStore.add_knowledge 接受 ingest_seq;内存 World 不接受 → TypeError 回退
            if ingest_seq is not None:
                try:
                    world.add_knowledge(edge, ingest_seq=ingest_seq)
                except TypeError:
                    world.add_knowledge(edge)
            else:
                world.add_knowledge(edge)
            new_edges.append(edge)
    return new_edges

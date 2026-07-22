"""graph() 须与 project_frame 一样尊重 knows.until_chapter。"""
from __future__ import annotations

from scribe3.ontology import Entity, Fact, KnowledgeEdge


def test_graph_hides_forgotten_knowledge(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:z_until", "role:甲", "密", "旧事", valid_from=1))
    store.add_knowledge(KnowledgeEdge(
        "role:甲", "fact:z_until", since_chapter=1, until_chapter=5))

    g3 = store.graph(chapter=3)
    knows3 = [
        e for e in g3.get("edges", [])
        if e.get("rel") == "knows" and e.get("src") == "role:甲"
        and "z_until" in str(e.get("dst"))
    ]
    assert knows3, f"章3 应显示 knows, edges={g3.get('edges')}"

    g6 = store.graph(chapter=6)
    knows6 = [
        e for e in g6.get("edges", [])
        if e.get("rel") == "knows" and e.get("src") == "role:甲"
        and "z_until" in str(e.get("dst"))
    ]
    assert not knows6, f"until_chapter=5 后章6 不应显示 knows: {knows6}"

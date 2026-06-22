"""纵切片的 canonical 场景:复刻用户最初揪出的 POV 泄露。

焦三的私密动机(攒钱给老娘治眼)secret=True、仅焦三知;老道(流云观皂衣道士)
是追索者,本不该知道。旧系统全知扁平注入 → 老道说出"够你给老娘治眼"=穿帮。
新系统按 focalizer 投影知识帧 → 老道帧里没有这条 → 渲染他视角时物理上写不出。

被 demo 与多个测试共用。基础世界恰含 2 条 Fact(治眼/雨)+ 1 个本章事件(对峙)。
"""
from __future__ import annotations

from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge, World


def luanshi_leak_world(w=None) -> World:
    """填焦三/老道泄露场景。w 可传任意与 World 鸭子兼容的后端(如 SurrealStore),
    不传则建内存 World。同一 canonical 场景可落内存或真库。"""
    if w is None:
        w = World()
    for eid, name in [("role:焦三", "焦三"), ("role:老道", "流云观皂衣道士"), ("role:阿萤", "阿萤")]:
        w.add_entity(Entity(eid, "character", name))
    w.add_entity(Entity("place:乱岗", "place", "乱葬岗"))

    # 焦三私密动机:secret,仅焦三持有边
    w.add_fact(Fact("fact:治眼", "role:焦三", "私密动机", "攒钱给老娘治眼", valid_from=1,
                    secret=True, leak_markers=["治眼", "看病", "治三年眼", "娘的眼"]))
    w.add_knowledge(KnowledgeEdge("role:焦三", "fact:治眼", since_chapter=1, acquired_via="given"))
    # 公开事实:暴雨 → 人人皆知
    w.add_fact(Fact("fact:雨", "place:乱岗", "天气", "暴雨", valid_from=1))
    w.grant_public("fact:雨", chapter=1)

    # 本章事件:老道在乱岗追上焦三索丹(章首场,无需 causal_in)
    w.add_event(Event("ev:对峙", "对峙",
                      participants={"SUBJ": "role:老道", "OBJ": "role:焦三"},
                      location="place:乱岗", story_time=1,
                      motivated_by_goal="goal:老道索丹"))
    return w


def chapter_events(world: World, chapter: int) -> list[Event]:
    return [ev for ev in world.events.values() if ev.story_time == chapter]

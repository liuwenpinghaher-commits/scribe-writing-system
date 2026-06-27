"""纵切片 · 本体层 + 知识帧投影的 TDD。

核心要证的是范式级断言:**限知渲染靠知识帧投影,角色不知道的事【物理上进不了他的帧】。**
这里证前半(帧投影);"进不了 prompt"由 project_frame + 主编对话写作保证。
全内存 dataclass,不碰 SurrealDB(故中文路径 panic 坑无关、可任意 cwd 跑)。

模型取最忠实最简:知识【只】经 KnowledgeEdge(显式 belief base,无隐式闭包)。
公开事实=给所有角色显式发边;私密=只给持有者发边;事件 effect=只给在场目击者发边。
"""
from scribe3.ontology import Entity, Fact, KnowledgeEdge, Event, World
from scribe3.knowledge import project_frame, see_event


def _luanshi_world() -> World:
    """复刻用户最初揪出的泄露场景:焦三的私密动机(攒钱给老娘治眼)只有焦三知道。
    老道(流云观皂衣道士)是追索者,本不该知道焦三为何要那颗丹。"""
    w = World()
    for eid, name in [("role:焦三", "焦三"), ("role:老道", "流云观皂衣道士"), ("role:阿萤", "阿萤")]:
        w.add_entity(Entity(eid, "character", name))
    w.add_entity(Entity("place:乱岗", "place", "乱葬岗"))
    # 焦三私密动机:secret=True,仅焦三持有 KnowledgeEdge
    w.add_fact(Fact("fact:治眼", "role:焦三", "私密动机", "攒钱给老娘治眼", valid_from=1, secret=True))
    w.add_knowledge(KnowledgeEdge("role:焦三", "fact:治眼", since_chapter=1, acquired_via="given"))
    # 一条公开事实:暴雨(人人可见)→ 给所有角色发边
    w.add_fact(Fact("fact:雨", "place:乱岗", "天气", "暴雨", valid_from=1))
    w.grant_public("fact:雨", chapter=1)
    return w


def test_world_store_roundtrip():
    w = _luanshi_world()
    assert w.entity("role:焦三").name == "焦三"
    assert len(w.facts_at(1)) == 2
    assert w.fact("fact:治眼").secret is True
    assert [f.id for f in w.facts_at(1)] == ["fact:治眼", "fact:雨"]


def test_focalizer_frame_excludes_others_secret():
    """范式证明(前半):老道的知识帧里【没有】焦三的私密动机,公开事实则有。"""
    w = _luanshi_world()
    laodao = project_frame(w, "role:老道", 1)
    assert not laodao.knows("fact:治眼"), "老道不该知道焦三私密动机"
    assert laodao.knows("fact:雨"), "公开事实老道应当知道"
    jiaosan = project_frame(w, "role:焦三", 1)
    assert jiaosan.knows("fact:治眼"), "焦三知道自己的动机"


def test_see_event_grants_knowledge_to_witnesses_only():
    """看见即知道:在场目击者获知事件 effect;不在场者不获知。"""
    w = _luanshi_world()
    w.add_fact(Fact("fact:取丹", "role:焦三", "持有", "尸丹", valid_from=2))
    ev = Event("ev:取丹", "取丹",
               participants={"SUBJ": "role:焦三", "WITNESS": "role:老道"},
               location="place:乱岗", story_time=2, effects=["fact:取丹"])
    see_event(w, ev)
    assert project_frame(w, "role:老道", 2).knows("fact:取丹"), "在场目击者获知"
    assert not project_frame(w, "role:阿萤", 2).knows("fact:取丹"), "不在场者不获知"


def test_world_frame_is_ground_truth():
    """world 帧 = 全知真相(一致性裁判用)。"""
    w = _luanshi_world()
    truth = project_frame(w, "world", 1)
    assert truth.knows("fact:治眼") and truth.knows("fact:雨")

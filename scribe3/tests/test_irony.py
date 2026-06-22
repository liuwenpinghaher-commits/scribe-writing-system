"""S3a · 三帧并存 + 戏剧反讽查询(in-memory)。

三帧 = 同一命题底座上按 knower 投影:world 真相 / 角色信念 / reader 已知。
戏剧反讽 = KNOWS(reader,F) ∧ ¬KNOWS(focal,F) —— 可计算查询,不是人脑事后判断。
"""
from scribe3.ontology import Entity, Fact, KnowledgeEdge, World
from scribe3.knowledge import project_frame, dramatic_irony


def _irony_world() -> World:
    w = World()
    w.add_entity(Entity("role:焦三", "character", "焦三"))
    w.add_entity(Entity("item:酒", "item", "那壶酒"))
    # 真相:酒里下了毒(secret,焦三不知)
    w.add_fact(Fact("fact:毒酒", "item:酒", "状态", "下了毒", valid_from=3, secret=True,
                    leak_markers=["毒", "下毒"]))
    # 读者第2章叙述就被揭示(reader 帧),焦三始终不知
    w.add_knowledge(KnowledgeEdge("reader", "fact:毒酒", since_chapter=2))
    return w


def test_three_frames_coexist():
    w = _irony_world()
    assert project_frame(w, "world", 3).knows("fact:毒酒"), "world 帧=真相,知道"
    assert project_frame(w, "reader", 3).knows("fact:毒酒"), "reader 帧:已被叙述揭示"
    assert not project_frame(w, "role:焦三", 3).knows("fact:毒酒"), "焦三不知"


def test_dramatic_irony_point():
    w = _irony_world()
    iro = dramatic_irony(w, "role:焦三", 3)
    assert any(f.id == "fact:毒酒" for f in iro), "读者知、焦三不知 = 反讽点"


def test_reader_not_yet_revealed_no_irony():
    """读者也还没被揭示时(章 < since)→ 无反讽。"""
    w = _irony_world()
    assert dramatic_irony(w, "role:焦三", 1) == [], "第1章读者还没知道,无反讽"


def test_owner_knowledge_not_irony():
    """若视角角色自己也知道 → 不构成对他的反讽。"""
    w = _irony_world()
    w.add_knowledge(KnowledgeEdge("role:焦三", "fact:毒酒", since_chapter=3, acquired_via="saw"))
    assert dramatic_irony(w, "role:焦三", 3) == [], "焦三也知道了,反讽消解"


def test_dramatic_irony_on_store(store):
    """三帧 + 反讽在真库 NS=scribe3 上成立(reader 帧走 reader_knows 表)。"""
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_fact(Fact("fact:毒酒", "item:酒", "状态", "下了毒", valid_from=3, secret=True))
    store.add_knowledge(KnowledgeEdge("reader", "fact:毒酒", since_chapter=2))
    assert project_frame(store, "reader", 3).knows("fact:毒酒"), "reader 帧落库可查"
    assert not project_frame(store, "role:焦三", 3).knows("fact:毒酒")
    iro = dramatic_irony(store, "role:焦三", 3)
    assert any(f.id == "fact:毒酒" for f in iro), "真库上反讽点成立"

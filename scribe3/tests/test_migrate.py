"""S6 · scribe2 → scribe3 数据迁移的纯映射 TDD。

把 scribe2(NS=scribe)的 character/setting 投影成 scribe3 ontology(character/proposition)。
映射函数纯(无 DB),易测;glue(读 scribe2 写 scribe3)是真机一次性脚本。
诚实:只迁世界观(角色+设定);章节正文/伏笔/母题 scribe3 尚无对应,不迁(见 README parity)。
"""
from scribe3.migrate import project_characters, project_settings


def test_project_characters():
    rows = [{"name": "焦三", "motivation": "救母", "voice": "话少", "text": "拾骨人"}]
    ents = project_characters(rows)
    assert ents[0].id == "role:焦三" and ents[0].kind == "character" and ents[0].name == "焦三"
    assert "救母" in ents[0].traits["backstory"]
    assert "拾骨人" in ents[0].traits["backstory"]


def test_project_settings():
    rows = [{"name": "铜炉之力", "stype": "力量体系", "content": "炼尸成丹,代价折寿"}]
    facts = project_settings(rows)
    assert facts[0].id == "fact:铜炉之力"
    assert facts[0].attribute == "铜炉之力"
    assert "折寿" in facts[0].value


def test_dedup_by_name():
    rows = [{"name": "焦三"}, {"name": "焦三"}]
    assert len(project_characters(rows)) == 1, "同名去重"


def test_project_foreshadows():
    from scribe3.migrate import project_foreshadows
    rows = [{"promise": "铜炉反噬", "chapter": 2, "ftype": "promise"},
            {"summary": "身世存疑", "chapter": None}]
    ps = project_foreshadows(rows)
    assert ps[0]["text"] == "铜炉反噬" and ps[0]["setup_chapter"] == 2
    assert ps[1]["setup_chapter"] == 1   # None → 1


def test_project_motifs():
    from scribe3.migrate import project_motifs
    rows = [{"name": "火", "bound_theme": "焚毁", "material_echoes": "['疤痕']", "metaphor_unfolding": "招魂之力"}]
    ms = project_motifs(rows)
    assert ms[0]["name"] == "火" and ms[0]["theme"] == "焚毁" and "招魂" in ms[0]["unfolding"]


def test_project_char_states():
    from scribe3.migrate import project_char_states
    rows = [{"character": "渡叔", "chapter_seq": "16", "change_type": "从保守到决绝", "state_desc": "同意夜渡"}]
    cs = project_char_states(rows)
    assert cs[0]["character"] == "role:渡叔" and cs[0]["chapter"] == 16 and cs[0]["value"] == "同意夜渡"

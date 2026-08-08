"""Test setting completeness system (设定完整性 + 动静结合)."""
from scribe3.ontology import Entity, Fact


class TestWorldRule:
    """层1: 世界规则 CRUD"""

    def test_add_and_list_world_rule(self, store):
        store.add_world_rule("内功三修禁忌", "magic",
                             source="天地灵气", cost="经脉寸断",
                             limitations=["最多同时修炼两门内功"],
                             exceptions=["混元体可三修"])
        rules = store.list_world_rules()
        assert len(rules) >= 1
        assert any(r["name"] == "内功三修禁忌" for r in rules)
        magic_rules = store.list_world_rules(category="magic")
        assert all(r["category"] == "magic" for r in magic_rules)

    def test_delete_world_rule(self, store):
        store.add_world_rule("测试规则", "social")
        store.delete_world_rule("测试规则")
        rules = store.list_world_rules()
        assert not any(r["name"] == "测试规则" for r in rules)


class TestFaction:
    """层1: 势力/组织 CRUD"""

    def test_add_and_list_faction(self, store):
        store.add_faction("天剑盟", ideology="正道秩序",
                          leader="苍云", known_members=["苍云", "林云"],
                          public_face="主持公道", private_operation="把持资源分配")
        factions = store.list_factions()
        assert len(factions) >= 1
        f = next(f for f in factions if f["name"] == "天剑盟")
        assert f["ideology"] == "正道秩序"
        assert "苍云" in f["known_members"]


class TestCharState:
    """层3: 角色弧光时间线"""

    def test_add_and_query_char_state(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_char_state("role:甲", 5, "ability", "突破内力中期",
                             after_state={"ability_snapshot": {"玄阴劲": "后期"}},
                             arc_phase="转折点")
        state = store.char_state_at("role:甲", 10)
        assert state["abilities"].get("玄阴劲") == "后期"
        assert len(state["arc_phases"]) >= 1

    def test_char_state_merges_multiple(self, store):
        store.add_entity(Entity("role:乙", "character", "乙"))
        store.add_char_state("role:乙", 3, "ability", "学会剑法",
                             after_state={"ability_snapshot": {"剑法": "入门"}})
        store.add_char_state("role:乙", 10, "relation", "与丙结盟",
                             after_state={"relation_snapshot": {"丙": "盟友"}})
        state = store.char_state_at("role:乙", 15)
        assert state["abilities"].get("剑法") == "入门"
        assert state["relations"].get("丙") == "盟友"

    def test_char_state_before_chapter_returns_empty(self, store):
        store.add_entity(Entity("role:丙", "character", "丙"))
        store.add_char_state("role:丙", 10, "ability", "突破")
        state = store.char_state_at("role:丙", 5)
        assert state["abilities"] == {}


class TestSettingCompleteness:
    """层2: 设定完整性检查"""

    def test_empty_book_low_score(self, store):
        result = store.setting_completeness()
        assert result["completeness_score"] < 100
        assert "世界规则" in " ".join(result["missing_dimensions"])

    def test_populated_book_higher_score(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_world_rule("魔法代价", "magic", cost="消耗灵力")
        store.add_faction("公会", ideology="互助")
        store.add_fact(Fact("fact:s1", "role:甲", "获知", "秘密", valid_from=1, secret=True))
        result = store.setting_completeness()
        assert result["total_chars"] >= 1
        assert result["total_rules"] >= 1
        assert result["total_factions"] >= 1
        assert result["completeness_score"] > 0


class TestRelationsWithUntil:
    """层3: 关系演变(until_chapter)"""

    def test_relation_ends(self, store):
        store.add_entity(Entity("role:A", "character", "A"))
        store.add_entity(Entity("role:B", "character", "B"))
        store.add_character_relation("role:A", "role:B", "ally", since_chapter=1)
        # 关系在第5章结束
        store._execute_write(
            "UPDATE character_relation SET until_chapter=$uc "
            "WHERE in=type::record('character',$a) AND out=type::record('character',$b)",
            {"uc": 5, "a": "A", "b": "B"})
        # 第3章:关系有效
        rels_3 = store.relations_at(3)
        assert any(r["relation"] == "ally" for r in rels_3)
        # 第7章:关系已结束
        rels_7 = store.relations_at(7)
        assert not any(r["relation"] == "ally" for r in rels_7)

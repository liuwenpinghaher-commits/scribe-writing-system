"""Test ontology completeness — VoiceProfile/item/term/resolve/validate."""
from scribe3.ontology import Entity, Fact


class TestVoiceProfile:
    """设计文档 §3.1.2: 9节声音指纹"""

    def test_set_and_get_voice_profile(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        profile = {
            "style_summary": "说话简短克制,不废话",
            "catchphrases": [{"phrase": "随你", "frequency": "high"}],
            "tone_rules": [{"situation": "陌生人", "tone": "冷漠"}],
            "ooc_signals": [{"signal_id": "s1", "description": "连续超过3句长句(>25字)",
                             "detection_method": "rule", "severity": "high"}],
            "version": 1,
        }
        store.set_voice_profile("role:甲", profile)
        vp = store.get_voice_profile("role:甲")
        assert vp is not None
        assert vp["style_summary"] == "说话简短克制,不废话"
        assert vp["character_id"] == "role:甲"

    def test_ooc_detection_long_sentences(self, store):
        store.add_entity(Entity("role:乙", "character", "乙"))
        store.set_voice_profile("role:乙", {
            "style_summary": "简短",
            "ooc_signals": [{"description": "连续超过3句长句(每句>25字)",
                             "detection_method": "rule", "severity": "high"}],
        })
        long_dialogue = "这是一段非常非常非常非常长的对话句子远远超过了二十五个字的限制。这又是一段非常非常非常非常长的对话句子远远超过了二十五个字的限制。这又是一段非常非常非常非常长的对话句子远远超过了二十五个字的限制。这又是一段非常非常非常非常长的对话句子远远超过了二十五个字的限制。"
        violations = store.check_ooc("role:乙", long_dialogue)
        assert len(violations) >= 1
        assert violations[0]["severity"] == "high"

    def test_ooc_no_violation_short_sentences(self, store):
        store.add_entity(Entity("role:丙", "character", "丙"))
        store.set_voice_profile("role:丙", {
            "style_summary": "简短",
            "ooc_signals": [{"description": "连续超过3句长句(每句>25字)",
                             "detection_method": "rule", "severity": "high"}],
        })
        short_dialogue = "好。行。知道了。走吧。"
        violations = store.check_ooc("role:丙", short_dialogue)
        assert len(violations) == 0


class TestItem:
    """设计文档 §3.1.4: 物品/道具"""

    def test_add_and_list_item(self, store):
        store.add_item("霜华剑", category="武器", description="家传之剑",
                       current_owner="role:甲", symbolic_state="active",
                       special_properties=["寒铁材质"])
        items = store.list_items()
        assert len(items) >= 1
        assert items[0]["name"] == "霜华剑"
        assert items[0]["symbolic_state"] == "active"

    def test_update_item_state(self, store):
        store.add_item("测试剑", symbolic_state="active")
        store.update_item_state("测试剑", "lost", chapter=22, note="被夺走")
        items = store.list_items(state="lost")
        assert any(i["name"] == "测试剑" for i in items)
        all_items = store.list_items()
        sword = next(i for i in all_items if i["name"] == "测试剑")
        assert len(sword.get("state_history") or []) >= 1

    def test_filter_by_state(self, store):
        store.add_item("active_item", symbolic_state="active")
        store.add_item("lost_item", symbolic_state="lost")
        active = store.list_items(state="active")
        lost = store.list_items(state="lost")
        assert all(i["symbolic_state"] == "active" for i in active)
        assert all(i["symbolic_state"] == "lost" for i in lost)


class TestTerm:
    """设计文档 §3.1.4: 专有名词/术语"""

    def test_add_and_list_term(self, store):
        store.add_term("化骨手", category="武功术语",
                       definition="以内力腐化对方经脉的阴毒手法",
                       aliases=["腐筋手", "化骨七式"])
        terms = store.list_terms()
        assert len(terms) >= 1
        t = next(t for t in terms if t["name"] == "化骨手")
        assert "腐筋手" in (t.get("aliases") or [])


class TestResolveEntities:
    """设计文档 §3.3: 四路召回"""

    def test_exact_name_match(self, store):
        store.add_entity(Entity("role:焦三", "character", "焦三"))
        results = store.resolve_entities("焦三在乱岗取出尸丹")
        assert any(r["name"] == "焦三" and r["reason"] == "exact_name" for r in results)

    def test_alias_match(self, store):
        store.add_entity(Entity("role:老道", "character", "老道",
                                traits={"aliases": ["云游道人"]}))
        results = store.resolve_entities("云游道人出现在山脚")
        assert any(r["reason"] == "alias" and r.get("matched_alias") == "云游道人" for r in results)

    def test_term_exact_name(self, store):
        store.add_term("尸丹", category="物品", definition="聚魂之丹")
        results = store.resolve_entities("焦三取出了尸丹")
        assert any(r["type"] == "term" and r["name"] == "尸丹" for r in results)


class TestValidateSetting:
    """设计文档 §3.4: 设定校验"""

    def test_item_state_violation(self, store):
        store.add_item("断剑", symbolic_state="destroyed")
        hints = store.validate_setting(1, "他拔出断剑迎敌")
        assert any(h["type"] == "item_state_inconsistency" for h in hints)

    def test_no_violation_clean_prose(self, store):
        store.add_item("好剑", symbolic_state="active")
        hints = store.validate_setting(1, "他拔出好剑迎敌")
        assert not any(h["type"] == "item_state_inconsistency" for h in hints)

    def test_ooc_violation_in_validate(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.set_voice_profile("role:甲", {
            "style_summary": "简短",
            "ooc_signals": [{"description": "直接说出情感词(我很高兴/我爱你/感谢)",
                             "detection_method": "rule", "severity": "high"}],
        })
        hints = store.validate_setting(1, "甲说:我很高兴见到你。")
        assert any(h["type"] == "personality_ooc" for h in hints)

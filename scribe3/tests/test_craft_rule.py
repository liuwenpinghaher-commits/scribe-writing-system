"""题材层 craft_rule · per-work 升华正则/法器写法/角色覆盖动作。用 store fixture(真临时库)。"""


def test_craft_rule_add_list(store):
    store.add_craft_rule("purple_regex", "天地为炉|万物为铜", "乱世铜炉升华句")
    rules = store.list_craft_rules()
    assert any(r["pattern"] == "天地为炉|万物为铜" for r in rules)
    assert all({"kind", "pattern", "note"} <= set(r) for r in rules)


def test_craft_rule_delete(store):
    store.add_craft_rule("artifact_craft", "法器四件套", "专名+工艺+术数+义理")
    rid = store.list_craft_rules()[0]["id"]
    store.delete_craft_rule(rid)
    assert not store.list_craft_rules()


def test_seed_craft_rules_luanshi(store):
    """首书种子:乱世铜炉的升华正则(8条)+法器四件套。"""
    store.seed_craft_rules()
    rules = store.list_craft_rules()
    kinds = {r["kind"] for r in rules}
    assert "purple_regex" in kinds and "artifact_craft" in kinds
    assert any("天地为炉" in r["pattern"] for r in rules)

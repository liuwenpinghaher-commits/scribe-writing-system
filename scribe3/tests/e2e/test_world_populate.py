from scribe3.tests.e2e import world


def test_populate_writes_characters_and_secret(store):
    world.populate(store)
    names = [c.name for c in store.characters()]
    assert "胡不为" in names and "老乌头" in names
    rules = store.list_world_rules()
    assert any(r["name"] == "灵龙镇煞钉" for r in rules)

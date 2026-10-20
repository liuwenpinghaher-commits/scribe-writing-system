"""矩阵②:写入后立即读回可见、不崩(U-002 漏刷新表 / U-004 RecordID 序列化崩溃)。"""


def test_world_rule_write_then_readback_visible(full_stack):
    """U-002:写世界规则 → 立即 GET 读回可见。"""
    r = full_stack.post("/world-rules", json={
        "name": "灵龙钉", "category": "magic", "scope": "global", "established_chapter": 1})
    assert r.status_code == 200, r.text
    rules = full_stack.get("/world-rules").json()
    assert any(x["name"] == "灵龙钉" for x in rules), "写入的世界规则必须能读回(非漏刷新)"


def test_faction_list_no_recordid_crash(full_stack):
    """U-004:写势力 → 列表读回 200 且可见,不因 RecordID 序列化裸 500。"""
    r = full_stack.post("/factions", json={"name": "青叶门", "ideology": "以活人尸骨炼丹续命之邪道纲领" * 16})
    assert r.status_code == 200, r.text
    resp = full_stack.get("/factions")
    assert resp.status_code == 200, f"列表不得 RecordID 崩溃:{resp.text}"
    assert any(f["name"] == "青叶门" for f in resp.json())

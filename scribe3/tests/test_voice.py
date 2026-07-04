"""声音标记 · voice_evolution_flag。
P3-e1 Fix 4: voice_sample 表已删除(039 迁移);原 test_add_list_voice_sample /
test_latest_voice_time_gate 已移除。保留 voice_evolution_flag 相关测试。"""


def test_voice_flag_add_list(store):
    # 批D P1-11:add_voice_flag 写入层把裸名规范化为 role: 前缀(裸名 flag 才能被 fold)
    store.add_voice_flag("焦三", 10, "被师父背叛")
    flags = store.list_voice_flags("open")
    assert any(f["character"] == "role:焦三" and f["reason"] == "被师父背叛" for f in flags)

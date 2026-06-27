"""声音标记 · voice_evolution_flag。
P3-e1 Fix 4: voice_sample 表已删除(039 迁移);原 test_add_list_voice_sample /
test_latest_voice_time_gate 已移除。保留 voice_evolution_flag 相关测试。"""


def test_voice_flag_add_list(store):
    store.add_voice_flag("焦三", 10, "被师父背叛")
    flags = store.list_voice_flags("open")
    assert any(f["character"] == "焦三" and f["reason"] == "被师父背叛" for f in flags)

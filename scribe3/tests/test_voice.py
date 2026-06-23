"""声音库 · voice_sample(4类独白+版本)+ voice_evolution_flag。用 store fixture。"""


def test_add_list_voice_sample(store):
    for kind in ("free", "pressure", "relation", "narration"):
        store.add_voice_sample("role:焦三", kind, f"{kind}样本", since_chapter=1)
    rows = store.list_voice_samples("role:焦三")
    assert len(rows) == 4
    assert {r["kind"] for r in rows} == {"free", "pressure", "relation", "narration"}


def test_latest_voice_time_gate(store):
    """同 character+kind 两版(第1章/第10章);latest 按 upto 取时间门内最新版,不剧透未来。"""
    store.add_voice_sample("role:焦三", "pressure", "初版:声细如蚊", since_chapter=1)
    store.add_voice_sample("role:焦三", "pressure", "进化:背叛后变冷硬", since_chapter=10)
    assert store.latest_voice_samples("role:焦三", 5)["pressure"] == "初版:声细如蚊"
    assert store.latest_voice_samples("role:焦三", 10)["pressure"] == "进化:背叛后变冷硬"


def test_voice_flag_add_list(store):
    store.add_voice_flag("焦三", 10, "被师父背叛")
    flags = store.list_voice_flags("open")
    assert any(f["character"] == "焦三" and f["reason"] == "被师父背叛" for f in flags)

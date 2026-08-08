"""D13: find_leaks 用焦点投影「没察觉的」作限知边界。"""
from __future__ import annotations

from scribe3.ontology import Entity, Fact
from scribe3.verify import find_leaks, find_leaks_for_chapter


def _five_layers(*, unaware: str) -> str:
    return "\n".join([
        "### 看到/听到", "门开了。",
        "### 知道", "对方在等人。",
        "### 以为(误读)", "以为是风。",
        "### 做了/说了", "他退了一步。",
        "### 没察觉的", unaware,
    ])


def test_find_leaks_flags_unaware_layer_phrase_in_prose():
    # world 无 secret，仅靠演绎边界
    class _EmptyWorld:
        knowledge = []

        def facts_at(self, chapter):
            return []

        def load_knowledge(self):
            return []

    ded = _five_layers(unaware="炉心真名写在灰契背面。")
    prose = "他忽然明白炉心真名写在灰契背面，舌尖发苦。"
    leaks = find_leaks(prose, _EmptyWorld(), "role:沈砚", 1, focal_deduction=ded)
    assert leaks
    assert any("炉心真名" in lk.marker for lk in leaks)
    assert any(lk.fact_id.startswith("deduction:unaware:") for lk in leaks)


def test_find_leaks_for_chapter_skips_stale_deduction(store):
    import json
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    store.save_chapter(1, "他忽然明白炉心真名写在灰契背面。", title="一", focalizer="role:沈砚")
    store.update_chapter_meta(1, {
        "scene_truth": "真相v1",
        "focalizer": "role:沈砚",
        "deductions": [{
            "character_id": "role:沈砚",
            "prose": _five_layers(unaware="炉心真名写在灰契背面。"),
        }],
    })
    # 剥 stamp + 改真相 → stale；for_chapter 不得用过期投影
    store._execute_write(
        "UPDATE type::record('chapter', $seq) SET deductions=$d",
        {"seq": 1, "d": json.dumps([{
            "character_id": "role:沈砚",
            "prose": _five_layers(unaware="炉心真名写在灰契背面。"),
        }], ensure_ascii=False)},
    )
    store.update_chapter_meta(1, {"scene_truth": "真相v2"})
    prose = store.get_chapter(1)["prose"]
    leaks = find_leaks_for_chapter(prose, store, "role:沈砚", 1)
    assert not any(lk.fact_id.startswith("deduction:unaware:") for lk in leaks)


def test_find_leaks_for_chapter_uses_fresh_deduction(store):
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    store.save_chapter(2, "正文干净。", title="二", focalizer="role:沈砚")
    store.update_chapter_meta(2, {
        "scene_truth": "客观：炉心真名写在灰契背面；沈砚不知。",
        "focalizer": "role:沈砚",
        "deductions": [{
            "character_id": "role:沈砚",
            "prose": _five_layers(unaware="炉心真名写在灰契背面。"),
        }],
    })
    # 确保 stamp 对齐当前 rev
    ch = store.get_chapter(2)
    rev = ch["scene_truth_revision"]
    store.update_chapter_meta(2, {
        "deductions": [{
            "character_id": "role:沈砚",
            "prose": _five_layers(unaware="炉心真名写在灰契背面。"),
            "based_on_truth_rev": rev,
        }],
    })
    leak_prose = "沈砚忽然看穿：炉心真名写在灰契背面。"
    leaks = find_leaks_for_chapter(leak_prose, store, "role:沈砚", 2)
    assert any("炉心真名" in lk.marker for lk in leaks)

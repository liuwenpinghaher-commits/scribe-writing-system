"""内容质量轨：闸绿 ≠ quality_pass。"""
from scribe3.ontology import Entity, Fact, KnowledgeEdge
from scribe3.verify_content_quality import review_chapter_quality


def _enrich_char(store, local: str, *, appearance: str, goal: str):
    store._execute_write(
        "UPDATE type::record('character', $n) SET appearance=$ap, surface_goal=$sg",
        {"n": local, "ap": appearance, "sg": goal},
    )


def craft_world_min(store):
    store.set_intent({
        "reader_feeling": "压抑中见一线热",
        "emotional_arc": "从隐瞒到被迫对质",
        "red_lines": "不美化私刑",
    })
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    store.add_entity(Entity("role:老道", "character", "老道"))
    _enrich_char(store, "沈砚", appearance="右手茧", goal="查清灰契")
    _enrich_char(store, "老道", appearance="灰袍", goal="守炉")
    store.add_character_relation("role:沈砚", "role:老道", "竞争者", 1)
    store.add_fact(Fact(
        "fact:炉秘", "role:老道", "身份", "炉看守",
        valid_from=1, secret=True, leak_markers=["炉心真名"],
    ))
    store.add_knowledge(KnowledgeEdge("role:老道", "fact:炉秘", since_chapter=1))
    store.add_motif("灰契", theme="契约代价", echoes="灰印/契血", unfolding="逐步兑价")
    store.plant_promise("灰契会反噬立契人", setup_chapter=1)
    ch = store.create_chapter(title="夜访")
    seq = ch["seq"] if isinstance(ch, dict) else 1
    return seq


def craft_chapter_scaffold(store, seq: int):
    """147 后只写还活着的字段：简介、出场、焦点。"""
    store.update_chapter_meta(seq, {
        "synopsis": (
            "沈砚夜访棺材铺,逼问灰契来历与代价;"
            "起因是他循灰印上门,转折是老道只给半句且以炉灰压场,"
            "结果冲突未决、真名仍锁。章末钩子:灰契反噬的气味已起,炉门未关死,夜色仍压着巷口。"
        ),
        "involved_characters": ["role:沈砚", "role:老道"],
        "focalizer": "role:沈砚",
    })


def test_short_prose_fails_quality(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    store.save_chapter(seq, "沈砚推门。老道缄口。灰印一痕。", focalizer="role:沈砚")
    r = review_chapter_quality(store, seq)
    assert r.ok is False
    assert any(c.id == "Q1_LENGTH" and not c.ok for c in r.checks)


def test_quality_not_auto_pass_when_gates_would_pass(store):
    """短而干净的稿可过 C1，但质量轨必须红。"""
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    prose = "沈砚推门。他对质灰契。老道缄口。灰印与契血似有若无。"
    store.save_chapter(seq, prose, focalizer="role:沈砚")
    r = review_chapter_quality(store, seq)
    assert r.ok is False
    assert "不通过" in r.summary


def test_quality_report_shape(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    store.save_chapter(seq, "x" * 100, focalizer="role:沈砚")
    d = review_chapter_quality(store, seq).to_dict()
    assert "quality_pass" in d
    assert "闸绿" in d["note"]

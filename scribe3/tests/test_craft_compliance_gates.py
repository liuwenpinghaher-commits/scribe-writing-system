"""工艺优先 GATE 机判 · 不依赖 Hermes。

P0 契约(方案 §12 + 专家团):
  空辅信必红 / 跳演绎必红 / 泄露必红 / 反面书必红 / 齐套可绿 / PASS 不含字数
"""
from __future__ import annotations

from scribe3.ontology import Entity, Fact, KnowledgeEdge
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.verify_craft_compliance import (
    PASS_FORMULA_KEYS,
    audit_chapter,
    audit_chapter_det,
    classify_root_cause,
    evaluate_save_craft_gate,
    gate_a,
    gate_b,
    gate_d,
    journey_pass,
)


def _enrich_char(store, local: str, *, appearance: str, goal: str):
    store._execute_write(
        "UPDATE type::record('character', $n) SET appearance=$ap, surface_goal=$sg",
        {"n": local, "ap": appearance, "sg": goal},
    )


def craft_world_min(store):
    """GATE-A 齐套最小世界。"""
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
    truth = (
        "客观上:灰契以炉心真名绑定立契人;老道知情;沈砚尚不知真名。"
        "本场沈砚推门夜访,对质灰契,老道只回半句。"
    )

    def _layers(*chunks: str) -> str:
        heads = ("看到/听到", "知道", "以为(误读)", "做了/说了", "没察觉的")
        # 每层至少一段可钉在 truth 上的 verbatim，满足 B6/B8
        body = []
        for h, c in zip(heads, chunks):
            body.append(f"### {h}\n{c}")
        return "\n\n".join(body)

    store.update_chapter_meta(seq, {
        "synopsis": (
            "沈砚夜访棺材铺,逼问灰契来历与代价;"
            "老道只给半句,冲突未决。再补字数避免 B1 soft。"
        ),
        "beats": [
            {"text": "沈砚推门"},
            {"text": "对质灰契"},
            {"text": "老道缄口"},
        ],
        "scene_truth": truth,
        "involved_characters": ["role:沈砚", "role:老道"],
        "focalizer": "role:沈砚",
        "deductions": [
            {
                "character_id": "role:沈砚",
                "character_name": "沈砚",
                "prose": _layers(
                    "本场沈砚推门夜访,对质灰契,老道只回半句。",
                    "客观上:灰契以炉心真名绑定立契人",  # 误：他不知真名——测试用短钉 truth
                    "未能从场景真相确认。",
                    "本场沈砚推门夜访,对质灰契,老道只回半句。",
                    "沈砚尚不知真名。",
                ),
            },
            {
                "character_id": "role:老道",
                "character_name": "老道",
                "prose": _layers(
                    "老道只回半句。",
                    "老道知情",
                    "未能从场景真相确认。",
                    "老道只回半句。",
                    "未能从场景真相确认。",
                ),
            },
        ],
    })


# ─── P0 ───────────────────────────────────────────────────────────

def test_pass_formula_excludes_word_count_and_form_fill():
    assert "word_count" not in PASS_FORMULA_KEYS
    assert "form_fill_count" not in PASS_FORMULA_KEYS
    assert "gate_a" in PASS_FORMULA_KEYS
    j = journey_pass(gate_a_ok=True, chapters=[
        {"seq": 1, "gate_b_ok": True, "gate_c_ok": True, "gate_d_ok": True},
    ])
    assert j["ok"] is True
    assert "word_count" in j["forbidden_keys_in_formula"]


def test_gate_a_fails_when_promises_and_motifs_empty(store):
    store.set_intent({
        "reader_feeling": "x", "emotional_arc": "y", "red_lines": "z",
    })
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    _enrich_char(store, "甲", appearance="高", goal="活")
    _enrich_char(store, "乙", appearance="矮", goal="逃")
    store.add_character_relation("role:甲", "role:乙", "仇敌", 1)
    store.add_fact(Fact("fact:a", "role:甲", "状态", "活着", valid_from=1))
    # 无 promise / motif
    r = gate_a(store)
    assert r.ok is False
    ids = {c.id for c in r.checks if c.verdict == "fail"}
    assert "A5" in ids or "A6" in ids
    assert "RC-EMPTY-AUX" in r.root_causes


def test_gate_a_fails_when_intent_empty(store):
    r = gate_a(store)
    assert r.ok is False
    assert any(c.id == "A1" and c.verdict == "fail" for c in r.checks)


def test_gate_a_fails_when_characters_under_two(store):
    store.set_intent({
        "reader_feeling": "x", "emotional_arc": "y", "red_lines": "z",
    })
    store.add_entity(Entity("role:甲", "character", "甲"))
    _enrich_char(store, "甲", appearance="高", goal="活")
    store.add_motif("母题", echoes="回声")
    store.plant_promise("伏笔一", setup_chapter=1)
    store.add_fact(Fact("fact:a", "role:甲", "状态", "活着", valid_from=1))
    r = gate_a(store)
    assert r.ok is False
    assert any(c.id == "A2" and c.verdict == "fail" for c in r.checks)


def test_gate_a_passes_on_min_craft_world(store):
    craft_world_min(store)
    r = gate_a(store)
    assert r.ok is True, r.to_dict()
    assert not r.root_causes or all(
        c.verdict != "fail" for c in r.checks if c.hard
    )


def test_gate_b_fails_when_skip_deduce(store):
    seq = craft_world_min(store)
    # 只有 synopsis,无演绎
    store.update_chapter_meta(seq, {
        "synopsis": "沈砚夜访。",
        "beats": [{"text": "推门"}, {"text": "问话"}, {"text": "离开"}],
    })
    r = gate_b(store, seq)
    assert r.ok is False
    fail_ids = {c.id for c in r.checks if c.verdict == "fail"}
    assert "B3" in fail_ids or "B4" in fail_ids or "B5" in fail_ids
    assert "RC-SKIP-STAGE" in classify_root_cause(r)


def test_gate_b_fails_when_missing_deduction_for_involved(store):
    seq = craft_world_min(store)
    store.update_chapter_meta(seq, {
        "synopsis": "沈砚夜访棺材铺逼问灰契。",
        "beats": [{"text": "推门"}, {"text": "对质"}, {"text": "缄口"}],
        "scene_truth": "灰契绑定真名;老道知情。",
        "involved_characters": ["role:沈砚", "role:老道"],
        "focalizer": "role:沈砚",
        "deductions": [
            {"character_id": "role:沈砚", "prose": "只知要问灰契,不知真名。"},
            # 缺老道
        ],
    })
    r = gate_b(store, seq)
    assert r.ok is False
    assert any(c.id == "B5" and c.verdict == "fail" for c in r.checks)


def test_gate_b_passes_on_full_scaffold(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    r = gate_b(store, seq)
    assert r.ok is True, r.to_dict()


def test_gate_b_stage_journal_order(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    bad = gate_b(store, seq, stage_journal={"order": ["deduce", "outline", "beats"]})
    assert bad.ok is False
    assert any(c.id == "B7" and c.verdict == "fail" for c in bad.checks)
    good = gate_b(store, seq, stage_journal={"order": ["outline", "beats", "deduce"]})
    assert good.ok is True


def test_gate_b_warns_stale_and_weak_layers(store):
    """B6s 过期 warn；B8 缺五层 warn。"""
    import json
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    # 剥 stamp 模拟旧投影 + 改真相
    store._execute_write(
        "UPDATE type::record('chapter', $seq) SET deductions=$d",
        {"seq": seq, "d": json.dumps([
            {"character_id": "role:沈砚", "prose": "只有一段散文，没有五层标题。"},
            {"character_id": "role:老道", "prose": "同样缺标题的老道投影。"},
        ], ensure_ascii=False)},
    )
    store.update_chapter_meta(seq, {"scene_truth": "客观上:灰契真名绑定；真相已改写一版。"})
    r = gate_b(store, seq)
    ids = {c.id: c for c in r.checks}
    assert ids["B6s"].verdict == "warn"
    assert ids["B8"].verdict == "warn"


def test_gate_c_fails_on_pov_leak(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    # 沈砚视角写出帧外破绽词
    leak_prose = (
        "沈砚站在门槛内。他忽然明白炉心真名就在舌尖,"
        "灰印像活物一样爬上腕子。"
    )
    store.save_chapter(seq, leak_prose, title="夜访", focalizer="role:沈砚")
    r = audit_chapter_det(store, seq)
    assert r.ok is False, r.to_dict()
    assert any(c.id == "C1" and c.verdict == "fail" for c in r.checks)


def test_gate_c_passes_on_clean_prose(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    clean = (
        "沈砚推门。棺材铺昏灯摇了一下。"
        "他对质灰契来历,老道只回半句,便缄口。"
        "灰印的影子在门楣上晃,他心里发紧,却问不出更多。"
    )
    store.save_chapter(seq, clean, title="夜访", focalizer="role:沈砚")
    r = audit_chapter_det(store, seq)
    # C1 必须过;其他 soft 不挡
    c1 = next(c for c in r.checks if c.id == "C1")
    assert c1.verdict == "pass", r.to_dict()
    assert r.ok is True, r.to_dict()


def test_anti_book_b4e72480_must_fail_new_formula(store):
    """反面:有正文、无 promise/motif/演绎脚手架 → 新公式必红。"""
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    # 故意不设 intent / motif / promise / 完整档案
    ch = store.create_chapter(title="空脚手架章")
    seq = ch["seq"] if isinstance(ch, dict) else 1
    store.save_chapter(seq, "他走了一整夜,什么也没想明白。" * 20, title="空")
    a = gate_a(store)
    b = gate_b(store, seq)
    assert a.ok is False
    assert b.ok is False
    rcs = set(a.root_causes) | set(b.root_causes)
    assert "RC-EMPTY-AUX" in rcs or "RC-SKIP-STAGE" in rcs
    # 旅程汇总也不得 PASS
    jp = journey_pass(
        gate_a_ok=a.ok,
        chapters=[{"seq": seq, "gate_b_ok": b.ok, "gate_c_ok": True, "gate_d_ok": True}],
    )
    assert jp["ok"] is False


def test_fail_always_has_rc_hint(store):
    r = gate_a(store)
    assert r.ok is False
    assert len(r.root_causes) >= 1
    assert all(x.startswith("RC-") for x in r.root_causes)


def test_audit_chapter_requires_gate_b(store):
    seq = craft_world_min(store)
    # 无脚手架直接写正文
    store.save_chapter(seq, "一段没有脚手架的正文。" * 10, focalizer="role:沈砚")
    rep = audit_chapter(store, seq, check_gate_b=True)
    assert rep.ok is False
    assert rep.gate_b is not None and rep.gate_b.ok is False


def test_gate_d_skip_without_touch_requirement(store):
    seq = craft_world_min(store)
    r = gate_d(store, seq, expect_promise_touch=False)
    # 无 hard fail
    assert r.ok is True or not any(
        c.hard and c.verdict == "fail" for c in r.checks
    )


def test_full_happy_path_journey_pass(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    prose = (
        "沈砚推门。棺材铺昏灯摇了一下。"
        "他对质灰契,老道缄口只回半句。"
        "灰印的冷意从门缝里渗进来。"
    )
    store.save_chapter(seq, prose, title="夜访", focalizer="role:沈砚")
    a = gate_a(store)
    b = gate_b(store, seq, stage_journal={"order": ["outline", "beats", "deduce"]})
    c = audit_chapter_det(store, seq)
    d = gate_d(store, seq)
    assert a.ok and b.ok and c.ok, {
        "a": a.to_dict(), "b": b.to_dict(), "c": c.to_dict(),
    }
    jp = journey_pass(
        gate_a_ok=a.ok,
        chapters=[{
            "seq": seq,
            "gate_b_ok": b.ok,
            "gate_c_ok": c.ok,
            "gate_d_ok": d.ok,
        }],
    )
    assert jp["ok"] is True


def test_evaluate_save_blocks_without_scaffold(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "1")
    seq = craft_world_min(store)
    # 无脚手架
    long_prose = "他走了一整夜什么也没想明白。" * 8
    r = evaluate_save_craft_gate(store, seq, long_prose)
    assert r["allowed"] is False
    assert r["code"] in ("craft_gate_a", "craft_gate_b")


def test_evaluate_save_allows_with_scaffold(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "1")
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    long_prose = (
        "沈砚推门。棺材铺昏灯摇了一下。"
        "他对质灰契,老道缄口只回半句。"
        "灰印的冷意从门缝里渗进来。"
    )
    r = evaluate_save_craft_gate(store, seq, long_prose)
    assert r["allowed"] is True, r


def test_evaluate_save_short_prose_allowed(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "1")
    seq = craft_world_min(store)
    r = evaluate_save_craft_gate(store, seq, "短")
    assert r["allowed"] is True
    assert r["code"] == "short_prose"


def test_save_chapter_api_409_when_craft_gate_on(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "1")
    A.set_store(store)
    c = TestClient(A.app)
    seq = craft_world_min(store)
    long_prose = "他走了一整夜什么也没想明白。" * 8
    r = c.post("/save-chapter", json={
        "seq": seq, "prose": long_prose, "title": "x", "focalizer": "role:沈砚",
    })
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail.get("code") in ("craft_gate_a", "craft_gate_b")


def test_save_chapter_api_ok_with_scaffold(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "1")
    A.set_store(store)
    c = TestClient(A.app)
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    long_prose = (
        "沈砚推门。棺材铺昏灯摇了一下。"
        "他对质灰契,老道缄口只回半句。"
        "灰印的冷意从门缝里渗进来。"
    )
    r = c.post("/save-chapter", json={
        "seq": seq, "prose": long_prose, "title": "夜访", "focalizer": "role:沈砚",
    })
    assert r.status_code == 200, r.text


def test_craft_gates_endpoint(store):
    A.set_store(store)
    c = TestClient(A.app)
    craft_world_min(store)
    r = c.get("/craft-gates")
    assert r.status_code == 200
    body = r.json()
    assert body["gate_a"]["ok"] is True
    assert "gate_a" in body

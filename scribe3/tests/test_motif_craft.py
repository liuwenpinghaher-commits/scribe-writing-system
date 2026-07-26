"""母题工艺纯函数 + store/brief/生成注入集成验收(真路径)。"""
from __future__ import annotations

from scribe3.motif_craft import (
    parse_echo_terms,
    format_echoes,
    motif_heat,
    schedule_motifs,
    motif_schedule_directives,
    generation_motif_block,
    evidence_acceptable,
)


def test_parse_echo_terms_legacy_and_structured():
    assert parse_echo_terms("炉火/锈迹、纸人") == ["炉火", "锈迹", "纸人"]
    assert parse_echo_terms("", ["炉火", "炉火", "x"]) == ["炉火"]
    assert parse_echo_terms("炉火", ["锈迹"]) == ["锈迹", "炉火"]
    assert format_echoes(["炉火", "锈迹"]) == "炉火/锈迹"
    assert evidence_acceptable("炉") is False
    assert evidence_acceptable("炉火忽明") is True


def test_motif_heat_hot_cold_neutral():
    h = motif_heat([7, 8, 9], 10)
    assert h["heat"] == "hot" and h["streak"] == 3 and h["last_touch"] == 9
    c = motif_heat([1, 2], 10)
    assert c["heat"] == "cold" and c["gap"] == 8
    assert motif_heat([], 5)["heat"] == "cold"
    n = motif_heat([8], 10)
    assert n["heat"] == "neutral" and n["gap"] == 2


def test_schedule_and_generation_block():
    motifs = [
        {"id": "a", "name": "铜炉", "theme": "代价", "echoes": "炉火", "phase": "echo"},
        {"id": "b", "name": "纸命", "theme": "命如纸", "echo_terms": ["纸人"], "phase": "seed"},
        {"id": "c", "name": "休眠", "phase": "rest", "echoes": "静水"},
    ]
    tmap = {"a": [7, 8, 9], "b": [1], "c": [1, 2, 3]}
    d = motif_schedule_directives(motifs, tmap, 10)
    assert any("铜炉" in x for x in d["avoid_overuse"])
    assert any("纸命" in x for x in d["must_echo"])
    assert not any("休眠" in x for x in d["must_echo"])
    block = generation_motif_block(d)
    assert "must_echo" in block and "avoid_overuse" in block
    assert "铜炉" in block and "纸命" in block


def test_store_heat_brief_and_codex_generation(store):
    """多章 instance → schedule hot/cold; brief 与 _codex_block 注入 must_echo/avoid_overuse。"""
    store.add_motif("铜炉", theme="代价", echoes="炉火/锈迹", phase="echo")
    store.add_motif("纸命", theme="命如纸", echo_terms=["纸人", "白幡"], phase="seed")
    mid_hot = [m for m in store.list_motifs() if m["name"] == "铜炉"][0]["id"]
    mid_cold = [m for m in store.list_motifs() if m["name"] == "纸命"][0]["id"]
    for ch in (2, 3, 4):
        assert store.add_motif_instance(mid_hot, ch, evidence=f"炉火第{ch}章") is True
    assert store.add_motif_instance(mid_cold, 1, evidence="纸人僵立") is True

    sched = store.motif_schedule(5)
    assert "铜炉" in [r["name"] for r in sched["avoid_overuse"]]
    assert "纸命" in [r["name"] for r in sched["must_echo"]]

    from scribe3.brief import assemble_chapter_brief
    brief = assemble_chapter_brief(store, 5)
    text = brief["text"]
    assert "must_echo" in text or "该回声" in text
    assert "avoid_overuse" in text or "过热" in text
    assert "铜炉" in text and "纸命" in text
    mo = brief["sections"]["motifs"]
    assert any("铜炉" in x for x in mo.get("avoid_overuse") or [])
    assert any("纸命" in x for x in mo.get("must_echo") or [])

    import scribe3.app as A
    gen = A._codex_block(store, for_generation=True, chapter=5)
    assert "must_echo" in gen or "该回声" in gen
    assert "avoid_overuse" in gen or "过热" in gen
    talk = A._codex_block(store, for_generation=False)
    assert "炉火" not in talk


def test_store_structured_echoes_dedupe_short_evidence_timeline(store):
    store.add_motif("铜炉", theme="宿命", echo_terms=["炉火", "铜锈"])
    m = store.list_motifs()[0]
    assert "炉火" in m["echo_terms"] and "铜锈" in m["echo_terms"]
    terms = store.motif_terms()
    assert "炉火" in terms and "铜锈" in terms and "铜炉" in terms

    mid = m["id"]
    assert store.add_motif_instance(mid, 2, evidence="") is False
    assert store.add_motif_instance(mid, 2, evidence="x") is False
    assert store.list_motif_instances(2) == []
    assert store.add_motif_instance(mid, 2, evidence="炉火忽明忽暗") is True
    assert store.add_motif_instance(mid, 2, evidence="炉火忽明忽暗") is False
    assert len(store.list_motif_instances(2)) == 1
    assert store.add_motif_instance(mid, 3, evidence="锈迹浮起") is True

    store.patch_motif(mid, {"phase": "turn", "tier": "volume", "scope": "卷1"})
    got = store.get_motif(mid)
    assert got["phase"] == "turn" and got["tier"] == "volume" and got["scope"] == "卷1"

    tl = store.list_motif_timeline(mid)
    assert [t["chapter"] for t in tl] == [2, 3]
    assert tl[0]["evidence"]

    store.delete_motif(mid)
    assert store.list_motifs() == []
    assert store.list_motif_instances(2) == []
    assert store.list_motif_timeline(mid) == []


def test_motif_timeline_and_schedule_http(store):
    from .test_app import _client
    c = _client(store)
    c.post("/motifs-new", json={
        "name": "铃声", "theme": "引魂", "echoes": "残铃",
        "echo_terms": ["残铃", "细鸣"], "phase": "echo", "tier": "volume",
    })
    mid = c.get("/motifs").json()[0]["id"]
    store.add_motif_instance(mid, 1, evidence="铃自鸣一次")
    store.add_motif_instance(mid, 2, evidence="铃再鸣")
    r = c.get(f"/motifs/{mid}/timeline")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2 and body[0]["chapter"] == 1
    sch = c.get("/motif-schedule?seq=5").json()
    assert "must_echo" in sch and "avoid_overuse" in sch and "rows" in sch

"""章后统一分析：prompt/parse/缓存（无网）。"""
from __future__ import annotations

from scribe3.chapter_analysis import (
    build_unified_chapter_prompt,
    get_cached_analysis,
    parse_unified_chapter_reply,
    put_cached_analysis,
    run_unified_llm_extract,
)


def test_parse_unified_two_columns():
    reply = """
    {"knowledge":{"learned":[{"who":"沈拾灯","fact":"纸钱有替字"}],"did":[],"voice_shift":[],
    "arc":[],"events":[{"type":"发现","participants":{"SUBJ":"沈拾灯"},"goal":"查替","caused_by":[]}],
    "motif":[],"promise_touch":[],"belief":[],"relation_touches":[]},
    "settings":{"entities":[{"module":"character","op":"add","name":"王阿禾","evidence":"王阿禾影",
    "confidence":0.8}],"world_rules":[],"factions":[{"name":"高门代还","evidence":"高门代还清单","confidence":0.85}],
    "items":[],"terms":[],"relations":[],"facts":[],"knowledge_edges":[],"promises":[],"motifs":[]}}
    """
    p = parse_unified_chapter_reply(reply)
    assert p["format"] == "unified"
    assert p["knowledge"]["learned"][0]["who"] == "沈拾灯"
    assert p["knowledge"]["events"][0]["type"] == "发现"
    names = {(c.module, c.target) for c in p["claims"]}
    assert ("character", "role:王阿禾") in names
    assert ("faction", "高门代还") in names


def test_parse_legacy_knowledge_flat():
    reply = '{"learned":[{"who":"A","fact":"x"}],"did":[],"events":[]}'
    p = parse_unified_chapter_reply(reply)
    assert p["format"] == "legacy_knowledge"
    assert p["knowledge"]["learned"][0]["fact"] == "x"
    assert p["claims"] == []


def test_unified_extract_with_fake_fn():
    def fake(prompt: str) -> str:
        assert "settings" in prompt and "knowledge" in prompt
        return (
            '{"knowledge":{"learned":[],"did":[{"who":"沈","action":"推门","seen_by":[]}],'
            '"voice_shift":[],"arc":[],"events":[],"motif":[],"promise_touch":[],"belief":[],'
            '"relation_touches":[]},'
            '"settings":{"entities":[],"world_rules":[],"factions":[],"items":[{"name":"火镰","evidence":"取出火镰"}],'
            '"terms":[],"relations":[],"facts":[],"knowledge_edges":[],"promises":[],"motifs":[]}}'
        )
    p = run_unified_llm_extract("取出火镰。", fake, known_character_names=["沈"])
    assert p["format"] == "unified"
    assert p["knowledge"]["did"][0]["action"] == "推门"
    assert any(c.module == "item" and c.target == "火镰" for c in p["claims"])


def test_cache_roundtrip():
    put_cached_analysis(
        "w1", 3, "正文甲",
        {"knowledge": {"learned": []}, "settings": {}, "claims": [], "format": "unified"},
    )
    c = get_cached_analysis("w1", 3, "正文甲")
    assert c and c["format"] == "unified"
    assert get_cached_analysis("w1", 3, "正文乙") is None


def test_store_cache_and_events_backfill():
    """库缓存 + 事件补枪。"""
    from scribe3.chapter_analysis import ensure_events_in_knowledge, put_cached_analysis, get_cached_analysis

    class _St:
        def __init__(self):
            self.blob = None
            self.fp = None

        def set_post_analysis_cache(self, seq, prose, payload):
            import hashlib, json
            self.fp = hashlib.sha256((prose or "").encode()).hexdigest()[:16]
            self.blob = json.dumps({**payload, "prose_fp": self.fp}, ensure_ascii=False)

        def get_post_analysis_cache(self, seq, prose):
            import hashlib, json
            if not self.blob:
                return None
            fp = hashlib.sha256((prose or "").encode()).hexdigest()[:16]
            body = json.loads(self.blob)
            if body.get("prose_fp") != fp:
                return None
            return body

    st = _St()
    put_cached_analysis(
        "w", 1, "取出火镰。",
        {
            "knowledge": {"learned": [], "did": [], "events": []},
            "settings": {"items": [{"name": "火镰", "evidence": "取出火镰"}]},
            "format": "unified",
        },
        st=st,
    )
    # 清进程缓存，只靠 store
    from scribe3 import chapter_analysis as ca
    ca._CACHE.clear()
    got = get_cached_analysis("w", 1, "取出火镰。", st=st)
    assert got and got.get("settings", {}).get("items")
    assert any(c.target == "火镰" for c in (got.get("claims") or []))

    def fake_ev(prompt: str) -> str:
        assert "事件" in prompt or "events" in prompt.lower() or "专用" in prompt
        return '{"events":[{"type":"取物","participants":{"SUBJ":"沈"},"goal":"点火","caused_by":[]}]}'

    kn = ensure_events_in_knowledge(
        {"learned": [], "did": [], "events": []},
        "取出火镰。",
        fake_ev,
    )
    assert kn and kn["events"] and kn.get("_events_backfilled")


def test_tension_cache_and_dashboard():
    from scribe3.chapter_analysis import (
        build_analysis_dashboard,
        clear_cached_analysis,
        run_tension_rubric_with_cache,
    )

    prose = "张力测正文。章末危险临近。"
    clear_cached_analysis("tw", 4, prose=prose)
    n = {"c": 0}

    def fake(prompt: str, system=None):
        n["c"] += 1
        return (
            '{"dramatic_question":{"present":true,"answered_escalated":false,"note":"谁动了灯"},'
            '"outcomes":[{"scene":"对峙","type":"yes_but"}],'
            '"value_shift":{"present":true,"note":"暖→冷"},'
            '"micro_tension":{"deserts":[]},'
            '"hook":{"present":true,"type":"danger","strength":"med"}}'
        )

    r1 = run_tension_rubric_with_cache(
        work="tw", seq=4, prose=prose, complete_fn=fake, force=False,
    )
    assert r1.get("cache_hit") is False and r1.get("rubric")
    r2 = run_tension_rubric_with_cache(
        work="tw", seq=4, prose=prose, complete_fn=fake, force=False,
    )
    assert r2.get("cache_hit") is True and n["c"] == 1
    dash = build_analysis_dashboard(work="tw", seq=4, prose=prose)
    assert dash.get("has_tension")
    assert dash.get("qc_quick", {}).get("source") == "deterministic"


def test_discipline_cache_roundtrip():
    from scribe3.chapter_analysis import (
        clear_cached_analysis,
        get_cached_analysis,
        run_discipline_with_cache,
    )

    calls = {"n": 0}

    def fake(prompt: str, system=None):
        calls["n"] += 1
        return '{"ok": true, "violations": [], "cut_after": ""}'

    clear_cached_analysis("dw", 2, prose="纪律测正文")
    r1 = run_discipline_with_cache(
        work="dw", seq=2, prose="纪律测正文", complete_fn=fake, force=False,
    )
    assert r1.get("cache_hit") is False
    assert calls["n"] == 1
    r2 = run_discipline_with_cache(
        work="dw", seq=2, prose="纪律测正文", complete_fn=fake, force=False,
    )
    assert r2.get("cache_hit") is True
    assert calls["n"] == 1  # 未再调模型
    c = get_cached_analysis("dw", 2, "纪律测正文")
    assert c and c.get("discipline") is not None


def test_prompt_contains_bible_and_wrapper():
    pr = build_unified_chapter_prompt(
        "雨中推门。",
        known_character_names=["沈拾灯"],
        world_rule_names=["不渡夜魂"],
        motif_names=["灯与债"],
        promise_items=[{"id": "p1", "text": "合灯夜"}],
    )
    assert "沈拾灯" in pr and "不渡夜魂" in pr and "灯与债" in pr
    assert '"knowledge"' in pr and '"settings"' in pr

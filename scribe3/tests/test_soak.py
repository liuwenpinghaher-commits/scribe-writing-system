"""浸泡前置 · 渲染前产出情感曲线种子词(意识流丢弃)。用 fake complete_fn,不连网。"""
from scribe3.scenario import luanshi_leak_world
from scribe3.soak import build_soak_prompt, parse_soak, soak


def test_soak_prompt_in_focalizer_voice_and_limited():
    w = luanshi_leak_world()
    p = build_soak_prompt(w, 1, "role:老道")
    assert "流云观皂衣道士" in p, "soak 以视角角色身份"
    assert "治眼" not in p, "soak 也受限知约束:不含他人私密"


def test_parse_soak_extracts_cot():
    reply = '随便一段意识流……{"emotion_arc":"戒备→贪念","turn":"看清那颗丹时","seed_words":["潮","锈","贪"]}'
    r = parse_soak(reply)
    assert r["emotion_arc"] == "戒备→贪念"
    assert r["turn"] == "看清那颗丹时"
    assert r["seed_words"] == ["潮", "锈", "贪"]


def test_parse_soak_bad_json_safe():
    r = parse_soak("模型只吐了散文没有 JSON")
    assert r == {"emotion_arc": "", "turn": "", "seed_words": []}


def test_soak_calls_model():
    w = luanshi_leak_world()
    def fake(prompt, **kw):
        return '{"emotion_arc":"冷→锐","turn":"拔刀","seed_words":["铁","血"]}'
    r = soak(w, 1, "role:老道", fake)
    assert r["seed_words"] == ["铁", "血"]

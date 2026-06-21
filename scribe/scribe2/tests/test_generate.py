"""写作层移植 Phase3:生成管线(上下文+续写prompt+可注入LLM)+ 确定性记忆 rollup(防漂移)。"""
from scribe2.domain import Domain
from scribe2.store import Store
from scribe2.generate import generate_continue, rollup_global, build_chapter_prompt


def _dom(db):
    d = Domain(Store(db)); d.s.init_schema()
    return d


def test_generate_continue_prompt_carries_context_instruction_target(db):
    d = _dom(db)
    w = d.create_work("书")
    d.set_intent(w, reader_feeling="苍凉克制的宿命感")
    d.add_character(w, "渡叔", motivation="守渡四十年", voice="极静带谶语")
    captured = {}

    def fake_complete(prompt: str) -> str:
        captured["p"] = prompt
        return "渡叔立于船头,独眼望着浊浪。"

    out = generate_continue(d, w, seq=1, instruction="写渡叔深夜独自夜渡",
                            complete_fn=fake_complete, target=600)
    assert out == "渡叔立于船头,独眼望着浊浪。"
    assert "苍凉克制的宿命感" in captured["p"]   # _writing_context 注入
    assert "极静带谶语" in captured["p"]          # 角色声音
    assert "写渡叔深夜独自夜渡" in captured["p"]   # instruction(可 steer)
    assert "600" in captured["p"]                  # target 长度


def test_continue_prompt_uses_prev_for_coherence():
    p = build_chapter_prompt("【北极星】X", seq=3, instruction="本节要写A",
                             prev="前文:渡船已到河心。", target=700)
    assert "本节要写A" in p and "渡船已到河心" in p and "700" in p and "X" in p


def test_deterministic_global_rollup_no_drift(db):
    # 关键:全局记忆=章梗概确定性拼接,不经 LLM 压缩 → 根除旧底座的身份血缘漂移
    d = _dom(db)
    w = d.create_work("书")
    d.save_chapter_memory(w, 1, "阿砚是苏清湄的孙辈")
    d.save_chapter_memory(w, 2, "渡叔守渡四十年")
    g = rollup_global(d, w)
    assert "阿砚是苏清湄的孙辈" in g    # 原文保真,绝不被压成"独子"
    assert "渡叔守渡四十年" in g
    assert d.get_global_memory(w) == g  # 已落库

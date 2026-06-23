"""纵切片 · 渲染层 TDD —— 范式证明的后半:**私密物理上进不了 prompt。**

这是整个重构的 load-bearing 断言:限知不靠事后判官,靠渲染前的知识帧投影。
老道视角的 prompt 里【不可能】出现焦三的私密动机,因为它不在老道的帧里。
"""
from scribe3.scenario import luanshi_leak_world
from scribe3.render import build_render_prompt, render


def test_render_prompt_cannot_contain_others_secret():
    """范式证明:老道视角 prompt 不含焦三私密;焦三视角则含(他知道自己的动机)。"""
    w = luanshi_leak_world()
    p_laodao = build_render_prompt(w, 1, "role:老道")
    assert "治眼" not in p_laodao, "老道视角 prompt 绝不能含焦三私密动机"
    assert "攒钱给老娘" not in p_laodao
    p_jiaosan = build_render_prompt(w, 1, "role:焦三")
    assert "治眼" in p_jiaosan, "焦三视角应含自己的动机"


def test_render_prompt_has_focalizer_and_event():
    w = luanshi_leak_world()
    p = build_render_prompt(w, 1, "role:老道")
    assert "流云观皂衣道士" in p, "prompt 标明视角角色"
    assert "对峙" in p, "prompt 含本章要渲染的事件"
    assert "暴雨" in p, "公开事实在帧内,应注入"


def test_render_prompt_forbids_meta_narration():
    """真机暴露:模型会回'已完成…我写了…'元叙述而非正文。prompt 须明令直接吐正文。"""
    w = luanshi_leak_world()
    p = build_render_prompt(w, 1, "role:老道")
    assert "直接输出" in p and "正文" in p, "须明令直接输出小说正文"
    assert "元叙述" in p or "不要复述" in p or "不要说明" in p, "须禁止元叙述/复述指令"


def test_render_feeds_clean_prompt_to_model():
    """render() 把(限知后的)prompt 喂给注入的 complete_fn;不连网即可验证。"""
    w = luanshi_leak_world()
    captured = {}

    def fake_complete(prompt, **kw):
        captured["prompt"] = prompt
        return "雨砸在乱葬岗的烂泥上。皂衣道士拦住去路,只问那颗丹。"

    out = render(w, 1, "role:老道", complete_fn=fake_complete, soak=False)
    assert "皂衣道士" in out
    assert "治眼" not in captured["prompt"], "喂给模型的 prompt 不含泄露"


from scribe3.craft import build_craft_block


def test_prompt_injects_craft_block():
    w = luanshi_leak_world()
    p = build_render_prompt(w, 1, "role:老道", craft_block=build_craft_block())
    assert "写作引擎" in p and "身体先行" in p, "渲染 prompt 含引擎层 craft"


def test_prompt_injects_soak_seeds():
    w = luanshi_leak_world()
    sr = {"emotion_arc": "戒备→贪念", "turn": "看清那颗丹", "seed_words": ["潮", "锈", "贪"]}
    p = build_render_prompt(w, 1, "role:老道", soak_result=sr)
    assert "情感曲线" in p and "戒备→贪念" in p and "潮" in p


def test_craft_does_not_break_limited_pov():
    """load-bearing:craft/soak 注入后,老道视角仍不含焦三私密。"""
    w = luanshi_leak_world()
    sr = {"emotion_arc": "", "turn": "", "seed_words": ["雨", "刀"]}
    p = build_render_prompt(w, 1, "role:老道", craft_block=build_craft_block(), soak_result=sr)
    assert "治眼" not in p and "攒钱给老娘" not in p


def test_prompt_injects_voice():
    w = luanshi_leak_world()
    voice = {"free": "胡话连篇", "pressure": "声细如蚊", "relation": "对娘软", "narration": "冷眼看世道"}
    p = build_render_prompt(w, 1, "role:老道", voice=voice)
    assert "你" in p and "声音" in p
    assert "声细如蚊" in p and "冷眼看世道" in p


def test_voice_does_not_break_pov():
    """load-bearing:注入声音后,老道视角仍不含焦三私密。"""
    w = luanshi_leak_world()
    voice = {"narration": "皂衣道士的冷眼"}
    p = build_render_prompt(w, 1, "role:老道", voice=voice)
    assert "治眼" not in p and "攒钱给老娘" not in p


def test_render_runs_soak_then_renders():
    """soak=True:complete_fn 先被 soak 调一次、再被渲染调一次;最终输出是渲染结果。"""
    w = luanshi_leak_world()
    calls = []
    def fake(prompt, **kw):
        calls.append(prompt)
        if "写前浸泡一次" in prompt:   # soak prompt 独有串(渲染 prompt 的 craft 引擎也叫'浸泡',故不能用'浸泡'判别)
            return '{"emotion_arc":"冷→锐","turn":"拔刀","seed_words":["铁"]}'
        return "雨砸在乱葬岗的烂泥上。"
    out = render(w, 1, "role:老道", complete_fn=fake, soak=True)
    assert out == "雨砸在乱葬岗的烂泥上。"
    assert len(calls) == 2 and "铁" in calls[1], "soak 种子词进了渲染 prompt"

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


# --- 非线性叙事:story_at(事件) / frame_at(知识帧) ---
from scribe3.ontology import World, Entity, Fact, KnowledgeEdge, Event


def test_linear_default_unchanged():
    """默认 story_at=frame_at=chapter → 与显式传相等参数完全相同(线性零回归)。"""
    w = luanshi_leak_world()
    a = build_render_prompt(w, 1, "role:老道")
    b = build_render_prompt(w, 1, "role:老道", story_at=1, frame_at=1)
    assert a == b


def test_flashback_renders_past_events():
    """story_at 控制事件源:第10叙事章渲染 story_at=1 → 含第1章事件;默认(story_at=10)则无。"""
    w = luanshi_leak_world()
    p_flash = build_render_prompt(w, 10, "role:老道", story_at=1)
    assert "对峙" in p_flash, "story_at=1 应渲染第1章事件"
    p_linear10 = build_render_prompt(w, 10, "role:老道")
    assert "对峙" not in p_linear10, "第10章无事件(events_at(10) 空)"


def test_flashback_label():
    """story_at≠chapter 时 prompt 含插叙标注;线性时不含。"""
    w = luanshi_leak_world()
    p_flash = build_render_prompt(w, 10, "role:老道", story_at=1)
    assert "插叙" in p_flash or "闪回" in p_flash
    p_linear = build_render_prompt(w, 1, "role:老道")
    assert "插叙" not in p_linear and "闪回" not in p_linear


def test_flashback_does_not_break_pov():
    """load-bearing:插叙第1章,frame_at 默认=1,老道帧不含焦三私密(限知红利免费)。"""
    w = luanshi_leak_world()
    p = build_render_prompt(w, 10, "role:老道", story_at=1)
    assert "治眼" not in p and "攒钱给老娘" not in p


def _timevarying_world() -> World:
    """甲在第5章才学到'晚知'真相 → frame(甲,1) 不含、frame(甲,10) 含。用于区分沉浸/回忆。"""
    w = World()
    w.add_entity(Entity("role:甲", "character", "甲"))
    w.add_fact(Fact("fact:晚知", "role:甲", "认知", "后来才懂的真相", valid_from=1))
    w.add_knowledge(KnowledgeEdge("role:甲", "fact:晚知", since_chapter=5, acquired_via="learned"))
    w.add_event(Event("ev:早", "旧事", participants={"SUBJ": "role:甲"}, story_time=1))
    return w


def test_immersive_default_frame():
    """沉浸式(frame_at 默认=story_at=1):甲第1章还不知'晚知'(since=5)。"""
    w = _timevarying_world()
    p = build_render_prompt(w, 10, "role:甲", story_at=1)
    assert "后来才懂的真相" not in p, "沉浸式:frame_at=1,甲尚未知晓"


def test_recall_mode_present_frame():
    """回忆式(显式 frame_at=10):甲已知'晚知',带现在认知回忆过去。"""
    w = _timevarying_world()
    p = build_render_prompt(w, 10, "role:甲", story_at=1, frame_at=10)
    assert "后来才懂的真相" in p, "回忆式:frame_at=10,甲已知晓"


def test_render_flashback_passes_story_at():
    """render 把 story_at/frame_at 透传给 build_render_prompt:第10叙事章渲染第1章事件。"""
    w = luanshi_leak_world()
    captured = {}

    def fake(prompt, **kw):
        captured["prompt"] = prompt
        return "雨砸在乱葬岗的烂泥上。"

    render(w, 10, "role:老道", complete_fn=fake, soak=False, story_at=1)
    assert "对峙" in captured["prompt"], "render 应透传 story_at=1 → 渲染第1章事件"
    assert "插叙" in captured["prompt"] or "闪回" in captured["prompt"], "应带插叙标注"
    assert "治眼" not in captured["prompt"], "限知不破:frame_at=1 老道帧无焦三私密"

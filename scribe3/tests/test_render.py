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


def test_render_feeds_clean_prompt_to_model():
    """render() 把(限知后的)prompt 喂给注入的 complete_fn;不连网即可验证。"""
    w = luanshi_leak_world()
    captured = {}

    def fake_complete(prompt, **kw):
        captured["prompt"] = prompt
        return "雨砸在乱葬岗的烂泥上。皂衣道士拦住去路,只问那颗丹。"

    out = render(w, 1, "role:老道", complete_fn=fake_complete)
    assert "皂衣道士" in out
    assert "治眼" not in captured["prompt"], "喂给模型的 prompt 不含泄露"

"""In-memory tests for shipped build_ctx guide slots. No Surreal."""
from __future__ import annotations

from scribe3.ontology import Fact
from scribe3.playbook.context import build_ctx, strip_seed_pad, synopsis_is_generic
from scribe3.playbook.prompts import duty_generate, duty_judge
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.structural import check_draft_struct, metaphor_per_800


PAD = "此句只为把设定写够，说明处境、代价和不能拆穿的事。"


class _World:
    def __init__(self):
        self._intent = {
            "north_star": "读完要先冷后烫，还想翻下一页。",
            "reader_feeling": "先冷后烫",
            "emotional_arc": "从隐瞒到按回",
            "imagery": "黑屋",
        }
        self._vols = [{"id": "cage", "title": "囚笼", "intro": "大遮蔽内，觉醒到华山成核。"}]
        self._lite = [
            {"seq": 1, "title": "华山成核", "synopsis": "华山北峰当夜必须决定交碎片还是按回。",
             "volume": "cage", "focalizer": "role:柳岸青"},
            {"seq": 2, "title": "四十二度", "synopsis": "体温被写成标价后决定是否切断观测。",
             "volume": "cage", "focalizer": "role:柳岸青"},
        ]
        self._facts = [
            Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1, secret=False),
            Fact("fact:坐标密", "role:柳岸青", "秘密", "看不见场核坐标", 1, secret=True),
        ]
        self._rules = [{"name": "场核是拓扑锚", "cost": "拔核等于真空衰变"}]
        self._chars = [{"name": "柳岸青", "gender": "男"}]

    def get_intent(self):
        return dict(self._intent)

    def list_volumes(self):
        return list(self._vols)

    def chapters_lite(self):
        return [dict(r) for r in self._lite]

    def facts_at(self, chapter):
        return list(self._facts)

    def list_world_rules(self, category=None):
        return list(self._rules)

    def list_characters(self):
        return list(self._chars)

    def recent_proses(self, before_seq=None, k=1, **_kw):
        return [{"seq": 1, "prose": "墙比他想象中湿。" * 20}] if int(before_seq or 0) > 1 else []


class _Both(_World):
    def __init__(self):
        super().__init__()
        self._frozen = {
            ("duty_card", 1): {"must_happen": "按回碎片", "bill": "一层皮"},
            ("chapter_play", 1): {"text": "柳岸青把掌心按在潮砖上，砖缝返上来的水往指甲缝里钻。"},
            ("chapter_contract", 1): {"fields": {"hook": {"quote": "等着人来兑现"}}},
            ("chapter_state", 1): {"characters": [{"name": "柳岸青", "gender": "男"}]},
            ("chapter_deduce", 1): {
                "characters": [{"id": "role:柳岸青", "known": "砖是湿的", "believed": "还能按回去"}]
            },
        }

    def get_frozen(self, table, seq):
        return self._frozen.get((table, int(seq)))


class _FrozenOnly:
    def get_frozen(self, table, seq):
        return _Both().get_frozen(table, seq)


def test_same_object_slots_are_filled():
    st = _Both()
    ctx = build_ctx(st, 2, focalizer="role:柳岸青")
    assert "囚笼" in ctx["volume_outline"]
    assert "华山成核" in ctx["volume_outline"] or "大遮蔽" in ctx["volume_outline"]
    assert ctx["north_star"].startswith("读完要先冷后烫")
    assert "四十二度" in ctx["chapter_duty"]
    assert "按回碎片" in ctx["recent_duty_summary"]
    assert "潮砖" in ctx["recent_scene_summary"]
    assert "四十二度不是病是标价" in ctx["codex_recall"]
    assert "看不见场核坐标" not in ctx["codex_recall"]
    assert "请点名" not in ctx["codex_recall"]
    assert ctx["prev_hook_quote"] == "等着人来兑现"
    d = duty_generate(ctx)
    assert "（无）" not in d.split("卷纲：", 1)[1][:80]
    assert "【本章责】" in d
    assert "（无）" not in d.split("【本章责】", 1)[1].split("\n", 1)[0]


def test_split_world_must_not_fake_frozen():
    world = _World()
    assert not hasattr(world, "get_frozen")
    frozen = _FrozenOnly()
    ctx = build_ctx(world, 2, focalizer="role:柳岸青", playbook=frozen)
    assert "囚笼" in ctx["volume_outline"]
    assert "按回碎片" in ctx["recent_duty_summary"]
    assert ctx["prev_hook_quote"] == "等着人来兑现"
    assert "四十二度不是病是标价" in ctx["codex_recall"]


def test_codex_recall_does_not_alphabet_pad_unrelated():
    world = _World()
    world._facts = [
        Fact("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", 1, secret=False),
        Fact("fact:路人", "role:赵三", "身份", "路人甲不该被字母序塞进来", 1, secret=False),
    ]
    ctx = build_ctx(world, 1, focalizer="role:柳岸青", playbook=_FrozenOnly())
    assert "四十二度不是病是标价" in ctx["codex_recall"]
    assert "路人甲" not in ctx["codex_recall"]
    assert "看不见场核坐标" not in ctx["codex_recall"]


def test_fact_dataclass_and_dict_both_filter_secret():
    world = _World()
    world._facts = [
        {"entity_id": "role:柳岸青", "attribute": "身体", "value": "四十二度不是病是标价", "secret": False},
        {"entity_id": "role:柳岸青", "attribute": "秘密", "value": "看不见场核坐标", "secret": True},
    ]
    ctx = build_ctx(world, 1, playbook=_FrozenOnly())
    assert "四十二度不是病是标价" in ctx["codex_recall"]
    assert "看不见场核坐标" not in ctx["codex_recall"]


def test_ten_identical_padded_synopses_omit_chapter_duty_body():
    world = _World()
    syn = "华山北峰当夜必须决定交碎片还是按回。" + PAD + PAD
    world._lite = [
        {"seq": i, "title": f"第{i}章", "synopsis": syn, "volume": "cage", "focalizer": "role:柳岸青"}
        for i in range(1, 11)
    ]
    ctx = build_ctx(world, 1, playbook=_FrozenOnly())
    assert "华山北峰当夜必须决定交碎片还是按回" not in ctx["chapter_duty"]
    assert "第1章" in ctx["chapter_duty"] or "这一章" in ctx["chapter_duty"]


def test_three_chapter_two_matching_keeps_unique_third():
    world = _World()
    same = "同一夜必须按回碎片。"
    world._lite = [
        {"seq": 1, "title": "一", "synopsis": same, "volume": "cage"},
        {"seq": 2, "title": "二", "synopsis": same, "volume": "cage"},
        {"seq": 3, "title": "三", "synopsis": "体温被写成标价后决定是否切断观测。", "volume": "cage"},
    ]
    ctx = build_ctx(world, 3, playbook=_FrozenOnly())
    assert "切断观测" in ctx["chapter_duty"]
    assert not synopsis_is_generic(world._lite, 3, world._lite[2]["synopsis"])


def test_strip_pad_and_version():
    assert PAD not in strip_seed_pad("真种子。" + PAD + PAD)
    assert PLAYBOOK_VERSION == "playbook.3.2.8"
    assert "【本章责】" in duty_generate({})
    assert "【本章责】" in duty_judge({})
    assert metaphor_per_800("像火。") >= 0
    play = "完全另一场戏，没有盒子。" * 40
    draft = ("「按回去。」他说。\n他按住盒子，袖口发烫。沈烛把任务书推过来。\n" * 80)
    hit = check_draft_struct(draft, play_text=play)
    assert hit.get("code") != "changed_threshold"


def test_voice_anchor_still_not_in_context_module():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "playbook/context.py").read_text(encoding="utf-8")
    assert "voice_anchor_block" not in src


def test_guide_fail_only_on_throw_not_natural_empty():
    from scribe3.playbook.prompts import draft_generate
    from pathlib import Path
    ctx = build_ctx(_World(), 1, playbook=_FrozenOnly())
    assert ctx.get("_guide_fail") == []
    assert not ctx.get("recent_duty_summary")
    assert not ctx.get("prev_prose_tail")

    class BoomLite(_World):
        def chapters_lite(self):
            raise RuntimeError("lite boom")

    boom_lite = build_ctx(BoomLite(), 1, playbook=_FrozenOnly())
    assert "chapters_lite" in (boom_lite.get("_guide_fail") or [])

    import scribe3.playbook.context as ctxmod
    orig = ctxmod.playbook_volume_outline
    ctxmod.playbook_volume_outline = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("volume boom"))
    try:
        boom = build_ctx(_World(), 1, playbook=_FrozenOnly())
        assert "volume_outline" in (boom.get("_guide_fail") or [])
        assert boom.get("volume_outline") == ""
        src_ctx = (Path(__file__).resolve().parents[1] / "playbook/context.py").read_text()
        assert "soft_fail" in src_ctx
    finally:
        ctxmod.playbook_volume_outline = orig

    src = Path(__file__).resolve().parents[1] / "playbook/prompts.py"
    text = src.read_text(encoding="utf-8")
    assert "2000-4000" in text
    assert "连续 8 个字" not in draft_generate({})
    assert PLAYBOOK_VERSION == "playbook.3.2.8"


def test_extra_can_override_guide_fail():
    ctx = build_ctx(_World(), 1, extra={"_guide_fail": ["north_star"]}, playbook=_FrozenOnly())
    assert ctx["_guide_fail"] == ["north_star"]

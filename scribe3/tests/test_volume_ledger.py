"""本卷台账近窗：内存夹具，不启 Surreal。"""
from __future__ import annotations

import inspect
from pathlib import Path

from scribe3.feature_flags import flag_truthy, get_all_flags
from scribe3.playbook.context import (
    assemble_volume_ledger,
    build_ctx,
    playbook_volume_ledger,
)
from scribe3.playbook.prompts import duty_generate, duty_judge, play_generate, play_judge
from scribe3.playbook.quote import PLAYBOOK_VERSION

from scribe3.tests.test_playbook_context_guides import _FrozenOnly, _World


def _four_cage(world: _World) -> None:
    world._lite = [
        {"seq": 1, "title": "华山成核", "synopsis": "华山北峰当夜必须决定交碎片还是按回。",
         "volume": "cage", "has_prose": True, "focalizer": "role:柳岸青"},
        {"seq": 2, "title": "四十二度", "synopsis": "体温被写成标价后决定是否切断观测。",
         "volume": "cage", "focalizer": "role:柳岸青"},
        {"seq": 3, "title": "金縢裂纹", "synopsis": "金縢被点名之后他必须决定交不交。",
         "volume": "cage", "focalizer": "role:柳岸青"},
        {"seq": 4, "title": "灭活边缘", "synopsis": "灭活窗口只剩三分钟，他必须按或不按。",
         "volume": "cage", "focalizer": "role:柳岸青"},
    ]


def test_flag_registered_default_on():
    flags = get_all_flags()
    assert "SCRIBE3_VOLUME_LEDGER" in flags
    assert flags["SCRIBE3_VOLUME_LEDGER"]["default"] == "1"
    assert flag_truthy("SCRIBE3_VOLUME_LEDGER") is True


def test_ledger_lists_later_chapters_for_tonight():
    world = _World()
    _four_cage(world)
    ctx = build_ctx(world, 1, playbook=_FrozenOnly())
    text = ctx["volume_ledger"]
    assert "华山成核" in text
    assert "今晚" in text
    assert "四十二度" in text
    assert "金縢裂纹" in text
    assert "灭活边缘" in text
    assert "还没办" in text
    assert "tonight" not in text
    assert "later" not in text
    assert "done" not in text
    assert PLAYBOOK_VERSION == "playbook.3.2.17"


def test_ledger_not_via_compact_volume_intro():
    src = inspect.getsource(playbook_volume_ledger)
    src2 = inspect.getsource(assemble_volume_ledger)
    assert "injection_compact" not in src
    assert "injection_compact" not in src2
    from scribe3.injection_compact import compact_volume_intro
    world = _World()
    _four_cage(world)
    text = playbook_volume_ledger(world, _FrozenOnly(), 1, world._lite)
    intro = world._vols[0]["intro"]
    compacted = compact_volume_intro(intro)
    assert text
    assert text != compacted
    assert "四十二度" in text


def test_duty_and_play_prompts_carry_later_titles():
    world = _World()
    _four_cage(world)
    ctx = build_ctx(world, 1, playbook=_FrozenOnly())
    d = duty_generate(ctx)
    assert "【本卷还要办的】" in d
    assert "今晚只办这一章该办的那一笔" in d
    assert "金縢裂纹" in d
    j = duty_judge({**ctx, "duty_json": "{}"})
    assert "八问" in j
    assert "金縢裂纹" in j
    assert "灭活边缘" in j
    p = play_generate({**ctx, "duty": {"must_happen": "按碎片"}})
    assert "四十二度" in p
    pj = play_judge({**ctx, "duty_json": "{}", "play_text": "戏"})
    assert "十二问" in pj
    assert "灭活边缘" in pj


def test_unassigned_volume_is_empty_not_fail():
    world = _World()
    world._lite = [
        {"seq": 1, "title": "一", "synopsis": "独自办一件事。"},
        {"seq": 2, "title": "二", "synopsis": "另一件还没办。"},
    ]
    ctx = build_ctx(world, 1, playbook=_FrozenOnly())
    assert ctx.get("volume_ledger") == ""
    assert "volume_ledger" not in (ctx.get("_guide_fail") or [])
    assert ctx.get("_volume_ledger_skip") == "unassigned_or_empty"


def test_single_chapter_volume_skips():
    world = _World()
    world._lite = [
        {"seq": 1, "title": "华山成核", "synopsis": "北峰按碎片。", "volume": "cage"},
    ]
    ctx = build_ctx(world, 1, playbook=_FrozenOnly())
    assert ctx.get("volume_ledger") == ""
    assert ctx.get("_volume_ledger_skip") == "single_chapter"
    assert "volume_ledger" not in (ctx.get("_guide_fail") or [])


def test_context_module_does_not_import_compact():
    src = (Path(__file__).resolve().parents[1] / "playbook/context.py").read_text(encoding="utf-8")
    assert "from scribe3.injection_compact" not in src
    assert "import compact_volume_intro" not in src

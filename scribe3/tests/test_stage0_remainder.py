"""Stage 0 余项：铺垫豁免、铁律双锚、hint 不累积、digest 200、定稿记账。"""
from __future__ import annotations

from scribe3.codex_digest import _VALUE_MAX, digest_payloads
from scribe3.playbook.pipeline import _settled_note, draft_struct_hint
from scribe3.playbook.prompts import (
    IRON_RULES,
    PACE_EXEMPT,
    duty_generate,
    duty_judge,
    draft_generate,
    draft_judge,
    final_generate,
    final_judge,
    play_generate,
    play_judge,
)
from scribe3.playbook.quote import PLAYBOOK_VERSION


def test_version_324():
    assert PLAYBOOK_VERSION == "playbook.3.2.4"
    assert PACE_EXEMPT in duty_judge({"seq": 1})
    assert PACE_EXEMPT in play_judge({"seq": 1})
    assert PACE_EXEMPT in draft_judge({})
    assert PACE_EXEMPT in final_judge({})


def test_iron_rules_dual_anchor_in_generate():
    ctx = {"seq": 1, "forbidden_reveal": ["炉认主"], "secret_list": ["炉认主"]}
    for fn in (duty_generate, play_generate, draft_generate, final_generate):
        text = fn(ctx)
        assert text.count("今晚还不能拆穿") >= 2
        assert IRON_RULES.split("\n")[0] in text
        assert text.count("今晚钉住") == 1
        assert "写完再核一次" in text


def test_draft_hint_last_round_only():
    first = draft_struct_hint(["draft_len"], last_message="写够")
    second = draft_struct_hint(["draft_copy_play"], last_message="别搬戏")
    assert "写够" not in second or "别搬戏" in second
    only = draft_struct_hint(["draft_copy_play"], last_message="别搬戏")
    assert "draft_len" not in only
    assert first


def test_digest_cap_and_key_fields():
    assert _VALUE_MAX == 200
    rows = digest_payloads("character", "role:柳岸青", {
        "name": "柳岸青",
        "gender": "男",
        "appearance": "右腕内嵌断指" * 40,
        "backstory_secret": True,
        "fear": "被观测",
    })
    assert all(len(r["value"]) <= 201 for r in rows)
    blob = " ".join(r["value"] for r in rows)
    assert "柳岸青" in blob
    assert "男" in blob


def test_settled_note_from_duty():
    note = _settled_note(
        {"must_happen": "把碎片按回裂口"},
        {"fields": {"decision": {"text": "按了进去"}}},
        1,
    )
    assert note.startswith("第1章办成了")
    assert "按回裂口" in note

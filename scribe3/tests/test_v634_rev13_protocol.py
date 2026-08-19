"""rev.13 协议与 Wave C 尺子必须打到已上线函数，禁止对照实现。"""
from __future__ import annotations

from pathlib import Path

from scribe3.playbook.judge import _normalize
from scribe3.playbook.quality_metrics import dialogue_ratio, measure_chapter, metaphor_per_800
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.structural import check_draft_struct, check_final_last_mile


ROOT = Path(__file__).resolve().parents[2]
PROTO = ROOT / "docs" / "e2e-director-journey-v634-true-chat-full-capability.md"
WANJIE = ROOT / "docs" / "worlds" / "wanjie-probability-war-v7.md"


def test_protocol_is_rev13_and_wave_c():
    text = PROTO.read_text(encoding="utf-8")
    assert "v6.3.4 rev.13" in text
    assert "文件名" not in text or "e2e-director-journey-v634-true-chat-full-capability.md" in text
    assert "总 PASS ⇔ Wave A ∧ Wave B ∧ Wave C" in text or "Wave A ∧ Wave B ∧ Wave C" in text
    assert "ShouldRate" in text and "0.80" in text
    assert "Gate 0" in text
    assert "07-trace-reconciliation.md" in text
    assert "code=`draft_copy_play`" in text or "code=draft_copy_play" in text or "draft_copy_play" in text
    assert "duty→design(play+contract)→deduce→draft→final" in text
    assert "层法官放行" in text
    assert "窗口版本冻结" in text
    assert "13 槽" in text


def test_wanjie_ssot_five_layer_not_outline():
    text = WANJIE.read_text(encoding="utf-8")
    assert "rev.13" in text
    assert "duty_card + chapter_play" in text or "duty_card" in text
    assert "13 槽" in text
    assert "第 1 章五层金样" in text


def test_playbook2_and_d1_code_is_draft_copy_play():
    assert PLAYBOOK_VERSION == "playbook.2"
    play = "沈烛若把场核碎片按回胸口，四十二度顺着袖口往上爬。" * 20
    hit = check_draft_struct(play + "他又看了一眼。" * 8, play_text=play)
    assert hit["code"] == "draft_copy_play"
    assert _normalize({"verdict": "???", "answers": []})["verdict"] == "needs_human"
    prose = ("他按回碎片，袖口发烫。" * 120) + "上一章末他就数过。"
    assert check_final_last_mile(prose)["code"] == "meta_chapter_ref"


def test_dialogue_and_metaphor_metrics_use_real_text():
    talk = "「你按回去。」沈烛说。\n「不交。」柳岸青说。\n"
    body = talk + "他按住碎片。" * 20
    assert dialogue_ratio(body) > 0.1
    dense = "像火。仿佛夜。似的冷。" * 5
    assert metaphor_per_800(dense) > 1.0


class _Mem:
    def __init__(self):
        self._f = {}

    def get_frozen(self, table, seq):
        return self._f.get((table, int(seq)))

    def get_chapter(self, seq):
        return {"prose": (self.get_frozen("chapter_draft", seq) or {}).get("text") or ""}


def test_measure_chapter_fails_copy_and_solo_cast():
    st = _Mem()
    play = "交出去，娘就有一线生机。" * 30
    st._f[("chapter_play", 1)] = {"text": play}
    st._f[("chapter_draft", 1)] = {"text": play}
    st._f[("chapter_contract", 1)] = {"fields": {"cost": None, "hook": {"quote": "钩"}}, "beats": []}
    st._f[("duty_card", 1)] = {"who": ["柳岸青"]}
    row = measure_chapter(st, 1)
    assert row["ok"] is False
    assert row["who_n"] == 1
    assert row["overlap"] > 0.15
    assert row["cost_ok"] is False

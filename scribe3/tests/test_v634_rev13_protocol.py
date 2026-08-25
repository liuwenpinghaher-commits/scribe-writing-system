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
    assert "主角代词跨章一致" in text
    assert "关键物件位置连续" in text or "关键物件位置跨章连续" in text
    assert "到期 open_loops 回响" in text or "到期悬念全部回响" in text
    assert "chapter_state 产物存在且保真" in text
    assert "连续性回读" in text
    assert "D9 代词翻转" in text
    assert "D10 状态造假" in text
    assert "D11 悬念超期" in text
    assert "D12 意象域断裂" in text
    assert "D13" in text
    assert "D14" in text
    assert "pov_consistency" in text
    assert "playbook.3.1" in text
    assert "playbook.3.2" in text
    assert "playbook.3.2.1" in text
    assert "rev.13.2" in text
    assert "rev.13.3" in text
    assert "rev.13.4" in text
    assert "rev.13.4.1" in text
    assert "rev.13.4.2" in text
    assert "D15" in text
    assert "syntax_tics" in text
    assert "book_8777aad8" in text
    assert "冻稿正文" in text
    assert "定稿" in text
    assert "引号行字数比" in text
    assert "book_be4343e4" in text
    assert "GET /chapters/{seq}/state" in text
    assert "06-defect-ledger.md" in text
    assert "叙事人称跨章一致" in text
    assert "08-chapter-states.md" in text
    assert "09-state-reconciliation.md" in text
    assert "backfill=true" in text
    assert "simile_density" in text
    assert "≤15%" in text
    assert "≥15%" in text
    assert "1/800" in text or "≤1 个/800" in text
    assert "0.80" in text


def test_wanjie_ssot_five_layer_not_outline():
    text = WANJIE.read_text(encoding="utf-8")
    assert "rev.13" in text
    assert "duty_card + chapter_play" in text or "duty_card" in text
    assert "13 槽" in text
    assert "第 1 章五层金样" in text


def test_gate0_imports_continuity_adversaries():
    from scribe3.tools.v634_smoke import smoke_imports
    rows = {n: (ok, detail) for n, ok, detail in smoke_imports()}
    assert rows["playbook_version"][0] is True
    assert rows["gender_pronoun_gate"][0] is True
    assert rows["state_quote_gate"][0] is True
    assert rows["simile_density_gate"][0] is True
    assert rows["state_quote_pass"][0] is True
    assert rows["d13_pov_gate"][0] is True
    assert rows["d13_draft_pov"][0] is True
    assert rows["dialogue_floor_gate"][0] is True
    assert rows["thin_unlike_is"][0] is True
    assert rows["d14_residue"][0] is True
    assert rows["d15_syntax_tics"][0] is True
    assert rows["craft_rhythm"][0] is True
    assert rows["play_is_design"][0] is True
    assert rows["duty_chapter_duty_slot"][0] is True


def test_playbook2_and_d1_code_is_draft_copy_play():
    assert PLAYBOOK_VERSION == "playbook.3.2.19"
    play = "沈烛若把场核碎片按回胸口，四十二度顺着袖口往上爬。" * 80
    hit = check_draft_struct(play + "他又看了一眼裂口。" * 20, play_text=play)
    assert hit["code"] == "draft_copy_play"
    assert _normalize({"verdict": "???", "answers": []})["verdict"] == "needs_human"
    prose = ("他按回碎片，袖口发烫。" * 120) + "上一章末他就数过。"
    assert check_final_last_mile(prose)["code"] == "meta_chapter_ref"


def test_dialogue_and_metaphor_metrics_use_real_text():
    talk = "「你按回去。」沈烛说。\n「不交。」柳岸青说。\n"
    body = talk + "他按住碎片。" * 20
    assert dialogue_ratio(body) > 0.1
    curly = "“十八个月。”沈烛说，“中途不返航。”\n他看着盒子。\n"
    assert dialogue_ratio(curly) > 0.4
    dense = "像火。仿佛夜。似的冷。" * 5
    assert metaphor_per_800(dense) > 1.0


class _Mem:
    def __init__(self):
        self._f = {}

    def get_frozen(self, table, seq):
        return self._f.get((table, int(seq)))

    def get_chapter(self, seq):
        return {"prose": (self.get_frozen("chapter_draft", seq) or {}).get("text") or ""}


def test_hooks_do_not_paint_failed_ok():
    src = (ROOT / "scribe3" / "pipeline_trace_hooks.py").read_text(encoding="utf-8")
    assert "链异常但产物已落库" not in src
    assert "status = \"ok\"" not in src.split("def finish_failed")[-1].split("def emit_gate_spans")[0]


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

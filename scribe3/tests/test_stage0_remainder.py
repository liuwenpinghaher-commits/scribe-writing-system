"""Stage 0 余项：铺垫豁免、铁律双锚、hint 不累积、digest 200、定稿记账。"""
from __future__ import annotations

from scribe3.codex_digest import _VALUE_MAX, digest_payloads
from scribe3.playbook.pipeline import _settled_note, draft_struct_hint
from scribe3.llm_temps import TEMP_DESIGN, TEMP_DRAFT, TEMP_JUDGE, TEMP_PLAN_MAX
from scribe3.playbook.prompts import (
    IRON_RULES,
    PACE_EXEMPT,
    VOLUME_LEDGER_DISCIPLINE,
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
    assert PLAYBOOK_VERSION == "playbook.3.2.20"
    assert PACE_EXEMPT in duty_judge({"seq": 1})
    assert PACE_EXEMPT in play_judge({"seq": 1})
    assert PACE_EXEMPT in draft_judge({})
    assert PACE_EXEMPT in final_judge({})


def test_ledger_forbids_foreshadow_in_prose():
    assert "账本" in VOLUME_LEDGER_DISCIPLINE
    assert "不许用任何形式预告" in VOLUME_LEDGER_DISCIPLINE
    d = duty_generate({"seq": 1, "volume_ledger": "第2章《四十二度》〔还没办〕"})
    assert "账本" in d
    assert "酝酿情绪" in PACE_EXEMPT


def test_temps_single_source():
    assert TEMP_JUDGE == 0.0
    assert TEMP_DRAFT == 0.4
    assert TEMP_DESIGN == 0.6
    assert TEMP_PLAN_MAX == 0.6
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    src = (root / "playbook/layers.py").read_text(encoding="utf-8")
    assert "temperature=0.4" not in src
    assert "TEMP_DRAFT" in src
    assert "TEMP_JUDGE" in (root / "playbook/judge.py").read_text(encoding="utf-8")
    assert "TEMP_JUDGE" in (root / "review/l1_epistemic.py").read_text(encoding="utf-8")
    assert "TEMP_JUDGE" in (root / "api/routers/write.py").read_text(encoding="utf-8")
    assert "TEMP_JUDGE" in (root / "api/routers/misc_routes.py").read_text(encoding="utf-8")


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


def test_intro_change_stale_skips_high_confidence():
    from scribe3.outline_status import classify_intro_change, should_block_stage
    split = classify_intro_change([
        {"seq": 1, "confidence": "low"},
        {"seq": 2, "confidence": "high"},
        {"seq": 3},
    ])
    assert split["stale"] == [1, 3]
    assert split["pending_human"] == [2]
    assert should_block_stage("deduce", "stale") is True
    assert should_block_stage("duty", "stale") is False
    assert should_block_stage("draft", "") is False
    assert should_block_stage("deduce", "review") is False


def test_intro_text_changed_ignores_whitespace():
    from scribe3.outline_status import intro_text_changed
    assert intro_text_changed("华山成核 / 四十二度", "华山成核 / 四十二度") is False
    assert intro_text_changed("华山成核 / 四十二度", "  华山成核   /  四十二度\n") is False
    assert intro_text_changed("华山成核", "四十二度") is True


def test_rev_cap_marks_review_not_stale():
    from scribe3.outline_status import classify_intro_change, REFREEZE_REV_CAP
    split = classify_intro_change([
        {"seq": 1, "confidence": "low", "outline_rev": REFREEZE_REV_CAP},
        {"seq": 2, "confidence": "low", "outline_rev": 0},
    ])
    assert split["pending_human"] == [1]
    assert split["stale"] == [2]


def test_refreeze_volume_only_pending():
    from scribe3.outline_status import refreeze_volume

    class _St:
        def __init__(self):
            self.rows = [
                {"seq": 1, "outline_status": "stale", "outline_rev": 0},
                {"seq": 2, "outline_status": "review", "outline_rev": 1},
                {"seq": 3, "outline_status": "frozen", "outline_rev": 2},
            ]
            self.ch = {r["seq"]: dict(r) for r in self.rows}

        def _query(self, sql, vars=None):
            return list(self.rows)

        def update_chapter_meta(self, seq, fields):
            self.ch[int(seq)].update(fields)
            for r in self.rows:
                if r["seq"] == int(seq):
                    r.update(fields)
            return True

        def get_chapter(self, seq):
            row = self.ch.get(int(seq))
            return dict(row) if row else None

    st = _St()
    out = refreeze_volume(st, "cage")
    assert out["ok"] is True
    assert set(out["seqs"]) == {1, 2}
    assert st.ch[1]["outline_status"] == "frozen"
    assert st.ch[2]["outline_status"] == "frozen"
    assert st.ch[3]["outline_status"] == "frozen"
    assert st.ch[3]["outline_rev"] == 2


def test_refreeze_loop_idempotent():
    from scribe3.outline_status import mark_volume_intro_changed, refreeze_chapter

    class _St:
        def __init__(self):
            self.rows = [
                {"seq": 1, "confidence": "low", "outline_status": "frozen", "outline_rev": 0},
                {"seq": 2, "confidence": "high", "outline_status": "frozen", "outline_rev": 2},
            ]
            self.ch = {r["seq"]: dict(r) for r in self.rows}

        def _query(self, _sql, _vars=None):
            return list(self.rows)

        def update_chapter_meta(self, seq, fields):
            self.ch[int(seq)].update(fields)
            for r in self.rows:
                if r["seq"] == int(seq):
                    r.update(fields)
            return True

        def get_chapter(self, seq):
            row = self.ch.get(int(seq))
            return dict(row) if row else None

    st = _St()
    split = mark_volume_intro_changed(st, "cage")
    assert split["stale"] == [1]
    assert split["pending_human"] == [2]
    assert st.ch[1]["outline_status"] == "stale"
    assert st.ch[2]["outline_status"] == "review"
    out = refreeze_chapter(st, 1)
    assert out["ok"] is True
    assert out["idempotent"] is False
    assert out["outline_status"] == "frozen"
    assert out["outline_rev"] == 1
    again = refreeze_chapter(st, 1)
    assert again["idempotent"] is True
    assert again["outline_rev"] == 1
    missing = refreeze_chapter(st, 99)
    assert missing["ok"] is False


def test_outline_gate_fail_open_is_logged():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "stage_generate.py").read_text(encoding="utf-8")
    assert "outline_gate_fail_open" in src
    assert "fail-open" in src
    assert "逃生口" in src


def test_outline_gate_fail_open_emits_trace(monkeypatch):
    seen = []

    def _boom(*_a, **_k):
        raise RuntimeError("injected")

    def _note(name):
        seen.append(name)

    monkeypatch.setattr("scribe3.feature_flags.flag_truthy", _boom)
    monkeypatch.setattr("scribe3.pipeline_trace_hooks.note_guide_missing", _note)
    monkeypatch.setattr(
        "scribe3.stage_generate.run_stage",
        lambda *a, **k: {"ok": True, "skipped": True},
    )
    monkeypatch.setattr("scribe3.stage_generate.build_ctx", lambda *a, **k: {})
    monkeypatch.setattr("scribe3.stage_generate._emit_upstream_guide_span", lambda *a, **k: None)
    from scribe3.stage_generate import thicken_stage
    thicken_stage("design", {}, llm_fn=lambda *a, **k: "", persist_fn=None, seq=1)
    assert "outline_gate_fail_open" in seen


def test_settled_note_from_duty():
    note = _settled_note(
        {"must_happen": "把碎片按回裂口"},
        {"fields": {"decision": {"text": "按了进去"}}},
        1,
    )
    assert note.startswith("第1章办成了")
    assert "按回裂口" in note
    with_bill = _settled_note(
        {"must_happen": "把碎片按回裂口", "bill": "左手不受他管"},
        {},
        1,
    )
    assert "付了" in with_bill
    assert "左手" in with_bill

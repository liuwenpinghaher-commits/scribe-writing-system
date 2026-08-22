"""propose_outline 不再因恒真桩跳过。"""
from __future__ import annotations


def test_propose_outline_calls_thicken(monkeypatch):
    from scribe3.api.services.pilot_actions import outline as ol

    called = {}

    def fake_thicken(stage, ch0=None, **kw):
        called["yes"] = True
        called["stage"] = stage
        return {"ok": True, "synopsis": "新大纲"}

    monkeypatch.setattr("scribe3.stage_generate.thicken_stage", fake_thicken)
    acts = ol.build_actions("w")
    ol._pilot_steer = lambda st, seq: ""
    ol._pilot_llm_gen = lambda *a, **k: "x"

    class St:
        def get_chapter(self, seq):
            return {"seq": seq, "synopsis": "旧"}

        def update_chapter_meta(self, seq, fields):
            return True

    out = acts["propose_outline"](St(), 1)
    assert called.get("yes") is True
    assert out.get("synopsis") == "新大纲"
    assert "skipped" not in out


def test_propose_outline_source_has_no_iceberg_skip():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "api" / "services" / "pilot_actions" / "outline.py").read_text(encoding="utf-8")
    assert "章设计已过" not in src
    assert "iceberg_ok_for" not in src

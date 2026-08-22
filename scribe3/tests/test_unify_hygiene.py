"""统一度收口卫生：措辞、挂牌、parked 头注。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parents[1]


def test_no_stop_loss_fuse_in_product_copy():
    hits = []
    for py in SRC.rglob("*.py"):
        if "tests" in py.parts:
            continue
        text = py.read_text(encoding="utf-8")
        if "止损熔断" in text:
            hits.append(str(py.relative_to(SRC)))
    plan = ROOT / "docs" / "plans" / "2026-08-22-ultimate-reform.md"
    if plan.is_file() and "止损熔断" in plan.read_text(encoding="utf-8"):
        hits.append("docs/plans/2026-08-22-ultimate-reform.md")
    assert hits == []


def test_xfail_ledger_lists_r8_and_deadline():
    text = (ROOT / "docs" / "plans" / "xfail-ledger.md").read_text(encoding="utf-8")
    assert "test_reader_lamp_not_machine_pass" in text
    assert "test_write_layout_has_no_dual_lamp_chips" in text
    assert "test_meta_pane_one_scene_paper" in text
    assert "test_chapter_open_defaults_to_manuscript" in text
    assert "2026-09-22" in text


def test_parked_module_headers():
    for name in ("story_complete.py", "unattended_scene.py", "prompt_allowlist.py"):
        text = (SRC / name).read_text(encoding="utf-8")
        assert "parked" in text[:400].lower()
    ledger = (ROOT / "docs" / "plans" / "parked-modules.md").read_text(encoding="utf-8")
    assert "story_complete" in ledger
    assert "unattended_scene" in ledger
    assert "prompt_allowlist" in ledger

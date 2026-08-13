"""P1：focalizer 独立段 + 全知横幅点明 secret_guard。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.context_budget import (
    L0_NEVER_CUT,
    NOVEL_PROMPT_HARD,
    generation_physical_order_names,
    join_generation_segments,
)
from scribe3.epistemic_guard import (
    writing_limited_banner,
    writing_omniscient_author_banner,
)


def test_hard_budget_and_order():
    assert NOVEL_PROMPT_HARD == 48000
    assert "focalizer" in L0_NEVER_CUT
    order = generation_physical_order_names()
    assert order.index("secret_guard") < order.index("focalizer")
    assert order.index("focalizer") < order.index("narrative_contract")


def test_limited_banner_names_focalizer():
    text = writing_limited_banner("role:灰七")
    assert "认知分身·写作限知" in text
    assert "灰七" in text
    assert "role:" not in text


def test_omniscient_banner_mentions_secret_guard():
    text = writing_omniscient_author_banner()
    assert "作者视角写作" in text
    assert "secret_guard" in text
    assert "破绽词" in text


def test_v1_pushes_focalizer_independently():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert src.count('_push("focalizer"') == 1
    assert '_push("focalizer", "redline", _focalizer_txt)' in src
    assert 'prefix += _domain_input(\n        f"chapter:{chapter}:focalizer"' not in src


def test_join_reports_focalizer_length():
    banner = writing_limited_banner("role:灰七")
    _out, rep = join_generation_segments([
        {"name": "prefix", "layer": "redline", "text": "IDENT"},
        {"name": "secret_guard", "layer": "redline", "text": "GUARD"},
        {"name": "focalizer", "layer": "redline", "text": banner},
    ])
    assert rep["domain_lengths"]["focalizer"] == len(banner)
    assert _out.index("IDENT") < _out.index("GUARD") < _out.index("灰七")

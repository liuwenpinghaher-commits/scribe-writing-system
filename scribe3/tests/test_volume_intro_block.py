"""卷纲注入矩阵（纯逻辑 · 无 Surreal）。

驱动真实 shipped ``_volume_intro_block``（write_assemble），覆盖：
  R1 有卷 + 非空 intro → 注入且 ≤ 预算
  R2 有卷 + 空 intro → 不注入（防 S2 假绿）
  R3 无卷 → 空串
  R4 flag 关 → 空串
"""
from __future__ import annotations

import os

from scribe3.api.services.write_assemble import (
    _VOLUME_INTRO_BUDGET,
    _volume_intro_block,
    _volume_intro_inject_enabled,
)


class _FakeStore:
    def __init__(self, chapters=None, volumes=None):
        self._ch = chapters or {}
        self._vols = volumes or []

    def get_chapter(self, seq):
        return self._ch.get(int(seq))

    def list_volumes(self):
        return list(self._vols)


def test_volume_intro_budget_constant():
    assert _VOLUME_INTRO_BUDGET == 400


def test_inject_enabled_default_on():
    os.environ.pop("SCRIBE3_VOLUME_INTRO_INJECT", None)
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "1"
    assert _volume_intro_inject_enabled() is True
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "0"
    assert _volume_intro_inject_enabled() is False
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "1"


def test_volume_plus_nonempty_intro_injects():
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "1"
    long_intro = ("卷级主冲突是铜钱与义庄，" * 40).strip()
    st = _FakeStore(
        chapters={2: {"volume": "vol-a", "synopsis": "短纲"}},
        volumes=[{"id": "vol-a", "title": "试卷", "intro": long_intro}],
    )
    blk = _volume_intro_block(st, 2)
    assert "本卷卷纲摘要" in blk
    assert "卷级主冲突" in blk
    # body clip ≤ budget (+ header/wrapping)
    assert "不得覆盖本章大纲" in blk
    # clip: the intro body alone should not exceed budget after clip helper
    # (header lines exist; ensure we didn't dump unbounded intro)
    assert len(blk) < len(long_intro) + 200


def test_volume_plus_empty_intro_no_inject():
    """S2 / R-Vol-5：有归属但 intro 空 → 空串（不得假绿）。"""
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "1"
    st = _FakeStore(
        chapters={2: {"volume": "vol-a", "synopsis": "短纲"}},
        volumes=[{"id": "vol-a", "title": "试卷", "intro": ""}],
    )
    assert _volume_intro_block(st, 2) == ""
    st2 = _FakeStore(
        chapters={2: {"volume": "vol-a"}},
        volumes=[{"id": "vol-a", "title": "试卷", "intro": "   "}],
    )
    assert _volume_intro_block(st2, 2) == ""


def test_no_volume_no_inject():
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "1"
    st = _FakeStore(
        chapters={3: {"volume": None, "synopsis": "x"}},
        volumes=[{"id": "vol-a", "intro": "不该注入"}],
    )
    assert _volume_intro_block(st, 3) == ""
    st2 = _FakeStore(chapters={3: {"synopsis": "x"}}, volumes=[])
    assert _volume_intro_block(st2, 3) == ""


def test_flag_off_no_inject():
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "0"
    st = _FakeStore(
        chapters={2: {"volume": "vol-a"}},
        volumes=[{"id": "vol-a", "intro": "有内容也不注"}],
    )
    assert _volume_intro_block(st, 2) == ""
    os.environ["SCRIBE3_VOLUME_INTRO_INJECT"] = "1"


def test_none_chapter_empty():
    assert _volume_intro_block(_FakeStore(), None) == ""

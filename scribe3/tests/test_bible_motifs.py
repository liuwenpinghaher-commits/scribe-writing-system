"""开书母题强制 · 纯函数测（无 Surreal）。"""
from __future__ import annotations

from scribe3.bible_motifs import (
    MIN_BIBLE_MOTIFS,
    build_motif_seed_proposal,
    count_named_motifs,
    evaluate_motif_gap,
    pick_seed_motifs,
)


class _M:
    def __init__(self, names=None):
        self._m = [{"name": n} for n in (names or [])]

    def list_motifs(self):
        return list(self._m)


def test_gap_empty():
    g = evaluate_motif_gap(_M([]))
    assert g["ok"] is False
    assert g["count"] == 0
    assert g["deficit"] == MIN_BIBLE_MOTIFS


def test_gap_full():
    names = [f"m{i}" for i in range(MIN_BIBLE_MOTIFS)]
    g = evaluate_motif_gap(_M(names))
    assert g["ok"] is True
    assert g["deficit"] == 0
    assert build_motif_seed_proposal(_M(names)) is None


def test_pick_and_proposal_fills_deficit_only():
    st = _M(["灯与债"])  # 已有一条默认种子名
    seeds = pick_seed_motifs(st)
    assert len(seeds) == MIN_BIBLE_MOTIFS - 1
    assert all(s["name"] != "灯与债" for s in seeds)
    prop = build_motif_seed_proposal(st, work="book_x")
    assert prop is not None
    assert prop["domain"] == "motif.manage"
    assert prop["source"] == "bible_motif_force"
    assert len(prop["ops"]) == MIN_BIBLE_MOTIFS - 1
    assert all(op["tool"] == "s3_add_motif" for op in prop["ops"])
    assert prop["ops"][0]["args"]["name"]


def test_count_named_skips_blank():
    st = _M(["a", "", "  "])
    # blank names in list_motifs: count_named only counts non-empty
    st._m = [{"name": "a"}, {"name": ""}, {"name": "  "}]
    assert count_named_motifs(st) == 1

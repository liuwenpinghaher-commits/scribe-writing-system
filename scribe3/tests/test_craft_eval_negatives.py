"""P1.3 mechanical negatives: cut / pump / lecture on a dev chapter."""
from __future__ import annotations

from scribe3.eval.extract_card import load_source_slice
from scribe3.eval.negatives import LECTURE, make_cut, make_lecture, make_pump, stay_quotes, turn_quotes


def test_seq1_cut_drops_the_turn_sentence():
    src = load_source_slice(1)
    cut = make_cut(1)
    assert "收入怀中" in src
    assert "收入怀中" not in cut
    assert len(cut) < len(src)
    assert turn_quotes(1)


def test_seq1_pump_keeps_spectacle_drops_stay():
    src = load_source_slice(1)
    pump = make_pump(1)
    assert stay_quotes(1)
    assert "收入怀中" in src
    assert "收入怀中" not in pump
    assert "三五百年" in pump


def test_seq1_lecture_asserts_instead_of_showing():
    lec = make_lecture(1)
    assert LECTURE in lec
    assert "收入怀中" not in lec

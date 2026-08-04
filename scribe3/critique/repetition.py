"""Critique family facade: repetition (implementation in rules_impl)."""
from __future__ import annotations

from scribe3.critique.rules_impl import (
    find_repetitions,
    find_cross_chapter_repetitions,
    distinctive_phrases,
    cross_repetition_sentences,
    rewrite_cross_repetitions,
    find_near_duplicate_paragraphs,
    intra_repetition_sentences,
    rewrite_intra_chapter_issues,
    find_duplicate_lines,
    find_emotion_telling,
)

__all__ = ['find_repetitions', 'find_cross_chapter_repetitions', 'distinctive_phrases', 'cross_repetition_sentences', 'rewrite_cross_repetitions', 'find_near_duplicate_paragraphs', 'intra_repetition_sentences', 'rewrite_intra_chapter_issues', 'find_duplicate_lines', 'find_emotion_telling']


"""Critique family facade: structure_style (implementation in rules_impl)."""
from __future__ import annotations

from scribe3.critique.rules_impl import (
    find_structural_repeats,
    repair_nested_dialogue_opens,
    normalize_punctuation_suggestions,
    find_purple_prose,
    find_ai_tics,
    find_oversaturation,
    find_adverb_density,
    find_rule_of_three,
    find_elegant_variation,
    quality_flags,
)

__all__ = ['find_structural_repeats', 'repair_nested_dialogue_opens', 'normalize_punctuation_suggestions', 'find_purple_prose', 'find_ai_tics', 'find_oversaturation', 'find_adverb_density', 'find_rule_of_three', 'find_elegant_variation', 'quality_flags']


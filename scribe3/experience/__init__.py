"""经验压力层 · 责编式问诊与场景动能(非文学总分)。

设计真源:设计文档/2026-08-05-写作经验差距改进方案.md
宪法:不进默认 finalize blocking;无 total_score;advisory 不自动改写。
"""
from __future__ import annotations

from scribe3.experience.modes import (
    REVISION_MODES,
    normalize_revision_mode,
    revision_mode_priority,
)
from scribe3.experience.letter import (
    LETTER_KINDS,
    ITEM_STATUSES,
    build_revision_letter,
    update_letter_item_status,
    letter_has_total_score,
)
from scribe3.experience.scene_grid import (
    SCENE_KEYS,
    empty_scene_grid,
    normalize_scene_grid,
    diagnose_scene_grid,
    evaluate_strict_scene_gate,
)
from scribe3.experience.choice_seed import (
    build_choice_audit,
    suggest_seeds,
    promote_seed_payload,
)
from scribe3.experience.continue_rite import (
    build_continue_snapshot,
    continue_block_text,
    reread_allowed,
)
from scribe3.experience.feedback_cut import (
    parse_feedback_markdown,
    suggest_cut_candidates,
)
from scribe3.experience import state as exp_state

__all__ = [
    "REVISION_MODES",
    "normalize_revision_mode",
    "revision_mode_priority",
    "LETTER_KINDS",
    "ITEM_STATUSES",
    "build_revision_letter",
    "update_letter_item_status",
    "letter_has_total_score",
    "SCENE_KEYS",
    "empty_scene_grid",
    "normalize_scene_grid",
    "diagnose_scene_grid",
    "evaluate_strict_scene_gate",
    "build_choice_audit",
    "suggest_seeds",
    "promote_seed_payload",
    "build_continue_snapshot",
    "continue_block_text",
    "reread_allowed",
    "parse_feedback_markdown",
    "suggest_cut_candidates",
    "exp_state",
]

"""修订模式 · 只改展示优先级,不关 finalize_gate。"""
from __future__ import annotations

REVISION_MODES = ("structure", "scene", "line", "proof", "full")

# 各模式下 letter kind 的优先序(越前越先展示)
_MODE_KIND_ORDER: dict[str, tuple[str, ...]] = {
    "structure": (
        "opening_promise", "middle_sag", "character_arc", "theme_or_intent",
        "unpaid_promise", "pacing", "info_control", "latent_seed",
        "external_read", "custom",
    ),
    "scene": (
        "scene_kinetics", "pacing", "middle_sag", "character_arc",
        "unpaid_promise", "opening_promise", "theme_or_intent",
        "info_control", "latent_seed", "external_read", "custom",
    ),
    "line": (
        "info_control", "pacing", "custom", "external_read",
        "opening_promise", "middle_sag", "character_arc", "theme_or_intent",
        "unpaid_promise", "latent_seed", "scene_kinetics",
    ),
    "proof": (
        "external_read", "custom", "info_control", "unpaid_promise",
        "opening_promise", "middle_sag", "character_arc", "theme_or_intent",
        "pacing", "latent_seed", "scene_kinetics",
    ),
    "full": (
        "opening_promise", "middle_sag", "character_arc", "theme_or_intent",
        "unpaid_promise", "scene_kinetics", "pacing", "info_control",
        "latent_seed", "external_read", "custom",
    ),
}


def normalize_revision_mode(raw: str | None) -> str:
    m = (raw or "full").strip().lower()
    return m if m in REVISION_MODES else "full"


def revision_mode_priority(mode: str | None) -> tuple[str, ...]:
    return _MODE_KIND_ORDER[normalize_revision_mode(mode)]

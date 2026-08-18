"""Stage names, extra flags, 410 for retired stages."""
from __future__ import annotations

import re

from scribe3.playbook.errors import StageGone

LIVE_STAGES = ("duty", "design", "deduce", "draft", "final")
GONE_STAGES = frozenset({"outline", "beats", "chapter_design", "plan"})
MIGRATE_HINT = (
    "outline/beats/chapter_design 已废止。"
    "请改用 duty → design → deduce → draft → final。"
)
STAGE_MAX_TOKENS = {
    "duty": 2048,
    "design": 4096,
    "deduce": 8192,
    "draft": 16384,
    "final": 16384,
    "write": 16384,
}
_FORCE_RE = re.compile(r"(?:^|[,\s])force\s*=\s*1(?:[,\s]|$)", re.I)
_REWRITE_RE = re.compile(r"(?:^|[,\s])rewrite\s*=\s*1(?:[,\s]|$)", re.I)


def normalize_stage(phase: str | None) -> str:
    p = (phase or "").strip().lower()
    if p in ("write", "prose"):
        return "final"
    return p


def reject_gone_stage(stage: str) -> dict | None:
    p = normalize_stage(stage)
    if p in GONE_STAGES:
        return StageGone(p, MIGRATE_HINT).as_dict()
    return None


def stage_max_tokens(phase: str | None) -> int:
    p = normalize_stage(phase)
    return int(STAGE_MAX_TOKENS.get(p, 4096))


def parse_force(extra: str) -> bool:
    return bool(_FORCE_RE.search(extra or ""))


def parse_rewrite(extra: str) -> bool:
    return bool(_REWRITE_RE.search(extra or ""))


def extra_authors(extra: str) -> list[str]:
    """Keep the old extra-as-author ban without world_surface."""
    if not extra:
        return []
    cleaned = re.sub(r"禁止[^。\n]{0,80}(?:必须原样|原样使用|原样复述|必须有一句|必须以)", "", extra)
    if re.search(r"必须原样|必须有一句|必须以时空", cleaned):
        return ["extra_authors"]
    return []

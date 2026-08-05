"""讨论驱动能力编排 · WorkPackage / Catalog / Proposal / UI directive。"""
from __future__ import annotations

from scribe3.orchestration.catalog import (
    CATALOG,
    get_domain,
    list_domains,
    primary_domain_ids,
)
from scribe3.orchestration.resolve import (
    apply_ui_directive_events,
    evaluate_turn,
    match_domain,
    resolve_work_package,
)
from scribe3.orchestration import state as package_state
from scribe3.orchestration.proposal import apply_proposal_ops, build_write_proposal

__all__ = [
    "CATALOG",
    "get_domain",
    "list_domains",
    "primary_domain_ids",
    "resolve_work_package",
    "match_domain",
    "evaluate_turn",
    "apply_ui_directive_events",
    "package_state",
    "build_write_proposal",
    "apply_proposal_ops",
]

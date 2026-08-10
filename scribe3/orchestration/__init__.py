"""讨论驱动能力编排 · WorkPackage / Catalog / Proposal / UiTarget / Drafts。"""
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
    instruction_suffix_for_entry,
    match_domain,
    resolve_work_package,
)
from scribe3.orchestration import state as package_state
from scribe3.orchestration import drafts as draft_store
from scribe3.orchestration.proposal import (
    apply_proposal_ops,
    build_write_proposal,
    proposal_from_discussion,
    resolve_approve_ui_target,
    post_approve_ui_target,
)
from scribe3.orchestration.ui_target import (
    apply_ui_target_events,
    build_ui_target,
    selection_is_ghost_leaf,
)

__all__ = [
    "CATALOG",
    "get_domain",
    "list_domains",
    "primary_domain_ids",
    "resolve_work_package",
    "match_domain",
    "instruction_suffix_for_entry",
    "evaluate_turn",
    "apply_ui_directive_events",
    "apply_ui_target_events",
    "build_ui_target",
    "selection_is_ghost_leaf",
    "package_state",
    "draft_store",
    "build_write_proposal",
    "proposal_from_discussion",
    "resolve_approve_ui_target",
    "post_approve_ui_target",
    "apply_proposal_ops",
]

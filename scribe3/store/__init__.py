"""scribe3.store package — physical split of monolithic store.py.

Canonical import (unchanged for callers)::

    from scribe3.store import SurrealStore, list_works, ...
"""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403
from scribe3.store.surreal import SurrealStore
from scribe3.store.core_preamble import MATERIAL_KINDS, MATERIAL_ORIGINS, OVERDUE_SLACK, QUALITY_CACHE_REVISION, archive_work, archived_works, backfill_material_memory, backfill_proposition_tokens, backfill_scalability_caches, build_memory_trace, create_work, delete_work, list_works, mask_memory_trace, promise_window_state, rename_work, restore_work, _overdue_flag, _redact_run_trace_secrets  # noqa: F401

__all__ = ["SurrealStore", 'MATERIAL_KINDS', 'MATERIAL_ORIGINS', 'OVERDUE_SLACK', 'QUALITY_CACHE_REVISION', 'archive_work', 'archived_works', 'backfill_material_memory', 'backfill_proposition_tokens', 'backfill_scalability_caches', 'build_memory_trace', 'create_work', 'delete_work', 'list_works', 'mask_memory_trace', 'promise_window_state', 'rename_work', 'restore_work', '_overdue_flag', '_redact_run_trace_secrets']

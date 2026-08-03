"""Shared FastAPI dependencies for scribe3 API routers.

Phase 1 extraction: store resolution and (future) auth helpers.
Keep SurrealStore per-work cache ownership in app_impl for now;
routers receive the resolver via app.state or explicit Depends.
"""
from __future__ import annotations

from typing import Callable

from fastapi import Request

from scribe3.store import SurrealStore


def get_store_for(request: Request) -> Callable[[str], SurrealStore]:
    """Return the process-level work→SurrealStore resolver.

    Assigned on the FastAPI app as ``app.state.store_for`` after the cache
    is defined in app_impl. Routers should prefer this over importing
    private ``_store_for``.
    """
    return request.app.state.store_for

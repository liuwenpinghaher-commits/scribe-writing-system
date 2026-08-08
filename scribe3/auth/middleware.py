"""HTTP middleware: session gate + work ownership choke point."""
from __future__ import annotations

import hmac
import os
import re
from typing import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse

from scribe3.auth.context import reset_auth_context, set_auth_context
from scribe3.auth.ownership import assert_user_may_access_work
from scribe3.auth.session import COOKIE_NAME, parse_session_token

# Paths that never require a session (probe + auth endpoints).
_PUBLIC_EXACT = frozenset({
    "/health",
    "/ready",
    "/auth/login",
    "/auth/logout",
    "/auth/me",
})

# Global (not work-scoped) surfaces when authenticated: no default-main ownership check.
# Work-scoped handlers default work="main" / SCRIBE3_WORK — those MUST hit ownership.
_GLOBAL_EXACT = frozenset({
    "/health",
    "/ready",
    "/auth/login",
    "/auth/logout",
    "/auth/me",
    "/works",
    "/works/archived",
    "/capabilities",
    # Process-level probe only — not work-scoped store access
    "/ai/runtime-status",
})

# Prefix allowlist for true globals only. Do NOT put "/ai/" here: most /ai/runs*
# and /ai/usage take ?work= and call _store_for(work); they must hit ownership.
_GLOBAL_PREFIXES = (
    "/auth/",
    "/admin/",
    "/settings",
    "/gateway",
    "/health",
)

_WORKS_SLUG_RE = re.compile(
    r"^/works/(?P<slug>[A-Za-z0-9_]+)(?:/(?:restore|purge))?$"
)


def auth_enabled() -> bool:
    return (os.environ.get("SCRIBE3_AUTH_ENABLED") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _api_token() -> str:
    return (os.environ.get("SCRIBE3_API_TOKEN") or "").strip()


def resolve_username(request: Request) -> str | None:
    """Cookie session first; optional machine Bearer SCRIBE3_API_TOKEN → synthetic user."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            data = parse_session_token(token)
        except RuntimeError:
            data = None
        if data:
            return data.username

    api_tok = _api_token()
    if api_tok:
        auth = request.headers.get("authorization") or ""
        if auth.startswith("Bearer "):
            presented = auth[7:].strip()
            if hmac.compare_digest(presented, api_tok):
                # Machine token: act as legacy owner so ops can manage historical books.
                return (os.environ.get("SCRIBE3_MACHINE_USER")
                        or os.environ.get("SCRIBE3_LEGACY_OWNER")
                        or "admin").strip()
    return None


def is_global_route(path: str) -> bool:
    """Routes that are not bound to a single work DB (list/settings/auth/health)."""
    if not path:
        return True
    if path in _GLOBAL_EXACT or path in _PUBLIC_EXACT:
        return True
    for prefix in _GLOBAL_PREFIXES:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return True
    return False


def _slug_from_works_path(path: str) -> str | None:
    if path in ("/works", "/works/archived") or path.startswith("/works/archived"):
        return None
    m = _WORKS_SLUG_RE.match(path or "")
    if m:
        return m.group("slug")
    return None


def default_work_slug() -> str:
    """Same fallback as app_impl._normalize_work when work is omitted."""
    return (os.environ.get("SCRIBE3_WORK") or "main").strip() or "main"


def resolve_effective_work(
    path: str,
    query_work: str | None,
    *,
    default: str | None = None,
) -> str | None:
    """Resolve the work slug a handler would use.

    Order: ?work= → /works/{slug} path → SCRIBE3_WORK/main default for work-scoped
    routes. Global routes return None (no ownership check).
    """
    if is_global_route(path):
        # /works/{slug} is not global; is_global_route is false for those paths
        return None
    q = (query_work or "").strip()
    if q:
        return q
    path_slug = _slug_from_works_path(path)
    if path_slug:
        return path_slug
    return default if default is not None else default_work_slug()


def resolve_username_public(request: Request) -> str | None:
    """Alias for routes module."""
    return resolve_username(request)


async def l1_auth_middleware(request: Request, call_next: Callable):
    path = request.url.path or ""
    # CORS preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    username: str | None = None
    tokens = None
    try:
        if auth_enabled():
            if path not in _PUBLIC_EXACT and not path.startswith("/health"):
                username = resolve_username(request)
                if not username:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "authentication required"},
                    )
            else:
                # login/me/logout may still resolve session for convenience
                username = resolve_username(request)
        else:
            # Auth off: still parse session if present (no force)
            username = resolve_username(request)

        tokens = set_auth_context(username)
        request.state.scribe3_user = username

        # Ownership choke: same effective work as handlers (query | path | default main)
        if auth_enabled() and username:
            effective = resolve_effective_work(
                path, request.query_params.get("work")
            )
            if effective:
                try:
                    assert_user_may_access_work(username, effective)
                except KeyError:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": "work not found"},
                    )
                except PermissionError:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "work access denied"},
                    )

        return await call_next(request)
    finally:
        if tokens is not None:
            reset_auth_context(tokens)


def install_l1_auth(app) -> None:
    """Register middleware (call after app creation). Last add = outermost first run."""
    app.middleware("http")(l1_auth_middleware)

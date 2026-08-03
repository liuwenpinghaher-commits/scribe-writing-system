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


def _slug_from_path(path: str) -> str | None:
    if path in ("/works", "/works/archived") or path.startswith("/works/archived"):
        return None
    m = _WORKS_SLUG_RE.match(path)
    if m:
        return m.group("slug")
    return None


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

        # Ownership choke: work query + /works/{slug}
        if auth_enabled() and username:
            work_q = request.query_params.get("work")
            slug = work_q or _slug_from_path(path)
            if slug:
                try:
                    assert_user_may_access_work(username, slug)
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

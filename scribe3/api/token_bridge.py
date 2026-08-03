"""EventSource token bridge (Phase 1 style — no touch of 554k app_impl).

Browsers cannot set Authorization on EventSource. Frontend appends ?token=.
This outermost middleware injects Authorization: Bearer from query token
so the existing app_impl _auth_middleware continues to work unchanged.
"""
from __future__ import annotations


async def token_query_bridge(request, call_next):
    # Only inject when Authorization is absent; never override an explicit header.
    has_auth = any(k.lower() == b"authorization" for k, _ in request.scope.get("headers", []))
    if not has_auth:
        token = request.query_params.get("token")
        if token:
            headers = list(request.scope.get("headers", []))
            headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))
            request.scope["headers"] = headers
    return await call_next(request)


def install_token_query_bridge(app) -> None:
    """Register as outermost HTTP middleware (last add = first run)."""
    app.middleware("http")(token_query_bridge)

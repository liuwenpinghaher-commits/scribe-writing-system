"""Auth HTTP routes: login / logout / me."""
from __future__ import annotations

import os

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from scribe3.auth.middleware import auth_enabled, resolve_username
from scribe3.auth.session import COOKIE_NAME, issue_session_token
from scribe3.auth.users import authenticate, ensure_bootstrap_users

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


def _cookie_secure() -> bool:
    flag = (os.environ.get("SCRIBE3_SESSION_SECURE") or "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    # Default secure when public domain assumed in production notes
    return False


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
        max_age=int(os.environ.get("SCRIBE3_SESSION_TTL_HOURS", "168") or "168") * 3600,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


@router.post("/auth/login")
def login(body: LoginIn, response: Response):
    ensure_bootstrap_users()
    if not authenticate(body.username.strip(), body.password):
        return JSONResponse(
            status_code=401,
            content={"detail": "invalid credentials"},
        )
    if auth_enabled():
        secret_ok = bool((os.environ.get("SCRIBE3_SESSION_SECRET") or "").strip())
        if not secret_ok:
            return JSONResponse(
                status_code=503,
                content={"detail": "SCRIBE3_SESSION_SECRET not configured"},
            )
    token = issue_session_token(body.username.strip())
    _set_session_cookie(response, token)
    return {"ok": True, "username": body.username.strip()}


@router.post("/auth/logout")
def logout(response: Response):
    _clear_session_cookie(response)
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request):
    username = resolve_username(request)
    if not username:
        if auth_enabled():
            return JSONResponse(
                status_code=401,
                content={"detail": "authentication required"},
            )
        return JSONResponse(
            status_code=401,
            content={"detail": "authentication required"},
        )
    return {"username": username}

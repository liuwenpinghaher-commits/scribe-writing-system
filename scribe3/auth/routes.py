"""Auth HTTP routes: login / logout / me."""
from __future__ import annotations

import os

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from scribe3.auth.middleware import auth_enabled, resolve_username
from scribe3.auth.session import COOKIE_NAME, issue_session_token
from scribe3.auth.users import authenticate, ensure_bootstrap_users, get_user, is_admin

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


def _session_bool_from_env(key: str) -> bool | None:
    """显式 env 非空 → True/False；未设或空 → None（继续后续规则）。"""
    raw = os.environ.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    flag = str(raw).strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    return None


def _cookie_secure(request: Request | None = None) -> bool:
    """EH-05 / P1-4/5：显式 env 优先；settings 覆盖次之；未设时 HTTPS 推断。

    - SCRIBE3_SESSION_SECURE=1/0（env）→ 强制
    - settings 注册表有 override → 用 settings 真值
    - 否则：X-Forwarded-Proto: https 或 scheme==https → True
    - 默认 False（本地 HTTP 开发）
    """
    # 1) 显式 env 优先（进程注入 / docker -e）
    env_flag = _session_bool_from_env("SCRIBE3_SESSION_SECURE")
    if env_flag is not None:
        return env_flag
    # 2) settings 注册表（DB 热覆盖）
    try:
        from scribe3 import settings as _settings
        try:
            if getattr(_settings, "settings_store", None) and _settings.settings_store.has_override(
                "SCRIBE3_SESSION_SECURE"
            ):
                return bool(_settings.get_setting("SCRIBE3_SESSION_SECURE"))
        except Exception:
            pass
        # 无 override 时 get_setting 可能回落 env（已空）或默认 False——不在此抢在 XFP 之前
    except Exception:
        pass
    # 3) 请求侧 HTTPS 推断
    if request is not None:
        try:
            xfp = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
            if xfp == "https":
                return True
            if str(getattr(request.url, "scheme", "") or "").lower() == "https":
                return True
        except Exception:
            pass
    return False


def _session_ttl_seconds() -> int:
    """会话 Cookie max_age：settings 优先，env 回落，默认 168h。"""
    hours = 168
    try:
        from scribe3.settings import get_setting
        v = get_setting("SCRIBE3_SESSION_TTL_HOURS")
        if v is not None and str(v).strip() != "":
            hours = max(1, int(v))
    except Exception:
        raw = os.environ.get("SCRIBE3_SESSION_TTL_HOURS", "168") or "168"
        try:
            hours = max(1, int(raw))
        except ValueError:
            hours = 168
    return int(hours) * 3600


def _set_session_cookie(response: Response, token: str, request: Request | None = None) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        path="/",
        max_age=_session_ttl_seconds(),
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


@router.post("/auth/login")
def login(body: LoginIn, response: Response, request: Request):
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
    uname = body.username.strip()
    token = issue_session_token(uname)
    _set_session_cookie(response, token, request=request)
    u = get_user(uname) or {}
    return {
        "ok": True,
        "username": uname,
        "role": u.get("role") or "author",
        "is_admin": is_admin(uname),
        "display_name": u.get("display_name") or "",
    }


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
    u = get_user(username) or {}
    return {
        "username": username,
        "role": u.get("role") or "author",
        "is_admin": is_admin(username),
        "display_name": u.get("display_name") or "",
        "status": u.get("status") or "active",
    }

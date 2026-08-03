"""Signed session tokens for Cookie transport."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass


COOKIE_NAME = "s3_session"
DEFAULT_TTL_HOURS = 168  # 7 days


@dataclass(frozen=True)
class SessionData:
    username: str
    exp: int


def _secret() -> bytes:
    raw = os.environ.get("SCRIBE3_SESSION_SECRET") or ""
    if not raw:
        raise RuntimeError("SCRIBE3_SESSION_SECRET is required when auth is enabled")
    return raw.encode("utf-8")


def _ttl_seconds() -> int:
    try:
        hours = float(os.environ.get("SCRIBE3_SESSION_TTL_HOURS", str(DEFAULT_TTL_HOURS)))
    except (TypeError, ValueError):
        hours = DEFAULT_TTL_HOURS
    return max(300, int(hours * 3600))


def issue_session_token(username: str, *, now: float | None = None, secret: bytes | None = None) -> str:
    if not username or not str(username).strip():
        raise ValueError("username required")
    ts = int(now if now is not None else time.time())
    exp = ts + _ttl_seconds()
    payload = {"u": str(username).strip(), "exp": exp}
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii").rstrip("=")
    key = secret if secret is not None else _secret()
    sig = hmac.new(key, body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def parse_session_token(
    token: str | None,
    *,
    now: float | None = None,
    secret: bytes | None = None,
) -> SessionData | None:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    if not body or not sig:
        return None
    key = secret if secret is not None else _secret()
    expect = hmac.new(key, body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, sig):
        return None
    pad = "=" * (-len(body) % 4)
    try:
        raw = base64.urlsafe_b64decode(body + pad)
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    username = str(payload.get("u") or "").strip()
    try:
        exp = int(payload.get("exp"))
    except (TypeError, ValueError):
        return None
    if not username:
        return None
    ts = int(now if now is not None else time.time())
    if exp < ts:
        return None
    return SessionData(username=username, exp=exp)

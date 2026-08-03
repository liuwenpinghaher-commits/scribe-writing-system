"""L1 session auth + work ownership (see docs/L1-AUTH-ISOLATION.md)."""
from __future__ import annotations

from scribe3.auth.context import (
    current_owner_filter,
    current_user_id,
    reset_auth_context,
    set_auth_context,
)
from scribe3.auth.middleware import install_l1_auth
from scribe3.auth.passwords import hash_password, verify_password
from scribe3.auth.session import SessionData, issue_session_token, parse_session_token

__all__ = [
    "SessionData",
    "current_owner_filter",
    "current_user_id",
    "hash_password",
    "install_l1_auth",
    "issue_session_token",
    "parse_session_token",
    "reset_auth_context",
    "set_auth_context",
    "verify_password",
]

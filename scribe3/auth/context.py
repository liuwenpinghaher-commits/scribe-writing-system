"""Request-scoped user identity for list/create_work filtering."""
from __future__ import annotations

from contextvars import ContextVar, Token
from typing import NamedTuple


class AuthUser(NamedTuple):
    username: str


current_user_id: ContextVar[str | None] = ContextVar("scribe3_auth_user", default=None)
current_owner_filter: ContextVar[str | None] = ContextVar(
    "scribe3_owner_filter", default=None
)


def set_auth_context(username: str | None) -> tuple[Token, Token]:
    t1 = current_user_id.set(username)
    t2 = current_owner_filter.set(username)
    return t1, t2


def reset_auth_context(tokens: tuple[Token, Token]) -> None:
    current_user_id.reset(tokens[0])
    current_owner_filter.reset(tokens[1])

"""Password hashing (stdlib PBKDF2 — no extra dependency)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_SCHEME = "pbkdf2_sha256"
_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("password required")
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return f"{_SCHEME}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not password or not stored:
        return False
    try:
        scheme, salt, hex_dk = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != _SCHEME:
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return hmac.compare_digest(dk.hex(), hex_dk)

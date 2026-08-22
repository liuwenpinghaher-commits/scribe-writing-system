"""新接口错误：编号 + 人话。"""
from __future__ import annotations

from fastapi import HTTPException


def error_body(code: str, message: str, **extra) -> dict:
    out = {"code": str(code), "message": str(message)}
    out.update(extra)
    return out


def http_error(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status_code=int(status), detail=error_body(code, message, **extra))

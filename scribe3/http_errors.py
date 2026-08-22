"""新接口错误：编号 + 人话。"""
from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def error_body(code: str, message: str, **extra) -> dict:
    out = {"code": str(code), "message": str(message)}
    out.update(extra)
    return out


def shape_http_detail(detail) -> dict:
    """任意 HTTPException.detail → {code, message, ...}。"""
    if isinstance(detail, dict):
        code = str(detail.get("code") or "http_error")
        message = str(detail.get("message") or detail.get("error") or "")
        extra = {k: v for k, v in detail.items() if k not in ("code", "message")}
        if not message:
            message = code
        return error_body(code, message, **extra)
    return error_body("http_error", str(detail))


def http_error(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status_code=int(status), detail=error_body(code, message, **extra))


def http_error_response(status: int, detail) -> JSONResponse:
    body = shape_http_detail(detail)
    return JSONResponse(status_code=int(status), content={"detail": body})

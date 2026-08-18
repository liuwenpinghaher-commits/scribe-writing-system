"""JSON parse + infra vs quality split."""
from __future__ import annotations

import json
import re
from typing import Any, Callable

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class InfraError(Exception):
    """Timeout / rate-limit / transport. Does not consume quality rounds."""


class ParseError(Exception):
    """Illegal / truncated JSON after one retry."""


def strip_fence(raw: str) -> str:
    return _FENCE.sub("", (raw or "").strip()).strip()


def parse_json_object(raw: str) -> dict[str, Any]:
    s = strip_fence(raw)
    start, end = s.find("{"), s.rfind("}")
    if start >= 0 and end > start:
        s = s[start : end + 1]
    data = json.loads(s)
    if not isinstance(data, dict):
        raise ParseError("JSON 根必须是对象")
    return data


def parse_json_with_retry(fn: Callable[[], str]) -> dict[str, Any]:
    last: Exception | None = None
    for _ in range(2):
        try:
            return parse_json_object(fn())
        except (json.JSONDecodeError, ParseError, ValueError, TypeError) as exc:
            last = exc
            continue
    raise ParseError(str(last) if last else "JSON 解析失败")

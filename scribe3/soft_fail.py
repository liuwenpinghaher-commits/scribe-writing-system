"""Fail-soft 可观测（包 B / EH-16′）。

写路径允许吞异常，但禁止完全静默：至少记录 ``op`` + 异常类型名（不含 secret 正文）。
"""
from __future__ import annotations

import logging
from typing import Any


def soft_fail(
    op: str,
    err: BaseException,
    *,
    logger: logging.Logger | str | None = None,
    level: int = logging.WARNING,
    **ctx: Any,
) -> None:
    """记录 soft_fail；永不抛出。

    日志形态：``soft_fail op=<op> err=<ExceptionType> [k=v ...]``
    """
    if isinstance(logger, logging.Logger):
        log = logger
    elif isinstance(logger, str) and logger:
        log = logging.getLogger(logger)
    else:
        log = logging.getLogger("scribe3.soft_fail")
    try:
        parts = [f"soft_fail op={op}", f"err={type(err).__name__}"]
        for k, v in ctx.items():
            if v is None:
                continue
            # 截断，避免把正文/secret 打进日志
            s = str(v)
            if len(s) > 80:
                s = s[:77] + "..."
            parts.append(f"{k}={s}")
        log.log(level, " ".join(parts))
    except Exception:
        # 日志本身失败仍不得影响主路径
        pass

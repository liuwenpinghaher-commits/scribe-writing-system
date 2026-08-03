"""scribe3 后端 API 入口。

物理拆分: 实现主体位于 ``scribe3/api/app_impl.py``。
本模块在导入时将自身替换为 app_impl,保证:

- ``import scribe3.app as A`` 与实现模块是同一对象
- 测试 ``monkeypatch.setattr(A, ...)`` 作用于真实 handler 闭包全局
- ``from scribe3.app import app`` 仍可用

存储层物理拆分见 ``scribe3/store/`` 包。

Phase 1 路由抽出（入口接线 + 剥内联，避免动 554k app_impl）:
- health → ``scribe3/api/health.py``
- intent / intent-goals / north-star/chapter → ``scribe3/api/intent_northstar.py``
"""
from __future__ import annotations

import sys

from scribe3.api import app_impl as _impl

# Phase 1: 已抽 router 在入口统一接线；剥掉 app_impl 内联同名路径，避免双注册。
from scribe3.api.health import router as health_router
from scribe3.api.intent_northstar import router as intent_northstar_router

# Exact paths only (no prefix match) — /intent-goals is distinct from /intent.
_EXTRACTED_PATHS = frozenset({
    "/health",
    "/ready",
    "/intent",
    "/intent-goals",
})
# Path-prefix patterns for path-param routes extracted to routers.
_EXTRACTED_PREFIXES = (
    "/north-star/chapter/",
)


def _is_extracted_route(path: str | None) -> bool:
    if not path:
        return False
    if path in _EXTRACTED_PATHS:
        return True
    return any(path.startswith(p) for p in _EXTRACTED_PREFIXES)


_impl.app.router.routes[:] = [
    r for r in _impl.app.router.routes
    if not _is_extracted_route(getattr(r, "path", None))
]
_impl.app.include_router(health_router)
_impl.app.include_router(intent_northstar_router)

if __name__ == "__main__":
    # `python -m scribe3.app` 是公开的后端启动约定。模块别名本身不会触发
    # app_impl 的 `if __name__ == "__main__"`，因此必须显式委托入口。
    _impl.main()
else:
    # 关键模块身份 → 测试与生产共用同一 globals
    sys.modules[__name__] = _impl

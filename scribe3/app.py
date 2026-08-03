"""scribe3 后端 API 入口。

物理拆分: 实现主体位于 ``scribe3/api/app_impl.py``。
本模块在导入时将自身替换为 app_impl,保证:

- ``import scribe3.app as A`` 与实现模块是同一对象
- 测试 ``monkeypatch.setattr(A, ...)`` 作用于真实 handler 闭包全局
- ``from scribe3.app import app`` 仍可用

存储层物理拆分见 ``scribe3/store/`` 包。

Phase 1 路由抽出: health 已落 ``scribe3/api/health.py``；在入口接线并
剥掉 app_impl 内残留的内联 /health /ready（大文件整删延后到后续搬迁 PR）。
"""
from __future__ import annotations

import sys

from scribe3.api import app_impl as _impl

# Phase 1: health 路由已抽到 scribe3.api.health；入口统一接线。
# app_impl 内若仍有内联 @app.get("/health")/("/ready")，先剥掉再 include，
# 避免双注册；auth middleware 仍按 path 前缀跳过 /health（不变）。
from scribe3.api.health import router as health_router

_HEALTH_PATHS = frozenset({"/health", "/ready"})
_impl.app.router.routes[:] = [
    r for r in _impl.app.router.routes
    if getattr(r, "path", None) not in _HEALTH_PATHS
]
_impl.app.include_router(health_router)

if __name__ == "__main__":
    # `python -m scribe3.app` 是公开的后端启动约定。模块别名本身不会触发
    # app_impl 的 `if __name__ == "__main__"`，因此必须显式委托入口。
    _impl.main()
else:
    # 关键模块身份 → 测试与生产共用同一 globals
    sys.modules[__name__] = _impl

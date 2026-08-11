"""scribe3 后端 API 入口。

物理拆分: 共享核与可 monkeypatch 符号在 ``scribe3/api/app_impl.py``；
领域路由在 ``scribe3/api/routers/*`` 与既有 ``health`` / ``intent_northstar``。

本模块在导入时将自身替换为 app_impl,保证:

- ``import scribe3.app as A`` 与实现模块是同一对象
- 测试 ``monkeypatch.setattr(A, ...)`` 作用于真实 handler 闭包全局
- ``from scribe3.app import app`` 仍可用

存储层物理拆分见 ``scribe3/store/`` 包。

拆分规范: docs/ARCHITECTURE_SPLIT_ROADMAP.md
"""
from __future__ import annotations

import sys

from scribe3.api import app_impl as _impl

# Domain routers (extracted from app_impl; bind handlers onto app_impl globals).
from scribe3.api.health import router as health_router
from scribe3.api.intent_northstar import router as intent_northstar_router
from scribe3.api.routers.chapters import router as chapters_router
from scribe3.api.routers.chat_threads import router as chat_threads_router
from scribe3.api.routers.codex import router as codex_router
from scribe3.api.routers.context_sessions import router as context_sessions_router
from scribe3.api.routers.experience import router as experience_router
from scribe3.api.routers.director import router as director_router
from scribe3.api.routers.ingest_import import router as ingest_import_router
from scribe3.api.routers.materials import router as materials_router
from scribe3.api.routers.memory import router as memory_router
from scribe3.api.routers.misc_routes import router as misc_routes_router
from scribe3.api.routers.product_backlog import router as product_backlog_router
from scribe3.api.routers.pilot_inbox import router as pilot_inbox_router
from scribe3.api.routers.quality import router as quality_router
from scribe3.api.routers.settings_gateway import router as settings_gateway_router
from scribe3.api.routers.works import router as works_router
from scribe3.api.routers.world_read import router as world_read_router
from scribe3.api.routers.write import router as write_router
from scribe3.api.routers.canon_loop import router as canon_loop_router
from scribe3.api.token_bridge import install_token_query_bridge
from scribe3.auth.middleware import install_l1_auth
from scribe3.auth.routes import router as auth_router
from scribe3.auth.admin_routes import router as admin_router
from scribe3.auth.users import ensure_bootstrap_users

# Exact paths still defined inline in app_impl that we peel to avoid double registration
# (health + intent already have dedicated routers).
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

# All domain routers included below — peel any residual app_impl routes that share paths.
_DOMAIN_ROUTERS = (
    health_router,
    intent_northstar_router,
    settings_gateway_router,
    context_sessions_router,
    chat_threads_router,
    memory_router,
    works_router,
    world_read_router,
    chapters_router,
    codex_router,
    materials_router,
    quality_router,
    write_router,
    ingest_import_router,
    pilot_inbox_router,
    experience_router,
    director_router,
    misc_routes_router,
    product_backlog_router,
    canon_loop_router,
    auth_router,
    admin_router,
)


def _paths_from_router(router) -> set[str]:
    out: set[str] = set()
    for r in router.routes:
        path = getattr(r, "path", None)
        if path:
            out.add(path)
    return out


_ALL_EXTRACTED: set[str] = set(_EXTRACTED_PATHS)
for _r in _DOMAIN_ROUTERS:
    _ALL_EXTRACTED |= _paths_from_router(_r)


def _is_extracted_route(path: str | None) -> bool:
    if not path:
        return False
    if path in _ALL_EXTRACTED:
        return True
    return any(path.startswith(p) for p in _EXTRACTED_PREFIXES)


# Peel extracted paths from app_impl (inline duplicates / residual).
_impl.app.router.routes[:] = [
    r for r in _impl.app.router.routes
    if not _is_extracted_route(getattr(r, "path", None))
]

for _router in _DOMAIN_ROUTERS:
    _impl.app.include_router(_router)

# Bootstrap admin/users when SCRIBE3_BOOTSTRAP_USERS set and auth DB empty.
try:
    ensure_bootstrap_users()
except Exception:
    pass

# L1 session + ownership (inner relative to token bridge).
install_l1_auth(_impl.app)

# Outermost: ?token= → Authorization Bearer (machine/SSE legacy bridge).
install_token_query_bridge(_impl.app)

if __name__ == "__main__":
    # `python -m scribe3.app` 是公开的后端启动约定。模块别名本身不会触发
    # app_impl 的 `if __name__ == "__main__"`，因此必须显式委托入口。
    _impl.main()
else:
    # 替换模块身份 → 测试与生产共用同一 globals
    sys.modules[__name__] = _impl

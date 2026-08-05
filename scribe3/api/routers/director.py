"""写作导演 API · WorkflowSnapshot。"""
from __future__ import annotations

import types

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["director"])


def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith("__"):
            continue
        if k not in g:
            g[k] = v


try:
    _import_core_defaults()
except Exception:
    pass


def workflow_snapshot_ep(work: str = "main", seq: int | None = None):
    """书/章进度单源：状态页与进度胶囊同源。"""
    from scribe3.director import build_workflow_snapshot
    st = _store_for(work)
    if st is None:
        raise HTTPException(503, "store 未就绪")
    snap = build_workflow_snapshot(st, work=work, seq=seq)
    # 契约守卫：禁止文学总分
    if "total_score" in snap or "composite_score" in snap:
        raise HTTPException(500, "snapshot 不得含 total_score")
    return snap


def _bind_and_register():
    from scribe3.api import app_impl as core
    g = globals()

    def _bind(name: str, path: str, methods: list[str]):
        _fn = g[name]
        _re = types.FunctionType(
            _fn.__code__, core.__dict__, name, _fn.__defaults__, _fn.__closure__)
        if _fn.__annotations__:
            _re.__annotations__ = dict(_fn.__annotations__)
        setattr(core, name, _re)
        g[name] = _re
        router.add_api_route(path, _re, methods=methods, name=name)

    _bind("workflow_snapshot_ep", "/workflow/snapshot", ["GET"])


_bind_and_register()

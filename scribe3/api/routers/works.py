"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import types
from typing import Any, Optional, List, Dict, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Body,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

router = APIRouter(tags=['works'])


# Import app_impl constants/models used as signature defaults (late-safe for helpers).
def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith('__'):
            continue
        if k not in g:
            g[k] = v
try:
    _import_core_defaults()
except Exception:
    pass  # core may be partially init during first import cycle


def works():
    # 作品注册表可有数百本书；为每个书卡建 Surreal 连接、跑迁移再查三次统计，会让
    # 新作者甚至无法进入刚建的空书。书库只复用已加载的连接；其余明确标待加载，绝不
    # 以 0 字/0 章冒充真实统计。打开该书后，其连接会进入缓存，下一次列表即可显示真值。
    with _stores_lock:
        loaded_stores = {slug: _stores.get(slug) for slug in _stores}
    out = []
    for w in list_works():
        store = loaded_stores.get(w["slug"])
        if store is None:
            out.append({**w, "stats_pending": True})
            continue
        try:
            st = store.stats()
            intent = store.get_intent()
            # 携带 total_word_goal 供书卡进度条使用;None 时前端回退 100000
            if intent.get("total_word_goal") is not None:
                st["total_word_goal"] = intent["total_word_goal"]
        except Exception:
            # U-011(作者要 fail-loud):删"假0"——查询失败返 chapter_count=0/word_count=0,
            # 作者会误读成"稿子丢了"。改为标 stats_error 让前端显"统计查询失败"(而非假0),
            # 且【每书隔离】——单书查询失败不拖垮整个书列表(否则一本坏书全列表 500 更糟)。
            logging.getLogger("scribe3").error(
                "/works stats 查询失败: %s", w.get("slug"), exc_info=True)
            st = {"stats_error": True}
        out.append({**w, **st})
    return out

def make_work(w: WorkIn):
    try:
        return create_work(w.title)
    except ValueError as e:
        raise HTTPException(409, str(e))

def rename(slug: str, w: WorkIn):
    try:
        rename_work(slug, w.title)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}

def works_archived():
    """废弃箱列表——须先于 GET /works/{slug}(若存在)注册,防动态路由把
    'archived' 当 slug 吞掉。当前无 GET /works/{slug},此处仅按纪律占位说明。"""
    return {"works": archived_works()}

def remove_work(slug: str):
    """软删:移入废弃箱(DB 不动,仅注册表标记 archived=true)。真删见 /works/{slug}/purge。"""
    try:
        archive_work(slug)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _stores.pop(slug, None)
    return {"ok": True, "archived": True}

def restore_work_ep(slug: str):
    try:
        restore_work(slug)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}

def purge_work_ep(slug: str, req: WorkPurgeReq):
    """永久删除,唯一真删入口——两道门:必须已在废弃箱 + confirm_title 与库中书名一致。
    书名比对不论该 slug 当前是否已废弃(未废弃时也要能拦 422/409),故活跃+废弃两表都查。"""
    rows = [w for w in list_works() + archived_works() if w["slug"] == slug]
    title = ((rows[0]["title"] if rows else None) or "").strip()
    confirm = (req.confirm_title or "").strip()
    # 空名守卫(与 store._guard_title 双保险):空名会让 ''=='' 恒真、强确认形同虚设。
    # store 层已从源头拒收空名,此处兜底历史脏数据里可能已存在的空名书。
    if not title or not confirm:
        raise HTTPException(422, "书名为空,无法确认永久删除;请先改名后再删")
    if confirm != title:
        raise HTTPException(422, "书名不匹配,永久删除已取消")
    try:
        delete_work(slug)
    except ValueError as e:
        raise HTTPException(409, str(e))
    _stores.pop(slug, None)
    return {"ok": True, "purged": True}



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['works']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'works', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'works', _re)
    g['works'] = _re
    router.add_api_route('/works', _re, methods=['GET'], name='works')

    _fn = g['make_work']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'make_work', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'make_work', _re)
    g['make_work'] = _re
    router.add_api_route('/works', _re, methods=['POST'], name='make_work')

    _fn = g['rename']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'rename', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'rename', _re)
    g['rename'] = _re
    router.add_api_route('/works/{slug}', _re, methods=['PATCH'], name='rename')

    _fn = g['works_archived']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'works_archived', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'works_archived', _re)
    g['works_archived'] = _re
    router.add_api_route('/works/archived', _re, methods=['GET'], name='works_archived')

    _fn = g['remove_work']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'remove_work', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'remove_work', _re)
    g['remove_work'] = _re
    router.add_api_route('/works/{slug}', _re, methods=['DELETE'], name='remove_work')

    _fn = g['restore_work_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'restore_work_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'restore_work_ep', _re)
    g['restore_work_ep'] = _re
    router.add_api_route('/works/{slug}/restore', _re, methods=['POST'], name='restore_work_ep')

    _fn = g['purge_work_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'purge_work_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'purge_work_ep', _re)
    g['purge_work_ep'] = _re
    router.add_api_route('/works/{slug}/purge', _re, methods=['DELETE'], name='purge_work_ep')

_bind_and_register()

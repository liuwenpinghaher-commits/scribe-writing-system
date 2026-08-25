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

router = APIRouter(tags=['materials'])


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


def list_materials_ep(kind: str | None = None, limit: int | None = Query(default=None, ge=1, le=500),
                      cursor: int = Query(default=0, ge=0), q: str = "", view: str = "all",
                      origin: str | None = None, work: str = "main",
                      mode: str = "bm25"):
    """素材列表:服务端 view/q/origin 过滤 + 偏移分页。limit 缺省返回数组(兼容旧客户端)。
    mode=hybrid 时在命中集上再按标题贴近度排。"""
    _check_material_kind(kind)
    page = _store_for(work).list_materials_page(
        kind=kind, view=view or "all", q=q or "", limit=limit, cursor=cursor, origin=origin,
        mode=mode or "bm25")
    if limit is None:
        return page["items"]
    return page

def materials_health_ep(work: str = "main"):
    """素材库健康度:从未召回 / 无 summary / 无标签计数。"""
    return _store_for(work).material_health_counts()

def add_material_ep(m: MaterialIn, work: str = "main"):
    _check_material_kind(m.kind)
    mid = _store_for(work).add_material(
        m.title, m.body, m.kind, m.tags, m.source,
        ref_tags=m.ref_tags, summary=m.summary, pinned=bool(m.pinned),
        origin="manual")
    return {"ok": True, "id": mid}

def edit_material_ep(mid: str, m: MaterialPatch, work: str = "main"):
    _check_material_kind(m.kind)
    fields = {k: v for k, v in m.model_dump().items() if v is not None}
    found = _store_for(work).update_material(mid, fields)
    if not found:
        raise HTTPException(status_code=404, detail=f"material '{mid}' 不存在")
    return {"ok": True}

def del_material_ep(mid: str, confirm_impact_token: str | None = None, work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), "material", mid, work, confirm_impact_token)

async def material_import_ep(background: BackgroundTasks, text: str = Form(None),
                            url: str = Form(None), source: str = Form(None),
                            file: UploadFile = File(None), work: str = "main"):
    """导入入口:file(markitdown)/url(可读正文+markitdown)/text → 后台 AI 切分 → job_id。"""
    import uuid
    markdown = ""
    if file is not None:
        import os
        import tempfile
        from scribe3.material_import import parse_to_markdown
        content = await file.read()
        suffix = os.path.splitext(file.filename or "")[1] or ".txt"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(content)
            tmp.close()
            markdown = parse_to_markdown(tmp.name)
        finally:
            os.unlink(tmp.name)
        source = source or file.filename
    elif url:
        from scribe3.material_import import parse_url_to_markdown
        try:
            markdown = parse_url_to_markdown(url)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"URL 解析失败: {e}") from e
        source = source or url
    elif text:
        markdown = text
    if not (markdown or "").strip():
        raise HTTPException(status_code=422, detail="无内容可导入(text/url/file 至少一个非空)")
    job_id = uuid.uuid4().hex[:12]
    job = {"stage": "解析完成", "done": False, "total": 0,
           "items": [], "error": "", "work": work, "source": source}
    _import_job_save(job_id, job)
    try:
        _store_for(work).purge_expired_import_jobs()
    except Exception:
        pass
    background.add_task(_run_import, job_id, markdown, source, work)
    return {"job_id": job_id}

async def material_import_progress_ep(job_id: str, work: str = "main"):
    """SSE 进度推送:解析→切分打标→待预览/完成/错误(0.5s 轮询,上限 5 分钟防挂)。"""
    import asyncio
    import json as _j

    async def gen():
        for _ in range(600):
            job = _import_job_get(job_id, work)
            if job is None:
                yield "data: " + _j.dumps({"stage": "not_found", "done": True}) + "\n\n"
                return
            yield ("data: " + _j.dumps({"stage": job["stage"], "done": job["done"],
                                        "total": job["total"], "error": job["error"]}) + "\n\n")
            if job["done"]:
                return
            await asyncio.sleep(0.5)
    from scribe3.api.sse import sse_response
    return sse_response(gen())

def material_import_preview_ep(job_id: str, work: str = "main"):
    """预览 AI 切分结果(作者编辑/删条/合并前)。"""
    job = _import_job_get(job_id, work)
    if job is None:
        raise HTTPException(status_code=404, detail=f"导入任务 '{job_id}' 不存在或已清理")
    return {"stage": job["stage"], "done": job["done"], "error": job["error"],
            "items": job["items"]}

def material_import_commit_ep(job_id: str, req: ImportCommitReq, work: str = "main"):
    """作者确认(可编辑后)→ 批量落库 + 建联想边。近重挡入库进 failed。origin=import。"""
    from scribe3.material_import import near_dup_block_reason
    job = _import_job_get(job_id, work)
    if job is None:
        raise HTTPException(status_code=404, detail=f"导入任务 '{job_id}' 不存在或已清理")
    if job.get("error"):
        raise HTTPException(status_code=409, detail=f"导入任务 '{job_id}' 已失败,不能确认")
    if not job.get("done"):
        raise HTTPException(status_code=409, detail=f"导入任务 '{job_id}' 尚未完成预览")
    st = _store_for(work)
    ids = []
    failed = []
    warnings = []
    for idx, it in enumerate(req.items):
        title = (it.get("title") or "").strip()
        if not title:
            failed.append({"index": idx, "title": "", "reason": "标题为空"})
            continue
        try:
            try:
                dups = st.find_near_duplicate_materials(
                    title, it.get("body"), threshold=0.88, limit=3)
                blocked = near_dup_block_reason(dups)
            except Exception as e:
                warnings.append({
                    "index": idx, "title": title, "stage": "near_dup_scan",
                    "reason": str(e)[:200],
                })
                blocked = None
            if blocked:
                failed.append({
                    "index": idx, "title": title, "reason": blocked,
                    "matches": dups,
                })
                continue
            mid = st.add_material(
                title, it.get("body"), it.get("kind") or "note",
                it.get("tags"), it.get("source"),
                ref_tags=it.get("ref_tags"),
                summary=it.get("summary"),
                pinned=bool(it.get("pinned")),
                origin="import")
            ids.append(mid)
            try:
                st.build_material_edges(mid)
            except Exception as e:
                warnings.append({
                    "index": idx,
                    "title": title,
                    "stage": "build_edges",
                    "reason": str(e),
                })
        except Exception as e:
            failed.append({"index": idx, "title": title, "reason": str(e)})
    _import_jobs.pop(job_id, None)
    try:
        st.delete_import_job(job_id)
    except Exception:
        pass
    return {"created": len(ids), "ids": ids, "failed": failed, "warnings": warnings}

def material_recall_ep(q: str, chapter: int | None = None, k: int = 5,
                       with_meta: bool = False, work: str = "main"):
    """素材三通道召回。with_meta=true 时返回 {items, degraded_sources}。"""
    degraded: list = []
    items = _store_for(work).material_recall(q, chapter, k, degraded_out=degraded)
    if with_meta:
        return {"items": items, "degraded_sources": degraded}
    # 兼容:默认仍返回数组;通道失败时附加不破坏 JSON 数组的方式——旧客户端只要 list。
    # 新客户端请 with_meta=1。
    return items

def material_graph_ep(focus: str | None = None, limit: int = Query(default=200, ge=1, le=2000),
                      hop: int = Query(default=1, ge=1, le=3), work: str = "main"):
    """素材记忆网络:节点+边;focus+hop 做 ego-neighborhood。"""
    return _store_for(work).material_graph(focus=focus, limit=limit, hop=hop)

def material_refs_by_chapter_ep(chapter: int, work: str = "main"):
    """反向溯源:本章参考了哪些素材(+ reason/dimension)。"""
    st = _store_for(work)
    rows = st.material_refs_by_chapter(chapter)
    out = []
    for r in rows:
        m = st.get_material(str(r.get("material_id"))) or {}
        out.append({**r, "title": m.get("title"), "kind": m.get("kind"), "source": m.get("source")})
    return out

def add_material_reference_ep(mid: str, req: MaterialReferenceIn, work: str = "main"):
    """作者采纳手动插入的素材后，显式写入双向溯源。"""
    st = _store_for(work)
    if st.get_material(mid) is None:
        raise HTTPException(status_code=404, detail=f"material '{mid}' 不存在")
    st.add_material_reference(
        mid, req.chapter, req.dimension, req.reason,
        via="manual_insert", ref_kind=req.ref_kind or "inspiration",
    )
    return {"ok": True, "ref_kind": req.ref_kind or "inspiration"}

def material_refs_ep(mid: str, work: str = "main"):
    """正向溯源:这条素材用在了哪些章。"""
    return _store_for(work).material_refs_by_material(mid)

def get_material_ep(mid: str, work: str = "main"):
    """单条素材(须注册在 /materials/recall|graph|health|import 之后,防路径吞没)。"""
    # 保留字拒绝,防止静态路径未注册时误 404 信息
    if mid in ("recall", "graph", "health", "import", "refs-by-chapter"):
        raise HTTPException(status_code=404, detail=f"unknown materials route '{mid}'")
    row = _store_for(work).get_material(mid)
    if not row:
        raise HTTPException(status_code=404, detail=f"material '{mid}' 不存在")
    return row



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['list_materials_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'list_materials_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'list_materials_ep', _re)
    g['list_materials_ep'] = _re
    router.add_api_route('/materials', _re, methods=['GET'], name='list_materials_ep')

    _fn = g['materials_health_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'materials_health_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'materials_health_ep', _re)
    g['materials_health_ep'] = _re
    router.add_api_route('/materials/health', _re, methods=['GET'], name='materials_health_ep')

    _fn = g['add_material_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_material_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_material_ep', _re)
    g['add_material_ep'] = _re
    router.add_api_route('/materials', _re, methods=['POST'], name='add_material_ep')

    _fn = g['edit_material_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'edit_material_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'edit_material_ep', _re)
    g['edit_material_ep'] = _re
    router.add_api_route('/materials/{mid}', _re, methods=['PATCH'], name='edit_material_ep')

    _fn = g['del_material_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_material_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_material_ep', _re)
    g['del_material_ep'] = _re
    router.add_api_route('/materials/{mid}', _re, methods=['DELETE'], name='del_material_ep')

    _fn = g['material_import_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_import_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_import_ep', _re)
    g['material_import_ep'] = _re
    router.add_api_route('/materials/import', _re, methods=['POST'], name='material_import_ep')

    _fn = g['material_import_progress_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_import_progress_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_import_progress_ep', _re)
    g['material_import_progress_ep'] = _re
    router.add_api_route('/materials/import/{job_id}/progress', _re, methods=['GET'], name='material_import_progress_ep')

    _fn = g['material_import_preview_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_import_preview_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_import_preview_ep', _re)
    g['material_import_preview_ep'] = _re
    router.add_api_route('/materials/import/{job_id}/preview', _re, methods=['GET'], name='material_import_preview_ep')

    _fn = g['material_import_commit_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_import_commit_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_import_commit_ep', _re)
    g['material_import_commit_ep'] = _re
    router.add_api_route('/materials/import/{job_id}/commit', _re, methods=['POST'], name='material_import_commit_ep')

    _fn = g['material_recall_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_recall_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_recall_ep', _re)
    g['material_recall_ep'] = _re
    router.add_api_route('/materials/recall', _re, methods=['GET'], name='material_recall_ep')

    _fn = g['material_graph_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_graph_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_graph_ep', _re)
    g['material_graph_ep'] = _re
    router.add_api_route('/materials/graph', _re, methods=['GET'], name='material_graph_ep')

    _fn = g['material_refs_by_chapter_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_refs_by_chapter_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_refs_by_chapter_ep', _re)
    g['material_refs_by_chapter_ep'] = _re
    router.add_api_route('/materials/refs-by-chapter', _re, methods=['GET'], name='material_refs_by_chapter_ep')

    _fn = g['add_material_reference_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_material_reference_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_material_reference_ep', _re)
    g['add_material_reference_ep'] = _re
    router.add_api_route('/materials/{mid}/refs', _re, methods=['POST'], name='add_material_reference_ep')

    _fn = g['material_refs_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'material_refs_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'material_refs_ep', _re)
    g['material_refs_ep'] = _re
    router.add_api_route('/materials/{mid}/refs', _re, methods=['GET'], name='material_refs_ep')

    _fn = g['get_material_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_material_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_material_ep', _re)
    g['get_material_ep'] = _re
    router.add_api_route('/materials/{mid}', _re, methods=['GET'], name='get_material_ep')

_bind_and_register()

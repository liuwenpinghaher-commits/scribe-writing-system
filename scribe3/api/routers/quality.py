"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import time
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

router = APIRouter(tags=['quality'])


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


def chapter_health_ep(seq: int, work: str = "main"):
    from scribe3.chapter_health import aggregate_chapter_health
    from scribe3.motif_heat import motif_overheat_advisory
    st = _store_for(work)
    pb = {}
    pc = {}
    rv = {}
    try:
        if hasattr(st, "get_frozen"):
            d = st.get_frozen("chapter_draft", seq) or st.get_frozen("duty_card", seq) or {}
            review = d.get("review") if isinstance(d, dict) else None
            pb = {
                "status": (review or {}).get("verdict") or ("ok" if d else "missing"),
                "ok": bool(d) and str((review or {}).get("verdict") or "pass") != "fail",
                "verdict": (review or {}).get("verdict"),
            }
            if isinstance(review, dict):
                rv = dict(review)
    except Exception:
        pb = {"status": "unknown"}
    try:
        if hasattr(st, "post_analysis_summary"):
            pc = st.post_analysis_summary(seq) or {}
            if isinstance(pc, dict) and "verdict" not in pc:
                if pc.get("present"):
                    pc["verdict"] = "pass" if pc.get("fp_match") is not False else "advisory"
                else:
                    pc["verdict"] = "unknown"
    except Exception:
        pc = pc or {}
    try:
        getter = getattr(st, "get_chapter_review_row", None)
        if callable(getter):
            row = getter(f"{work}_{int(seq)}") or {}
            if row:
                cov = row.get("coverage") or row.get("cov")
                rv = {**rv, **row}
                if cov is not None:
                    rv["coverage"] = cov.get("coverage") if isinstance(cov, dict) else cov
                if row.get("verdict"):
                    rv["verdict"] = row.get("verdict")
    except Exception:
        pass
    inst = []
    try:
        lister = getattr(st, "list_motif_instances", None)
        inst = lister(seq) if callable(lister) else []
    except Exception:
        inst = []
    h = aggregate_chapter_health(playbook=pb, post_check=pc, review=rv)
    h["motif_overheat"] = motif_overheat_advisory(inst)
    h["playbook"] = pb
    h["post_check"] = pc
    h["review"] = rv
    return h


def craft_gates(seq: int | None = Query(default=None, ge=1), work: str = "main"):
    """旧工艺闸已废。存正文走 finalize_gate。"""
    out: dict = {
        "work": work,
        "gate_a": {"ok": True, "retired": True},
        "ok": True,
        "message": "craft 节拍闸已废，改走 play-contract。",
    }
    if seq is not None:
        out["seq"] = seq
    return out

from scribe3.quality.cache import (
    _QUALITY_TTL,
    _QUALITY_TTL_SEC,
    invalidate_quality_cache,
    quality_cache_get,
    quality_cache_put,
)


def quality(work: str = "main"):
    """质量仪表盘聚合:每章 字数/双层QC问题/因果违规 + 伏笔状态。
    P3-e1 Fix 1: 使用 OVERDUE_SLACK 模块常量(唯一真源),支持 intent.overdue_threshold 覆盖;
    foreshadow.promises 含每条 promise 的 overdue 字段,前端直读,不重算。

    Phase0-BE1(千万字基座):**改读 outline() 章级缓存列**(qc_word_count/qc_issues/qc_causal/
    qc_breakdown),不再逐章 get_chapter 全文 + quality_flags 重算 + 逐章查因果图(数千章=分钟级)。
    缓存由 save_chapter 写时落库;若版本戳过期，响应明确标注而不把旧值伪装为当前结论。"""
    from scribe3.qc_product_keys import project_product_qc_breakdown
    st = _store_for(work)
    try:
        stamp = (work, int(st.max_chapter() or 0))
    except Exception:
        stamp = (work, None)
    cached = quality_cache_get(stamp)
    if cached is not None:
        return cached
    out = st.outline()
    per = []
    stale_chapters = []
    for c in out["chapters"]:
        cache_stale = c.get("qc_cache_revision") != QUALITY_CACHE_REVISION
        if cache_stale:
            stale_chapters.append(c["seq"])
        per.append({
            "seq": c["seq"], "title": c.get("title", ""),
            "word_count": c.get("word_count") or 0,
            "qc_issues": c.get("qc_issues") or 0,
            "qc_breakdown": project_product_qc_breakdown(c.get("qc_breakdown") or {}),
            "causal": c.get("qc_causal") or 0,
            "cache_stale": cache_stale,
        })
    # 缓存稳定章序按 seq 升序返回(与旧 list_chapters ORDER BY seq 口径一致)
    per.sort(key=lambda x: x["seq"])
    proms = st.list_promises()
    mc = st.max_chapter()
    # 单源阈值:intent 可覆盖 OVERDUE_SLACK(per-work 配置)
    # 经 list_promises 补算窗口后 legacy slack 分支仅数据异常行可达,threshold 近似废弃,留防御
    intent = st.get_intent()
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    prom_list = []
    for p in proms:
        is_overdue = _overdue_flag(p, mc, slack)
        prom_list.append({
            "id": p.get("id"), "text": p.get("text", ""),
            "setup_chapter": p.get("setup_chapter"), "status": p["status"],
            "kind": p.get("kind"), "overdue": is_overdue,
        })
    fore = {
        "open": sum(1 for p in proms if p["status"] == "open"),
        "closed": sum(1 for p in proms if p["status"] == "closed"),
        "overdue": sum(1 for p in prom_list if p["overdue"]),
        "promises": prom_list,
    }
    result = {"chapters": per, "foreshadow": fore, "total_words": sum(c["word_count"] for c in per),
            "cache_stale_chapters": sorted(stale_chapters),
            "cache_revision": QUALITY_CACHE_REVISION}
    quality_cache_put(stamp, result)
    return result

def accept_advisory_ep(seq: int, work: str = "main"):
    from scribe3.advisory_ttl import accept_advisory
    out = accept_advisory(_store_for(work), seq)
    if not out.get("ok"):
        code = out.get("code") or ""
        status = 409 if code == "expired" else 404
        raise HTTPException(status_code=status, detail=out)
    return out


def refresh_quality(work: str = "main"):
    """作者显式刷新本书过期质量缓存；仅更新派生列，不触碰正文和正典数据。"""
    for key in list(_QUALITY_TTL):
        if key[0] == work:
            _QUALITY_TTL.pop(key, None)
    refreshed = _store_for(work).refresh_quality_caches()
    return {"ok": True, "refreshed_chapters": refreshed,
            "cache_revision": QUALITY_CACHE_REVISION}



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    # quality/refresh 经 FunctionType 绑到 app_impl.__dict__，缓存符号必须进 core，
    # 否则 GET /quality 运行时 NameError: quality_cache_get。
    for _name in (
        "_QUALITY_TTL", "_QUALITY_TTL_SEC",
        "invalidate_quality_cache", "quality_cache_get", "quality_cache_put",
    ):
        if _name in g:
            setattr(core, _name, g[_name])
    _fn = g['craft_gates']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'craft_gates', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'craft_gates', _re)
    g['craft_gates'] = _re
    router.add_api_route('/craft-gates', _re, methods=['GET'], name='craft_gates')

    _fn = g['quality']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'quality', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'quality', _re)
    g['quality'] = _re
    router.add_api_route('/quality', _re, methods=['GET'], name='quality')

    _fn = g['refresh_quality']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'refresh_quality', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'refresh_quality', _re)
    g['refresh_quality'] = _re
    router.add_api_route('/quality/refresh', _re, methods=['POST'], name='refresh_quality')

    _fn = g['chapter_health_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'chapter_health_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'chapter_health_ep', _re)
    g['chapter_health_ep'] = _re
    router.add_api_route('/chapters/{seq}/health', _re, methods=['GET'], name='chapter_health_ep')

    _fn = g['accept_advisory_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'accept_advisory_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'accept_advisory_ep', _re)
    g['accept_advisory_ep'] = _re
    router.add_api_route('/chapters/{seq}/accept-advisory', _re, methods=['POST'], name='accept_advisory_ep')

_bind_and_register()

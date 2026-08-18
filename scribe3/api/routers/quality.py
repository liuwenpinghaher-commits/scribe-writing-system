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


def craft_gates(seq: int | None = Query(default=None, ge=1), work: str = "main"):
    """工艺优先门闩只读投影(GATE-A / 可选 B+C-Det+D)。

    e2e 与 CLI 同源:scribe3.verify_craft_compliance。
    seq 省略 → 只跑 GATE-A;给出 seq → 附加该章 B/C/D 与 journey 汇总。
    """
    st = _store_for(work)
    out: dict = {
        "work": work,
        "gate_a": {"ok": True, "retired": True},
        "ok": True,
        "message": "craft 节拍闸已废，改走 play-contract。",
    }
    return out
    ga = None
    if seq is not None:
        gb = gate_b(st, seq)
        gc = audit_chapter_det(st, seq)
        gd = gate_d(st, seq)
        out["gate_b"] = to_jsonable(gb)
        out["gate_c_det"] = to_jsonable(gc)
        out["gate_d"] = to_jsonable(gd)
        out["seq"] = seq
        out["ok"] = ga.ok and gb.ok and gc.ok and gd.ok
        out["journey"] = journey_pass(
            gate_a_ok=ga.ok,
            chapters=[{
                "seq": seq,
                "gate_b_ok": gb.ok,
                "gate_c_ok": gc.ok,
                "gate_d_ok": gd.ok,
            }],
        )
    return out

def quality(work: str = "main"):
    """质量仪表盘聚合:每章 字数/双层QC问题/因果违规 + 伏笔状态。
    P3-e1 Fix 1: 使用 OVERDUE_SLACK 模块常量(唯一真源),支持 intent.overdue_threshold 覆盖;
    foreshadow.promises 含每条 promise 的 overdue 字段,前端直读,不重算。

    Phase0-BE1(千万字基座):**改读 outline() 章级缓存列**(qc_word_count/qc_issues/qc_causal/
    qc_breakdown),不再逐章 get_chapter 全文 + quality_flags 重算 + 逐章查因果图(数千章=分钟级)。
    缓存由 save_chapter 写时落库;若版本戳过期，响应明确标注而不把旧值伪装为当前结论。"""
    from scribe3.qc_product_keys import project_product_qc_breakdown
    st = _store_for(work)
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
    return {"chapters": per, "foreshadow": fore, "total_words": sum(c["word_count"] for c in per),
            "cache_stale_chapters": sorted(stale_chapters),
            "cache_revision": QUALITY_CACHE_REVISION}

def refresh_quality(work: str = "main"):
    """作者显式刷新本书过期质量缓存；仅更新派生列，不触碰正文和正典数据。"""
    refreshed = _store_for(work).refresh_quality_caches()
    return {"ok": True, "refreshed_chapters": refreshed,
            "cache_revision": QUALITY_CACHE_REVISION}



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
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

_bind_and_register()

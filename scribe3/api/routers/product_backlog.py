"""延期产品 backlog 路由（O18–O23 / O30–O33 · 薄 API · 默认旗关）。"""
from __future__ import annotations

import types
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(tags=["product_backlog"])


def storyline_gantt_ep(work: str = "main"):
    """O30：故事线 Gantt 投影（只读）。"""
    from scribe3.storyline_project import project_gantt_rows
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        chapters = list(st.list_chapters() or []) if hasattr(st, "list_chapters") else []
        prom = []
        if hasattr(st, "open_promises"):
            prom = list(st.open_promises() or [])
        elif hasattr(st, "list_promises"):
            prom = list(st.list_promises() or [])
    except Exception:
        chapters, prom = [], []
    return project_gantt_rows(chapters, open_promises=prom)


def storyline_emotion_ep(work: str = "main"):
    """O31：情绪/张力曲线（启发式 · 非文学分）。"""
    from scribe3.storyline_project import project_emotion_curve
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        chapters = list(st.list_chapters() or []) if hasattr(st, "list_chapters") else []
    except Exception:
        chapters = []
    return project_emotion_curve(chapters)


def chapter_stage_get_ep(seq: int, work: str = "main"):
    """O19：当前阶段。"""
    from scribe3.chapter_stage import stage_from_chapter_dict, PHASES, stage_machine_enabled
    ch = {}
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        ch = st.get_chapter(int(seq)) or {}
    except Exception:
        ch = {}
    phase = stage_from_chapter_dict(ch)
    return {
        "seq": int(seq),
        "work": work,
        "phase": phase,
        "phases": list(PHASES),
        "enabled": stage_machine_enabled(),
        "severity": "advisory",
    }


def chapter_stage_advance_ep(seq: int, req: dict | None = None, work: str = "main"):
    """O19：推进阶段（默认 soft）。"""
    from scribe3.chapter_stage import (
        transition, stage_from_chapter_dict, stage_machine_hard,
    )
    payload = req if isinstance(req, dict) else {}
    action = str(payload.get("action") or "advance")
    ch = {}
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        ch = st.get_chapter(int(seq)) or {}
    except Exception:
        ch = {}
    cur = payload.get("current") or stage_from_chapter_dict(ch)
    result = transition(cur, action)
    # soft 持久化 next 到 stage_state（fail-soft）
    if result.get("next") and not result.get("blocked"):
        try:
            from scribe3.api import app_impl as core
            st = core._store_for(work)
            if hasattr(st, "update_chapter_meta") or hasattr(st, "patch_chapter"):
                # 最小：若有 set 字段 API
                pass
            if hasattr(st, "_execute_write"):
                st._execute_write(
                    "UPDATE type::record('chapter',$seq) SET stage_state=$ss",
                    {"seq": int(seq), "ss": {"phase": result["next"]}},
                )
        except Exception:
            result["persist"] = "skipped"
        else:
            result["persist"] = "ok"
    result["seq"] = int(seq)
    result["work"] = work
    return result


def parallel_deduce_plan_ep(seq: int, req: dict | None = None, work: str = "main"):
    """O22：并行演绎 dry-run plan。"""
    from scribe3.parallel_deduce import build_parallel_deduce_plan
    payload = req if isinstance(req, dict) else {}
    focals = payload.get("focalizers") or payload.get("viewpoints") or []
    if isinstance(focals, str):
        focals = [focals]
    plan = build_parallel_deduce_plan(
        int(seq),
        list(focals),
        max_parallel=int(payload.get("max_parallel") or 2),
        work=work,
    )
    # 可选占锁探测
    if payload.get("lock_probe"):
        from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
        r = acquire_chapter_lock("run", work, int(seq))
        plan["lock"] = r.as_dict()
        if r.ok:
            release_chapter_lock("run", work, int(seq))
    return plan


def agent_crons_list_ep():
    """O23：cron 目录。"""
    from scribe3.agent_crons import load_cron_catalog, agent_cron_ui_enabled
    return {
        "jobs": load_cron_catalog(),
        "enabled_flag": agent_cron_ui_enabled(),
        "surface": "agent_crons.list",
    }


def agent_crons_enable_ep(name: str, req: dict | None = None):
    """O23：启停覆盖（进程内）。"""
    from scribe3.agent_crons import set_cron_enabled
    payload = req if isinstance(req, dict) else {}
    en = payload.get("enabled")
    if en is None:
        en = True
    return set_cron_enabled(name, bool(en))


def benchmarks_list_ep():
    from scribe3.benchmark_lib import list_benchmarks, benchmark_lib_enabled
    return {
        "items": list_benchmarks(),
        "enabled_flag": benchmark_lib_enabled(),
        "surface": "benchmark.list",
    }


def benchmarks_upsert_ep(req: dict | None = None):
    from scribe3.benchmark_lib import upsert_benchmark
    payload = req if isinstance(req, dict) else {}
    return upsert_benchmark(payload)


def benchmarks_delete_ep(bid: str):
    from scribe3.benchmark_lib import delete_benchmark
    return {"id": bid, "deleted": delete_benchmark(bid)}


def storyline_inject_preview_ep(req: dict | None = None):
    """O33：注入 polish 预览。"""
    from scribe3.storyline_inject_polish import build_storyline_inject_segment
    from scribe3.storyline_project import project_gantt_rows, project_emotion_curve
    payload = req if isinstance(req, dict) else {}
    chapters = payload.get("chapters") or []
    gantt = project_gantt_rows(chapters)
    emo = project_emotion_curve(chapters)
    focus = payload.get("focus_seq")
    pt = None
    if focus and emo.get("points"):
        pt = next((p for p in emo["points"] if p.get("seq") == int(focus)), None)
    return build_storyline_inject_segment(
        focus_seq=int(focus) if focus else None,
        gantt_rows=gantt.get("rows"),
        open_promise_texts=payload.get("open_promises") or [],
        emotion_point=pt,
    )


def _bind_and_register() -> None:
    from scribe3.api import app_impl as core
    g = globals()
    routes = [
        ("storyline_gantt_ep", "/storyline/gantt", ["GET"]),
        ("storyline_emotion_ep", "/storyline/emotion-curve", ["GET"]),
        ("chapter_stage_get_ep", "/chapters/{seq}/stage", ["GET"]),
        ("chapter_stage_advance_ep", "/chapters/{seq}/stage/advance", ["POST"]),
        ("parallel_deduce_plan_ep", "/chapters/{seq}/deduce/parallel", ["POST"]),
        ("agent_crons_list_ep", "/agent-crons", ["GET"]),
        ("agent_crons_enable_ep", "/agent-crons/{name}/enable", ["POST"]),
        ("benchmarks_list_ep", "/benchmarks", ["GET"]),
        ("benchmarks_upsert_ep", "/benchmarks", ["POST"]),
        ("benchmarks_delete_ep", "/benchmarks/{bid}", ["DELETE"]),
        ("storyline_inject_preview_ep", "/storyline/inject-preview", ["POST"]),
    ]
    for name, path, methods in routes:
        fn = g[name]
        re = types.FunctionType(fn.__code__, core.__dict__, name, fn.__defaults__, fn.__closure__)
        if fn.__annotations__:
            re.__annotations__ = dict(fn.__annotations__)
        setattr(core, name, re)
        g[name] = re
        router.add_api_route(path, re, methods=methods, name=name)


_bind_and_register()

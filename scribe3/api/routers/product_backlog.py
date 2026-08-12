"""延期产品 backlog 路由（O18–O23 / O30–O33 · 薄 API · 默认旗关）。"""
from __future__ import annotations

import types
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(tags=["product_backlog"])


def _storyline_chapters(st) -> list:
    """故事线用窄章列表：优先 chapters_lite（synopsis/beats），避免全量 prose。"""
    if st is None:
        return []
    if hasattr(st, "chapters_lite"):
        try:
            return list(st.chapters_lite() or [])
        except Exception:
            pass
    if hasattr(st, "list_chapters"):
        try:
            return list(st.list_chapters() or [])
        except Exception:
            pass
    return []


def _storyline_promises(st) -> list:
    if st is None:
        return []
    try:
        if hasattr(st, "open_promises"):
            return list(st.open_promises() or [])
        if hasattr(st, "list_promises"):
            return list(st.list_promises() or [])
    except Exception:
        pass
    return []


def storyline_gantt_ep(work: str = "main"):
    """O30：故事线 Gantt 投影（只读）。"""
    from scribe3.storyline_project import project_gantt_rows
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        chapters = _storyline_chapters(st)
        prom = _storyline_promises(st)
    except Exception:
        chapters, prom = [], []
    return project_gantt_rows(chapters, open_promises=prom)


def storyline_emotion_ep(work: str = "main"):
    """O31：情绪/张力曲线（启发式 · 非文学分）。"""
    from scribe3.storyline_project import project_emotion_curve
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        chapters = _storyline_chapters(st)
    except Exception:
        chapters = []
    return project_emotion_curve(chapters)


def storyline_hub_ep(work: str = "main"):
    """故事线中枢一次打包：单次取章，避免 4 次 list_chapters + 串行往返。"""
    from scribe3.storyline_project import project_gantt_rows, project_emotion_curve
    from scribe3.storyline_store import list_storylines as mem_list
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
    except Exception:
        st = None
    chapters = _storyline_chapters(st)
    prom = _storyline_promises(st)
    gantt = project_gantt_rows(chapters, open_promises=prom)
    emotion = project_emotion_curve(chapters)
    lines: list = []
    backend = "memory"
    try:
        if st is not None and hasattr(st, "list_storylines"):
            lines = list(st.list_storylines() or [])
            backend = "surreal"
        else:
            lines = list(mem_list(work) or [])
    except Exception:
        try:
            lines = list(mem_list(work) or [])
        except Exception:
            lines = []
    align = emotion.get("craft_align")
    if not align:
        try:
            from scribe3.craft_ruler import craft_ruler_report
            align = craft_ruler_report(emotion.get("points") or [])
        except Exception:
            align = None
    return {
        "work": work,
        "gantt": gantt,
        "emotion": emotion,
        "storylines": lines,
        "count_lines": len(lines),
        "align": align,
        "backend": backend,
        "chapter_source": "chapters_lite",
    }


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
    """O19：推进阶段（默认 soft）。

    action=set + phase=…：soft 写任意合法 phase（作者 local 同步）。
    """
    from scribe3.chapter_stage import (
        transition, stage_from_chapter_dict, stage_machine_hard, normalize_phase, PHASES,
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
    # soft set：next = payload.phase（须合法）
    if action.strip().lower() == "set":
        tgt = normalize_phase(str(payload.get("phase") or payload.get("next") or ""))
        if tgt not in PHASES:
            return {
                "ok": False,
                "blocked": False,
                "current": cur,
                "next": cur,
                "action": "set",
                "advisories": ["invalid_phase"],
                "severity": "advisory",
                "seq": int(seq),
                "work": work,
                "phases": list(PHASES),
            }
        result = transition(tgt, "set")
        result["current"] = cur
        result["next"] = tgt
    else:
        result = transition(cur, action)
    # soft 持久化 next 到 stage_state（fail-soft）
    if result.get("next") and not result.get("blocked"):
        persisted = "skipped"
        try:
            from scribe3.api import app_impl as core
            st = core._store_for(work)
            ss = {"phase": result["next"]}
            if hasattr(st, "update_chapter_meta"):
                ok = st.update_chapter_meta(int(seq), {"stage_state": ss})
                persisted = "ok" if ok else "skipped"
            elif hasattr(st, "_execute_write"):
                st._execute_write(
                    "UPDATE type::record('chapter',$seq) SET stage_state=$ss",
                    {"seq": int(seq), "ss": ss},
                )
                persisted = "ok"
        except Exception:
            persisted = "skipped"
        result["persist"] = persisted
    result["seq"] = int(seq)
    result["work"] = work
    return result


def parallel_deduce_plan_ep(seq: int, req: dict | None = None, work: str = "main"):
    """O22：并行演绎 plan；body.execute=true 时真跑（限并发 · soft 失败）。"""
    from scribe3.parallel_deduce import (
        build_parallel_deduce_plan,
        execute_parallel_deduce,
        parallel_deduce_enabled,
    )
    payload = req if isinstance(req, dict) else {}
    focals = payload.get("focalizers") or payload.get("viewpoints") or []
    if isinstance(focals, str):
        focals = [focals]
    mode = str(payload.get("mode") or "preview")
    plan = build_parallel_deduce_plan(
        int(seq),
        list(focals),
        max_parallel=int(payload.get("max_parallel") or 2),
        work=work,
        mode=mode,
    )
    # 可选占锁探测（dry）
    if payload.get("lock_probe") and not payload.get("execute"):
        from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
        r = acquire_chapter_lock("run", work, int(seq))
        plan["lock"] = r.as_dict()
        if r.ok:
            release_chapter_lock("run", work, int(seq))
    # 显式 execute=true 才真跑；默认 dry-run
    if payload.get("execute") in (True, 1, "1", "true", "yes"):
        if not parallel_deduce_enabled():
            plan["execute"] = False
            plan["error"] = "PARALLEL_DEDUCE_disabled"
            return plan
        timeout_s = float(payload.get("timeout_s") or 120)
        use_lock = payload.get("lock", True) not in (False, 0, "0", "false")
        return execute_parallel_deduce(
            plan,
            lock=use_lock,
            timeout_s=timeout_s,
        )
    return plan


def agent_crons_list_ep():
    """O23：cron 目录 + Hermes 聚合（Phase1 · 不 mutate timer）。"""
    from scribe3.agent_crons import build_agent_crons_response
    return build_agent_crons_response()


def agent_crons_enable_ep(name: str, req: dict | None = None):
    """O23：启停覆盖（仅 catalog · 不改 Hermes timer）。"""
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


def benchmarks_advisory_preview_ep(bid: str):
    """Benchmark advisory 预览（不写正文）。"""
    from scribe3.benchmark_lib import build_advisory_preview
    return build_advisory_preview(bid)


def soak_ep(req: dict | None = None, work: str = "main"):
    """A9：浸泡前置 · 产出 seed_words（不写正典）。

    Body: {seq/chapter, focalizer, dry_run?}
    dry_run=true 或不传 complete 时只返回 prompt 预览。
    """
    payload = req if isinstance(req, dict) else {}
    seq = int(payload.get("seq") or payload.get("chapter") or 0)
    focalizer = str(payload.get("focalizer") or "").strip()
    dry = payload.get("dry_run") in (True, 1, "1", "true", "yes") or not payload.get("execute")
    if seq < 1:
        return {"ok": False, "error": "seq_required", "seed_words": [], "surface": "soak"}
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(str(payload.get("work") or work or "main"))
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "seed_words": [], "surface": "soak"}
    from scribe3.soak import build_soak_prompt, parse_soak, soak
    try:
        prompt = build_soak_prompt(st, seq, focalizer or "role:default")
    except Exception as e:
        return {"ok": False, "error": f"prompt:{e}"[:200], "seed_words": [], "surface": "soak"}
    if dry:
        return {
            "ok": True,
            "dry_run": True,
            "prompt_preview": (prompt or "")[:800],
            "seed_words": [],
            "surface": "soak",
            "note": "execute=true 才调 LLM；默认 dry_run",
        }
    try:
        from scribe3.llm import hermes_complete
        def _fn(p: str) -> str:
            return str(hermes_complete(p, max_tokens=200) or "")
    except Exception:
        def _fn(p: str) -> str:
            return ""
    try:
        out = soak(st, seq, focalizer or "role:default", _fn)
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)[:200],
            "seed_words": [],
            "surface": "soak",
            "severity": "soft",
        }
    return {
        "ok": True,
        "dry_run": False,
        "emotion_arc": out.get("emotion_arc"),
        "turn": out.get("turn"),
        "seed_words": out.get("seed_words") or [],
        "surface": "soak",
        "note": "seed_words 供写路径外部传入；本端点不自动改 prose",
    }


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


def storyline_list_ep(work: str = "main"):
    """GAP-16：列出独立 storyline 实体（优先 Surreal，降级进程内）。"""
    from scribe3.storyline_store import list_storylines as mem_list
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        if hasattr(st, "list_storylines"):
            rows = st.list_storylines() or []
            # 空列表也算 Surreal 真相源（勿因 empty 误降级到 memory）
            return {"work": work, "storylines": rows, "count": len(rows), "backend": "surreal"}
    except Exception:
        pass
    rows = mem_list(work)
    return {"work": work, "storylines": rows, "count": len(rows), "backend": "memory"}


def storyline_create_ep(req: dict | None = None, work: str = "main"):
    """GAP-16：创建 storyline（可编辑，优先持久化）。"""
    from scribe3.storyline_store import create_storyline as mem_create
    payload = req if isinstance(req, dict) else {}
    w = str(payload.get("work") or work or "main")
    title = str(payload.get("title") or "")
    arc_kind = str(payload.get("arc_kind") or "main")
    chapter_seqs = list(payload.get("chapter_seqs") or [])
    notes = str(payload.get("notes") or "")
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(w)
        if hasattr(st, "create_storyline"):
            row = st.create_storyline(
                title=title, arc_kind=arc_kind,
                chapter_seqs=chapter_seqs, notes=notes,
            )
            if row and row.get("persisted") is not False:
                return row
    except Exception:
        pass
    return mem_create(w, title=title, arc_kind=arc_kind, chapter_seqs=chapter_seqs, notes=notes)


def storyline_patch_ep(sid: str, req: dict | None = None, work: str = "main"):
    from scribe3.storyline_store import update_storyline as mem_update
    payload = req if isinstance(req, dict) else {}
    w = str(payload.get("work") or work or "main")
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(w)
        if hasattr(st, "update_storyline"):
            row = st.update_storyline(
                sid,
                title=payload.get("title"),
                arc_kind=payload.get("arc_kind"),
                chapter_seqs=payload.get("chapter_seqs"),
                notes=payload.get("notes"),
            )
            if row:
                return row
    except Exception:
        pass
    row = mem_update(
        w, sid,
        title=payload.get("title"),
        arc_kind=payload.get("arc_kind"),
        chapter_seqs=payload.get("chapter_seqs"),
        notes=payload.get("notes"),
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "storyline not found")
    return row


def storyline_link_chapter_ep(sid: str, req: dict | None = None, work: str = "main"):
    from scribe3.storyline_store import link_chapter as mem_link
    payload = req if isinstance(req, dict) else {}
    w = str(payload.get("work") or work or "main")
    seq = int(payload.get("seq") or payload.get("chapter") or 0)
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(w)
        if hasattr(st, "link_storyline_chapter"):
            row = st.link_storyline_chapter(sid, seq)
            if row:
                return row
    except Exception:
        pass
    row = mem_link(w, sid, seq)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "storyline not found")
    return row


def storyline_craft_align_ep(work: str = "main"):
    """GAP-19：技法标尺对标报告。"""
    from scribe3.storyline_project import project_emotion_curve
    from scribe3.craft_ruler import craft_ruler_report
    try:
        from scribe3.api import app_impl as core
        st = core._store_for(work)
        chapters = _storyline_chapters(st)
    except Exception:
        chapters = []
    emo = project_emotion_curve(chapters)
    return {
        "work": work,
        "emotion": emo,
        "align": emo.get("craft_align") or craft_ruler_report(emo.get("points") or []),
    }


def _bind_and_register() -> None:
    from scribe3.api import app_impl as core
    g = globals()
    # 供 rebind 后的 endpoint 全局可见（FunctionType 用 core.__dict__ 作 globals）
    for helper in ("_storyline_chapters", "_storyline_promises"):
        if helper in g:
            setattr(core, helper, g[helper])
    routes = [
        ("storyline_gantt_ep", "/storyline/gantt", ["GET"]),
        ("storyline_emotion_ep", "/storyline/emotion-curve", ["GET"]),
        ("storyline_hub_ep", "/storyline/hub", ["GET"]),
        ("storyline_list_ep", "/storyline/lines", ["GET"]),
        ("storyline_create_ep", "/storyline/lines", ["POST"]),
        ("storyline_patch_ep", "/storyline/lines/{sid}", ["PATCH"]),
        ("storyline_link_chapter_ep", "/storyline/lines/{sid}/link", ["POST"]),
        ("storyline_craft_align_ep", "/storyline/craft-align", ["GET"]),
        ("chapter_stage_get_ep", "/chapters/{seq}/stage", ["GET"]),
        ("chapter_stage_advance_ep", "/chapters/{seq}/stage/advance", ["POST"]),
        ("parallel_deduce_plan_ep", "/chapters/{seq}/deduce/parallel", ["POST"]),
        ("agent_crons_list_ep", "/agent-crons", ["GET"]),
        ("agent_crons_enable_ep", "/agent-crons/{name}/enable", ["POST"]),
        ("benchmarks_list_ep", "/benchmarks", ["GET"]),
        ("benchmarks_upsert_ep", "/benchmarks", ["POST"]),
        ("benchmarks_delete_ep", "/benchmarks/{bid}", ["DELETE"]),
        ("benchmarks_advisory_preview_ep", "/benchmarks/{bid}/advisory-preview", ["POST"]),
        ("storyline_inject_preview_ep", "/storyline/inject-preview", ["POST"]),
        ("soak_ep", "/soak", ["POST"]),
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

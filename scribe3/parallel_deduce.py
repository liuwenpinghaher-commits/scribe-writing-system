"""并行多视角演绎（O22 · 默认 dry-run · execute 显式 · 不 fork Hermes）。"""
from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

_log = logging.getLogger("scribe3.parallel_deduce")

CompleteFn = Callable[[dict[str, Any]], dict[str, Any]]


def parallel_deduce_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_PARALLEL_DEDUCE") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def build_parallel_deduce_plan(
    chapter: int,
    focalizers: list[str] | None = None,
    *,
    max_parallel: int = 2,
    work: str = "main",
) -> dict[str, Any]:
    """生成 N 路 deduce run 计划（profile=scribe3_deduce）。

    不发起 LLM；execute 由调用方旗控。
    """
    focals = [str(f).strip() for f in (focalizers or []) if str(f).strip()]
    if not focals:
        focals = ["_default"]
    cap = max(1, min(6, int(max_parallel or 2)))
    runs = []
    for i, f in enumerate(focals[:cap]):
        runs.append({
            "index": i,
            "focalizer": f if f != "_default" else "",
            "profile": "scribe3_deduce",
            "api_env": "HERMES_DEDUCE_RUNS_API",
            "run_scope": f"chapter:{int(chapter)}:deduce",
            "work": work or "main",
            "chapter": int(chapter),
            "system_hint": (
                f"限知视角：{f}。只读工具；演绎不得直写 prose。"
                if f != "_default"
                else "限知演绎；只读工具；不得直写 prose。"
            ),
        })
    return {
        "chapter": int(chapter),
        "work": work or "main",
        "runs": runs,
        "max_parallel": cap,
        "dry_run": True,
        "execute": False,
        "enabled_flag": parallel_deduce_enabled(),
        "lock_kind": "run",
        "surface": "parallel_deduce.plan",
        "note": "execute 须显式二次确认；默认只返回 plan",
    }


def _default_complete_fn(run_spec: dict[str, Any]) -> dict[str, Any]:
    """默认完成入口：尝试 Hermes/deduce 现成路径；失败 soft。

    不 fork Hermes；仅调宿主已有 complete/ai_run 入口（若可导入）。
    """
    focal = str(run_spec.get("focalizer") or "") or "_default"
    work = str(run_spec.get("work") or "main")
    chapter = int(run_spec.get("chapter") or 0)
    # 优先：可注入的 mock 友好路径 —— 调用方应传 complete_fn
    # 生产：尝试 hermes_runtime / ai 薄封装
    try:
        from scribe3 import hermes_runtime as hr  # type: ignore
        if hasattr(hr, "complete_deduce_focalizer"):
            return hr.complete_deduce_focalizer(
                work=work, chapter=chapter, focalizer=focal, profile="scribe3_deduce",
            )
    except Exception as e:
        _log.debug("hermes complete_deduce_focalizer unavailable: %s", e)
    # 无 LLM 时返回 stub（便于 dry 结构与测试）；真正 execute 应注入 complete_fn
    return {
        "status": "stub",
        "summary": f"[stub] parallel deduce focalizer={focal} chapter={chapter}",
        "tool_trace_ok": False,
        "note": "no complete_fn / hermes path; inject complete_fn for real runs",
    }


def execute_parallel_deduce(
    plan: dict[str, Any] | None = None,
    *,
    chapter: int | None = None,
    focalizers: list[str] | None = None,
    max_parallel: int = 2,
    work: str = "main",
    complete_fn: CompleteFn | None = None,
    lock: bool = True,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """真跑 N 路并行演绎（限并发、章锁、soft 失败）。

    - 默认 complete_fn 可注入（单测 mock）
    - lock=True 时整批 acquire chapter_lock(kind=run)
    - 超时与单路失败不抛穿；汇总 status
    """
    if not parallel_deduce_enabled():
        return {
            "execute": False,
            "enabled_flag": False,
            "results": [],
            "error": "PARALLEL_DEDUCE_disabled",
            "surface": "parallel_deduce.execute",
        }

    if plan is None:
        plan = build_parallel_deduce_plan(
            int(chapter or 0),
            focalizers,
            max_parallel=max_parallel,
            work=work,
        )
    else:
        plan = dict(plan)

    runs = list(plan.get("runs") or [])
    cap = max(1, min(6, int(plan.get("max_parallel") or max_parallel or 2)))
    work_s = str(plan.get("work") or work or "main")
    ch = int(plan.get("chapter") or chapter or 0)
    fn = complete_fn or _default_complete_fn

    lock_info: dict[str, Any] | None = None
    locked = False
    if lock and ch > 0:
        try:
            from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
            r = acquire_chapter_lock("run", work_s, ch)
            lock_info = r.as_dict() if hasattr(r, "as_dict") else {"ok": bool(getattr(r, "ok", False))}
            locked = bool(getattr(r, "ok", False))
            if not locked:
                return {
                    "execute": True,
                    "dry_run": False,
                    "chapter": ch,
                    "work": work_s,
                    "results": [],
                    "lock": lock_info,
                    "error": "chapter_busy",
                    "surface": "parallel_deduce.execute",
                    "enabled_flag": True,
                }
        except Exception as e:
            lock_info = {"ok": False, "error": str(e)}
            # fail-open soft：无锁模块时继续（单测/薄环境）
            locked = False
            _log.warning("parallel_deduce lock fail-soft: %s", e)

    results: list[dict[str, Any]] = []
    t0 = time.time()

    def _one(spec: dict[str, Any]) -> dict[str, Any]:
        focal = str(spec.get("focalizer") or "") or "_default"
        row: dict[str, Any] = {
            "index": spec.get("index"),
            "focalizer": "" if focal == "_default" else focal,
            "status": "error",
            "summary": "",
            "tool_trace_ok": False,
        }
        try:
            out = fn(dict(spec))
            if not isinstance(out, dict):
                out = {"summary": str(out), "status": "ok"}
            row["status"] = str(out.get("status") or "ok")
            row["summary"] = str(out.get("summary") or out.get("text") or "")[:4000]
            row["tool_trace_ok"] = bool(out.get("tool_trace_ok", True))
            if out.get("error"):
                row["error"] = str(out["error"])[:500]
                if row["status"] == "ok":
                    row["status"] = "error"
        except Exception as e:
            row["status"] = "error"
            row["error"] = str(e)[:500]
            row["summary"] = ""
            row["tool_trace_ok"] = False
        return row

    try:
        if cap <= 1 or len(runs) <= 1:
            for spec in runs:
                if time.time() - t0 > timeout_s:
                    results.append({
                        "index": spec.get("index"),
                        "focalizer": spec.get("focalizer") or "",
                        "status": "timeout",
                        "summary": "",
                        "tool_trace_ok": False,
                        "error": "batch_timeout",
                    })
                    break
                results.append(_one(spec))
        else:
            with ThreadPoolExecutor(max_workers=cap) as pool:
                futs = {pool.submit(_one, spec): spec for spec in runs}
                for fut in as_completed(futs, timeout=timeout_s):
                    try:
                        results.append(fut.result(timeout=max(1.0, timeout_s - (time.time() - t0))))
                    except Exception as e:
                        spec = futs[fut]
                        results.append({
                            "index": spec.get("index"),
                            "focalizer": spec.get("focalizer") or "",
                            "status": "error",
                            "summary": "",
                            "tool_trace_ok": False,
                            "error": str(e)[:500],
                        })
    except TimeoutError:
        for spec in runs:
            if not any(r.get("index") == spec.get("index") for r in results):
                results.append({
                    "index": spec.get("index"),
                    "focalizer": spec.get("focalizer") or "",
                    "status": "timeout",
                    "summary": "",
                    "tool_trace_ok": False,
                    "error": "batch_timeout",
                })
    finally:
        if locked and ch > 0:
            try:
                from scribe3.chapter_lock import release_chapter_lock
                release_chapter_lock("run", work_s, ch)
            except Exception:
                pass

    results.sort(key=lambda r: int(r.get("index") or 0))
    ok_n = sum(1 for r in results if r.get("status") in ("ok", "stub"))
    return {
        "execute": True,
        "dry_run": False,
        "chapter": ch,
        "work": work_s,
        "plan": {k: plan[k] for k in ("runs", "max_parallel", "surface") if k in plan},
        "results": results,
        "ok_count": ok_n,
        "fail_count": len(results) - ok_n,
        "elapsed_s": round(time.time() - t0, 3),
        "lock": lock_info,
        "enabled_flag": True,
        "surface": "parallel_deduce.execute",
        "severity": "soft",
        "note": "单路失败 soft；不 fork Hermes",
    }

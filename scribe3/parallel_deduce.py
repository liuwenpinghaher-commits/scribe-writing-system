"""并行多视角演绎（O22 · 默认 dry-run · execute 显式 · 不 fork Hermes）。

默认 mode=preview → scribe3_deduce_preview + HERMES_DEDUCE_PREVIEW_RUNS_API (:8646)。
mode=deduce → full profile :8645。
stub 不得计入 ok_count。
"""
from __future__ import annotations

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

_log = logging.getLogger("scribe3.parallel_deduce")

CompleteFn = Callable[[dict[str, Any]], dict[str, Any]]

_TERMINAL_OK = frozenset({"completed", "complete", "succeeded", "success", "done"})
_TERMINAL_FAIL = frozenset({"failed", "error", "cancelled", "canceled", "timeout", "expired"})
_FOCAL_SLUG_RE = re.compile(r"[^a-zA-Z0-9_]+")


def parallel_deduce_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_PARALLEL_DEDUCE") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def parallel_deduce_llm_enabled() -> bool:
    """显式 LLM 执行旗（默认开；关则 execute 仅返回 plan 错误）。"""
    raw = (os.environ.get("SCRIBE3_PARALLEL_DEDUCE_LLM") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def parallel_deduce_max() -> int:
    """产品 cap：默认 2，env 可调 1–6。"""
    raw = (os.environ.get("SCRIBE3_PARALLEL_DEDUCE_MAX") or "2").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 2
    return max(1, min(6, n))


def clamp_max_parallel(requested: int | None) -> int:
    env_max = parallel_deduce_max()
    try:
        body = int(requested or env_max)
    except (TypeError, ValueError):
        body = env_max
    return max(1, min(env_max, body, 6))


def _mode_profile(mode: str) -> tuple[str, str, str]:
    """返回 (mode, profile, api_env)。"""
    m = (mode or "preview").strip().lower()
    if m in ("deduce", "full", "write"):
        return "deduce", "scribe3_deduce", "HERMES_DEDUCE_RUNS_API"
    return "preview", "scribe3_deduce_preview", "HERMES_DEDUCE_PREVIEW_RUNS_API"


def build_parallel_deduce_plan(
    chapter: int,
    focalizers: list[str] | None = None,
    *,
    max_parallel: int = 2,
    work: str = "main",
    mode: str = "preview",
) -> dict[str, Any]:
    """生成 N 路 deduce run 计划。

    不发起 LLM；execute 由调用方显式 true。
    """
    focals = [str(f).strip() for f in (focalizers or []) if str(f).strip()]
    if not focals:
        focals = ["_default"]
    cap = clamp_max_parallel(max_parallel)
    mode_s, profile, api_env = _mode_profile(mode)
    phase = "deduce_preview" if mode_s == "preview" else "deduce"
    runs = []
    for i, f in enumerate(focals[:cap]):
        runs.append({
            "index": i,
            "focalizer": f if f != "_default" else "",
            "profile": profile,
            "api_env": api_env,
            "mode": mode_s,
            "run_scope": f"chapter:{int(chapter)}:{phase}",
            "work": work or "main",
            "chapter": int(chapter),
            "system_hint": (
                f"限知视角：{f}。只读工具；不得写 prose / 不得 s3_patch_chapter_plan。"
                if mode_s == "preview" and f != "_default"
                else (
                    f"限知视角：{f}。演绎工作台合同。"
                    if f != "_default"
                    else (
                        "限知演绎预览；只读工具；不得直写 prose。"
                        if mode_s == "preview"
                        else "限知演绎；工具面受 profile 约束。"
                    )
                )
            ),
        })
    return {
        "chapter": int(chapter),
        "work": work or "main",
        "mode": mode_s,
        "profile": profile,
        "api_env": api_env,
        "runs": runs,
        "max_parallel": cap,
        "dry_run": True,
        "execute": False,
        "enabled_flag": parallel_deduce_enabled(),
        "lock_kind": "run",
        "surface": "parallel_deduce.plan",
        "note": "execute 须显式 true；默认 dry-run；preview=:8646 / deduce=:8645",
    }


def _focal_slug(focal: str) -> str:
    """HTTP session_key 必须 latin-1 安全：中文视角 → 短 hash，禁止入 header。"""
    import hashlib
    raw = (focal or "default").strip() or "default"
    ascii_part = _FOCAL_SLUG_RE.sub("_", raw)
    # 若含非 ASCII 或清洗后为空，用 hash 保证 header 安全
    if not ascii_part.isascii() or not ascii_part or ascii_part == "_" or any(
        ord(c) > 127 for c in raw
    ):
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        prefix = re.sub(r"[^a-zA-Z0-9]", "", ascii_part)[:8] or "f"
        return f"{prefix}_{h}"[:48]
    return ascii_part[:48]


def _extract_summary(status: dict[str, Any], events: list[dict[str, Any]] | None = None) -> str:
    if not isinstance(status, dict):
        return ""
    for key in ("output", "summary", "text", "result", "final_output"):
        v = status.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()[:4000]
        if isinstance(v, dict):
            for kk in ("text", "content", "output"):
                if isinstance(v.get(kk), str) and v[kk].strip():
                    return v[kk].strip()[:4000]
    # nested data
    data = status.get("data") if isinstance(status.get("data"), dict) else {}
    for key in ("output", "text", "summary"):
        if isinstance(data.get(key), str) and data[key].strip():
            return data[key].strip()[:4000]
    if events:
        chunks: list[str] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            t = str(ev.get("type") or ev.get("event") or "")
            if "delta" in t or "output" in t or "completed" in t or "message" in t:
                for kk in ("text", "delta", "content", "output"):
                    if isinstance(ev.get(kk), str) and ev[kk].strip():
                        chunks.append(ev[kk])
        if chunks:
            return "".join(chunks)[-4000:]
    return ""


def tool_trace_status(
    events: list[dict[str, Any]] | None,
    *,
    require_get_chapter: bool,
    events_fetch_ok: bool = True,
) -> str:
    """工具痕迹三态：``ok`` | ``missing`` | ``unknown``。

    - 不要求读章（非 preview）→ ok
    - 事件流拉取失败/空且无法判断 → unknown（**不**当 missing 假红）
    - 有 events 且见 s3_get_chapter 完成 → ok
    - 有 events 但无读章 → missing
    """
    if not require_get_chapter:
        return "ok"
    if not events_fetch_ok:
        return "unknown"
    if not events:
        return "unknown"
    saw_get = False
    for ev in events:
        if not isinstance(ev, dict):
            continue
        blob = str(ev)
        name = str(ev.get("name") or ev.get("tool") or ev.get("tool_name") or "")
        if "s3_get_chapter" in name or "s3_get_chapter" in blob:
            t = str(ev.get("type") or ev.get("event") or "").lower()
            if "fail" in t or "error" in t:
                continue
            saw_get = True
            break
    return "ok" if saw_get else "missing"


def _tool_trace_ok(events: list[dict[str, Any]] | None, *, require_get_chapter: bool) -> bool | None:
    """兼容布尔：ok→True, missing→False, unknown→None（勿当失败红）。"""
    st = tool_trace_status(events, require_get_chapter=require_get_chapter)
    if st == "ok":
        return True
    if st == "missing":
        return False
    return None


def complete_deduce_focalizer(
    run_spec: dict[str, Any],
    *,
    poll_interval_s: float = 1.0,
    max_wait_s: float = 90.0,
) -> dict[str, Any]:
    """真路径：HermesRuntime create_run + poll status + 可选 events。

    不 fork Hermes。失败 soft → status error/timeout/degraded。
    """
    from scribe3.hermes_runtime import HermesRuntime, scribe3_session_key

    focal = str(run_spec.get("focalizer") or "") or "_default"
    work = str(run_spec.get("work") or "main")
    chapter = int(run_spec.get("chapter") or 0)
    profile = str(run_spec.get("profile") or "scribe3_deduce_preview")
    api_env = str(run_spec.get("api_env") or "HERMES_DEDUCE_PREVIEW_RUNS_API")
    mode = str(run_spec.get("mode") or "preview")
    require_get = mode == "preview"

    # resolve api base
    api_base = (os.environ.get(api_env) or "").strip()
    if not api_base:
        try:
            from scribe3.settings import get_setting
            api_base = str(get_setting(api_env) or "").strip()
        except Exception:
            api_base = ""
    if not api_base:
        # defaults by mode
        api_base = (
            "http://127.0.0.1:8646/v1" if mode == "preview" else "http://127.0.0.1:8645/v1"
        )

    session_key = scribe3_session_key(
        work, scope=f"parallel_deduce:{chapter}:{_focal_slug(focal)}",
    )
    hint = str(run_spec.get("system_hint") or "")
    input_text = (
        f"第 {chapter} 章并行演绎（mode={mode}）。"
        f"视角：{focal if focal != '_default' else '默认'}。\n"
        f"{hint}\n"
        "先调用 s3_get_chapter 读取本章；输出可供作者对照的限知摘要 markdown。"
        "不得写正典、不得调用写工具。"
        if mode == "preview"
        else (
            f"第 {chapter} 章并行演绎（full）。视角：{focal if focal != '_default' else '默认'}。\n"
            f"{hint}"
        )
    )
    instructions = (
        "你是铜炉限知演绎助手。preview 模式仅只读工具；禁止 s3_save_chapter / patch prose。"
        if mode == "preview"
        else "你是铜炉演绎助手；遵守 profile 工具白名单。"
    )

    rt = HermesRuntime(api_base=api_base, profile=profile)
    try:
        created = rt.create_run(
            input_text,
            instructions=instructions,
            session_key=session_key,
            timeout=min(60.0, max_wait_s),
        )
    except Exception as e:
        _log.warning("parallel deduce create_run fail: %s", e)
        return {
            "status": "error",
            "summary": "",
            "error": f"create_run:{e}"[:500],
            "tool_trace_ok": False,
            "run_id": None,
        }

    run_id = (
        created.get("id")
        or created.get("run_id")
        or (created.get("run") or {}).get("id")
        if isinstance(created, dict)
        else None
    )
    if not run_id:
        return {
            "status": "error",
            "summary": "",
            "error": "no_run_id",
            "tool_trace_ok": False,
            "raw_create": created if isinstance(created, dict) else None,
        }

    t0 = time.time()
    last_status: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    while time.time() - t0 < max_wait_s:
        try:
            last_status = rt.run_status(str(run_id), session_key=session_key, timeout=30.0)
        except Exception as e:
            _log.debug("run_status fail-soft: %s", e)
            time.sleep(poll_interval_s)
            continue
        st = str(
            last_status.get("status")
            or last_status.get("state")
            or (last_status.get("run") or {}).get("status")
            or ""
        ).lower()
        if st in _TERMINAL_OK or st in _TERMINAL_FAIL:
            break
        time.sleep(poll_interval_s)
    else:
        st = "timeout"

    # best-effort events
    events_fetch_ok = True
    try:
        for ev in rt.run_events(str(run_id), session_key=session_key, timeout=15.0):
            if isinstance(ev, dict):
                events.append(ev)
            if len(events) > 200:
                break
    except Exception as e:
        events_fetch_ok = False
        _log.debug("run_events fail-soft: %s", e)

    summary = _extract_summary(last_status, events)
    tstat = tool_trace_status(
        events, require_get_chapter=require_get, events_fetch_ok=events_fetch_ok,
    )
    tool_ok = True if tstat == "ok" else (False if tstat == "missing" else None)
    st = str(
        last_status.get("status")
        or last_status.get("state")
        or st
        or ""
    ).lower()

    if st in _TERMINAL_FAIL or st == "timeout":
        status_out = "timeout" if st == "timeout" else "error"
    elif st in _TERMINAL_OK:
        if summary:
            status_out = "ok"
        else:
            status_out = "degraded"
            summary = summary or "[degraded] run completed without extractable output"
    else:
        status_out = "timeout" if time.time() - t0 >= max_wait_s else "error"

    # best-effort ai_run_trace
    try:
        from scribe3.api import app_impl as core
        st_store = core._store_for(work)
        if hasattr(st_store, "upsert_ai_run_trace"):
            st_store.upsert_ai_run_trace({
                "run_id": str(run_id),
                "work": work,
                "chapter": chapter,
                "phase": "deduce_preview" if mode == "preview" else "deduce",
                "profile": profile,
                "status": status_out,
                "surface": "parallel_deduce",
                "focalizer": "" if focal == "_default" else focal,
            })
    except Exception:
        pass

    return {
        "status": status_out,
        "summary": summary,
        "tool_trace_status": tstat if status_out in ("ok", "degraded") else "unknown",
        # None = unknown：调用方勿当 fail 红
        "tool_trace_ok": tool_ok if status_out in ("ok", "degraded") else False,
        "run_id": str(run_id),
        "mode": mode,
        "profile": profile,
        "note": "audit depth: best-effort; tool_trace_status ok|missing|unknown",
    }


def _default_complete_fn(run_spec: dict[str, Any]) -> dict[str, Any]:
    """默认完成入口：调用 complete_deduce_focalizer；失败不返回假绿 stub-as-ok。"""
    if not parallel_deduce_llm_enabled():
        return {
            "status": "error",
            "summary": "",
            "error": "PARALLEL_DEDUCE_LLM_disabled",
            "tool_trace_ok": False,
        }
    try:
        from scribe3 import hermes_runtime as hr  # type: ignore
        if hasattr(hr, "complete_deduce_focalizer"):
            return hr.complete_deduce_focalizer(
                work=str(run_spec.get("work") or "main"),
                chapter=int(run_spec.get("chapter") or 0),
                focalizer=str(run_spec.get("focalizer") or ""),
                profile=str(run_spec.get("profile") or "scribe3_deduce_preview"),
            )
    except Exception as e:
        _log.debug("hermes complete_deduce_focalizer unavailable: %s", e)
    try:
        return complete_deduce_focalizer(run_spec)
    except Exception as e:
        _log.warning("complete_deduce_focalizer failed: %s", e)
        return {
            "status": "error",
            "summary": "",
            "error": str(e)[:500],
            "tool_trace_ok": False,
            "note": "no silent stub success",
        }


def execute_parallel_deduce(
    plan: dict[str, Any] | None = None,
    *,
    chapter: int | None = None,
    focalizers: list[str] | None = None,
    max_parallel: int = 2,
    work: str = "main",
    mode: str = "preview",
    complete_fn: CompleteFn | None = None,
    lock: bool = True,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """真跑 N 路并行演绎（限并发、章锁、soft 失败）。"""
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
            mode=mode,
        )
    else:
        plan = dict(plan)

    runs = list(plan.get("runs") or [])
    cap = clamp_max_parallel(plan.get("max_parallel") or max_parallel)
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
                    "ok_count": 0,
                    "fail_count": 0,
                    "all_stub": False,
                }
        except Exception as e:
            lock_info = {"ok": False, "error": str(e)}
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
            row["status"] = str(out.get("status") or "error")
            row["summary"] = str(out.get("summary") or out.get("text") or "")[:4000]
            # 三态：unknown 时 tool_trace_ok 为 None（勿 bool() 抹掉）
            if "tool_trace_status" in out:
                row["tool_trace_status"] = out.get("tool_trace_status")
            tok = out.get("tool_trace_ok", False)
            row["tool_trace_ok"] = tok if tok is None or isinstance(tok, bool) else bool(tok)
            if out.get("run_id"):
                row["run_id"] = out["run_id"]
            if out.get("error"):
                row["error"] = str(out["error"])[:500]
            if out.get("note"):
                row["note"] = str(out["note"])[:300]
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
    # K: stub 不得计入 ok_count（仅 status==ok）
    ok_n = sum(1 for r in results if r.get("status") == "ok")
    stub_n = sum(1 for r in results if r.get("status") == "stub")
    fail_n = len(results) - ok_n
    return {
        "execute": True,
        "dry_run": False,
        "chapter": ch,
        "work": work_s,
        "mode": plan.get("mode") or mode,
        "plan": {k: plan[k] for k in ("runs", "max_parallel", "surface", "profile", "api_env", "mode") if k in plan},
        "results": results,
        "ok_count": ok_n,
        "fail_count": fail_n,
        "stub_count": stub_n,
        "all_stub": bool(results) and stub_n == len(results),
        "elapsed_s": round(time.time() - t0, 3),
        "lock": lock_info,
        "enabled_flag": True,
        "surface": "parallel_deduce.execute",
        "severity": "soft",
        "note": "ok_count 仅 status=ok；stub/error/timeout 不计成功；不 fork Hermes",
    }

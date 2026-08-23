"""Play-contract facade. Old outline/beats chain is gone."""
from __future__ import annotations

import logging
from typing import Any, Callable, Mapping

_log = logging.getLogger("scribe3.stage_generate")

from scribe3.playbook.prompts import IDENTITY_NOVELIST
from scribe3.playbook.stages import (
    STAGE_MAX_TOKENS,
    extra_authors,
    normalize_stage,
    reject_gone_stage,
    stage_max_tokens,
)
from weakref import WeakKeyDictionary

from scribe3.playbook.pipeline import run_stage
from scribe3.playbook.parse import strip_fence as _strip_fence
from scribe3.playbook.context import GUIDE_SLOT_KEYS, build_ctx
from scribe3.playbook.memory_store import MemoryPlaybookStore
from scribe3.playbook.stages import parse_force

_PLAYBOOK_STORES: WeakKeyDictionary = WeakKeyDictionary()

LlmFn = Callable[..., str]
PersistFn = Callable[[dict], Any]


def planning_system_prompt() -> str:
    return IDENTITY_NOVELIST


def stage_skips_editor_chrome(phase: str | None) -> bool:
    return normalize_stage(phase) in ("duty", "design", "deduce", "draft")


def stage_skips_drama_vacuum(phase: str | None) -> bool:
    return normalize_stage(phase) in ("duty", "design", "deduce")


def stage_skips_craft_engine(phase: str | None) -> bool:
    return True


def stage_skips_structure_diversity(phase: str | None) -> bool:
    return True


def stage_skips_continue_snapshot(phase: str | None) -> bool:
    return normalize_stage(phase) in ("duty", "design")


def stage_is_planning_paper(phase: str | None) -> bool:
    return normalize_stage(phase) in ("duty", "design")


def stage_skips_secret_guard(phase: str | None) -> bool:
    return stage_is_planning_paper(phase)


def stage_spec(phase: str | None) -> dict[str, Any]:
    p = normalize_stage(phase)
    gone = reject_gone_stage(p)
    if gone:
        return {"stage": p, "gone": True, "message": gone["message"]}
    return {
        "stage": p,
        "persist_tool": "s3_generate_stage",
        "max_tokens": stage_max_tokens(p),
        "short_kernel": "duty → design → deduce → draft → final",
    }


def stage_craft_kernel(phase: str | None) -> str:
    return ""


def stage_ready(ch, stage, *, store=None, seq=None) -> dict[str, Any]:
    stg = normalize_stage(stage)
    gone = reject_gone_stage(stg)
    if gone:
        return {"ok": False, "code": "stage_gone", **gone}
    need = {
        "design": "duty_card",
        "deduce": "chapter_play",
        "draft": "chapter_deduce",
        "final": "chapter_draft",
    }.get(stg)
    if need is None or store is None or seq is None:
        return {"ok": True, "missing": [], "stage": stg, "message": ""}
    frozen = store.get_frozen(need, int(seq)) if hasattr(store, "get_frozen") else None
    if frozen:
        return {"ok": True, "missing": [], "stage": stg, "message": ""}
    return {
        "ok": False,
        "code": "stage_not_ready",
        "stage": stg,
        "missing": [{"id": need}],
        "message": f"还不能进{stg}：上一层未冻结",
    }


def stage_not_ready_http(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "code": report.get("code") or "stage_not_ready",
        "message": report.get("message") or "上一阶段未齐",
        "missing": list(report.get("missing") or []),
        "stage": report.get("stage"),
        "hint": "先跑上一层 duty/design/deduce/draft 直到冻结。",
    }


def iceberg_ok_for(ch, field, *, store=None, seq=None) -> bool:
    return True


def resolve_stage_focalizer(req_focalizer: str | None, chapter: Mapping[str, Any] | None) -> str:
    hit = str(req_focalizer or "").strip()
    if hit:
        return hit
    ch = chapter if isinstance(chapter, dict) else {}
    return str(ch.get("focalizer") or "").strip()


class _EmptyBook:
    names: tuple = ()
    lines: tuple = ()
    duty_who: tuple = ()
    duty_event: str = ""
    duty_bill: str = ""


def load_design_book(st, seq, ch, extra: str = ""):
    return _EmptyBook()


def dispatch_design_stage(stg: str, ch, *, extra: str = "") -> dict | None:
    gone = reject_gone_stage(stg)
    if gone:
        return gone
    if extra_authors(extra):
        return {
            "ok": False,
            "code": "extra_authors",
            "missing": ["extra_authors"],
            "message": "extra 不得当作者：禁止「必须原样 / 必须有一句 / 必须以时空」",
        }
    return None


def _emit_fate_artifacts(kind, out, fields, ch) -> None:
    return None


def _missing_bucket(mid: str) -> str:
    return str(mid or "")


def draft_full_block(ch) -> str:
    if isinstance(ch, dict):
        return str(ch.get("draft") or "")
    return ""


def _as_playbook_store(st):
    if st is None:
        return MemoryPlaybookStore()
    if all(hasattr(st, n) for n in ("get_frozen", "insert", "next_version", "mark_superseded")):
        return st
    try:
        mem = _PLAYBOOK_STORES.get(st)
        if mem is None:
            mem = MemoryPlaybookStore()
            _PLAYBOOK_STORES[st] = mem
        return mem
    except TypeError:
        # 仅测试替身入此路，生产路径已收敛到 WeakKeyDictionary。
        existing = getattr(st, "_playbook_mem", None)
        if existing is not None and all(
            hasattr(existing, n) for n in ("get_frozen", "insert", "next_version", "mark_superseded")
        ):
            return existing
        mem = MemoryPlaybookStore()
        try:
            setattr(st, "_playbook_mem", mem)
        except Exception:
            pass
        return mem


def _emit_upstream_guide_span(ctx: Mapping[str, Any] | None) -> None:
    from scribe3.pipeline_trace_hooks import playbook_span_end, playbook_span_start
    ctx = ctx or {}
    failed = [str(x) for x in (ctx.get("_guide_fail") or []) if x]
    payload = {k: len(str(ctx.get(k) or "")) for k in GUIDE_SLOT_KEYS}
    payload["failed"] = failed
    sid = playbook_span_start("playbook.upstream_guide")
    if not sid:
        return
    missing = bool(failed)
    playbook_span_end(
        sid,
        status="failed" if missing else "ok",
        actual="missing" if missing else "present",
        actual_reason="upstream_guide_missing" if missing else None,
        compute=payload,
    )


def thicken_stage(
    stage: str,
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    gone = reject_gone_stage(stage)
    if gone:
        return gone
    work_s = work or getattr(st, "db_name", None) or "main"
    n_lock = int(seq or 1)
    owned_lock = False
    try:
        from scribe3.chapter_lock import (
            acquire_chapter_lock, release_chapter_lock, chapter_lock_held_here,
        )
        if st is not None and not chapter_lock_held_here(work_s, n_lock):
            clr = acquire_chapter_lock("run", work_s, n_lock, store=st, ttl_seconds=1200)
            if not clr.ok:
                return {
                    "ok": False,
                    "code": "chapter_busy",
                    "status": "busy",
                    "message": clr.detail or "本章正在执行",
                }
            owned_lock = True
    except Exception:
        owned_lock = False
    try:
        return _thicken_stage_body(
            stage, ch, llm_fn=llm_fn, persist_fn=persist_fn, seq=seq,
            extra=extra, st=st, work=work, focalizer=focalizer,
        )
    finally:
        if owned_lock:
            try:
                from scribe3.chapter_lock import release_chapter_lock
                release_chapter_lock("run", work_s, n_lock, store=st)
            except Exception:
                pass


def _thicken_stage_body(
    stage: str,
    ch: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: PersistFn | None = None,
    seq: int | None = None,
    extra: str = "",
    st=None, work=None, focalizer: str = "",
) -> dict[str, Any]:
    try:
        from scribe3.feature_flags import flag_truthy
        if flag_truthy("SCRIBE3_OUTLINE_STATUS_GATE"):
            from scribe3.outline_status import should_block_stage
            stg = normalize_stage(stage)
            status = str((ch or {}).get("outline_status") or "").strip()
            if should_block_stage(stg, status):
                return {
                    "ok": False,
                    "code": "outline_stale",
                    "message": "这章的纲改过还没核对。核完了对主编说冻回去。对话里续写不拦，那是逃生口。",
                }
    except Exception as exc:
        _log.warning("outline_status gate fail-open: %s", type(exc).__name__)
        try:
            from scribe3.pipeline_trace_hooks import note_guide_missing
            note_guide_missing("outline_gate_fail_open")
        except Exception:
            pass
    store = _as_playbook_store(st)
    n = int(seq or 1)
    if normalize_stage(stage) == "duty":
        from scribe3.playbook.duty_gate import refuse_empty_synopsis
        blocked = refuse_empty_synopsis(
            {"synopsis": (ch or {}).get("synopsis"), "seq": n},
            store=st, seq=n,
        )
        if blocked:
            return blocked
    if normalize_stage(stage) == "final" and not parse_force(extra):
        if str((ch or {}).get("prose") or "").strip():
            return {"ok": True, "skipped": True, "status": "already_frozen"}
    world = st if st is not None else store
    ctx = build_ctx(world, n, focalizer=focalizer, playbook=store)
    if str((ch or {}).get("synopsis") or "").strip() and not str(ctx.get("synopsis") or "").strip():
        ctx["synopsis"] = str(ch.get("synopsis") or "").strip()
    if str((ch or {}).get("prose") or "").strip():
        ctx["has_prose"] = True
        ctx["existing_prose"] = str((ch or {}).get("prose") or "")
    _emit_upstream_guide_span(ctx)
    out = run_stage(store, n, normalize_stage(stage), extra=extra, llm_fn=llm_fn, ctx=ctx, persist=persist_fn is not None or st is not None)
    if persist_fn and out.get("ok") and not out.get("skipped"):
        fields: dict[str, Any] = {}
        if out.get("prose"):
            fields["prose"] = out["prose"]
        draft = out.get("artifact") if normalize_stage(stage) == "draft" else None
        if isinstance(draft, dict) and draft.get("text"):
            fields["draft"] = draft["text"]
        if fields:
            persist_fn(fields)
        else:
            snap = {k: out.get(k) for k in ("synopsis", "beats", "goal", "choice", "duty") if out.get(k)}
            if snap:
                persist_fn(snap)
    return out


def _call_llm(llm_fn, prompt, max_tokens=4096):
    try:
        return llm_fn(prompt, max_tokens=max_tokens)
    except TypeError:
        return llm_fn(prompt)

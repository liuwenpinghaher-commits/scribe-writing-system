"""Play-contract facade. Old outline/beats chain is gone."""
from __future__ import annotations

from typing import Any, Callable, Mapping

from scribe3.playbook.prompts import IDENTITY_NOVELIST
from scribe3.playbook.stages import (
    STAGE_MAX_TOKENS,
    extra_authors,
    normalize_stage,
    reject_gone_stage,
    stage_max_tokens,
)
from scribe3.playbook.pipeline import run_stage
from scribe3.playbook.parse import strip_fence as _strip_fence
from scribe3.playbook.context import available_cast, available_lines, build_ctx, prev_hook_quote
from scribe3.playbook.memory_store import MemoryPlaybookStore

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
    mem = MemoryPlaybookStore()
    setattr(st, "_playbook_mem", mem)
    return mem


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
    store = _as_playbook_store(st)
    n = int(seq or 1)
    ctx = build_ctx(store, n, focalizer=focalizer)
    if st is not None and store is not st:
        ctx["available_cast"] = available_cast(st)
        ctx["available_lines"] = available_lines(st)
        ctx["prev_hook_quote"] = prev_hook_quote(store, n)
    out = run_stage(store, n, normalize_stage(stage), extra=extra, llm_fn=llm_fn, ctx=ctx, persist=persist_fn is not None or st is not None)
    if persist_fn and out.get("ok"):
        fields: dict[str, Any] = {}
        if out.get("prose"):
            fields["prose"] = out["prose"]
        draft = out.get("artifact") if normalize_stage(stage) == "draft" else None
        if isinstance(draft, dict) and draft.get("text"):
            fields["draft"] = draft["text"]
        if fields:
            persist_fn(fields)
    return out


def _call_llm(llm_fn, prompt, max_tokens=4096):
    try:
        return llm_fn(prompt, max_tokens=max_tokens)
    except TypeError:
        return llm_fn(prompt)

"""Five-layer orchestration: generate → judge → struct. force/rewrite semantics."""
from __future__ import annotations

import json
from typing import Any, Callable

from scribe3.playbook.envelope import pass_review
from scribe3.playbook.errors import FrozenAssetError, StageGone
from scribe3.playbook.judge import judge, majority_if_disagreed
from scribe3.playbook.context import gender_roster
from scribe3.playbook.layers import gen_contract, gen_deduce, gen_draft, gen_duty, gen_final, gen_play, gen_state
from scribe3.playbook.memory_store import (
    MemoryPlaybookStore,
    freeze_artifact,
    overwrite_play,
    supersede_downstream,
)
from scribe3.playbook.parse import InfraError, ParseError
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.stages import (
    GONE_STAGES,
    LIVE_STAGES,
    MIGRATE_HINT,
    extra_authors,
    normalize_stage,
    parse_force,
    parse_rewrite,
    reject_gone_stage,
)
from scribe3.playbook.structural import (
    check_chapter_state_struct,
    check_contract_struct,
    check_deduce_struct,
    check_draft_struct,
    check_duty_struct,
    check_final_last_mile,
    check_final_struct,
    check_play_struct,
)

MAX_QUALITY_ROUNDS = 5
_TABLE = {
    "duty": "duty_card",
    "play": "chapter_play",
    "contract": "chapter_contract",
    "deduce": "chapter_deduce",
    "draft": "chapter_draft",
    "state": "chapter_state",
}


def _roster(ctx: dict[str, Any]) -> list[dict[str, str]]:
    if ctx.get("gender_roster"):
        return list(ctx.get("gender_roster") or [])
    return gender_roster(ctx.get("prev_state"), ctx.get("cast_cards"))


def _continuity_judge(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "prev_state": ctx.get("prev_state"),
        "imagery": ctx.get("imagery") or "",
    }


def _trace(store: Any, rec: dict[str, Any]) -> None:
    fn = getattr(store, "record_playbook_trace", None)
    if callable(fn):
        try:
            fn(rec)
        except Exception:
            return
    buf = getattr(store, "pipeline_traces", None)
    if isinstance(buf, list):
        buf.append(rec)


def _json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except TypeError:
        return str(obj)


def _quality_loop(
    *,
    name: str,
    generate: Callable[[], dict[str, Any] | str],
    struct: Callable[[Any], dict[str, Any]],
    judge_type: str,
    judge_ctx: Callable[[Any], dict[str, Any]],
    llm_fn: Callable,
    extract: Callable[[Any], Any] | None = None,
) -> dict[str, Any]:
    last_sha = ""
    last_verdict: dict[str, Any] | None = None
    last_struct: dict[str, Any] = {"ok": False, "code": "no_attempt"}
    last_art: Any = None
    quality = 0
    infra_fails = 0
    while quality < MAX_QUALITY_ROUNDS:
        try:
            art = generate()
        except InfraError as exc:
            return {"ok": False, "code": "infra", "message": str(exc), "layer": name}
        except ParseError as exc:
            infra_fails += 1
            last_struct = {"ok": False, "code": "json", "message": str(exc)}
            if infra_fails >= 3:
                return {"ok": False, "code": "infra", "message": str(exc), "layer": name}
            continue
        last_art = art
        target = extract(art) if extract else art
        last_struct = struct(target)
        if not last_struct.get("ok"):
            quality += 1
            _trace(None, {})  # no-op; caller traces
            continue
        try:
            verdict = judge(judge_type, art if isinstance(art, dict) else {"text": art},
                            PLAYBOOK_VERSION, judge_ctx(art), llm_fn=llm_fn)
        except InfraError as exc:
            return {"ok": False, "code": "infra", "message": str(exc), "layer": name}
        except ParseError as exc:
            infra_fails += 1
            last_struct = {"ok": False, "code": "judge_json", "message": str(exc)}
            if infra_fails >= 3:
                return {"ok": False, "code": "infra", "message": str(exc), "layer": name}
            continue
        body = target if isinstance(target, str) else _json(target)
        sha = str(hash(body))
        if last_verdict and last_sha == sha and last_verdict.get("verdict") != verdict.get("verdict"):
            third = judge(judge_type, art if isinstance(art, dict) else {"text": art},
                          PLAYBOOK_VERSION, judge_ctx(art), llm_fn=llm_fn)
            verdict = majority_if_disagreed(last_verdict, verdict, third)
        last_verdict = verdict
        last_sha = sha
        if verdict.get("verdict") == "pass":
            return {"ok": True, "artifact": art, "review": verdict, "rounds": quality + 1}
        if verdict.get("verdict") == "needs_human":
            return {
                "ok": False,
                "code": "needs_human",
                "status": "needs_human",
                "layer": name,
                "struct": last_struct,
                "review": verdict,
                "artifact": last_art,
                "rounds": quality + 1,
            }
        quality += 1
    return {
        "ok": False,
        "code": "needs_human",
        "status": "needs_human",
        "layer": name,
        "struct": last_struct,
        "review": last_verdict,
        "artifact": last_art,
        "rounds": quality,
    }


def run_stage(
    store: MemoryPlaybookStore,
    seq: int,
    stage: str,
    *,
    extra: str = "",
    llm_fn: Callable | None = None,
    ctx: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    name = normalize_stage(stage)
    gone = reject_gone_stage(name)
    if gone:
        return gone
    if name not in LIVE_STAGES:
        return {"ok": False, "code": "unknown_stage", "message": f"无独立生成链: {stage}"}
    if extra_authors(extra):
        return {
            "ok": False,
            "code": "extra_authors",
            "message": "extra 不得当作者：禁止「必须原样 / 必须有一句 / 必须以时空」",
        }
    if llm_fn is None:
        return {"ok": False, "code": "infra", "message": "缺少 llm_fn"}
    force = parse_force(extra)
    rewrite = parse_rewrite(extra)
    if rewrite and name != "design":
        return {"ok": False, "code": "rewrite_not_allowed", "message": "rewrite=1 只允许 design 层"}
    ctx = dict(ctx or {})
    ctx.setdefault("seq", seq)

    if name == "duty":
        return _run_duty(store, seq, ctx, llm_fn, force=force, persist=persist)
    if name == "design":
        return _run_design(store, seq, ctx, llm_fn, force=force, rewrite=rewrite, persist=persist)
    if name == "deduce":
        return _run_deduce(store, seq, ctx, llm_fn, force=force, persist=persist)
    if name == "draft":
        return _run_draft(store, seq, ctx, llm_fn, force=force, persist=persist)
    return _run_final(store, seq, ctx, llm_fn, force=force, persist=persist)


def _skip_or_force(store, table: str, seq: int, *, force: bool, rewrite: bool) -> dict[str, Any] | None:
    frozen = store.get_frozen(table, seq)
    if frozen and not force and not rewrite:
        return {"ok": True, "skipped": True, "artifact": frozen, "sha": frozen.get("sha")}
    return None


def _run_duty(store, seq, ctx, llm_fn, *, force, persist):
    hit = _skip_or_force(store, "duty_card", seq, force=force, rewrite=False)
    if hit:
        return hit
    result = _quality_loop(
        name="duty",
        generate=lambda: gen_duty(ctx, llm_fn),
        struct=lambda d: check_duty_struct(
            d,
            available_cast=ctx.get("available_cast") or [],
            available_lines=ctx.get("available_lines") or [],
            prev_hook_quote=ctx.get("prev_hook_quote"),
        ),
        judge_type="duty",
        judge_ctx=lambda d: {
            "duty_json": _json(d),
            "volume_outline": ctx.get("volume_outline"),
            "recent_duty_summary": ctx.get("recent_duty_summary"),
            "prev_hook_quote": ctx.get("prev_hook_quote"),
            **_continuity_judge(ctx),
        },
        llm_fn=llm_fn,
    )
    return _finish(store, "duty_card", "duty_card.v1", seq, result, persist=persist, rewrite=force)


def _run_design(store, seq, ctx, llm_fn, *, force, rewrite, persist):
    play_frozen = store.get_frozen("chapter_play", seq)
    if rewrite and play_frozen:
        store.mark_superseded("chapter_play", seq, int(play_frozen.get("version") or 0))
        supersede_downstream(store, seq, str(play_frozen.get("sha") or ""))
        play_frozen = None
    if play_frozen is None:
        duty = store.get_frozen("duty_card", seq) or ctx.get("duty")
        if not duty:
            return {"ok": False, "code": "stage_not_ready", "message": "还没有冻结的责任卡", "need": "duty"}
        ctx = {**ctx, "duty": duty}
        result = _quality_loop(
            name="play",
            generate=lambda: gen_play(ctx, llm_fn),
            struct=lambda p: check_play_struct(p.get("text") if isinstance(p, dict) else str(p)),
            judge_type="play",
            judge_ctx=lambda p: {
                "duty_json": _json(duty),
                "play_text": p.get("text") if isinstance(p, dict) else str(p),
                **_continuity_judge(ctx),
            },
            llm_fn=llm_fn,
        )
        if not result.get("ok"):
            return result
        if persist:
            play_frozen = freeze_artifact(
                store, "chapter_play", seq, result["artifact"],
                schema="chapter_play.v1",
                source_sha=str((duty or {}).get("sha") or ""),
                review=pass_review(),
                rewrite=False,
            )
        else:
            play_frozen = result["artifact"]
    elif force:
        # force on design = re-extract Contract only; Play stays
        pass
    else:
        existing_c = store.get_frozen("chapter_contract", seq)
        if existing_c:
            return {
                "ok": True, "skipped": True,
                "play": play_frozen, "contract": existing_c,
                "sha": play_frozen.get("sha"),
            }

    ctx = {**ctx, "play": play_frozen, "play_text": play_frozen.get("text")}
    c_hit = _skip_or_force(store, "chapter_contract", seq, force=force, rewrite=False)
    if c_hit and not rewrite:
        c_hit["play"] = play_frozen
        c_hit["sha"] = play_frozen.get("sha")
        return c_hit
    result = _quality_loop(
        name="contract",
        generate=lambda: gen_contract(ctx, llm_fn),
        struct=lambda c: check_contract_struct(
            c, play_frozen.get("text") or "",
            available_lines=ctx.get("available_lines") or (ctx.get("duty") or {}).get("available_lines"),
        ),
        judge_type="contract",
        judge_ctx=lambda c: {
            "play_text": play_frozen.get("text"),
            "contract_json": _json(c),
        },
        llm_fn=llm_fn,
    )
    if not result.get("ok"):
        result["play"] = play_frozen
        result["sha"] = play_frozen.get("sha")
        return result
    contract = result["artifact"]
    if persist:
        contract = freeze_artifact(
            store, "chapter_contract", seq, contract,
            schema="chapter_contract.v1",
            source_sha=str(play_frozen.get("sha") or ""),
            review=pass_review(),
            rewrite=force,
        )
    return {
        "ok": True,
        "play": play_frozen,
        "contract": contract,
        "sha": play_frozen.get("sha"),
        "rounds": result.get("rounds"),
    }


def _need_play_contract(store, seq, ctx):
    play = store.get_frozen("chapter_play", seq) or ctx.get("play")
    contract = store.get_frozen("chapter_contract", seq) or ctx.get("contract")
    if not play:
        return None, None, {"ok": False, "code": "stage_not_ready", "message": "还没有冻结的戏", "need": "design"}
    if not contract:
        return None, None, {"ok": False, "code": "stage_not_ready", "message": "还没有冻结的契约", "need": "design"}
    return play, contract, None


def _run_deduce(store, seq, ctx, llm_fn, *, force, persist):
    play, contract, err = _need_play_contract(store, seq, ctx)
    if err:
        return err
    hit = _skip_or_force(store, "chapter_deduce", seq, force=force, rewrite=False)
    if hit:
        hit["sha"] = play.get("sha")
        return hit
    ctx = {**ctx, "play": play, "contract": contract, "play_text": play.get("text"),
           "contract_json": _json(contract),
           "forbidden_reveal": (ctx.get("duty") or store.get_frozen("duty_card", seq) or {}).get("forbidden_reveal")}
    result = _quality_loop(
        name="deduce",
        generate=lambda: gen_deduce(ctx, llm_fn),
        struct=check_deduce_struct,
        judge_type="deduce",
        judge_ctx=lambda d: {
            "play_text": play.get("text"),
            "contract_json": _json(contract),
            "deduction_json": _json(d),
            "characters_epistemic_history": ctx.get("characters_epistemic_history"),
            "forbidden_reveal": ctx.get("forbidden_reveal"),
            **_continuity_judge(ctx),
        },
        llm_fn=llm_fn,
    )
    out = _finish(store, "chapter_deduce", "chapter_deduce.v1", seq, result,
                  persist=persist, rewrite=force, source_sha=play.get("sha") or "")
    out["sha"] = play.get("sha")
    return out


def _run_draft(store, seq, ctx, llm_fn, *, force, persist):
    play, contract, err = _need_play_contract(store, seq, ctx)
    if err:
        return err
    deduce = store.get_frozen("chapter_deduce", seq) or ctx.get("deduce")
    if not deduce:
        return {"ok": False, "code": "stage_not_ready", "message": "还没有冻结的演绎", "need": "deduce"}
    hit = _skip_or_force(store, "chapter_draft", seq, force=force, rewrite=False)
    if hit:
        hit["sha"] = play.get("sha")
        return hit
    duty = ctx.get("duty") or store.get_frozen("duty_card", seq) or {}
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    hook_q = ((fields.get("hook") or {}) if isinstance(fields.get("hook"), dict) else {}).get("quote")
    bite_q = ctx.get("prev_hook_quote") or hook_q or ""
    ctx = {
        **ctx, "play": play, "contract": contract, "deduction": deduce,
        "play_text": play.get("text"), "contract_json": _json(contract),
        "deduction_json": _json(deduce),
        "focalizer": duty.get("focalizer") or ctx.get("focalizer") or "",
        "forbidden_reveal": duty.get("forbidden_reveal") or [],
        "bite_quote": bite_q,
    }
    play_text = play.get("text") or ""
    exempt = tuple(q for q in (bite_q, hook_q) if q)
    result = _quality_loop(
        name="draft",
        generate=lambda: gen_draft(ctx, llm_fn),
        struct=lambda d: check_draft_struct(
            d.get("text") if isinstance(d, dict) else str(d),
            play_text=play_text,
            exempt_quotes=exempt,
            characters=_roster(ctx),
        ),
        judge_type="draft",
        judge_ctx=lambda d: {
            "draft_text": d.get("text") if isinstance(d, dict) else str(d),
            "play_text": play_text,
            "contract_json": _json(contract),
            "deduction_json": _json(deduce),
            "forbidden_reveal": ctx.get("forbidden_reveal"),
            **_continuity_judge(ctx),
        },
        llm_fn=llm_fn,
    )
    out = _finish(store, "chapter_draft", "chapter_draft.v1", seq, result,
                  persist=persist, rewrite=force, source_sha=play.get("sha") or "")
    out["sha"] = play.get("sha")
    if out.get("ok") and persist:
        draft_rec = out.get("artifact") or {}
        draft_text = draft_rec.get("text") if isinstance(draft_rec, dict) else str(draft_rec or "")
        state_out = extract_chapter_state(
            store, seq, draft_text,
            llm_fn=llm_fn, ctx=ctx, persist=True,
            source_sha=str(draft_rec.get("sha") or play.get("sha") or ""),
        )
        out["chapter_state"] = state_out.get("artifact")
        if not state_out.get("ok"):
            out["ok"] = False
            out["code"] = state_out.get("code") or "chapter_state_extract"
            out["message"] = state_out.get("message") or "章末态没抽出"
            out["blockers"] = state_out.get("blockers") or []
            out["state_struct"] = state_out.get("struct")
    return out


def _run_final(store, seq, ctx, llm_fn, *, force, persist):
    play, contract, err = _need_play_contract(store, seq, ctx)
    if err:
        return err
    draft = store.get_frozen("chapter_draft", seq) or ctx.get("draft")
    deduce = store.get_frozen("chapter_deduce", seq) or ctx.get("deduce")
    if not draft:
        return {"ok": False, "code": "stage_not_ready", "message": "还没有冻结的排演", "need": "draft"}
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    duty = ctx.get("duty") or store.get_frozen("duty_card", seq) or {}
    ctx = {
        **ctx, "play": play, "contract": contract, "draft": draft, "deduction": deduce,
        "draft_text": draft.get("text") if isinstance(draft, dict) else str(draft),
        "goal_text": (fields.get("goal") or {}).get("text"),
        "choice_text": (fields.get("choice") or {}).get("text"),
        "decision_text": (fields.get("decision") or {}).get("text"),
        "hook_text": (fields.get("hook") or {}).get("text"),
        "cost_text": (fields.get("cost") or {}).get("text") if isinstance(fields.get("cost"), dict) else "",
        "deduction_json": _json(deduce or {}),
        "forbidden_reveal": duty.get("forbidden_reveal") or [],
        "contract_core_json": _json({k: fields.get(k) for k in ("goal", "choice", "decision", "hook", "cost")}),
        "deduction_epistemic": _json((deduce or {}).get("characters")),
    }
    result = _quality_loop(
        name="final",
        generate=lambda: gen_final(ctx, llm_fn),
        struct=lambda d: check_final_last_mile(
            d.get("text") if isinstance(d, dict) else str(d),
            store=store, seq=seq,
            characters=_roster(ctx),
        ),
        judge_type="final",
        judge_ctx=lambda d: {
            "prose_text": d.get("text") if isinstance(d, dict) else str(d),
            "contract_core_json": ctx.get("contract_core_json"),
            "deduction_epistemic": ctx.get("deduction_epistemic"),
            "forbidden_reveal": ctx.get("forbidden_reveal"),
            "ban_list": "升华/连续同类比喻/元叙述/泄密",
            **_continuity_judge(ctx),
        },
        llm_fn=llm_fn,
    )
    if result.get("ok") and persist:
        persist_fn = getattr(store, "save_chapter_prose", None)
        prose = result["artifact"].get("text") if isinstance(result["artifact"], dict) else result["artifact"]
        if callable(persist_fn):
            persist_fn(seq, prose, play_sha=play.get("sha"), contract_sha=contract.get("sha"))
        draft_text = draft.get("text") if isinstance(draft, dict) else str(draft or "")
        if str(prose or "").strip() and str(prose or "").strip() != str(draft_text or "").strip():
            from scribe3.playbook.envelope import artifact_sha
            state_out = extract_chapter_state(
                store, seq, str(prose or ""),
                llm_fn=llm_fn, ctx=ctx, persist=True,
                source_sha=artifact_sha({"text": prose, "seq": seq}),
            )
            result["chapter_state"] = state_out.get("artifact")
            if not state_out.get("ok"):
                result["ok"] = False
                result["code"] = state_out.get("code") or "chapter_state_extract"
                result["message"] = state_out.get("message") or "定稿后章末态没抽出"
                result["blockers"] = state_out.get("blockers") or []
    if result.get("ok"):
        result["sha"] = play.get("sha")
        result["play"] = play
        result["prose"] = (result.get("artifact") or {}).get("text") if isinstance(result.get("artifact"), dict) else result.get("artifact")
    else:
        result["sha"] = play.get("sha")
    return result


def extract_chapter_state(
    store: MemoryPlaybookStore,
    seq: int,
    source_text: str,
    *,
    llm_fn: Callable,
    ctx: dict[str, Any] | None = None,
    persist: bool = True,
    source_sha: str = "",
) -> dict[str, Any]:
    """Draft/final 冻结后的场记抽取。失败不静默：落 needs_human，返回 blockers。"""
    ctx = dict(ctx or {})
    ctx.setdefault("seq", int(seq))
    ctx["source_text"] = source_text or ""
    if int(seq) > 1 and not ctx.get("prev_state"):
        getter = getattr(store, "get_frozen", None)
        if callable(getter):
            ctx["prev_state"] = getter("chapter_state", int(seq) - 1)
    last_struct: dict[str, Any] = {"ok": False, "code": "no_attempt"}
    last_art: Any = None
    infra_fails = 0
    quality = 0
    while quality < MAX_QUALITY_ROUNDS:
        try:
            art = gen_state(ctx, llm_fn)
        except InfraError as exc:
            return {"ok": False, "code": "infra", "message": str(exc), "layer": "chapter_state"}
        except ParseError as exc:
            infra_fails += 1
            last_struct = {"ok": False, "code": "json", "message": str(exc)}
            if infra_fails >= 3:
                return {"ok": False, "code": "infra", "message": str(exc), "layer": "chapter_state"}
            continue
        last_art = art
        last_struct = check_chapter_state_struct(art, source_text)
        if last_struct.get("ok"):
            if persist:
                try:
                    frozen = freeze_artifact(
                        store, "chapter_state", int(seq), art,
                        schema="chapter_state.v1",
                        source_sha=source_sha,
                        review=pass_review(),
                        rewrite=True,
                    )
                except FrozenAssetError as exc:
                    return {"ok": False, "code": "frozen", "message": str(exc), "layer": "chapter_state"}
                return {"ok": True, "artifact": frozen, "rounds": quality + 1}
            return {"ok": True, "artifact": art, "rounds": quality + 1}
        quality += 1
    blockers = [{
        "detector": "chapter_state",
        "kind": "sealed",
        "code": last_struct.get("code") or "chapter_state_extract",
        "note": last_struct.get("message") or "章末态没抽出",
    }]
    if persist and last_art:
        rec = dict(last_art) if isinstance(last_art, dict) else {"text": last_art}
        rec["seq"] = int(seq)
        rec["status"] = "needs_human"
        rec["version"] = store.next_version("chapter_state", int(seq))
        rec["schema"] = "chapter_state.v1"
        rec["playbook_version"] = PLAYBOOK_VERSION
        store.insert("chapter_state", rec)
    return {
        "ok": False,
        "code": "chapter_state_extract",
        "message": last_struct.get("message") or "章末态没抽出",
        "layer": "chapter_state",
        "struct": last_struct,
        "blockers": blockers,
        "artifact": last_art,
        "rounds": quality,
    }


def _finish(store, table, schema, seq, result, *, persist, rewrite, source_sha=""):
    if not result.get("ok"):
        art = result.get("artifact")
        if persist and art and result.get("code") == "needs_human":
            rec = dict(art) if isinstance(art, dict) else {"text": art}
            rec["seq"] = seq
            rec["status"] = "needs_human"
            rec["version"] = store.next_version(table, seq)
            store.insert(table, rec)
        return result
    art = result["artifact"]
    if persist:
        try:
            frozen = freeze_artifact(
                store, table, seq, art if isinstance(art, dict) else {"text": art, "seq": seq},
                schema=schema, source_sha=source_sha, review=pass_review(), rewrite=rewrite,
            )
        except FrozenAssetError as exc:
            return {"ok": False, "code": "frozen", "message": str(exc)}
        result["artifact"] = frozen
    return result


def review_and_freeze_play(
    store: MemoryPlaybookStore,
    seq: int,
    text: str,
    *,
    llm_fn: Callable,
    ctx: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Judge a human-edited play draft and freeze it as a new version.

    Old frozen play is superseded; downstream citing the old sha is superseded.
    """
    ctx = dict(ctx or {})
    ctx.setdefault("seq", int(seq))
    duty = store.get_frozen("duty_card", seq) or ctx.get("duty") or {}
    struct = check_play_struct(text)
    if not struct.get("ok"):
        return {**struct, "layer": "play"}
    art = {"seq": int(seq), "text": text, "duty_sha": duty.get("sha") or ""}
    try:
        verdict = judge(
            "play", art, PLAYBOOK_VERSION,
            {"duty_json": _json(duty), "play_text": text, "prev_state": ctx.get("prev_state")},
            llm_fn=llm_fn,
        )
    except (InfraError, ParseError) as exc:
        return {"ok": False, "code": "infra", "message": str(exc), "layer": "play"}
    if verdict.get("verdict") != "pass":
        if persist:
            rec = {
                "seq": int(seq), "text": text, "status": "draft",
                "schema": "chapter_play.v1", "playbook_version": PLAYBOOK_VERSION,
                "duty_sha": duty.get("sha") or "",
                "version": store.next_version("chapter_play", int(seq)),
            }
            store.insert("chapter_play", rec)
        return {
            "ok": False, "code": "needs_human", "status": "draft",
            "review": verdict, "layer": "play",
        }
    if not persist:
        return {"ok": True, "artifact": art, "review": verdict}
    frozen = freeze_artifact(
        store, "chapter_play", int(seq), art,
        schema="chapter_play.v1",
        source_sha=str(duty.get("sha") or ""),
        review=pass_review(),
        rewrite=True,
    )
    return {"ok": True, "artifact": frozen, "play": frozen, "sha": frozen.get("sha"), "review": verdict}


# Re-export for tests that drive freeze/overwrite through this module.
__all__ = [
    "run_stage", "overwrite_play", "freeze_artifact", "MemoryPlaybookStore",
    "normalize_stage", "reject_gone_stage", "GONE_STAGES", "LIVE_STAGES",
    "MIGRATE_HINT", "StageGone", "MAX_QUALITY_ROUNDS", "review_and_freeze_play",
    "extract_chapter_state",
]

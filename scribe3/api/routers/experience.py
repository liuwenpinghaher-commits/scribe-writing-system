"""经验压力层 API · 问诊/场景动能/种子/续写/读感。"""
from __future__ import annotations

import types
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["experience"])


def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith("__"):
            continue
        if k not in g:
            g[k] = v


try:
    _import_core_defaults()
except Exception:
    pass


class ModeReq(BaseModel):
    mode: str = "full"


class LetterItemUpdate(BaseModel):
    status: str
    author_note: str = ""


class SceneGridReq(BaseModel):
    goal: str = ""
    conflict: str = ""
    disaster: str = ""
    reaction: str = ""
    dilemma: str = ""
    decision: str = ""
    source: str = "author"


class StrictSceneReq(BaseModel):
    enabled: bool = False


class ChoiceAuditReq(BaseModel):
    quote: str
    character_id: str = ""
    anchors: dict = Field(default_factory=dict)
    recent_synopsis: str = ""


class SeedSuggestReq(BaseModel):
    seq: int | None = None
    prose: str = ""


class SeedPromoteReq(BaseModel):
    seed_id: str


class RequireRereadReq(BaseModel):
    enabled: bool = False


class AckRereadReq(BaseModel):
    seq: int


class FeedbackImportReq(BaseModel):
    text: str


class CutSuggestReq(BaseModel):
    prose: str = ""


def get_revision_mode(work: str = "main"):
    from scribe3.experience import exp_state
    from scribe3.experience.modes import REVISION_MODES
    return {
        "work": work,
        "mode": exp_state.get_revision_mode(work),
        "allowed": list(REVISION_MODES),
        "note": "只改问诊优先级,不关闭 finalize_gate",
    }


def set_revision_mode(req: ModeReq, work: str = "main"):
    from scribe3.experience import exp_state
    m = exp_state.set_revision_mode(work, req.mode)
    return {"work": work, "mode": m}


def get_revision_letter(work: str = "main", scope: str = "book"):
    """全书 re-vision 问诊信。"""
    from scribe3.experience import exp_state
    from scribe3.experience.letter import build_revision_letter, letter_has_total_score
    from scribe3.experience.scene_grid import diagnose_scene_grid

    st = _store_for(work)
    mode = exp_state.get_revision_mode(work)
    # 收集场景诊断
    scene_diags = []
    try:
        chapters = []
        if hasattr(st, "chapters_lite"):
            chapters = st.chapters_lite() or []
        for c in chapters:
            seq = c.get("seq")
            if seq is None:
                continue
            g = exp_state.get_scene_grid(work, int(seq))
            if g:
                for d in diagnose_scene_grid(g, seq=int(seq)):
                    if d.get("code") != "empty_grid":
                        scene_diags.append(d)
    except Exception:
        pass

    letter = build_revision_letter(
        st,
        work=work,
        mode=mode,
        status_overlay=exp_state.get_letter_overlay(work),
        external_feedback=exp_state.get_feedback(work),
        seed_suggestions=exp_state.get_seeds(work),
        scene_diagnostics=scene_diags,
    )
    letter["scope"] = scope
    if letter_has_total_score(letter):
        raise HTTPException(500, "letter 含总分字段,违反宪法")
    # 双检:items 无 score
    for it in letter.get("items") or []:
        if "score" in it and it["score"] is not None:
            raise HTTPException(500, "letter item 含 score")
    return letter


def patch_revision_letter_item(item_id: str, req: LetterItemUpdate, work: str = "main"):
    from scribe3.experience import exp_state
    from scribe3.experience.letter import ITEM_STATUSES, build_revision_letter

    if req.status not in ITEM_STATUSES:
        raise HTTPException(422, f"status 须为 {ITEM_STATUSES}")
    # 确保 item 存在于当前 letter(或允许预登记 overlay)
    letter = build_revision_letter(
        _store_for(work),
        work=work,
        mode=exp_state.get_revision_mode(work),
        status_overlay=exp_state.get_letter_overlay(work),
        external_feedback=exp_state.get_feedback(work),
        seed_suggestions=exp_state.get_seeds(work),
    )
    ids = {i["id"] for i in letter.get("items") or []}
    if item_id not in ids:
        # 仍写入 overlay,便于审计外部项
        pass
    saved = exp_state.set_letter_item(
        work, item_id, status=req.status, author_note=req.author_note)
    # 返回刷新后的 letter
    refreshed = get_revision_letter(work=work)
    return {"ok": True, "item": saved, "letter": refreshed}


def get_scene_grid_ep(seq: int, work: str = "main"):
    from scribe3.experience import exp_state
    from scribe3.experience.scene_grid import (
        diagnose_scene_grid, empty_scene_grid, normalize_scene_grid,
    )
    g = exp_state.get_scene_grid(work, seq) or empty_scene_grid()
    g = normalize_scene_grid(g)
    return {
        "seq": seq,
        "grid": g,
        "issues": diagnose_scene_grid(g, seq=seq),
        "strict": exp_state.get_strict_scene(work),
    }


def put_scene_grid_ep(seq: int, req: SceneGridReq, work: str = "main"):
    from scribe3.experience import exp_state
    from scribe3.experience.scene_grid import diagnose_scene_grid, normalize_scene_grid
    g = normalize_scene_grid(req.model_dump())
    exp_state.set_scene_grid(work, seq, g)
    return {
        "seq": seq,
        "grid": g,
        "issues": diagnose_scene_grid(g, seq=seq),
    }


def set_strict_scene_ep(req: StrictSceneReq, work: str = "main"):
    from scribe3.experience import exp_state
    return {"work": work, "strict_scene_grid": exp_state.set_strict_scene(work, req.enabled)}


def choice_audit_ep(req: ChoiceAuditReq, work: str = "main"):
    from scribe3.experience.choice_seed import build_choice_audit
    anchors = dict(req.anchors or {})
    # 尝试从 store 补角色
    if req.character_id and not anchors:
        try:
            st = _store_for(work)
            if hasattr(st, "get_entity"):
                ent = st.get_entity(req.character_id) or {}
                anchors = dict(ent.get("traits") or {})
                anchors["name"] = ent.get("name") or req.character_id
                anchors["id"] = req.character_id
        except Exception:
            pass
    audit = build_choice_audit(
        quote=req.quote,
        character_id=req.character_id,
        anchors=anchors,
        recent_synopsis=req.recent_synopsis,
    )
    if audit.get("likeness_score") is not None:
        raise HTTPException(500, "choice_audit 不得返回 likeness 分")
    return audit


def seed_suggest_ep(req: SeedSuggestReq, work: str = "main"):
    from scribe3.experience import exp_state
    from scribe3.experience.choice_seed import suggest_seeds
    st = _store_for(work)
    prose = req.prose
    seq = req.seq
    if not prose and seq is not None:
        ch = st.get_chapter(int(seq)) or {}
        prose = ch.get("prose") or ""
    existing = []
    try:
        if hasattr(st, "open_promises"):
            existing = [p.get("text") or "" for p in (st.open_promises() or [])]
    except Exception:
        pass
    seeds = suggest_seeds(prose, existing_promise_texts=existing, seq=seq)
    exp_state.set_seeds(work, seeds)
    return {"work": work, "seeds": seeds, "count": len(seeds)}


def seed_promote_ep(req: SeedPromoteReq, work: str = "main"):
    """返回须审批的 promise payload;不自动 plant。"""
    from scribe3.experience import exp_state
    from scribe3.experience.choice_seed import promote_seed_payload
    seeds = exp_state.get_seeds(work)
    seed = next((s for s in seeds if s.get("id") == req.seed_id), None)
    if not seed:
        raise HTTPException(404, "seed not found;先 POST /seeds/suggest")
    payload = promote_seed_payload(seed)
    exp_state.mark_seed_promoted(work, req.seed_id)
    return {
        "ok": True,
        "planted": False,
        "requires_approval": True,
        "promise_draft": payload,
        "note": "请经伏笔/MCP 待批通道写入;本端点不落正典",
    }


def continue_snapshot_ep(seq: int, work: str = "main"):
    from scribe3.experience import exp_state
    from scribe3.experience.continue_rite import build_continue_snapshot, reread_allowed
    st = _store_for(work)
    snap = build_continue_snapshot(st, seq, work=work)
    req = exp_state.get_require_reread(work)
    acked = exp_state.has_reread_ack(work, seq)
    gate = reread_allowed(require_reread=req, acked=acked, is_generate=True)
    return {
        "snapshot": snap,
        "require_reread": req,
        "acked": acked,
        "generate_gate": gate,
    }


def set_require_reread_ep(req: RequireRereadReq, work: str = "main"):
    from scribe3.experience import exp_state
    return {"work": work, "require_reread": exp_state.set_require_reread(work, req.enabled)}


def ack_reread_ep(req: AckRereadReq, work: str = "main"):
    from scribe3.experience import exp_state
    exp_state.ack_reread(work, req.seq)
    return {"ok": True, "seq": req.seq, "acked": True}


def feedback_import_ep(req: FeedbackImportReq, work: str = "main"):
    from scribe3.experience import exp_state
    from scribe3.experience.feedback_cut import parse_feedback_markdown
    items = parse_feedback_markdown(req.text)
    if not items:
        raise HTTPException(422, "未解析到反馈项")
    all_items = exp_state.append_feedback(work, items)
    return {"imported": len(items), "total": len(all_items), "items": items}


def cut_suggest_ep(req: CutSuggestReq, work: str = "main"):
    from scribe3.experience.feedback_cut import suggest_cut_candidates
    prose = req.prose
    if not prose:
        raise HTTPException(422, "prose required")
    cands = suggest_cut_candidates(prose)
    assert all(c.get("auto_delete") is False for c in cands)
    return {"candidates": cands, "auto_delete": False,
            "note": "仅建议,不自动删正文"}


def experience_flags(work: str = "main"):
    """操作员可见汇总。"""
    from scribe3.experience import exp_state
    return {
        "work": work,
        "revision_mode": exp_state.get_revision_mode(work),
        "strict_scene_grid": exp_state.get_strict_scene(work),
        "require_reread": exp_state.get_require_reread(work),
        "seed_count": len(exp_state.get_seeds(work)),
        "feedback_count": len(exp_state.get_feedback(work)),
        "letter_not_blocking": True,
        "no_total_score": True,
    }


def _bind_and_register() -> None:
    from scribe3.api import app_impl as core
    g = globals()

    def _bind(name: str, path: str, methods: list[str]):
        _fn = g[name]
        _re = types.FunctionType(
            _fn.__code__, core.__dict__, name, _fn.__defaults__, _fn.__closure__)
        if _fn.__annotations__:
            _re.__annotations__ = dict(_fn.__annotations__)
        setattr(core, name, _re)
        g[name] = _re
        router.add_api_route(path, _re, methods=methods, name=name)

    _bind("get_revision_mode", "/revision/mode", ["GET"])
    _bind("set_revision_mode", "/revision/mode", ["POST"])
    _bind("get_revision_letter", "/revision/letter", ["GET"])
    _bind("patch_revision_letter_item", "/revision/letter/items/{item_id}", ["POST"])
    _bind("get_scene_grid_ep", "/chapters/{seq}/scene-grid", ["GET"])
    _bind("put_scene_grid_ep", "/chapters/{seq}/scene-grid", ["PUT"])
    _bind("set_strict_scene_ep", "/revision/strict-scene", ["POST"])
    _bind("choice_audit_ep", "/revision/choice-audit", ["POST"])
    _bind("seed_suggest_ep", "/seeds/suggest", ["POST"])
    _bind("seed_promote_ep", "/seeds/promote", ["POST"])
    _bind("continue_snapshot_ep", "/continue/snapshot", ["GET"])
    _bind("set_require_reread_ep", "/continue/require-reread", ["POST"])
    _bind("ack_reread_ep", "/continue/ack-reread", ["POST"])
    _bind("feedback_import_ep", "/feedback/import", ["POST"])
    _bind("cut_suggest_ep", "/revision/cut-suggestions", ["POST"])
    _bind("experience_flags", "/revision/flags", ["GET"])


_bind_and_register()

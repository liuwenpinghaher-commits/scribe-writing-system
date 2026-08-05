"""写作导演 API · WorkflowSnapshot + 编排 WorkPackage。"""
from __future__ import annotations

import types
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["director"])


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


class OrchResolveReq(BaseModel):
    message: str = ""
    chapter: int | None = None
    phase: str | None = None
    action: str = "auto"  # auto|create|continue|switch
    journey_next_domain: str | None = None
    focus_hint: dict[str, Any] | None = None
    activate: bool = True  # 写入 active package


class OrchTurnReq(BaseModel):
    tools_called: list[str] = Field(default_factory=list)
    approved_writes: list[str] = Field(default_factory=list)
    package: dict[str, Any] | None = None  # 缺省用 active


class OrchProposalReq(BaseModel):
    ops: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    package: dict[str, Any] | None = None


class OrchProposalApplyReq(BaseModel):
    proposal: dict[str, Any]
    decision: str = "approve"  # approve|reject
    selected: list[int] | None = None
    # 测试/紧急：是否真执行 plant/patch（生产前端经 Hermes 审批；此端点供编排契约与测试）
    execute: bool = False


def workflow_snapshot_ep(work: str = "main", seq: int | None = None):
    """书/章进度单源：状态页与进度胶囊同源。"""
    from scribe3.director import build_workflow_snapshot
    st = _store_for(work)
    if st is None:
        raise HTTPException(503, "store 未就绪")
    snap = build_workflow_snapshot(st, work=work, seq=seq)
    # 契约守卫：禁止文学总分
    if "total_score" in snap or "composite_score" in snap:
        raise HTTPException(500, "snapshot 不得含 total_score")
    return snap


def orch_catalog_ep(work: str = "main"):
    from scribe3.orchestration.catalog import CATALOG, list_domains
    return {
        "work": work,
        "domains": list_domains(),
        "count": len(CATALOG),
        "entries": [
            {
                "domain": c["domain"],
                "label": c.get("label"),
                "write_tools": list(c.get("write_tools") or ()),
                "required_outcome": c.get("required_outcome"),
                "channel": c.get("channel"),
            }
            for c in CATALOG
        ],
    }


def orch_resolve_ep(req: OrchResolveReq, work: str = "main"):
    """统一编排入口：解析 WorkPackage + ui_directive 事件列表。"""
    from scribe3.orchestration import package_state
    from scribe3.orchestration.resolve import apply_ui_directive_events, resolve_work_package

    prior = package_state.get_active(work)
    pkg = resolve_work_package(
        req.message,
        work=work,
        chapter=req.chapter,
        phase=req.phase,
        prior_package=prior,
        journey_next_domain=req.journey_next_domain,
        focus_hint=req.focus_hint,
        action=req.action or "auto",
    )
    if req.activate:
        package_state.set_active(work, pkg)
    events = apply_ui_directive_events(pkg.get("ui_directive"))
    out = {
        "work": work,
        "package": pkg,
        "ui_events": events,
        "use_world_write_run": bool(pkg.get("use_world_write_run")),
        "channel": pkg.get("channel"),
    }
    if "total_score" in out or "composite_score" in str(out):
        raise HTTPException(500, "orchestration payload 不得含文学分")
    return out


def orch_active_ep(work: str = "main"):
    from scribe3.orchestration import package_state
    return {"work": work, "package": package_state.get_active(work)}


def orch_evaluate_turn_ep(req: OrchTurnReq, work: str = "main"):
    from scribe3.orchestration import package_state
    from scribe3.orchestration.resolve import evaluate_turn

    pkg = req.package or package_state.get_active(work)
    if not pkg:
        raise HTTPException(404, "no active work package")
    result = evaluate_turn(
        pkg,
        tools_called=req.tools_called,
        approved_writes=req.approved_writes,
    )
    # 更新 package status
    pkg = dict(pkg)
    pkg["status"] = result["status"]
    if result.get("status") == "applied":
        package_state.set_active(work, None)  # 完成清空
    else:
        package_state.set_active(work, pkg)
    return {"work": work, "evaluation": result, "package": package_state.get_active(work) or pkg}


def orch_build_proposal_ep(req: OrchProposalReq, work: str = "main"):
    from scribe3.orchestration import package_state
    from scribe3.orchestration.proposal import build_write_proposal

    pkg = req.package or package_state.get_active(work)
    if not pkg:
        raise HTTPException(404, "no active work package")
    prop = build_write_proposal(pkg, req.ops, summary=req.summary)
    return {"work": work, "proposal": prop}


def orch_apply_proposal_ep(req: OrchProposalApplyReq, work: str = "main"):
    """契约层批准/拒绝。execute=True 时用 store 执行白名单写（测试/紧急）。

    生产主路径仍是 Hermes 审批卡；本端点保证「未 approve 不写」可测。
    """
    from scribe3.orchestration.proposal import apply_proposal_ops
    from scribe3.orchestration.resolve import apply_ui_directive_events

    executors: dict = {}
    if req.execute and req.decision == "approve":
        st = _store_for(work)
        if st is None:
            raise HTTPException(503, "store 未就绪")

        def _plant(**kw):
            text = kw.get("text") or kw.get("promise_text") or ""
            setup = int(kw.get("setup_chapter") or kw.get("chapter") or 1)
            if not hasattr(st, "plant_promise"):
                return {"status": "error", "error": "no plant_promise"}
            row = st.plant_promise(text, setup, kind=kw.get("kind") or "promise",
                                   tier=kw.get("tier") or "chapter")
            return {"status": "written", "promise": row}

        def _patch_char(**kw):
            cid = kw.get("character_id") or kw.get("oid") or ""
            if hasattr(st, "patch_character"):
                ok = st.patch_character(cid, **{k: v for k, v in kw.items()
                                                if k not in ("character_id", "oid")})
                return {"status": "written" if ok is not False else "error", "ok": ok}
            # MiniStore / 测试：挂内存角色
            if not hasattr(st, "_orch_chars"):
                st._orch_chars = {}
            st._orch_chars[cid] = dict(kw)
            return {"status": "written", "character_id": cid}

        def _patch_plan(**kw):
            seq = int(kw.get("seq") or kw.get("chapter") or 1)
            if hasattr(st, "patch_chapter"):
                st.patch_chapter(seq, synopsis=kw.get("synopsis"), beats=kw.get("beats"))
                return {"status": "written", "seq": seq}
            if hasattr(st, "chapters"):
                for c in st.chapters:
                    if int(c.get("seq") or -1) == seq:
                        if kw.get("synopsis") is not None:
                            c["synopsis"] = kw["synopsis"]
                        if kw.get("beats") is not None:
                            c["beats"] = kw["beats"]
                        return {"status": "written", "seq": seq}
            return {"status": "error", "error": "chapter not found"}

        executors = {
            "s3_plant_promise": _plant,
            "s3_patch_character": _patch_char,
            "s3_add_character": _patch_char,
            "s3_patch_chapter_plan": _patch_plan,
            "s3_patch_chapter_meta": _patch_plan,
        }

    if req.decision != "approve":
        result = apply_proposal_ops(req.proposal, decision="reject", executors={})
        return {"work": work, "proposal": result, "ui_events": []}

    if not req.execute:
        # 仅标记：真实写由 Hermes 审批完成；此处不调用 executor
        result = apply_proposal_ops(req.proposal, decision="reject", executors={})
        # 重新标记为 awaiting_external_approval 语义
        result = dict(req.proposal)
        result["status"] = "awaiting_hermes_approval"
        result["note"] = "生产请经 Hermes 审批卡；execute=false 不落库"
        return {"work": work, "proposal": result, "ui_events": []}

    result = apply_proposal_ops(
        req.proposal, decision="approve", executors=executors, selected=req.selected,
    )
    ui_events = []
    if result.get("status") in ("applied", "partial"):
        ui_events = apply_ui_directive_events(
            (req.proposal or {}).get("ui_after")
            or (result.get("ui_after")),
        )
    return {"work": work, "proposal": result, "ui_events": ui_events}


def _bind_and_register():
    from scribe3.api import app_impl as core
    g = globals()

    for _model_name in (
        "OrchResolveReq", "OrchTurnReq", "OrchProposalReq", "OrchProposalApplyReq",
        "BaseModel", "Field",
    ):
        if _model_name in g:
            setattr(core, _model_name, g[_model_name])

    def _bind(name: str, path: str, methods: list[str]):
        _fn = g[name]
        _re = types.FunctionType(
            _fn.__code__, core.__dict__, name, _fn.__defaults__, _fn.__closure__)
        if _fn.__annotations__:
            _re.__annotations__ = dict(_fn.__annotations__)
        setattr(core, name, _re)
        g[name] = _re
        router.add_api_route(path, _re, methods=methods, name=name)

    _bind("workflow_snapshot_ep", "/workflow/snapshot", ["GET"])
    _bind("orch_catalog_ep", "/orchestration/catalog", ["GET"])
    _bind("orch_resolve_ep", "/orchestration/resolve", ["POST"])
    _bind("orch_active_ep", "/orchestration/active", ["GET"])
    _bind("orch_evaluate_turn_ep", "/orchestration/evaluate-turn", ["POST"])
    _bind("orch_build_proposal_ep", "/orchestration/proposal", ["POST"])
    _bind("orch_apply_proposal_ep", "/orchestration/proposal/apply", ["POST"])


_bind_and_register()

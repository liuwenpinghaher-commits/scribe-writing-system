"""正典变更闭环 HTTP：全类型抽取、候选列表、安全 apply（Surreal）。"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scribe3.canon_loop import (
    CanonClaim,
    ChangePack,
    InMemoryCanonStore,
    apply_change_pack,
    item_requires_human_approval,
)
from scribe3.api.services.canon_hooks import (
    body_confirmed_report,
    discussion_change_pack,
    run_chapter_extract,
)

router = APIRouter(tags=["canon-loop"])

# 测试用内存账本（无 work store 时）
_DEMO_STORES: dict[str, InMemoryCanonStore] = {}


def _mem(work: str) -> InMemoryCanonStore:
    if work not in _DEMO_STORES:
        _DEMO_STORES[work] = InMemoryCanonStore()
    return _DEMO_STORES[work]


def _store(work: str):
    try:
        from scribe3.api.app_impl import _store_for
        st = _store_for(work)
        if st is not None:
            return st
    except Exception:
        pass
    return _mem(work)


def _work_from(body_work: str | None, query_work: Any = None) -> str:
    """解析 work：body 非默认优先；否则用 ?work=（前端 j/post 只挂 query）。

    单测可直接调 endpoint 函数；query_work 须为 str/None（勿传 FastAPI Query 哨兵）。
    """
    if not isinstance(query_work, str):
        query_work = None
    if not isinstance(body_work, str):
        body_work = None
    bw = (body_work or "").strip()
    qw = (query_work or "").strip()
    if bw and bw != "main":
        return bw
    if qw:
        return qw
    return bw or "main"


class ClaimIn(BaseModel):
    layer: str = "L1"
    op: str = "patch"
    module: str = "character"
    target: str
    after: Any = None
    evidence: str = ""
    risk: str = "med"
    field: Optional[str] = None
    requires_approval: Optional[bool] = None


class ChangePackFromTextReq(BaseModel):
    text: str = ""
    work: str = "main"
    source: str = "discussion"
    claims: Optional[list[ClaimIn]] = None
    persist: bool = True
    use_llm: bool = False
    # 测试/高级：覆盖 store 快照与章索引
    chapter_index: Optional[dict[str, list[int]]] = None
    canon_snapshot: Optional[dict[str, Any]] = None


class PostFinalizeReq(BaseModel):
    seq: int = Field(ge=1)
    prose: str = ""
    work: str = "main"
    claims: Optional[list[ClaimIn]] = None
    persist: bool = True
    use_llm: bool = False
    chapter_index: Optional[dict[str, list[int]]] = None
    canon_snapshot: Optional[dict[str, Any]] = None


class ApplyPackReq(BaseModel):
    pack: dict[str, Any]
    approved_item_ids: list[str] = Field(default_factory=list)
    apply_objective_l2: bool = True
    work: str = "main"
    use_surreal: bool = True
    seed_snapshot: Optional[dict[str, Any]] = None


class ExtractReq(BaseModel):
    seq: int = Field(ge=1)
    work: str = "main"
    use_llm: bool = True


class DecideReq(BaseModel):
    decision: str = "approve"  # approve|reject
    work: str = "main"
    # 编辑后批准：覆盖 target/field/after/module/op
    edit: Optional[dict[str, Any]] = None
    merge_into: Optional[str] = None  # 合并到已有 target
    reason: str = ""


class BatchDecideReq(BaseModel):
    work: str = "main"
    ids: list[str] = Field(default_factory=list)
    decision: str = "reject"  # approve|reject
    reason: str = ""
    # 便捷：忽略当前噪声桶
    noise_only: bool = False


def _claims(req_claims: list[ClaimIn] | None) -> list[CanonClaim] | None:
    if req_claims is None:
        return None
    return [
        CanonClaim(
            layer=c.layer, op=c.op, module=c.module, target=c.target,
            after=c.after, evidence=c.evidence, risk=c.risk, field=c.field,
            requires_approval=c.requires_approval,
        )
        for c in req_claims
    ]


def _complete(use_llm: bool):
    if not use_llm:
        return None
    try:
        from scribe3.llm import hermes_complete
        return lambda p: hermes_complete(p, timeout=90.0, max_tokens=2000, retries_override=0)
    except Exception:
        return None


@router.post("/canon/change-pack")
def change_pack_from_text(req: ChangePackFromTextReq, work: str | None = None):
    w = _work_from(req.work, work)
    st = _store(w)
    return discussion_change_pack(
        work=w,
        text=req.text,
        source=req.source,
        claims=_claims(req.claims),
        st=st,
        canon_snapshot=req.canon_snapshot,
        chapter_index=req.chapter_index,
        complete_fn=_complete(req.use_llm),
        persist=req.persist and hasattr(st, "add_canon_candidate"),
    )


@router.post("/canon/post-finalize-report")
def post_finalize_report_ep(req: PostFinalizeReq, work: str | None = None):
    w = _work_from(req.work, work)
    st = _store(w)
    return body_confirmed_report(
        work=w,
        seq=req.seq,
        prose=req.prose,
        claims=_claims(req.claims),
        st=st,
        canon_snapshot=req.canon_snapshot,
        chapter_index=req.chapter_index,
        complete_fn=_complete(req.use_llm),
        persist=req.persist and hasattr(st, "add_canon_candidate"),
    )


@router.post("/canon/extract")
def canon_extract_ep(req: ExtractReq, work: str | None = None):
    w = _work_from(req.work, work)
    st = _store(w)
    if isinstance(st, InMemoryCanonStore):
        raise HTTPException(503, "需要 Surreal work store")
    return run_chapter_extract(
        st, work=w, seq=req.seq, complete_fn=_complete(req.use_llm),
    )


@router.get("/canon/candidates")
def list_candidates(
    work: str = "main",
    status: str = "pending",
    module: str | None = None,
    seq: int | None = None,
    source: str | None = None,
    extractor: str | None = None,
    risk: str | None = None,
    min_confidence: float | None = None,
    noise: str | None = None,  # only|exclude|all
    priority: str | None = None,  # suggested|all
    limit: int = 200,
    offset: int = 0,
):
    from scribe3.canon_inbox import annotate_flags, facets, filter_items

    st = _store(work)
    if not hasattr(st, "list_canon_candidates"):
        return {"work": work, "items": [], "debt": {"total": 0, "high": 0}, "facets": {}}
    raw = st.list_canon_candidates(status=status, module=module, seq=seq)
    fac = facets(raw)
    items = filter_items(
        raw,
        source=source,
        extractor=extractor,
        risk=risk,
        min_confidence=min_confidence,
        noise=noise if noise in ("only", "exclude", "all") else None,
        priority=priority if priority in ("suggested", "all") else None,
    )
    # annotate all returned
    items = [annotate_flags(i) for i in items]
    total_filtered = len(items)
    lim = max(1, min(int(limit or 200), 500))
    off = max(0, int(offset or 0))
    page = items[off: off + lim]
    debt = st.count_canon_debt() if hasattr(st, "count_canon_debt") else {}
    # enrich debt
    debt = dict(debt or {})
    debt["noise_count"] = fac.get("noise_count", 0)
    debt["suggested_priority_count"] = fac.get("suggested_priority_count", 0)
    return {
        "work": work,
        "items": page,
        "total": total_filtered,
        "offset": off,
        "limit": lim,
        "debt": debt,
        "facets": fac,
    }


@router.get("/canon/debt")
def canon_debt(work: str = "main"):
    from scribe3.canon_inbox import facets

    st = _store(work)
    if not hasattr(st, "count_canon_debt"):
        return {"work": work, "total": 0, "high": 0}
    d = dict(st.count_canon_debt() or {})
    d["work"] = work
    if hasattr(st, "list_canon_candidates"):
        fac = facets(st.list_canon_candidates(status="pending"))
        d["noise_count"] = fac.get("noise_count", 0)
        d["suggested_priority_count"] = fac.get("suggested_priority_count", 0)
        d["by_source"] = fac.get("by_source", {})
    return d


def _apply_one(st, w: str, uid: str, row: dict, *, edit: dict | None = None, merge_into: str | None = None):
    item = {
        "id": uid,
        "layer": row.get("layer") or "L1",
        "op": row.get("op") or "patch",
        "module": row.get("module"),
        "target": row.get("target"),
        "field": row.get("field"),
        "after": row.get("after"),
        "before": row.get("before"),
        "evidence": row.get("evidence") or "",
        "risk": row.get("risk") or "med",
        "requires_approval": True,
        "approved": False,
        "applied": False,
    }
    if edit:
        for k in ("module", "op", "target", "field", "after", "layer", "risk"):
            if k in edit and edit[k] is not None:
                item[k] = edit[k]
    if merge_into:
        item["op"] = "patch"
        item["target"] = merge_into
    pack = {
        "id": f"cp_one_{uid}",
        "work": w,
        "source": "decide",
        "items": [item],
        "impact": row.get("impact") or {},
        "status": "proposed",
    }
    result = apply_change_pack(
        pack, approved_item_ids=[uid], apply_objective_l2=True, store=st,
    )
    ok = bool(result.get("applied"))
    if ok:
        st.set_canon_candidate_status(uid, "approved")
        if hasattr(st, "log_canon_apply"):
            st.log_canon_apply(uid, item["module"], item["target"], item.get("field"), "ok")
    else:
        if hasattr(st, "log_canon_apply"):
            st.log_canon_apply(
                uid, item["module"], item["target"], item.get("field"), "rejected",
                str(result.get("rejected")),
            )
    return ok, result, item


# 静态路径须在 {uid} 之前注册
@router.post("/canon/candidates/batch-decide")
def batch_decide(req: BatchDecideReq, work: str | None = None):
    from scribe3.canon_inbox import annotate_flags, is_noise_heuristic

    w = _work_from(req.work, work)
    st = _store(w)
    if not hasattr(st, "list_canon_candidates"):
        raise HTTPException(503, "no candidate store")
    ids = list(req.ids or [])
    if req.noise_only:
        pending = st.list_canon_candidates(status="pending")
        ids = [i["id"] for i in pending if i.get("id") and is_noise_heuristic(annotate_flags(i))]
    if not ids:
        return {"ok": True, "processed": 0, "results": []}
    if len(ids) > 300:
        raise HTTPException(422, "batch too large (max 300)")
    decision = (req.decision or "reject").strip()
    if decision not in ("approve", "reject"):
        raise HTTPException(422, "decision must be approve|reject")
    results = []
    for uid in ids:
        row = st.get_canon_candidate(uid) if hasattr(st, "get_canon_candidate") else None
        if not row:
            results.append({"id": uid, "ok": False, "error": "not_found"})
            continue
        mod = (row.get("module") or "").lower()
        if decision == "approve" and mod in ("world_rule", "intent"):
            results.append({"id": uid, "ok": False, "error": "high_risk_module_requires_single_approve"})
            continue
        if decision == "reject":
            st.set_canon_candidate_status(uid, "rejected")
            results.append({"id": uid, "ok": True, "status": "rejected"})
            continue
        ok, result, _ = _apply_one(st, w, uid, row)
        results.append({"id": uid, "ok": ok, "status": "approved" if ok else "error", "result": result})
    return {
        "ok": True,
        "processed": len(results),
        "ok_count": sum(1 for r in results if r.get("ok")),
        "results": results,
    }


@router.get("/canon/candidates/{uid}")
def get_candidate_detail(uid: str, work: str = "main"):
    from scribe3.canon_inbox import enrich_candidate

    st = _store(work)
    if not hasattr(st, "get_canon_candidate"):
        raise HTTPException(503, "no candidate store")
    row = st.get_canon_candidate(uid)
    if not row:
        raise HTTPException(404, "candidate not found")
    return {"work": work, **enrich_candidate(st, row)}


@router.post("/canon/candidates/{uid}/decide")
def decide_candidate(uid: str, req: DecideReq, work: str | None = None):
    w = _work_from(req.work, work)
    st = _store(w)
    if not hasattr(st, "get_canon_candidate"):
        raise HTTPException(503, "no candidate store")
    row = st.get_canon_candidate(uid)
    if not row:
        raise HTTPException(404, "candidate not found")
    if req.decision == "reject":
        st.set_canon_candidate_status(uid, "rejected")
        if hasattr(st, "log_canon_apply"):
            st.log_canon_apply(uid, row.get("module") or "", row.get("target") or "",
                               row.get("field"), "rejected", req.reason or "")
        return {"ok": True, "status": "rejected", "id": uid}
    if req.decision != "approve":
        raise HTTPException(422, "decision must be approve|reject")
    ok, result, item = _apply_one(
        st, w, uid, row, edit=req.edit, merge_into=req.merge_into,
    )
    return {"ok": ok, "status": "approved" if ok else "error", "id": uid, "result": result, "item": item}


@router.post("/canon/change-pack/apply")
def apply_change_pack_ep(req: ApplyPackReq, work: str | None = None):
    w = _work_from(req.work, work)
    st = _store(w) if req.use_surreal else _mem(w)
    if isinstance(st, InMemoryCanonStore) and req.seed_snapshot:
        snap = req.seed_snapshot
        if isinstance(snap.get("characters"), dict):
            st.characters.update(snap["characters"])
        if isinstance(snap.get("world_rules"), dict):
            st.world_rules.update(snap["world_rules"])
    try:
        raw = dict(req.pack or {})
        items = []
        for it in raw.get("items") or []:
            if not isinstance(it, dict):
                continue
            clean = dict(it)
            clean["approved"] = False
            lay = (clean.get("layer") or "L1").upper()
            mod = (clean.get("module") or "").strip().lower()
            if item_requires_human_approval(lay, mod):
                clean["requires_approval"] = True
                if mod and mod != "knowledge" and lay == "L2":
                    clean["layer"] = "L1"
            items.append(clean)
        raw["items"] = items
        pack = ChangePack.from_dict(raw)
    except Exception as e:
        raise HTTPException(400, f"invalid pack: {e}") from e
    result = apply_change_pack(
        pack,
        approved_item_ids=req.approved_item_ids,
        apply_objective_l2=req.apply_objective_l2,
        store=st,
    )
    # mark candidates approved when surreal
    if hasattr(st, "set_canon_candidate_status"):
        for a in result.get("applied") or []:
            cid = a.get("item_id")
            if cid:
                try:
                    st.set_canon_candidate_status(cid, "approved")
                except Exception:
                    pass
    return result


@router.get("/canon/store-snapshot")
def canon_store_snapshot(work: str = "main"):
    st = _store(work)
    if hasattr(st, "snapshot"):
        return {"work": work, "snapshot": st.snapshot()}
    from scribe3.api.services.canon_hooks import build_canon_snapshot_from_store
    return {"work": work, "snapshot": build_canon_snapshot_from_store(st)}

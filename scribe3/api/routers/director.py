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


class OrchDraftUpsertReq(BaseModel):
    object_type: str = "character"
    label: str
    fields: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    draft_id: str | None = None
    message: str | None = None  # 若提供则规则抽取后 upsert


class OrchFromDiscussionReq(BaseModel):
    package: dict[str, Any] | None = None
    summary: str = ""
    draft_ids: list[str] = Field(default_factory=list)
    # v6.1：讨论原文（可与 summary 合并）→ ChangePack；claims 可注入确定性主张
    text: str = ""
    claims: list[dict[str, Any]] = Field(default_factory=list)


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
    """统一编排入口：解析 WorkPackage + ui_target 事件列表。"""
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
    events = apply_ui_directive_events(
        pkg.get("ui_directive"),
        focus_policy=pkg.get("focus_policy") or "soft",
        ui_target=pkg.get("ui_target"),
    )
    out = {
        "work": work,
        "package": pkg,
        "ui_target": pkg.get("ui_target"),
        "focus_policy": pkg.get("focus_policy") or "soft",
        "ui_events": events,
        "use_world_write_run": bool(pkg.get("use_world_write_run")),
        "channel": pkg.get("channel"),
        # H1：顶层暴露，便于前端不挖 package 也能拼 instructions
        "instruction_suffix": pkg.get("instruction_suffix") or "",
        "context_pack": list(pkg.get("context_pack") or []),
    }
    if "total_score" in out or "composite_score" in str(out):
        raise HTTPException(500, "orchestration payload 不得含文学分")
    return out


def orch_drafts_list_ep(work: str = "main"):
    from scribe3.orchestration import drafts as draft_store
    rows = draft_store.list_drafts(work)
    return {"work": work, "drafts": rows, "count": len(rows)}


def orch_drafts_upsert_ep(req: OrchDraftUpsertReq, work: str = "main"):
    from scribe3.orchestration import drafts as draft_store
    if req.message:
        rows = draft_store.upsert_from_message(
            work, req.message, object_type_hint=req.object_type,
        )
        if req.label:
            row = draft_store.upsert_draft(
                work,
                object_type=req.object_type,
                label=req.label,
                fields=req.fields,
                aliases=req.aliases,
                draft_id=req.draft_id,
            )
            return {"work": work, "draft": row, "touched": rows}
        return {"work": work, "drafts": rows, "touched": rows}
    row = draft_store.upsert_draft(
        work,
        object_type=req.object_type,
        label=req.label,
        fields=req.fields,
        aliases=req.aliases,
        draft_id=req.draft_id,
    )
    return {"work": work, "draft": row}


def orch_from_discussion_ep(req: OrchFromDiscussionReq, work: str = "main"):
    """讨论 → WriteProposal（不落库）。"""
    from scribe3.orchestration import drafts as draft_store
    from scribe3.orchestration import package_state
    from scribe3.orchestration.proposal import proposal_from_discussion

    pkg = req.package or package_state.get_active(work)
    if not pkg:
        raise HTTPException(404, "no active work package")
    drafts = []
    if req.draft_ids:
        for did in req.draft_ids:
            d = draft_store.get_draft(work, did)
            if d:
                drafts.append(d)
    if not drafts:
        # 包内 entities 或全域列表
        for did in pkg.get("entities") or []:
            d = draft_store.get_draft(work, did)
            if d:
                drafts.append(d)
    if not drafts:
        drafts = draft_store.list_drafts(work)
        # 按 domain 过滤
        ot = None
        dom = str(pkg.get("domain") or "")
        if "character" in dom:
            ot = "character"
        elif "faction" in dom:
            ot = "faction"
        elif "promise" in dom:
            ot = "promise"
        if ot:
            drafts = [d for d in drafts if d.get("object_type") == ot]
    prop = proposal_from_discussion(pkg, drafts, summary=req.summary)
    # v6.1 §5.1：讨论 → ChangePack（不写库；L1 须另走 /canon/change-pack/apply）
    change_pack = None
    try:
        from scribe3.api.services.canon_hooks import discussion_change_pack
        st = _store_for(work)
        disc_text = (req.text or "").strip() or (req.summary or "").strip()
        claims = req.claims or None
        change_pack = discussion_change_pack(
            work=work,
            text=disc_text,
            source="discussion",
            claims=claims,
            st=st,
        )
    except Exception as e:
        change_pack = {
            "error": str(e)[:200],
            "items": [],
            "status": "error",
            "note": "change_pack 生成失败，不阻塞 orch proposal",
        }
    return {
        "work": work,
        "proposal": prop,
        "drafts_used": [d.get("draft_id") for d in drafts],
        "change_pack": change_pack,
        "canon_loop": {
            "path": "discussion",
            "silent_l1_write": False,
            "next": "POST /canon/change-pack/apply with approved_item_ids",
        },
    }


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

        def _patch_promise(**kw):
            pid = str(kw.get("promise_id") or kw.get("pid") or "").strip()
            if not pid or not hasattr(st, "update_promise"):
                return {"status": "error", "error": "missing promise_id"}
            fields = {
                k: kw[k] for k in (
                    "text", "resolution", "tier", "setup_chapter", "kind",
                    "payoff_min", "payoff_max",
                ) if kw.get(k) is not None
            }
            if not fields:
                return {"status": "noop", "promise_id": pid}
            try:
                ok = st.update_promise(pid, fields)
            except ValueError as e:
                return {"status": "error", "error": str(e)[:200]}
            return {"status": "written" if ok else "error", "promise_id": pid, "fields": list(fields)}

        def _patch_char(**kw):
            """角色字段更正。生产 Store 无 patch_character，须走 update_record 真落库。
            旧实现在无 patch_character 时只写 _orch_chars 内存 → API 仍空 → Web 设定像没写。"""
            cid = (kw.get("character_id") or kw.get("oid") or "").strip()
            local = cid.split(":", 1)[-1] if cid else ""
            if not local:
                return {"status": "error", "error": "empty character_id"}
            oid = cid if cid.startswith("role:") else f"role:{local}"
            fields = {
                k: v for k, v in kw.items()
                if k not in ("character_id", "oid", "work", "label") and v is not None
            }
            from scribe3.iceberg import persist_codex_fields_blocked
            _blk = persist_codex_fields_blocked("character", fields, mode="incremental")
            if _blk:
                return {"status": "error", "error": _blk["message"], "code": _blk["code"]}
            if hasattr(st, "patch_character"):
                ok = st.patch_character(cid, **fields)
                return {"status": "written" if ok is not False else "error", "ok": ok, "character_id": oid}
            if hasattr(st, "update_record"):
                from scribe3.ontology import Entity
                if hasattr(st, "exists") and not st.exists(oid):
                    st.add_entity(Entity(oid, "character", local))
                st.update_record(oid, fields)
                return {"status": "written", "character_id": oid, "fields": list(fields.keys())}
            # 测试桩：挂内存角色
            if not hasattr(st, "_orch_chars"):
                st._orch_chars = {}
            st._orch_chars[oid] = dict(fields)
            return {"status": "written", "character_id": oid}

        def _patch_plan(**kw):
            return {
                "status": "error",
                "http": 410,
                "code": "stage_gone",
                "error": "s3_patch_chapter_plan 已废，请走 s3_generate_stage 或 s3_patch_play / s3_patch_contract。",
            }
            seq = int(kw.get("seq") or kw.get("chapter") or 1)
            fields = {k: v for k, v in kw.items()
                      if k not in ("seq", "chapter", "work") and v is not None}
            from scribe3.iceberg import persist_fields_blocked, sync_design_surface
            from scribe3.stage_generate import load_design_book
            cur = st.get_chapter(seq) if hasattr(st, "get_chapter") else {}
            if "chapter_spine" in fields:
                fields = sync_design_surface(fields, cur if isinstance(cur, dict) else None, store=st)
            book = load_design_book(st, seq, {**(cur or {}), **fields} if isinstance(cur, dict) else fields)
            _blocked = persist_fields_blocked(
                fields,
                existing=cur if isinstance(cur, dict) else None,
                known_line_ids=known_line_ids_from_store(st),
                book=book,
                store=st,
                **persist_fate_kwargs(st, seq, fields, cur if isinstance(cur, dict) else None),
            )
            if _blocked:
                return {
                    "status": "error",
                    "error": _blocked["message"],
                    "code": _blocked["code"],
                    "iceberg": _blocked,
                }
            if hasattr(st, "update_chapter_meta") and fields:
                ok = st.update_chapter_meta(seq, fields)
                return {"status": "written" if ok else "error", "seq": seq, "fields": list(fields)}
            if hasattr(st, "patch_chapter"):
                st.patch_chapter(seq, **fields)
                return {"status": "written", "seq": seq}
            return {"status": "error", "error": "chapter not found"}

        def _set_intent(**kw):
            fields = {k: v for k, v in kw.items() if v is not None and k not in ("work",)}
            if not fields:
                return {"status": "noop"}
            if hasattr(st, "set_intent"):
                st.set_intent(fields)
                return {"status": "written", "fields": list(fields.keys())}
            return {"status": "error", "error": "no set_intent"}

        def _add_char(**kw):
            """新建角色：优先 store.add_character / add_entity，并写入 traits 字段。"""
            name = (kw.get("name") or kw.get("label") or "").strip()
            oid = (kw.get("oid") or kw.get("character_id") or "").strip()
            if not oid and name:
                oid = f"role:{name}"
            if oid and not oid.startswith("role:") and ":" not in oid:
                oid = f"role:{oid}"
            if not name and oid.startswith("role:"):
                name = oid.split(":", 1)[-1]
            if not oid:
                return {"status": "error", "error": "missing character oid/name"}
            from scribe3.canon_aliases import normalize_char_importance
            if kw.get("importance") is not None:
                kw = dict(kw)
                kw["importance"] = normalize_char_importance(kw.get("importance"))
            traits = {
                k: v for k, v in kw.items()
                if k not in ("oid", "character_id", "name", "label", "work") and v is not None
            }
            from scribe3.iceberg import persist_codex_fields_blocked
            _blk = persist_codex_fields_blocked("character", traits, mode="incremental")
            if _blk:
                return {"status": "error", "error": _blk["message"], "code": _blk["code"]}
            if hasattr(st, "add_character"):
                st.add_character(oid, name, **traits)
                return {"status": "written", "oid": oid, "name": name, "fields": list(traits.keys())}
            if hasattr(st, "add_entity"):
                from scribe3.ontology import Entity
                # traits 进 Entity，避免只建空壳名
                try:
                    ent = Entity(oid, "character", name or oid, traits=traits)
                except TypeError:
                    ent = Entity(oid, "character", name or oid)
                st.add_entity(ent)
                if traits and hasattr(st, "update_record"):
                    st.update_record(oid, traits)
                elif traits and hasattr(st, "patch_character"):
                    st.patch_character(oid, **traits)
                return {"status": "written", "oid": oid, "name": name, "fields": list(traits.keys())}
            return _patch_char(character_id=oid, oid=oid, name=name, **kw)

        def _add_volume(**kw):
            title = kw.get("title") or ""
            if hasattr(st, "add_volume"):
                row = st.add_volume(title=title, sort_order=int(kw.get("sort_order") or 0),
                                    intro=kw.get("intro"), color=kw.get("color"))
                return {"status": "written", "volume": row}
            return {"status": "error", "error": "no add_volume"}

        def _add_chapter(**kw):
            title = kw.get("title") or "未命名"
            vol = kw.get("volume") or kw.get("volume_id")
            if hasattr(st, "create_chapter"):
                row = st.create_chapter(title=title, volume_id=vol)
                return {"status": "written", "chapter": row}
            if hasattr(st, "save_chapter") and hasattr(st, "max_chapter"):
                seq = int(st.max_chapter() or 0) + 1
                st.save_chapter(seq, "", title=title)
                return {"status": "written", "seq": seq, "title": title}
            return {"status": "error", "error": "no create_chapter"}

        def _add_fact(**kw):
            text = kw.get("text") or kw.get("content") or kw.get("value") or ""
            if not text:
                return {"status": "error", "error": "empty fact"}
            if hasattr(st, "add_fact"):
                from scribe3.ontology import Fact
                import uuid as _uuid
                # 兼容 s3_add_fact(oid=...) 与旧 id= / prop:
                fid = (
                    kw.get("oid") or kw.get("id")
                    or f"fact:{_uuid.uuid4().hex[:12]}"
                )
                if not str(fid).startswith("fact:") and ":" not in str(fid):
                    fid = f"fact:{fid}"
                entity = kw.get("entity_id") or kw.get("entity") or "world:rule"
                attr = kw.get("attribute") or kw.get("kind") or "world_rule"
                f = Fact(
                    id=fid,
                    entity_id=entity,
                    attribute=attr,
                    value=text,
                    valid_from=int(kw.get("valid_from") or 1),
                    secret=bool(kw.get("secret") or False),
                )
                # D4：默认 supersede 同键开区间，避免新旧真值并存
                row = st.add_fact(f, supersede_open=True)
                return {"status": "written", "fact_id": fid, "value": text}
            return {"status": "error", "error": "no add_fact"}

        def _supersede_fact(**kw):
            if not hasattr(st, "supersede_fact"):
                return {"status": "error", "error": "no supersede_fact"}
            entity = (kw.get("entity_id") or kw.get("entity") or "").strip()
            attr = (kw.get("attribute") or "").strip()
            value = kw.get("value") or kw.get("text") or ""
            since = int(kw.get("since_chapter") or kw.get("valid_from") or 1)
            if not entity or not attr or not value:
                return {"status": "error", "error": "need entity_id, attribute, value"}
            oid = st.supersede_fact(
                entity, attr, str(value), since,
                secret=bool(kw.get("secret") or False),
            )
            return {"status": "written", "fact_id": oid, "value": value, "since_chapter": since}

        def _add_world_rule(**kw):
            name = (kw.get("name") or "").strip()
            if not name or not hasattr(st, "add_world_rule"):
                return {"status": "error", "error": "no name or add_world_rule"}
            from scribe3.iceberg import persist_codex_fields_blocked
            _blk = persist_codex_fields_blocked(
                "world_rule",
                {k: v for k, v in kw.items()
                 if v is not None and k in (
                     "cost", "source", "limitations", "exceptions", "capabilities",
                 )},
                mode="incremental",
            )
            if _blk:
                return {"status": "error", "error": _blk["message"], "code": _blk["code"]}
            from scribe3.canon_aliases import normalize_rule_category
            st.add_world_rule(
                name=name,
                category=normalize_rule_category(kw.get("category")),
                source=kw.get("source"),
                capabilities=kw.get("capabilities"),
                cost=kw.get("cost"),
                limitations=kw.get("limitations"),
                exceptions=kw.get("exceptions"),
                scope=kw.get("scope") or "global",
                established_chapter=kw.get("established_chapter"),
                note=kw.get("note"),
            )
            return {"status": "written", "name": name}

        def _add_faction(**kw):
            name = (kw.get("name") or "").strip()
            if not name or not hasattr(st, "add_faction"):
                return {"status": "error", "error": "no name or add_faction"}
            from scribe3.iceberg import persist_codex_fields_blocked
            _blk = persist_codex_fields_blocked(
                "faction",
                {k: v for k, v in kw.items()
                 if v is not None and k not in ("name", "work", "label")},
                mode="incremental",
            )
            if _blk:
                return {"status": "error", "error": _blk["message"], "code": _blk["code"]}
            st.add_faction(
                name,
                ideology=kw.get("ideology"),
                status=kw.get("status") or "active",
                leader=kw.get("leader"),
                known_members=kw.get("known_members"),
                public_face=kw.get("public_face"),
                private_operation=kw.get("private_operation"),
                first_mention_chapter=kw.get("first_mention_chapter"),
            )
            return {"status": "written", "name": name}

        def _add_item(**kw):
            name = (kw.get("name") or "").strip()
            if not name or not hasattr(st, "add_item"):
                return {"status": "error", "error": "no name or add_item"}
            from scribe3.iceberg import persist_codex_fields_blocked
            _blk = persist_codex_fields_blocked(
                "item",
                {k: v for k, v in kw.items()
                 if v is not None and k in (
                     "description", "current_owner", "special_properties",
                 )},
                mode="incremental",
            )
            if _blk:
                return {"status": "error", "error": _blk["message"], "code": _blk["code"]}
            st.add_item(
                name=name,
                category=kw.get("category"),
                description=kw.get("description"),
                current_owner=kw.get("current_owner"),
                symbolic_state=kw.get("symbolic_state") or "active",
                special_properties=kw.get("special_properties"),
                first_chapter=kw.get("first_chapter"),
            )
            return {"status": "written", "name": name}

        def _add_term(**kw):
            name = (kw.get("name") or "").strip()
            if not name or not hasattr(st, "add_term"):
                return {"status": "error", "error": "no name or add_term"}
            from scribe3.iceberg import persist_codex_fields_blocked
            _blk = persist_codex_fields_blocked(
                "term", {"definition": kw.get("definition")} if kw.get("definition") else {},
                mode="incremental",
            )
            if _blk:
                return {"status": "error", "error": _blk["message"], "code": _blk["code"]}
            st.add_term(
                name=name,
                category=kw.get("category"),
                definition=kw.get("definition"),
                aliases=kw.get("aliases"),
                first_mention_chapter=kw.get("first_mention_chapter"),
            )
            return {"status": "written", "name": name}

        def _add_motif(**kw):
            name = (kw.get("name") or "").strip()
            if not name or not hasattr(st, "add_motif"):
                return {"status": "error", "error": "no name or add_motif"}
            from scribe3.iceberg import persist_codex_fields_blocked
            _blk = persist_codex_fields_blocked(
                "motif",
                {k: v for k, v in kw.items()
                 if v and k in ("theme", "echoes", "echo_terms", "unfolding")},
                mode="incremental",
            )
            if _blk:
                return {"status": "error", "error": _blk["message"], "code": _blk["code"]}
            # 同名幂等：已存在则跳过新建，避免重复批准草案叠行
            try:
                for m in (st.list_motifs() or []):
                    if (m.get("name") or "").strip() == name:
                        return {"status": "noop", "name": name, "module": "motif", "reason": "exists"}
            except Exception:
                pass
            st.add_motif(
                name,
                theme=kw.get("theme") or "",
                echoes=kw.get("echoes") or "",
                unfolding=kw.get("unfolding") or "",
                echo_terms=kw.get("echo_terms"),
                phase=kw.get("phase") or "seed",
                tier=kw.get("tier") or "book",
                scope=kw.get("scope"),
            )
            return {"status": "written", "name": name, "module": "motif"}

        def _add_char_rel(**kw):
            src = (kw.get("src_oid") or kw.get("src") or "").strip()
            dst = (kw.get("dst_oid") or kw.get("dst") or "").strip()
            rel = (kw.get("relation") or kw.get("relation_type") or "未知").strip()
            if not src.startswith("role:"):
                src = f"role:{src}" if src else src
            if not dst.startswith("role:"):
                dst = f"role:{dst}" if dst else dst
            if not src or not dst or not hasattr(st, "add_character_relation"):
                return {"status": "error", "error": "bad src/dst or no add_character_relation"}
            st.add_character_relation(
                src, dst, rel,
                since_chapter=int(kw.get("since_chapter") or 1),
                note=kw.get("note"),
            )
            return {"status": "written", "src": src, "dst": dst, "relation": rel}

        executors = {
            "s3_plant_promise": _plant,
            "s3_patch_promise": _patch_promise,
            "s3_patch_character": _patch_char,
            "s3_add_character": _add_char,
            "s3_set_intent": _set_intent,
            "s3_patch_chapter_plan": _patch_plan,
            "s3_patch_chapter_meta": _patch_plan,
            "s3_add_volume": _add_volume,
            "s3_add_chapter": _add_chapter,
            "s3_add_fact": _add_fact,
            "s3_supersede_fact": _supersede_fact,
            "s3_add_world_rule": _add_world_rule,
            "s3_add_faction": _add_faction,
            "s3_add_item": _add_item,
            "s3_add_term": _add_term,
            "s3_add_motif": _add_motif,
            "s3_add_character_relation": _add_char_rel,
        }

    if req.decision != "approve":
        result = apply_proposal_ops(req.proposal, decision="reject", executors={})
        return {"work": work, "proposal": result, "ui_events": [], "ui_target": None, "focus_policy": "soft"}

    if not req.execute:
        # 仅标记：真实写由 Hermes 审批完成；此处不调用 executor
        result = dict(req.proposal)
        result["status"] = "awaiting_hermes_approval"
        result["note"] = "生产请经 Hermes 审批卡；execute=false 不落库"
        return {"work": work, "proposal": result, "ui_events": [], "ui_target": None, "focus_policy": "soft"}

    result = apply_proposal_ops(
        req.proposal, decision="approve", executors=executors, selected=req.selected,
    )
    ui_events = []
    ui_target = None
    if result.get("status") in ("applied", "partial"):
        from scribe3.orchestration.proposal import resolve_approve_ui_target
        # 与 proposal 层同一规则：优先 leaf，create+label 提升为 leaf（禁止 hard 到 codex_new）
        ui_target = resolve_approve_ui_target(req.proposal) or resolve_approve_ui_target(result)
        if isinstance(ui_target, dict) and ui_target.get("kind"):
            ui_events = apply_ui_directive_events(
                None, focus_policy="hard", ui_target=ui_target,
            )
        # 草稿标记
        try:
            from scribe3.orchestration import drafts as draft_store
            for did in (req.proposal or {}).get("draft_ids") or []:
                draft_store.mark_status(work, did, "approved")
        except Exception:
            pass
    return {
        "work": work,
        "proposal": result,
        "ui_events": ui_events,
        "ui_target": ui_target,
        "focus_policy": "hard" if ui_events else "soft",
    }


def _bind_and_register():
    from scribe3.api import app_impl as core
    g = globals()

    for _model_name in (
        "OrchResolveReq", "OrchTurnReq", "OrchProposalReq", "OrchProposalApplyReq",
        "OrchDraftUpsertReq", "OrchFromDiscussionReq",
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
    _bind("orch_drafts_list_ep", "/orchestration/drafts", ["GET"])
    _bind("orch_drafts_upsert_ep", "/orchestration/drafts", ["POST"])
    _bind("orch_from_discussion_ep", "/orchestration/proposal/from-discussion", ["POST"])


_bind_and_register()

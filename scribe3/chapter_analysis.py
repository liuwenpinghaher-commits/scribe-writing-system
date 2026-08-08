"""章后统一模型分析：一次 LLM 同时产出 L1 设定增量 + L2 知识/事件 delta。

定稿（finalize）与 ingest 共用，避免「设定抽一遍、知识再抽一遍」。
失败 fail-soft：解析失败时调用方回退旧分路；不静默写 L1。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Any, Callable

from scribe3.canon_extract import claims_from_settings_json, resolve_extract_mode
from scribe3.canon_loop import CanonClaim, parse_marker_claims
from scribe3.critique import build_knowledge_extract_prompt, parse_knowledge_delta

_log = logging.getLogger("scribe3.chapter_analysis")

# 进程内短缓存：同 work+seq+prose 指纹复用（finalize 后紧接 ingest 免二调）
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_MAX = 64


def unified_analysis_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_UNIFIED_CHAPTER_ANALYSIS") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def quick_qc_summary(prose: str) -> dict[str, Any]:
    """确定性 QC 摘要（无额外模型调用），挂在终选/重分析报告上。"""
    text = prose or ""
    if not text.strip():
        return {"source": "deterministic", "empty": True, "grade": "light", "gates_hit": [], "counts": {}}
    try:
        from scribe3.critique import aggregate_ai_grade, quality_flags
        flags = quality_flags(text)
        grade = aggregate_ai_grade(flags, text)
        counts: dict[str, int] = {}
        for k, v in (flags or {}).items():
            if k in ("rhythm", "adverb"):
                if isinstance(v, dict) and v:
                    counts[k] = 1
                continue
            if isinstance(v, list):
                counts[k] = len(v)
        return {
            "source": "deterministic",
            "empty": False,
            "grade": grade.get("grade") or "light",
            "gates_hit": list(grade.get("gates_hit") or []),
            "counts": {k: n for k, n in counts.items() if n},
            "word_count": len("".join(text.split())),
        }
    except Exception as e:
        _log.warning("quick_qc_summary: %s", e)
        return {"source": "deterministic", "error": str(e)[:120]}


def _prose_fp(prose: str) -> str:
    return hashlib.sha256((prose or "").encode("utf-8")).hexdigest()[:16]


def _cache_key(work: str, seq: int, prose: str) -> str:
    return f"{work}|{seq}|{_prose_fp(prose)}"


def _normalize_cache_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """统一缓存形态：knowledge + settings + discipline(+ 可选 claims)。"""
    if not isinstance(payload, dict):
        return None
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    claims = payload.get("claims")
    disc = payload.get("discipline") if isinstance(payload.get("discipline"), dict) else None
    out = {
        "knowledge": payload.get("knowledge"),
        "settings": settings,
        "format": payload.get("format"),
        "claims": claims if isinstance(claims, list) else [],
        "discipline": disc,
    }
    return out


def get_cached_analysis(
    work: str,
    seq: int,
    prose: str,
    *,
    st: Any = None,
) -> dict[str, Any] | None:
    """进程内 → 库内。返回含 knowledge/settings/discipline/claims。"""
    mem = _CACHE.get(_cache_key(work, seq, prose))
    if mem:
        return _normalize_cache_payload(mem)
    if st is not None and hasattr(st, "get_post_analysis_cache"):
        try:
            body = st.get_post_analysis_cache(int(seq), prose or "")
        except Exception as e:
            _log.warning("get_post_analysis_cache: %s", e)
            body = None
        if body:
            settings = body.get("settings") if isinstance(body.get("settings"), dict) else {}
            claims = claims_from_settings_json(settings) if settings else []
            if settings and "knowledge_edges" in settings and "knowledge" not in settings:
                settings = dict(settings)
                settings["knowledge"] = settings.get("knowledge_edges") or []
                claims = claims_from_settings_json(settings)
            payload = {
                "knowledge": body.get("knowledge"),
                "settings": settings,
                "claims": claims,
                "format": body.get("format") or "store",
                "discipline": body.get("discipline") if isinstance(body.get("discipline"), dict) else None,
            }
            put_cached_analysis(work, seq, prose, payload, st=None)
            return payload
    return None


def clear_cached_analysis(
    work: str,
    seq: int,
    *,
    prose: str | None = None,
    st: Any = None,
) -> None:
    """强制重分析前清进程缓存 + 库缓存。"""
    if prose is not None:
        _CACHE.pop(_cache_key(work, seq, prose), None)
    else:
        prefix = f"{work}|{int(seq)}|"
        for k in list(_CACHE.keys()):
            if k.startswith(prefix):
                _CACHE.pop(k, None)
    if st is not None and hasattr(st, "clear_post_analysis_cache"):
        try:
            st.clear_post_analysis_cache(int(seq))
        except Exception as e:
            _log.warning("clear_post_analysis_cache: %s", e)


def put_cached_analysis(
    work: str,
    seq: int,
    prose: str,
    payload: dict[str, Any],
    *,
    st: Any = None,
) -> None:
    """双写：进程内 + 可选 Surreal chapter 字段。"""
    # 合并已有缓存字段（避免只写 knowledge 时冲掉 discipline）
    prev = _CACHE.get(_cache_key(work, seq, prose)) or {}
    settings = payload.get("settings")
    if not isinstance(settings, dict):
        settings = prev.get("settings") if isinstance(prev.get("settings"), dict) else {}
    claims = payload.get("claims") if payload.get("claims") is not None else prev.get("claims") or []
    disc = payload.get("discipline") if "discipline" in payload else prev.get("discipline")
    kn = payload.get("knowledge") if "knowledge" in payload else prev.get("knowledge")
    fmt = payload.get("format") or prev.get("format")
    norm = {
        "knowledge": kn,
        "settings": settings,
        "claims": claims if isinstance(claims, list) else [],
        "format": fmt,
        "discipline": disc if isinstance(disc, dict) else None,
    }
    if len(_CACHE) >= _CACHE_MAX:
        try:
            _CACHE.pop(next(iter(_CACHE)))
        except Exception:
            _CACHE.clear()
    _CACHE[_cache_key(work, seq, prose)] = norm
    if st is not None and hasattr(st, "set_post_analysis_cache"):
        try:
            st.set_post_analysis_cache(int(seq), prose or "", {
                "knowledge": norm.get("knowledge"),
                "settings": settings,
                "format": norm.get("format"),
                "discipline": norm.get("discipline"),
            })
        except Exception as e:
            _log.warning("set_post_analysis_cache: %s", e)


def discipline_cache_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_DISCIPLINE_CACHE") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def run_discipline_with_cache(
    *,
    work: str,
    seq: int,
    prose: str,
    complete_fn: Callable[..., str],
    brief: str = "",
    known: dict | None = None,
    st: Any = None,
    force: bool = False,
) -> dict[str, Any]:
    """纪律判：优先章后缓存，未命中再调模型并写回缓存。

    返回与 discipline_truncate 同构：text/violations/extra/changed/(cut_after)/(parse_failed)/cache_hit
    """
    from scribe3.critique import discipline_truncate

    prose = prose or ""
    if not force and discipline_cache_enabled():
        cached = get_cached_analysis(work, seq, prose, st=st)
        disc = (cached or {}).get("discipline") if cached else None
        if isinstance(disc, dict) and ("violations" in disc or "ok" in disc or "changed" in disc):
            # 还原 truncate 结果
            out = {
                "text": disc.get("text") if disc.get("changed") and disc.get("text") else prose,
                "violations": list(disc.get("violations") or []),
                "extra": list(disc.get("extra") or []),
                "changed": bool(disc.get("changed")),
                "cache_hit": True,
                "source": "cache",
            }
            if disc.get("cut_after"):
                out["cut_after"] = disc["cut_after"]
            if disc.get("parse_failed"):
                out["parse_failed"] = True
            return out

    # complete_fn 可能是 (prompt) 或 (prompt, system)
    def _fn(prompt: str, system: str | None = None) -> str:
        try:
            return complete_fn(prompt, system)  # type: ignore[misc]
        except TypeError:
            return complete_fn(prompt)  # type: ignore[call-arg]

    result = discipline_truncate(prose, brief or "", _fn, known=known)
    # 写入缓存（不存过长 text，除非截断后）
    disc_store: dict[str, Any] = {
        "ok": not bool(result.get("violations")) and not result.get("changed"),
        "violations": list(result.get("violations") or []),
        "extra": list(result.get("extra") or []),
        "changed": bool(result.get("changed")),
        "cut_after": result.get("cut_after") or "",
    }
    if result.get("parse_failed"):
        disc_store["parse_failed"] = True
    if result.get("changed") and result.get("text") and result["text"] != prose:
        # 仅存截断稿（通常更短）
        disc_store["text"] = result["text"]
    if discipline_cache_enabled():
        put_cached_analysis(work, seq, prose, {"discipline": disc_store}, st=st)
    result = dict(result)
    result["cache_hit"] = False
    result["source"] = "llm"
    return result


def build_unified_chapter_prompt(
    prose: str,
    *,
    known_character_names: list[str] | None = None,
    world_rule_names: list[str] | None = None,
    motif_names: list[str] | None = None,
    promise_items: list[dict] | None = None,
    belief_chars: list[dict] | None = None,
) -> str:
    """构造「knowledge + settings」双栏 JSON 的统一 prompt。"""
    from scribe3.ingest import _relation_touch_prompt_addendum

    base = build_knowledge_extract_prompt(
        prose,
        motif_names=motif_names,
        promise_items=promise_items,
        belief_chars=belief_chars,
    )
    # 把「只输出一行 JSON: {learned...」改成嵌套 knowledge 栏说明
    base = base.replace(
        "只输出一行 JSON:",
        "先在脑中完成知识账本抽取，最终放入顶层键 knowledge。",
    )
    known = list(known_character_names or [])
    wr = list(world_rule_names or [])
    bible = ""
    if known:
        bible += "已立角色（勿重复新建，可 patch）: " + "、".join(known[:40]) + "\n"
    if wr:
        bible += "已立世界规则: " + "、".join(str(x) for x in wr[:20]) + "\n"
    if motif_names:
        bible += "已立母题（触及只能选自下列，禁发明）: " + "、".join(motif_names[:20]) + "\n"

    settings_block = (
        "\n\n【第二栏 · 设定增量 settings · 进作者收件箱，禁止静默写库】\n"
        "相对【已有设定】只抽正文明确出现的增量；宁缺毋滥；每条须 evidence 原文短引。\n"
        "禁止：推门/一会/鞋帮等口语当势力；「叫我来看」类动词短语当人名。\n"
        "settings 对象键（缺省空数组）:\n"
        "entities[{module,op,name,fields,evidence,confidence}] module∈character|faction|item|term\n"
        "world_rules, factions, items, terms, relations[{a,b,relation,evidence}],\n"
        "facts[{entity,attribute,value,evidence}], knowledge_edges[{knower,proposition,via,evidence}],\n"
        "promises[{op,text,evidence}], motifs[{op,name,theme,echoes,evidence}]\n"
        f"【已有设定】\n{bible or '(空库)'}\n"
    )

    wrapper = (
        "\n\n【统一输出格式 · 只输出一行 JSON，不要 markdown】\n"
        '{"knowledge":{'
        '"learned":[...],"did":[...],"voice_shift":[...],"arc":[...],"events":[...],'
        '"motif":[...],"promise_touch":[...],"belief":[...],"relation_touches":[...]'
        '},"settings":{'
        '"entities":[],"world_rules":[],"factions":[],"items":[],"terms":[],'
        '"relations":[],"facts":[],"knowledge_edges":[],"promises":[],"motifs":[]'
        '}}\n'
        "knowledge 栏字段语义与上文知识抽取一致；settings 栏为设定增量。\n"
        "若某栏无内容仍须输出空数组。\n"
    )
    return base + _relation_touch_prompt_addendum() + settings_block + wrapper


def _normalize_knowledge_blob(blob: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(blob, dict):
        return None
    # 允许模型把 knowledge 字段写成与 parse_knowledge_delta 相同扁平结构
    return {
        "learned": list(blob.get("learned") or []),
        "did": list(blob.get("did") or []),
        "voice_shift": list(blob.get("voice_shift") or []),
        "arc": list(blob.get("arc") or []),
        "motif": list(blob.get("motif") or []),
        "promise_touch": list(blob.get("promise_touch") or []),
        "belief": list(blob.get("belief") or []),
        "events": list(blob.get("events") or []),
        "relation_touches": list(blob.get("relation_touches") or []),
    }


def parse_unified_chapter_reply(reply: str) -> dict[str, Any]:
    """解析统一回复。

    成功字段：
      knowledge: dict|None  （None=知识栏不可用）
      settings: dict
      claims: list[CanonClaim]
      format: unified|legacy_knowledge|legacy_settings
    """
    out: dict[str, Any] = {
        "knowledge": None,
        "settings": {},
        "claims": [],
        "format": "empty",
        "raw_ok": False,
    }
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            return out
        data = json.loads(m.group(0))
    except Exception as e:
        _log.warning("parse_unified_chapter_reply: %s", e)
        return out
    if not isinstance(data, dict):
        return out
    out["raw_ok"] = True

    if isinstance(data.get("knowledge"), dict) or isinstance(data.get("settings"), dict):
        kn = _normalize_knowledge_blob(data.get("knowledge") if isinstance(data.get("knowledge"), dict) else {})
        settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
        # 兼容 settings.knowledge_edges vs knowledge key 冲突：设定栏用 knowledge_edges
        if "knowledge_edges" in settings and "knowledge" not in settings:
            settings = dict(settings)
            settings["knowledge"] = settings.get("knowledge_edges") or []
        out["knowledge"] = kn
        out["settings"] = settings
        out["claims"] = claims_from_settings_json(settings)
        out["format"] = "unified"
        return out

    # 旧扁平知识 delta
    if any(k in data for k in ("learned", "did", "events", "arc")):
        out["knowledge"] = _normalize_knowledge_blob(data)
        out["format"] = "legacy_knowledge"
        return out

    # 旧扁平设定
    if any(k in data for k in ("entities", "world_rules", "factions", "items", "terms", "motifs")):
        out["settings"] = data
        out["claims"] = claims_from_settings_json(data)
        out["format"] = "legacy_settings"
        return out

    return out


def run_unified_llm_extract(
    prose: str,
    complete_fn: Callable[[str], str],
    *,
    known_character_names: list[str] | None = None,
    world_rule_names: list[str] | None = None,
    motif_names: list[str] | None = None,
    promise_items: list[dict] | None = None,
    belief_chars: list[dict] | None = None,
    max_attempts: int = 2,
) -> dict[str, Any]:
    """调模型并解析；失败返回 knowledge=None, claims=[]。"""
    prompt = build_unified_chapter_prompt(
        prose,
        known_character_names=known_character_names,
        world_rule_names=world_rule_names,
        motif_names=motif_names,
        promise_items=promise_items,
        belief_chars=belief_chars,
    )
    last: dict[str, Any] = {"knowledge": None, "settings": {}, "claims": [], "format": "empty", "raw_ok": False}
    for attempt in range(max(1, max_attempts)):
        try:
            reply = complete_fn(prompt) or ""
        except Exception as e:
            _log.warning("unified llm attempt %s fail: %s", attempt, e)
            continue
        parsed = parse_unified_chapter_reply(reply)
        last = parsed
        # 至少一侧有货，或 raw_ok 且 knowledge 有结构
        kn = parsed.get("knowledge")
        has_kn = bool(kn and any(kn.get(k) for k in ("learned", "did", "events", "arc", "motif", "promise_touch")))
        has_set = bool(parsed.get("claims"))
        if parsed.get("format") == "unified" and parsed.get("raw_ok"):
            return parsed
        if has_kn or has_set:
            return parsed
        kd = parse_knowledge_delta(reply)
        if kd is not None:
            from scribe3.ingest import parse_relation_touches
            parsed["knowledge"] = {**kd, "relation_touches": parse_relation_touches(reply)}
            parsed["format"] = "legacy_knowledge_salvage"
            return parsed
    return last


def ensure_events_in_knowledge(
    knowledge: dict[str, Any] | None,
    prose: str,
    complete_fn: Callable[[str], str],
    *,
    max_attempts: int = 2,
) -> dict[str, Any] | None:
    """统一包若漏 events，专用第二枪补事件（与 ingest 旧逻辑同构）。"""
    if knowledge is None:
        return None
    from scribe3.ingest import _build_dedicated_event_extract_prompt, _has_persistable_event
    if _has_persistable_event(knowledge):
        return knowledge
    for _ in range(max(1, max_attempts)):
        try:
            reply = complete_fn(_build_dedicated_event_extract_prompt(prose)) or ""
        except Exception as e:
            _log.warning("event backfill fail: %s", e)
            continue
        event_delta = parse_knowledge_delta(reply)
        if event_delta is not None and _has_persistable_event(event_delta):
            knowledge = dict(knowledge)
            knowledge["events"] = event_delta["events"]
            knowledge["_events_backfilled"] = True
            return knowledge
    return knowledge


def context_from_store(st: Any) -> dict[str, Any]:
    """从 store 收集统一抽取上下文。"""
    known: list[str] = []
    wr: list[str] = []
    motifs: list[str] = []
    promises: list[dict] = []
    belief: list[dict] = []
    if st is None:
        return {
            "known_character_names": known,
            "world_rule_names": wr,
            "motif_names": motifs,
            "promise_items": promises,
            "belief_chars": belief,
        }
    try:
        for c in (st.characters() if hasattr(st, "characters") else []) or []:
            n = (getattr(c, "name", None) or "").strip()
            if n:
                known.append(n)
            try:
                a = st.char_anchors(c.id) if hasattr(st, "char_anchors") else {}
                if a.get("lie"):
                    belief.append({"name": n or c.id, "lie": a["lie"]})
            except Exception:
                pass
    except Exception:
        pass
    try:
        if hasattr(st, "list_world_rules"):
            for r in st.list_world_rules() or []:
                if isinstance(r, dict) and r.get("name"):
                    wr.append(str(r["name"]))
    except Exception:
        pass
    try:
        if hasattr(st, "list_motifs"):
            motifs = [m.get("name") for m in (st.list_motifs() or []) if m.get("name")]
    except Exception:
        pass
    try:
        if hasattr(st, "open_promises"):
            promises = [{"id": p["id"], "text": p["text"]} for p in (st.open_promises() or [])]
        elif hasattr(st, "list_promises"):
            promises = [
                {"id": p.get("id"), "text": p.get("text")}
                for p in (st.list_promises() or [])
                if p.get("status") == "open"
            ]
    except Exception:
        pass
    return {
        "known_character_names": known,
        "world_rule_names": wr,
        "motif_names": motifs,
        "promise_items": promises,
        "belief_chars": belief,
    }


def extract_for_ingest(
    st: Any,
    seq: int,
    complete_fn: Callable[[str], str],
    *,
    work: str = "main",
    max_attempts: int = 2,
    prose: str | None = None,
) -> dict[str, Any]:
    """ingest 用：优先缓存 / 统一抽取 → knowledge delta。"""
    if not prose:
        ch = st.get_chapter(seq) if st and hasattr(st, "get_chapter") else {}
        prose = (ch or {}).get("prose") or ""
    cached = get_cached_analysis(work, seq, prose, st=st)
    if cached and cached.get("knowledge") is not None:
        kn = cached["knowledge"]
        # 缓存也可能漏 events：有 complete_fn 时补枪
        kn = ensure_events_in_knowledge(kn, prose, complete_fn, max_attempts=1)
        return {
            "delta": kn,
            "claims": cached.get("claims") or [],
            "source": "cache" if not (kn or {}).get("_events_backfilled") else "cache+events",
            "format": cached.get("format"),
        }
    if not unified_analysis_enabled() or not complete_fn:
        return {"delta": None, "claims": [], "source": "disabled"}
    ctx = context_from_store(st)
    parsed = run_unified_llm_extract(
        prose, complete_fn, max_attempts=max_attempts, **ctx,
    )
    kn = parsed.get("knowledge")
    if kn is not None and "relation_touches" not in kn:
        kn["relation_touches"] = []
    kn = ensure_events_in_knowledge(kn, prose, complete_fn, max_attempts=max_attempts)
    put_cached_analysis(work, seq, prose, {
        "knowledge": kn,
        "settings": parsed.get("settings") or {},
        "claims": parsed.get("claims") or [],
        "format": parsed.get("format"),
    }, st=st)
    return {
        "delta": kn,
        "claims": parsed.get("claims") or [],
        "source": "unified",
        "format": parsed.get("format"),
    }


def claims_for_prose_unified(
    prose: str,
    complete_fn: Callable[[str], str] | None,
    *,
    st: Any = None,
    work: str = "main",
    seq: int | None = None,
    mode: str | None = None,
    max_attempts: int = 2,
) -> tuple[list[CanonClaim], dict[str, Any]]:
    """设定抽取入口：标记 +（默认）统一模型；返回 (claims, meta)。"""
    m = resolve_extract_mode(mode)
    claims: list[CanonClaim] = list(parse_marker_claims(prose or ""))
    meta: dict[str, Any] = {
        "extract_mode": m,
        "unified": False,
        "knowledge": None,
        "format": None,
    }
    if m == "marker" or not complete_fn:
        return claims, meta

    if m in ("llm", "hybrid") and unified_analysis_enabled():
        ctx = context_from_store(st)
        if seq is not None:
            cached = get_cached_analysis(work, seq, prose or "", st=st)
            if cached and (
                cached.get("claims")
                or cached.get("knowledge") is not None
                or cached.get("settings")
            ):
                for c in cached.get("claims") or []:
                    claims.append(c)
                kn = cached.get("knowledge")
                if kn is not None and complete_fn:
                    kn = ensure_events_in_knowledge(kn, prose or "", complete_fn, max_attempts=1)
                meta.update({
                    "unified": True,
                    "knowledge": kn,
                    "format": cached.get("format") or "cache",
                    "from_cache": True,
                    "settings": cached.get("settings") or {},
                })
                return claims, meta
        parsed = run_unified_llm_extract(
            prose or "", complete_fn, max_attempts=max_attempts, **ctx,
        )
        kn = parsed.get("knowledge")
        if kn is not None and complete_fn:
            kn = ensure_events_in_knowledge(kn, prose or "", complete_fn, max_attempts=1)
            parsed["knowledge"] = kn
        for c in parsed.get("claims") or []:
            claims.append(c)
        meta.update({
            "unified": True,
            "knowledge": kn,
            "format": parsed.get("format"),
            "from_cache": False,
            "settings": parsed.get("settings") or {},
        })
        if seq is not None:
            put_cached_analysis(work, seq, prose or "", {
                "knowledge": kn,
                "settings": parsed.get("settings") or {},
                "claims": parsed.get("claims") or [],
                "format": parsed.get("format"),
            }, st=st)
        return claims, meta

    # hybrid/llm 但统一关闭：回退旧仅设定 LLM
    if m in ("llm", "hybrid") and complete_fn:
        from scribe3.canon_extract import _llm_extract
        from scribe3.api.services.canon_hooks import build_canon_snapshot_from_store
        snap = build_canon_snapshot_from_store(st) if st is not None else {}
        for c in _llm_extract(
            prose or "", complete_fn,
            known_character_names=context_from_store(st)["known_character_names"],
            canon_snapshot=snap,
        ):
            claims.append(c)
        meta["unified"] = False
        meta["format"] = "settings_only_llm"
    return claims, meta

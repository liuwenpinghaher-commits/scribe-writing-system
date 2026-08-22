"""冰山只做注入截断。evaluate_iceberg 语义闸已废，只留 clip_for。
"""
from __future__ import annotations

import re
from typing import Any

# 水下质量地板（覆盖/信息量，不是评分）
SYNOPSIS_FLOOR = 500
BEAT_EACH_FLOOR = 500
BEAT_SUM_FLOOR = 2000
DEDUCTION_FLOOR = 5000
DRAFT_FLOOR = 10000
PROSE_SURFACE = 5000  # 水面：正文要有足够面积让冰山露出来

# 注入帽：刚过闸必须全给；只砍「写超了很多」的尾巴。final 与 thicken 同档。
# 设定 kind 与章字段共用本表；讨论/写作/名片/秘密由组装层决定，clip_for 不加 purpose。
INJECT_CAP = {
    "synopsis": 2500,
    "beat": 1200,
    "scene_truth": 2500,
    "deduction": 6000,
    "draft": 12000,
    "character_public": 2500,
    "faction_public": 2500,
    "item": 1200,
    "term": 1200,
    "world_rule": 1200,
}
DEDUCTION_PACK_CAP = 8500  # 5000 闸 + 2500 真相 + ≤1000 头尾
NEAR_FLOOR_RATIO = 1.2
# 包级帽（不是 INJECT_CAP 行）
CARD_LINE_CAP = 80
CARDS_PACK_CAP = 1500
NAMED_PACK_SOFT_CAP_NARROW = 4500
NAMED_PACK_SOFT_CAP_WIDE = 12000

_WS = re.compile(r"\s+")

# 这些阶段是在写厚冰山，不得用冰山闸卡住
_THICKEN_PHASES = frozenset({
    "outline", "plan", "beats", "design", "chapter_design", "deduce", "scaffold", "meta",
})
_PROSE_PHASES = frozenset({"", "draft", "final", "write", "prose"})


def cn_len(text: str | None) -> int:
    from scribe3.llm_visible import strip_thinking_markup
    return len(_WS.sub("", strip_thinking_markup(text or "")))


def _floor_for(field: str) -> int:
    if field in ("synopsis", "beat"):
        return 0
    return {
        "synopsis": SYNOPSIS_FLOOR,
        "beat": BEAT_EACH_FLOOR,
        "scene_truth": 0,
        "deduction": 0,
        "draft": 0,
    }.get(field, 0)


def clip_for(field: str, text: str | None) -> str:
    """唯一冰山裁切：近地板不裁；否则裁到 INJECT_CAP 且不低于地板。"""
    raw = text or ""
    if not raw:
        return ""
    n = cn_len(raw)
    floor = _floor_for(field)
    cap = int(INJECT_CAP.get(field) or 0)
    if floor and n <= int(floor * NEAR_FLOOR_RATIO):
        return raw
    if not cap or n <= cap:
        return raw
    # 按字符裁到 cap，尽量不拆到地板以下
    keep = max(cap, floor)
    if len(raw) <= keep:
        return raw
    return raw[:keep]


def named_pack_soft_cap(*, work: str | None) -> int:
    """点名包软顶。走 resolve_write_caps(work)：48k→4500，96k→12000。

    显式 ``SCRIBE3_CODEX_INJECT_CAP`` 正整数覆盖两档（运维逃生）。
    禁止 ``get_codex_inject_cap()`` 无 work 各算各的。
    """
    from scribe3.feature_flags import get_flag
    raw = get_flag("SCRIBE3_CODEX_INJECT_CAP").strip()
    if raw.isdigit():
        return max(500, int(raw))
    from scribe3.context_budget import resolve_write_caps
    caps = resolve_write_caps(work)
    ph = int(caps.get("prompt_hard") or 0)
    if ph >= 90_000:
        return NAMED_PACK_SOFT_CAP_WIDE
    return NAMED_PACK_SOFT_CAP_NARROW


def iceberg_enabled() -> bool:
    from scribe3.feature_flags import get_flag
    return get_flag("SCRIBE3_ICEBERG_WRITE").strip().lower() not in ("0", "false", "no", "off")


def evaluate_iceberg(
    ch: dict | None,
    *,
    for_phase: str = "draft",
    known_line_ids: set | None = None,
    st=None,
    seq: int | None = None,
    fate_ctx=None,
) -> dict[str, Any]:
    """旧语义闸已废。只给旧调用点一个永远放行的壳。"""
    return {"ok": True, "missing": [], "measures": {}, "message": "", "code": ""}


def should_block_prose_write(phase: str | None, *, write_intent: bool) -> bool:
    if not write_intent:
        return False
    p = (phase or "draft").strip().lower()
    if p in _THICKEN_PHASES:
        return False
    return p in _PROSE_PHASES


def design_half_block(detail: str) -> dict[str, Any]:
    """旧半稿闸已废。"""
    return {
        "code": "stage_gone",
        "http": 410,
        "message": "章纲/节拍半稿已废。请走 duty → design。",
        "missing": [{"id": "design_half", "detail": detail}],
    }


def sync_design_surface(
    fields: dict[str, Any] | None,
    existing: dict[str, Any] | None = None,
    *,
    store=None,
) -> dict[str, Any]:
    """旧章纲同步已废。原样交回字段。"""
    return dict(fields or {})


def persist_fields_blocked(
    fields: dict | None,
    *,
    existing: dict | None = None,
    known_line_ids: set | None = None,
    fate_ctx=None,
    chapter: dict | None = None,
    book=None,
    store=None,
) -> dict[str, Any] | None:
    """旧大纲/节拍 persist 闸已废。None=放行。"""
    return None


# ── 设定库 persist 闸（独立旗；不写入 _floor_for）────────────────
CODEX_PACK_FLOOR: dict[str, int] = {
    "character": 1200,
    "faction": 1200,
    "item": 1200,
    "term": 1200,
    "world_rule": 1200,
}
CODEX_FIELD_FLOOR: dict[str, dict[str, int]] = {
    "character": {
        "personality_detail": 200, "surface_goal": 80, "deep_need": 80,
        "fear": 80, "internal_conflict": 80, "appearance": 40, "backstory": 200,
    },
    "faction": {
        "ideology": 200, "public_face": 80, "recruitment": 80,
        "secret_agenda": 80, "origin": 80,
        "artifact_operation": 80, "external_manipulation": 80,
        "acceleration_methods": 80,
    },
    "item": {"description": 400},
    "term": {"definition": 1200},
    "world_rule": {"cost": 80, "source": 1},
    "motif": {"theme": 40, "unfolding": 80},
    "voice": {"style_summary": 80},
}
CODEX_MIN_ITEMS: dict[str, dict[str, int]] = {
    "character": {"abilities": 1, "weaknesses": 1},
    "faction": {"goals": 1},
    "item": {"special_properties": 1},
    "world_rule": {"limitations": 1, "exceptions": 1, "capabilities": 1},
    "motif": {"echo_terms": 3},
}
_CODEX_PACK_SKIP_KEYS = frozenset({
    "name", "id", "kind", "archived", "category", "scope", "symbolic_state",
    "importance", "first_appearance", "first_chapter", "first_mention_chapter",
    "status", "leader", "phase", "tier",
})
_SENTINEL_NONE = frozenset({"无", "无人", "遗失"})


def codex_thicken_gate_enabled() -> bool:
    from scribe3.feature_flags import get_flag
    return get_flag("SCRIBE3_CODEX_THICKEN_GATE").strip().lower() not in ("0", "false", "no", "off")


def field_cn(value: Any) -> int:
    """只计正文。dict/list 用 json.dumps 去空白。不走 clip_for。"""
    if value is None:
        return 0
    if isinstance(value, (list, tuple, set)):
        items = [x for x in value if str(x).strip()]
        if not items:
            return 0
        import json as _json
        return cn_len(_json.dumps(list(items), ensure_ascii=False, separators=(",", ":")))
    if isinstance(value, dict):
        if not value:
            return 0
        import json as _json
        return cn_len(_json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return cn_len(str(value))


def _is_empty_codex_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return not str(value).strip()


def pack_cn(kind: str, public_fields: dict | None) -> int:
    """公开包长 = 各公开厚字段 field_cn 之和（不含 name/枚举/旗标）。"""
    if not isinstance(public_fields, dict):
        return 0
    total = 0
    for key, val in public_fields.items():
        k = str(key or "")
        if not k or k in _CODEX_PACK_SKIP_KEYS or k.endswith("_secret"):
            continue
        if k in ("secret_agenda",):
            continue
        total += field_cn(val)
    return total


def persist_codex_fields_blocked(
    kind: str,
    submitted: dict | None,
    *,
    existing: dict | None = None,
    mode: str = "incremental",
) -> dict[str, Any] | None:
    """None=放行。incremental 只评本次非空厚字段；pack 评整包+must。"""
    del existing  # L1 不并包；保留形参对照「即将写入」
    if not codex_thicken_gate_enabled() or not isinstance(submitted, dict):
        return None
    k = (kind or "").strip().lower()
    if k == "voice_profile":
        k = "voice"
    missing: list[dict[str, Any]] = []
    floors = CODEX_FIELD_FLOOR.get(k) or {}
    mins = CODEX_MIN_ITEMS.get(k) or {}
    if (mode or "incremental") == "pack":
        cn = pack_cn(k, submitted)
        need = int(CODEX_PACK_FLOOR.get(k) or 0)
        if need and cn < need:
            missing.append({"id": "pack", "got": cn, "need": need})
        if k == "term":
            definition = str(submitted.get("definition") or "")
            for part in ("是什么", "不是什么", "本书用法", "边界"):
                if part not in definition:
                    missing.append({"id": f"part:{part}", "got": 0, "need": 1})
        if k == "character":
            for key, n in (
                ("personality_detail", 200), ("surface_goal", 80), ("deep_need", 80),
                ("fear", 80), ("internal_conflict", 80),
            ):
                got = field_cn(submitted.get(key))
                if got < n:
                    missing.append({"id": key, "got": got, "need": n})
            for key in ("abilities", "weaknesses"):
                items = submitted.get(key) or []
                if not isinstance(items, (list, tuple)) or len([x for x in items if str(x).strip()]) < 1:
                    missing.append({"id": key, "got": 0, "need": 1})
        if k == "faction":
            if field_cn(submitted.get("ideology")) < 200:
                missing.append({"id": "ideology", "got": field_cn(submitted.get("ideology")), "need": 200})
            if field_cn(submitted.get("public_face")) < 80:
                missing.append({"id": "public_face", "got": field_cn(submitted.get("public_face")), "need": 80})
            struct_cn = max(field_cn(submitted.get("structure")), field_cn(submitted.get("recruitment")))
            if struct_cn < 80:
                missing.append({"id": "structure", "got": struct_cn, "need": 80})
            if _is_empty_codex_value(submitted.get("leader")):
                missing.append({"id": "leader", "got": 0, "need": 1})
            goals = submitted.get("goals") or []
            has_target = False
            if isinstance(goals, list):
                for g in goals:
                    if isinstance(g, dict) and str(g.get("target") or "").strip():
                        has_target = True
                    elif str(g or "").strip():
                        has_target = True
            if not has_target:
                missing.append({"id": "goals", "got": 0, "need": 1})
        if k == "item":
            if field_cn(submitted.get("description")) < 400:
                missing.append({"id": "description", "got": field_cn(submitted.get("description")), "need": 400})
            if _is_empty_codex_value(submitted.get("current_owner")):
                missing.append({"id": "current_owner", "got": 0, "need": 1})
            props = submitted.get("special_properties") or []
            if not isinstance(props, (list, tuple)) or not [x for x in props if str(x).strip()]:
                missing.append({"id": "special_properties", "got": 0, "need": 1})
        if k == "world_rule":
            if field_cn(submitted.get("cost")) < 80:
                missing.append({"id": "cost", "got": field_cn(submitted.get("cost")), "need": 80})
            for key in ("limitations", "exceptions", "capabilities"):
                items = submitted.get(key) or []
                if not isinstance(items, (list, tuple)) or not [x for x in items if str(x).strip()]:
                    missing.append({"id": key, "got": 0, "need": 1})
            if _is_empty_codex_value(submitted.get("source")):
                missing.append({"id": "source", "got": 0, "need": 1})
        if k == "motif":
            if field_cn(submitted.get("theme")) < 40:
                missing.append({"id": "theme", "got": field_cn(submitted.get("theme")), "need": 40})
            echoes = submitted.get("echo_terms") or submitted.get("echoes") or []
            n = 0
            if isinstance(echoes, (list, tuple)):
                n = len([x for x in echoes if len(str(x).strip()) >= 2])
            elif isinstance(echoes, str):
                n = len([x for x in re.split(r"[,，、;；]", echoes) if len(x.strip()) >= 2])
            if n < 3:
                missing.append({"id": "echo_terms", "got": n, "need": 3})
            if field_cn(submitted.get("unfolding")) < 80:
                missing.append({"id": "unfolding", "got": field_cn(submitted.get("unfolding")), "need": 80})
        if k == "voice":
            if field_cn(submitted.get("style_summary")) < 80:
                missing.append({"id": "style_summary", "got": field_cn(submitted.get("style_summary")), "need": 80})
            sections = 0
            for key in ("catchphrases", "tone_rules", "internal_monologue_style", "sentence_patterns"):
                if not _is_empty_codex_value(submitted.get(key)):
                    sections += 1
            if sections < 2:
                missing.append({"id": "voice_sections", "got": sections, "need": 2})
    else:
        for key, val in submitted.items():
            if _is_empty_codex_value(val):
                continue
            if key == "private_operation":
                missing.append({
                    "id": "private_operation",
                    "got": 1,
                    "need": 0,
                    "hint": "拆到 artifact_operation / external_manipulation / acceleration_methods",
                })
                continue
            floor = int(floors.get(key) or 0)
            if floor and field_cn(val) < floor:
                missing.append({"id": key, "got": field_cn(val), "need": floor})
            min_n = int(mins.get(key) or 0)
            if min_n:
                items = val if isinstance(val, (list, tuple)) else []
                got = len([x for x in items if str(x).strip()])
                if key == "special_properties" and any(str(x).strip() in _SENTINEL_NONE for x in items):
                    continue
                if got < min_n:
                    missing.append({"id": key, "got": got, "need": min_n})
    if not missing:
        return None
    bits = [f"{m['id']} {m['got']}<{m['need']}" for m in missing]
    return {
        "code": "codex_thin_persist",
        "message": "不能把薄设定存成已有档案：" + "；".join(bits),
        "missing": missing,
        "kind": k,
        "mode": mode,
        "role": "codex_substrate",
    }


def codex_l1_error(kind: str, submitted: dict | None) -> dict[str, Any] | None:
    hit = persist_codex_fields_blocked(kind, submitted, mode="incremental")
    if not hit:
        return None
    return {
        "status": "error",
        "code": hit["code"],
        "error": hit["message"],
        "missing": hit.get("missing"),
        "kind": kind,
    }


def evaluate_codex_ready(kind: str, row: dict | None) -> dict[str, Any]:
    """合并后整行。stub / thin / ready。只决定 skip 与灯，不挡 L1。"""
    k = (kind or "").strip().lower()
    if k == "voice_profile":
        k = "voice"
    src = dict(row or {})
    thick_keys = set((CODEX_FIELD_FLOOR.get(k) or {})) | set((CODEX_MIN_ITEMS.get(k) or {}))
    if k == "character":
        thick_keys |= {"abilities", "weaknesses", "personality_detail"}
    has_thick = False
    for key in thick_keys:
        if not _is_empty_codex_value(src.get(key)):
            has_thick = True
            break
    if k == "term" and str(src.get("definition") or "").strip():
        has_thick = True
    blocked = persist_codex_fields_blocked(k, src, mode="pack")
    if not has_thick:
        status = "stub"
        ok = False
    elif blocked:
        status = "thin"
        ok = False
    else:
        status = "ready"
        ok = True
    return {
        "ok": ok,
        "status": status,
        "kind": k,
        "pack_cn": pack_cn(k, src),
        "blocked": blocked,
        "role": "codex_ready",
    }


def attach_codex_ready(
    kind: str,
    row: dict | None,
    *,
    evaluate_from: dict | None = None,
) -> dict[str, Any]:
    """给档案响应挂 ``codex_ready``。``evaluate_from`` 用于掩码前的真值。"""
    src = dict(row or {})
    ev = evaluate_codex_ready(kind, evaluate_from if evaluate_from is not None else src)
    src["codex_ready"] = {
        "ok": bool(ev.get("ok")),
        "status": ev.get("status"),
        "pack_cn": int(ev.get("pack_cn") or 0),
    }
    return src


def codex_ready_badge(kind: str, row: dict | None) -> dict[str, Any]:
    ev = evaluate_codex_ready(kind, row)
    status = str(ev.get("status") or "stub")
    labels = {"stub": "空壳", "thin": "偏薄", "ready": "已齐"}
    tones = {"stub": "faint", "thin": "warn", "ready": "ok"}
    return {
        "kind": "codex_ready",
        "value": labels.get(status, status),
        "tone": tones.get(status, "faint"),
        "status": status,
    }


def iceberg_http_detail(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": "iceberg_thin",
        "message": report.get("message") or "冰山未厚",
        "iceberg": report,
        "hint": "补情节原子（选择/代价/线），禁止烟/锅/巷凑句；或 danger_draft / skip_iceberg 旁路（会写成口号戏）。",
    }

"""全类型设定抽取：默认「标记 + 模型」；启发式仅 hybrid/heuristic 模式。

模式（SCRIBE3_CANON_EXTRACT_MODE / mode 参数）:
  llm        — 标记 + LLM（默认；无 complete_fn 时仅标记，不跑启发式）
  hybrid     — 标记 + LLM + 启发式（旧行为，噪声多）
  heuristic  — 标记 + 启发式（离线/无模型）
  marker     — 仅【设定】标记
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import json
import logging
import os
import re
from typing import Any, Callable

from scribe3.canon_loop import (
    MODULES,
    CanonClaim,
    item_requires_human_approval,
    parse_marker_claims,
)

_log = logging.getLogger("scribe3.canon_extract")

# 扩展标记：【规则 L1|world_rule|债契三夜|cost|折声或折命|高】...
_NAME_RE = re.compile(r"[\u4e00-\u9fff]{2,4}")

_VALID_MODES = frozenset({"llm", "hybrid", "heuristic", "marker"})


def resolve_extract_mode(mode: str | None = None) -> str:
    raw = (mode or get_flag("SCRIBE3_CANON_EXTRACT_MODE") or "llm").strip().lower()
    if raw in ("model", "ai"):
        raw = "llm"
    if raw not in _VALID_MODES:
        _log.warning("unknown extract mode %r, fallback llm", raw)
        return "llm"
    return raw


def extract_claims_from_prose(
    prose: str,
    *,
    known_character_names: list[str] | None = None,
    complete_fn: Callable[[str], str] | None = None,
    mode: str | None = None,
    canon_snapshot: dict[str, Any] | None = None,
) -> list[CanonClaim]:
    """从正文抽全类型主张。

    默认 mode=llm：1) 标记 2) LLM（有 complete_fn）。**不跑**规则启发式。
    hybrid 才叠加启发式（兼容旧测与回滚）。
    """
    text = prose or ""
    claims: list[CanonClaim] = []
    seen: set[tuple] = set()
    m = resolve_extract_mode(mode)

    def _add(c: CanonClaim) -> None:
        key = (c.module, c.target, c.field, str(c.after)[:40])
        if key in seen:
            return
        seen.add(key)
        claims.append(c)

    for c in parse_marker_claims(text):
        _add(c)

    if m in ("llm", "hybrid") and complete_fn:
        try:
            for c in _llm_extract(
                text, complete_fn,
                known_character_names=known_character_names,
                canon_snapshot=canon_snapshot,
            ):
                _add(c)
        except Exception as e:
            _log.warning("canon extract llm fail: %s", e)
            try:
                from scribe3.alerts import emit_alert
                emit_alert("ingest_extract_fail", f"抽取失败: {type(e).__name__}")
            except Exception:
                pass
            try:
                from scribe3.extract_retry import queue_extract_retry
                queue_extract_retry(text, reason=type(e).__name__)
            except Exception:
                pass
    elif m in ("llm", "hybrid") and not complete_fn:
        _log.info("canon extract mode=%s but no complete_fn; markers only (+heur if hybrid)", m)

    # 启发式：仅 hybrid / heuristic；默认 llm 关闭（根治推门/一会噪声）
    if m not in ("hybrid", "heuristic"):
        return claims

    known = set(known_character_names or [])
    # 启发式人名：仅「叫作/名为/名叫」，禁止裸「叫…」(「叫我来看」≠人名)
    _bad_person = re.compile(
        r"^(我|你|他|她|它|这|那|人|谁|什么|怎|哪)"
        r"|来看|写上|替了|莫应|看这|看那|起来|过去|过来|下去"
    )
    for m in re.finditer(
        r"(?:叫作|名为|名叫)([\u4e00-\u9fff]{2,4})",
        text,
    ):
        name = m.group(1)
        if name in known or _bad_person.search(name):
            continue
        if name[-1] in "来去上下过了着的地得":
            continue
        # 组织后缀更像势力，不做人名
        if name.endswith(("门", "帮", "教", "宗", "盟", "阁", "堂", "派", "府")):
            continue
        _add(CanonClaim(
            layer="L1",
            op="add",
            module="character",
            target=f"role:{name}",
            after={"name": name},
            field=None,
            evidence=m.group(0),
            risk="med",
            requires_approval=True,
            confidence=0.4,
        ))

    # 世界规则弱模式：「按…规矩/法则/戒律」「…铁律/禁令」
    for m in re.finditer(
        r"(?:按|依|循)([\u4e00-\u9fff]{2,12})(?:之)?(?:规矩|法则|戒律|铁律|禁令|规矩办)",
        text,
    ):
        name = m.group(1)
        _add(CanonClaim(
            layer="L1", op="add", module="world_rule",
            target=name, after={"name": name, "note": m.group(0)},
            evidence=m.group(0), risk="high", requires_approval=True,
            confidence=0.55,
        ))
    for m in re.finditer(
        r"([\u4e00-\u9fff]{2,10})(?:是|为)(?:一条|这)?(?:铁律|禁令|戒律)",
        text,
    ):
        name = m.group(1)
        _add(CanonClaim(
            layer="L1", op="add", module="world_rule",
            target=name, after={"name": name, "note": m.group(0)},
            evidence=m.group(0), risk="high", requires_approval=True,
            confidence=0.55,
        ))

    # 势力：组织型后缀；排除门/帮日常义。故意不匹配「…会」(一会/看一会)
    for m in re.finditer(
        # 后缀后允许 的/是/在/标点，避免「灯火门在镇口」整段吃掉；仍拒「…门板」连写长词
        r"(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{2,4}(?:门|帮|教|宗|盟|阁|堂|派|府|司|卫|营))"
        r"(?=的|是|在|与|和|中|里|外|内|、|，|。|！|？|；|：|\s|$|[^\u4e00-\u9fff])",
        text,
    ):
        name = m.group(1)
        if not _looks_like_faction_name(name, text, m.start()):
            continue
        _add(CanonClaim(
            layer="L1", op="add", module="faction",
            target=name, after={"name": name},
            evidence=m.group(0)[:80], risk="med", requires_approval=True,
            confidence=0.4,
        ))

    # 物件：短专名
    for m in re.finditer(
        r"(?:手持|佩戴|取出|掏出|亮出|递过)([\u4e00-\u9fff]{2,6})",
        text,
    ):
        name = m.group(1)
        if name[-1] in "了着的地得过":
            continue
        _add(CanonClaim(
            layer="L1", op="add", module="item",
            target=name, after={"name": name, "description": m.group(0)},
            evidence=m.group(0), risk="med", requires_approval=True,
            confidence=0.4,
        ))

    # 术语
    for m in re.finditer(
        r"(?:所谓|名曰)([\u4e00-\u9fff]{2,8})",
        text,
    ):
        name = m.group(1)
        _add(CanonClaim(
            layer="L1", op="add", module="term",
            target=name, after={"name": name, "definition": m.group(0)},
            evidence=m.group(0), risk="med", requires_approval=True,
            confidence=0.45,
        ))

    # 伏笔：收紧长度
    for m in re.finditer(
        r"(?:他日|日后|总有一天|终有一日)([^。！？\n]{4,24})",
        text,
    ):
        frag = m.group(0).strip()
        if len(frag) > 36:
            continue
        _add(CanonClaim(
            layer="L1", op="plant", module="promise",
            target=frag[:40], after=frag[:80],
            evidence=frag[:120], risk="med", requires_approval=True,
            confidence=0.4,
        ))

    return claims


_ORG_SUFFIX = ("门", "帮", "教", "宗", "盟", "阁", "堂", "派", "府", "司", "卫", "营")
_DOOR_VERB_BEFORE = re.compile(
    r"(推|开|关|掩|闩|出|入|进|到|从|站在|靠在|半掩|角|客店|房|屋|窗|巷|街).{0,2}$"
)
_FUNC_START = re.compile(
    r"^(是|会|的|了|在|有|和|与|把|被|将|从|向|对|给|让|到|又|也|都|还|就|才|却|"
    r"已|未|不|没|他|她|我|你|这|那|其|此|该|小|大|一|两|几|好|等|看|躺|走|推|开|朝|名|为)"
)


def _looks_like_faction_name(name: str, full: str, start: int) -> bool:
    """组织名质检：拒门板/鞋帮/代词起头残片。"""
    n = (name or "").strip()
    if len(n) < 2 or len(n) > 6:
        return False
    if not n.endswith(_ORG_SUFFIX):
        return False
    if n.endswith("会"):
        return False
    if _FUNC_START.search(n):
        return False
    if "替" in n and "门" in n:
        return False
    if n in ("高门", "低门", "正门", "侧门", "山门", "家门", "师门", "正教", "旁门"):
        return False
    prefix = full[max(0, start - 4):start]
    if n.endswith("门"):
        if _DOOR_VERB_BEFORE.search(prefix):
            return False
        if any(v in n for v in ("推", "开", "关", "掩", "闩", "站", "走", "到", "从", "的")):
            return False
        if len(n) == 2 and n[0] in "推开关出入到从":
            return False
    if n.endswith("帮") and ("鞋" in n or n.endswith("船帮")):
        return False
    if n.endswith("教") and len(n) <= 2:
        return False
    if len(n) == 2 and not n.endswith(("宗", "盟", "派", "府", "阁")):
        return False
    return True




def claims_from_settings_json(data: dict[str, Any] | None) -> list[CanonClaim]:
    """把模型 settings 块（或旧扁平设定 JSON）转为 CanonClaim 列表。"""
    if not isinstance(data, dict):
        return []
    out: list[CanonClaim] = []
    for it in data.get("entities") or []:
        if not isinstance(it, dict):
            continue
        mod = (it.get("module") or "character").strip()
        if mod not in MODULES:
            continue
        name = (it.get("name") or "").strip()
        if not name:
            continue
        fields = it.get("fields") if isinstance(it.get("fields"), dict) else {}
        op = (it.get("op") or ("add" if not fields else "patch")).strip()
        if fields:
            for fk, fv in fields.items():
                out.append(CanonClaim(
                    layer="L1", op="patch" if op != "add" else "add", module=mod,
                    target=f"role:{name}" if mod == "character" else name,
                    field=fk, after=fv,
                    evidence=str(it.get("evidence") or "")[:200],
                    risk="med",
                    requires_approval=item_requires_human_approval("L1", mod),
                    confidence=float(it.get("confidence") or 0.75),
                ))
        else:
            out.append(CanonClaim(
                layer="L1", op=op, module=mod,
                target=f"role:{name}" if mod == "character" else name,
                after={"name": name} if mod == "character" else name,
                evidence=str(it.get("evidence") or "")[:200],
                risk="med",
                confidence=float(it.get("confidence") or 0.75),
            ))
    for it in data.get("world_rules") or []:
        if not isinstance(it, dict) or not it.get("name"):
            continue
        fields = it.get("fields") if isinstance(it.get("fields"), dict) else {}
        if fields:
            for fk, fv in fields.items():
                out.append(CanonClaim(
                    layer="L1", op=it.get("op") or "patch", module="world_rule",
                    target=str(it["name"]), field=fk, after=fv,
                    evidence=str(it.get("evidence") or "")[:200], risk="high",
                ))
        else:
            out.append(CanonClaim(
                layer="L1", op=it.get("op") or "add", module="world_rule",
                target=str(it["name"]), after=it.get("fields") or {"note": it.get("name")},
                evidence=str(it.get("evidence") or "")[:200], risk="high",
            ))
    for it in data.get("relations") or []:
        if not isinstance(it, dict):
            continue
        a, b = it.get("a"), it.get("b")
        if not a or not b:
            continue
        out.append(CanonClaim(
            layer="L1", op="add", module="relation",
            target=f"{a}|{b}", field=it.get("relation") or "关联",
            after={"src": a, "dst": b, "relation": it.get("relation") or "关联"},
            evidence=str(it.get("evidence") or "")[:200], risk="med",
        ))
    for it in data.get("facts") or []:
        if not isinstance(it, dict):
            continue
        out.append(CanonClaim(
            layer="L1", op="add", module="fact",
            target=str(it.get("entity") or ""),
            field=str(it.get("attribute") or "note"),
            after={"entity": it.get("entity"), "attribute": it.get("attribute"),
                   "value": it.get("value")},
            evidence=str(it.get("evidence") or "")[:200], risk="med",
        ))
    for it in data.get("knowledge") or []:
        if not isinstance(it, dict):
            continue
        out.append(CanonClaim(
            layer="L2", op="add", module="knowledge",
            target=str(it.get("knower") or ""),
            field=str(it.get("proposition") or it.get("proposition_hint") or ""),
            after=it.get("via") or "saw",
            evidence=str(it.get("evidence") or "")[:200], risk="low",
            requires_approval=False,
        ))
    for it in data.get("items") or []:
        if isinstance(it, dict) and it.get("name"):
            out.append(CanonClaim(
                layer="L1", op=it.get("op") or "add", module="item",
                target=str(it["name"]),
                after=it.get("fields") or {"description": it.get("description") or it["name"]},
                evidence=str(it.get("evidence") or "")[:200], risk="med",
            ))
    for it in data.get("terms") or []:
        if isinstance(it, dict) and it.get("name"):
            out.append(CanonClaim(
                layer="L1", op=it.get("op") or "add", module="term",
                target=str(it["name"]),
                after=it.get("fields") or {"definition": it.get("definition") or it["name"]},
                evidence=str(it.get("evidence") or "")[:200], risk="med",
            ))
    for it in data.get("factions") or []:
        if isinstance(it, dict) and it.get("name"):
            out.append(CanonClaim(
                layer="L1", op=it.get("op") or "add", module="faction",
                target=str(it["name"]),
                after=it.get("fields") or {"name": it["name"]},
                evidence=str(it.get("evidence") or "")[:200], risk="med",
            ))
    for it in data.get("promises") or []:
        if isinstance(it, dict) and (it.get("text") or it.get("name")):
            out.append(CanonClaim(
                layer="L1", op=it.get("op") or "plant", module="promise",
                target=str(it.get("text") or it.get("name")),
                after=it.get("text") or it.get("name"),
                evidence=str(it.get("evidence") or "")[:200], risk="med",
            ))
    for it in data.get("motifs") or []:
        if not isinstance(it, dict) or not it.get("name"):
            continue
        name = str(it["name"]).strip()
        out.append(CanonClaim(
            layer="L1", op=it.get("op") or "add", module="motif",
            target=name,
            after={
                "name": name,
                "theme": it.get("theme") or "",
                "echoes": it.get("echoes") or "",
            },
            evidence=str(it.get("evidence") or "")[:200],
            risk="med",
            confidence=float(it.get("confidence") or 0.7),
        ))
    return out

def _llm_extract(
    prose: str,
    complete_fn: Callable[[str], str],
    *,
    known_character_names: list[str] | None = None,
    canon_snapshot: dict[str, Any] | None = None,
) -> list[CanonClaim]:
    known = list(known_character_names or [])
    snap = canon_snapshot or {}
    wr = list((snap.get("world_rules") or {}).keys())[:20]
    bible = ""
    if known:
        bible += "已立角色（勿重复新建，可 patch 字段）: " + "、".join(known[:40]) + "\n"
    if wr:
        bible += "已立世界规则: " + "、".join(str(x) for x in wr) + "\n"
    schema_line = ""
    try:
        from scribe3.codex_schema import fields_for
        bits = []
        for kind in ("character", "faction", "item", "term", "world_rule"):
            keys = [f.key for f in fields_for(kind)[:12]]
            if keys:
                bits.append(f"{kind}: {', '.join(keys)}")
        if bits:
            schema_line = "schema 字段（fields 只能用这些键）: " + "；".join(bits) + "\n"
    except Exception:
        schema_line = ""
    prompt = (
        "你是长篇写作系统的设定增量抽取器。只根据【正文】相对【已有设定】抽「需要作者确认」的增量。\n"
        "铁律:\n"
        "1) 禁止编造正文没有的专名/规则；每条必须有 evidence 原文短引。\n"
        "2) 已立角色/规则不要重复 add；仅当正文明确新信息时用 op=patch + fields。\n"
        "3) 不要把门/推门/一会/口语残片当成势力；组织须像专名（如「高门代还」「灯火门」）。\n"
        "4) 人名须是人物称呼，禁止「叫我来看」类动词短语。\n"
        "5) 宁缺毋滥：不确定就省略。\n"
        f"{schema_line}"
        "输出一行 JSON，键可含 entities/relations/world_rules/factions/items/terms/"
        "promises/facts/knowledge/motifs（缺省用空数组）。\n"
        "entities: {module,op,name,fields,evidence,confidence} module 仅 character|faction|item|term；"
        "confidence 0~1。\n"
        "world_rules: {op,name,fields,evidence,confidence}\n"
        "relations: {a,b,relation,evidence}\n"
        "facts: {entity,attribute,value,evidence}\n"
        "knowledge: {knower,proposition,via,evidence}\n"
        "promises: {op,text,evidence}\n"
        "motifs: {op,name,theme,echoes,evidence} 仅当正文强烈呈现可复用意象且书中尚无时。\n"
        f"【已有设定】\n{bible or '(空库)'}\n"
        f"【正文】\n{prose[:8000]}\n"
    )
    try:
        reply = complete_fn(prompt) or ""
    except Exception as e:
        _log.warning("llm extract fail: %s", e)
        return []
    try:
        m = re.search(r"\{.*\}", reply, re.S)
        if not m:
            return []
        data = json.loads(m.group(0))
    except Exception as e:
        _log.warning("llm extract parse: %s", e)
        return []
    # 兼容统一章后包 {settings:{...}} 与旧扁平设定 JSON
    if isinstance(data.get("settings"), dict):
        data = data["settings"]
    return claims_from_settings_json(data)

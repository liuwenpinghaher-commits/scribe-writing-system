"""全类型设定抽取：标记 + 启发式 + 可选 LLM，输出 CanonClaim 列表。"""
from __future__ import annotations

import json
import logging
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
# 复用 parse_marker_claims；补充启发式

_NAME_RE = re.compile(r"[\u4e00-\u9fff]{2,4}")


def extract_claims_from_prose(
    prose: str,
    *,
    known_character_names: list[str] | None = None,
    complete_fn: Callable[[str], str] | None = None,
) -> list[CanonClaim]:
    """从正文抽全类型主张。

    1) 确定性标记（权威）
    2) 可选 LLM JSON（complete_fn）
    3) 启发式：库外中文人名 → character/add
    """
    text = prose or ""
    claims: list[CanonClaim] = []
    seen: set[tuple] = set()

    def _add(c: CanonClaim) -> None:
        key = (c.module, c.target, c.field, str(c.after)[:40])
        if key in seen:
            return
        seen.add(key)
        claims.append(c)

    for c in parse_marker_claims(text):
        _add(c)

    if complete_fn:
        for c in _llm_extract(text, complete_fn):
            _add(c)

    known = set(known_character_names or [])
    # 启发式：正文中的「他/她叫X」弱模式 + 已知名以外的专名（谨慎）
    for m in re.finditer(
        r"(?:叫作?|名为|名叫)([\u4e00-\u9fff]{2,4})",
        text,
    ):
        name = m.group(1)
        if name in known:
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
        ))

    # 势力：专名须 2–6 字并以门/帮/会/教/宗/盟/阁/堂结尾；拒绝语法残片
    _bad_faction = re.compile(
        r"^(是|会|的|了|在|有|和|与|把|被|将|从|向|对|给|让|到|又|也|都|还|就|才|却)"
        r"|替高门|原本是|是会"
    )
    for m in re.finditer(
        r"(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{1,5}(?:门|帮|教|宗|盟|阁|堂))(?![\u4e00-\u9fff])",
        text,
    ):
        name = m.group(1)
        if len(name) < 2 or len(name) > 6:
            continue
        if _bad_faction.search(name):
            continue
        # 「会」单独后缀易误伤，要求至少 3 字（如 帮会 仍短则跳过纯「X会」口语）
        if name.endswith("会") and len(name) < 3:
            continue
        _add(CanonClaim(
            layer="L1", op="add", module="faction",
            target=name, after={"name": name},
            evidence=m.group(0)[:80], risk="med", requires_approval=True,
            confidence=0.45,
        ))

    # 物件：「手持/佩戴/取出…」
    for m in re.finditer(
        r"(?:手持|佩戴|取出|掏出|亮出|递过)([\u4e00-\u9fff]{2,8})",
        text,
    ):
        name = m.group(1)
        _add(CanonClaim(
            layer="L1", op="add", module="item",
            target=name, after={"name": name, "description": m.group(0)},
            evidence=m.group(0), risk="med", requires_approval=True,
        ))

    # 术语：「所谓…」「…一说」
    for m in re.finditer(
        r"(?:所谓|名曰)([\u4e00-\u9fff]{2,10})",
        text,
    ):
        name = m.group(1)
        _add(CanonClaim(
            layer="L1", op="add", module="term",
            target=name, after={"name": name, "definition": m.group(0)},
            evidence=m.group(0), risk="med", requires_approval=True,
        ))

    # 伏笔：「他日/日后/总有一天…」
    for m in re.finditer(
        r"(?:他日|日后|总有一天|终有一日)([^。！？\n]{4,40})",
        text,
    ):
        _add(CanonClaim(
            layer="L1", op="plant", module="promise",
            target=m.group(0)[:40], after=m.group(0)[:80],
            evidence=m.group(0)[:120], risk="med", requires_approval=True,
        ))

    return claims


def _llm_extract(prose: str, complete_fn: Callable[[str], str]) -> list[CanonClaim]:
    prompt = (
        "你是小说设定抽取器。只根据正文抽取相对「设定库」的增量，不要编造正文没有的内容。\n"
        "输出一行 JSON，键可含 entities/relations/world_rules/factions/items/terms/"
        "promises/facts/knowledge（缺省用空数组）。\n"
        "entities 元素: {module,op,name,fields,evidence,confidence} module 仅 "
        "character|faction|item|term。\n"
        "world_rules: {op,name,fields,evidence}\n"
        "relations: {a,b,relation,evidence}\n"
        "facts: {entity,attribute,value,evidence}\n"
        "knowledge: {knower,proposition,via,evidence}\n"
        "promises: {op,text,evidence}\n"
        f"【正文】\n{prose[:6000]}\n"
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
                ))
        else:
            out.append(CanonClaim(
                layer="L1", op=op, module=mod,
                target=f"role:{name}" if mod == "character" else name,
                after={"name": name} if mod == "character" else name,
                evidence=str(it.get("evidence") or "")[:200],
                risk="med",
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
    return out

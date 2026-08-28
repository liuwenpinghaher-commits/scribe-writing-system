"""设定库生成链：按 kind 合同写厚。必须 LLM。不扩 stage_generate。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Mapping

from scribe3.iceberg import (
    CODEX_PACK_FLOOR,
    cn_len,
    evaluate_codex_ready,
    persist_codex_fields_blocked,
)

LlmFn = Callable[..., str]
_FENCE = re.compile(r"^```(?:\w+)?\s*|\s*```$", re.MULTILINE)
_HEADING = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*|【)?(?P<h>是什么|不是什么|本书用法|边界|"
    r"性格|表层目标|深层需求|恐惧|内在冲突|能力|弱点|外貌|前史|"
    r"意识形态|公开面目|行为约束|领袖|阶段目标|"
    r"描述|持有者|特殊属性|状态|"
    r"代价|限制|例外|赋予能力|作用域|源头|"
    r"主题|回声|展开|声音摘要)\s*(?:】)?\s*[:：]?",
    re.MULTILINE,
)

IMPLEMENTED = frozenset({
    "character", "faction", "item", "term", "world_rule", "motif", "voice",
})
MAX_TOKENS = {
    "character": 4096, "faction": 4096, "item": 4096, "term": 4096,
    "world_rule": 4096, "motif": 1024, "voice": 1024,
}

_TERM_HEADS = ("是什么", "不是什么", "本书用法", "边界")
_CHAR_HEADS = {
    "性格": "personality_detail", "表层目标": "surface_goal", "深层需求": "deep_need",
    "恐惧": "fear", "内在冲突": "internal_conflict", "能力": "abilities",
    "弱点": "weaknesses", "外貌": "appearance", "前史": "backstory",
}
_ITEM_HEADS = {
    "描述": "description", "持有者": "current_owner",
    "特殊属性": "special_properties", "状态": "symbolic_state",
}
_RULE_HEADS = {
    "代价": "cost", "限制": "limitations", "例外": "exceptions",
    "赋予能力": "capabilities", "作用域": "scope", "源头": "source",
}


def _call_llm(llm_fn: LlmFn | None, prompt: str, max_tokens: int) -> str:
    if llm_fn is None or not callable(llm_fn):
        raise ValueError("codex_generate 必须提供 llm_fn，禁止模板/切句回退")
    try:
        raw = llm_fn(prompt, max_tokens)
    except TypeError:
        raw = llm_fn(prompt)
    return str(raw or "").strip()


def _strip_fence(text: str) -> str:
    return _FENCE.sub("", text or "").strip()


def _split_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in re.split(r"[,，、;；\n]", str(value or "")) if x.strip()]


def _extract_slots(text: str) -> dict[str, str]:
    src = text or ""
    marks = list(_HEADING.finditer(src))
    out: dict[str, str] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(src)
        out[m.group("h")] = src[m.end():end].strip()
    return out


def parse_codex_payload(kind: str, raw: str) -> dict[str, Any]:
    text = _strip_fence(raw)
    fields: dict[str, Any] = {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            fields = dict(obj)
    except Exception:
        fields = {}
    if not fields:
        slots = _extract_slots(text)
        if kind == "term":
            if any(h in slots for h in _TERM_HEADS):
                fields["definition"] = "\n".join(
                    f"{h}：{slots.get(h, '').strip()}" for h in _TERM_HEADS if slots.get(h)
                )
            elif text:
                fields["definition"] = text
        elif kind == "character":
            for zh, key in _CHAR_HEADS.items():
                if not slots.get(zh):
                    continue
                if key in ("abilities", "weaknesses"):
                    fields[key] = _split_list(slots[zh])
                else:
                    fields[key] = slots[zh]
        elif kind == "item":
            for zh, key in _ITEM_HEADS.items():
                if not slots.get(zh):
                    continue
                fields[key] = _split_list(slots[zh]) if key == "special_properties" else slots[zh]
        elif kind == "world_rule":
            for zh, key in _RULE_HEADS.items():
                if not slots.get(zh):
                    continue
                fields[key] = (
                    _split_list(slots[zh])
                    if key in ("limitations", "exceptions", "capabilities")
                    else slots[zh]
                )
        elif kind == "faction":
            mapping = {
                "意识形态": "ideology", "公开面目": "public_face",
                "行为约束": "recruitment", "领袖": "leader",
            }
            for zh, key in mapping.items():
                if slots.get(zh):
                    fields[key] = slots[zh]
            if slots.get("阶段目标"):
                fields["goals"] = [{"target": t} for t in _split_list(slots["阶段目标"])]
        elif kind == "motif":
            if slots.get("主题"):
                fields["theme"] = slots["主题"]
            if slots.get("展开"):
                fields["unfolding"] = slots["展开"]
            if slots.get("回声"):
                fields["echo_terms"] = _split_list(slots["回声"])
        elif kind == "voice":
            if slots.get("声音摘要"):
                fields["style_summary"] = slots["声音摘要"]
    if kind == "term":
        dfn = fields.get("definition")
        if isinstance(dfn, dict):
            bits = []
            for h in _TERM_HEADS:
                val = dfn.get(h)
                if val:
                    bits.append(f"{h}：{str(val).strip()}")
            fields["definition"] = "\n".join(bits) if bits else json.dumps(dfn, ensure_ascii=False)
        elif dfn is not None and not isinstance(dfn, str):
            fields["definition"] = str(dfn)
        if not str(fields.get("definition") or "").strip() and any(
            h in fields for h in _TERM_HEADS
        ):
            fields["definition"] = "\n".join(
                f"{h}：{str(fields.get(h) or '').strip()}"
                for h in _TERM_HEADS if fields.get(h)
            )
        # 缺四格不得由解析器代写口号小标题；L2 pack 闸应判 thin。
    for arr_key in (
        "abilities", "weaknesses", "special_properties",
        "limitations", "exceptions", "capabilities", "echo_terms", "aliases",
    ):
        if arr_key in fields:
            fields[arr_key] = _split_list(fields[arr_key])
    return fields


def _split_bags(kind: str, fields: dict) -> tuple[dict, dict, dict]:
    from scribe3.codex_schema import chief_only_keys, secret_capable_keys
    chief = set(chief_only_keys(kind) or ()) if kind in (
        "character", "faction", "item", "term", "world_rule",
    ) else set()
    secret_keys = set(secret_capable_keys(kind) or ()) if kind in (
        "character", "faction", "item", "term", "world_rule",
    ) else set()
    public, secret, only = {}, {}, {}
    for key, val in (fields or {}).items():
        if key in chief:
            only[key] = val
        elif key in secret_keys and (
            fields.get(f"{key}_secret") or (kind == "character" and key == "backstory" and fields.get("backstory_secret"))
        ):
            secret[key] = val
        elif key.endswith("_secret"):
            if fields.get(key):
                secret[key] = val
        else:
            public[key] = val
    public.pop("secret_agenda", None)
    return public, secret, only


def _schema_field_ask(kind: str) -> str:
    """CDX-03：把 schema 字段键交给模型，新增字段才会被写出来。"""
    try:
        from scribe3.codex_schema import fields_for
        keys = [f.key for f in fields_for(kind) if not f.deprecated]
    except Exception:
        keys = []
    if not keys:
        return ""
    return "JSON 键（按这本书的登记表）：" + ", ".join(keys) + "。该有的写上，没有的不要编。\n"


def spec_ask(kind: str) -> str:
    schema_line = _schema_field_ask(kind)
    if kind == "term":
        return (
            "写这个词在这本书里怎么收账。不是词典。"
            "说清：它是什么、它不是什么、它怎样让人变贵、它的边界。"
            "用小标题或 JSON 交卷，好让机器读懂。\n"
            + schema_line
        )
    if kind == "character":
        return (
            "写这个人在这本书里的责任。不是填表。"
            "他要什么、他会让主角付出什么、他怕什么、他不知道什么。"
            "性格、前史只为说清这四件事。"
            "用 JSON 交卷。不要只回一个名字。\n"
            + schema_line
        )
    if kind == "faction":
        return (
            "写这股势力在这本书里要主角付出什么。不是机构简介。"
            "他们公开要什么、私下要什么、谁来收账。"
            "用 JSON 交卷。\n"
            + schema_line
        )
    if kind == "item":
        return (
            "写这件东西让谁变贵。不是器物说明书。"
            "谁拿着、碰它要付什么、它此刻处于什么状态。"
            "用 JSON 交卷。\n"
            + schema_line
        )
    if kind == "world_rule":
        return (
            "写这条规矩谁打破谁付钱。不是免费超能力。"
            "代价是什么、谁例外、它管到哪里。"
            "用 JSON 交卷。\n"
            + schema_line
        )
    if kind == "motif":
        return (
            "写这个母题在书里怎么一次次回来咬人。不是主题作文。"
            "它回声是什么、它怎样展开。"
            "用 JSON 交卷。\n"
            + schema_line
        )
    if kind == "voice":
        return (
            "写这个人说话时让人听得出是他。不是形容词堆砌。"
            "用 JSON 交卷。\n"
            + schema_line
        )
    return schema_line


_CHAR_SLOT_LABEL = {
    "surface_goal": "他要什么",
    "deep_need": "他要什么",
    "fear": "他让人付出什么",
    "internal_conflict": "他让人付出什么",
    "personality_detail": "性格（只为说清他要什么、他让人付出什么）",
    "abilities": "他靠什么收账",
    "weaknesses": "他缺什么会付账",
    "appearance": "外貌",
    "backstory": "前史",
}
_TERM_PARTS = ("是什么", "不是什么", "本书用法", "边界")


def _codex_slot_label(kind: str, slot: str) -> str:
    if kind == "character":
        return _CHAR_SLOT_LABEL.get(slot, slot)
    if kind == "term" and str(slot).startswith("part:"):
        return str(slot).split(":", 1)[1]
    if kind == "faction":
        return {
            "ideology": "他们私下要什么",
            "public_face": "他们公开要什么",
            "structure": "谁来收账",
            "recruitment": "谁来收账",
            "leader": "谁来收账",
            "goals": "他们要主角付出什么",
        }.get(slot, slot)
    if kind == "item":
        return {
            "description": "这件东西让谁变贵",
            "current_owner": "谁拿着",
            "special_properties": "碰它要付什么",
            "symbolic_state": "它此刻什么状态",
        }.get(slot, slot)
    if kind == "world_rule":
        return {
            "cost": "谁打破谁付钱",
            "limitations": "它管到哪里",
            "exceptions": "谁例外",
            "capabilities": "它给人什么",
            "source": "规矩从哪来",
        }.get(slot, slot)
    return slot


def _codex_slot_reason(kind: str, slot: str, row: Mapping[str, Any] | None) -> str:
    name = ""
    if isinstance(row, dict):
        name = str(row.get("name") or row.get("id") or "")
    who = name or "这个人"
    if kind == "character":
        if slot in ("surface_goal", "deep_need"):
            return f"{who}要什么还没立住。写他在这本书里非拿到不可的那件事。"
        if slot in ("fear", "internal_conflict"):
            return f"{who}让人付出什么还没立住。写他会逼主角丢掉什么。"
        if slot == "personality_detail":
            return f"{who}的性格只为说清他要什么、他让人付出什么，不要写成鉴定表。"
        if slot == "abilities":
            return f"写清{who}靠什么收账。"
        if slot == "weaknesses":
            return f"写清{who}缺什么就会付账。"
        return f"只改{who}卡上不像的那一条。"
    if kind == "term":
        part = slot.split(":", 1)[1] if str(slot).startswith("part:") else slot
        if part in _TERM_PARTS:
            return f"这个词的「{part}」还没说清它怎么让人变贵。"
        return "这个词还没写够让人看见它怎么收账。"
    if kind == "faction":
        return "这股势力要主角付出什么还没立住。"
    if kind == "item":
        return "这件东西让谁变贵还没立住。"
    if kind == "world_rule":
        return "这条规矩谁打破谁付钱还没立住。"
    return "只改不像的那一条。"


def first_codex_slot(kind: str, missing: list | None, fields: Mapping[str, Any] | None) -> str | None:
    ids: list[str] = []
    for m in missing or []:
        mid = m.get("id") if isinstance(m, dict) else str(m)
        mid = str(mid or "").strip()
        if mid and mid != "pack":
            ids.append(mid)
    if kind == "character":
        for prefer in (
            "surface_goal", "deep_need", "fear", "internal_conflict",
            "personality_detail", "abilities", "weaknesses",
        ):
            if prefer in ids:
                return prefer
    if kind == "term":
        for part in _TERM_PARTS:
            key = f"part:{part}"
            if key in ids:
                return key
    if ids:
        return ids[0]
    src = fields if isinstance(fields, dict) else {}
    if kind == "character":
        thinnest, n = "", 10 ** 9
        for key in ("surface_goal", "deep_need", "fear", "internal_conflict", "personality_detail"):
            got = cn_len(src.get(key))
            if got < n:
                thinnest, n = key, got
        return thinnest or "surface_goal"
    if kind == "term":
        return "part:是什么"
    return None


def merge_codex_slot(kind: str, base: dict, patch: dict, slot: str) -> dict[str, Any]:
    out = dict(base or {})
    src = patch if isinstance(patch, dict) else {}
    if kind == "term" and str(slot).startswith("part:"):
        part = slot.split(":", 1)[1]
        new = str(src.get(part) or "").strip()
        dfn = str(src.get("definition") or "")
        if not new and dfn:
            m = re.search(
                rf"{re.escape(part)}\s*[:：]\s*(.+?)(?=(?:是什么|不是什么|本书用法|边界)\s*[:：]|\Z)",
                dfn,
                re.S,
            )
            if m:
                new = m.group(1).strip()
        if new:
            old = str(out.get("definition") or "")
            pat = re.compile(
                rf"{re.escape(part)}\s*[:：].*?(?=(?:是什么|不是什么|本书用法|边界)\s*[:：]|\Z)",
                re.S,
            )
            if pat.search(old):
                out["definition"] = pat.sub(f"{part}：{new}\n", old).strip()
            else:
                out["definition"] = (old + f"\n{part}：{new}").strip()
        return out
    key = slot
    if key in src and src[key] not in (None, "", [], {}):
        out[key] = src[key]
    return out


def _codex_slot_edit_hint(
    kind: str,
    slot: str,
    row: Mapping[str, Any] | None,
    working: Mapping[str, Any] | None,
) -> str:
    keep = json.dumps(
        {k: v for k, v in (working or {}).items() if v not in (None, "", [], {})},
        ensure_ascii=False,
    )[:2000]
    label = _codex_slot_label(kind, slot)
    reason = _codex_slot_reason(kind, slot, row)
    return (
        "【只改这一条】别的字段已经钉住，一个字都不要动。\n"
        f"【已过·原样保留】{keep}\n"
        f"只改「{label}」。\n"
        f"{reason}\n"
        "只输出这一条，不要重写整张卡。\n"
    )


def build_codex_prompt(
    kind: str,
    row: Mapping[str, Any] | None,
    *,
    extra: str = "",
    strict: bool = False,
    previous: str = "",
    bible: str = "",
    retry_hint: str = "",
) -> str:
    if retry_hint and "只改这一条" in retry_hint:
        bits = [retry_hint]
        name = ""
        if isinstance(row, dict):
            name = str(row.get("name") or row.get("id") or "")
        if name:
            bits.append(f"实体名：{name}")
        if extra:
            bits.append(extra.strip())
        if (bible or "").strip():
            bits.append(str(bible).strip())
        return "\n\n".join(bits)
    bits = [spec_ask(kind)]
    if strict:
        bits.insert(0, "【重试·必须达到覆盖地板，禁止短稿】")
    name = ""
    if isinstance(row, dict):
        name = str(row.get("name") or row.get("id") or "")
        bits.append("现有字段：" + json.dumps(
            {k: v for k, v in row.items() if v not in (None, "", [], {})},
            ensure_ascii=False,
        )[:2000])
    if name:
        bits.append(f"实体名：{name}")
    if extra:
        bits.append(extra.strip())
    if (bible or "").strip():
        bits.append(str(bible).strip())
    if previous:
        bits.append("上次输出过短或结构不够，按合同重写：\n" + previous[:800])
    return "\n\n".join(bits)


_NAME_ONLY_KEYS = frozenset({"name", "id", "kind", "archived", "local"})


def _local_name(name: str) -> str:
    n = str(name or "").strip()
    return n.split(":", 1)[-1] if ":" in n else n


def row_is_name_only(row: Mapping[str, Any] | None) -> bool:
    if not isinstance(row, dict):
        return True
    for key, val in row.items():
        if key in _NAME_ONLY_KEYS:
            continue
        if val not in (None, "", [], {}):
            return False
    return True


def load_codex_row(st, kind: str, name: str) -> dict[str, Any]:
    """从 store 读整行，供 skip / 灯 / thicken 合并。无行返回 {}。"""
    if st is None:
        return {}
    k = (kind or "").strip().lower()
    if k == "voice_profile":
        k = "voice"
    n = str(name or "").strip()
    local = _local_name(n)
    row: dict[str, Any] = {}
    try:
        if k == "character":
            if hasattr(st, "get_character_archive_row"):
                got = st.get_character_archive_row(local)
                if got:
                    row = dict(got)
            if not row and hasattr(st, "characters"):
                for c in st.characters() or []:
                    cname = getattr(c, "name", "") or ""
                    cid = str(getattr(c, "id", "") or "")
                    if cname in (n, local) or cid in (n, f"role:{local}") or cid.endswith(":" + local):
                        traits = getattr(c, "traits", None) or {}
                        row = {"name": cname, **(traits if isinstance(traits, dict) else {})}
                        break
        elif k == "faction" and hasattr(st, "get_faction"):
            got = st.get_faction(n) or (st.get_faction(local) if local != n else None)
            if got:
                row = dict(got)
        elif k == "item" and hasattr(st, "get_item"):
            got = st.get_item(n) or (st.get_item(local) if local != n else None)
            if got:
                row = dict(got)
        elif k == "term" and hasattr(st, "get_term"):
            got = st.get_term(n) or (st.get_term(local) if local != n else None)
            if got:
                row = dict(got)
        elif k == "world_rule" and hasattr(st, "get_world_rule"):
            got = st.get_world_rule(n) or (st.get_world_rule(local) if local != n else None)
            if got:
                row = dict(got)
        elif k == "motif" and hasattr(st, "list_motifs"):
            for m in st.list_motifs() or []:
                mid = str(m.get("id") or "")
                if str(m.get("name") or "") in (n, local) or mid.endswith(local) or mid == n:
                    row = dict(m)
                    break
        elif k == "voice":
            if hasattr(st, "get_voice_profile"):
                for cid in (n, f"role:{local}", local):
                    got = st.get_voice_profile(cid)
                    if got:
                        row = dict(got)
                        row.setdefault("name", cid)
                        break
            if not row and hasattr(st, "list_voice_profiles"):
                for p in st.list_voice_profiles() or []:
                    cid = str(p.get("character_id") or p.get("name") or "")
                    if cid in (n, local, f"role:{local}") or cid.endswith(":" + local):
                        row = dict(p)
                        row.setdefault("name", cid)
                        break
    except Exception:
        logging.getLogger("scribe3.codex_generate").debug("load_codex_row failed", exc_info=True)
        return {}
    if row and not row.get("name"):
        row["name"] = n or local
    return row


def apply_codex_persist_fields(
    kind: str,
    public: dict | None,
    secret: dict | None = None,
    chief_only: dict | None = None,
) -> dict[str, Any]:
    """§9.1：三袋合并进一次落库 dict，秘密键带 ``{key}_secret``。"""
    from scribe3.codex_schema import chief_only_keys, secret_flag_key

    k = (kind or "").strip().lower()
    pub = dict(public or {})
    sec = dict(secret or {})
    only = dict(chief_only or {})
    for bag in (pub, sec, only):
        if bag.get("private_operation"):
            raise ValueError("deprecated_field:private_operation")
    chief: set[str] = set()
    try:
        if k in ("character", "faction", "item", "term", "world_rule"):
            chief = set(chief_only_keys(k) or ())
    except Exception:
        chief = {"secret_agenda"} if k == "faction" else set()
    for key in list(pub):
        if key in chief:
            only.setdefault(key, pub.pop(key))
    fields = dict(pub)

    def _put_secret(src: dict) -> None:
        for key, val in src.items():
            if key.endswith("_secret"):
                if val:
                    fields[key] = True
                continue
            fields[key] = val
            try:
                fields[secret_flag_key(key)] = True
            except Exception:
                fields[f"{key}_secret"] = True

    _put_secret(sec)
    _put_secret(only)
    return fields


PORTRAIT_FACT_CAP = 12
_PORTRAIT_KINDS = frozenset({"character", "faction", "item", "term", "world_rule"})

_KIND_PREFIX = {
    "character": "role",
    "faction": "org",
    "item": "item",
    "term": "term",
    "world_rule": "rule",
}


def portrait_entity_oids(kind: str, row: Mapping[str, Any] | None) -> list[str]:
    """这个实体在命题里可能出现的主语 id。"""
    src = row if isinstance(row, dict) else {}
    name = str(src.get("name") or "").strip()
    raw_id = str(src.get("id") or src.get("oid") or "").strip()
    out: list[str] = []
    seen: set[str] = set()

    def _add(oid: str) -> None:
        oid = (oid or "").strip()
        if oid and oid not in seen:
            seen.add(oid)
            out.append(oid)

    _add(raw_id)
    prefix = _KIND_PREFIX.get((kind or "").strip().lower())
    if prefix and name:
        _add(f"{prefix}:{name}")
    if name and ":" not in name:
        _add(name)
    return out


def facts_for_portrait(
    st,
    kind: str,
    row: Mapping[str, Any] | None,
    *,
    cap: int = PORTRAIT_FACT_CAP,
) -> list:
    """这个实体自己的命题，按章号排。含 隐瞒·。

    写厚短文问的是「他要什么 / 他让人付出什么」。答案在命题里，不在设定名片上。
    """
    if st is None:
        return []
    oids = set(portrait_entity_oids(kind, row))
    if not oids:
        return []
    reader = getattr(st, "facts_unfolded_at", None) or getattr(st, "facts_at", None)
    if not callable(reader):
        return []
    try:
        facts = list(reader(10**9) or [])
    except TypeError:
        facts = list(reader() or [])
    except Exception:
        logging.getLogger("scribe3.codex_generate").debug(
            "facts_for_portrait failed", exc_info=True)
        return []
    hit = []
    for f in facts:
        eid = str(getattr(f, "entity_id", "") or "")
        if eid in oids:
            hit.append(f)
    hit.sort(key=lambda f: (
        int(getattr(f, "valid_from", 0) or 0),
        str(getattr(f, "attribute", "") or ""),
        str(getattr(f, "id", "") or ""),
    ))
    return hit[: max(0, int(cap))]


def format_portrait_facts(facts) -> str:
    lines = []
    for f in facts or []:
        ch = getattr(f, "valid_from", None)
        attr = str(getattr(f, "attribute", "") or "").strip()
        val = str(getattr(f, "value", "") or "").strip()
        if not attr and not val:
            continue
        prefix = f"第{ch}章 " if ch not in (None, "") else ""
        lines.append(f"- {prefix}{attr}：{val}")
    if not lines:
        return ""
    return "【这个实体在书里已经发生的事】\n" + "\n".join(lines)


def _bible_for(st, work, kind: str, row: dict, extra: str, include_secret: bool) -> str:
    if st is None:
        return ""
    if not hasattr(st, "characters") and not hasattr(st, "list_terms"):
        return ""
    from scribe3.api.services.write_assemble_blocks import _codex_segments
    from scribe3.iceberg import named_pack_soft_cap
    name = str((row or {}).get("name") or "")
    request = " ".join(p for p in (name, extra) if p)
    named, cards, _st = _codex_segments(
        st, reveal=not include_secret, focalizer="",
        chapter=None, for_generation=not include_secret,
        request_text=request, work=work,
        named_soft_cap=named_pack_soft_cap(work=work),
    )
    own = ""
    if (kind or "").strip().lower() in _PORTRAIT_KINDS:
        own = format_portrait_facts(facts_for_portrait(st, kind, row))
    return "\n".join(p for p in (named, cards, own) if p)


#: 角色 duty 字段实质下限。改前：非空即过。改后：四槽各自达到这个字数。
#: 依据：现库「他要体温。」5 字被放行；7/23 的 surface_goal 短于 25 字。
#: 25 是「能说出要什么/让人付什么」的最短完整句，不是文风线，不许为过线再调低。
DUTY_FIELD_MIN = 25
CHAR_WANT_KEYS = ("surface_goal", "deep_need")
CHAR_PAY_KEYS = ("fear", "internal_conflict")


def _duty_cn(text: str) -> int:
    return cn_len(str(text or "").strip())


def _duty_long_enough(text: str) -> bool:
    return _duty_cn(text) >= DUTY_FIELD_MIN


def character_duty_issues(row: Mapping[str, Any] | None) -> list[str]:
    """缺他要什么 / 缺他让人付出什么。四槽都要够长，OR 两槽会把短句放行。"""
    src = row if isinstance(row, dict) else {}
    issues: list[str] = []
    if not all(_duty_long_enough(str(src.get(k) or "")) for k in CHAR_WANT_KEYS):
        issues.append("缺他要什么")
    if not all(_duty_long_enough(str(src.get(k) or "")) for k in CHAR_PAY_KEYS):
        issues.append("缺他让人付出什么")
    return issues


def duty_fields_ready(kind: str, row: Mapping[str, Any] | None) -> bool:
    src = row if isinstance(row, dict) else {}
    if kind == "character":
        return not character_duty_issues(src)
    if kind == "item":
        return bool(str(src.get("description") or "").strip() or src.get("special_properties"))
    if kind == "world_rule":
        return bool(str(src.get("cost") or "").strip())
    if kind == "term":
        return bool(str(src.get("definition") or "").strip())
    if kind == "faction":
        return bool(str(src.get("ideology") or "").strip() or src.get("goals"))
    return False


def build_portrait_prompt(kind: str, row: Mapping[str, Any] | None, extra: str = "", bible: str = "") -> str:
    name = ""
    if isinstance(row, dict):
        name = str(row.get("name") or row.get("id") or "")
    who = name or "这个人"
    if kind == "character":
        ask = (
            f"写{who}在这本书里是谁。他要什么写两句，他会让人付出什么写两句。"
            "不要填表，不要 JSON。不要写他怕什么。"
        )
    elif kind == "item":
        ask = f"写{who}这件东西让谁变贵。不要填表，不要 JSON。"
    elif kind == "world_rule":
        ask = f"写{who}这条规矩谁打破谁付钱。不要填表，不要 JSON。"
    elif kind == "term":
        ask = f"写{who}这个词在这本书里怎么收账。不要填表，不要 JSON。"
    else:
        ask = f"写{who}这股势力要主角付出什么。不要填表，不要 JSON。"
    bits = [ask, "只输出这篇短文。"]
    if extra:
        bits.append(extra.strip())
    if (bible or "").strip():
        bits.append(str(bible).strip())
    return "\n\n".join(bits)


PORTRAIT_EXTRACT_TRIES = 4


def build_portrait_extract_prompt(kind: str, portrait: str, *, missing: str = "") -> str:
    if kind == "character":
        need = (
            "他要什么：\n他还要什么：\n"
            "他让人付出什么：\n他还让人付出什么：\n"
            f"四行都要，每行至少 {DUTY_FIELD_MIN} 个字。"
            "不要抄「他要体温。」这种短句；短文里还有更长的原句就抄长的。"
        )
    elif kind == "item":
        need = "让谁变贵："
    elif kind == "world_rule":
        need = "谁打破谁付钱："
    elif kind == "term":
        need = "是什么：\n不是什么：\n本书用法：\n边界："
    else:
        need = "他们要主角付出什么："
    bits = [
        "下面这篇短文已经过审。只从这篇里抽出这几行，不要另编。",
        need,
        "【短文】\n" + (portrait or "").strip(),
        "只输出从短文里抄出来的行。抽出的字必须是短文里连续出现的原句。",
    ]
    if (missing or "").strip():
        bits.append("【缺的就是这几条，只补它们】\n" + missing.strip())
    return "\n\n".join(bits)


def portrait_missing_hint(kind: str, working: Mapping[str, Any] | None, portrait: str) -> str:
    """抽取重试时把缺哪条直接点给模型。"""
    src = working if isinstance(working, dict) else {}
    bits: list[str] = []
    if kind == "character":
        labels = (
            ("surface_goal", "他要什么"),
            ("deep_need", "他还要什么"),
            ("fear", "他让人付出什么"),
            ("internal_conflict", "他还让人付出什么"),
        )
        for key, lab in labels:
            if not _duty_long_enough(str(src.get(key) or "")):
                bits.append(f"缺「{lab}」。从短文里抄一句原话，不要改写，不要写他怕什么。")
    elif kind == "item":
        if not str(src.get("description") or "").strip() and not src.get("special_properties"):
            bits.append("缺「让谁变贵」。从短文里抄一句原话，不要改写。")
    elif kind == "world_rule":
        if not str(src.get("cost") or "").strip():
            bits.append("缺「谁打破谁付钱」。从短文里抄一句原话，不要改写。")
    elif kind == "term":
        if not str(src.get("definition") or "").strip():
            bits.append("缺这个词怎么收账。从短文里抄，不要改写。")
    elif kind == "faction":
        if not str(src.get("ideology") or "").strip() and not src.get("goals"):
            bits.append("缺「他们要主角付出什么」。从短文里抄一句原话，不要改写。")
    if duty_fields_ready(kind, src) and not portrait_grounded(kind, src, portrait):
        bits.append("抽出的字必须是短文里连续出现的原句，不要改写、不要把两句拼成一句。")
    return "\n".join(bits)


def portrait_stash_fields(kind: str, src: Mapping[str, Any] | None, portrait: str) -> dict[str, Any]:
    """抽取最终失败时把短文留下来。已有正文的字段不覆盖。"""
    text = str(portrait or "").strip()
    if not text:
        return {}
    key = {
        "character": "personality_detail",
        "faction": "ideology",
        "item": "description",
        "world_rule": "cost",
        "term": "definition",
    }.get((kind or "").strip().lower())
    if not key:
        return {}
    row = src if isinstance(src, dict) else {}
    if str(row.get(key) or "").strip():
        return {}
    return {key: text}


def _duty_blob(kind: str, fields: Mapping[str, Any] | None) -> str:
    src = fields if isinstance(fields, dict) else {}
    if kind == "character":
        return " ".join(str(src.get(k) or "") for k in (
            "surface_goal", "deep_need", "fear", "internal_conflict",
        ))
    if kind == "item":
        return str(src.get("description") or "")
    if kind == "world_rule":
        return str(src.get("cost") or "")
    if kind == "term":
        return str(src.get("definition") or "")
    if kind == "faction":
        return str(src.get("ideology") or "")
    return ""


#: 字段实词过半落在短文里即算同源。与 charter._loose_match 同一条线：
#: 防的是另编，不是防抽取器把长句压短。过半是「多数」，不是「全部」——
#: 压缩会丢掉虚词和尾巴，全部命中会把合法压缩误杀。
PORTRAIT_GROUND_RATIO = 0.5
PORTRAIT_REUSE_MIN = 80

_DUTY_KEYS = {
    "character": ("surface_goal", "deep_need", "fear", "internal_conflict"),
    "item": ("description",),
    "world_rule": ("cost",),
    "term": ("definition",),
    "faction": ("ideology",),
}


def duty_field_texts(kind: str, fields: Mapping[str, Any] | None) -> list[str]:
    src = fields if isinstance(fields, dict) else {}
    out: list[str] = []
    for key in _DUTY_KEYS.get((kind or "").strip().lower(), ()):
        val = src.get(key)
        if isinstance(val, (list, tuple)):
            val = " ".join(str(x) for x in val if str(x).strip())
        text = str(val or "").strip()
        if text:
            out.append(text)
    return out


def _field_in_portrait(field: str, portrait: str) -> bool:
    from scribe3.charter import _tokens
    from scribe3.playbook.quote import _norm
    toks = [t for t in _tokens(field, drop_stop=True) if len(t) >= 2]
    if not toks:
        f, p = _norm(field), _norm(portrait)
        return bool(f) and f in p
    hit = sum(1 for t in toks if t in portrait)
    return hit / len(toks) >= PORTRAIT_GROUND_RATIO


def portrait_grounded(kind: str, fields: Mapping[str, Any] | None, portrait: str) -> bool:
    """每个非空 duty 字段单独对短文判定，不再把字段拼成一串再找子串。"""
    if not str(portrait or "").strip():
        return False
    texts = duty_field_texts(kind, fields)
    if not texts:
        return False
    return all(_field_in_portrait(t, portrait) for t in texts)


def existing_portrait(kind: str, src: Mapping[str, Any] | None) -> str:
    """已经 stash 过的短文。够长就直接抽，不要再写一篇。"""
    key = {
        "character": "personality_detail",
        "faction": "ideology",
        "item": "description",
        "world_rule": "cost",
        "term": "definition",
    }.get((kind or "").strip().lower())
    if not key:
        return ""
    text = str((src or {}).get(key) or "").strip()
    return text if len(text) >= PORTRAIT_REUSE_MIN else ""


def _labeled_line(text: str, *labels: str) -> str:
    for lab in labels:
        m = re.search(rf"{re.escape(lab)}\s*[:：]\s*(.+)", text)
        if m:
            return m.group(1).strip().split("\n", 1)[0].strip()
    return ""


def _split_unlabeled_parts(text: str, n: int) -> list[str]:
    """无标签切 n 段：空行分段优先，否则按句号切。不够就空串，不许拿别段凑。"""
    src = (text or "").strip()
    empty = [""] * n
    if not src or n <= 0:
        return empty
    paras = [p.strip() for p in re.split(r"\n\s*\n", src) if p.strip()]
    if len(paras) >= n:
        return paras[:n]
    sents = [s.strip() for s in re.split(r"(?<=[。！？])", src) if s.strip()]
    if len(sents) >= n:
        return sents[:n]
    return empty


def _split_unlabeled_pair(text: str) -> tuple[str, str]:
    """无标签两段：空行分段优先，否则按句号切两句。"""
    a, b = _split_unlabeled_parts(text, 2)[:2]
    return a, b


_CHAR_EXTRACT_SLOTS = (
    ("surface_goal", ("他要什么", "表层目标")),
    ("deep_need", ("他还要什么", "深层需求")),
    ("fear", ("他让人付出什么",)),
    ("internal_conflict", ("他还让人付出什么", "内在冲突")),
)


def _accept_extract_val(val: str) -> str:
    """抽出的字短于下限就当没抽到。改前原样收下「他要体温。」，四槽看似有值、duty 仍失败。"""
    text = str(val or "").strip()
    return text if _duty_long_enough(text) else ""


def _apply_portrait_extract(kind: str, working: dict, patch: dict, raw: str) -> dict[str, Any]:
    out = dict(working or {})
    src = dict(patch or {})
    text = raw or ""
    if kind == "character":
        for key, labels in _CHAR_EXTRACT_SLOTS:
            val = _accept_extract_val(src.get(key) or "")
            if not val:
                val = _accept_extract_val(_labeled_line(text, *labels))
            if val:
                out[key] = val
        missing = [k for k, _ in _CHAR_EXTRACT_SLOTS
                   if not _duty_long_enough(str(out.get(k) or ""))]
        if missing:
            parts = _split_unlabeled_parts(text, 4)
            if all(parts):
                for (key, _labels), part in zip(_CHAR_EXTRACT_SLOTS, parts):
                    if not _duty_long_enough(str(out.get(key) or "")):
                        part = _accept_extract_val(part)
                        if part:
                            out[key] = part
            elif not any(_duty_long_enough(str(out.get(k) or ""))
                         for k, _ in _CHAR_EXTRACT_SLOTS):
                want, pay = _split_unlabeled_pair(text)
                if _accept_extract_val(want):
                    out["surface_goal"] = want.strip()
                if _accept_extract_val(pay):
                    out["fear"] = pay.strip()
        return out
    if kind == "item":
        desc = str(src.get("description") or "").strip()
        if not desc:
            m = re.search(r"让谁变贵\s*[:：]\s*(.+)", text)
            if m:
                desc = m.group(1).strip().split("\n", 1)[0]
        if desc:
            out["description"] = desc
        return out
    if kind == "world_rule":
        cost = str(src.get("cost") or "").strip()
        if not cost:
            m = re.search(r"谁打破谁付钱\s*[:：]\s*(.+)", text)
            if m:
                cost = m.group(1).strip().split("\n", 1)[0]
        if cost:
            out["cost"] = cost
        return out
    if kind == "term" and src.get("definition"):
        out["definition"] = src.get("definition")
        return out
    if kind == "faction":
        idea = str(src.get("ideology") or "").strip()
        if not idea:
            m = re.search(r"他们要主角付出什么\s*[:：]\s*(.+)", text)
            if m:
                idea = m.group(1).strip().split("\n", 1)[0]
        if idea:
            out["ideology"] = idea
    out.update({k: v for k, v in src.items() if v not in (None, "", [], {})})
    return out


def thicken_codex_portrait(
    kind: str,
    src: dict[str, Any],
    *,
    llm_fn: LlmFn,
    persist_fn: Callable[[dict], Any] | None,
    extra: str,
    include_secret: bool,
    bible: str,
) -> dict[str, Any]:
    reused = existing_portrait(kind, src)
    if reused:
        portrait = reused
        first = {}
    else:
        portrait = _call_llm(llm_fn, build_portrait_prompt(kind, src, extra=extra, bible=bible), MAX_TOKENS[kind])
        first = parse_codex_payload(kind, portrait)
    working = dict(first)
    if not (duty_fields_ready(kind, working) and portrait_grounded(kind, working, portrait)):
        for _rnd in range(PORTRAIT_EXTRACT_TRIES):
            if duty_fields_ready(kind, working) and portrait_grounded(kind, working, portrait):
                break
            hint = portrait_missing_hint(kind, working, portrait)
            ext = _call_llm(
                llm_fn,
                build_portrait_extract_prompt(kind, portrait, missing=hint),
                1024,
            )
            patch = parse_codex_payload(kind, ext)
            working = _apply_portrait_extract(kind, working, patch, ext)
        if not duty_fields_ready(kind, working) or not portrait_grounded(kind, working, portrait):
            stash = portrait_stash_fields(kind, src, portrait)
            if persist_fn and stash:
                persist_fn(stash)
            return {
                "ok": False, "code": "llm_thin", "kind": kind, "name": src.get("name"),
                "message": "短文过了，他要什么 / 他让人付出什么还没从这篇里抽出",
                "portrait": portrait[:800],
                "portrait_stashed": bool(stash),
                "stash_fields": stash,
            }
    public, secret, only = _split_bags(kind, working)
    out_fields = dict(public)
    if include_secret:
        out_fields.update(secret)
        out_fields.update(only)
    if persist_fn:
        persist_fn(out_fields)
    return {
        "ok": True,
        "kind": kind,
        "name": src.get("name"),
        "public_fields": public,
        "secret_fields": secret if include_secret else {},
        "chief_only_fields": only if include_secret else {},
        "cn": cn_len(json.dumps(public, ensure_ascii=False)),
        "source": "llm",
        "bible_attached": bool((bible or "").strip()),
        "portrait": portrait[:800],
    }


def thicken_codex(
    kind: str,
    row: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist_fn: Callable[[dict], Any] | None = None,
    extra: str = "",
    force: bool = False,
    include_secret: bool = False,
    st=None,
    work=None,
    name: str = "",
) -> dict[str, Any]:
    k = (kind or "").strip().lower()
    if k == "voice_profile":
        k = "voice"
    if k not in IMPLEMENTED:
        return {"ok": False, "code": "unknown_kind" if k not in {
            "character", "faction", "item", "term", "world_rule", "motif", "voice",
            "promise", "intent", "fact",
        } else "kind_not_implemented", "kind": k}
    src = dict(row or {})
    if name and not src.get("name"):
        src["name"] = name
    if st is not None and row_is_name_only(src):
        loaded = load_codex_row(st, k, str(src.get("name") or name or ""))
        if loaded:
            merged = dict(loaded)
            merged.update({kk: vv for kk, vv in src.items() if vv not in (None, "", [], {})})
            src = merged
    if k in _PORTRAIT_KINDS:
        if duty_fields_ready(k, src) and not force:
            return {"ok": True, "skipped": True, "status": "ready", "kind": k, "name": src.get("name")}
        bible = _bible_for(st, work, k, src, extra, include_secret)
        return thicken_codex_portrait(
            k, src, llm_fn=llm_fn, persist_fn=persist_fn, extra=extra,
            include_secret=include_secret, bible=bible,
        )
    ready = evaluate_codex_ready(k, src)
    if ready.get("ok") and not force:
        return {"ok": True, "skipped": True, "status": "ready", "kind": k, "name": src.get("name")}
    bible = _bible_for(st, work, k, src, extra, include_secret)
    prompt = build_codex_prompt(k, src, extra=extra, bible=bible)
    raw = _call_llm(llm_fn, prompt, MAX_TOKENS[k])
    fields = parse_codex_payload(k, raw)
    working = dict(fields)
    public, secret, only = _split_bags(k, working)
    blocked = persist_codex_fields_blocked(k, dict(public), mode="pack")
    for _rnd in range(4):
        if not blocked:
            break
        slot = first_codex_slot(k, blocked.get("missing"), public)
        if not slot:
            break
        hint = _codex_slot_edit_hint(k, slot, src, public)
        raw2 = _call_llm(
            llm_fn,
            build_codex_prompt(k, src, extra=extra, bible=bible, retry_hint=hint),
            MAX_TOKENS[k],
        )
        patch = parse_codex_payload(k, raw2)
        working = merge_codex_slot(k, working, patch, slot)
        public, secret, only = _split_bags(k, working)
        blocked = persist_codex_fields_blocked(k, dict(public), mode="pack")
    if blocked:
        return {
            "ok": False, "code": "llm_thin", "kind": k, "name": src.get("name"),
            "message": blocked.get("message"), "missing": blocked.get("missing"),
            "got": (blocked.get("missing") or [{}])[0].get("got"),
            "need": (blocked.get("missing") or [{}])[0].get("need"),
        }
    out_fields = dict(public)
    if include_secret:
        out_fields.update(secret)
        out_fields.update(only)
    if persist_fn:
        persist_fn(out_fields)
    return {
        "ok": True,
        "kind": k,
        "name": src.get("name"),
        "public_fields": public,
        "secret_fields": secret if include_secret else {},
        "chief_only_fields": only if include_secret else {},
        "cn": cn_len(json.dumps(public, ensure_ascii=False)),
        "source": "llm",
        "bible_attached": bool((bible or "").strip()),
    }


def list_codex_thicken_targets(
    st,
    *,
    kinds: list[str] | None = None,
    force: bool = False,
    offset: int = 0,
    max_items: int = 50,
) -> dict[str, Any]:
    want = [k for k in (kinds or list(IMPLEMENTED)) if k in IMPLEMENTED]
    cap = max(1, min(int(max_items or 50), 100))
    off = max(0, int(offset or 0))
    scanned = 0
    queued: list[dict[str, Any]] = []

    def _consider(kind: str, name: str, row: dict) -> None:
        nonlocal scanned
        scanned += 1
        if scanned <= off:
            return
        if len(queued) >= cap:
            return
        ready = evaluate_codex_ready(kind, row)
        if ready.get("ok") and not force:
            return
        queued.append({"kind": kind, "name": name, "row": row, "status": ready.get("status")})

    for kind in want:
        if kind == "character" and hasattr(st, "characters"):
            for c in st.characters() or []:
                name = getattr(c, "name", "") or ""
                traits = getattr(c, "traits", None) or {}
                row = {"name": name, **(traits if isinstance(traits, dict) else {})}
                _consider(kind, name, row)
        elif kind == "faction" and hasattr(st, "list_factions"):
            for row in st.list_factions() or []:
                _consider(kind, str(row.get("name") or ""), dict(row))
        elif kind == "item" and hasattr(st, "list_items"):
            for row in st.list_items() or []:
                _consider(kind, str(row.get("name") or ""), dict(row))
        elif kind == "term" and hasattr(st, "list_terms"):
            for row in st.list_terms() or []:
                _consider(kind, str(row.get("name") or ""), dict(row))
        elif kind == "world_rule" and hasattr(st, "list_world_rules"):
            for row in st.list_world_rules() or []:
                _consider(kind, str(row.get("name") or ""), dict(row))
        elif kind == "motif" and hasattr(st, "list_motifs"):
            for row in st.list_motifs() or []:
                _consider(kind, str(row.get("name") or ""), dict(row))
        elif kind == "voice" and hasattr(st, "list_voice_profiles"):
            for row in st.list_voice_profiles() or []:
                nm = str(row.get("character_id") or row.get("name") or "")
                packed = dict(row)
                packed.setdefault("name", nm)
                _consider(kind, nm, packed)
    return {
        "scanned": scanned,
        "queued": queued,
        "next_offset": off + len(queued) if off + len(queued) < scanned else None,
    }


def persist_codex_row(st, kind: str, name: str, fields: dict) -> bool:
    """批量免批落库：直接 store，不再套一层待批工具。"""
    n = (name or "").strip()
    if not n or not isinstance(fields, dict):
        return False
    k = kind
    try:
        if k == "term":
            if hasattr(st, "get_term") and st.get_term(n):
                return bool(st.patch_term(n, fields))
            st.add_term(n, **{kk: vv for kk, vv in fields.items() if kk != "name"})
            return True
        if k == "item":
            if hasattr(st, "get_item") and st.get_item(n):
                return bool(st.patch_item(n, fields))
            st.add_item(n, **{kk: vv for kk, vv in fields.items() if kk != "name"})
            return True
        if k == "world_rule":
            if hasattr(st, "get_world_rule") and st.get_world_rule(n):
                return bool(st.patch_world_rule(n, fields))
            st.add_world_rule(n, **{kk: vv for kk, vv in fields.items() if kk != "name"})
            return True
        if k == "faction":
            fields = {kk: vv for kk, vv in fields.items() if kk != "private_operation"}
            st.add_faction(n, **fields)
            return True
        if k == "character":
            from scribe3.ontology import Entity
            oid = f"role:{n}"
            if hasattr(st, "exists") and st.exists(oid):
                st.update_record(oid, fields)
            else:
                st.add_entity(Entity(oid, "character", n, traits=fields))
            return True
        if k == "motif":
            mid = str((fields.get("id") or n)).split(":")[-1]
            existing = None
            if hasattr(st, "get_motif"):
                existing = st.get_motif(mid) or st.get_motif(n)
            if not existing and hasattr(st, "list_motifs"):
                for m in st.list_motifs() or []:
                    if str(m.get("name") or "") == n or str(m.get("id") or "").endswith(mid):
                        existing = m
                        mid = str((m.get("id") or mid)).split(":")[-1]
                        break
            if existing:
                if hasattr(st, "update_motif"):
                    st.update_motif(mid, fields)
                    return True
                if hasattr(st, "patch_motif"):
                    return bool(st.patch_motif(mid, fields))
            if hasattr(st, "add_motif"):
                st.add_motif(
                    n,
                    theme=fields.get("theme") or "",
                    echoes=fields.get("echoes") or "",
                    unfolding=fields.get("unfolding") or "",
                    echo_terms=fields.get("echo_terms"),
                    phase=fields.get("phase") or "seed",
                    tier=fields.get("tier") or "book",
                    scope=fields.get("scope"),
                )
                return True
            return False
        if k == "voice" and hasattr(st, "set_voice_profile"):
            st.set_voice_profile(n, fields)
            return True
    except Exception as e:
        logging.getLogger("scribe3.codex_generate").warning("persist %s %s failed: %s", k, n, e)
        return False
    return False


def thicken_codex_batch(
    st,
    *,
    llm_fn: LlmFn,
    persist: bool = False,
    kinds: list[str] | None = None,
    force: bool = False,
    extra: str = "",
    include_secret: bool = False,
    offset: int = 0,
    max_items: int = 50,
    work=None,
) -> dict[str, Any]:
    listed = list_codex_thicken_targets(
        st, kinds=kinds, force=force, offset=offset, max_items=max_items,
    )
    items: list[dict[str, Any]] = []
    for tgt in listed["queued"]:
        out = thicken_codex(
            tgt["kind"], tgt["row"], llm_fn=llm_fn, extra=extra, force=force,
            include_secret=include_secret, st=st, work=work, name=tgt["name"],
        )
        row: dict[str, Any] = {
            "kind": tgt["kind"], "name": tgt["name"],
            "status": "ok" if out.get("ok") and not out.get("skipped") else (
                "skipped_ready" if out.get("skipped") else out.get("code") or "llm_thin"
            ),
            "cn": out.get("cn") or 0,
            "persist": "none",
        }
        if out.get("ok") and persist and not out.get("skipped"):
            try:
                fields = apply_codex_persist_fields(
                    tgt["kind"],
                    out.get("public_fields"),
                    out.get("secret_fields") if include_secret else {},
                    out.get("chief_only_fields") if include_secret else {},
                )
            except ValueError:
                row["persist"] = "write_failed"
                row["status"] = "deprecated_field"
                items.append(row)
                continue
            written = persist_codex_row(st, tgt["kind"], tgt["name"], fields)
            row["persist"] = "written" if written else "write_failed"
            if not written:
                row["status"] = "write_failed"
            logging.getLogger("scribe3.codex_generate").info(
                "codex_batch work=%s kind=%s name=%s cn=%s source=codex_batch written=%s",
                work, tgt["kind"], tgt["name"], row["cn"], written,
            )
        elif persist and out.get("stash_fields"):
            written = persist_codex_row(st, tgt["kind"], tgt["name"], out["stash_fields"])
            row["persist"] = "stashed" if written else "write_failed"
            row["portrait_stashed"] = bool(written)
        elif not persist:
            row["persist"] = "preview"
            row["public_fields"] = out.get("public_fields") or {}
        if out.get("message"):
            row["error"] = out.get("message")
        items.append(row)
    return {
        "status": "ok",
        "scanned": listed["scanned"],
        "queued": len(listed["queued"]),
        "next_offset": listed["next_offset"],
        "items": items,
    }

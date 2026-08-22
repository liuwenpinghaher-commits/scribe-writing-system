"""Write-assemble prompt blocks (PR-EH-10).

Extracted helpers re-exported by ``write_assemble`` facade.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from scribe3.feature_flags import get_flag

_CODEX_PAD_SLOGAN = "这不是口号，是巷里炉灰和铜腥贴在骨头上的实感。"


def strip_codex_pad(text: str) -> str:
    """剥历史垫字口号，并压掉连续重复的同一短句。"""
    raw = str(text or "")
    if not raw:
        return ""
    cleaned = raw.replace(_CODEX_PAD_SLOGAN, "")
    cleaned = re.sub(r"[；;]{2,}", "；", cleaned)
    cleaned = re.sub(r"。{2,}", "。", cleaned)
    cleaned = re.sub(r"(这不是口号[^。]{0,40}。\s*)+", "", cleaned)
    # 同一短句连写三遍以上 → 留一遍
    cleaned = re.sub(r"([^。；\n]{8,40})(?:[；;]\s*\1){2,}", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def _live_known_members(st, row: dict) -> list:
    """ATL-06：势力成员按当前在册角色过滤，归档/已删的不进 prompt。"""
    members = list(row.get("known_members") or [])
    if not members:
        return members
    alive: set[str] = set()
    try:
        chars = []
        if hasattr(st, "characters"):
            chars = st.characters() or []
        elif hasattr(st, "list_characters"):
            chars = st.list_characters() or []
        for c in chars:
            if isinstance(c, dict):
                name = str(c.get("name") or "").strip()
                oid = str(c.get("id") or "")
            else:
                name = str(getattr(c, "name", "") or "").strip()
                oid = str(getattr(c, "id", "") or "")
            if name:
                alive.add(name)
                alive.add(f"role:{name}")
            if oid:
                alive.add(oid)
                alive.add(oid.split(":")[-1])
    except Exception:
        return members
    if not alive:
        return members
    return [m for m in members if str(m) in alive or str(m).split(":")[-1] in alive]


def _faction_prompt_block(st, row: dict, *, chapter: int, known_ids: set,
                          secret_ids: set, fact_index: dict, for_generation: bool) -> str:
    """单个势力的结构化注入块(CX-Task 6):按注册表 in_prompt 字段拼,secret/chief_only
    字段经三档可见性门控,附该势力的关系网摘要,超预算截断。

    U-003 三档可见性(2026-07-15):`for_generation` 是本函数的核心门控参数——
    True=限知续写/生成路径(读者最终会看到的正文),False=作者/主编对话(不流进正文,
    只是编辑讨论)。三档字段各自的门控规则:
    ① `chief_only`(如 secret_agenda,codex_chief_only_keys 结构性名单):
       for_generation=True → 永不注入,不看任何 knows 边/字段标志;
       for_generation=False → 直接注入(仅主编可见=主编对话看得见)。
    ② `secret_capable` 且 `{key}_secret=True`(如 origin/artifact_operation):
       for_generation=True → 保持既有**正证式** fail-closed(白名单,非黑名单):
       作者勾了 `{key}_secret` 就已经是"此字段是秘密"的权威声明,要证的只有一件事:
       **当前焦点者知道它**。证据 = 该字段桥接命题(codex_secret_bridge.sync_faction_secrets
       生成)的 fact id 出现在 known_ids(project_frame 在该章的知情投影)里。没有
       桥接命题(fid is None)、或 fid 不在 known_ids → 拿不出证据 → 不注入。
       for_generation=False → 直接注入(作者自己标记的秘密,作者/主编对话当然看得见,
       不必再向 knows 边求证——这是本次修订相对旧版最大的行为变化:旧版不分场合都走
       knows 边判据,导致主编在纯讨论里也看不到作者自己写的势力秘密)。
    ③ 其余字段:两档都注入,不受本函数门控影响。

    ⚠️ 2026-07-14 对抗审查修(仍然有效,别退回去):②的 fail-closed 判定只认 known_ids
    正证,不再用 `_secret_fact_ids` 反证"它是不是秘密"——那是黑名单式,`_secret_fact_ids`
    fail-soft 失败退空集会让黑名单式判据变成 fail-open(不看知不知情直接注入明文)。
    (secret_ids 参数保留在签名里供调用方兼容,判定不使用。)"""
    from scribe3.codex_schema import (
        chief_only_keys,
        fields_for,
        prompt_keys,
        secret_capable_keys,
        secret_flag_key,
    )
    from scribe3.api.services.prompt_blocks import _codex_value_repr, _faction_relation_summary
    name = row.get("name") or ""
    field_defs = {f.key: f for f in fields_for("faction")}
    secret_keys = set(secret_capable_keys("faction"))
    chief_keys = set(chief_only_keys("faction"))
    entity_id = f"faction:{name}"
    parts = []
    for key in prompt_keys("faction"):
        if key == "name":
            continue
        value = row.get(key)
        if key == "known_members":
            value = _live_known_members(st, row)
        if value in (None, "", [], {}):
            continue
        if key in chief_keys:
            if for_generation:
                continue   # ① 主编独知:生成/续写路径永不注入,即便字段有值
            # for_generation=False(作者/主编对话):直接注入,落到下面的拼接
        elif key in secret_keys and row.get(secret_flag_key(key)):
            if for_generation:
                fid = fact_index.get((entity_id, key))
                if fid is None or fid not in known_ids:
                    continue   # 拿不出"焦点者知情"的正面证据 → 不注入(fail-closed)
            # for_generation=False(作者/主编对话):直接注入,作者自己的秘密他看得见
        f = field_defs.get(key)
        if f is None:
            continue
        rep = _codex_value_repr(f, value)
        if rep:
            parts.append(f"{f.label}:{rep}")
    rel = _faction_relation_summary(st, name, chapter, for_generation=for_generation)
    if rel:
        parts.append(f"关系:{rel}")
    body = "；".join(parts)
    text = f"{name}（{body}）" if body else name
    # 点名公开档由调用方 clip_for(faction_public)；未点名走名片 ≤80。禁止 400+「…(略)」。
    return text


def _field_text(value, *, item_limit: int = 12) -> str:
    """拼公开档字段：不按字段 160 预裁，整档再 clip_for。"""
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return "、".join(items[:item_limit])
    if isinstance(value, dict):
        bits = []
        for k, v in value.items():
            sv = _field_text(v, item_limit=item_limit)
            if sv:
                bits.append(f"{k}={sv}")
        return "，".join(bits)
    return str(value).strip()


def _card_line(name: str, extra: str = "") -> str:
    from scribe3.iceberg import CARD_LINE_CAP
    label = str(name or "").strip()
    extra = str(extra or "").strip()
    text = f"- {label}（{extra}）" if extra else f"- {label}"
    if len(text) > CARD_LINE_CAP:
        return text[: max(1, CARD_LINE_CAP - 1)] + "…"
    return text


def _needles_for(kind: str, entity) -> list[str]:
    if kind == "character":
        name = str(getattr(entity, "name", "") or "").strip()
        cid = str(getattr(entity, "id", "") or "").strip()
        traits = getattr(entity, "traits", None) or {}
        aliases = traits.get("aliases") or []
        return [n for n in (name, cid, *[str(a).strip() for a in aliases]) if n]
    row = entity if isinstance(entity, dict) else {}
    name = str(row.get("name") or "").strip()
    out = [name] if name else []
    if kind in ("faction", "term"):
        for a in row.get("aliases") or []:
            s = str(a).strip()
            if s:
                out.append(s)
    return out


def _haystack_hit(needles: list[str], haystack: str) -> bool:
    if not haystack:
        return False
    return any(n and n in haystack for n in needles)


def _chapter_mention_blob(ch: dict | None) -> str:
    if not isinstance(ch, dict):
        return ""
    bits = [str(ch.get("synopsis") or "")]
    for b in ch.get("beats") or []:
        if isinstance(b, dict):
            bits.append(str(b.get("text") or ""))
        else:
            bits.append(str(b or ""))
    bits.append(str(ch.get("scene_truth") or ""))
    return "\n".join(bits)


def _named_priority(kind: str, request_hit: bool, focal_hit: bool, chapter_hit: bool, idx: int) -> tuple:
    """越大越先淘汰。request > focalizer > 章内提及 > 存储序；非 request 时保 term/rule/item。"""
    if request_hit:
        hit = 0
    elif focal_hit:
        hit = 1
    elif chapter_hit:
        hit = 2
    else:
        hit = 3
    kind_penalty = 0 if (request_hit or kind in ("term", "world_rule", "item")) else 1
    return (hit, kind_penalty, idx)


def _clip_named(kind: str, text: str) -> str:
    from scribe3.iceberg import clip_for
    field = {
        "character": "character_public",
        "faction": "faction_public",
        "item": "item",
        "term": "term",
        "world_rule": "world_rule",
    }.get(kind, kind)
    return clip_for(field, text)


def _character_named_line(c, *, reveal: bool) -> str:
    traits = (c.traits or {}) if hasattr(c, "traits") else {}
    bs = str(traits.get("backstory") or "")
    if bs and not reveal and traits.get("backstory_secret"):
        bs = ""
    fields = [
        ("别名", _field_text(traits.get("aliases"))),
        ("外观习惯", _field_text(traits.get("appearance"))),
        ("性格细节", _field_text(traits.get("personality_detail"))),
        ("性格标签", _field_text(traits.get("personality_tags"))),
        ("表层目标", _field_text(traits.get("surface_goal"))),
        ("深层需要", _field_text(traits.get("deep_need"))),
        ("恐惧", _field_text(traits.get("fear"))),
        ("内在冲突", _field_text(traits.get("internal_conflict"))),
        ("能力", _field_text(traits.get("abilities"))),
        ("弱点", _field_text(traits.get("weaknesses"))),
        ("叙事重要性", _field_text(traits.get("importance"))),
        ("首次登场", _field_text(traits.get("first_appearance"))),
    ]
    profile = "；".join(f"{label}:{value}" for label, value in fields if value)
    if bs:
        profile = f"前史:{bs}" + (f"；{profile}" if profile else "")
    body = f"- {c.name}" + (f"（{profile}）" if profile else "")
    return _clip_named("character", body)


def _item_named_line(row: dict) -> str:
    fields = [
        ("类别", _field_text(row.get("category"))),
        ("描述", _field_text(row.get("description"))),
        ("状态", _field_text(row.get("symbolic_state"))),
        ("持有者", _field_text(row.get("current_owner"))),
        ("特殊属性", _field_text(row.get("special_properties"))),
    ]
    body = "；".join(f"{lab}:{val}" for lab, val in fields if val)
    name = str(row.get("name") or "")
    text = f"- {name}" + (f"：{body}" if body else "")
    return _clip_named("item", text)


def _term_named_line(row: dict) -> str:
    fields = [
        ("类别", _field_text(row.get("category"))),
        ("定义", _field_text(row.get("definition"))),
        ("别名", _field_text(row.get("aliases"))),
    ]
    body = "；".join(f"{lab}:{val}" for lab, val in fields if val)
    name = str(row.get("name") or "")
    text = f"- {name}" + (f"：{body}" if body else "")
    return _clip_named("term", text)


def _rule_named_line(row: dict) -> str:
    fields = [
        ("类别", _field_text(row.get("category"))),
        ("源头", _field_text(row.get("source"))),
        ("代价", _field_text(row.get("cost"))),
        ("作用域", _field_text(row.get("scope"))),
        ("限制", _field_text(row.get("limitations"))),
        ("例外", _field_text(row.get("exceptions"))),
        ("赋予能力", _field_text(row.get("capabilities"))),
        ("备注", _field_text(row.get("note"))),
    ]
    body = "；".join(f"{lab}:{val}" for lab, val in fields if val)
    name = str(row.get("name") or "")
    text = f"- {name}" + (f"（{body}）" if body else "")
    return _clip_named("world_rule", text)


def _codex_known_ids(st, focalizer: str, chapter: int) -> set:
    if not focalizer:
        return set()
    try:
        from scribe3.feature_flags import flag_truthy
        if flag_truthy("SCRIBE3_EPISTEMIC_ORACLE"):
            from scribe3.epistemic import visible_to
            return {x for x in visible_to(st, "", int(chapter or 1), focalizer) if x}
    except Exception:
        pass
    if not hasattr(st, "load_knowledge") and not hasattr(st, "knowledge"):
        return set()
    from scribe3.knowledge import project_frame
    frame = project_frame(st, focalizer, chapter)
    return {f.id for f in frame.facts}


def _codex_bridge_index(st, chapter: int) -> dict:
    try:
        return {(f.entity_id, f.attribute): f.id for f in st.facts_at(chapter)}
    except Exception:
        return {}


def _join_kind_section(title: str, lines: list[str]) -> str:
    kept = [ln for ln in lines if ln]
    if not kept:
        return ""
    return title + "\n" + "\n".join(kept)


def _codex_segments(st, reveal: bool = True, focalizer: str = "", chapter: int | None = None,
                    for_generation: bool = False, request_text: str = "",
                    *, work: str | None = None, named_soft_cap: int | None = None
                    ) -> tuple[str, str, dict]:
    """点名公开档 + 未点名名片。秘密门在拼接阶段。"""
    from scribe3.iceberg import CARDS_PACK_CAP, named_pack_soft_cap

    def _safe(fn):
        return fn() or []

    mention = ""
    if for_generation and chapter is not None:
        try:
            mention = _chapter_mention_blob(st.get_chapter(int(chapter)) or {})
        except Exception:
            mention = ""

    named_items: list[dict] = []
    card_by_kind: dict[str, list[str]] = {
        "character": [], "faction": [], "item": [], "term": [], "world_rule": [],
    }
    card_limits = {
        "character": 14, "faction": 10, "item": 14, "term": 14, "world_rule": 10,
    }
    titles = {
        "character": "〔角色〕",
        "faction": "〔势力〕",
        "item": "〔物件〕",
        "term": "〔术语〕",
        "world_rule": "〔世界规则〕",
    }

    def _classify(kind: str, entity, idx: int, named_text: str, card_text: str) -> None:
        needles = _needles_for(kind, entity)
        req_hit = _haystack_hit(needles, request_text)
        foc_hit = False
        if for_generation and focalizer:
            foc_hit = any(focalizer == n or n in focalizer for n in needles if n)
        ch_hit = bool(for_generation and _haystack_hit(needles, mention))
        if req_hit or foc_hit or ch_hit:
            named_items.append({
                "kind": kind,
                "text": named_text,
                "label": needles[0] if needles else kind,
                "pri": _named_priority(kind, req_hit, foc_hit, ch_hit, idx),
            })
        elif len(card_by_kind[kind]) < card_limits[kind]:
            card_by_kind[kind].append(card_text)

    chars = _safe(st.characters)
    for idx, c in enumerate(chars):
        _classify(
            "character", c, idx,
            _character_named_line(c, reveal=reveal),
            _card_line(getattr(c, "name", "") or "", _field_text(
                ((c.traits or {}) if hasattr(c, "traits") else {}).get("importance")
            )),
        )

    facs = _safe(st.list_factions) if hasattr(st, "list_factions") else []
    if facs:
        eff_chapter = chapter if chapter is not None else 1
        known_ids = _codex_known_ids(st, focalizer, eff_chapter)
        from scribe3.context_assembler import _secret_fact_ids
        secret_ids = _secret_fact_ids(st)
        fact_index = _codex_bridge_index(st, eff_chapter)
        for idx, f in enumerate(facs):
            named_txt = _faction_prompt_block(
                st, f, chapter=eff_chapter, known_ids=known_ids,
                secret_ids=secret_ids, fact_index=fact_index,
                for_generation=for_generation,
            )
            if named_txt:
                named_txt = _clip_named("faction", f"- {named_txt}")
            _classify(
                "faction", f, idx, named_txt,
                _card_line(str((f or {}).get("name") or ""), str((f or {}).get("status") or "")),
            )

    items = _safe(st.list_items) if hasattr(st, "list_items") else []
    for idx, it in enumerate(items):
        _classify("item", it, idx, _item_named_line(it), _card_line(str((it or {}).get("name") or "")))

    terms = _safe(st.list_terms) if hasattr(st, "list_terms") else []
    for idx, t in enumerate(terms):
        _classify("term", t, idx, _term_named_line(t), _card_line(str((t or {}).get("name") or "")))

    rules = _safe(st.list_world_rules) if hasattr(st, "list_world_rules") else []
    for idx, r in enumerate(rules):
        cat = str((r or {}).get("category") or "")
        _classify(
            "world_rule", r, idx, _rule_named_line(r),
            _card_line(str((r or {}).get("name") or ""), cat),
        )

    cap = int(named_soft_cap) if named_soft_cap is not None else named_pack_soft_cap(work=work)
    named_items.sort(key=lambda x: x["pri"])
    kept_named: list[dict] = []
    used = 0
    for item in named_items:
        piece = item.get("text") or ""
        if not piece:
            continue
        if kept_named and used + len(piece) + 1 > cap:
            continue
        kept_named.append(item)
        used += len(piece) + 1

    named_by_kind: dict[str, list[str]] = {k: [] for k in titles}
    for item in kept_named:
        named_by_kind[item["kind"]].append(item["text"])

    named_parts = [
        _join_kind_section(titles[k], named_by_kind[k])
        for k in ("character", "faction", "item", "term", "world_rule")
    ]
    named_parts = [p for p in named_parts if p]

    motifs = _safe(st.list_motifs) if hasattr(st, "list_motifs") else []
    motif_block = ""
    if motifs:
        if for_generation:
            from scribe3.motif_craft import motif_schedule_directives, generation_motif_block
            next_ch = int(chapter) if chapter is not None else 1
            tmap = st.motif_touch_map() if hasattr(st, "motif_touch_map") else {}
            d = motif_schedule_directives(motifs, tmap, next_ch)
            motif_block = generation_motif_block(d) or ""
            if not motif_block:
                names = [m.get("name") for m in motifs[:5] if m.get("name")]
                if names:
                    motif_block = "〔母题·可主动编织〕" + "；".join(names)
        else:
            names = [m.get("name") for m in motifs[:10] if m.get("name")]
            if names:
                motif_block = "〔母题〕" + "；".join(names)
    if motif_block:
        named_parts.append(motif_block)

    banner = "【本书设定圣经(以下即这本书的全部设定,务必只据此写,绝不串入别的书/别的世界)】"
    named_body = "\n".join(named_parts)
    named_text = f"{banner}\n{named_body}" if named_body else ""

    card_parts = [
        _join_kind_section(titles[k], card_by_kind[k])
        for k in ("character", "faction", "item", "term", "world_rule")
    ]
    card_parts = [p for p in card_parts if p]
    cards_text = "\n".join(card_parts)
    if len(cards_text) > CARDS_PACK_CAP:
        cards_text = cards_text[: max(0, CARDS_PACK_CAP - 1)] + "…"
    if cards_text and not named_text:
        named_text = banner
        # 只有名片时仍保留圣经标题，避免旧测/身份块丢锚
        cards_text = f"{banner}\n{cards_text}"
        named_text = ""

    legacy_named, legacy_cards = named_text, cards_text
    try:
        from scribe3.feature_flags import flag_truthy
        if (
            flag_truthy("SCRIBE3_RECALL_PLAYBOOK")
            and flag_truthy("SCRIBE3_RECALL_DISCUSS")
            and chapter is not None
            and not for_generation
        ):
            from scribe3.recall_service import pack_text, recall
            pack = recall(
                st,
                chapter=int(chapter),
                focalizer=focalizer or "",
                query=request_text or mention or "",
                budget_tag="discuss_codex",
                work=work,
                reveal=reveal,
            )
            body = pack_text(pack)
            if body:
                chunks = [banner, body]
                if named_body:
                    chunks.append(named_body)
                named_text = "\n".join(chunks)
                cards_text = ""
            else:
                facts_fn = getattr(st, "facts_at", None)
                public = False
                if callable(facts_fn):
                    try:
                        public = any(
                            (f.get("secret") is not True if isinstance(f, dict) else not getattr(f, "secret", False))
                            for f in (facts_fn(int(chapter)) or [])
                        )
                    except Exception:
                        public = False
                if public:
                    try:
                        from scribe3.pipeline_trace_hooks import note_guide_missing
                        note_guide_missing(
                            "codex_recall_empty",
                            source="discuss",
                            budget_tag="discuss_codex",
                        )
                    except Exception:
                        pass
                # 优雅降级：空召回时保留全景名片，探索式宽问不变薄。
                # 语义=对得上的优先，对不上时至少不丢信息。作者已接受此折中。
                cards_text = legacy_cards
    except Exception:
        named_text, cards_text = legacy_named, legacy_cards  # 降级安全网，非旧路
        try:
            from scribe3.pipeline_trace_hooks import note_guide_missing
            note_guide_missing("codex_recall_overlay_skip")
        except Exception:
            pass

    stats = {
        "codex_named_chars": len(named_text),
        "codex_cards_chars": len(cards_text),
        "codex_entities_full": [f"{i['kind']}:{i['label']}" for i in kept_named],
        "codex_entities_card": [
            f"{k}:{ln}" for k, lines in card_by_kind.items() for ln in lines
        ],
    }
    try:
        from scribe3.feature_flags import flag_truthy
        if flag_truthy("SCRIBE3_RECALL_SHADOW") and chapter is not None:
            from scribe3.recall_service import shadow_diff
            legacy = "\n".join(p for p in (legacy_named, legacy_cards) if p)
            rec = shadow_diff(
                st, int(chapter), focalizer or "", legacy,
                query=request_text or "", path="discuss",
                reveal=reveal,
            )
            stats["recall_shadow_threshold_ok"] = rec.get("threshold_ok")
    except Exception:
        pass
    return named_text, cards_text, stats


def _codex_block(st, reveal: bool = True, focalizer: str = "", chapter: int | None = None,
                 for_generation: bool = False, request_text: str = "",
                 *, work: str | None = None) -> str:
    """兼容旧调用：点名档 + 名片拼成一段。写/讨论生产入口请用 ``_codex_segments``。"""
    named, cards, _stats = _codex_segments(
        st, reveal=reveal, focalizer=focalizer, chapter=chapter,
        for_generation=for_generation, request_text=request_text, work=work,
    )
    return "\n".join(p for p in (named, cards) if p)


def _editor_system(st, focalizer: str = "", chapter: int = None,
                   for_generation: bool = False, request_text: str = "") -> str:
    """主编对话的系统提示:注入本书北极星 + 角色 + 已确立设定。

    focalizer 非空(限知章):设定块只注入焦点者帧内可见事实,secret 明文屏蔽;
    focalizer 空(作者全知视角):M6 设定三态注入(opt-in)——本书未配 injection_mode 时
      等同旧 facts_at(99999)[:28] 全量(含私密标记,行为一字不变);一旦有 fact 显式配了
      injection_mode 则启用门控(None/always→恒注入,detected 挂真实实体→须本章草料提及,
      never→不注入,世界级命题→恒注入)+ 字符预算裁剪。

    for_generation(U-003 三档可见性,2026-07-15,默认 False=作者/主编对话):单纯
    透传给 `_codex_block`,门控势力 secret_capable/chief_only 字段是否注入——本函数
    自己不做判断。**`_editor_write_system`(唯一的生成/限知续写入口)调用本函数时
    恒传 True**;`chat_stream`/`chat_agentic_stream`(作者与主编对话,不流进正文)
    不传,吃默认值 False。新增任何调用点前,先想清楚它是不是"生成落进读者看到的
    正文"——是则必须显式传 True,不传默认值就是泄密(本仓库教训:每新开一个注入点
    都泄露过一次)。"""
    intent = st.get_intent()
    chars = st.characters()
    ctx_chars = "、".join(c.name for c in chars[:14]) or "(尚无角色)"

    if focalizer:
        # 限知模式:只注入焦点者帧内可见事实,secret value 物理屏蔽
        try:
            from scribe3.knowledge import project_frame
            ch = chapter if chapter is not None else 1
            frame = project_frame(st, focalizer, ch)
            masked = _facts(frame.facts, reveal_secret=False)
            visible = [d for d in masked if d.get("value") is not None]
            lines = [
                f"- {d.get('entity', '')} · {d.get('attribute', '')}:{d.get('value', '')}"
                for d in visible[:28]
            ]
        except Exception:
            raise   # U-011 fail-loud: _editor_system 限知帧可见设定
        ctx_set = "\n".join(lines) or "(焦点者帧内暂无可见设定)"
        set_label = f"【焦点者({focalizer})帧内可见设定(限知基座,帧外私密已屏蔽)】"
    else:
        # 作者全知视角:M6 设定三态注入(opt-in,migration 056)。
        # 真·向后兼容:本书从未配 injection_mode → assemble_injection 回 fallback=True,
        #   此处直接走旧 facts[:28] 全量,旧书行为一字不变(未点名实体/世界级命题/secret 均不丢)。
        # 一旦作者显式配了 ≥1 条 injection_mode → 启用门控:None/always/世界级 恒注入,
        #   detected 挂真实实体须本章草料(synopsis/beats/scene_truth)提及,never 不注入。
        def _line(f):
            return (f"- {f.entity_id} · {f.attribute}:{f.value}"
                    + ("(私密/伏线)" if f.secret else ""))

        def _is_faction_bridge_mirror(f) -> bool:
            """这条 Fact 是不是 codex_secret_bridge 造的势力 secret 字段镜像?

            薄委托(2026-07-15,parity 修补):判据本体已下沉到
            `codex_secret_bridge.is_faction_bridge_mirror`(单一真相源)——本函数只做
            Fact→(entity_id, attribute) 的取值适配,不再自己重复"entity_id 前缀 +
            secret_capable 字段名"这条逻辑。context_assembler.py 的 canonical 候选/store
            降级两条取数路径(Gap-B 修补)现在调用的是同一个领域函数,防止此处与那里各自
            实现、渐行渐远(2026-07-15 之前两处确实各写了一份)。
            (Fact 数据类没有 source 字段、facts_at 也没 SELECT 它,否则 source=='codex_bridge'
             会是更直白的判据;等哪天 Fact 带上 source,这里可以简化。)"""
            from scribe3.codex_secret_bridge import is_faction_bridge_mirror
            return is_faction_bridge_mirror(getattr(f, "entity_id", "") or "",
                                            getattr(f, "attribute", "") or "")

        # U-003(2026-07-15,端到端接线测试撞出的真实洞,不是假设性风险):
        # codex_secret_bridge.sync_faction_secrets 把 faction 表的 secret_capable/chief_only
        # 字段(origin/secret_agenda/...)镜像成一条 proposition(secret=True),目的只是给
        # project_frame/knowledge 限知链消费——它"该不该被看见"的权威判定已经由上面的
        # _codex_block/_faction_prompt_block 三档门控负责(带正确的中文字段标签,如"隐秘议程:…")。
        # 这条通用 Facts 全知转储此前对 for_generation 一无所知:只要 focalizer 为空(省略焦点者的
        # 全知视角续写章——一种正常写作模式,不是边角场景),同一份内容就会以裸格式
        # ("- faction:X · secret_agenda:明文(私密/伏线)")二次泄露,完全绕过三档门控。
        #
        # 在 **Fact 层**(渲染之前)滤掉这些镜像,而不是事后正则渲染出来的行:lines 有两个来源
        # (fallback 走 _line,门控态走 brief._fact_inject_line),字符串过滤要赌这两个格式
        # 永远保持一致——赌不起。不影响其余(非 codex 桥接的)真实故事秘密在全知视角的既有转储
        # 行为(那是长期支持的"省略焦点者=全知叙事"写法,不在 U-003 修复范围内)。
        def _keep_fact(f) -> bool:
            return not (for_generation and _is_faction_bridge_mirror(f))

        def _keep_item(i, by_id) -> bool:
            """门控态(assemble_injection 已渲染成 text)的同款判定。

            优先用结构判据(按 id 查回 Fact);查不回来时(理论上不该发生)降级到
            字符串判据兜底——两道判据都放行才注入。宁可多丢一行全知转储,不可漏一条。"""
            if not for_generation:
                return True
            f = by_id.get(i.get("id"))
            if f is not None:
                return not _is_faction_bridge_mirror(f)
            txt = i.get("text") or ""
            return not ("faction:" in txt
                        and any(f" · {k}:" in txt for k in codex_secret_capable_keys("faction")))

        try:
            from scribe3.brief import assemble_injection
            inj = assemble_injection(st, chapter)
            if inj["fallback"]:
                lines = [_line(f) for f in inj["facts"] if _keep_fact(f)][:28]
            else:
                by_id = {getattr(f, "id", None): f for f in (inj.get("facts") or [])}
                lines = [f"- {i['text']}" for i in inj["chosen"] if _keep_item(i, by_id)]
        except Exception:
            raise   # U-011 fail-loud: M6全知转储:assemble_injection崩不退裸转储
        ctx_set = "\n".join(lines) or "(尚无设定)"
        set_label = "【已确立设定(你全知,含私密伏线)】"

    # 开着的伏笔:预注入强提醒(易忘项;母题/事件等详情留主编按需调工具查)
    promises = st.open_promises() if hasattr(st, "open_promises") else []
    rem = ""
    if promises:
        items = "；".join(
            f"第{p.get('setup_chapter')}章埋:{(p.get('text') or '')[:30]}" for p in promises[:6])
        rem = f"\n【⚠ 开着的承诺线·勿忘(适时推进/回收,别让它凭空消失)】{items}"
    # 素材记忆能力提示(非空库时引导主编按需经 s3_material_recall 唤起参考素材;借鉴非事实)
    mat_hint = ""
    try:
        if st.list_materials():
            mat_hint = ("\n【素材记忆库】作者备有素材记忆(研究/风格/桥段等参考),讨论或构思时"
                        "可经 s3_material_recall(query) 按当前话题唤起相关素材借鉴(借鉴非照搬),"
                        "并向作者说明为什么参考。")
    except Exception:
        raise   # U-011 fail-loud: _editor_system 素材提示块
    red = (intent.get("red_lines") or "").strip()
    strip_iron = False
    try:
        from scribe3.memory_gain import should_strip_iron_laws
        strip_iron = should_strip_iron_laws()
    except Exception:
        strip_iron = False
    # D2：铁律单独成块；B2/B3 strip 时 constraint 与北极星行内红线一并清空
    constraint = ""
    if red and not strip_iron:
        constraint = (
            "\n【作者铁律·写作宪法｜必须遵守，禁止违反、禁止装忘、禁止用系统流/面板腔稀释】\n"
            f"{red}\n"
            "落实要求:正文中须可观察到上述约束的结果(如触感/禁忌/禁写法),勿仅口头复述原句。\n"
        )
    red_inline = "—" if strip_iron else (intent.get("red_lines") or "—")
    # D6：讨论全知 vs 限知写作分身标注
    mode_banner = ""
    try:
        from scribe3.epistemic_guard import (
            discussion_omniscient_banner, writing_limited_banner,
        )
        if for_generation and focalizer:
            mode_banner = writing_limited_banner(focalizer)
        elif not for_generation:
            mode_banner = discussion_omniscient_banner()
    except Exception:
        pass
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        f"{mode_banner}"
        f"【北极星·作品意图】读者感受:{intent['reader_feeling'] or '—'};"
        f"情感弧:{intent['emotional_arc'] or '—'};绝不背叛的红线:{red_inline}\n"
        f"{constraint}"
        f"【主要角色】{ctx_chars}\n{set_label}\n{ctx_set}\n\n"
        # 主编对话无焦点=全知 reveal；写章有焦点=限知，不把秘密摊给角色。
        f"{_codex_block(st, reveal=not focalizer, focalizer=focalizer, chapter=chapter, for_generation=for_generation, request_text=request_text) or '【本书设定圣经(以下即这本书的全部设定,务必只据此写,绝不串入别的书/别的世界)】\n(尚无设定)'}\n\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣上面的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    ) + rem + mat_hint + _author_prefs_block_safe()

def _editor_identity_block() -> str:
    """主编身份 + 硬协议(纯身份,零数据注入)。I1:v1 上下文段由 envelope 独占,故 v1
    只取本块作身份,避免 _editor_system 的设定/角色/伏笔注入与 envelope 的 canonical/global
    重复(facts 出现 2 次、promises 最多 3 次的注意力稀释病灶,B-3 同型)。
    与 _editor_system 共享措辞但独立成函数:_editor_system 保持原样(旧路径字节一致),
    本块把"上面的世界观与北极星"改指"下方提供的"——v1 里数据段在身份之后由 envelope 给出。"""
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣下方提供的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    )


def _write_protocol_block() -> str:
    """写作硬协议(讨论 vs 动稿)+ 文风基准(纯静态,零数据)。原 _editor_write_system 内联串
    原样抽出,供旧 _editor_write_system 与 v1 共用——不改一字,保旧路径字节一致。"""
    try:
        exemplar = _LUANSHI_EXEMPLAR  # type: ignore[name-defined]
    except NameError:
        from scribe3.api import app_impl as _core
        exemplar = getattr(_core, "_LUANSHI_EXEMPLAR", "……")
    return (
        "\n\n你是这部小说的主编,以**作者视角**帮作者写/改这本书的手稿——作者在写一本书,"
        "不是从某个角色的受限视角做渲染。\n\n"
        "## 核心判断:讨论 vs 动稿\n"
        "- 若作者只是讨论/提问/点评/分析/给意见 → **纯文字回复,绝对禁止输出 ⟦PROPOSAL⟧ 围栏**。\n"
        "- **仅当**作者明确使用「写/改/续写/帮我写/重写/把这段…/本章这样展开」等写作动词,\n"
        "  或作者提供了角色演绎草稿请求成文时 → 先简短说一句你的处理思路,"
        "然后把**书的本章正文**放进围栏:\n"
        "  (scope 取 chapter=整章 / selection=改选中段 / append=续写接在后面)\n"
        "  ⟦PROPOSAL scope=chapter⟧\n  （书的正文，作者笔调，纯散文，不要解说）\n  ⟦/PROPOSAL⟧\n"
        "- **多候选**:当作者对某段改写要求「2-3 个候选/几个版本/不同侧重」时,**连续输出 2-3 个独立的**\n"
        "  ⟦PROPOSAL scope=selection⟧…⟦/PROPOSAL⟧ 围栏,每个是对同一段的不同改法(如:一个收紧、"
        "一个加潜台词、一个换感官切入),围栏之间可不写解说。其余情况只出一个围栏。\n\n"
        "## 写作规则\n"
        "- 若作者给了某角色的「演绎草稿」(那角色这一场的限知体验)作为素材,把它**织进**书的叙事。\n"
        "- 尊重已确立设定/伏笔/北极星意图。默认作者视角(可全知);仅当作者明确指定本章跟某焦点者的"
        "限知走时,叙事才贴该视角、不写他不知道的私密。\n\n"
        "## 文风基准:贴《乱世铜炉》(志怪笔记体)——两条硬要求\n"
        "1. **古白话语体**:句子要带旧白话的筋骨与风物实词,少用现代抽象/翻译腔。多用'端的、岂料、怎禁得、"
        "却原来、一径、约莫'这类词;状物用具体名物(花脚毛驴、青骡子、喜糕、水酒)而非笼统形容。"
        "**禁**'像散了一地的骨头''张牙舞爪'这类用力过猛的现代文学比喻——冷笔、素描,信物自身说话。\n"
        "2. **世界密度(乱世铜炉的命门)**:每章须织入与主线无关、却让世界活起来的市井风物侧笔——"
        "婚丧社戏的张罗、乡邻帮衬、打更人讨水酒、行当忌讳、节庆吃食。别一上来直奔情节;让村镇先有烟火气,"
        "妖异方有依附。范例语感(仅供体感,勿照抄字句):\n"
        "  「" + exemplar + "」\n"
        "  ——注意它如何用一整段写婚宴的杀猪宰羊、姑嫂蒸糕、打更人讨酒,世界先活,事件才落地。"
    )


_REVISION_PHASES = frozenset({
    "revise", "revision", "rewrite", "edit", "polish", "span",
})

# 单字「改」太宽（改天/改名）；只认明确改稿意图。
_REVISION_HINTS = (
    "改稿", "修订", "重写", "改这段", "改选中", "只改这",
    "span 级", "span级", "定向改", "revise", "rewrite",
    "把这段改", "把这句改", "最小片段",
)


def is_revision_request(
    *,
    phase: str = "",
    request_text: str = "",
    extra_instructions: str = "",
) -> bool:
    """是否本次写请求在改已有稿。首稿/续写不灌修订纪律。"""
    ph = (phase or "").strip().lower()
    if ph in _REVISION_PHASES:
        return True
    blob = f"{request_text or ''}\n{extra_instructions or ''}"
    if not blob.strip():
        return False
    low = blob.lower()
    return any(h.lower() in low for h in _REVISION_HINTS)


def _write_revision_block() -> str:
    """M8 修订纪律。只应在 is_revision_request 为真时注入。"""
    return (
        "\n\n## 修订纪律\n"
        "- 改稿默认 **span 级定向**:只重写被指出的最小片段,其余一字不动;"
        "除非作者明确要求整章重写。\n"
        "- 禁止开放式整章自评重写(critique 放在大纲/节拍层;正文层只做表达增强)——"
        "自评重写会同质化、越改越平。\n"
        "- 高潮章作者要多候选时,按已有多候选围栏规则出 2-3 个独立版本。")


def inject_floor_env_enabled() -> bool:
    """SCRIBE3_INJECT_FLOOR 默认开启;测试可关以对照组装差。"""
    v = get_flag("SCRIBE3_INJECT_FLOOR").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def _anti_slop_floor_block() -> str:
    """内核3 最小生产集 · 反平庸/反 AI 腔硬约束(生成时注入,非仅事后检)。

    恒注入于写路径(受 SCRIBE3_INJECT_FLOOR 门控);不宣称保证文学上限。
    """
    if not inject_floor_env_enabled():
        return ""
    return (
        "\n\n## 生产下限\n"
        "- 禁 AI 腔与段末升华金句；情绪走微动作，不直说「他感到」。\n"
        "- 叙述者须真诚相信当下认知，禁「果然/殊不知/万万没想到」预告腔。\n"
        "- 设定只露必要；开着的承诺须推进或回收。"
    )


def provenance_in_prompt_enabled() -> bool:
    """SCRIBE3_PROVENANCE_IN_PROMPT 默认关：溯源清单不进生成 prompt（trace 仍可有）。"""
    try:
        from scribe3.quality_enablement_flags import provenance_in_prompt_enabled as _f
        return bool(_f())
    except Exception:
        v = (get_flag("SCRIBE3_PROVENANCE_IN_PROMPT") or "0").strip().lower()
        return v in ("1", "true", "yes", "on")


def generation_forbidden_source_kinds() -> tuple[str, ...]:
    """写路径禁用 source_kind；默认含 provenance（双保险）。调试旗可恢复旧行为。"""
    if provenance_in_prompt_enabled():
        return ()
    return ("provenance",)

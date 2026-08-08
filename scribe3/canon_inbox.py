"""待确认设定收件箱：标签、噪声判定、详情 enrichment。"""
from __future__ import annotations

import re
from typing import Any

MODULE_LABELS = {
    "character": "角色",
    "faction": "势力",
    "item": "物件",
    "term": "术语",
    "world_rule": "世界规则",
    "relation": "关系",
    "promise": "伏笔",
    "motif": "母题",
    "fact": "事实",
    "knowledge": "知识",
    "char_state": "弧光状态",
    "intent": "意图",
}
OP_LABELS = {
    "add": "新建",
    "patch": "修改",
    "plant": "埋设",
    "advance": "推进",
    "touch": "触碰",
    "deprecate": "废弃",
}
FIELD_LABELS = {
    "fear": "恐惧",
    "appearance": "外形",
    "personality_detail": "性格",
    "surface_goal": "表层目标",
    "deep_need": "深层需要",
    "backstory": "身世",
    "note": "备注",
    "description": "描述",
    "definition": "定义",
    "cost": "代价",
    "name": "名称",
}
SOURCE_LABELS = {
    "prose_finalize": "正文定稿",
    "discussion": "讨论",
    "ingest": "ingest",
    "verify": "验证",
    "hybrid": "混合",
}
EXTRACTOR_LABELS = {
    "marker": "标记",
    "llm": "LLM",
    "heuristic": "启发式",
    "hybrid": "混合",
    "ingest_resolve_char": "ingest人物",
}

# 连接残片 / 过短势力名等
_NOISE_FACTION_RE = re.compile(
    r"^(是|会|的|了|在|有|和|与|把|被|将|从|向|对|给|让|到|又|也|都|还|就|才|却|已|未|不|没)"
    r"|替高门|原本是|是会|中人$|^其|^此|^该"
    r"|推门|开门|关门|掩门|闩门|从门|到门|在门|的门|角门|客店门"
    r"|一会$|好一会|了一会|看一会|躺了一会|沉默了一会"
    r"|鞋帮|船帮"
)
_NOISE_PERSON_RE = re.compile(
    r"^(我|你|他|她|它|这|那|人|谁)"
    r"|来看|写上|替了|莫应|看这|看那|灯芯$|之来$"
)
_DOORISH = re.compile(
    r"(推|开|关|掩|闩|站|走|到|从|朝).{0,4}门$|门$|的门$|半掩|角门|客店"
)
_ORG_OK_SUFFIX = ("门", "帮", "教", "宗", "盟", "阁", "堂", "派", "府", "司", "卫", "营")


def display_name(item: dict) -> str:
    t = (item.get("target") or "").strip()
    bare = t.split(":")[-1] if t else ""
    after = item.get("after")
    if isinstance(after, dict) and after.get("name"):
        return str(after["name"])
    return bare or t or "（未命名）"


def human_title(item: dict) -> str:
    mod = MODULE_LABELS.get((item.get("module") or "").lower(), item.get("module") or "设定")
    op = OP_LABELS.get((item.get("op") or "patch").lower(), item.get("op") or "变更")
    name = display_name(item)
    field = item.get("field")
    fl = FIELD_LABELS.get(field, field) if field else None
    if fl:
        return f"{op} · {mod}「{name}」· {fl}"
    return f"{op} · {mod}「{name}」"


def is_noise_heuristic(item: dict) -> bool:
    """服务端权威噪声：启发式/残片势力/假人名。

    marker 仍豁免。hybrid/heuristic 的裸 add 默认从严：像口语/门板/一会 一律噪声，
    避免 conf 被误写成 1.0 时仍灌满收件箱。
    """
    ext = (item.get("extractor") or "").lower()
    mod = (item.get("module") or "").lower()
    conf = float(item.get("confidence") or 1.0)
    name = display_name(item)
    op = (item.get("op") or "add").lower()
    has_field = bool(item.get("field"))
    # 明确 marker / 结构化字段 patch 不进噪声
    if ext in ("marker",):
        return False
    if has_field and ext in ("llm", "llm_v1", "marker"):
        return False

    bare_add = (not has_field) and op in ("add", "plant")

    # —— 势力残片（主噪声源）——
    if mod == "faction":
        if len(name) < 2:
            return True
        if _NOISE_FACTION_RE.search(name):
            return True
        if name.endswith("会"):  # 一会/看一会 历史脏数据
            return True
        if _DOORISH.search(name):
            return True
        if "替" in name and "门" in name:
            return True
        if name in ("高门", "低门", "正门", "侧门", "山门", "家门", "师门", "正教", "旁门"):
            return True
        # 无组织后缀 / 过长叙事句
        if not name.endswith(_ORG_OK_SUFFIX):
            return True
        if len(name) > 6:
            return True
        # 代词/动词起头
        if name[0] in "是会的了在有和与把被将从向对给让到又也都还就才却他她我你这那其此该小等看躺走推开朝":
            return True
        if bare_add and ext in ("heuristic", "hybrid", "ingest_resolve_char", "") and conf < 0.85:
            # 低置信裸势力默认噪声；真组织应靠 marker/LLM 高置信或人标
            if len(name) <= 3 and not name.endswith(("宗", "盟", "派", "府", "阁", "教")):
                return True
        if bare_add and conf >= 0.99 and ext in ("hybrid", "heuristic", ""):
            # 落库时未降权的 conf=1 裸 add：仍按噪声处理（历史数据）
            if not name.endswith(("宗", "盟", "派", "府", "阁")) or len(name) < 3:
                # 收灯一脉 / 高门代还 等真名通常 ≥4 或带专名感；纯 X门 多为脏
                if len(name) <= 4 and name.endswith("门") and not any(
                    k in name for k in ("高门代", "收灯", "代还", "一脉", "债")
                ):
                    return True
        # 建筑「堂」口语（正堂/前堂 ≠ 组织）
        if name in ("正堂", "前堂", "中堂", "后堂", "大堂", "厅堂"):
            return True
        if any(x in name for x in ("正堂", "前堂", "回到", "照得", "听见", "忽然")):
            return True
        # 师门教 等残片
        if name in ("师门教", "旁门左道") or (name.endswith("教") and len(name) <= 3 and name[0] in "他她我你师"):
            return True
        return False

    # —— 假人名（叫我来看这 / 叫写上灯芯）——
    if mod == "character" and bare_add:
        if _NOISE_PERSON_RE.search(name):
            return True
        if name in ("什么", "怎么", "哪里", "谁人", "几个"):
            return True
        if name and name[-1] in "来去上下过了着的地得句么":
            return True
        if any(x in name for x in ("来看", "写上", "替了", "灯芯", "莫应", "几句")):
            return True
        if len(name) < 2:
            return True
        if name[0] in "了的在把被将从向":
            return True
        if conf < 0.45 and ext in ("heuristic", "hybrid", ""):
            return True
        # conf=1 的 hybrid 裸 add 人名：无字段则倾向噪声（真角色多有 patch 或 marker）
        if conf >= 0.99 and ext in ("hybrid", "heuristic", "") and not has_field:
            # 已知像真名的短 2–3 字放行（沈砚之），其余口语残片拒
            if len(name) >= 4 or name[0] in "我你他她这那人了":
                return True

    # —— 假物件：动词碎片 ——
    if mod == "item" and bare_add:
        if len(name) < 2 or name[0] in "去来到把被将在":
            return True
        if name in ("去道", "来道", "说道", "问道"):
            return True
        if name.endswith(("了", "着", "的", "过")) and len(name) <= 3:
            return True

    # —— 通用：低置信启发式 ——
    if conf < 0.45 and ext in ("heuristic", "hybrid", "") and bare_add:
        return True
    return False


def annotate_flags(item: dict) -> dict:
    out = dict(item)
    flags = list(out.get("flags") or [])
    if is_noise_heuristic(out) and "noise_heuristic" not in flags:
        flags.append("noise_heuristic")
    out["flags"] = flags
    out["is_noise"] = "noise_heuristic" in flags
    out["title"] = human_title(out)
    out["labels"] = {
        "module": MODULE_LABELS.get((out.get("module") or "").lower(), out.get("module")),
        "op": OP_LABELS.get((out.get("op") or "").lower(), out.get("op")),
        "field": FIELD_LABELS.get(out.get("field") or "", out.get("field")),
        "source": SOURCE_LABELS.get((out.get("source") or "").lower(), out.get("source")),
        "extractor": EXTRACTOR_LABELS.get((out.get("extractor") or "").lower(), out.get("extractor")),
    }
    return out


def filter_items(
    items: list[dict],
    *,
    source: str | None = None,
    extractor: str | None = None,
    risk: str | None = None,
    min_confidence: float | None = None,
    noise: str | None = None,  # only|exclude|all
    priority: str | None = None,  # suggested|all
) -> list[dict]:
    out = []
    for raw in items:
        it = annotate_flags(raw)
        if source and (it.get("source") or "") != source:
            continue
        if extractor and (it.get("extractor") or "") != extractor:
            continue
        if risk and (it.get("risk") or "") != risk:
            continue
        if min_confidence is not None and float(it.get("confidence") or 0) < min_confidence:
            continue
        is_n = it.get("is_noise")
        if noise == "only" and not is_n:
            continue
        if noise == "exclude" and is_n:
            continue
        if priority == "suggested":
            # 建议优先：非噪声 + (marker/llm / 字段 patch / 高置信且非裸 heuristic)
            ext = (it.get("extractor") or "").lower()
            conf = float(it.get("confidence") or 0)
            op = (it.get("op") or "add").lower()
            bare_add = (not it.get("field")) and op in ("add", "plant")
            if is_n:
                continue
            if it.get("field") or ext in ("marker", "llm", "llm_v1"):
                out.append(it)
                continue
            if bare_add and ext in ("heuristic", "hybrid", "ingest_resolve_char", ""):
                # 裸启发式进「全部」不进建议；除非置信极高且像专名（≥0.9 且短名）
                if conf < 0.9:
                    continue
                nm = display_name(it)
                if len(nm) > 6 or len(nm) < 2:
                    continue
            elif conf < 0.8 and it.get("risk") != "high":
                continue
        out.append(it)
    return out


def facets(items: list[dict]) -> dict[str, Any]:
    by_mod: dict[str, int] = {}
    by_src: dict[str, int] = {}
    by_ext: dict[str, int] = {}
    noise_n = 0
    for it in items:
        a = annotate_flags(it)
        m = a.get("module") or "other"
        by_mod[m] = by_mod.get(m, 0) + 1
        s = a.get("source") or "unknown"
        by_src[s] = by_src.get(s, 0) + 1
        e = a.get("extractor") or "unknown"
        by_ext[e] = by_ext.get(e, 0) + 1
        if a.get("is_noise"):
            noise_n += 1
    suggested = len(filter_items(items, priority="suggested", noise="exclude"))
    return {
        "by_module": by_mod,
        "by_source": by_src,
        "by_extractor": by_ext,
        "noise_count": noise_n,
        "suggested_priority_count": suggested,
        "total": len(items),
    }


def enrich_candidate(st: Any, item: dict) -> dict[str, Any]:
    """组装详情：diff、codex 相似、章摘录。"""
    a = annotate_flags(item)
    before, after = a.get("before"), a.get("after")
    op = (a.get("op") or "patch").lower()
    kind = "add" if op in ("add", "plant") or before in (None, "", {}, []) else "patch"
    diff = {"kind": kind, "before": before, "after": after, "field": a.get("field")}

    # codex match (lightweight)
    similar = []
    exists = False
    name = display_name(a)
    mod = (a.get("module") or "").lower()
    try:
        if mod == "character" and hasattr(st, "characters"):
            chars = st.characters() if callable(st.characters) else []
            for c in chars or []:
                cn = (getattr(c, "name", None) or "").strip()
                cid = str(getattr(c, "id", "") or "")
                if cn == name or cid.endswith(name):
                    exists = True
                    similar.append({"id": cid, "name": cn, "score": 1.0})
                elif cn and (cn in name or name in cn) and len(name) >= 2:
                    similar.append({"id": cid, "name": cn, "score": 0.7})
        if mod == "faction" and hasattr(st, "list_factions"):
            for f in st.list_factions() or []:
                fn = (f.get("name") if isinstance(f, dict) else None) or ""
                if fn == name:
                    exists = True
                    similar.append({"id": fn, "name": fn, "score": 1.0})
        if mod == "world_rule" and hasattr(st, "list_world_rules"):
            for r in st.list_world_rules() or []:
                rn = (r.get("name") if isinstance(r, dict) else None) or ""
                if rn == name:
                    exists = True
                    similar.append({"id": rn, "name": rn, "score": 1.0})
    except Exception:
        pass

    chapter_excerpt = None
    seq = a.get("seq")
    evidence = (a.get("evidence") or "").strip()
    if seq is not None and hasattr(st, "get_chapter"):
        try:
            ch = st.get_chapter(int(seq)) or {}
            prose = ch.get("prose") or ""
            snippet = ""
            highlight = None
            if evidence and prose:
                idx = prose.find(evidence[:40] if len(evidence) > 40 else evidence)
                if idx < 0:
                    # try short core
                    core = re.sub(r"\s+", "", evidence)[:12]
                    p2 = re.sub(r"\s+", "", prose)
                    # fallback window by first CJK chars
                    for n in range(min(8, len(evidence)), 3, -1):
                        frag = evidence[:n]
                        j = prose.find(frag)
                        if j >= 0:
                            idx = j
                            break
                if idx >= 0:
                    lo = max(0, idx - 40)
                    hi = min(len(prose), idx + max(len(evidence), 40) + 40)
                    snippet = prose[lo:hi]
                    highlight = [idx - lo, idx - lo + min(len(evidence), hi - idx)]
                else:
                    snippet = prose[:160]
            elif prose:
                snippet = prose[:160]
            chapter_excerpt = {
                "seq": int(seq),
                "title": ch.get("title"),
                "snippet": snippet,
                "highlight": highlight,
                "located": highlight is not None,
            }
        except Exception:
            chapter_excerpt = {"seq": seq, "snippet": "", "located": False}

    # 合并候选项：同 module 下可选 target 列表（最多 40）
    merge_options: list[dict] = []
    try:
        if mod == "character" and hasattr(st, "characters"):
            chars = st.characters() if callable(st.characters) else []
            for c in chars or []:
                cn = (getattr(c, "name", None) or "").strip()
                cid = str(getattr(c, "id", "") or "")
                if cn or cid:
                    merge_options.append({
                        "target": cid if cid.startswith("role:") else f"role:{cn or cid.split(':')[-1]}",
                        "label": cn or cid,
                    })
        elif mod == "faction" and hasattr(st, "list_factions"):
            for f in st.list_factions() or []:
                fn = (f.get("name") if isinstance(f, dict) else None) or ""
                if fn:
                    merge_options.append({"target": fn, "label": fn})
        elif mod == "world_rule" and hasattr(st, "list_world_rules"):
            for r in st.list_world_rules() or []:
                rn = (r.get("name") if isinstance(r, dict) else None) or ""
                if rn:
                    merge_options.append({"target": rn, "label": rn})
        elif mod == "item" and hasattr(st, "list_items"):
            for it in st.list_items() or []:
                n = (it.get("name") if isinstance(it, dict) else None) or ""
                if n:
                    merge_options.append({"target": n, "label": n})
        elif mod == "term" and hasattr(st, "list_terms"):
            for it in st.list_terms() or []:
                n = (it.get("name") if isinstance(it, dict) else None) or ""
                if n:
                    merge_options.append({"target": n, "label": n})
    except Exception:
        pass
    # 去重
    seen_t = set()
    uniq_opts = []
    for o in merge_options:
        t = o.get("target")
        if t and t not in seen_t:
            seen_t.add(t)
            uniq_opts.append(o)
    merge_options = uniq_opts[:40]

    group_key = f"{mod}|{(a.get('target') or '').split(':')[-1]}"

    return {
        "item": a,
        "title": a["title"],
        "labels": a["labels"],
        "diff": diff,
        "codex_match": {"exists": exists, "similar": similar[:8]},
        "chapter_excerpt": chapter_excerpt,
        "impact": a.get("impact") or {},
        "is_noise": a.get("is_noise"),
        "merge_options": merge_options,
        "group_key": group_key,
        "modules_enum": list(MODULE_LABELS.keys()),
        "module_labels": MODULE_LABELS,
    }

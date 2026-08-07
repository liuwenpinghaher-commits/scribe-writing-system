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
)


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
    """服务端权威噪声：启发式/残片势力等。标记与 LLM 默认不标噪声。"""
    ext = (item.get("extractor") or "").lower()
    mod = (item.get("module") or "").lower()
    conf = float(item.get("confidence") or 1.0)
    name = display_name(item)
    # 明确 marker 不进噪声
    if ext in ("marker", "llm", "llm_v1"):
        return False
    if conf < 0.45 and ext in ("heuristic", "hybrid", ""):
        if mod == "faction" or len(name) < 2:
            return True
    if mod == "faction" and ext in ("heuristic", "hybrid", "ingest_resolve_char", ""):
        if len(name) < 2:
            return True
        if _NOISE_FACTION_RE.search(name):
            return True
        # 过长短语不像专名
        if len(name) > 8 and not name.endswith(("门", "帮", "会", "教", "宗", "盟", "阁", "堂")):
            return True
        # 「…替高门」类
        if "替" in name and "门" in name and len(name) > 4:
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
            # 建议优先：非噪声且 (置信≥0.8 或 marker/llm 或 high risk 真变更)
            ext = (it.get("extractor") or "").lower()
            conf = float(it.get("confidence") or 0)
            if is_n:
                continue
            if not (
                conf >= 0.8
                or ext in ("marker", "llm", "llm_v1")
                or (it.get("risk") == "high" and ext != "heuristic")
                or it.get("field")  # 字段 patch 优先于裸 add 噪声
            ):
                # 仍允许非 heuristic 的 add
                if ext in ("heuristic", "") and (it.get("op") or "add") == "add":
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

    return {
        "item": a,
        "title": a["title"],
        "labels": a["labels"],
        "diff": diff,
        "codex_match": {"exists": exists, "similar": similar[:8]},
        "chapter_excerpt": chapter_excerpt,
        "impact": a.get("impact") or {},
        "is_noise": a.get("is_noise"),
    }

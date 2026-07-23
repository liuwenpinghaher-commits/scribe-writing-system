"""素材召回引擎(纯函数为主):聚焦 query / 强度加权 / 门控 / LLM 重排理由 / block 渲染。

store.material_recall 做三通道 DB 召回(语义 HNSW + 全文 BM25 + 图),这里做其上的编排与
渲染——纯函数便于测试。参考语义:素材是"借鉴参考"非"必守事实",注入段明确反照搬边界。
"""
from __future__ import annotations

import json
import math


def extract_focus_query(ctx: dict, max_len: int = 80) -> str:
    """从写作上下文提取聚焦 query(防长上下文稀释:不整段拼,取关键实体 + beats 动作核心)。"""
    parts: list[str] = []
    parts.extend((ctx.get("mentioned") or [])[:3])   # 提及实体优先
    beats = ctx.get("beats") or []
    if beats:
        first = beats[0] if isinstance(beats[0], str) else str(beats[0])
        parts.append(first)
    return " ".join(parts).strip()[:max_len]


def _strength_factor(c: dict) -> float:
    """记忆强度因子:pinned 恒高;recall_count 对数温和加权(防马太效应)。"""
    if c.get("pinned"):
        return 2.0
    return 1.0 + math.log1p(c.get("recall_count") or 0) * 0.1


def apply_strength(cands: list[dict]) -> list[dict]:
    """按 score × 强度因子重排(pinned 优先浮现)。"""
    for c in cands:
        c["_weighted"] = (c.get("score") or 0.0) * _strength_factor(c)
    return sorted(cands, key=lambda c: -c.get("_weighted", 0.0))


def gate(cands: list[dict], budget_chars: int = 800) -> list[dict]:
    """门控:空候选直接返回空;否则按强度分排序并按字符预算裁剪,避免无意义 rerank。

    budget_chars 按每条摘要/正文估计占用(上限 ~160 字/条 + 固定开销),
    至少保留 1 条高分候选(有料时)。
    """
    if not cands:
        return []
    ranked = apply_strength([dict(c) for c in cands])
    if budget_chars is None or budget_chars <= 0:
        return ranked
    # 预留反照搬头约 80 字
    head_reserve = 80
    remain = max(40, int(budget_chars) - head_reserve)
    out: list[dict] = []
    used = 0
    for c in ranked:
        excerpt = (c.get("summary") or c.get("body") or "")[:120]
        est = min(160, 24 + len(c.get("title") or "") + len(excerpt)
                  + (len(c.get("reason") or "") if c.get("reason") else 0))
        if out and used + est > remain:
            break
        out.append(c)
        used += est
    return out or ranked[:1]


def rerank_materials(cands: list[dict], query: str, llm, k: int = 5) -> list[dict]:
    """LLM 重排 + 理由生成;失败降级 RRF 顺序 + 机械 reason(不抛)。llm(prompt)->str。"""
    if not cands:
        return []
    try:
        listing = "\n".join(
            f'{c["material_id"]}: {c.get("title", "")} — '
            f'{(c.get("summary") or c.get("body") or "")[:80]}'
            for c in cands)
        prompt = (f"当前写作场景:{query}\n候选参考素材:\n{listing}\n"
                  f"选出最值得当前场景借鉴的(最多 {k} 条),每条给一句'为什么值得借鉴'的理由。"
                  f'只返回 JSON 数组:[{{"id":"...","reason":"..."}}]')
        raw = llm(prompt)
        picked = json.loads(raw[raw.find("["):raw.rfind("]") + 1])
        by_id = {c["material_id"]: c for c in cands}
        out = [{**by_id[p["id"]], "reason": p.get("reason") or "相关"}
               for p in picked[:k] if p.get("id") in by_id]
        if out:
            return out
    except Exception:
        pass
    return [{**c, "reason": c.get("reason") or "检索命中"} for c in cands[:k]]


# 参考维度 → 差异化借鉴指令(风格借语感、剧情借结构不搬情节、手法借技法)
_DIM_HINT = {"风格": "借鉴其语感与节奏", "剧情": "借鉴其结构不搬情节",
             "桥段": "借鉴其结构不搬情节", "手法": "借鉴其技法", "情绪": "借鉴其情绪调度",
             "世界观": "借鉴其设定骨架不搬专名"}


def render_material_block(cands: list[dict], budget_chars: int = 800) -> str:
    """渲染"参考记忆"段:反照搬头 + 每条(维度化借鉴指令 + **优先 summary** + reason),字数预算裁剪。"""
    if not cands:
        return ""
    head = ("【参考记忆·借鉴非照搬】以下是与本环节相关的素材记忆,借鉴其手法/风格/思路,"
            "非必守事实;反抄边界:原文专名/事件顺序/标志台词/独特设定不可照搬,迁移至少改 3 项。\n")
    lines, used = [head], len(head)
    for c in cands:
        dims = c.get("ref_tags") or []
        hint = next((_DIM_HINT[d] for d in dims if d in _DIM_HINT), "借鉴其思路")
        # 优先 summary(手法摘要);无则 body 截断
        excerpt = (c.get("summary") or "").strip() or (c.get("body") or "")[:120]
        excerpt = excerpt[:120]
        line = f"- 【{'/'.join(dims) or '参考'}·{hint}】{c.get('title', '')}:{excerpt}"
        if c.get("reason"):
            line += f"(为何参考:{c['reason']})"
        line += "\n"
        if used + len(line) > budget_chars:
            break
        lines.append(line)
        used += len(line)
    return "".join(lines)


def emotion_target_from_materials(materials: list[dict], target_emotion: str) -> list[dict]:
    """从 emotion_module 素材中按目标情绪筛选(body/summary JSON 或纯文本子串)。

    返回匹配的素材行(保留 material 字段),供 brief/context 调用。
    """
    if not (target_emotion or "").strip():
        return []
    te = target_emotion.strip()
    hits = []
    for m in materials or []:
        if (m or {}).get("kind") != "emotion_module":
            continue
        raw = m.get("summary") or m.get("body") or m.get("content") or ""
        emotion = ""
        try:
            card = json.loads(raw) if isinstance(raw, str) and raw.strip().startswith("{") else None
            if isinstance(card, dict):
                emotion = str(card.get("emotion") or "")
        except (TypeError, ValueError):
            card = None
        blob = f"{emotion} {m.get('title') or ''} {raw}"
        if te in blob or (emotion and (te in emotion or emotion in te)):
            hits.append(m)
    return hits

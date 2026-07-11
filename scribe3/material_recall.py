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
    """门控:空候选直接返回空——不触发下游 LLM 重排/注入(空库/无关时零开销)。"""
    return cands if cands else []


def rerank_materials(cands: list[dict], query: str, llm, k: int = 5) -> list[dict]:
    """LLM 重排 + 理由生成;失败降级 RRF 顺序 + 机械 reason(不抛)。llm(prompt)->str。"""
    if not cands:
        return []
    try:
        listing = "\n".join(
            f'{c["material_id"]}: {c.get("title", "")} — {(c.get("body") or "")[:80]}'
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
             "桥段": "借鉴其结构不搬情节", "手法": "借鉴其技法", "情绪": "借鉴其情绪调度"}


def render_material_block(cands: list[dict], budget_chars: int = 800) -> str:
    """渲染"参考记忆"段:反照搬头 + 每条(维度化借鉴指令 + 摘要 + reason),字数预算裁剪。"""
    if not cands:
        return ""
    head = ("【参考记忆·借鉴非照搬】以下是与本环节相关的素材记忆,借鉴其手法/风格/思路,"
            "非必守事实;反抄边界:原文专名/事件顺序/标志台词/独特设定不可照搬,迁移至少改 3 项。\n")
    lines, used = [head], len(head)
    for c in cands:
        dims = c.get("ref_tags") or []
        hint = next((_DIM_HINT[d] for d in dims if d in _DIM_HINT), "借鉴其思路")
        excerpt = (c.get("summary") or c.get("body") or "")[:120]
        line = f"- 【{'/'.join(dims) or '参考'}·{hint}】{c.get('title', '')}:{excerpt}"
        if c.get("reason"):
            line += f"(为何参考:{c['reason']})"
        line += "\n"
        if used + len(line) > budget_chars:
            break
        lines.append(line)
        used += len(line)
    return "".join(lines)

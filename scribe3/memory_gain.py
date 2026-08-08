"""记忆质量 D7：记忆「获得感」——用过什么可见 + 有/无对照协议辅助。

不做：把通/绿当 9.5。本模块提供：
  · 从 envelope / trace.context 生成 **无秘密正文** 的 usage_digest（人话摘要）
  · 对照实验协议元数据（脚本与文档共用）
"""
from __future__ import annotations

from typing import Any


# 块名 → 作者可读标签
_BLOCK_LABELS = {
    "focus": "此刻焦点",
    "global": "全书稳定层（北极星/铁律/角色）",
    "canonical": "正典与戏剧必需",
    "recent": "近期过程/工作摘要",
    "procedural": "工艺与作者偏好",
    "reference": "参考素材（借鉴非事实）",
    "uncertainty": "不确定/冲突",
    "provenance": "溯源清单",
}


def _safe_source_label(source_id: str) -> str:
    sid = (source_id or "").strip()
    if not sid:
        return "（未命名来源）"
    # 不展开 value，只展示 id 形态
    if sid.startswith("must_link"):
        return "戏剧必需锚"
    if sid.startswith("intent:"):
        return "作品意图/铁律"
    if sid.startswith("promise") or "promise" in sid:
        return "开放伏笔"
    if sid.startswith("fact:"):
        return f"正典命题 {sid}"
    if sid.startswith("role:") or "character" in sid:
        return f"角色 {sid}"
    if "author_constraint" in sid or "铁律" in sid:
        return "作者铁律"
    return sid[:64]


def build_usage_digest_from_manifest(manifest: dict | None) -> dict[str, Any]:
    """从 envelope_trace_manifest 形状生成作者可见摘要（无块正文、无 secret value）。"""
    m = manifest or {}
    blocks_in = m.get("blocks") or []
    lines: list[str] = []
    by_block: list[dict[str, Any]] = []
    total_sources = 0
    for b in blocks_in:
        if not isinstance(b, dict):
            continue
        name = b.get("name") or ""
        ids = list(b.get("source_ids") or [])
        masked = set(b.get("masked_source_ids") or [])
        if not ids and not b.get("token_estimate"):
            continue
        label = _BLOCK_LABELS.get(name, name)
        shown = []
        for sid in ids[:12]:
            tag = _safe_source_label(str(sid))
            if sid in masked:
                tag += "（已屏蔽私密）"
            shown.append(tag)
        total_sources += len(ids)
        if shown or b.get("token_estimate"):
            lines.append(
                f"· {label}：{len(ids)} 条来源"
                + (f"，约 {b.get('token_estimate')} token" if b.get("token_estimate") else "")
            )
            if shown:
                lines.append("  " + "；".join(shown[:8]))
        by_block.append({
            "block": name,
            "label": label,
            "source_count": len(ids),
            "token_estimate": b.get("token_estimate"),
            "source_labels": shown,
        })
    omitted = m.get("omitted") or []
    omit_n = len(omitted) if isinstance(omitted, list) else 0
    summary = (
        f"本轮写作上下文用到约 {total_sources} 条记忆/正典来源"
        + (f"，另有 {omit_n} 条因预算或冲突未注入" if omit_n else "")
        + "。"
    )
    if not lines:
        summary = "本轮未记录到可展示的上下文块（可能未开 fabric 或尚未编译 envelope）。"
    return {
        "summary": summary,
        "lines": lines,
        "by_block": by_block,
        "total_sources": total_sources,
        "omitted_count": omit_n,
        "envelope_hash": m.get("envelope_hash"),
        "human_readable": summary + ("\n" + "\n".join(lines) if lines else ""),
    }


def comparison_protocol() -> dict[str, Any]:
    """D7 有/无记忆对照实验协议（质量 9.5 用人评，脚本只固定流程）。"""
    return {
        "name": "memory_gain_ab_v1",
        "goal": "证明有记忆时成稿更连贯、设定回指更强、作者更少粘贴设定",
        "setup": [
            "同一 book slug、同一章 synopsis、同一模型与 max_tokens",
            "A 组：MEMORY_FABRIC 开 + must-link + 铁律注入（正常产品）",
            "B 组：显式关 fabric 且/或 forbidden 掉 canonical/recent（仅测试 env）",
            "作者指令仅给冲突与 POV（SCRIBE3_MEMORY_STEER_MODE=minimal）",
            "禁止作者粘贴全书设定；若 detect_author_restated_canon 则作废该次",
        ],
        "scores": [
            {"key": "coherence", "label": "跨句/跨段连贯", "scale": "1-5"},
            {"key": "canon_echo", "label": "设定回指自然度", "scale": "1-5"},
            {"key": "contradiction", "label": "自相矛盾少（分高=矛盾少）", "scale": "1-5"},
            {"key": "author_effort", "label": "作者少重复设定（分高=更省力）", "scale": "1-5"},
        ],
        "pass_rule": (
            "A 组三项（coherence/canon_echo/contradiction）均 ≥4.5，"
            "且相对 B 组平均领先 ≥1.5；否则 D7 不得报 ≥9.0"
        ),
        "artifacts": [
            "a_prose.md", "b_prose.md",
            "a_usage_digest.json", "b_usage_digest.json",
            "scores.json", "00-author-path.md",
        ],
    }

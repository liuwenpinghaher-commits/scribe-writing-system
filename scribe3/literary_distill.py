"""文学蒸馏原型（P2 · O-11 · 无 LLM 启发式）。

把多段 recap 收成可审计决策要点；始终带 raw 以便还原。
**禁止**以 tokens_saved / 成本作控制开关。
``SCRIBE3_LITERARY_DISTILL`` 默认关；关时函数仍可调用（纯原型）。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import os
import re
from typing import Any

# 控制面明确排除的 KPI 名（测试可扫此集合）
DISTILL_FORBIDDEN_KPIS: frozenset[str] = frozenset({
    "tokens_saved",
    "token_saved",
    "cost_usd",
    "cost_cny",
    "api_cost",
})


def literary_distill_enabled() -> bool:
    raw = (get_flag("SCRIBE3_LITERARY_DISTILL") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def _classify_bullet(para: str) -> str:
    """启发式标签：paid_off | open_cost | attitude | beat。"""
    p = para.lower()
    if any(k in para for k in ("代价", "成本", "失去", "牺牲", "伤口", "cost")):
        return "open_cost"
    if any(k in para for k in ("态度", "心境", "决定", "不再", "终于", "改变", "决心")):
        return "attitude"
    if any(k in para for k in ("解决", "了结", "还清", "兑现", "落幕", "paid", "收束")):
        return "paid_off"
    if any(k in p for k in ("conflict", "对抗", "冲突", "对峙")):
        return "paid_off"
    return "beat"


def distill_mode() -> str:
    """GAP-10：heuristic | llm | token（默认 heuristic）。"""
    raw = (get_flag("SCRIBE3_DISTILL_MODE") or "heuristic").strip().lower()
    if raw in ("heuristic", "llm", "token"):
        return raw
    return "heuristic"


def distill_heuristic(recap: str, *, max_bullets: int = 12) -> dict[str, Any]:
    """纯启发式路径（原 literary_distill 核心）。"""
    raw = recap or ""
    paras = _split_paragraphs(raw)
    if not paras and raw.strip():
        paras = [raw.strip()]
    bullets: list[dict[str, Any]] = []
    for i, para in enumerate(paras[: max(1, int(max_bullets))]):
        line = re.sub(r"\s+", " ", para).strip()
        if len(line) > 160:
            line = line[:157] + "…"
        kind = _classify_bullet(para)
        bullets.append({"index": i, "kind": kind, "text": line})
    return {
        "bullets": bullets,
        "raw": raw,
        "mode": "heuristic",
        "audit": {
            "paragraph_count": len(paras),
            "bullet_count": len(bullets),
            "source": "literary_distill.heuristic_v0",
            "revert": "use field raw",
            "not_a_kpi": "tokens_saved",
            "forbidden_kpis": sorted(DISTILL_FORBIDDEN_KPIS),
        },
    }


def distill_llm(recap: str, *, max_bullets: int = 12, complete_fn=None) -> dict[str, Any]:
    """GAP-10 Level-2：优先 complete_fn（Hermes）；无网时句级抽取压缩（非段落启发式）。"""
    raw = recap or ""
    if complete_fn is not None:
        try:
            prompt = (
                f"将以下文学复盘压缩为不超过{max_bullets}条要点，每条一行：\n\n{raw[:4000]}"
            )
            out_text = str(complete_fn(prompt) or "")
            lines = [ln.strip(" -•\t") for ln in out_text.splitlines() if ln.strip()]
            bullets = [
                {"index": i, "kind": "beat", "text": ln[:160]}
                for i, ln in enumerate(lines[: max(1, int(max_bullets))])
            ]
            if bullets:
                return {
                    "bullets": bullets,
                    "raw": raw,
                    "mode": "llm",
                    "audit": {
                        "source": "literary_distill.llm_complete_fn",
                        "bullet_count": len(bullets),
                        "paragraph_count": len(_split_paragraphs(raw)),
                        "not_a_kpi": "tokens_saved",
                        "forbidden_kpis": sorted(DISTILL_FORBIDDEN_KPIS),
                    },
                }
        except Exception:
            pass
    # 句级抽取（不同于 heuristic 的段落分类）
    sentences = re.split(r"[。！？!?\n]+", raw)
    sentences = [s.strip() for s in sentences if s and s.strip()]
    # 按信息密度：保留含动词/代价词的短句
    picked: list[str] = []
    for s in sentences:
        if any(k in s for k in ("因", "但", "却", "终于", "必须", "代价", "决定", "发现")):
            picked.append(s)
        elif len(s) >= 12 and len(picked) < max_bullets:
            picked.append(s)
        if len(picked) >= max_bullets:
            break
    if not picked:
        picked = sentences[:max_bullets] or [raw[:120]]
    bullets = [
        {"index": i, "kind": "sentence", "text": re.sub(r"\s+", " ", s)[:160]}
        for i, s in enumerate(picked[:max_bullets])
    ]
    joined = " ".join(b["text"] for b in bullets)
    return {
        "bullets": bullets,
        "raw": raw,
        "mode": "llm",
        "audit": {
            "source": "literary_distill.llm_sentence_extract_v1",
            "bullet_count": len(bullets),
            "sentence_count": len(sentences),
            "compression_ratio_est": round(len(joined) / max(1, len(raw)), 3) if raw else 0.0,
            "not_a_kpi": "tokens_saved",
            "forbidden_kpis": sorted(DISTILL_FORBIDDEN_KPIS),
            "note": "sentence extract offline; pass complete_fn for Hermes",
        },
    }


def distill_token(recap: str, *, max_bullets: int = 12) -> dict[str, Any]:
    """GAP-10 Level-3：token 级粗压缩（无 llmlingua 依赖时用字级截断）。"""
    raw = recap or ""
    # 目标约 40% 长度
    keep = max(40, int(len(raw) * 0.4))
    compressed = raw[:keep] + ("…" if len(raw) > keep else "")
    base = distill_heuristic(compressed, max_bullets=max_bullets)
    base["mode"] = "token"
    base["raw"] = raw
    base["compressed_preview"] = compressed
    base["audit"] = {
        **(base.get("audit") or {}),
        "source": "literary_distill.token_trunc_v0",
        "ratio": round(len(compressed) / max(1, len(raw)), 3),
    }
    return base


def literary_distill(recap: str, *, max_bullets: int = 12) -> dict[str, Any]:
    """多段 recap → 结构化 bullets + raw/audit（按 SCRIBE3_DISTILL_MODE 分流）。

    控制路径不读 tokens_saved；audit 标明 not_a_kpi。
    """
    mode = distill_mode()
    if mode == "llm":
        out = distill_llm(recap, max_bullets=max_bullets)
    elif mode == "token":
        out = distill_token(recap, max_bullets=max_bullets)
    else:
        out = distill_heuristic(recap, max_bullets=max_bullets)
    out.setdefault("control", {})
    out["control"] = {
        "flag": literary_distill_enabled(),
        "mode": mode,
    }
    # preserve previous shape for callers expecting nested control.flag only
    if "audit" in out and "forbidden_kpis" not in out["audit"]:
        out["audit"]["forbidden_kpis"] = sorted(DISTILL_FORBIDDEN_KPIS)
    return out




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
    "global": "全书稳定层（作品意图/铁律/角色）",
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
    # Wave-A3：互斥裁掉条数（manifest.conflicts_dropped 或 omitted.reason 含 conflict）
    conflicts_dropped = 0
    try:
        if m.get("conflicts_dropped") is not None:
            conflicts_dropped = max(0, int(m.get("conflicts_dropped") or 0))
    except (TypeError, ValueError):
        conflicts_dropped = 0
    if isinstance(omitted, list):
        for o in omitted:
            if not isinstance(o, dict):
                continue
            reason = str(o.get("reason") or "").lower()
            if "conflict" in reason or "互斥" in reason or "injection_conflict" in reason:
                conflicts_dropped += 1
    conflict_note = ""
    if conflicts_dropped:
        conflict_note = f"，记忆已裁掉 {conflicts_dropped} 条互斥/冲突事实"
        lines.append(f"· 冲突消解：裁掉 {conflicts_dropped} 条（单真注入，防双真毒化）")
    summary = (
        f"本轮写作上下文用到约 {total_sources} 条记忆/正典来源"
        + (f"，另有 {omit_n} 条因预算或冲突未注入" if omit_n else "")
        + conflict_note
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
        "conflicts_dropped": conflicts_dropped,
        "envelope_hash": m.get("envelope_hash"),
        "human_readable": summary + ("\n" + "\n".join(lines) if lines else ""),
    }

def comparison_protocol() -> dict[str, Any]:
    """D7 有/无记忆对照实验协议（质量 9.5 用人评，脚本只固定流程）。

    v2：双轨 + 轨2 B 臂 B1→B2→B3 escalation（design rev.4）。
    """
    return {
        "name": "memory_gain_ab_v2",
        "goal": "证明有记忆时成稿更连贯、设定回指更强、作者更少粘贴设定",
        "tracks": {
            "track1_product": {
                "label": "产品增益（总开关）",
                "A": "MEMORY_FABRIC=on + must + facts + 铁律 + minimal",
                "B": "MEMORY_FABRIC=off + minimal",
                "primary": False,
            },
            "track2_memory_contrib": {
                "label": "记忆贡献（正典注入）",
                "A": "FABRIC=on + must + facts + minimal",
                "B": "FABRIC=on + SCRIBE3_MEMORY_ABLATION=no_must_facts + minimal",
                "primary": True,
                "env_b": "SCRIBE3_MEMORY_ABLATION=no_must_facts",
                "escalation": [
                    {"arm": "B1", "ablation": "no_must_facts", "strip_iron": False},
                    {"arm": "B2", "ablation": "no_must_facts", "strip_iron": True},
                    {
                        "arm": "B3",
                        "ablation": "no_must_facts",
                        "strip_iron": True,
                        "desensitize_synopsis": True,
                    },
                ],
            },
        },
        "gates": {
            "engineering_gate": "lead≥1.0 且 A 三项均 ≥4.0",
            "machine_pass_rule": "lead≥1.5 且 A 三项均 ≥4.5（= pass_rule_met）",
            "human_pass_rule": "真人双盲三项 + lead；正式 ≥9.5 唯一路径",
        },
        "setup": [
            "同一 book slug、同一章 synopsis、同一模型与 max_tokens",
            "A 组：MEMORY_FABRIC 开 + must-link + 正典注入（正常产品）",
            "B 组轨2：B1 no_must_facts → 未过门则 B2 剥铁律 → 仍未过则 B3 脱敏 synopsis",
            "作者指令仅给冲突与 POV（SCRIBE3_MEMORY_STEER_MODE=minimal）",
            "禁止作者粘贴全书设定；若 detect_author_restated_canon 则作废该次",
            "A/B 禁止 restore wipe 前旧章节版本（AB_SKIP_VERSION_RESTORE）",
        ],
        "scores": [
            {"key": "coherence", "label": "跨句/跨段连贯", "scale": "1-5"},
            {"key": "canon_echo", "label": "设定回指自然度", "scale": "1-5"},
            {"key": "contradiction", "label": "自相矛盾少（分高=矛盾少）", "scale": "1-5"},
            {"key": "author_effort", "label": "作者少重复设定（分高=更省力）", "scale": "1-5"},
        ],
        "pass_rule": (
            "A 组三项（coherence/canon_echo/contradiction）均 ≥4.5，"
            "且相对 B 组平均领先 ≥1.5；否则 D7 不得报 ≥9.0；"
            "正式 ≥9.5 须真人双盲覆核"
        ),
        "artifacts": [
            "a_prose.md", "b_prose.md",
            "a_usage_digest.json", "b_usage_digest.json",
            "scores.json", "00-author-path.md",
        ],
    }


def three_tier_gates(avg_a: float, avg_b: float, sa: dict, sb: dict | None = None) -> dict[str, Any]:
    """从 A/B 三项分组装三层闸门（纯函数，无 I/O）。

    sa 需含 coherence/canon_echo/contradiction。
    """
    keys = ("coherence", "canon_echo", "contradiction")
    lead = float(avg_a) - float(avg_b)
    a_ok_eng = all(float(sa.get(k) or 0) >= 4.0 for k in keys)
    a_ok_mach = all(float(sa.get(k) or 0) >= 4.5 for k in keys)
    eng = bool(a_ok_eng and lead >= 1.0)
    mach = bool(a_ok_mach and lead >= 1.5)
    return {
        "lead_A_minus_B": round(lead, 3),
        "engineering_gate": eng,
        "engineering_gate_rule": "lead≥1.0 且 A 三项均 ≥4.0",
        "machine_pass_rule_met": mach,
        "pass_rule_met": mach,  # 兼容旧字段
        "pass_rule": (
            "A 组 coherence/canon_echo/contradiction 均 ≥4.5，"
            "且相对 B 平均领先 ≥1.5"
        ),
        "human_pass_rule_met": None,
        "human_pass_rule": "真人双盲三项 + lead；正式 ≥9.5 唯一路径",
        "void_reason": None,
        "scorer": "heuristic_v2_not_human_blind",
        "note": "禁止仅凭 machine/heuristic 宣称任一维 ≥9.5",
    }


def score_prose_heuristic_v2(prose: str, syn: str = "", *, label: str = "X") -> dict[str, Any]:
    """scorer v2：物件态/专名/债 加权；铜腥等书无关感官降权（design OQ4）。"""
    import re

    def cn_len(s: str) -> int:
        from scribe3.llm_visible import strip_thinking_markup
        return len(re.sub(r"\s+", "", strip_thinking_markup(s or "")))

    n = cn_len(prose)
    anchors = {
        "覃灰七": prose.count("覃灰七"),
        "三棱铜匙": prose.count("三棱铜匙"),
        "缺口": prose.count("缺口"),
        "铜腥": prose.count("铜腥") + prose.count("炉灰"),
        "冷锅婆": prose.count("冷锅婆"),
        "一炉香债": prose.count("一炉香债") + prose.count("香债"),
        "完整无缺": prose.count("完整无缺"),
        "沈拾灯": prose.count("沈拾灯"),
        "A7_full": prose.count("炉心印能开旧库侧门"),
        "炉心印": prose.count("炉心印"),
        "侧门": prose.count("侧门"),
    }
    coh = 2.0
    if n >= 3000:
        coh += 1.0
    if n >= 3800:
        coh += 0.5
    if n >= 4500:
        coh += 0.5
    if anchors["沈拾灯"] == 0:
        coh += 0.5
    coh = min(5.0, coh)

    # v2：state/专名/债为主；铜腥最多 +0.2（原 +0.7）
    echo = 1.5
    if anchors["覃灰七"] >= 3:
        echo += 0.9
    if anchors["三棱铜匙"] >= 1:
        echo += 0.9
    if anchors["缺口"] >= 1:
        echo += 0.9
    if anchors["冷锅婆"] >= 1:
        echo += 0.5
    if anchors["一炉香债"] >= 1:
        echo += 0.5
    if anchors["炉心印"] >= 1 or anchors["侧门"] >= 1:
        echo += 0.3
    if anchors["铜腥"] >= 1:
        echo += 0.2  # 降权
    echo = min(5.0, echo)

    contra = 5.0
    if anchors["完整无缺"] and anchors["缺口"]:
        contra -= 2.0
    if anchors["完整无缺"] and "缺口" in (syn or ""):
        contra -= 1.5
    if anchors["沈拾灯"]:
        contra -= 2.0
    if anchors["A7_full"]:
        contra -= 1.5
    contra = max(1.0, contra)

    effort = 4.5 if n >= 2500 else 3.0
    return {
        "label": label,
        "chars": n,
        "anchors": anchors,
        "coherence": round(coh, 2),
        "canon_echo": round(echo, 2),
        "contradiction": round(contra, 2),
        "author_effort": round(effort, 2),
    }


def iron_strip_mode() -> str:
    """keep（产品默认）| strip（B2/B3 评测）。"""
    import os
    v = ""
    try:
        from scribe3.settings import get_setting
        v = str(get_setting("SCRIBE3_MEMORY_IRON_IN_ABLATION") or "")
    except Exception:
        v = ""
    if not v:
        v = os.environ.get("SCRIBE3_MEMORY_IRON_IN_ABLATION") or "keep"
    # env 显式 strip 优先于默认 keep（测试/脚本）
    env = (os.environ.get("SCRIBE3_MEMORY_IRON_IN_ABLATION") or "").strip().lower()
    if env in {"strip", "off", "0", "false", "no", "ablate"}:
        v = env
    v = v.strip().lower()
    if v in {"strip", "off", "0", "false", "no", "ablate"}:
        return "strip"
    return "keep"


def should_strip_iron_laws() -> bool:
    return iron_strip_mode() == "strip"

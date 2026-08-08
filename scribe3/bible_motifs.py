"""开书 / 设定圣经阶段 · 母题强制闭环。

母题是「先立档、再回响」：GATE-A / 写作注入 / ingest 触及都依赖已立 motif。
本模块提供：缺口检测、种子草案 ops、写入提案构造（人批后经 orch apply 落库）。
"""
from __future__ import annotations

import time
import uuid
from typing import Any

# 与 craft GATE-A min_motifs 对齐的「可写」下限；圣经阶段目标更高
MIN_MOTIFS_CRAFT = 1
MIN_BIBLE_MOTIFS = 3

# 灯债系 / 默认旅程书种子（可被 intent 语境覆盖 label）
DEFAULT_MOTIF_SEEDS: list[dict[str, str]] = [
    {
        "name": "灯与债",
        "theme": "点灯即记账，照亮也是索取",
        "echoes": "暖黄灯/冷白灯/灯芯写名/合灯",
        "unfolding": "全书核心意象：守灯与背债一体两面",
    },
    {
        "name": "替与真名",
        "theme": "顶死、转债、名被改写",
        "echoes": "替字/纸钱/伪契/真名",
        "unfolding": "身份与债务如何被纸笔偷换",
    },
    {
        "name": "应到之声",
        "theme": "一声「到」即入债链",
        "echoes": "应到/折声/夜审点名",
        "unfolding": "声响作为契约与代价的触发器",
    },
    {
        "name": "不渡与守暖",
        "theme": "师训不渡夜魂，却在人命前违训护暖",
        "echoes": "不渡夜魂/暖黄灯/削替字",
        "unfolding": "规矩与良心的摩擦",
    },
    {
        "name": "雨巷纸味",
        "theme": "湿冷青石与纸钱墨迹的感官底色",
        "echoes": "雨巷/湿纸钱/河灯市/旧渡口",
        "unfolding": "每章气味触感锚，拒绝干讲设定",
    },
]


def count_named_motifs(st: Any) -> int:
    if not st or not hasattr(st, "list_motifs"):
        return 0
    try:
        rows = st.list_motifs() or []
    except Exception:
        return 0
    n = 0
    for m in rows:
        if not isinstance(m, dict):
            continue
        name = (m.get("name") or "").strip()
        if name:
            n += 1
    return n


def existing_motif_names(st: Any) -> set[str]:
    out: set[str] = set()
    if not st or not hasattr(st, "list_motifs"):
        return out
    try:
        for m in st.list_motifs() or []:
            if isinstance(m, dict) and (m.get("name") or "").strip():
                out.add(str(m["name"]).strip())
    except Exception:
        pass
    return out


def evaluate_motif_gap(
    st: Any,
    *,
    min_required: int = MIN_BIBLE_MOTIFS,
) -> dict[str, Any]:
    """返回母题缺口摘要（产品与 WCG 共用）。"""
    count = count_named_motifs(st)
    need = max(0, int(min_required) - count)
    return {
        "ok": count >= int(min_required),
        "count": count,
        "min_required": int(min_required),
        "deficit": need,
        "craft_ok": count >= MIN_MOTIFS_CRAFT,
        "names": sorted(existing_motif_names(st)),
    }


def pick_seed_motifs(
    st: Any | None = None,
    *,
    min_required: int = MIN_BIBLE_MOTIFS,
    seeds: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """选出尚未存在的种子母题，仅补足 deficit。"""
    have = existing_motif_names(st) if st is not None else set()
    need = (
        evaluate_motif_gap(st, min_required=min_required)["deficit"]
        if st is not None
        else int(min_required)
    )
    if need <= 0:
        return []
    pool = list(seeds or DEFAULT_MOTIF_SEEDS)
    picked: list[dict[str, str]] = []
    for row in pool:
        if len(picked) >= need:
            break
        name = (row.get("name") or "").strip()
        if not name or name in have:
            continue
        picked.append({
            "name": name,
            "theme": (row.get("theme") or "").strip(),
            "echoes": (row.get("echoes") or "").strip(),
            "unfolding": (row.get("unfolding") or "").strip(),
        })
    # 仍不足：编号占位（极少）
    i = 1
    while len(picked) < need:
        name = f"贯穿母题{i}"
        i += 1
        if name in have or any(p["name"] == name for p in picked):
            continue
        picked.append({
            "name": name,
            "theme": "待作者收紧主题",
            "echoes": "感官回响词1/回响词2",
            "unfolding": "开书阶段占位，批准后请改成作品真母题",
        })
    return picked


def motif_ops_from_seeds(seeds: list[dict[str, str]]) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    for s in seeds:
        name = (s.get("name") or "").strip()
        if not name:
            continue
        args = {
            "name": name,
            "theme": s.get("theme") or "",
            "echoes": s.get("echoes") or "",
            "unfolding": s.get("unfolding") or "",
        }
        ops.append({
            "tool": "s3_add_motif",
            "args": args,
            "label": f"新建母题·{name}",
            "out_of_allowlist": False,
            "status": "pending",
        })
    return ops


def build_motif_seed_proposal(
    st: Any | None = None,
    *,
    min_required: int = MIN_BIBLE_MOTIFS,
    work: str = "main",
    summary: str | None = None,
) -> dict[str, Any] | None:
    """构造待批写入提案；已达门槛则返回 None。"""
    gap = evaluate_motif_gap(st, min_required=min_required)
    if gap["ok"]:
        return None
    seeds = pick_seed_motifs(st, min_required=min_required)
    ops = motif_ops_from_seeds(seeds)
    if not ops:
        return None
    first = seeds[0]["name"]
    return {
        "id": f"prop_motif_{uuid.uuid4().hex[:10]}",
        "work_package_id": f"bible.motif:{work}",
        "domain": "motif.manage",
        "summary": summary or (
            f"开书强制母题草案 · 现有 {gap['count']} 条，目标 ≥{min_required}，"
            f"拟新增 {len(ops)} 条（人批后进 Codex）"
        ),
        "ops": ops,
        "ui_after": {
            "kind": "leaf",
            "entry": "motif",
            "object_type": "motif",
            "id": first,
            "label": first,
            "right_tab": "chief",
            "panel": "motif",
        },
        "ui_target_after": {
            "kind": "leaf",
            "entry": "motif",
            "object_type": "motif",
            "id": first,
            "label": first,
            "right_tab": "chief",
            "panel": "motif",
        },
        "created_at": int(time.time()),
        "status": "pending",
        "source": "bible_motif_force",
        "gap": gap,
    }


def next_step_for_motif_gap(gap: dict[str, Any]) -> dict[str, Any]:
    n = gap.get("count") or 0
    need = gap.get("min_required") or MIN_BIBLE_MOTIFS
    return {
        "id": "seed_motifs",
        "title": f"立母题（已有 {n}，目标 ≥{need}）",
        "why": (
            "母题须在开书/圣经阶段先立档：写作注入、跨章回响、ingest 触及都只匹配已立母题；"
            "不会从正文自动新建。"
        ),
        "how_chat": (
            "请主编提交写入提案：用 s3_add_motif 为本书立至少 "
            f"{need} 条母题（name/theme/echoes），供我批准。"
        ),
        "ui_target": {
            "kind": "leaf",
            "entry": "motif",
            "object_type": "motif",
            "panel": "motif",
            "right_tab": "chief",
        },
    }

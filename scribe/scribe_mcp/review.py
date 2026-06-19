"""主动引擎(规则版)—— 全文体检,产出主编札记 ProactiveInsight(内核0 §3.5)。

当前规则(零 LLM,可离线验证):超期未回收的伏笔 → 札记。
后续可加:主线偏离北极星(需 LLM)、孤立设定、节奏疲劳等;由 Cron 周期触发(Batch 5)。
低误报 + 去重:同一伏笔不重复刷札记(防"狼来了")。
"""
from __future__ import annotations

from .db import Database
from .foreshadow import ForeshadowStore


def run_proactive_review(db: Database, work_id: str, current_chapter: int,
                         overdue_threshold: int = 50) -> list[str]:
    """返回新生成的 insight id 列表。"""
    fs = ForeshadowStore(db.conn)
    new_ids: list[str] = []
    for f in fs.overdue(work_id, current_chapter, overdue_threshold):
        key = f"foreshadow:{f['id']}"
        if db.insight_exists(work_id, "foreshadow_overdue", key):
            continue  # 去重,不重复刷
        gap = current_chapter - (f["foreshadow_chapter"] or 0)
        iid = db.add_proactive_insight(
            work_id, kind="foreshadow_overdue",
            summary=f"伏笔「{f['summary']}」埋于第 {f['foreshadow_chapter']} 章,已 {gap} 章未回收。",
            severity="major" if f["importance"] == "critical" else "minor",
            suggested_action="考虑在近几章触发或回收;若已无必要,标记 abandoned。",
            evidence_refs={"key": key, "foreshadow_id": f["id"]},
        )
        new_ids.append(iid)
    return new_ids


def review_all_works(db: Database, overdue_threshold: int = 50) -> dict:
    """对所有作品做一轮体检(后台主动引擎周期调用)。返回 {work_id: 新札记数}。"""
    out: dict[str, int] = {}
    for w in db.list_all_works():
        chs = db.list_chapters(w["id"])
        cur = max((c["seq"] for c in chs), default=0)
        if cur == 0:
            continue
        out[w["id"]] = len(run_proactive_review(db, w["id"], cur, overdue_threshold))
    return out


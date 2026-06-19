"""伏笔 F-T-P 状态机(门槛1 / CFPG arXiv 2601.07033)。

状态:planted → triggered → paid(终态);planted/triggered → abandoned(终态)。
非法转移抛错(防"挖坑跳填"等不合法状态跳变)。含未回收预警(overdue)与回收率统计。
纯 stdlib,可离线单测。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

# 合法转移表:from -> {允许的 to}
_TRANSITIONS = {
    "planted": {"triggered", "abandoned"},
    "triggered": {"paid", "abandoned"},
    "paid": set(),        # 终态
    "abandoned": set(),   # 终态
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ForeshadowStore:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def plant(self, work_id: str, summary: str, foreshadow_chapter: int,
              importance: str = "normal", payload: dict | None = None) -> str:
        fid = str(uuid.uuid4())
        ts = _now()
        self.conn.execute(
            "INSERT INTO foreshadows(id,work_id,summary,foreshadow_chapter,state,importance,"
            "payload,created_at,updated_at) VALUES(?,?,?,?,'planted',?,?,?,?)",
            (fid, work_id, summary, foreshadow_chapter, importance,
             json.dumps(payload or {}, ensure_ascii=False), ts, ts),
        )
        self.conn.commit()
        return fid

    def get(self, fid: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM foreshadows WHERE id=?", (fid,)).fetchone()
        return dict(r) if r else None

    def transition(self, fid: str, to_state: str, chapter: int | None = None) -> None:
        """推进伏笔状态;非法转移抛 ValueError。"""
        row = self.get(fid)
        if not row:
            raise ValueError(f"伏笔不存在: {fid}")
        cur = row["state"]
        if to_state not in _TRANSITIONS.get(cur, set()):
            raise ValueError(f"非法状态转移: {cur} → {to_state}(伏笔 {fid})")
        col = {"triggered": "trigger_chapter", "paid": "payoff_chapter"}.get(to_state)
        sets = "state=?, updated_at=?"
        params: list = [to_state, _now()]
        if col and chapter is not None:
            sets += f", {col}=?"
            params.append(chapter)
        params.append(fid)
        self.conn.execute(f"UPDATE foreshadows SET {sets} WHERE id=?", params)
        self.conn.commit()

    def list_open(self, work_id: str) -> list[dict]:
        """未了结(planted/triggered)的伏笔。"""
        rows = self.conn.execute(
            "SELECT * FROM foreshadows WHERE work_id=? AND state IN('planted','triggered') "
            "ORDER BY foreshadow_chapter",
            (work_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def overdue(self, work_id: str, current_chapter: int, threshold: int = 50) -> list[dict]:
        """埋设后超过 threshold 章仍未回收 → 预警(critical 伏笔阈值减半,提前预警)。"""
        out = []
        for r in self.list_open(work_id):
            thr = threshold // 2 if r["importance"] == "critical" else threshold
            if current_chapter - (r["foreshadow_chapter"] or 0) >= thr:
                out.append(r)
        return out

    def payoff_rate(self, work_id: str) -> float:
        """回收率 = paid / (paid + abandoned + 仍未了结)。无伏笔则 1.0。"""
        rows = self.conn.execute(
            "SELECT state, COUNT(*) c FROM foreshadows WHERE work_id=? GROUP BY state",
            (work_id,),
        ).fetchall()
        counts = {r["state"]: r["c"] for r in rows}
        total = sum(counts.values())
        return 1.0 if total == 0 else counts.get("paid", 0) / total

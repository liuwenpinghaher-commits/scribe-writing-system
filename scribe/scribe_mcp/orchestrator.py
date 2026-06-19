"""章生成编排状态机(实现3 · C3-3)—— 15 态 ChapterTask + 合法转移强制。

把"一章从规划到定稿"的流程显式化为状态机:每步只能走合法转移,非法转移拒绝。
配合既有流水线(draft→评改→定稿;save→索引→校验→摄取)提供可追踪、可续跑的编排骨架。
状态机纯逻辑(legal_transition / next_states)可离线单测;持久化经 db.chapter_tasks。
"""
from __future__ import annotations

from datetime import datetime, timezone

# 15 态(实现3 回路状态机)
STATES = [
    "PLANNING", "AWAITING_OUTLINE_CHOICE", "OUTLINED", "DRAFTING", "DRAFTED",
    "REFLECTING", "REVISING", "AWAITING_DRAFT_CHOICE", "REVIEWING", "REVIEW_FAILED",
    "AWAITING_HUMAN", "CONSISTENCY_CHECK", "MEMORY_UPDATE", "DONE", "FAILED",
]

# 合法转移图
TRANSITIONS: dict[str, set[str]] = {
    "PLANNING": {"AWAITING_OUTLINE_CHOICE", "OUTLINED", "FAILED"},
    "AWAITING_OUTLINE_CHOICE": {"OUTLINED", "FAILED"},
    "OUTLINED": {"DRAFTING", "FAILED"},
    "DRAFTING": {"DRAFTED", "FAILED"},
    "DRAFTED": {"REFLECTING", "AWAITING_DRAFT_CHOICE", "REVIEWING", "FAILED"},
    "REFLECTING": {"REVISING", "REVIEWING", "FAILED"},
    "REVISING": {"DRAFTED", "REVIEWING", "FAILED"},
    "AWAITING_DRAFT_CHOICE": {"REVIEWING", "REVISING", "FAILED"},
    "REVIEWING": {"REVIEW_FAILED", "CONSISTENCY_CHECK", "AWAITING_HUMAN", "FAILED"},
    "REVIEW_FAILED": {"REVISING", "AWAITING_HUMAN", "FAILED"},
    "AWAITING_HUMAN": {"REVISING", "CONSISTENCY_CHECK", "DONE", "FAILED"},
    "CONSISTENCY_CHECK": {"MEMORY_UPDATE", "REVIEW_FAILED", "FAILED"},
    "MEMORY_UPDATE": {"DONE", "FAILED"},
    "DONE": set(),
    "FAILED": {"PLANNING"},  # 允许重启
}

INITIAL = "PLANNING"
TERMINAL = {"DONE", "FAILED"}


def legal_transition(frm: str, to: str) -> bool:
    return to in TRANSITIONS.get(frm, set())


def next_states(frm: str) -> set[str]:
    return TRANSITIONS.get(frm, set())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Orchestrator:
    def __init__(self, db):
        self.db = db

    def get(self, work_id: str, seq: int) -> dict | None:
        r = self.db.conn.execute(
            "SELECT * FROM chapter_tasks WHERE work_id=? AND seq=?", (work_id, seq)).fetchone()
        return dict(r) if r else None

    def ensure(self, work_id: str, seq: int) -> dict:
        t = self.get(work_id, seq)
        if t:
            return t
        import uuid
        self.db.conn.execute(
            "INSERT INTO chapter_tasks(id,work_id,seq,status,detail,updated_at) "
            "VALUES(?,?,?,?,?,?)", (uuid.uuid4().hex, work_id, seq, INITIAL, "", _now()))
        self.db.conn.commit()
        return self.get(work_id, seq)

    def advance(self, work_id: str, seq: int, to: str, detail: str = "") -> dict:
        """推进到 to;非法转移抛 ValueError。"""
        if to not in STATES:
            raise ValueError(f"未知状态:{to}")
        t = self.ensure(work_id, seq)
        if not legal_transition(t["status"], to):
            raise ValueError(f"非法转移:{t['status']} → {to}")
        self.db.conn.execute(
            "UPDATE chapter_tasks SET status=?, detail=?, updated_at=? WHERE work_id=? AND seq=?",
            (to, detail, _now(), work_id, seq))
        self.db.conn.commit()
        return self.get(work_id, seq)

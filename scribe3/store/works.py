"""SurrealStore mixin: works."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class WorksMixin:

    def upsert_working_summary(self, work: str, thread_id: str, *, through_turn: int = 0,
                               goals: list[str] | None = None,
                               open_tasks: list[str] | None = None,
                               decisions: list[str] | None = None,
                               assumptions: list[str] | None = None,
                               summary: str = "") -> None:
        """落/覆盖某线程的工作摘要(thread 唯一,幂等 UPSERT)。id 用 work|thread 去重。"""
        rid = f"{work}|{thread_id}"
        self._execute_write(
            "UPSERT type::thing('working_summary', $rid) SET work=$w, thread_id=$tid, "
            "through_turn=$tt, goals=$goals, open_tasks=$tasks, decisions=$dec, "
            "assumptions=$asm, summary=$sum, updated_at=time::now() RETURN NONE",
            {"rid": rid, "w": work, "tid": thread_id, "tt": int(through_turn),
             "goals": goals or [], "tasks": open_tasks or [], "dec": decisions or [],
             "asm": assumptions or [], "sum": summary or ""})

    def get_working_summary(self, work: str, thread_id: str) -> dict | None:
        rid = f"{work}|{thread_id}"
        rows = self._query(
            f"SELECT {self._WORKING_SUMMARY_FIELDS} FROM type::thing('working_summary', $rid)",
            {"rid": rid})
        return rows[0] if rows else None

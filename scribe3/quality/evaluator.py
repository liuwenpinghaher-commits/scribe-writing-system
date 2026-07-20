"""固定十维系统评价器。"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from scribe3.store import SurrealStore


class QualityEvaluator:
    def __init__(self, store: "SurrealStore", llm: Any):
        self._store = store
        self._llm = llm

    def evaluate_chapter(
        self,
        *,
        work: str,
        snapshot_id: str,
        chapter_version_id: str,
        contract_id: str,
        contract_revision: int,
    ) -> dict[str, Any]:
        raise NotImplementedError("evaluate_chapter 待实现")

    def compare_references(
        self,
        *,
        work: str,
        snapshot_id: str,
        reference_fingerprint_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        raise NotImplementedError("compare_references 待实现")

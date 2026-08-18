"""In-memory playbook store. Used by unit tests and as the freeze protocol."""
from __future__ import annotations

from typing import Any

from scribe3.playbook.envelope import artifact_sha, wrap
from scribe3.playbook.errors import FrozenAssetError

TABLES = (
    "duty_card",
    "chapter_play",
    "chapter_contract",
    "chapter_deduce",
    "chapter_draft",
)
DOWNSTREAM = ("chapter_contract", "chapter_deduce", "chapter_draft")


class MemoryPlaybookStore:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {t: [] for t in TABLES}

    def list_versions(self, table: str, seq: int) -> list[dict[str, Any]]:
        return sorted(
            [r for r in self.rows[table] if int(r.get("seq") or 0) == int(seq)],
            key=lambda r: int(r.get("version") or 0),
        )

    def next_version(self, table: str, seq: int) -> int:
        vers = [int(r.get("version") or 0) for r in self.list_versions(table, seq)]
        return (max(vers) + 1) if vers else 1

    def get_frozen(self, table: str, seq: int) -> dict[str, Any] | None:
        for rec in reversed(self.list_versions(table, seq)):
            if rec.get("status") == "frozen":
                return rec
        return None

    def get_by_sha(self, table: str, sha: str) -> dict[str, Any] | None:
        for rec in self.rows[table]:
            if rec.get("sha") == sha:
                return rec
        return None

    def insert(self, table: str, rec: dict[str, Any]) -> dict[str, Any]:
        row = dict(rec)
        self.rows[table].append(row)
        return row

    def mark_superseded(self, table: str, seq: int, version: int) -> None:
        for rec in self.rows[table]:
            if int(rec.get("seq") or 0) == int(seq) and int(rec.get("version") or 0) == int(version):
                rec["status"] = "superseded"

    def list_by_play_sha(self, table: str, play_sha: str) -> list[dict[str, Any]]:
        return [r for r in self.rows[table] if r.get("play_sha") == play_sha]


def overwrite_play(store: MemoryPlaybookStore, sha: str, new_text: str) -> dict[str, Any]:
    """Forbidden path: mutate frozen play content in place."""
    rec = store.get_by_sha("chapter_play", sha)
    if rec is None:
        raise KeyError(sha)
    if rec.get("status") == "frozen":
        raise FrozenAssetError(f"frozen play {sha} cannot be overwritten")
    rec["text"] = new_text
    rec["sha"] = artifact_sha(rec)
    return rec


def freeze_artifact(
    store: MemoryPlaybookStore,
    table: str,
    seq: int,
    payload: dict[str, Any],
    *,
    schema: str,
    source_sha: str = "",
    review: dict[str, Any] | None = None,
    rewrite: bool = False,
) -> dict[str, Any]:
    existing = store.get_frozen(table, seq)
    wrapped = wrap(schema, payload, source_sha=source_sha, status="frozen", review=review)
    sha = wrapped["sha"]
    if existing and existing.get("sha") == sha:
        return existing
    if existing and not rewrite:
        raise FrozenAssetError(f"{table} seq={seq} frozen sha={existing.get('sha')}")
    if existing and rewrite:
        store.mark_superseded(table, seq, int(existing.get("version") or 0))
        if table == "chapter_play":
            supersede_downstream(store, seq, str(existing.get("sha") or ""))
    wrapped["seq"] = int(seq)
    wrapped["version"] = store.next_version(table, seq)
    return store.insert(table, wrapped)


def supersede_downstream(store: MemoryPlaybookStore, seq: int, old_play_sha: str) -> list[str]:
    touched: list[str] = []
    for table in DOWNSTREAM:
        for rec in store.list_versions(table, seq):
            if rec.get("status") == "frozen" and rec.get("play_sha") == old_play_sha:
                rec["status"] = "superseded"
                touched.append(f"{table}:{rec.get('sha')}")
    return touched

"""Surreal mixin for playbook tables. Same protocol as MemoryPlaybookStore."""
from __future__ import annotations

import json
from typing import Any

from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.store.core_preamble import *  # noqa: F403

TABLES = (
    "duty_card",
    "chapter_play",
    "chapter_contract",
    "chapter_deduce",
    "chapter_draft",
    "chapter_state",
)


class PlaybookOpsMixin:
    def get_frozen(self, table: str, seq: int) -> dict[str, Any] | None:
        if table not in TABLES:
            return None
        try:
            rows = self._query(
                f"SELECT * FROM {table} WHERE seq=$seq AND status='frozen' "
                "ORDER BY version DESC LIMIT 1",
                {"seq": int(seq)},
            )
        except Exception:
            return None
        return _row(rows[0]) if rows else None

    def clear_frozen_for_seq(self, seq: int) -> None:
        for table in TABLES:
            try:
                self._execute_write(
                    f"UPDATE {table} SET status='superseded' WHERE seq=$seq AND status='frozen'",
                    {"seq": int(seq)},
                )
            except Exception:
                pass

    def get_by_sha(self, table: str, sha: str) -> dict[str, Any] | None:
        if table not in TABLES:
            return None
        try:
            rows = self._query(
                f"SELECT * FROM {table} WHERE sha=$sha LIMIT 1",
                {"sha": str(sha)},
            )
        except Exception:
            return None
        return _row(rows[0]) if rows else None

    def next_version(self, table: str, seq: int) -> int:
        # Surreal 3.x math::max(version) 常空/报错；空则退回 1，会 UPSERT 掉已冻的 1 号稿。
        vers = [int(r.get("version") or 0) for r in self.list_versions(table, seq)]
        if vers:
            return max(vers) + 1
        if self.get_frozen(table, seq):
            return 2
        return 1

    def list_versions(self, table: str, seq: int) -> list[dict[str, Any]]:
        try:
            rows = self._query(
                f"SELECT * FROM {table} WHERE seq=$seq ORDER BY version ASC",
                {"seq": int(seq)},
            )
        except Exception:
            return []
        return [_row(r) for r in (rows or [])]

    def insert(self, table: str, rec: dict[str, Any]) -> dict[str, Any]:
        seq = int(rec.get("seq") or 0)
        ver = int(rec.get("version") or 1)
        existing = {int(r.get("version") or 0): r for r in self.list_versions(table, seq)}
        while ver in existing:
            old = existing[ver]
            same_sha = str(old.get("sha") or "") and old.get("sha") == rec.get("sha")
            if old.get("status") == "frozen" and not (
                rec.get("status") == "frozen" and same_sha
            ):
                ver += 1
                continue
            break
        rec["seq"] = seq
        rec["version"] = ver
        rid = f"{seq}_{ver}"
        body = json.dumps(rec, ensure_ascii=False)
        self._execute_write(
            f"UPSERT type::record('{table}', $rid) SET seq=$seq, version=$ver, "
            "status=$st, sha=$sha, playbook_version=$pv, source_sha=$src, "
            "schema_name=$sch, body=$body",
            {
                "rid": rid,
                "seq": int(rec.get("seq") or 0),
                "ver": int(rec.get("version") or 1),
                "st": str(rec.get("status") or "draft"),
                "sha": str(rec.get("sha") or ""),
                "pv": str(rec.get("playbook_version") or ""),
                "src": str(rec.get("source_sha") or ""),
                "sch": str(rec.get("schema") or ""),
                "body": body,
            },
        )
        return rec

    def mark_superseded(self, table: str, seq: int, version: int) -> None:
        self._execute_write(
            f"UPDATE {table} SET status='superseded' WHERE seq=$seq AND version=$ver",
            {"seq": int(seq), "ver": int(version)},
        )

    def list_by_play_sha(self, table: str, play_sha: str) -> list[dict[str, Any]]:
        try:
            rows = self._query(
                f"SELECT * FROM {table} WHERE source_sha=$sha OR sha=$sha",
                {"sha": str(play_sha)},
            )
        except Exception:
            return []
        out = []
        for r in rows or []:
            rec = _row(r)
            if rec.get("play_sha") == play_sha or rec.get("source_sha") == play_sha:
                out.append(rec)
        return out

    def record_playbook_trace(self, rec: dict[str, Any]) -> None:
        fn = getattr(self, "append_pipeline_event", None)
        if callable(fn):
            try:
                fn(rec)
            except Exception:
                return

    def save_chapter_prose(self, seq: int, prose: str, *, play_sha: str = "", contract_sha: str = "") -> None:
        save = getattr(self, "save_chapter", None)
        if callable(save):
            save(int(seq), prose or "")
        meta = {"play_sha": play_sha, "contract_sha": contract_sha, "playbook_version": PLAYBOOK_VERSION}
        upd = getattr(self, "update_chapter_meta", None)
        if callable(upd):
            try:
                upd(int(seq), meta)
            except Exception:
                return


    def migrate_legacy_plays(self) -> int:
        """Copy beats_meta.play where play_review_ok into frozen chapter_play (legacy)."""
        import hashlib
        import json
        n = 0
        try:
            rows = self._query("SELECT seq, beats_meta FROM chapter")
        except Exception:
            return 0
        for raw in rows or []:
            seq = raw.get("seq")
            meta = raw.get("beats_meta")
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            if not isinstance(meta, dict) or not meta.get("play_review_ok"):
                continue
            text = str(meta.get("play") or "").strip()
            if not text or seq is None:
                continue
            if self.get_frozen("chapter_play", int(seq)):
                continue
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            rec = {
                "schema": "chapter_play.v1",
                "playbook_version": PLAYBOOK_VERSION,
                "seq": int(seq),
                "version": 1,
                "text": text,
                "status": "frozen",
                "sha": sha,
                "review": {"judge_version": "legacy", "verdict": "pass"},
            }
            self.insert("chapter_play", rec)
            n += 1
        return n


def _row(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    body = raw.get("body")
    if isinstance(body, str):
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    if isinstance(body, dict):
        return body
    return dict(raw)

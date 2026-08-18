"""章设计整份缓存。热更时若表不存在会自建。"""
from __future__ import annotations

import json
from typing import Any

from scribe3.store.core_preamble import *  # noqa: F403


_DDL = (
    "DEFINE TABLE IF NOT EXISTS design_attempt SCHEMAFULL;"
    "DEFINE FIELD IF NOT EXISTS seq ON design_attempt TYPE int;"
    "DEFINE FIELD IF NOT EXISTS attempt ON design_attempt TYPE int;"
    "DEFINE FIELD IF NOT EXISTS ok ON design_attempt TYPE bool;"
    "DEFINE FIELD IF NOT EXISTS errors ON design_attempt TYPE string;"
    "DEFINE FIELD IF NOT EXISTS body ON design_attempt TYPE string;"
    "DEFINE FIELD IF NOT EXISTS created_at ON design_attempt TYPE datetime DEFAULT time::now();"
)


class DesignAttemptsMixin:
    def _ensure_design_attempt_table(self) -> None:
        if getattr(self, "_design_attempt_ready", False):
            return
        try:
            for stmt in _DDL.split(";"):
                sql = stmt.strip()
                if sql:
                    self._execute_write(sql, {})
            self._design_attempt_ready = True
        except Exception:
            self._design_attempt_ready = False

    def save_design_attempt(self, seq: int, rec: dict[str, Any]) -> None:
        self._ensure_design_attempt_table()
        if not getattr(self, "_design_attempt_ready", False):
            return
        body = {
            "chapter_spine": rec.get("chapter_spine") or {},
            "beats": rec.get("beats") or [],
            "clock": rec.get("clock") or {},
            "place": rec.get("place") or {},
            "designated_beat": rec.get("designated_beat"),
            "synopsis": rec.get("synopsis") or "",
            "raw_head": rec.get("raw_head") or "",
            "slot": rec.get("slot") or "",
        }
        try:
            self._execute_write(
                "CREATE design_attempt SET seq=$seq, attempt=$n, ok=$ok, "
                "errors=$err, body=$body",
                {
                    "seq": int(seq),
                    "n": int(rec.get("n") or 0),
                    "ok": bool(rec.get("struct_ok") and rec.get("exam_ok")),
                    "err": json.dumps(list(rec.get("errors") or []), ensure_ascii=False),
                    "body": json.dumps(body, ensure_ascii=False),
                },
            )
        except Exception:
            return

    def list_design_attempts(self, seq: int, *, limit: int = 20) -> list[dict[str, Any]]:
        self._ensure_design_attempt_table()
        if not getattr(self, "_design_attempt_ready", False):
            return []
        try:
            rows = self._query(
                "SELECT seq, attempt, ok, errors, body, created_at FROM design_attempt "
                "WHERE seq=$seq ORDER BY created_at ASC LIMIT $lim",
                {"seq": int(seq), "lim": int(limit)},
            )
        except Exception:
            return []
        out = []
        for r in rows or []:
            body = {}
            try:
                body = json.loads(r.get("body") or "{}")
            except Exception:
                body = {}
            errs = r.get("errors")
            if isinstance(errs, str):
                try:
                    errs = json.loads(errs)
                except Exception:
                    errs = [errs]
            out.append({
                "n": r.get("attempt"),
                "ok": bool(r.get("ok")),
                "errors": errs or [],
                "created_at": r.get("created_at"),
                **(body if isinstance(body, dict) else {}),
            })
        return out

"""SurrealStore mixin: canon_candidate 全类型待确认 + 审计。"""
from __future__ import annotations

import json
from typing import Any

from scribe3.store.core_preamble import *  # noqa: F403

CANDIDATE_TTL_DAYS = 30


def candidate_is_expired(row: dict | None, *, now_ts: float | None = None, ttl_days: int = CANDIDATE_TTL_DAYS) -> bool:
    """纯函数：created_at 超过 ttl 即过期。"""
    import time
    if not row:
        return True
    created = row.get("created_at")
    ts = None
    if isinstance(created, (int, float)):
        ts = float(created)
    elif isinstance(created, str):
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
        except Exception:
            ts = None
    if ts is None:
        return False
    now = time.time() if now_ts is None else float(now_ts)
    return now - ts > int(ttl_days) * 86400


class CanonCandidatesMixin:
    def ensure_canon_candidate_schema(self) -> None:
        """幂等补表（老库未跑 migration 时 best-effort）。"""
        try:
            self._raw_query(
                "DEFINE TABLE IF NOT EXISTS canon_candidate SCHEMAFULL;"
            )
        except Exception:
            pass

    def add_canon_candidate(self, row: dict[str, Any]) -> str:
        """写入一条 pending 候选，返回 local id。被拒过的同哈希不再进待确认。"""
        import hashlib
        import uuid
        local = (row.get("id") or "").strip() or uuid.uuid4().hex[:12]
        before = row.get("before")
        after = row.get("after")
        impact = row.get("impact")
        eh_src = "|".join([
            str(row.get("module") or ""),
            str(row.get("target") or ""),
            str(row.get("field") or ""),
            json.dumps(after, ensure_ascii=False, sort_keys=True) if after is not None else str(row.get("after_json") or ""),
        ])
        entity_hash = hashlib.sha1(eh_src.encode("utf-8")).hexdigest()[:20]
        try:
            rejected = self._query(
                "SELECT id FROM canon_candidate WHERE status='rejected' AND entity_hash=$h LIMIT 1",
                {"h": entity_hash},
            ) or []
            if rejected:
                return str(rejected[0].get("id") or local)
        except Exception:
            pass
        self._execute_write(
            "CREATE type::record('canon_candidate', $id) SET "
            "seq=$seq, source=$source, extractor=$extractor, module=$module, op=$op, "
            "target=$target, field=$field, before_json=$bj, after_json=$aj, "
            "evidence=$evidence, confidence=$conf, risk=$risk, layer=$layer, "
            "status=$status, change_pack_id=$cpid, impact_json=$ij, entity_hash=$eh",
            {
                "id": local,
                "seq": row.get("seq"),
                "source": row.get("source") or "prose_finalize",
                "extractor": row.get("extractor") or "marker",
                "module": row.get("module") or "character",
                "op": row.get("op") or "patch",
                "target": row.get("target") or "",
                "field": row.get("field"),
                "bj": json.dumps(before, ensure_ascii=False) if before is not None else None,
                "aj": json.dumps(after, ensure_ascii=False) if after is not None else None,
                "evidence": (row.get("evidence") or "")[:500],
                "conf": float(row.get("confidence") or 1.0),
                "risk": row.get("risk") or "med",
                "layer": row.get("layer") or "L1",
                "status": row.get("status") or "pending",
                "cpid": row.get("change_pack_id"),
                "ij": json.dumps(impact, ensure_ascii=False) if impact is not None else None,
                "eh": entity_hash,
            },
        )
        return local

    def expire_stale_canon_candidates(self, ttl_days: int = 30) -> int:
        """DED-13：pending 超过 30 天标 expired。"""
        try:
            self._execute_write(
                "UPDATE canon_candidate SET status='expired', decided_at=time::now() "
                "WHERE status='pending' AND created_at < time::now() - 30d",
            )
        except Exception:
            return 0
        return 0

    def list_canon_candidates(
        self,
        status: str = "pending",
        module: str | None = None,
        seq: int | None = None,
    ) -> list[dict]:
        if status == "pending":
            self.expire_stale_canon_candidates()
        q = (
            "SELECT meta::id(id) AS id, seq, source, extractor, module, op, target, field, "
            "before_json, after_json, evidence, confidence, risk, layer, status, "
            "change_pack_id, impact_json, created_at, decided_at "
            "FROM canon_candidate WHERE status=$st"
        )
        params: dict[str, Any] = {"st": status}
        if module:
            q += " AND module=$m"
            params["m"] = module
        if seq is not None:
            q += " AND seq=$seq"
            params["seq"] = seq
        q += " ORDER BY created_at DESC"
        try:
            rows = self._query(q, params)
        except Exception:
            return []
        out = []
        for r in rows or []:
            item = dict(r)
            for jk, key in (("before_json", "before"), ("after_json", "after"), ("impact_json", "impact")):
                raw = item.pop(jk, None)
                if raw:
                    try:
                        item[key] = json.loads(raw)
                    except Exception:
                        item[key] = raw
                else:
                    item[key] = None
            out.append(item)
        return out

    def get_canon_candidate(self, uid: str) -> dict | None:
        try:
            rows = self._query(
                "SELECT meta::id(id) AS id, seq, source, extractor, module, op, target, field, "
                "before_json, after_json, evidence, confidence, risk, layer, status, "
                "change_pack_id, impact_json, created_at, decided_at "
                "FROM type::record('canon_candidate', $u)",
                {"u": uid},
            )
            if not rows:
                return None
            item = dict(rows[0])
            for jk, key in (
                ("before_json", "before"),
                ("after_json", "after"),
                ("impact_json", "impact"),
            ):
                raw = item.pop(jk, None)
                if raw:
                    try:
                        item[key] = json.loads(raw)
                    except Exception:
                        item[key] = raw
                else:
                    item[key] = None
            return item
        except Exception:
            return None

    def set_canon_candidate_status(self, uid: str, status: str) -> None:
        self._execute_write(
            "UPDATE type::record('canon_candidate', $u) SET status=$st, decided_at=time::now()",
            {"u": uid, "st": status},
        )

    def count_canon_debt(self) -> dict[str, int]:
        try:
            rows = self._query(
                "SELECT module, count() AS n FROM canon_candidate "
                "WHERE status='pending' GROUP BY module"
            )
        except Exception:
            return {"total": 0, "high": 0}
        by_mod = {r.get("module"): int(r.get("n") or 0) for r in (rows or [])}
        total = sum(by_mod.values())
        try:
            hi = self._query(
                "SELECT count() AS n FROM canon_candidate "
                "WHERE status='pending' AND risk='high' GROUP ALL"
            )
            high = int((hi[0] or {}).get("n") or 0) if hi else 0
        except Exception:
            high = 0
        return {"total": total, "high": high, "by_module": by_mod}

    def log_canon_apply(
        self, candidate_id: str, module: str, target: str,
        field: str | None, result: str, detail: str = "",
    ) -> None:
        try:
            self._execute_write(
                "CREATE canon_apply_audit SET candidate_id=$c, module=$m, target=$t, "
                "field=$f, result=$r, detail=$d",
                {
                    "c": candidate_id, "m": module, "t": target,
                    "f": field, "r": result, "d": (detail or "")[:500],
                },
            )
        except Exception:
            pass

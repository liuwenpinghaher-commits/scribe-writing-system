"""SurrealStore mixin: unverified_ingest (split from store/misc.py)."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403


class UnverifiedIngestMixin:
    def grant_public(self, fact_id: str, chapter: int) -> None:
        """给所有角色发一条 given 知识边(事务内执行)。"""
        _, plocal = _split(fact_id)
        stmts = []
        for c in self.characters():
            ctbl, clocal = _split(c.id)
            stmts.append(
                f"RELATE {ctbl}:`{clocal}`->knows->proposition:`{plocal}` "
                f"SET since_chapter={chapter}, acquired_via='given'")
        if stmts:
            surql = "BEGIN TRANSACTION; " + "; ".join(stmts) + "; COMMIT TRANSACTION;"
            self._raw_query(surql)

    def add_unverified_ref(self, name: str, seq: int, role: str) -> None:
        """登记 ingest 抽到的库外角色名→待确认(不建实体、不发边)。

        - 解析残片(is_garbage_character_name)直接丢弃，不灌 pending
        - 同名已有 pending → 不重复建行（防 re-ingest 炸出 8 条沈砚之）
        - 同名已被人裁决(ignored/accepted) → 决策跨 re-ingest 存活(C-3)
        """
        n = (name or "").strip()
        if not n:
            return
        try:
            from scribe3.canon_inbox import is_garbage_character_name
            if is_garbage_character_name(n):
                return
        except Exception:
            pass
        decided = self._query(
            "SELECT id FROM ingest_unverified WHERE name=$n AND status != 'pending' LIMIT 1",
            {"n": n})
        if decided:
            return
        pending = self._query(
            "SELECT id FROM ingest_unverified WHERE name=$n AND status='pending' LIMIT 1",
            {"n": n})
        if pending:
            return
        self._execute_write(
            "CREATE ingest_unverified SET name=$n, seq=$s, role=$r, status='pending'",
            {"n": n, "s": seq, "r": role})

    def set_unverified_status(self, uid: str, status: str) -> None:
        """裁决待确认条目(pending→ignored/accepted;accept 的建实体流程在 accept_unverified)。"""
        self._execute_write(
            "UPDATE type::record('ingest_unverified',$uid) SET status=$st",
            {"uid": uid, "st": status})

    def list_unverified(self, status: str = "pending") -> list[dict]:
        """列待确认条目(pending/accepted/ignored)。"""
        return self._query(
            "SELECT meta::id(id) AS id, name, seq, role, status "
            "FROM ingest_unverified WHERE status=$st", {"st": status})

    def accept_unverified(self, uid: str, complete_fn=None) -> dict:
        """接受待确认引用:若 role:{name} 不存在则建角色,标记该行 accepted,并重放该章 ingest 回填被阻塞的知识。

        Args:
            uid: ingest_unverified 行的 id。
            complete_fn: LLM complete 函数(与 ingest_chapter 同签名 prompt→str)。
                传入时重放该章 ingest——此前因角色不存在而跳过的 learned/did 边现在得以写入。
                不传(None)时跳过 replay(角色仍建立,replayed=False)。

        Returns:
            {created: bool, oid: str, replayed: bool}
            replay 失败时 fail-soft:角色建立 + status=accepted 保留,replayed=False。
        """
        rows = self._query(
            "SELECT name, seq FROM type::record('ingest_unverified', $u)", {"u": uid})
        if not rows:
            return {"created": False, "oid": "", "replayed": False}
        name = rows[0]["name"]
        seq = rows[0].get("seq")
        oid = f"role:{name}"
        created = self.entity(oid) is None
        if created:
            from scribe3.ontology import Entity
            self.add_entity(Entity(oid, "character", name))
        self._execute_write(
            "UPDATE type::record('ingest_unverified', $u) SET status='accepted'", {"u": uid})

        # 重放该章 ingest:现在角色已存在,_resolve_char 不再跳过,被阻塞的知识边得以回填
        replayed = False
        if complete_fn is not None and seq is not None:
            import logging
            try:
                from scribe3.ingest import ingest_chapter
                work = getattr(self, "db_name", None) or "main"
                # 接受待确认角色后须强制重放（即使同指纹）
                r = ingest_chapter(self, seq, complete_fn, work=work, force=True)
                replayed = not r.get("parse_failed", False) and not r.get("skipped")
            except Exception as e:
                logging.getLogger("scribe3.store").warning(
                    "accept_unverified uid=%s seq=%s replay 失败(soft): %s", uid, seq, e)

        return {"created": created, "oid": oid, "replayed": replayed}

    def ignore_unverified(self, uid: str) -> None:
        """将待确认行标记为 ignored。"""
        self._execute_write(
            "UPDATE type::record('ingest_unverified', $u) SET status='ignored'", {"u": uid})

    def dedupe_unverified_pending(self) -> dict:
        """pending 同名只留一条（先见者保留），其余 ignored。"""
        rows = self.list_unverified("pending") or []
        seen: set[str] = set()
        kept = 0
        removed = 0
        for r in rows:
            name = (r.get("name") or "").strip()
            uid = r.get("id")
            if not uid:
                continue
            if not name:
                try:
                    self.ignore_unverified(uid)
                    removed += 1
                except Exception:
                    pass
                continue
            if name in seen:
                try:
                    self.ignore_unverified(uid)
                    removed += 1
                except Exception:
                    pass
            else:
                seen.add(name)
                kept += 1
        return {"ok": True, "kept": kept, "removed": removed}


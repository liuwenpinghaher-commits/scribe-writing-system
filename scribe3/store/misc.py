"""SurrealStore mixin: residual cross-cutting helpers (owned leftovers).

Ownership / where new code should go instead
--------------------------------------------
- **Motifs** → ``store/motifs.py``
- **Ingest unverified + grant_public** → ``store/unverified_ingest.py``
- **Progress / stats / allow lists** → ``store/progress_stats.py``
- **Character arc / OOC / setting completeness** → ``store/character_arc.py``
- **Context sessions / memory list** still here until graduated to
  ``context_store`` / ``chat_ai`` aggregates; do **not** add new domain tables here.

ARCHITECTURE_SPLIT_ROADMAP Phase C.
"""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403


class MiscMixin:
    def all_entities(self) -> list[Entity]:
        """角色 + 地点(前端结构面/实体清单用)。"""
        prows = self._query("SELECT meta::id(id) AS local, name FROM place")
        return self.characters() + [Entity(f"place:{r['local']}", "place", r["name"]) for r in prows]

    def upsert_chief_digest(self, day: str, body: str, error: str | None = None) -> None:
        """P2:每日创作摘报一天一行(重跑覆盖);error 非空=部分失败源,收件箱如实显示。"""
        self._execute_write(
            "DELETE chief_digest WHERE day=$d; "
            "CREATE chief_digest SET work=$w, day=$d, body=$b, error=$e RETURN NONE",
            {"d": day, "w": self.db_name, "b": body, "e": error})

    def latest_chief_digest(self) -> dict | None:
        rows = self._query(
            "SELECT work, day, body, error, (IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at "
            "FROM chief_digest ORDER BY day DESC LIMIT 1")
        return rows[0] if rows else None

    def get_distill_marker(self, chapter: int) -> dict | None:
        rows = self._query(
            "SELECT chapter, msg_count, last_turn FROM type::thing('distill_marker',$c)",
            {"c": chapter})
        return rows[0] if rows else None

    def set_distill_marker(self, chapter: int, msg_count: int, last_turn: str) -> None:
        self._execute_write(
            "UPSERT type::thing('distill_marker',$c) SET chapter=$c, msg_count=$n, "
            "last_turn=$t, ts=time::now()",
            {"c": chapter, "n": msg_count, "t": last_turn or ""})

    def list_style_profiles(self) -> list[dict]:
        import json
        rows = self._query(
            "SELECT seq, profile FROM style_profile ORDER BY seq ASC")
        out = []
        for r in rows:
            try:
                p = json.loads(r.get("profile") or "{}")
            except Exception:
                # U-011:JSON 损坏≠没数据(序列化侧真 bug)。log.error 让损坏可见,不静默当空。
                logging.getLogger("scribe3").error(
                    "style_profile JSON 损坏 seq=%s: %r", r.get("seq"), r.get("profile"), exc_info=True)
                p = {}
            out.append({"seq": r.get("seq"), **p})
        return out

    def update_record(self, oid: str, fields: dict) -> None:
        t, l = _split(oid)
        self._update_by(t, l, fields)

    def exists(self, oid: str) -> bool:
        """只读存在性检查(写前 404 校验用)。"""
        try:
            t, l = _split(oid)
        except (KeyError, ValueError):
            return False
        rows = self._query("SELECT id FROM type::thing($tbl,$local) LIMIT 1",
                           {"tbl": t, "local": l})
        return bool(rows)

    def record_lifecycle_impact(self, oid: str) -> dict | None:
        """对象删除影响计数。返回 None 表示对象不存在。"""
        if not self.exists(oid):
            return None
        table, local = _split(oid)
        rid = RecordID(table, local)
        counts: dict[str, int] = {}
        label = oid
        if oid.startswith("role:"):
            ent = self.entity(oid)
            label = ent.name if ent else oid
            counts["proposition"] = len(self._query(
                "SELECT id FROM proposition WHERE entity_id=$oid", {"oid": oid}))
            try:
                counts["knowledge_edge"] = len(self._query(
                    "SELECT id FROM knows WHERE in=$rid", {"rid": rid}))
            except Exception:
                counts["knowledge_edge"] = 0
            try:
                counts["event_involvement"] = len(self._query(
                    "SELECT id FROM involves WHERE out=$rid", {"rid": rid}))
            except Exception:
                counts["event_involvement"] = 0
        elif oid.startswith("fact:"):
            fact = self.fact(oid)
            label = f"{fact.entity_id}·{fact.attribute}" if fact else oid
            try:
                counts["knowledge_edge"] = len(self._query(
                    "SELECT id FROM knows WHERE out=$rid", {"rid": rid}))
            except Exception:
                counts["knowledge_edge"] = 0
            counts["reader_knowledge"] = len(self._query(
                "SELECT id FROM reader_knows WHERE proposition=$rid", {"rid": rid}))
            try:
                counts["event_effect"] = len(self._query(
                    "SELECT id FROM causes WHERE out=$rid", {"rid": rid}))
            except Exception:
                counts["event_effect"] = 0
        return {"object": {"id": oid, "label": label}, "counts": counts}

    def delete_record(self, oid: str, cleanup_refs: bool = False) -> bool:
        if not self.exists(oid):
            return False
        if cleanup_refs:
            self._cleanup_record_refs(oid)
        t, l = _split(oid)
        self._delete_by(t, l)
        return True

    def create_context_session(self, work: str, actor_id: str, device_id: str,
                               thread_id: str | None = None) -> dict:
        """开一个上下文会话并落 revision=0 的初始快照,返回初始快照 dict。

        session 与初始快照在同一条事务里创建:不存在"有 session 无快照"的中间态,
        get_context_snapshot 对新会话永远有得读。

        Task 6 兑现:thread_id 取自本 work 的正式主编线程(get_or_create_editorial_thread,
        幂等)——create_context_session / backfill_thread_ids / list_thread_messages 三处
        共用同一 ethread id,前端 snapshot.thread_id 与 /chat/threads、backfill 归档端到端一致
        (此前占位 thread:{work}_default 与 ethread 命名空间断裂,旧对话在 UI 上凭空消失)。

        如实说明:本方法非幂等——_context_tx 的连接重试若落在"首次已提交、
        响应丢失"的窗口,重放会以同 id CREATE 撞库报错(本机 WS 该窗口极小,
        与 store 既有论断一致,可接受;调用方收到错误重新 create 即可)。"""
        from datetime import datetime, timezone
        from uuid import uuid4
        sid = uuid4().hex
        snap_id = uuid4().hex
        # P0a:thread_id 给定(作者选了会话)→ 快照绑该线程;未给=既有行为(active 默认线程)。
        # 有效性由端点层 _resolve_thread_or_raise 把关(零降级:无效 404/409,不静默回落)。
        thread_id = thread_id or self.get_or_create_editorial_thread(work, actor_id)["thread_id"]
        snap = ContextSnapshot(
            session_id=sid, work=work, revision=0, thread_id=thread_id,
            entry="manuscript", directory_path=(),
            focus=ContextFocus(type="entry", id="entry:manuscript", label=""),
            detail_route="entry:manuscript", chapter=None, phase=None,
            focalizer=None, previous_revision=None, navigation_id="init",
            captured_at=datetime.now(timezone.utc), context_hash="",
        ).with_hash()   # hash 在 Python 侧算好落库,库里存最终值
        payload = snap.model_dump(mode="json")
        self._context_tx(
            "BEGIN TRANSACTION; "
            "CREATE type::thing('context_session', $sid) SET work=$work, "
            "actor_id=$actor, device_id=$device, thread_id=$thread, status='active', "
            "revision=0, current_snapshot_id=$snap_id, updated_at=time::now(); "
            "CREATE type::thing('context_snapshot', $snap_id) SET session_id=$sid, "
            "work=$work, revision=0, previous_revision=NONE, navigation_id='init', "
            "thread_id=$thread, entry=$entry, directory_path=$path, focus=$focus, "
            "detail_route=$route, chapter=NONE, phase=NONE, focalizer=NONE, "
            "reason='restore', context_hash=$hash; "
            "COMMIT TRANSACTION;",
            {"sid": sid, "work": work, "actor": actor_id, "device": device_id,
             "thread": thread_id, "snap_id": snap_id, "entry": payload["entry"],
             "path": payload["directory_path"], "focus": payload["focus"],
             "route": payload["detail_route"], "hash": payload["context_hash"]})
        # reason 不在 ContextSnapshot 模型里(它是导航属性),但落库并随 dict 返回
        return payload | {"reason": "restore"}

    def advance_context(self, session_id: str, intent: dict) -> dict:
        """CAS 推进上下文:仅当 session 处于 active 且 revision == expected_revision
        时创建新快照并推进游标;失配抛 StaleContextError(带 latest),绝不自动覆盖。

        幂等合同:同 navigation_id 一律视为重放——新 payload 被【忽略】,以先落库的
        快照为准(payload 不一致仅 log warning)。重放路径有三层:
        ① 预查命中 → 直接返回;注意预查先于 ended 守卫——已 ended 的会话重放
          已有 navigation_id 仍幂等返回旧快照而非拒绝(只有"推进出新快照"才被拒);
        ② 并发重放对方已提交时,后到者的事务撞的是 stale THROW(IF 判定在 CREATE
          之前,轮不到唯一索引)——故 stale/冲突分支都先按 navigation 读回,命中
          即幂等成功,读不回才是真 stale(实测修正:唯一索引只是极端兜底);
        ③ UNIQUE(session_id, navigation_id) 索引兜底剩余竞态,冲突同样转读回。"""
        from datetime import datetime, timezone
        from uuid import uuid4
        it = NavigationIntent.model_validate(intent)
        # 1. 幂等预查:该导航已落库 → 直接返回(顺序重放的快路径)
        existing = self._find_context_snapshot_by_navigation(session_id, it.navigation_id)
        if existing is not None:
            self._warn_context_replay_mismatch(existing, it)
            return existing
        # 2. 读会话拿 work/thread_id(不在这里判 revision——判定必须进事务)
        sess = self._query(
            "SELECT work, thread_id FROM type::thing('context_session', $sid)",
            {"sid": session_id})
        if not sess:
            raise ValueError(f"advance_context: context_session '{session_id}' 不存在")
        new_rev = it.expected_revision + 1
        snap_id = uuid4().hex
        snap = ContextSnapshot(
            session_id=session_id, work=sess[0]["work"], revision=new_rev,
            thread_id=sess[0]["thread_id"], entry=it.entry,
            directory_path=tuple(it.directory_path), focus=it.focus,
            detail_route=it.detail_route, chapter=it.chapter, phase=it.phase,
            focalizer=it.focalizer, previous_revision=it.expected_revision,
            navigation_id=it.navigation_id,
            captured_at=datetime.now(timezone.utc), context_hash="",
        ).with_hash()
        payload = snap.model_dump(mode="json")
        # 3. 单事务 CAS:读-判-写在同一条多语句 SurrealQL 里完成
        try:
            self._context_tx(
                "BEGIN TRANSACTION; "
                "LET $cur = (SELECT revision, status "
                "FROM type::thing('context_session', $sid)); "
                "IF array::len($cur) == 0 { THROW 'context_session_missing' }; "
                # I-2:ended 守卫——已结束的会话拒绝推进(end 方法由后续任务建)
                "IF $cur[0].status != 'active' { THROW 'context_session_ended' }; "
                "IF $cur[0].revision != $expected "
                "{ THROW 'stale_revision:' + <string>$cur[0].revision }; "
                "CREATE type::thing('context_snapshot', $snap_id) SET session_id=$sid, "
                "work=$work, revision=$rev, previous_revision=$prev, navigation_id=$nav, "
                "thread_id=$thread, entry=$entry, directory_path=$path, focus=$focus, "
                "detail_route=$route, chapter=$chapter, phase=$phase, "
                "focalizer=$focalizer, reason=$reason, context_hash=$hash; "
                "UPDATE type::thing('context_session', $sid) SET revision=$rev, "
                "current_snapshot_id=$snap_id, updated_at=time::now(); "
                "COMMIT TRANSACTION;",
                {"sid": session_id, "expected": it.expected_revision,
                 "snap_id": snap_id, "work": payload["work"], "rev": new_rev,
                 "prev": it.expected_revision, "nav": it.navigation_id,
                 "thread": payload["thread_id"], "entry": payload["entry"],
                 "path": payload["directory_path"], "focus": payload["focus"],
                 "route": payload["detail_route"], "chapter": it.chapter,
                 "phase": it.phase, "focalizer": it.focalizer,
                 "reason": it.reason, "hash": payload["context_hash"]})
        except _CONN_ERRORS:
            raise   # 连接类异常已在 _context_tx 重试过一次,再失败原样上抛
        except Exception as e:
            msg = str(e)
            kind = self._classify_context_tx_error(msg)
            if kind in ("stale", "unique_conflict", "commit_conflict"):
                # I-1:三类都可能是同 navigation 的并发重放——对方已提交时,
                # 后到者的事务在 IF 处撞 stale THROW(轮不到唯一索引),直接抛
                # 就是给重放请求喂假 409。先按 navigation 读回,命中即幂等成功。
                replay = self._find_context_snapshot_by_navigation(
                    session_id, it.navigation_id)
                if replay is not None:
                    self._warn_context_replay_mismatch(replay, it)
                    return replay
                # 读不回才是真 CAS 失配(含提交层读写冲突/revision 唯一键被抢):
                # actual 优先取 THROW 携带的值,否则回读会话
                m = re.search(r"stale_revision:(\d+)", msg)
                if m:
                    actual = int(m.group(1))
                else:
                    cur = self._query(
                        "SELECT revision FROM type::thing('context_session', $sid)",
                        {"sid": session_id})
                    actual = cur[0]["revision"] if cur else -1
                # latest 带上服务端最新快照,前端可直接对齐免再读
                raise StaleContextError(
                    it.expected_revision, actual,
                    latest=self.get_context_snapshot(session_id)) from e
            if kind == "session_missing":
                raise ValueError(
                    f"advance_context: context_session '{session_id}' 不存在") from e
            if kind == "session_ended":
                raise ValueError(
                    f"advance_context: context_session '{session_id}' 已结束"
                    "(status != 'active'),拒绝推进") from e
            raise
        return payload | {"reason": it.reason}

    def get_context_snapshot(self, session_id: str, revision: int | None = None) -> dict | None:
        """读快照:revision=None 返回 current(经 current_snapshot_id,悬空时兜底
        取最大 revision);指定 revision 返回该历史版;找不到返回 None。"""
        if revision is not None:
            rows = self._query(
                f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} FROM context_snapshot "
                "WHERE session_id=$sid AND revision=$rev LIMIT 1",
                {"sid": session_id, "rev": int(revision)})
            return rows[0] if rows else None
        sess = self._query(
            "SELECT current_snapshot_id FROM type::thing('context_session', $sid)",
            {"sid": session_id})
        if not sess:
            return None
        snap_id = sess[0].get("current_snapshot_id")
        if snap_id:
            rows = self._query(
                f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} "
                "FROM type::thing('context_snapshot', $snap)",
                {"snap": snap_id})
            if rows:
                return rows[0]
        # 兜底:current_snapshot_id 缺失/悬空时取最大 revision
        # (3.x ORDER BY 必须引用选择列——revision 在选择列里,合规)
        rows = self._query(
            f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} FROM context_snapshot "
            "WHERE session_id=$sid ORDER BY revision DESC LIMIT 1",
            {"sid": session_id})
        return rows[0] if rows else None

    def list_memories(self, kind: str | None = None, work: str | None = None,
                      scope_type: str | None = None, status: str | None = "active") -> list[dict]:
        """列经验记忆(默认 active),按 created_at 降序。含 provenance/linked_ids(活化字段)。"""
        where: list[str] = []
        vars: dict = {}
        if kind:
            where.append("kind=$k")
            vars["k"] = kind
        if work:
            where.append("work=$w")
            vars["w"] = work
        if scope_type:
            where.append("scope_type=$sc")
            vars["sc"] = scope_type
        if status:
            where.append("status=$st")
            vars["st"] = status
        w = ("WHERE " + " AND ".join(where) + " ") if where else ""
        # 3.x:ORDER BY 必须引用选择列,故显式把 created_at 纳入投影(_MEMORY_COLS 不含)。
        return self._query(
            f"SELECT {self._MEMORY_COLS}, (IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at "
            f"FROM memory_item {w}ORDER BY created_at DESC", vars)

    def resolve_temporal_view(self, work: str, chapter: int | None,
                              focalizer: str | None = None,
                              *, kind: str | None = None) -> list[dict]:
        """把 work 下的 active 经验记忆按 (chapter, focalizer) 投影为可见子集。
        focalizer=None → 只按 story_time(故事真值 / 全知视角);
        focalizer 非空 → 在 story_time 之上叠加 knowledge_time 限知门(该聚焦角色此刻能否知道)。
        投影判定下沉到 memory_lifecycle.resolve_temporal_view(与检索限知门同源)。"""
        where = ["work=$w", "status='active'"]
        vars: dict = {"w": work}
        if kind:
            where.append("kind=$k")
            vars["k"] = kind
        rows = self._query(
            f"SELECT {self._MEMORY_COLS} FROM memory_item WHERE {' AND '.join(where)}", vars)
        return _resolve_view(rows or [], chapter, focalizer)

    def add_pending_authority_claim(self, work: str, text: str, *,
                                    entity: str | None = None, attribute: str | None = None,
                                    value: str | None = None, source_type: str = "",
                                    source_id: str = "", thread_id: str | None = None) -> str:
        """把正典揭示(真实身份等)入【待审】队列——绝不直接进领域表,更不进 memory_item。
        领域表仍是 fact 唯一真相源,作者审批后再由既有 ingest/命题写入路径落库。"""
        # P1 幂等根治(对齐 add_memory_item):按确定性键 (work, source_type, source_id) 预查去重。
        # 崩溃窗口后事件落 failed → consolidate 重 drain,以 source_id=event_id 再路由至此;
        # 裸 CREATE 会产生重复待审(同 text 两行)。source_id 非空时预查命中即返回旧 id,不新建。
        if source_id:
            _dup = self._query(
                "SELECT meta::id(id) AS id FROM pending_authority_claim "
                "WHERE work=$w AND source_type=$st AND source_id=$sid LIMIT 1",
                {"w": work, "st": source_type or "", "sid": source_id})
            if _dup:
                return _dup[0]["id"]
        rows = self._query(
            "CREATE pending_authority_claim SET work=$w, thread_id=$tid, text=$text, "
            "entity=$entity, attribute=$attribute, value=$value, "
            "source_type=$st, source_id=$sid, status='pending'",
            {"w": work, "tid": thread_id, "text": text or "",
             "entity": entity, "attribute": attribute, "value": value,
             "st": source_type or "", "sid": source_id or ""})
        rid = (rows[0] if rows else {}).get("id")
        s = str(rid)
        return s.split(":")[-1] if ":" in s else s

    def list_pending_authority_claims(self, work: str | None = None,
                                      status: str | None = "pending") -> list[dict]:
        """列待审正典揭示(默认 pending),按 created_at 升序(先到先审)。"""
        where: list[str] = []
        vars: dict = {}
        if work:
            where.append("work=$w")
            vars["w"] = work
        if status:
            where.append("status=$st")
            vars["st"] = status
        w = ("WHERE " + " AND ".join(where) + " ") if where else ""
        return self._query(
            f"SELECT {self._PENDING_CLAIM_FIELDS} FROM pending_authority_claim {w}"
            "ORDER BY created_at ASC", vars)

    def resolve_pending_authority_claim(
            self, claim_id: str, decision: str, *,
            valid_from: int = 1, secret: bool = False) -> dict:
        """关闭待审队列:approve → 写入 proposition 正典;reject → 仅改 status。
        decision 受控:approve|reject。仅 status=pending 可解析;已关闭返回 no-op 信息。"""
        decision = (decision or "").strip().lower()
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be approve or reject")
        cid = (claim_id or "").strip()
        if ":" in cid:
            cid = cid.split(":")[-1]
        rows = self._query(
            f"SELECT {self._PENDING_CLAIM_FIELDS} FROM type::thing('pending_authority_claim', $id)",
            {"id": cid})
        if not rows:
            raise ValueError(f"pending claim not found: {claim_id}")
        row = rows[0]
        if (row.get("status") or "pending") != "pending":
            return {"status": row.get("status"), "claim_id": cid, "noop": True}
        if decision == "reject":
            self._execute_write(
                "UPDATE type::thing('pending_authority_claim', $id) SET status='rejected'",
                {"id": cid})
            return {"status": "rejected", "claim_id": cid, "fact_id": None}
        # approve → 落命题。产品 capture 常只带 text、entity 空:
        # 用可解析回落(world:待审揭示 + text 作 value),避免队列黑洞。
        entity = (row.get("entity") or "").strip()
        attribute = (row.get("attribute") or "").strip() or "揭示"
        value = (row.get("value") or row.get("text") or "").strip()
        if not entity:
            entity = "world:待审揭示"
        if not value:
            raise ValueError(
                "approve requires value or text on the pending claim")
        import uuid
        from scribe3.ontology import Fact
        fact_id = f"fact:pa-{uuid.uuid4().hex[:10]}"
        self.add_fact(Fact(fact_id, entity, attribute, value,
                           valid_from=int(valid_from), secret=bool(secret)))
        self._execute_write(
            "UPDATE type::thing('pending_authority_claim', $id) SET status='approved'",
            {"id": cid})
        return {"status": "approved", "claim_id": cid, "fact_id": fact_id}

    def count_active_context_sessions(self) -> int:
        """runtime-status 指标(Task 16-B):本库仍活跃的上下文会话数(轻量计数,不载快照)。"""
        rows = self._query(
            "SELECT count() AS n FROM context_session WHERE status='active' GROUP ALL")
        return int(rows[0]["n"]) if rows else 0


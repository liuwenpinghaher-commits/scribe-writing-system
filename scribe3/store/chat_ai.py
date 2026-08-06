"""SurrealStore mixin: chat_ai."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class ChatAiMixin:

    def add_chat_message(self, chapter: int, stage: str, role: str, text: str,
                         turn: str = "", trace: dict | None = None, *,
                         thread_id: str | None = None,
                         context_session_id: str | None = None,
                         context_revision: int | None = None,
                         context_hash: str | None = None,
                         focus: dict | None = None,
                         response_id: str | None = None) -> None:
        """追加一条对话留痕;work 用本库名自动填(D-002),ts 由 DB 侧 time::now()。
        turn(P0门审查 P2-6):同一轮 user/assistant 共享的配对 id,防并发会话交错
        污染蒸馏原料(任务8);空串=未知轮(兼容旧行/直写调用方)。

        Task 6:新增关键字参数(全默认 None,向后兼容——旧调用方一字不改仍生效):
        thread_id 挂主编线程(一 work 一连续线程);context_* 是本轮的上下文绑定
        游标(revision/hash/session);focus 是本轮的焦点标签(切焦点不切线程);
        response_id 是本轮 LLM 响应 id。None 一律落 NONE(option 字段,存量行不受影响)。"""
        self._execute_write(
            "CREATE chat_message SET work=$w, chapter=$c, stage=$s, role=$r, text=$t, "
            "turn=$turn, trace=$trace, thread_id=$thread_id, "
            "context_session_id=$ctx_sid, context_revision=$ctx_rev, "
            "context_hash=$ctx_hash, focus=$focus, response_id=$resp_id, "
            "ts=time::now() RETURN NONE",
            {"w": self.db_name, "c": chapter, "s": stage or "", "r": role, "t": text,
             "turn": turn or "", "trace": trace or {}, "thread_id": thread_id,
             "ctx_sid": context_session_id, "ctx_rev": context_revision,
             "ctx_hash": context_hash, "focus": focus, "resp_id": response_id})

    def list_chat_messages(self, chapter: int | None = None, limit: int = 500) -> list[dict]:
        """按章(缺省全部)拉取对话留痕,ts 升序返回;limit 取**最新** N 条再反转
        (P0门审查 P2-6:此前 ASC LIMIT 取最老 N 条,超量后回看永远读不到新对话);
        limit 夹取 [1,2000] 防 SurrealQL 非法值 500。"""
        n = max(1, min(int(limit), 2000))
        where = "WHERE chapter = $c " if chapter is not None else ""
        rows = self._query(
            f"SELECT {self._CHAT_MESSAGE_FIELDS} "
            f"FROM chat_message {where}ORDER BY ts DESC LIMIT {n}",
            {"c": chapter})
        return list(reversed(rows))

    def _get_editorial_thread(self, thread_id: str) -> dict | None:
        rows = self._query(
            f"SELECT {self._EDITORIAL_THREAD_FIELDS} FROM editorial_thread "
            "WHERE thread_id=$tid LIMIT 1", {"tid": thread_id})
        return rows[0] if rows else None

    def get_or_create_editorial_thread(self, work: str, actor_id: str) -> dict:
        """取或建本 work + actor 的活跃主编线程(一 work 一连续线程,幂等)。

        已有 active 线程(最早创建者,稳定不漂)直接返回;无则建默认线程。
        thread_id 全局唯一(ethread:<work>:<uuid>),隔离仍靠 per-work db。

        actor_id 语义:线程按 (work, actor_id) 定活跃线程——当前单作者场景恒传
        "author"(见调用方 backfill/create_context_session),即"一 work 一 author 线程"。
        将来多 actor(协作/多设备各自成线)时,不同 actor_id 各得一条活跃线程,
        本方法无需改动;届时需上层决定 snapshot 该绑哪个 actor 的线程。"""
        from uuid import uuid4
        rows = self._query(
            f"SELECT {self._EDITORIAL_THREAD_FIELDS} FROM editorial_thread "
            "WHERE work=$w AND actor_id=$a AND status='active' "
            "ORDER BY created_at ASC LIMIT 1", {"w": work, "a": actor_id})
        if rows:
            return rows[0]
        tid = f"ethread:{work}:{uuid4().hex}"
        self._execute_write(
            "CREATE editorial_thread SET thread_id=$tid, work=$w, actor_id=$a, "
            "parent_thread_id=NONE, title=$title, status='active', "
            "hermes_conversation_id=NONE, previous_response_id=NONE, summary='', "
            "created_at=time::now(), updated_at=time::now() RETURN NONE",
            {"tid": tid, "w": work, "a": actor_id, "title": "主编讨论"})
        return self._get_editorial_thread(tid)

    def update_thread_response_id(self, thread_id: str, response_id: str | None,
                                  conversation_id: str | None = None) -> None:
        """Task 11:一轮 Responses 完成后,把新 response id(可选 conversation id)写回线程。

        为什么:previous_response_id 是下一轮 Hermes 服务端会话续接锚。**设计约束**——
        Hermes Responses 服务端存储 LRU 100 条,长线程必然掉链;此处只是"尽力续接",掉链后
        由 list_thread_messages + working summary 重建,不依赖 Hermes 端无限续接。

        幂等/健壮:response_id 为空则不动 previous_response_id(不覆盖已有锚为 NONE);
        conversation_id 缺省不改。线程不存在时 UPDATE 空操作(不抛),调用方 fail-soft。"""
        if not response_id and not conversation_id:
            return
        sets = []
        params: dict = {"tid": thread_id}
        if response_id:
            sets.append("previous_response_id=$resp")
            params["resp"] = response_id
        if conversation_id:
            sets.append("hermes_conversation_id=$conv")
            params["conv"] = conversation_id
        sets.append("updated_at=time::now()")
        self._execute_write(
            f"UPDATE editorial_thread SET {', '.join(sets)} "
            "WHERE thread_id=$tid RETURN NONE", params)

    def list_editorial_threads(self, work: str) -> list[dict]:
        """列本 work 的全部主编线程(含分支),按创建时间升序。"""
        return self._query(
            f"SELECT {self._EDITORIAL_THREAD_FIELDS} FROM editorial_thread "
            "WHERE work=$w ORDER BY created_at ASC", {"w": work})

    def list_thread_messages(self, thread_id: str, limit: int = 500,
                             before_ts: str | None = None) -> list[dict]:
        """按线程拉取对话留痕,ts 升序返回;limit 取最新 N 条再反转(同 list_chat_messages)。
        P0b:before_ts(ISO 字符串)给定时只取更早的消息——前端「载入更早」分页游标。
        隔离:只读本 store 的 db,别的 work 的 thread_id 在此库无消息 → 返回 []。"""
        n = max(1, min(int(limit), 2000))
        if before_ts:
            rows = self._query(
                f"SELECT {self._CHAT_MESSAGE_FIELDS} FROM chat_message "
                f"WHERE thread_id=$tid AND ts < type::datetime($before) "
                f"ORDER BY ts DESC LIMIT {n}", {"tid": thread_id, "before": before_ts})
        else:
            rows = self._query(
                f"SELECT {self._CHAT_MESSAGE_FIELDS} FROM chat_message "
                f"WHERE thread_id=$tid ORDER BY ts DESC LIMIT {n}", {"tid": thread_id})
        return list(reversed(rows))

    def set_thread_summary(self, thread_id: str, summary: str, upto_ts: str) -> None:
        """P0b:写线程增量摘要 + 覆盖游标,并清 summary_error(成功即清,防红字常驻)。"""
        self._execute_write(
            "UPDATE editorial_thread SET summary=$s, summarized_upto_ts=$u, "
            "summary_error=NONE, updated_at=time::now() WHERE thread_id=$tid RETURN NONE",
            {"s": summary, "u": upto_ts, "tid": thread_id})

    def set_thread_summary_error(self, thread_id: str, error: str) -> None:
        """P0b:摘要生成失败标记(前端摘要卡红字)。旧 summary 保留,下轮重试。"""
        self._execute_write(
            "UPDATE editorial_thread SET summary_error=$e, updated_at=time::now() "
            "WHERE thread_id=$tid RETURN NONE", {"e": error, "tid": thread_id})

    def create_editorial_thread(self, work: str, actor_id: str,
                                title: str | None = None) -> dict:
        """显式新建主编线程(P0a 多会话):与 get_or_create 不同,每次都建新的。
        默认标题「新会话」——首条 user 消息落库时由 maybe_autotitle_thread 自动改名。"""
        from uuid import uuid4
        tid = f"ethread:{work}:{uuid4().hex}"
        self._execute_write(
            "CREATE editorial_thread SET thread_id=$tid, work=$w, actor_id=$a, "
            "parent_thread_id=NONE, title=$title, status='active', "
            "hermes_conversation_id=NONE, previous_response_id=NONE, summary='', "
            "created_at=time::now(), updated_at=time::now() RETURN NONE",
            {"tid": tid, "w": work, "a": actor_id,
             "title": (title or "").strip() or "新会话"})
        return self._get_editorial_thread(tid)

    def update_editorial_thread_meta(self, thread_id: str, *,
                                     title: str | None = None,
                                     status: str | None = None) -> None:
        """改名/归档(P0a):只改传入字段。status 合法值 active|archived(调用方校验)。"""
        sets, params = ["updated_at=time::now()"], {"tid": thread_id}
        if title is not None:
            sets.append("title=$title")
            params["title"] = title
        if status is not None:
            sets.append("status=$status")
            params["status"] = status
        self._execute_write(
            f"UPDATE editorial_thread SET {', '.join(sets)} "
            "WHERE thread_id=$tid RETURN NONE", params)

    def maybe_autotitle_thread(self, thread_id: str, first_user_text: str) -> None:
        """P0a:首条 user 消息自动命名(截 24 字)。仅当标题仍是默认值时改——
        改过名/自动命名过的线程不再动(幂等,零 LLM,零降级:纯库内两条小查询,失败上抛)。"""
        row = self._get_editorial_thread(thread_id)
        if row is None or (row.get("title") or "") not in self._AUTOTITLE_DEFAULTS:
            return
        text = (first_user_text or "").strip().replace("\n", " ")[:24]
        if text:
            self.update_editorial_thread_meta(thread_id, title=text)

    def fork_editorial_thread(self, parent_thread_id: str,
                              title: str | None = None) -> dict:
        """显式分支:以 parent_thread_id 为父建新活跃线程(导航路径绝不调此)。
        actor_id/work 继承父线程;title 缺省沿用父标题。

        子线程消息从空开始,但 **summary 继承父线程**(P0a:分支不失忆——
        prompt 注入层能带上父线程的早期上下文);需要逐条父历史由上层显式携带。"""
        from uuid import uuid4
        parent = self._get_editorial_thread(parent_thread_id)
        if parent is None:
            raise ValueError(f"fork_editorial_thread: 父线程 '{parent_thread_id}' 不存在")
        tid = f"ethread:{parent['work']}:{uuid4().hex}"
        self._execute_write(
            "CREATE editorial_thread SET thread_id=$tid, work=$w, actor_id=$a, "
            "parent_thread_id=$parent, title=$title, status='active', "
            "hermes_conversation_id=NONE, previous_response_id=NONE, summary=$sum, "
            "created_at=time::now(), updated_at=time::now() RETURN NONE",
            {"tid": tid, "w": parent["work"], "a": parent["actor_id"],
             "parent": parent_thread_id,
             "title": title or parent.get("title") or "主编讨论",
             "sum": parent.get("summary") or ""})
        return self._get_editorial_thread(tid)

    def backfill_thread_ids(self, actor_id: str = "author") -> int:
        """把 thread_id 为 NONE 的存量 chat_message 全部归入本 work 默认线程(幂等)。

        升级后旧对话不得从 UI 消失(纸命现网已有真实 chat_message,无 thread_id)。
        默认线程取 get_or_create_editorial_thread(db_name, actor_id="author")——与
        create_context_session 同一 ethread id,前端 snapshot.thread_id 读得到这些旧消息。
        context_revision/focus 留 NONE(存量无从追溯);再跑无变化(NONE 已被清光);
        回填前后 chat_message 总数不变(只 UPDATE 不增删)。返回本次更新条数。

        后续任务事项:pilot/loop 等写入点当前不带 thread_id,会持续产生 thread_id=NONE
        的孤儿消息——backfill 只在启动时兜底归档一次,长期应让所有 add_chat_message
        调用点显式带 thread_id(消除孤儿源头),而非依赖回填清扫。"""
        thread = self.get_or_create_editorial_thread(self.db_name, actor_id)
        tid = thread["thread_id"]
        # 只更新 thread_id 尚未设置(NONE)的行——已归属者不动 → 幂等。
        rows = self._query(
            "SELECT count() AS n FROM chat_message WHERE thread_id IS NONE GROUP ALL")
        n = int(rows[0]["n"]) if rows and rows[0].get("n") is not None else 0
        if n:
            self._execute_write(
                "UPDATE chat_message SET thread_id=$tid "
                "WHERE thread_id IS NONE RETURN NONE", {"tid": tid})
        return n

    def upsert_ai_run_trace(self, run_id: str, *, status: str | None = None,
                            session_key: str | None = None,
                            input_text: str | None = None,
                            instructions: str | None = None,
                            tool_calls: list[dict] | None = None,
                            tool_outputs: list[dict] | None = None,
                            approvals: list[dict] | None = None,
                            raw_events: list[dict] | None = None,
                            usage: dict | None = None,
                            error=None,
                            response: dict | None = None) -> None:
        existing = self.get_ai_run_trace(run_id) or {}
        existing_status = str(existing.get("status") or "")
        # collector 线程可能晚一步补写 streaming/waiting_for_approval。
        # 活跃态不得把既有 Run 终态或“审批会话已失效”覆盖掉；
        # 真实的后续 completed/failed 终态仍可正常接管 approval_expired。
        active_statuses = {"created", "streaming", "waiting_for_approval", "requires_approval"}
        sticky_statuses = {
            "completed", "completed_unverified", "failed", "stopped",
            "cancelled", "canceled", "approval_expired",
        }
        effective_status = status
        if existing_status in sticky_statuses and status in active_statuses:
            effective_status = existing_status
        payload = {
            "work": self.db_name,
            "run_id": run_id,
            "status": effective_status or existing.get("status") or "created",
            "session_key": session_key if session_key is not None else existing.get("session_key"),
            "input_text": input_text if input_text is not None else existing.get("input_text"),
            "instructions": instructions if instructions is not None else existing.get("instructions"),
            "tool_calls": tool_calls if tool_calls is not None else (existing.get("tool_calls") or []),
            "tool_outputs": tool_outputs if tool_outputs is not None else (existing.get("tool_outputs") or []),
            "approvals": approvals if approvals is not None else (existing.get("approvals") or []),
            "raw_events": raw_events if raw_events is not None else (existing.get("raw_events") or []),
            "usage": usage if usage is not None else existing.get("usage"),
            "error": error if error is not None else existing.get("error"),
            # Run 的创建、终态事件和作者审批会各自补一部分安全响应元数据。
            # 不能让晚到的 approval({status:'resumed'}) 整包覆盖终态的 model/usage/output，
            # 否则真实调用的供应商审计身份会在审批后丢失。
            "response": (
                {**existing.get("response", {}), **response}
                if isinstance(existing.get("response"), dict) and isinstance(response, dict)
                else (response if response is not None else existing.get("response"))
            ),
        }
        # Task 16-A:落库前统一 redactor——认证头(Authorization/Bearer/Basic/Proxy/api_key/
        # cookie…)与秘密事实真值在 at-rest 前抹掉。error(C-2:直取上游 4xx/5xx HTTP 文本,
        # 常回显出错的认证头)必须纳入。幂等:append_ai_run_trace_event 读回已屏蔽数据再合并
        # 重掩,已屏蔽串不再命中。
        _sv = self._secret_proposition_values()
        for _f in ("tool_calls", "tool_outputs", "raw_events", "approvals",
                   "response", "error"):
            payload[_f] = _redact_run_trace_secrets(payload[_f], _sv)
        self._execute_write(
            "UPSERT type::thing('ai_run_trace', $run) SET work=$work, run_id=$run_id, "
            "status=$status, session_key=$session_key, input_text=$input_text, "
            "instructions=$instructions, tool_calls=$tool_calls, tool_outputs=$tool_outputs, "
            "approvals=$approvals, raw_events=$raw_events, usage=$usage, error=$error, "
            "response=$response, updated_at=time::now() RETURN NONE",
            {"run": run_id, **payload},
        )

    def get_ai_run_trace(self, run_id: str) -> dict | None:
        rows = self._query(
            "SELECT work, run_id, status, session_key, input_text, instructions, "
            "tool_calls, tool_outputs, approvals, raw_events, usage, error, response, "
            # Task 13:发起时上下文绑定 + 完成快照(审批重校验/刷新恢复的事实源)
            "parent_thread_id, context_session_id, origin_context_revision, "
            "origin_context_hash, envelope_hash, focus, completion_context_revision, "
            "write_effects, stage_policy, policy_violations, tool_contract, "
            "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at, (IF updated_at IS NONE THEN NONE ELSE <string>updated_at END) AS updated_at "
            "FROM type::thing('ai_run_trace', $run)",
            {"run": run_id},
        )
        return rows[0] if rows else None

    def update_ai_run_context(self, run_id: str, **fields) -> None:
        """Task 13:写 run 的上下文绑定/完成快照字段(与既有 upsert_ai_run_trace 主体解耦,
        避免与 Task 10 的记忆改动在 store.py 撞行)。

        只 SET 传入的白名单字段(None 跳过,但 write_effects 允许显式空列表落库);
        UPSERT 在 create_run 已建行时纯合并——既有 SET 子句不触碰这些新字段,故审批/流式
        期间的状态 upsert 不会把绑定冲掉(SCHEMAFULL 下未列字段保持原值)。"""
        allowed = {
            "parent_thread_id", "context_session_id", "origin_context_revision",
            "origin_context_hash", "envelope_hash", "focus",
            "completion_context_revision", "write_effects", "stage_policy", "policy_violations",
            "tool_contract",
        }
        patch = {k: v for k, v in fields.items()
                 if k in allowed and (v is not None or k == "write_effects")}
        if not patch:
            return
        sets = ", ".join(f"{k}=${k}" for k in patch)
        self._execute_write(
            "UPSERT type::thing('ai_run_trace', $run) SET work=$work, run_id=$run_id, "
            f"{sets}, updated_at=time::now() RETURN NONE",
            {"run": run_id, "work": self.db_name, "run_id": run_id, **patch},
        )

    def list_ai_run_traces(self, limit: int = 100) -> list[dict]:
        n = max(1, min(int(limit), 1000))
        rows = self._query(
            f"SELECT work, run_id, status, session_key, input_text, tool_calls, "
            f"tool_outputs, approvals, usage, error, stage_policy, tool_contract, (IF updated_at IS NONE THEN NONE ELSE <string>updated_at END) AS updated_at "
            f"FROM ai_run_trace ORDER BY updated_at DESC LIMIT {n}",
        )
        return rows

    def usage_summary(self, days: int = 7) -> dict:
        """H-10:近 N 天 LLM token 真实用量聚合(/ai/usage 数据源)。

        数据源是两条审计链已存的 Hermes usage:chat_message.trace.usage(Responses
        写作/讨论)+ ai_run_trace.usage(Runs 写入型任务)。行数有限(留痕表按章),
        取回后在 Python 侧按天聚合——SurrealQL 嵌套字段 group-by 不值得为此冒方言坑。
        天按 ts 前 10 位(UTC 日界),与日帽台账的本地日界可能差几小时,预算展示可容忍。
        """
        n = max(1, min(int(days), 90))
        import datetime as _dt
        cutoff = (_dt.date.today() - _dt.timedelta(days=n - 1)).isoformat()
        zero = lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}  # noqa: E731
        acc: dict[str, dict] = {}

        def _add(day: str, channel: str, u) -> None:
            if not isinstance(u, dict) or not day or day < cutoff:
                return
            d = acc.setdefault(day, {"responses": zero(), "runs": zero()})
            slot = d[channel]
            slot["calls"] += 1
            slot["input_tokens"] += int(u.get("input_tokens") or u.get("prompt_tokens") or 0)
            slot["output_tokens"] += int(u.get("output_tokens") or u.get("completion_tokens") or 0)
            slot["total_tokens"] += int(u.get("total_tokens") or 0)

        for r in self._query(
                "SELECT (IF ts IS NONE THEN NONE ELSE <string>ts END) AS ts, trace.usage AS usage FROM chat_message "
                "WHERE trace.usage != NONE ORDER BY ts DESC LIMIT 5000"):
            _add((r.get("ts") or "")[:10], "responses", r.get("usage"))
        for r in self._query(
                "SELECT (IF updated_at IS NONE THEN NONE ELSE <string>updated_at END) AS ts, usage FROM ai_run_trace "
                "WHERE usage != NONE ORDER BY ts DESC LIMIT 2000"):
            _add((r.get("ts") or "")[:10], "runs", r.get("usage"))

        days_out = []
        for day in sorted(acc, reverse=True):
            d = acc[day]
            total = zero()
            for ch in ("responses", "runs"):
                for k in total:
                    total[k] += d[ch][k]
            days_out.append({"day": day, **d, "total": total})
        return {"days": days_out, "since": cutoff}

    def add_lesson(self, chapter: int, kind: str, text: str, condition: str = "",
                   evidence_turns: list | None = None) -> bool:
        """落一条 lesson(带软去重):先在 lesson 专属 HNSW 索引召回近邻,
        余弦相似 ≥ MERGE_SIM 的既有条目 → importance+1 合并不新增(返回 False);
        否则新增(返回 True)。embedding=text+condition(条件参与语义)。"""
        from scribe3.embed import embed
        from scribe3.lesson import MERGE_SIM
        import json as _json
        vec = embed([f"{text} {condition}".strip()])[0]
        near = self._query(
            "SELECT meta::id(id) AS id, chapter, kind, embedding, "
            "vector::distance::knn() AS dist "
            "FROM lesson WHERE embedding <|3,40|> $qv ORDER BY dist", {"qv": vec})
        for n in near:
            # P1门审查 P1-3:合并须同 kind 且 sim≥MERGE_SIM(0.97 收紧)——embedding 对
            # 否定不敏感,反向纠偏("反转别再压章尾")与旧课 0.92 档极易误合并,
            # "correction 最值钱"恰是被吞的那类;0.92-0.97 灰区直接新增,重复由
            # importance 机制无害共存。
            if n.get("kind") != kind:
                continue
            if n.get("dist") is not None and (1 - n["dist"]) >= MERGE_SIM:
                row = self._query(
                    "SELECT invalid_at FROM type::thing('lesson',$i)", {"i": n["id"]})
                if row and row[0].get("invalid_at"):
                    continue   # 已失效条目不合并(允许同课重立)
                # P1门审查 P1-1:同章重跑不 bump——ExpeL"跨章重复=偏好积累"语义,
                # 同章编辑期反复蒸馏不算重复偏好。
                if n.get("chapter") != chapter:
                    self._execute_write(
                        "UPDATE type::thing('lesson',$i) SET importance += 1",
                        {"i": n["id"]})
                return False
        self._execute_write(
            "CREATE lesson SET chapter=$c, kind=$k, text=$t, condition=$cond, "
            "evidence_turns=$ev, importance=2, uses=0, created_at=time::now(), embedding=$v",
            {"c": chapter, "k": kind, "t": text, "cond": condition or "",
             "ev": _json.dumps(evidence_turns or [], ensure_ascii=False), "v": vec})
        return True

    def list_lessons(self, chapter: int | None = None,
                     include_invalid: bool = False) -> list[dict]:
        where = []
        if chapter is not None:
            where.append("chapter = $c")
        if not include_invalid:
            where.append("invalid_at IS NONE")
        w = ("WHERE " + " AND ".join(where) + " ") if where else ""
        rows = self._query(
            f"SELECT meta::id(id) AS id, chapter, kind, text, condition, importance, uses, "
            f"evidence_turns, invalid_at, (IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at "
            f"FROM lesson {w}ORDER BY created_at ASC",
            {"c": chapter})
        import json as _json
        for r in rows:   # P1门审查 P2-8:证据指针读侧还原(此前只写不读,溯源链断)
            try:
                r["evidence_turns"] = _json.loads(r.get("evidence_turns") or "[]")
            except Exception:
                logging.getLogger("scribe3").error("lesson evidence_turns JSON 损坏: %r", r.get("evidence_turns"), exc_info=True)   # U-011
                r["evidence_turns"] = []
        return rows

    def bump_lesson_importance(self, lesson_id: str, delta: int = 1) -> None:
        self._execute_write(
            "UPDATE type::thing('lesson',$i) SET importance += $d",
            {"i": lesson_id, "d": delta})

    def invalidate_lesson(self, lesson_id: str) -> None:
        """失效标记不物理删(Zep 先例):craft_rule 审批溯源链保留。"""
        self._execute_write(
            "UPDATE type::thing('lesson',$i) SET invalid_at = time::now()",
            {"i": lesson_id})

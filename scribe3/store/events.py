"""SurrealStore mixin: events."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class EventsMixin:

    def add_event(self, ev: Event, ingest_seq: int | None = None) -> Event:
        """落事件 + 图边(involves/causes/causal)+ 有 effects 时自动 see_event。
        ingest_seq:由 ingest 抽取路径传入(批D P1-5),供 purge_ingest 幂等清理;
        手动种 / MCP s3_add_event 不传 → ingest_seq=NONE,不受 purge 影响(向后兼容)。

        生产路径不变量:带 effects 的事件落库后,在场参与者自动获得 knows(acquired_via=saw);
        调用方禁止再手调 see_event。"""
        _, local = _split(ev.id)
        ev_rid = RecordID("event", local)
        loc_local = _split(ev.location)[1] if ev.location else None
        with self.transaction():
            self._execute_write(
                "CREATE type::record('event', $local) SET event_type=$t, "
                "story_chapter=$vf, narrative_position=$np, "
                "motivated_by_goal=$g, causal_root_reason=$crr, location=$loc, preconditions=$pre"
                + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
                {"local": local, "t": ev.type, "vf": ev.story_time, "g": ev.motivated_by_goal,
                 "crr": ev.causal_root_reason,
                 "np": ev.narrative_position,  # 完整期:可空叙事位;null 回退 story_chapter(向后兼容)
                 "loc": RecordID("place", loc_local) if loc_local else None,
                 "pre": ev.preconditions,
                 **({"iseq": ingest_seq} if ingest_seq is not None else {})})
            # participants → involves 图边
            for slot, ent_oid in ev.participants.items():
                if not ent_oid:
                    continue
                ctbl, clocal = _split(ent_oid)
                if ctbl != "character":
                    continue
                self._execute_write(
                    "RELATE $e->involves->$c SET role=$role",
                    {"e": ev_rid, "c": RecordID("character", clocal), "role": slot})
            # effects → causes 图边(供 see_event 给在场者发知识边)
            for fid in ev.effects:
                _, flocal = _split(fid)
                self._execute_write(
                    "RELATE $e->causes->$p",
                    {"e": ev_rid, "p": RecordID("proposition", flocal)})
            # causal_in → causal 图边
            for src_oid, ctype in ev.causal_in:
                _, slocal = _split(src_oid)
                self._execute_write(
                    "RELATE $e->causal->$src SET ctype=$ct",
                    {"e": ev_rid, "src": RecordID("event", slocal), "ct": ctype})
            # 看见即知道:有 effects 时给全部在场参与者发 knows(与 memory World 行为对齐)
            if ev.effects:
                from scribe3.knowledge import see_event
                see_event(self, ev, ingest_seq=ingest_seq)
        self._invalidate_chapter_quality_cache(ev.story_time)
        return ev

    def append_ai_run_trace_event(self, run_id: str, event: dict) -> None:
        trace = self.get_ai_run_trace(run_id) or {}
        tool_calls = list(trace.get("tool_calls") or [])
        tool_outputs = list(trace.get("tool_outputs") or [])
        approvals = list(trace.get("approvals") or [])
        raw_events = list(trace.get("raw_events") or [])
        status = trace.get("status") or "created"
        usage = trace.get("usage")
        error = trace.get("error")

        def _find_call(call_id: str | None = None) -> dict | None:
            if call_id:
                for call in reversed(tool_calls):
                    if call.get("call_id") == call_id:
                        return call
            completed = {out.get("call_id") for out in tool_outputs if out.get("call_id")}
            for call in reversed(tool_calls):
                if call.get("call_id") not in completed:
                    return call
            return tool_calls[-1] if tool_calls else None

        def _find_approval(approval_id: str | None = None,
                           call_id: str | None = None,
                           approval_status: str | None = None) -> dict | None:
            for approval in reversed(approvals):
                if approval_id and approval.get("approval_id") != approval_id:
                    continue
                if call_id and approval.get("call_id") != call_id:
                    continue
                if approval_status and approval.get("status") != approval_status:
                    continue
                return approval
            return None

        kind = event.get("kind") or event.get("type") or ""
        source_type = event.get("source_type") or event.get("type") or kind
        if kind in {"tool.started", "tool.start"}:
            parsed_args = _json_obj(event.get("arguments"))
            tool_calls.append({
                "call_id": event.get("call_id"),
                "name": event.get("name") or event.get("tool_name") or "",
                "arguments": event.get("arguments", ""),
                "parsed_arguments": parsed_args,
                "approval_id": event.get("approval_id"),
                "source_type": source_type,
            })
        elif kind in {"tool.output", "tool.complete"}:
            call_id = event.get("call_id")
            call = _find_call(call_id)
            parsed_output = _json_obj(event.get("output"))
            tool = (
                event.get("name") or event.get("tool_name")
                or (parsed_output or {}).get("tool")
                or (call or {}).get("name")
                or ""
            )
            approval_id = event.get("approval_id") or (call or {}).get("approval_id")
            approval = (
                _find_approval(approval_id=approval_id, approval_status="resolved")
                or _find_approval(approval_id=approval_id)
                or _find_approval(call_id=call_id, approval_status="resolved")
                or _find_approval(call_id=call_id)
            )
            decision = event.get("decision") or (approval or {}).get("decision")
            if approval and not approval_id:
                approval_id = approval.get("approval_id")
            result_status = (parsed_output or {}).get("status") or event.get("status")
            parsed_args = (call or {}).get("parsed_arguments") or _json_obj((call or {}).get("arguments"))
            write_effect = (
                _write_effect_from_tool(tool, parsed_args)
                or (call or {}).get("write_effect")
                or (approval or {}).get("write_effect")
            )
            if not result_status and tool.startswith("s3_"):
                if decision in {"approve", "approved", "once", "session", "always", True}:
                    result_status = "written"
                elif decision in {"deny", "denied", "reject", "rejected", False}:
                    result_status = "declined"
            if call is not None:
                if approval_id:
                    call["approval_id"] = approval_id
                if result_status:
                    call["result_status"] = result_status
                if write_effect:
                    call["write_effect"] = write_effect
            tool_outputs.append({
                "call_id": call_id,
                "tool": tool,
                "output": event.get("output", ""),
                "parsed_output": parsed_output,
                "approval_id": approval_id,
                "decision": decision,
                "result_status": result_status,
                "write_effect": write_effect,
                "source_type": source_type,
            })
        elif kind in {"approval.requested", "approval.request"}:
            call_id = event.get("call_id") or event.get("tool_call_id")
            call = _find_call(call_id)
            if call and not call_id:
                call_id = call.get("call_id")
            tool = event.get("name") or event.get("tool_name") or (call or {}).get("name") or ""
            approval_id = event.get("approval_id")
            write_effect = _write_effect_from_approval_message(event.get("message", ""))
            if call and approval_id:
                call["approval_id"] = approval_id
            if call and write_effect:
                call["write_effect"] = write_effect
            approvals.append({
                "run_id": event.get("run_id") or run_id,
                "approval_id": approval_id,
                "call_id": call_id,
                "tool": tool,
                "message": event.get("message", ""),
                "write_effect": write_effect,
                "status": "requested",
                "source": event.get("source") or "runtime",
                "source_type": source_type,
            })
        elif kind == "approval.resolved":
            approval_id = event.get("approval_id")
            requested = _find_approval(approval_id=approval_id, approval_status="requested")
            call_id = event.get("call_id") or event.get("tool_call_id") or (requested or {}).get("call_id")
            call = _find_call(call_id)
            if call and not call_id:
                call_id = call.get("call_id")
            tool = event.get("name") or event.get("tool_name") or (requested or {}).get("tool") or (call or {}).get("name") or ""
            if call and approval_id:
                call["approval_id"] = approval_id
            write_effect = (requested or {}).get("write_effect") or (call or {}).get("write_effect")
            approvals.append({
                "run_id": event.get("run_id") or run_id,
                "approval_id": approval_id,
                "call_id": call_id,
                "tool": tool,
                "decision": event.get("decision"),
                "write_effect": write_effect,
                "status": "resolved",
                "source": event.get("source") or "runtime",
                "source_type": source_type,
            })
        elif kind == "run.completed":
            status = "completed"
            usage = event.get("usage")
        elif kind == "run.failed":
            status = "failed"
            error = event.get("error") or "run failed"
        else:
            raw_events.append(event)

        self.upsert_ai_run_trace(
            run_id,
            status=status,
            tool_calls=tool_calls,
            tool_outputs=tool_outputs,
            approvals=approvals,
            raw_events=raw_events,
            usage=usage,
            error=error,
        )

    def update_event_narrative(self, event_oid: str, narrative_position: int | None) -> None:
        """更新已有事件的叙事位(narrative_position)。
        narrative_position=None → 清除叙事位,回退到 story_chapter(向后兼容线性叙事)。
        event_oid 须为 'ev:xxx' 格式。
        """
        _, local = _split(event_oid)
        self._execute_write(
            "UPDATE type::record('event',$local) SET narrative_position=$np",
            {"local": local, "np": narrative_position})

    def set_event_causal_root(self, event_oid: str, reason: str) -> None:
        """将既有事件标为同章独立场景根；已有因果入边的事件不可同时声明为根。"""
        _, local = _split(event_oid)
        event_rows = self._query(
            "SELECT story_chapter FROM type::record('event',$local)", {"local": local})
        linked = self._query(
            "SELECT count() AS n FROM causal WHERE in = type::record('event',$local)",
            {"local": local})
        if linked and (linked[0].get("n") or 0) > 0:
            raise ValueError("已有因果入边的事件不能登记为独立场景根")
        self._execute_write(
            "UPDATE type::record('event',$local) SET causal_root_reason=$reason",
            {"local": local, "reason": reason})
        self._invalidate_chapter_quality_cache(
            event_rows[0].get("story_chapter") if event_rows else None)

    def add_event_causal_link(self, event_oid: str, source_event_oid: str, ctype: str) -> None:
        """为既有同章事件补一条因果边；成功后清除目标事件的根理由，避免双重语义。"""
        _, local = _split(event_oid)
        _, source_local = _split(source_event_oid)
        if local == source_local:
            raise ValueError("事件不能以自身作为因果前驱")
        rows = self._query(
            "SELECT meta::id(id) AS local, story_chapter FROM event "
            "WHERE id IN [type::record('event',$target), type::record('event',$source)]",
            {"target": local, "source": source_local})
        chapters = {r.get("local"): r.get("story_chapter") for r in rows}
        if set(chapters) != {local, source_local}:
            raise ValueError("目标事件或前驱事件不存在")
        if chapters[local] != chapters[source_local]:
            raise ValueError("因果边只能连接同一章的事件")
        exists = self._query(
            "SELECT id FROM causal WHERE in=type::record('event',$target) "
            "AND out=type::record('event',$source) LIMIT 1",
            {"target": local, "source": source_local})
        if not exists:
            self._execute_write(
                "RELATE $target->causal->$source SET ctype=$ctype",
                {"target": RecordID("event", local), "source": RecordID("event", source_local),
                 "ctype": ctype})
        self._execute_write(
            "UPDATE type::record('event',$target) SET causal_root_reason=NONE",
            {"target": local})
        self._invalidate_chapter_quality_cache(chapters[local])

    def causal_debt_total(self) -> int:
        """因果欠账存量:各章 qc_causal 正值求和(-1 哨兵=无事件数据,不计入)。
        蓝图 §3-②:brief 只催收 top-5,超出部分落面板由此字段承载。"""
        rows = self._query(
            "SELECT qc_causal FROM chapter:.. WHERE archived = NONE OR archived != true")
        return sum((r.get("qc_causal") or 0) for r in rows
                   if (r.get("qc_causal") or 0) > 0)

    def events_at(self, chapter: int) -> list[Event]:
        """读取某章全部事件(沿图边取回 participants+effects,补 P03 限知裂口)。
        P3-e1 Fix 3: 读回 location / preconditions(之前写入后不回传,write-into-the-void)。"""
        rows = self._query(
            "SELECT meta::id(id) AS local, event_type, story_chapter, narrative_position, "
            "  motivated_by_goal, causal_root_reason, location, preconditions, "
            "  (SELECT meta::id(out) AS clocal, role FROM ->involves) AS parts, "
            "  (SELECT meta::id(out) AS plocal FROM ->causes) AS effs, "
            "  (SELECT meta::id(out) AS slocal, ctype FROM ->causal) AS causals "
            "FROM event WHERE story_chapter = $ch", {"ch": chapter})
        out = []
        for r in rows:
            participants = {p["role"]: f"role:{p['clocal']}" for p in (r.get("parts") or [])}
            effects = [f"fact:{e['plocal']}" for e in (r.get("effs") or [])]
            causal_in = [(f"ev:{c['slocal']}", c["ctype"]) for c in (r.get("causals") or [])]
            etype = r.get("event_type") or ""
            story_chapter = r.get("story_chapter") or 0
            # location 存储为 RecordID(place,x) → 回传为 "place:x" 字符串
            raw_loc = r.get("location")
            if raw_loc is not None:
                loc_str = str(raw_loc) if not isinstance(raw_loc, str) else raw_loc
            else:
                loc_str = None
            out.append(Event(f"ev:{r['local']}", etype,
                             participants=participants,
                             location=loc_str,
                             story_time=story_chapter,
                             preconditions=r.get("preconditions") or [],
                             effects=effects,
                             causal_in=causal_in,
                             causal_root_reason=r.get("causal_root_reason"),
                             motivated_by_goal=r.get("motivated_by_goal"),
                             narrative_position=r.get("narrative_position")))
        return out

    def _all_events_bulk(self) -> list["Event"]:
        """批量查全表所有事件(含图边 involves/causes/causal),一次往返。
        供 timeline() 事件泳道使用——替代逐章 events_at 循环(N 章→N 次多子查询往返)。
        返回结构与 events_at 完全一致(Event dataclass),调用方按章过滤/分组。"""
        rows = self._query(
            "SELECT meta::id(id) AS local, event_type, story_chapter, narrative_position, "
            "  motivated_by_goal, causal_root_reason, location, preconditions, "
            "  (SELECT meta::id(out) AS clocal, role FROM ->involves) AS parts, "
            "  (SELECT meta::id(out) AS plocal FROM ->causes) AS effs, "
            "  (SELECT meta::id(out) AS slocal, ctype FROM ->causal) AS causals "
            "FROM event")
        out = []
        for r in rows:
            participants = {p["role"]: f"role:{p['clocal']}" for p in (r.get("parts") or [])}
            effects = [f"fact:{e['plocal']}" for e in (r.get("effs") or [])]
            causal_in = [(f"ev:{c['slocal']}", c["ctype"]) for c in (r.get("causals") or [])]
            etype = r.get("event_type") or ""
            story_chapter = r.get("story_chapter") or 0
            raw_loc = r.get("location")
            loc_str = (str(raw_loc) if not isinstance(raw_loc, str) else raw_loc) if raw_loc is not None else None
            out.append(Event(f"ev:{r['local']}", etype,
                             participants=participants,
                             location=loc_str,
                             story_time=story_chapter,
                             preconditions=r.get("preconditions") or [],
                             effects=effects,
                             causal_in=causal_in,
                             causal_root_reason=r.get("causal_root_reason"),
                             motivated_by_goal=r.get("motivated_by_goal"),
                             narrative_position=r.get("narrative_position")))
        return out

    def timeline(self, ch_from: int = 1, ch_to: int | None = None,
                 axis: str = "story", limit: int | None = None) -> list[dict]:
        """聚合 [ch_from, ch_to] 区间内所有"章号锚状态",归并成时间线条目。
        进阶:四类泳道—— events / promise(伏笔) / arc(弧光质变) / relation(关系全史)。
        无写、无限知门控(作者全知工艺视图)。复用既有读方法,不新增 SQL 真源。
        向后兼容:items 中 kind=event 的条目结构与 MVP 一致。
        完整期新增:refs.causal_in 从 [ev_id_str] 升级为 [{id, chapter}],
        供前端 SVG 因果弧线计算两端 x 坐标。

        完整期双轴(spec §3.1 / §3.5):
          axis='story'(默认,向后兼容)—— 事件按 story_chapter(故事编年)横铺。
          axis='narrative'           —— 事件按 narrative_position ?? story_chapter(叙事顺序)横铺;
                                         倒叙/闪回事件(story 早、narrative 晚)落到叙事位。
          排序键用 `narrative_position ?? story_chapter`(Python 侧回退,SurrealDB ORDER BY 不支持 ?? — F-01)。
          每个事件条目恒带 story_chapter / narrative_position,前端可在两者不同时标"闪回"。
          axis 只影响事件泳道的 chapter 投影;伏笔/弧光/关系仅有故事章,两轴一致。"""
        narrative = (axis == "narrative")
        mc = self.max_chapter()
        hi = ch_to if ch_to is not None else mc
        if hi == 0:
            return []
        items: list[dict] = []
        # D-3:伏笔泳道 overdue 走 _overdue_flag 单源(与 /promises、/quality、/promises/ledger 一致);
        # 此前读 p.get("overdue")(list_promises 从不填该键)→ 恒 False,破不变量⑤。
        _intent = self.get_intent()
        _slack = (_intent.get("overdue_threshold")
                  if _intent.get("overdue_threshold") is not None else OVERDUE_SLACK)

        # 预建 ev_id→chapter 映射,供 causal_in 章号补全(一次全表查,不逐条单查)
        # 同时用 _all_events_bulk() 一次性拉取全表事件(含图边),消除逐章 events_at N+1。
        ev_ch_map = self._ev_chapter_map()

        # ── 1. 事件泳道 ──
        # 一次全表查(含 involves/causes/causal 图边),Python 侧按投影坐标过滤到 [ch_from, hi]。
        # 不能只查 [ch_from, hi] 的 story 章:叙事轴下 story_chapter 在区间外
        # 但 narrative_position 落在区间内的闪回事件会被漏掉——全表查再按轴坐标过滤是正确做法。
        for ev in self._all_events_bulk():
            # 投影坐标:叙事轴用 narrative_position ?? story_time;故事轴用 story_time
            np = ev.narrative_position
            plot_ch = (np if np is not None else ev.story_time) if narrative else ev.story_time
            if not (ch_from <= plot_ch <= hi):
                continue
            subj = [v for k, v in ev.participants.items() if k == "SUBJ"]
            obj_ = [v for k, v in ev.participants.items() if k == "OBJ"]
            wit  = [v for k, v in ev.participants.items() if k == "WITNESS"]
            # causal_in 带章号:前端 SVG 弧线需知道两端 x=章号(用 story_chapter,稳定真源)
            causal_in_rich = [
                {"id": c[0], "chapter": ev_ch_map.get(c[0])}
                for c in ev.causal_in
            ]
            items.append({
                "chapter": plot_ch,                    # 当前轴的横铺坐标
                "kind": "event",
                "id": ev.id,
                "label": ev.type,
                "goal": ev.motivated_by_goal,
                "lane_keys": subj + obj_,
                "event_type": ev.type,
                "story_chapter": ev.story_time,        # 故事编年(恒在,前端"故事@N")
                "narrative_position": np,              # 叙事位(可空,前端"叙事@M")
                "refs": {
                    "subj": subj,
                    "obj": obj_,
                    "witness": wit,
                    "effects": ev.effects,
                    "location": ev.location,
                    "causal_in": causal_in_rich,
                },
            })

        # ── 2. 伏笔泳道(setup 埋点 + payoff 收点) ──
        for p in self.list_promises():
            s = p.get("setup_chapter")
            if s is None:
                continue
            if ch_from <= s <= hi:
                items.append({
                    "chapter": s,
                    "kind": "promise_setup",
                    "id": p["id"],
                    "label": p["text"],
                    "lane_keys": ["__promise__"],
                    "refs": {
                        "status": p.get("status"),
                        "promise_kind": p.get("kind"),
                        "payoff_chapter": p.get("payoff_chapter"),
                        "overdue": _overdue_flag(p, mc, _slack),
                    },
                })
            pf = p.get("payoff_chapter")
            if pf and ch_from <= pf <= hi:
                items.append({
                    "chapter": pf,
                    "kind": "promise_payoff",
                    "id": p["id"],
                    "label": p["text"],
                    "lane_keys": ["__promise__"],
                    "refs": {
                        "setup_chapter": s,
                        "promise_kind": p.get("kind"),
                        "status": p.get("status"),
                    },
                })

        # ── 3. 弧光质变泳道(char_state 每条一个◆点) ──
        # 一次全表查所有 char_state,Python 按 character_id 分组——消除逐角色 list_char_states N+1。
        for cs in self._all_char_states_bulk():
            ch = cs.get("chapter")
            if ch is None:
                continue
            if not (ch_from <= ch <= hi):
                continue
            cid = cs.get("character_id")
            if not cid:
                continue
            items.append({
                "chapter": ch,
                "kind": "arc",
                "id": cs["id"],
                "label": cs.get("summary", ""),
                "lane_keys": [cid],
                "refs": {
                    "character": cid,
                    "change_type": cs.get("change_type"),
                    "arc_phase": cs.get("arc_phase"),
                    "affects_voice": cs.get("affects_voice"),
                },
            })

        # ── 4. 关系泳道(全量读,含已失效历史;不用 relations_at 带时间门) ──
        for r in self._all_relations():
            sc = r.get("since_chapter")
            uc = r.get("until_chapter")
            src_key = f"role:{r['src']}"
            dst_key = f"role:{r['dst']}"
            if sc is not None and ch_from <= sc <= hi:
                items.append({
                    "chapter": sc,
                    "kind": "relation_start",
                    "id": f"{r['src']}->{r['dst']}@{sc}",
                    "label": r.get("relation", ""),
                    "lane_keys": [src_key, dst_key],
                    "refs": {
                        "src": src_key,
                        "dst": dst_key,
                        "relation": r.get("relation"),
                        "until_chapter": uc,
                        "note": r.get("note"),
                    },
                })
            if uc is not None and ch_from <= uc <= hi:
                items.append({
                    "chapter": uc,
                    "kind": "relation_end",
                    "id": f"{r['src']}->{r['dst']}@end{uc}",
                    "label": r.get("relation", ""),
                    "lane_keys": [src_key, dst_key],
                    "refs": {
                        "src": src_key,
                        "dst": dst_key,
                        "relation": r.get("relation"),
                        "since_chapter": sc,
                        "note": r.get("note"),
                    },
                })

        items.sort(key=lambda x: (x["chapter"], x["kind"]))
        # 千万字基座(Phase0-BE1):total items 硬上限,防一次返上万条。
        # limit 为 None → 不截断(向后兼容,小书全返);给定则取按章序最早的 limit 条。
        if limit is not None and len(items) > limit:
            items = items[:limit]
        return items

    def validate_event_colocation(self, chapter: int) -> list[dict]:
        """遗留处置批次三:同章同主体多地事件 hint(纯结构查询,report-only)。
        story_time/story_chapter 是章粒度——双地可能有合法移动衔接,故 severity=low
        且 note 明示人工确认;永不进 blocking。"""
        by_subj: dict[str, set] = {}
        for ev in self.events_at(chapter):
            subj = (ev.participants or {}).get("SUBJ")
            if subj and ev.location:
                by_subj.setdefault(str(subj), set()).add(str(ev.location))
        hints: list[dict] = []
        for subj, locs in sorted(by_subj.items()):
            if len(locs) >= 2:
                ls = sorted(locs)
                hints.append({
                    "type": "event_colocation", "severity": "low",
                    "subject": subj, "locations": ls,
                    "note": (f"同章主体 {subj} 的事件分布在 {len(ls)} 个地点"
                             f"({'、'.join(ls)});story_time 为章粒度,可能有移动"
                             f"衔接,请人工确认时间线")})
        return hints

    def claim_pending_events(self, work: str | None = None, thread_id: str | None = None,
                             event_type: str | None = None, limit: int = 50) -> list[dict]:
        """原子认领 pending/failed(可重试)事件:单条 CAS UPDATE 置 processing + attempts+1,
        仅返回本次【实际翻转】的行(RETURN 投影取更新后值)。

        为什么不 SELECT-then-per-row-UPDATE:那是非原子的——两并发 consolidate 会双认领
        同一批(实测 30 轮 13 次双认领)。改单语句 UPDATE...WHERE status IN[...] 后,每条记录
        只被翻一次,双认领消解为"另一方拿到空集"。UPDATE 无 LIMIT 子句(SurrealQL 语义),
        故 limit 参数仅保留签名兼容、不再截断——掉线残留一次 drain 干净更符合意图。"""
        where = ["status IN ['pending', 'failed']"]
        vars: dict = {}
        if work:
            where.append("work=$w")
            vars["w"] = work
        if thread_id:
            where.append("thread_id=$tid")
            vars["tid"] = thread_id
        if event_type:
            where.append("event_type=$et")
            vars["et"] = event_type
        rows = self._query(
            "UPDATE memory_event SET status='processing', attempts += 1 "
            f"WHERE {' AND '.join(where)} "
            "RETURN event_id, work, thread_id, event_type, payload, status, attempts", vars)
        return rows or []

    def begin_processing_event(self, event_id: str) -> None:
        """单事件同步 drain:置 processing 并 attempts+1(capture_event 处理前调用)。"""
        self._execute_write(
            "UPDATE memory_event SET status='processing', attempts += 1 "
            "WHERE event_id=$e RETURN NONE", {"e": event_id})

    def mark_event_complete(self, event_id: str) -> None:
        self._execute_write(
            "UPDATE memory_event SET status='complete', error=NONE, "
            "processed_at=time::now() WHERE event_id=$e RETURN NONE", {"e": event_id})

    def mark_event_failed(self, event_id: str, error: str) -> None:
        """标记失败并留错误文案(attempts 已在 begin_processing/claim 时累加)。"""
        self._execute_write(
            "UPDATE memory_event SET status='failed', error=$err, "
            "processed_at=time::now() WHERE event_id=$e RETURN NONE",
            {"e": event_id, "err": (error or "")[:500]})

    def reclaim_stale_processing_events(
            self, work: str | None = None, thread_id: str | None = None,
            event_type: str | None = None, older_than_seconds: float = 0.0) -> list[dict]:
        """孤儿回收:把陈旧 'processing' 事件复位为 'failed'(可被 claim_pending_events 重认领)。

        病灶:_drain_one 先 begin_processing_event(status='processing')再跑 jieba+embed+CREATE
        才 mark_event_complete(非瞬时窗口)。进程在此窗口被 SIGKILL/OOM/部署重启 → 事件永久卡
        'processing';claim_pending_events 只认领 pending/failed(结构性排除 processing)、无 reaper,
        该轮经验记忆静默永久丢失,且 count_failed_memory_events 只数 'failed' → 告警不可见。
        本方法把处于 processing 且 processed_at 为空(从未完成)的孤儿复位 failed:既可被
        consolidate 的 claim 重 drain 找回,复位期间 count_failed 也让告警可见。

        判据(processed_at IS NONE + 可选时间阈值):
          · processed_at 为空 → 只碰"从未完成/从未标记"的在处理事件,绝不复原已 complete/failed。
          · older_than_seconds>0 → 仅复位 created_at 早于该阈值者(跨进程/未来后台 worker 的纵深防御)。
        同步单进程模型下 consolidate 起手调用(older_than_seconds=0):reaper 先于本 consolidate
        自身的 drain(见 consolidate_thread 步骤1),此刻任何 processing 皆为上一进程崩溃遗留、
        非本次在途,故 0 阈值复位安全;capture_event 的 drain 是同步的、返回前已 complete/failed,
        不会与 consolidate 并发同一线程(见 memory_capture 模块顶注)。attempts 不在此累加
        (复位非一次新尝试;真正重试由 claim +1)。"""
        where = ["status = 'processing'", "processed_at IS NONE"]
        vars: dict = {"err": "reclaimed_stale_processing"}
        if older_than_seconds and older_than_seconds > 0:
            from datetime import datetime as _dt, timedelta as _td, timezone as _tz
            cutoff = _dt.now(_tz.utc) - _td(seconds=float(older_than_seconds))
            where.append("created_at < type::datetime($cutoff)")
            vars["cutoff"] = cutoff.isoformat()
        if work:
            where.append("work=$w")
            vars["w"] = work
        if thread_id:
            where.append("thread_id=$tid")
            vars["tid"] = thread_id
        if event_type:
            where.append("event_type=$et")
            vars["et"] = event_type
        rows = self._query(
            "UPDATE memory_event SET status='failed', error=$err "
            f"WHERE {' AND '.join(where)} "
            "RETURN event_id, work, thread_id, event_type, attempts", vars)
        return rows or []

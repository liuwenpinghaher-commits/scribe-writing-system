"""SurrealStore mixin: facts_knowledge."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403


def collapse_facts_single_truth(facts: list) -> list:
    """D4 质量：同一 (entity_id, attribute) 在当章只保留一条有效真值。

    选取 valid_from 最大者；并列时保留列表中后者（通常为较新写入）。
    纯函数，便于无 DB 单测；facts_at 读路径安全网。
    多值同属性的「并存设计」若仍需要，写入时须 supersede_open=False 且
    读路径调用方自行跳过折叠——产品默认写作正典为单真值。
    """
    best: dict[tuple[str, str], object] = {}
    for f in facts or []:
        eid = getattr(f, "entity_id", None) or (f.get("entity_id") if isinstance(f, dict) else "") or ""
        attr = getattr(f, "attribute", None) or (f.get("attribute") if isinstance(f, dict) else "") or ""
        if not eid or not attr:
            # 无键的行无法折叠，原样挂到合成键上避免丢失
            key = (str(id(f)), "")
        else:
            key = (str(eid), str(attr))
        prev = best.get(key)
        if prev is None:
            best[key] = f
            continue
        prev_vf = getattr(prev, "valid_from", None)
        if prev_vf is None and isinstance(prev, dict):
            prev_vf = prev.get("valid_from")
        cur_vf = getattr(f, "valid_from", None)
        if cur_vf is None and isinstance(f, dict):
            cur_vf = f.get("valid_from")
        if (cur_vf or 0) >= (prev_vf or 0):
            best[key] = f
    return list(best.values())


class FactsKnowledgeMixin:

    def add_fact(self, f: Fact, ingest_seq: int | None = None, *,
                 supersede_open: bool = True) -> Fact:
        """写入命题。默认 supersede_open=True：关闭同 entity+attribute 的其它开区间先驱，
        保证「改设定后全世界只认新真相」(记忆质量 D4)。

        supersede_open=False：保留多值并存语义（显式需要时才关）。
        """
        _, local = _split(f.id)
        vf = int(f.valid_from) if f.valid_from is not None else 0
        # D4：先关闭同键开区间先驱（不含本 id），再 UPSERT 本行。
        # valid_to 半开区间 [from,to)：先驱 valid_to=本行 valid_from → 自本章起只认新值。
        if supersede_open and f.entity_id and f.attribute:
            # 与 supersede_fact 同口径：关闭同 entity+attribute 的开区间行。
            # 先关全部开区间，再 UPSERT 本行（本行会以新 valid_from / 开区间写回）。
            try:
                self._execute_write(
                    "UPDATE proposition SET valid_to=$vf "
                    "WHERE entity_id=$e AND attribute=$a AND valid_to=NONE "
                    "AND valid_from <= $vf",
                    {"e": f.entity_id, "a": f.attribute, "vf": vf},
                )
            except Exception as _e:
                logging.getLogger("scribe3.store").warning(
                    "add_fact supersede_open 关闭先驱失败(仍写入新命题): %s", _e)
        self._execute_write(
            "UPSERT type::record('proposition', $local) SET entity_id=$entity, "
            "attribute=$attr, value=$value, valid_from=$vf, valid_to=$vt, secret=$secret, "
            "leak_markers=$lm"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"local": local, "entity": f.entity_id, "attr": f.attribute, "value": f.value,
             "vf": f.valid_from, "vt": f.valid_to, "secret": f.secret, "lm": f.leak_markers,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        # 写入后建语义索引(与 s3_add_fact 对齐;embed 失败不阻断主写)
        try:
            self.semantic_index(f.id, f.value)
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "add_fact: embedding 失败,命题 %s 将不可语义召回: %s", f.id, _e)
        # Task 16-B:正典写入发表级失效(清 global/retrieval 缓存 + bump authority_revision)。
        # supersede_fact 内部也经此路径,故正典变更两条路都覆盖。best-effort,绝不阻断写。
        _emit_cache_invalidation("proposition", self.db_name)
        return f

    def add_knowledge(self, k: KnowledgeEdge, ingest_seq: int | None = None) -> KnowledgeEdge:
        if k.knower_id == "reader":   # reader 帧:单独表,不走 character->knows 边
            # 写 ingest_seq 供 purge_ingest 幂等清理;手动种的边 ingest_seq=NONE 不受 purge 影响
            self._execute_write(
                "CREATE reader_knows SET proposition=$p, since_chapter=$since"
                + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
                {"p": k.proposition_id, "since": k.since_chapter,
                 **({"iseq": ingest_seq} if ingest_seq is not None else {})})
            return k
        # P3-b: 验证 knower 端实体存在,防悬挂边(reader 已在上方提前返回)
        if self.entity(k.knower_id) is None:
            raise ValueError(
                f"add_knowledge: knower '{k.knower_id}' 不存在,拒绝写入悬挂边。"
                f"请先建立角色实体,或使用 'reader' 作为虚拟 knower。"
            )
        ktbl, klocal = _split(k.knower_id)
        ptbl, plocal = _split(k.proposition_id)
        # RELATE 箭头位不接受内联函数,用 RecordID 绑参
        self._execute_write(
            "RELATE $k->knows->$p SET since_chapter=$since, until_chapter=$until, "
            "polarity=$pol, acquired_via=$via, certainty=$cert"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"k": RecordID(ktbl, klocal), "p": RecordID(ptbl, plocal),
             "since": k.since_chapter, "until": k.until_chapter, "pol": k.polarity,
             "via": k.acquired_via, "cert": k.certainty,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        return k

    def supersede_fact(self, entity_id: str, attribute: str, new_value: str,
                       since_chapter: int, secret: bool = False) -> str:
        """显式超越:关闭同一 entity+attribute 的所有开区间先驱,写入新命题。
        返回新命题的 oid。写入走 add_fact(supersede_open=True)，双保险。"""
        import uuid
        # 1. 关闭所有该 entity+attribute 的开区间先驱（含 valid_from==since 的并列旧行）
        self._execute_write(
            "UPDATE proposition SET valid_to=$since "
            "WHERE entity_id=$e AND attribute=$a AND valid_to=NONE AND valid_from<=$since",
            {"e": entity_id, "a": attribute, "since": since_chapter})
        # 2. 写入新命题（add_fact 再扫一遍开区间，幂等）
        new_oid = f"fact:{uuid.uuid4().hex[:8]}"
        new_fact = Fact(new_oid, entity_id, attribute, new_value, valid_from=since_chapter, secret=secret)
        self.add_fact(new_fact, supersede_open=True)
        return new_oid

    def forget_knowledge(self, knower_id: str, proposition_id: str, until_chapter: int) -> None:
        """设置知识边的 until_chapter(令知识在该章起失效)。
        P2-a Fix2: 仅更新开区间边(until_chapter IS NONE),与 supersede_fact 对齐——
        已闭合的边(until_chapter 已设置)不被覆写,防止重复 forget 破坏历史记录。"""
        ktbl, klocal = _split(knower_id)
        ptbl, plocal = _split(proposition_id)
        self._execute_write(
            "UPDATE knows SET until_chapter=$uc "
            "WHERE in=$k AND out=$p AND until_chapter IS NONE",
            {"uc": until_chapter,
             "k": RecordID(ktbl, klocal),
             "p": RecordID(ptbl, plocal)})

    def fact(self, oid: str) -> Fact | None:
        _, local = _split(oid)
        rows = self._query(
            "SELECT entity_id, attribute, value, valid_from, valid_to, secret, leak_markers "
            "FROM type::record('proposition',$local)", {"local": local})
        if not rows:
            return None
        r = rows[0]
        eid = r.get("entity_id") or ""
        return Fact(oid, eid, r["attribute"], r["value"], r["valid_from"],
                    r.get("valid_to"), r.get("secret", False), r.get("leak_markers", []))

    def list_open_propositions(self, chapter: int = 99999) -> list[dict]:
        """开区间命题列表(设定树投影用)。返回 [{id, entity_id, attribute, value, valid_from, valid_to, secret}]。
        D4：同 entity+attribute 只保留 valid_from 最新一条（与 facts_at 一致）。"""
        ch = int(chapter)
        rows = self._query(
            "SELECT meta::id(id) AS id, entity_id, attribute, value, "
            "valid_from, valid_to, secret FROM proposition "
            "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch) "
            "AND (archived = NONE OR archived != true) "
            "ORDER BY valid_from DESC",
            {"ch": ch}) or []
        return collapse_facts_single_truth(rows)

    def facts_at(self, chapter: int) -> list[Fact]:
        rows = self._query(
            "SELECT meta::id(id) AS local, entity_id, attribute, value, "
            "valid_from, valid_to, secret, leak_markers, injection_mode, priority FROM proposition "
            "WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch) "
            "AND (archived = NONE OR archived != true)", {"ch": chapter})
        facts = [Fact(f"fact:{r['local']}", r.get("entity_id") or "",
                      r["attribute"], r["value"],
                      r["valid_from"], r.get("valid_to"), r.get("secret", False),
                      r.get("leak_markers", []),
                      injection_mode=r.get("injection_mode"), priority=r.get("priority"))
                 for r in rows]
        # D4 读路径安全网：即使历史数据有多条开区间同键，当章只暴露一条真值
        return collapse_facts_single_truth(facts)

    def _secret_proposition_values(self) -> set[str]:
        """本 work 权威 secret 命题的真值集(供 ai_run_trace redactor 抹工具回抛的秘密明文)。
        含单字真值(I-1:中文单字名讳常见)——单字由 redactor 走有界屏蔽,不全文裸替换。
        U-011(作者要 fail-loud):删"失败退空集"——空集=秘密真值不抹→泄进 ai_run_trace
        (fail-open 泄密方向)。查询失败直接【抛】,不静默漏抹把泄密躲过去。
        性能:每次落库全表扫 proposition(Task 16-B 缓存,此处先正确后优化)。"""
        # value 是 SurrealDB 保留字,不能作首字段(会被当 SELECT VALUE 修饰符);挪后即可。
        rows = self._query(
            "SELECT entity_id, value FROM proposition WHERE secret = true")
        out: set[str] = set()
        for r in (rows or []):
            v = r.get("value")
            if v is not None and len(str(v).strip()) >= 1:
                out.add(str(v))
        return out

    def orphan_knowledge_edges(self) -> list[dict]:
        """扫描孤儿知识边:knows/reader_knows 中指向不存在命题的悬挂边。
        返回列表 [{type, knower, proposition_ref}];正常情况应为空列表。
        S4 (W3#8): 写作链路完整性校验——ingest purge 后不应留悬挂边。"""
        orphans: list[dict] = []
        # 1. knows 边:按 out 找不存在的命题
        knows_rows = self._query(
            "SELECT meta::id(in) AS knower_local, meta::tb(in) AS knower_tb, "
            "meta::id(out) AS prop_local FROM knows")
        for r in knows_rows:
            prop_local = r.get("prop_local")
            if prop_local is None:
                continue
            exists = self._query(
                "SELECT id FROM type::record('proposition',$p) LIMIT 1", {"p": prop_local})
            if not exists:
                orphans.append({
                    "type": "knows",
                    "knower": f"{r.get('knower_tb', 'character')}:{r.get('knower_local', '')}",
                    "proposition_ref": f"fact:{prop_local}",
                })
        # 2. reader_knows 边:proposition 字段存的是本体 oid 字符串(如 "fact:k3-0")
        rk_rows = self._query("SELECT proposition FROM reader_knows")
        for r in rk_rows:
            prop_ref = r.get("proposition")
            if prop_ref is None:
                continue
            # prop_ref 可能是 "fact:xxx" 字符串或 RecordID 对象
            prop_str = str(prop_ref)
            # 提取 proposition 表的 local id
            if ":" in prop_str:
                _, prop_local = prop_str.split(":", 1)
            else:
                prop_local = prop_str
            exists = self._query(
                "SELECT id FROM type::record('proposition',$p) LIMIT 1", {"p": prop_local})
            if not exists:
                orphans.append({
                    "type": "reader_knows",
                    "knower": "reader",
                    "proposition_ref": prop_str,
                })
        return orphans

    def load_knowledge(self) -> list[KnowledgeEdge]:
        """显式拉全部知识边(knows + reader_knows)。昂贵:2 条查询。调用方应缓存。"""
        rows = self._query(
            "SELECT meta::tb(in) AS itb, meta::id(in) AS iid, meta::tb(out) AS otb, "
            "meta::id(out) AS olocal, since_chapter, until_chapter, polarity, acquired_via, certainty FROM knows")
        edges = [KnowledgeEdge(_join(r["itb"], r["iid"]), _join(r["otb"], r["olocal"]),
                               r.get("polarity", True), r.get("certainty", 1.0), r.get("since_chapter", 0),
                               r.get("until_chapter"), r.get("acquired_via", "given")) for r in rows]
        rr = self._query("SELECT proposition, since_chapter FROM reader_knows")
        edges += [KnowledgeEdge("reader", r["proposition"], True, 1.0,
                                r.get("since_chapter", 0), None, "given") for r in rr]
        return edges

    @property
    def knowledge(self) -> list[KnowledgeEdge]:
        """向后兼容薄封装(委托 load_knowledge)。新代码用 load_knowledge + 显式缓存。"""
        return self.load_knowledge()

    def add_faction(self, name: str,
                    ideology: str | None = _UNSET,
                    status: str = _UNSET,
                    leader: str | None = _UNSET,
                    known_members: list | None = _UNSET,
                    public_face: str | None = _UNSET,
                    private_operation: str | None = _UNSET,
                    first_mention_chapter: int | None = _UNSET,
                    private_operation_secret: bool = _UNSET,
                    **fields) -> str:
        """Upsert 势力(注册表驱动 MERGE,取代旧 DELETE+CREATE 整行覆盖)。

        legacy 9 个具名参数(ideology/status/leader/known_members/public_face/
        private_operation/first_mention_chapter/private_operation_secret)保留原有位置
        签名不变——app.py `POST /factions` 与 mcp.py `s3_add_faction` 历史上总是显式
        传出全部 9 个值(位置或关键字),此签名保证它们不炸;`**fields` 接住
        codex_schema.FACTION_FIELDS 里其余 ~19 个新字段(origin/key_figures/structure/
        artifacts/goals/... 及各自的 `{key}_secret` 旗标)。

        legacy 参数用哨兵 `_UNSET` 区分"显式传入"与"根本没传":未传的字段一律不进
        MERGE 内容,从而保住库中旧值(部分更新语义,决定 4——store 层直接支持
        PATCH,不必再靠 app.py 手工 pick() 回填全部字段才敢调用)。

        `**fields` 中出现的键必须在 `codex_schema.all_storage_keys('faction')` 白名单
        内,否则抛 `ValueError`(未知字段拒收,不静默丢弃——防止调用方拼错字段名却
        查不出为何没生效)。

        实现注记:`faction.name` 上有 `uniq_faction_name` UNIQUE 索引(migration 038),
        而现有行(含生产库既有势力)的 record id 是历史 DELETE+CREATE 留下的随机 id,
        并非 name 派生——若直接 `UPSERT type::record('faction', $name) MERGE ...`,
        对已存在但 id≠name 的老行会因 UPSERT 走"目标 id 不存在→CREATE"分支,试图新建
        一条 name 相同但 id 不同的记录,直接撞 UNIQUE 索引报错(已用测试验证复现)。
        故先按 name 查真实 record id,存在则 MERGE 到该 id 上;不存在才 CREATE 新行——
        对老随机 id 行和新行都安全,且仍是真部分更新(MERGE),不改变记录 id 语义。
        """
        allowed = set(_codex_all_storage_keys("faction"))
        content: dict = {}
        for k, v in (("ideology", ideology), ("status", status), ("leader", leader),
                     ("known_members", known_members), ("public_face", public_face),
                     ("private_operation", private_operation),
                     ("first_mention_chapter", first_mention_chapter),
                     ("private_operation_secret", private_operation_secret)):
            if v is not _UNSET:
                content[k] = v
        for k, v in fields.items():
            if k not in allowed:
                raise ValueError(
                    f"未知势力字段: {k!r}(不在 codex_schema.all_storage_keys('faction') "
                    "白名单内;如需新增字段,先去 codex_schema.py 注册再补 migration)")
            content[k] = v
        content["name"] = name
        existing = self._query("SELECT id FROM faction WHERE name=$n LIMIT 1", {"n": name})
        if existing:
            self._execute_write("UPDATE $rid MERGE $content",
                                {"rid": existing[0]["id"], "content": content})
        else:
            self._execute_write("CREATE faction CONTENT $content", {"content": content})
        return name

    def get_faction(self, name: str) -> dict | None:
        """按名精确取单个势力(codex_schema 阶段1 新增;供 REST/命题桥/一致性校验用)。"""
        rows = self._query("SELECT * FROM faction WHERE name=$n", {"n": name})
        return rows[0] if rows else None

    def list_factions(self) -> list[dict]:
        return self._query("SELECT * FROM faction")

    def delete_faction(self, name: str) -> None:
        self._execute_write("DELETE faction WHERE name=$n", {"n": name})

    def supersede_memory(self, memory_id: str, *, text: str | None = None,
                         reason: str = "author_correction",
                         confidence=_UNSET, importance=_UNSET,
                         valid_from=_UNSET, valid_to=_UNSET,
                         known_from=_UNSET, known_to=_UNSET,
                         provenance: list[dict] | None = None,
                         linked_ids: list[str] | None = None) -> dict:
        """更正一条经验记忆:新建取代记录 + corrects 边 + 旧记录 status='superseded'。
        审计不删——旧记录留库(仅改状态),检索靠 status 门自动排除(supersede 可被作者回溯)。
        三步(CREATE 新 / RELATE corrects / UPDATE 旧)单事务原子提交,不出现"半更正"中间态。

        时态与信心默认【承接】旧记录;传对应参数即更正之(_UNSET 哨兵区分"未传"与"显式设 None",
        故 valid_to=None 可表达"改为无界")。corrects 边方向:旧 --corrects--> 新
        (顺着更正边前向可达"取代它的当前记录",天然构成审计链)。

        幂等(M-1):取代记录用确定性来源键 (work, source_type=reason, source_id='supersede:'+旧id)
        标识,CREATE 前预查——与 Task 9 给 add_memory_item 的 (work,source_type,source_id) 预查同款。
        连接重连重试落在"首次已提交、响应丢失"窗口时,预查命中已建的取代记录直接返回(不再撞
        显式 id 冲突,也不会二次更正);同 (旧id,reason) 的重复 supersede 视为幂等重放。
        (要对同一条做第二次不同更正,应 supersede 上一次的【新记录】,其 source_id 不同,天然区分。)"""
        old = self.get_memory(memory_id)
        if old is None:
            raise ValueError(f"supersede_memory: memory_item '{memory_id}' 不存在")
        _reason = reason or "author_correction"
        _src_id = f"supersede:{memory_id}"
        _dup = self._query(
            "SELECT meta::id(id) AS id FROM memory_item "
            "WHERE work=$w AND source_type=$st AND source_id=$sid LIMIT 1",
            {"w": old.get("work"), "st": _reason, "sid": _src_id})
        if _dup:
            return self.get_memory(_dup[0]["id"])   # 幂等重放:取代记录已建,直接返回

        def _pick(v, key):
            return old.get(key) if v is _UNSET else v

        from datetime import datetime as _dt, timezone as _tz
        from uuid import uuid4

        from scribe3.embed import embed
        from scribe3.text_tokens import tokenize_for_fts
        new_text = text if text is not None else (old.get("text") or "")
        toks = tokenize_for_fts(new_text or "")
        vec = embed([new_text or ""])[0]
        new_id = uuid4().hex
        prov = list(provenance) if provenance is not None else list(old.get("provenance") or [])
        links = list(linked_ids) if linked_ids is not None else list(old.get("linked_ids") or [])
        self._context_tx(
            "BEGIN TRANSACTION; "
            "CREATE $new_rec SET "
            "work=$work, scope_type=$scope_type, scope_id=$scope_id, kind=$kind, "
            "text=$text, summary=$summary, condition=$condition, "
            "source_type=$source_type, source_id=$source_id, "
            "status='active', confidence=$confidence, importance=$importance, pinned=$pinned, "
            "supersedes=$old_rec, observed_at=type::datetime($observed_at), "
            "valid_from=$valid_from, valid_to=$valid_to, "
            "known_from=$known_from, known_to=$known_to, "
            "provenance=$provenance, linked_ids=$linked_ids, "
            "tokens=$tokens, embedding=$embedding, updated_at=time::now(); "
            "RELATE $old_rec->memory_relation->$new_rec "
            "SET relation='corrects', weight=1.0, provenance={reason: $reason}; "
            "UPDATE $old_rec SET status='superseded', updated_at=time::now(); "
            "COMMIT TRANSACTION;",
            {"new_rec": RecordID("memory_item", new_id),
             "old_rec": RecordID("memory_item", memory_id),
             "work": old.get("work"), "scope_type": old.get("scope_type") or "work",
             "scope_id": old.get("scope_id") or old.get("work"),
             "kind": old.get("kind") or "episodic",
             "text": new_text, "summary": old.get("summary") or "",
             "condition": old.get("condition"),
             "source_type": _reason,
             "source_id": _src_id,
             "confidence": float(_pick(confidence, "confidence")),
             "importance": int(_pick(importance, "importance")),
             "pinned": bool(old.get("pinned")),
             "observed_at": _dt.now(_tz.utc).isoformat(),
             "valid_from": _pick(valid_from, "valid_from"),
             "valid_to": _pick(valid_to, "valid_to"),
             "known_from": _pick(known_from, "known_from"),
             "known_to": _pick(known_to, "known_to"),
             "provenance": prov, "linked_ids": links,
             "tokens": toks, "embedding": vec, "reason": _reason})
        # Task 16-B:记忆 supersede 发表级失效,清检索缓存里被更正/取代的经验记忆。
        _emit_cache_invalidation("memory_item", old.get("work"))
        return self.get_memory(new_id)

    def _forget_origin_event_id(self, mem: dict) -> str | None:
        """回溯该记忆的捕获来源 memory_event(可识别原文残留链)。
        捕获管线落 memory_item 时 source_id=event_id(见 memory_capture._route),故来源事件的
        event_id == memory_item.source_id。只认真存在的 memory_event(手工 add_memory 无来源事件/
        supersede 的 source_id='supersede:…' 均查不到 → 返回 None,不误删)。"""
        sid = (mem.get("source_id") or "").strip()
        if not sid:
            return None
        ev = self.get_memory_event(sid)
        return sid if ev else None

    def forget_impact(self, memory_id: str) -> dict:
        """遗忘【第一阶段】:生成影响清单,不删任何东西。
        如实披露 forget 将清除的【全部】可识别残留(I-1 修:不止 memory_item):
          · 记忆本体 memory_item(含 embedding/tokens);
          · 触及它的联想边 memory_relation(in/out 两侧);
          · 捕获来源事件 memory_event 的 payload 原文(若来自捕获管线)——否则 consolidate
            会从残留 payload 把被遗忘原文自动重炼进 working_summary、甚至 re-drain 整条复活;
          · 受影响线程的派生 working_summary(作废,由下次 consolidate 从存活事件重建)。
        正典/领域数据(proposition 等)不在清单内——forget 只管经验记忆。"""
        mem = self.get_memory(memory_id)
        if mem is None:
            return {"memory_id": memory_id, "exists": False,
                    "relations": [], "relation_count": 0,
                    "origin_event_id": None, "working_summary_thread": None,
                    "note": "记忆不存在,无需遗忘。"}
        rec = RecordID("memory_item", memory_id)
        edges = self._query(
            "SELECT relation, meta::id(in) AS in_id, meta::id(out) AS out_id "
            "FROM memory_relation WHERE in=$r OR out=$r", {"r": rec})
        rels: list[dict] = []
        for e in (edges or []):
            outgoing = e.get("in_id") == memory_id
            rels.append({"relation": e.get("relation"),
                         "direction": "out" if outgoing else "in",
                         "other_id": e.get("out_id") if outgoing else e.get("in_id")})
        # embedding/tokens 是否真实存在(M-3:查实,不再恒 True 装饰)
        pres = self._query(
            "SELECT (embedding != NONE AND array::len(embedding) > 0) AS has_emb, "
            "(tokens != NONE AND tokens != '') AS has_tok "
            "FROM type::record('memory_item', $id)", {"id": memory_id})
        has_emb = bool(pres[0].get("has_emb")) if pres else False
        has_tok = bool(pres[0].get("has_tok")) if pres else False
        origin_event_id = self._forget_origin_event_id(mem)
        # 受影响 working_summary 线程:thread 域记忆的 scope_id 即 thread_id;否则取来源事件线程。
        ws_thread = mem.get("scope_id") if mem.get("scope_type") == "thread" else None
        if not ws_thread and origin_event_id:
            ev = self.get_memory_event(origin_event_id)
            ws_thread = (ev or {}).get("thread_id")
        return {
            "memory_id": memory_id, "exists": True,
            "kind": mem.get("kind"), "status": mem.get("status"),
            "text": mem.get("text"),
            "relations": rels, "relation_count": len(rels),
            "has_embedding": has_emb, "has_tokens": has_tok,
            "origin_event_id": origin_event_id, "working_summary_thread": ws_thread,
            "note": "确认后将永久删除:经验记忆本体(含 embedding/tokens)、其联想边、"
                    "捕获来源事件 payload 原文(若有)、并作废受影响线程的 working_summary;"
                    "正典/领域数据(proposition 等)不受影响。",
        }

    def forget_memory(self, memory_id: str, *, confirmed: bool = False) -> dict:
        """遗忘【第二阶段】:仅在 confirmed=True 时真删,且清除【全部可识别残留】(I-1)。
        未确认 → 只回影响清单并 deleted=False(不删)。确认 → 单事务删:
          ① 该记忆的 memory_relation 边(in/out 两侧);
          ② memory_item 本体(embedding/tokens 随记录一并消失);
          ③ 捕获来源事件 memory_event(若来自捕获管线)——否则 consolidate 会从其残留
             payload 把被遗忘原文自动重炼进 working_summary,甚至 re-drain 整条复活;
          ④ 作废受影响线程的 working_summary(下次 consolidate 从存活事件重建,不含被遗忘原文)。
        只删本记忆的边,不动关联到的其它记忆;正典/领域 object lifecycle 一概不碰。"""
        impact = self.forget_impact(memory_id)
        if not impact.get("exists") or not confirmed:
            return impact | {"deleted": False}
        rec = RecordID("memory_item", memory_id)
        origin_event_id = impact.get("origin_event_id")
        ws_thread = impact.get("working_summary_thread")
        work = self.get_memory(memory_id).get("work")
        with self.transaction():
            self._execute_write(
                "DELETE memory_relation WHERE in=$r OR out=$r RETURN NONE", {"r": rec})
            self._execute_write(
                "DELETE type::record('memory_item', $id) RETURN NONE", {"id": memory_id})
            if origin_event_id:   # 断复活链:删来源事件,consolidate/re-drain 再无残留原文可取
                self._execute_write(
                    "DELETE memory_event WHERE event_id=$e RETURN NONE", {"e": origin_event_id})
            if ws_thread and work is not None:   # 作废派生工作摘要(下次 consolidate 从存活事件重建)
                self._execute_write(
                    "DELETE type::record('working_summary', $rid) RETURN NONE",
                    {"rid": f"{work}|{ws_thread}"})
        return {"memory_id": memory_id, "deleted": True,
                "relations_deleted": impact.get("relation_count", 0),
                "origin_event_deleted": bool(origin_event_id),
                "working_summary_invalidated": bool(ws_thread)}

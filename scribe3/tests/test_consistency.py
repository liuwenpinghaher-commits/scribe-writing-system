"""P21 facts_at 内存/真库对拍 + P23 单写点 spy + P04 load_knowledge 缓存
+ S4 知识边孤儿对拍(W3#8)。"""
from scribe3.ontology import Entity, Fact, KnowledgeEdge, World
from scribe3.knowledge import project_frame, dramatic_irony


class TestFactsAtParity:
    """P21: World.facts_at 与 SurrealStore.facts_at 逐章一致"""

    def test_parity_memory_vs_store(self, store):
        w = World()
        store.add_entity(Entity("role:x", "character", "x"))
        w.add_entity(Entity("role:x", "character", "x"))
        seed = [
            Fact("fact:a", "role:x", "attr", "va", valid_from=1),
            Fact("fact:b", "role:x", "attr", "vb", valid_from=2, valid_to=5),
            Fact("fact:c", "role:x", "attr", "vc", valid_from=3),
        ]
        for f in seed:
            w.add_fact(f)
            store.add_fact(f)
        for ch in range(1, 7):
            mem = {f.id for f in w.facts_at(ch)}
            db = {f.id for f in store.facts_at(ch)}
            assert mem == db, f"第{ch}章漂移: memory={mem} store={db}"


class TestSingleWritePoint:
    """P23: 所有世界状态写经 _execute_write"""

    def test_add_methods_use_execute_write(self, store, monkeypatch):
        calls = []
        orig = store._execute_write
        def spy(surql, vars):
            calls.append(surql)
            orig(surql, vars)
        monkeypatch.setattr(store, "_execute_write", spy)
        from scribe3.ontology import Entity, Fact, KnowledgeEdge
        store.add_entity(Entity("role:s", "character", "s"))
        store.add_fact(Fact("fact:s1", "role:s", "attr", "val", valid_from=1))
        store.add_knowledge(KnowledgeEdge("role:s", "fact:s1", since_chapter=1, acquired_via="saw"))
        assert len(calls) >= 3, "add_entity/add_fact/add_knowledge 都应经 _execute_write"
        for s in calls:
            # UPDATE:add_fact 写入后经单点 _execute_write 补 embedding(P1),亦为合法写
            assert any(kw in s for kw in ["CREATE", "UPSERT", "RELATE", "UPDATE"]), f"写语句: {s}"


class TestLoadKnowledgeCaching:
    """P04: dramatic_irony 只调一次 load_knowledge(去 N+1)"""

    def test_dramatic_irony_single_load(self, store, monkeypatch):
        from scribe3.scenario import luanshi_leak_world
        luanshi_leak_world(store)
        calls = {"n": 0}
        orig = store.load_knowledge
        def counting():
            calls["n"] += 1
            return orig()
        monkeypatch.setattr(store, "load_knowledge", counting)
        dramatic_irony(store, "role:老道", 1)
        assert calls["n"] == 1, f"dramatic_irony 应只调 1 次 load_knowledge,实际 {calls['n']}"


class TestWriteGate:
    """P02: 所有写端点(含未来新增)必须显式登记授权语义"""

    KNOWN_REST_WRITE_ROUTES = {
        ("POST", "/characters"), ("PATCH", "/characters/{local}"), ("DELETE", "/characters/{local}"),
        ("POST", "/facts"), ("PATCH", "/facts/{local}"), ("DELETE", "/facts/{local}"),
        ("POST", "/promises-new"), ("PATCH", "/promises/{pid}"), ("DELETE", "/promises/{pid}"),
        ("POST", "/promises/{pid}/advance"), ("POST", "/promises/{pid}/mark-herring"),
        ("POST", "/promises/{pid}/clues"), ("DELETE", "/promises/{pid}/clues/{idx}"),
        ("POST", "/motifs-new"), ("PATCH", "/motifs/{mid}"), ("DELETE", "/motifs/{mid}"),
        ("POST", "/intent"), ("PUT", "/intent"), ("POST", "/works"),
        # DELETE /works/{slug}:移入废弃箱(软删,DB 不动)——真删见下方 purge。
        ("DELETE", "/works/{slug}"),
        ("PATCH", "/works/{slug}"),
        # 作品生命周期(2026-07-13):restore 复现;purge 是唯一真删入口,两道门=
        # 必须已在废弃箱(delete_work 语义收窄校验) + confirm_title 与库中书名一致。
        ("POST", "/works/{slug}/restore"), ("DELETE", "/works/{slug}/purge"),
        ("POST", "/save-chapter"), ("POST", "/ingest"),
        ("POST", "/checkpoint"),
        ("POST", "/save-draft"),   # Phase0-BE2 四阶段:写 chapter.draft + 追加 draft 版
        ("POST", "/check"),   # 护栏轻检查:不落库,read-only POST
        ("POST", "/post-check"),   # 生成后全量体检:QC+泄露+纪律LLM,不落库,read-only POST
        # 语义纪律修复：通过既有章节修复锁产出候选稿；质量门失败绝不落正文。
        ("POST", "/semantic-repair"),
        # 作者显式重算派生质量缓存；不改正文、版本或正典数据。
        ("POST", "/quality/refresh"),
        ("POST", "/draft-check"),   # 块四b 草稿轻量确定性分析:确定性检测器+泄露预览,只读不落库,read-only POST
        # 主编主动化(D-030/031):想法收件箱+Chapter Pilot。授权语义:
        # ideas 只写 idea 表/pilot_steer(setting/revise 永远 pending_approval,宪法);
        # pilot step/approve/run 全走既有链(loop/post-check/留版),finalize 宪法锚留人;
        # pause/reset-step 只改进程旗/清 parked 标记。
        ("POST", "/ideas"),
        ("POST", "/ideas/resolve"),   # 想法处理完出收件箱(status→done,防积压)
        ("POST", "/pilot/step"), ("POST", "/pilot/approve"), ("POST", "/pilot/run"),
        ("POST", "/pilot/pause"), ("POST", "/pilot/reset-step"),
        ("POST", "/pilot/dismiss"),   # 僵尸 pilot 态退出编排(清 pilot_*,零破坏)
        ("POST", "/tension-check"),   # M2a张力检查:确定性3项+LLM rubric,只读不落库,read-only POST
        ("POST", "/dedup-chapter"),   # QC治层:确定性事后跨章改写并存回(作者可信通道)
        ("POST", "/chat/write"),
        # 演绎事实对齐:只读 chapter.scene_truth + LLM 审查,绝不写入正典。
        ("POST", "/chapters/{seq}/deductions/grounding"),
        # Hermes Runs/Approval:写入型 agentic 任务入口。create/approval/stop 都走
        # scribe3_write gateway + work-scoped session key,并 best-effort 写 ai_run_trace。
        ("POST", "/ai/runs"),
        ("POST", "/ai/runs/{run_id}/approval"),
        ("POST", "/ai/runs/{run_id}/stop"),
        ("POST", "/world-rules"), ("DELETE", "/world-rules"),
        ("POST", "/factions"), ("DELETE", "/factions"),
        ("POST", "/items"), ("DELETE", "/items"),
        ("POST", "/items/{name}/state"),   # P1-9 物品状态流转:update_item_state 追加 state_history
        ("POST", "/terms"), ("DELETE", "/terms"),
        ("POST", "/char-states"),
        ("POST", "/ingest-unverified/{uid}/accept"),
        ("POST", "/ingest-unverified/{uid}/ignore"),
        ("POST", "/ingest-unverified/ignore-all"),   # R2-12:批量忽略死水(改 status,写)
        ("POST", "/facts/supersede"),
        ("POST", "/knowledge/forget"),
        ("POST", "/character-relations"),
        ("POST", "/character-relations/evolve"),
        ("POST", "/character-relations/end"),
        # CX-Task 5:通用实体关系表(双向认知 + 主编独知 truth + 时态)。作者可信通道,
        # 全权(含 truth);掩码哨兵见 app.add_entity_relation_ep 的 truth==_SECRET_MASK pop。
        ("POST", "/entity-relations"), ("DELETE", "/entity-relations"),
        ("POST", "/voice-flags/{fid}/resolve"),
        ("POST", "/voice-flags/fold"),
        # F-01 大纲/卷章树手稿支
        ("POST", "/chapters"),
        ("POST", "/chapters/reorder"),
        ("PATCH", "/chapters/{seq}"),
        ("POST", "/chapters/{seq}/archive"),
        ("POST", "/chapters/{seq}/restore"),
        ("DELETE", "/chapters/{seq}"),
        ("POST", "/volumes"),
        ("PATCH", "/volumes/{vid}"),
        ("DELETE", "/volumes/{vid}"),
        # 作者工具尾项:事件叙事位编辑(尾1)
        ("PATCH", "/events/{eid}/narrative"),
        # 事件因果作者直编：独立场景必须给出可审计根理由；建立因果边会清除根理由。
        ("PATCH", "/events/{eid}/causal-root"),
        ("PATCH", "/events/{eid}/causal"),
        # 工艺引擎P0 Task4:角色弧光锚(作者直编,局部更新)+ arc_plan 里程碑增删
        ("PATCH", "/char-anchors"),
        ("POST", "/arc-beats"),
        ("DELETE", "/arc-beats/{beat_id}"),
        # 块四a-1 素材库(非正典材料,作者直编;ingest/图谱/限知/时间线零感知)
        ("POST", "/materials"),
        ("PATCH", "/materials/{mid}"),
        ("DELETE", "/materials/{mid}"),
        # 审查修复:素材导入是作者显式提交路径;import 只建后台预览 job,
        # commit 才批量落素材且逐条返回 failed/warnings。
        ("POST", "/materials/import"),
        ("POST", "/materials/import/{job_id}/commit"),
        # 人工采纳素材后登记章级溯源引用(作者显式操作)。
        ("POST", "/materials/{mid}/refs"),
        # 审查修复:统一对象 lifecycle 删除,必须先经过 impact/token;
        # 有引用时无 token 返回 409,不会静默删除。
        ("DELETE", "/objects/{object_type}/{object_id}"),
        # 审查修复:统一对象 lifecycle 归档,作者显式操作;只标记 archived,
        # 不清引用、不硬删,用于替代高风险删除默认动作。
        ("POST", "/objects/{object_type}/{object_id}/archive"),
        # 方案B任务24:story-import 逆向导入(作者可信通道,journal 断点续跑)
        ("POST", "/import"),
        # 北极星任务4:修复环编排(写:留版本;pass 分支另 save_chapter+ingest;
        # advisory/needs_human 分支只留版本不落正文——写语义见 loop_chapter docstring)
        ("POST", "/loop/chapter"),
        # 北极星任务11:选择环(写:候选留版本;finalize 落正文+final版+lesson)
        ("POST", "/select/chapter"),
        ("POST", "/select/finalize"),
        # 统一上下文 Task 4:会话创建(落 revision=0 初始快照)+ CAS 导航推进。
        # 授权语义:只写 context_session/context_snapshot 两表(导航留痕),
        # 不碰正典数据;navigate 失配 409 绝不覆盖,同 navigation_id 幂等重放。
        ("POST", "/context/sessions"),
        ("POST", "/context/sessions/{session_id}/navigate"),
        # 统一上下文 Task 6:主编线程显式分支。授权语义:只写 editorial_thread
        # 一表(建子线程,写 parent_thread_id),不碰正典/对话内容;导航路径绝不调此。
        ("POST", "/chat/threads/{thread_id}/fork"),
        # P0a 多会话(2026-07-16):显式新建会话 + 改名/归档。授权语义:只写
        # editorial_thread 一表(title/status 元数据),不碰正典/对话内容;
        # PATCH 零降级门(不存在 404/跨 work 409/非法 status 422),归档可逆(status 回 active)。
        ("POST", "/chat/threads"),
        ("PATCH", "/chat/threads/{thread_id}"),
        # P0b(2026-07-16):摘要兜底(夜间 cron 调)。授权语义:只写 editorial_thread 的
        # summary/summarized_upto_ts/summary_error 三字段(LLM 压缩讨论历史),不碰正典/消息;
        # 幂等(阈值内秒过);失败线程如实列 errors 不静默。
        ("POST", "/maintenance/summarize-threads"),
        # P2(2026-07-16):每日创作摘报(cron 晨间调)。授权语义:只写 chief_digest 一表
        # (一天一行,重跑覆盖),汇总只读源(progress/inbox/promises);任一源失败如实进
        # error 字段进收件箱红字,绝不产出假完整摘报。
        ("POST", "/maintenance/daily-digest"),
        # 统一设置中心:PUT 写 SQLite 设置台账(带校验+审计,secret 掩码);
        # reset 删覆盖值回落 env/默认。不碰正典数据、不碰 SurrealDB。
        ("PUT", "/settings/{key}"),
        ("POST", "/settings/{key}/reset"),
        # 设置中心网关区:白名单内 profile 文件写(自动 .bak 备份 + sha 冲突 409;
        # .env 掩码行按原文件还原,密钥不经网络明文往返);重启由独立端点显式触发。
        ("PUT", "/gateway/files"),
        # 设置中心:一键重启网关(nohup 后台+轮询探活;失败如实报,不假成功;
        # profile 白名单硬编码 scribe3/scribe3_write,不接受任意命令注入面)
        ("POST", "/gateway/restart"),
        # Hermes Dashboard 探活与一键启动:拉起本机官方管理台进程,hermes_bin
        # 预检+nohup+轮询;无请求参数,无注入面。
        ("POST", "/gateway/dashboard/start"),
        # 统一上下文记忆 Task 8/10:直连 Hermes 会话的记忆钩子。授权语义:
        # prefetch 只读检索组装(不落库,read-only POST,组装失败降级空块);
        # capture-turn 幂等捕获对话轮进经验记忆(event_id 幂等,分类兜底偏保守
        # 待审,正典红线在 MemoryCapture 内,失败告警不 5xx);
        # flush 固化线程工作摘要((work,thread) 唯一 UPSERT,幂等,best-effort)。
        ("POST", "/memory/prefetch"),
        ("POST", "/memory/capture-turn"),
        ("POST", "/memory/flush"),
        # 章内治层(S-003):确定性事后章内改写并存回(与 /dedup-chapter 对称的
        # 作者可信通道;含限知二次门+回滚门,改写失败回滚原文)
        ("POST", "/polish-chapter"),
    }

    def test_no_unaudited_write_route(self):
        import scribe3.app as A
        actual = set()
        for route in A.app.routes:
            methods = getattr(route, "methods", set())
            if methods is None:
                continue
            for m in methods:
                if m in {"POST", "PUT", "PATCH", "DELETE"}:
                    actual.add((m, route.path))
        # 健康检查除外;背景任务端点不在此列
        exempt = {("GET", "/health")}
        unknown = actual - self.KNOWN_REST_WRITE_ROUTES - exempt
        assert not unknown, f"新写路径未登记授权语义: {unknown}"


class TestOrphanKnowledgeEdges:
    """S4 (W3#8): knows/reader_knows 孤儿边扫描 — 指向已删命题的悬挂边不应存在。"""

    def test_normal_ingest_no_orphans(self, store):
        """正常 ingest + purge 后不留孤儿边。"""
        from scribe3.ingest import apply_delta
        store.add_entity(Entity("role:甲", "character", "甲"))
        apply_delta(store, {
            "learned": [{"who": "甲", "fact": "天道不可违"}],
            "did": [],
        }, seq=1)
        orphans = store.orphan_knowledge_edges()
        assert orphans == [], f"正常 ingest 后不应有孤儿边,实际: {orphans}"

    def test_purge_leaves_no_orphans(self, store):
        """purge_ingest 清掉命题时,同批次 knows/reader_knows 边也被清。"""
        from scribe3.ingest import apply_delta
        store.add_entity(Entity("role:乙", "character", "乙"))
        apply_delta(store, {
            "learned": [{"who": "乙", "fact": "玄妙之道难测"}],
            "did": [],
        }, seq=2)
        # 重新 ingest(purge + 重写)
        apply_delta(store, {
            "learned": [{"who": "乙", "fact": "玄妙之道难测"}],
            "did": [],
        }, seq=2)
        orphans = store.orphan_knowledge_edges()
        assert orphans == [], f"purge 后不应有孤儿边,实际: {orphans}"

    def test_delete_proposition_cascades_knows_edge(self, store):
        """SurrealDB 图语义保障:删命题时 knows 边级联消失 → orphan_knowledge_edges 不会有遗留。
        这是对 SurrealDB 不变量的回归测试——确保级联删除正常工作。"""
        store.add_entity(Entity("role:丙", "character", "丙"))
        store.add_fact(Fact("fact:cascade_test", "role:丙", "获知", "级联删除验证值", valid_from=1))
        store.add_knowledge(KnowledgeEdge("role:丙", "fact:cascade_test", since_chapter=1,
                                          acquired_via="learned"))
        # 确认目前无孤儿、knows 边存在
        assert store.orphan_knowledge_edges() == []
        # 删掉命题:SurrealDB 会级联清理 knows 边
        store.delete_record("fact:cascade_test")
        # 级联后:knows 边消失,孤儿扫描仍返回空(因为边本身被级联删了)
        orphans = store.orphan_knowledge_edges()
        assert orphans == [], \
            f"SurrealDB 级联删除后不应有孤儿边(边已随节点消失),实际: {orphans}"
        # 额外验证:knows 边确实已消失
        knows_rows = store._query("SELECT id FROM knows")
        assert not knows_rows, "删命题后 knows 边应已级联消失"

    def test_reader_knows_delete_proposition_cascades(self, store):
        """reader_knows 表(非图边,是独立表)在命题删除后依赖 orphan_knowledge_edges 检出悬挂。
        注意:reader_knows 用的是 CREATE(非 RELATE),SurrealDB 不级联——这是需要 orphan 扫描保护的场景。"""
        store.add_entity(Entity("role:丁", "character", "丁"))
        store.add_fact(Fact("fact:rk_test", "role:丁", "获知", "读者知识测试", valid_from=1))
        store.add_knowledge(KnowledgeEdge("reader", "fact:rk_test", since_chapter=1,
                                          acquired_via="narrated"))
        assert store.orphan_knowledge_edges() == []
        # 删掉命题
        store.delete_record("fact:rk_test")
        # reader_knows 行本身不级联删除(独立表),orphan 扫描应能检出
        orphans = store.orphan_knowledge_edges()
        assert len(orphans) >= 1, \
            f"reader_knows 孤儿边应被 orphan_knowledge_edges 检出,实际: {orphans}"
        assert any("rk_test" in str(o) for o in orphans), \
            f"孤儿边记录应含 rk_test 引用,实际: {orphans}"


class TestCrossChapterConsistency:
    """M3 跨章一致性检测: validate_cross_chapter_consistency()。

    (a) 数字声明矛盾: 同一专名实体在不同章绑定不同数字 → numeric_inconsistency
    (b) 命名一致性(死代码实装): 高频未登记疑似专名 → unregistered_name
    """

    def test_numeric_inconsistency_detected(self, store):
        """章1「潭家二十七口」,章2「潭家三百一十七口」→ 报 numeric_inconsistency。"""
        # 登记专名"潭家"为阵营(faction)
        store.add_faction("潭家", ideology="", status="active", leader="",
                          known_members=[], public_face="")
        store.save_chapter(1, "潭家满门二十七口尽死于乱世。", title="第一章")
        store.save_chapter(2, "听闻潭家三百一十七口皆遭屠戮。", title="第二章")
        hints = store.validate_cross_chapter_consistency()
        types = [h["type"] for h in hints]
        assert "numeric_inconsistency" in types, (
            f"潭家数字矛盾(二十七口 vs 三百一十七口)应报 numeric_inconsistency,实际 hints: {hints}")
        ni = [h for h in hints if h["type"] == "numeric_inconsistency"]
        # 应包含实体名和两处证据
        assert any("潭家" in h.get("entity", "") or "潭家" in h.get("description", "")
                   for h in ni), f"numeric_inconsistency 应指向「潭家」,实际: {ni}"

    def test_numeric_consistent_no_hint(self, store):
        """同一数字无矛盾 → 不报 numeric_inconsistency。"""
        store.add_faction("潭家", ideology="", status="active", leader="",
                          known_members=[], public_face="")
        store.save_chapter(1, "潭家满门二十七口尽死于乱世。", title="第一章")
        store.save_chapter(2, "潭家二十七口皆亡,无一生还。", title="第二章")
        hints = store.validate_cross_chapter_consistency()
        ni = [h for h in hints if h["type"] == "numeric_inconsistency"]
        assert not ni, f"数字一致时不应报矛盾,实际: {ni}"

    def test_unregistered_high_freq_name_reported(self, store):
        """正文中高频出现(≥3次)但未登记的疑似专名 → 报 unregistered_name。"""
        # 不登记任何专名;正文中"灵虚子"出现3次
        store.save_chapter(1, "灵虚子施法,灵虚子退步,灵虚子最终败走。", title="第一章")
        hints = store.validate_cross_chapter_consistency()
        types = [h["type"] for h in hints]
        assert "unregistered_name" in types, (
            f"高频未登记专名「灵虚子」应报 unregistered_name,实际 hints: {hints}")

    def test_registered_name_not_reported(self, store):
        """已登记的专名高频出现 → 不报 unregistered_name。"""
        store.add_entity(__import__('scribe3.ontology', fromlist=['Entity']).Entity(
            "role:灵虚子", "character", "灵虚子"))
        store.save_chapter(1, "灵虚子施法,灵虚子退步,灵虚子最终败走。", title="第一章")
        hints = store.validate_cross_chapter_consistency()
        ur = [h for h in hints if h["type"] == "unregistered_name"
              and h.get("entity") == "灵虚子"]
        assert not ur, f"已登记专名「灵虚子」不应报 unregistered_name,实际: {ur}"

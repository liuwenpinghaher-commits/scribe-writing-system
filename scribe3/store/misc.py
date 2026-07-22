"""SurrealStore mixin: misc."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class MiscMixin:

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
        审计 C-3:同名已被人裁决(ignored/accepted)则不再登记——决策跨 re-ingest 存活。"""
        decided = self._query(
            "SELECT id FROM ingest_unverified WHERE name=$n AND status != 'pending' LIMIT 1",
            {"n": name})
        if decided:
            return
        self._execute_write(
            "CREATE ingest_unverified SET name=$n, seq=$s, role=$r, status='pending'",
            {"n": name, "s": seq, "r": role})

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
                r = ingest_chapter(self, seq, complete_fn)
                replayed = not r.get("parse_failed", False)
            except Exception as e:
                logging.getLogger("scribe3.store").warning(
                    "accept_unverified uid=%s seq=%s replay 失败(soft): %s", uid, seq, e)

        return {"created": created, "oid": oid, "replayed": replayed}

    def ignore_unverified(self, uid: str) -> None:
        """将待确认行标记为 ignored。"""
        self._execute_write(
            "UPDATE type::record('ingest_unverified', $u) SET status='ignored'", {"u": uid})

    def all_entities(self) -> list[Entity]:
        """角色 + 地点(前端结构面/实体清单用)。"""
        prows = self._query("SELECT meta::id(id) AS local, name FROM place")
        return self.characters() + [Entity(f"place:{r['local']}", "place", r["name"]) for r in prows]

    def add_motif(self, name: str, theme: str = "", echoes: str = "", unfolding: str = "") -> None:
        self._execute_write(
            "CREATE motif SET name=$n, theme=$t, echoes=$e, unfolding=$u",
            {"n": name, "t": theme, "e": echoes, "u": unfolding})

    def list_motifs(self) -> list[dict]:
        return self._query("SELECT meta::id(id) AS id, name, theme, echoes, unfolding FROM motif")

    def add_motif_instance(self, motif_id: str, chapter: int,
                           evidence: str = "", ingest_seq: int | None = None) -> None:
        self._execute_write(
            "CREATE motif_instance SET motif_id=$m, chapter=$c, evidence=$e, ingest_seq=$i",
            {"m": motif_id, "c": chapter, "e": evidence,
             "i": ingest_seq if ingest_seq is not None else chapter})

    def list_motif_instances(self, chapter: int) -> list[dict]:
        """本章触及的母题:[{motif_id, name, evidence}](name 由 motif 表 join)。"""
        rows = self._query(
            "SELECT motif_id, evidence FROM motif_instance WHERE chapter = $c",
            {"c": chapter})
        names = {m.get("id"): (m.get("name") or "") for m in self.list_motifs()}
        return [{"motif_id": r.get("motif_id"),
                 "name": names.get(r.get("motif_id"), ""),
                 "evidence": r.get("evidence") or ""} for r in rows]

    def upsert_chief_digest(self, day: str, body: str, error: str | None = None) -> None:
        """P2:每日创作摘报一天一行(重跑覆盖);error 非空=部分失败源,收件箱如实显示。"""
        self._execute_write(
            "DELETE chief_digest WHERE day=$d; "
            "CREATE chief_digest SET work=$w, day=$d, body=$b, error=$e RETURN NONE",
            {"d": day, "w": self.db_name, "b": body, "e": error})

    def latest_chief_digest(self) -> dict | None:
        rows = self._query(
            "SELECT work, day, body, error, <string> created_at AS created_at "
            "FROM chief_digest ORDER BY day DESC LIMIT 1")
        return rows[0] if rows else None

    def get_distill_marker(self, chapter: int) -> dict | None:
        rows = self._query(
            "SELECT chapter, msg_count, last_turn FROM type::record('distill_marker',$c)",
            {"c": chapter})
        return rows[0] if rows else None

    def set_distill_marker(self, chapter: int, msg_count: int, last_turn: str) -> None:
        self._execute_write(
            "UPSERT type::record('distill_marker',$c) SET chapter=$c, msg_count=$n, "
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
        rows = self._query("SELECT id FROM type::record($tbl,$local) LIMIT 1",
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

    def update_motif(self, motif_id: str, fields: dict) -> None:
        self._update_by("motif", motif_id, fields)

    def delete_motif(self, motif_id: str) -> None:
        self._delete_by("motif", motif_id)

    def purple_patterns(self) -> list[str]:
        """本书升华正则(喂 critique.find_purple_prose 的 extra_patterns)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "purple_regex"]

    def allow_patterns(self) -> list[str]:
        """方案B任务14:本书题材豁免正则(前置 skip 判定——减法,与 purple_patterns/
        extra_patterns 的加法标记彻底分离)。实际消费方:critique.find_purple_prose
        (经 quality_flags/quality_issues 透传)与 critique.find_emotion_telling
        (app.py /post-check 直接传入)——不是"各检测器"都吃这个白名单,新增消费方
        时请在此处补记,避免文档与接线脱节(收尾清理批 B14 审查发现)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "allow_pattern"]

    def allow_words(self) -> list[str]:
        """方案B任务14:本书题材豁免词(喂 critique.find_ai_tics 的 allow_words 白名单)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "allow_word"]

    def latest_draft_version(self, seq: int) -> dict | None:
        """该章最新 draft 版(prose+stats),供刷新恢复。无 draft 版返回 None。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, seq, prose, label, summary, stats, created_at "
            "FROM chapter_version WHERE seq=$seq AND stage='draft' "
            "ORDER BY created_at DESC LIMIT 1",
            {"seq": seq})
        if not rows:
            return None
        r = rows[0]
        r["stage"] = "draft"
        r.setdefault("summary", "")
        return r

    def total_word_count(self) -> int:
        """全书可见字数合计(qc_word_count 存稿缓存求和,不拉正文)。"""
        rows = self._query(
            "SELECT math::sum(qc_word_count) AS w FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        return int((rows[0].get("w") if rows else 0) or 0)

    def stats(self) -> dict:
        """本书章数 + 字数(读 QC 缓存,不回传全表正文)。"""
        count_rows = self._query(
            "SELECT count() AS chapter_count FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        word_rows = self._query(
            "SELECT math::sum(qc_word_count) AS word_count FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL")
        chapter_count = (count_rows[0].get("chapter_count") if count_rows else 0) or 0
        word_count = (word_rows[0].get("word_count") if word_rows else 0) or 0
        return {"chapter_count": chapter_count, "word_count": word_count}

    def progress(self, today: str | None = None, window: str | None = None) -> dict:
        """日字数序列 + 累计曲线 + 目标完成度 + 趋势窗口 + 最高产星期几。
        读 daily_progress + intent,纯聚合。
        window: '30' | '90' | 'all'(默认 'all')
        """
        import time as _time
        from datetime import date as _date, timedelta as _td
        today = today or _time.strftime("%Y-%m-%d")
        # `date` 是 SurrealDB 保留字,ORDER BY 须用别名;字典序即日期升序
        rows = self._query(
            "SELECT date AS dp_date, words_written, words_total FROM daily_progress ORDER BY dp_date")
        intent = self.get_intent()
        total_goal = intent.get("total_word_goal")       # None → 前端回退 100000
        daily_goal = intent.get("daily_word_goal")       # None → 不显每日目标
        total_words = self.stats().get("word_count", 0)
        # 把 dp_date 别名统一为 date 键(供 _compute_streaks 纯函数和输出共用)
        all_normalized = [{"date": r["dp_date"], "words_written": r["words_written"],
                           "words_total": r["words_total"]} for r in rows]

        # streak / heatmap 始终用全量数据,不受 window 裁剪影响
        cur_streak, longest_streak = _compute_streaks(all_normalized, today, daily_goal)
        today_words = next((r["words_written"] for r in all_normalized if r["date"] == today), 0)

        # window 裁剪:仅影响 daily 序列(用于图表);heatmap / streak 用全量
        win = str(window).strip() if window else "all"
        if win in ("30", "90"):
            n_days = int(win)
            cutoff = (_date.fromisoformat(today) - _td(days=n_days - 1)).isoformat()
            windowed = [r for r in all_normalized if r["date"] >= cutoff]
        else:
            windowed = all_normalized  # 'all' 或其他值均视为全程

        # weekday_histogram:基于全量数据聚合,返回 7 个槽(周一=0…周日=6)
        # 每槽:{weekday, label, total_words, avg_words, count}
        from collections import defaultdict
        _wd_total: dict[int, int] = defaultdict(int)
        _wd_count: dict[int, int] = defaultdict(int)
        for r in all_normalized:
            try:
                d = _date.fromisoformat(r["date"])
                ww = d.weekday()  # 0=周一,6=周日
                words = r.get("words_written") or 0
                if words > 0:   # 只统计有写字的天
                    _wd_total[ww] += words
                    _wd_count[ww] += 1
            except ValueError:
                pass
        _WD_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday_histogram = []
        for ww in range(7):
            tot = _wd_total.get(ww, 0)
            cnt = _wd_count.get(ww, 0)
            weekday_histogram.append({
                "weekday": ww,
                "label": _WD_LABELS[ww],
                "total_words": tot,
                "avg_words": round(tot / cnt) if cnt > 0 else 0,
                "count": cnt,
            })
        # 最高产星期几:按 avg_words 降序,取第一个有数据的
        best_wd = max(weekday_histogram, key=lambda x: x["avg_words"], default=None)
        best_weekday = best_wd["label"] if best_wd and best_wd["avg_words"] > 0 else None

        # 理想线(ideal):若设了 total_word_goal,按匀速插值
        # 起点=第一条记录日期,终点=总目标字数,每天均摊
        ideal_daily_rate = None
        if total_goal and total_goal > 0 and windowed:
            first_date = _date.fromisoformat(windowed[0]["date"])
            today_date = _date.fromisoformat(today)
            total_days_elapsed = max(1, (today_date - first_date).days + 1)
            ideal_daily_rate = round(total_goal / total_days_elapsed)   # 匀速字数/天
        # 在 daily 序列里附加 ideal_cumulative(匀速理想累计)
        daily_with_ideal = []
        for i, r in enumerate(windowed):
            row_date = _date.fromisoformat(r["date"])
            row = {"date": r["date"], "words": r["words_written"], "cumulative": r["words_total"]}
            if total_goal and windowed:
                first_d = _date.fromisoformat(windowed[0]["date"])
                days_from_start = (row_date - first_d).days + 1
                row["ideal_cumulative"] = min(total_goal, round(total_goal * days_from_start
                                              / max(1, (_date.fromisoformat(today) - first_d).days + 1)))
            daily_with_ideal.append(row)

        return {
            "today": today,
            "window": win,
            "total_words": total_words,
            "total_word_goal": total_goal,
            "daily_word_goal": daily_goal,
            "today_words": today_words,
            "daily": daily_with_ideal,
            "current_streak": cur_streak,
            "longest_streak": longest_streak,
            "heatmap": [{"date": r["date"], "words": r["words_written"]} for r in all_normalized],
            "weekday_histogram": weekday_histogram,
            "best_weekday": best_weekday,
            "ideal_daily_rate": ideal_daily_rate,
        }

    def add_arc_beat(self, character_id: str, beat_name: str, target_chapter: int,
                     lie_belief_target: int | None = None, trigger_event: str = "") -> None:
        """加一条弧光里程碑(beat):目标章 + 该拍应到达的 lie 信奉度 + 触发事件。"""
        self._execute_write(
            "CREATE arc_plan SET character_id=$c, beat_name=$b, target_chapter=$t, "
            "lie_belief_target=$lb, trigger_event=$te",
            {"c": character_id, "b": beat_name, "t": target_chapter,
             "lb": lie_belief_target, "te": trigger_event or None})

    def list_arc_plan(self, character_id: str) -> list[dict]:
        """角色的弧光里程碑,按 target_chapter 升序。"""
        return self._query(
            "SELECT meta::id(id) AS id, character_id, beat_name, target_chapter, "
            "lie_belief_target, trigger_event FROM arc_plan "
            "WHERE character_id=$c ORDER BY target_chapter ASC", {"c": character_id})

    def delete_arc_beat(self, beat_id: str) -> None:
        self._execute_write("DELETE type::record('arc_plan', $b)", {"b": beat_id})

    def latest_lie_belief(self, character_id: str, upto_chapter: int) -> int | None:
        """到某章为止最新的 lie 信奉度(char_state 里 chapter<=upto 且 lie_belief 非空的最新一条)。"""
        # SurrealDB 3.x:ORDER BY 字段必须出现在投影里,故连带 SELECT chapter
        rows = self._query(
            "SELECT lie_belief, chapter FROM char_state WHERE character_id=$c AND chapter<=$ch "
            "AND lie_belief IS NOT NONE ORDER BY chapter DESC LIMIT 1",
            {"c": character_id, "ch": upto_chapter})
        return rows[0]["lie_belief"] if rows else None

    def reverse_current_state(self, character_id: str) -> dict:
        """方案B任务24(story-import 逆向导入):对该角色 char_states 按 change_type 分组,
        各取 max(chapter) 的最新一条,合成「当前状态快照」——用于反推续写起点的角色当前态,
        与 char_state_at(锁定到某个既定章号)不同,这里没有"续写到第几章"的既定坐标,
        只关心"到目前为止最新是什么"。

        无状态角色(list_char_states 为空)返回 {}(不像 char_state_at 那样给空壳,
        逆向导入只关心"有没有可用状态",没有就是空,调用方据此判断是否需要人工补设定)。

        返回结构:
          - 每个出现过的 change_type 一个键,值为 {"chapter":最新章号,"summary":该条摘要,
            "after_state":该条 after_state}(该视图按 change_type 分组各取最新一条,
            用 latest_by_type 折叠即可——这里只关心"这一类型本身最新是什么",与
            "跨类型 chapter 全局序"无关);
          - 额外派生键(与 char_state_at 同范式,方便直接消费):
            abilities/relations/personality 分别聚合 ability/relation/personality/composite
            类型的 after_state;belief 类型的 lie_belief 提升为顶层 lie_belief 键。
            这些派生键必须照抄 char_state_at 的范式——对 list_char_states 返回的 rows
            (已按 chapter ASC 排序)直接顺序遍历、逐条 update 覆盖——因为 composite 与
            专项类型(如 ability)会写同一个键(如"剑术"),只有按全局 chapter 时间序
            遍历才能保证最终值是时间上最新的值;若先按 change_type 折叠
            (latest_by_type,dict 按首次插入序遍历)再合并,插入序较晚遍历到的旧类型
            会覆盖 chapter 实际更新的另一类型,产出过期值(B24 审查发现的正确性 bug)。
        """
        rows = self.list_char_states(character_id)
        if not rows:
            return {}
        latest_by_type: dict[str, dict] = {}
        for r in rows:
            latest_by_type[r["change_type"]] = r
        snapshot: dict = {}
        for ct, r in latest_by_type.items():
            after = r.get("after_state") or {}
            snapshot[ct] = {"chapter": r["chapter"], "summary": r.get("summary"),
                            "after_state": after or None}
        abilities: dict = {}
        relations: dict = {}
        personality = ""
        lie_belief = None
        for r in rows:
            ct = r["change_type"]
            after = r.get("after_state") or {}
            if ct in ("ability", "composite"):
                abilities.update(after.get("ability_snapshot") or {})
            if ct in ("relation", "composite"):
                relations.update(after.get("relation_snapshot") or {})
            if ct in ("personality", "composite"):
                p = after.get("personality_snapshot")
                if p:
                    personality = p
            if ct == "belief" and r.get("lie_belief") is not None:
                lie_belief = r["lie_belief"]
        if abilities:
            snapshot["abilities"] = abilities
        if relations:
            snapshot["relations"] = relations
        if personality:
            snapshot["personality"] = personality
        if lie_belief is not None:
            snapshot["lie_belief"] = lie_belief
        return snapshot

    def setting_completeness(self) -> dict:
        """检查当前书的设定完整度,返回各维度缺项。"""
        chars = self.characters()
        rules = self.list_world_rules()
        factions = self.list_factions()
        places = self._query("SELECT * FROM place")
        facts = self.facts_at(99999)

        char_issues = []
        for c in chars:
            issues = []
            if not c.traits.get("backstory"):
                issues.append("缺前史/背景")
            if not c.traits.get("personality_tags"):
                issues.append("缺性格标签")
            if issues:
                char_issues.append({"name": c.name, "issues": issues})

        missing = []
        if not rules:
            missing.append("世界规则(魔法体系/物理法则/社会制度)")
        if not factions:
            missing.append("势力/组织")
        if not places:
            missing.append("地点/场景")
        if not any(f.secret for f in facts):
            missing.append("私密设定/伏线(角色隐藏底细)")

        return {
            "total_chars": len(chars),
            "total_rules": len(rules),
            "total_factions": len(factions),
            "total_places": len(places),
            "total_facts": len(facts),
            "char_issues": char_issues,
            "missing_dimensions": missing,
            "completeness_score": max(0, 100 - len(missing) * 20 - len(char_issues) * 5),
        }

    def check_ooc(self, character_id: str, dialogue: str) -> list[dict]:
        """OOC 检测:对照 voice_profile.ooc_signals 规则列表扫描对话。
        返回违规列表 [{signal, line, severity}]。"""
        vp = self.get_voice_profile(character_id)
        if not vp or not vp.get("ooc_signals"):
            return []
        violations = []
        for signal in vp["ooc_signals"]:
            if not isinstance(signal, dict):
                continue
            desc = signal.get("description", "")
            severity = signal.get("severity", "medium")
            method = signal.get("detection_method", "rule")
            if method == "rule":
                if "长句" in desc:
                    sentences = [s for s in dialogue.split("。") if s.strip()]
                    long_count = sum(1 for s in sentences if len(s.strip()) > 25)
                    if long_count > 3:
                        violations.append({"signal": desc, "severity": severity,
                                           "line": f"连续{long_count}句长句(>25字)"})
                elif "感叹号" in desc:
                    if dialogue.count("！") > 2:
                        violations.append({"signal": desc, "severity": severity,
                                           "line": f"感叹号{dialogue.count('！')}次"})
                elif "情感词" in desc or "直接说" in desc or "高兴" in desc or "我爱你" in desc:
                    emo_words = ["很高兴", "我爱你", "感谢", "很开心", "太好了"]
                    found = [w for w in emo_words if w in dialogue]
                    if found:
                        violations.append({"signal": desc, "severity": severity,
                                           "line": f"直接情感词: {found}"})
        return violations

    def resolve_entities(self, text: str, chapter: int = 9999) -> list[dict]:
        """解析文本中出现的实体引用,返回相关设定候选。
        四路召回:精确名 → 别名 → hint → 向量语义。"""
        candidates = {}

        # 路1:精确名匹配(角色名/物品名/术语名/地点名)
        for c in self.characters():
            if c.name and c.name in text:
                candidates[c.id] = {"id": c.id, "type": "character", "name": c.name,
                                    "score": 1.0, "reason": "exact_name"}
        for item in self.list_items():
            if item.get("name") and item["name"] in text:
                candidates[f"item:{item['name']}"] = {"id": f"item:{item['name']}",
                    "type": "item", "name": item["name"], "score": 1.0, "reason": "exact_name"}
        for term in self.list_terms():
            if term.get("name") and term["name"] in text:
                candidates[f"term:{term['name']}"] = {"id": f"term:{term['name']}",
                    "type": "term", "name": term["name"], "score": 1.0, "reason": "exact_name"}

        # 路2:别名匹配
        for c in self.characters():
            aliases = c.traits.get("aliases") or []
            for alias in aliases:
                if alias and alias in text:
                    if c.id not in candidates:
                        candidates[c.id] = {"id": c.id, "type": "character",
                            "name": c.name, "score": 0.9, "reason": "alias",
                            "matched_alias": alias}
        for term in self.list_terms():
            for alias in (term.get("aliases") or []):
                if alias and alias in text:
                    key = f"term:{term['name']}"
                    if key not in candidates:
                        candidates[key] = {"id": key, "type": "term",
                            "name": term["name"], "score": 0.9, "reason": "alias",
                            "matched_alias": alias}

        # 路3:向量语义(仅当精确+别名 < 15)
        if len(candidates) < 15:
            try:
                for f in self.semantic_recall(text, k=10):
                    if f.id not in candidates:
                        candidates[f.id] = {"id": f.id, "type": "fact",
                            "name": f.attribute, "score": 0.7, "reason": "embedding"}
            except Exception:
                pass

        return sorted(candidates.values(), key=lambda x: -x["score"])

    def validate_setting(self, chapter: int, prose: str) -> list[dict]:
        """设定校验:比对正文与设定圣经,产出冲突线索。
        覆盖:规则违反/OOC/物品状态矛盾/命名不一致(能力矛盾未实现,归检测器扩展)。"""
        hints = []

        # 1. 物品状态校验:destroyed/lost 的物品不应在正文中被使用
        for item in self.list_items():
            state = item.get("symbolic_state", "active")
            if state in ("lost", "destroyed") and item["name"] in prose:
                hints.append({
                    "type": "item_state_inconsistency", "severity": "high",
                    "entity": item["name"], "description": f"物品「{item['name']}」状态为「{state}」但正文出现使用",
                    "evidence": item["name"]})

        # 2. OOC 校验:对每个有 voice_profile 的角色检测对话
        for c in self.characters():
            vp = self.get_voice_profile(c.id)
            if vp and vp.get("ooc_signals"):
                # 简单提取含角色名的句子作为对话
                sentences = [s.strip() for s in prose.split("。") if c.name in s]
                dialogue = "。".join(sentences)
                if dialogue:
                    ooc_violations = self.check_ooc(c.id, dialogue)
                    for v in ooc_violations:
                        hints.append({
                            "type": "personality_ooc", "severity": v["severity"],
                            "entity": c.name, "description": v["signal"],
                            "evidence": v["line"]})

        # 3. 世界规则校验:检查 limitations 是否被违反
        for rule in self.list_world_rules():
            for lim in (rule.get("limitations") or []):
                # 简单检查:limitation 关键词出现在正文中
                if lim and len(lim) > 4 and lim[:4] in prose:
                    hints.append({
                        "type": "rule_violation", "severity": "medium",
                        "entity": rule["name"], "description": f"可能违反规则「{rule['name']}」限制:{lim}",
                        "evidence": lim})

        # 4. 命名一致性:扫正文中疑似专名(人/地/物),未登记的报 hint
        # P2-a Fix3(选①):原 known_names 构建完未用就 return,属死代码——实装扫描逻辑。
        known_names = set()
        for c in self.characters():
            known_names.add(c.name)
            known_names.update(c.traits.get("aliases") or [])
        for term in self.list_terms():
            known_names.add(term["name"])
            known_names.update(term.get("aliases") or [])
        for it in self.list_items():
            known_names.add(it["name"])
        for pl in self._query("SELECT name FROM place"):
            known_names.add(pl.get("name", ""))
        known_names.discard("")
        try:
            import jieba
            # 切词后取长度>=2 的汉字 token,若与 known_names 的某项高度相似但不完全匹配则报 hint
            # 简单策略:正文中出现的已知名称的前缀/后缀变体(疑似别名)被捕获
            tokens = [w for w in jieba.cut(prose) if len(w) >= 2 and all("一" <= c <= "鿿" for c in w)]
            for tok in set(tokens):
                # 若该 token 不在 known_names,且正文含量>1(排除偶发音),则报 unknown_name hint
                if tok not in known_names and prose.count(tok) >= 2:
                    # 避免过度噪声:只在与任一已知名同首字或同尾字时才报(疑似衍生别名)
                    is_derived = any(
                        (kn[0] == tok[0] or kn[-1] == tok[-1])
                        for kn in known_names if len(kn) >= 2
                    )
                    if is_derived:
                        hints.append({
                            "type": "unknown_name", "severity": "low",
                            "entity": tok,
                            "description": f"「{tok}」出现 {prose.count(tok)} 次但未登记为角色/术语/地点/物品",
                            "evidence": tok})
        except Exception:
            pass  # jieba 不可用时静默跳过,不阻塞校验

        return hints

    def lie_belief_jumps(self, threshold: int = 15) -> list[dict]:
        """弧光跳变(工艺引擎 M3 检测半件,pulse arc 维数据源):同一角色相邻两次
        lie_belief 记录位移>threshold → 顿悟太便宜。纯结构查询,report-only。"""
        rows = self._query(
            "SELECT character_id, chapter, lie_belief FROM char_state "
            "WHERE lie_belief != NONE ORDER BY character_id, chapter")
        out: list[dict] = []
        prev: dict = {}
        for r in rows:
            cid = str(r.get("character_id"))
            lb = r.get("lie_belief")
            if lb is None:
                continue
            p = prev.get(cid)
            ch = r.get("chapter")
            if p is not None and ch == p["chapter"]:
                # 审查 P1-4:同章多记录(重复 ingest 残留)不构成"跳变对",取后值为准
                prev[cid] = {"lie_belief": lb, "chapter": ch}
                continue
            if p is not None and abs(lb - p["lie_belief"]) > threshold:
                out.append({"character_id": cid, "chapter": ch,
                            "cur": lb, "prev": p["lie_belief"],
                            "prev_chapter": p["chapter"],
                            "gap": (ch or 0) - (p["chapter"] or 0)})
            prev[cid] = {"lie_belief": lb, "chapter": ch}
        return out

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
            "CREATE type::record('context_session', $sid) SET work=$work, "
            "actor_id=$actor, device_id=$device, thread_id=$thread, status='active', "
            "revision=0, current_snapshot_id=$snap_id, updated_at=time::now(); "
            "CREATE type::record('context_snapshot', $snap_id) SET session_id=$sid, "
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
            "SELECT work, thread_id FROM type::record('context_session', $sid)",
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
                "FROM type::record('context_session', $sid)); "
                "IF array::len($cur) == 0 { THROW 'context_session_missing' }; "
                # I-2:ended 守卫——已结束的会话拒绝推进(end 方法由后续任务建)
                "IF $cur[0].status != 'active' { THROW 'context_session_ended' }; "
                "IF $cur[0].revision != $expected "
                "{ THROW 'stale_revision:' + <string>$cur[0].revision }; "
                "CREATE type::record('context_snapshot', $snap_id) SET session_id=$sid, "
                "work=$work, revision=$rev, previous_revision=$prev, navigation_id=$nav, "
                "thread_id=$thread, entry=$entry, directory_path=$path, focus=$focus, "
                "detail_route=$route, chapter=$chapter, phase=$phase, "
                "focalizer=$focalizer, reason=$reason, context_hash=$hash; "
                "UPDATE type::record('context_session', $sid) SET revision=$rev, "
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
                        "SELECT revision FROM type::record('context_session', $sid)",
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
            "SELECT current_snapshot_id FROM type::record('context_session', $sid)",
            {"sid": session_id})
        if not sess:
            return None
        snap_id = sess[0].get("current_snapshot_id")
        if snap_id:
            rows = self._query(
                f"SELECT {self._CONTEXT_SNAPSHOT_FIELDS} "
                "FROM type::record('context_snapshot', $snap)",
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
            f"SELECT {self._MEMORY_COLS}, <string> created_at AS created_at "
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

    def count_active_context_sessions(self) -> int:
        """runtime-status 指标(Task 16-B):本库仍活跃的上下文会话数(轻量计数,不载快照)。"""
        rows = self._query(
            "SELECT count() AS n FROM context_session WHERE status='active' GROUP ALL")
        return int(rows[0]["n"]) if rows else 0

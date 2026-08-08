"""SurrealStore mixin: character_arc (split from store/misc.py)."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403


class CharacterArcMixin:
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

        motifs = []
        try:
            if hasattr(self, "list_motifs"):
                motifs = [m for m in (self.list_motifs() or []) if (m.get("name") or "").strip()]
        except Exception:
            motifs = []

        missing = []
        if not rules:
            missing.append("世界规则(魔法体系/物理法则/社会制度)")
        if not factions:
            missing.append("势力/组织")
        if not places:
            missing.append("地点/场景")
        if not any(f.secret for f in facts):
            missing.append("私密设定/伏线(角色隐藏底细)")
        # 开书强制：母题先立档（与 bible_motifs / GATE-A 同源）
        from scribe3.bible_motifs import MIN_BIBLE_MOTIFS
        if len(motifs) < MIN_BIBLE_MOTIFS:
            missing.append(f"母题(已有{len(motifs)}，目标≥{MIN_BIBLE_MOTIFS})")

        return {
            "total_chars": len(chars),
            "total_rules": len(rules),
            "total_factions": len(factions),
            "total_places": len(places),
            "total_facts": len(facts),
            "total_motifs": len(motifs),
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


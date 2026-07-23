"""SurrealStore mixin: codex_ext."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class CodexExtMixin:

    def add_relation_touch(self, a: str, b: str, chapter: int, kind: str, note: str = "") -> None:
        """登记一次关系触碰。a/b 是无序对(登记时不必关心先后)。
        kind 语义由调用方约束(ingest 抽取纪律见 ingest.py),store 层不做枚举校验。"""
        self._execute_write(
            "CREATE relation_touch SET a=$a, b=$b, chapter=$c, kind=$k, note=$n",
            {"a": a, "b": b, "c": chapter, "k": kind, "n": note or None})

    def list_relation_touches(self, a: str | None = None, b: str | None = None) -> list[dict]:
        """列关系触碰记录,按章号升序。a/b 无序对:传单侧或双侧均对称匹配(不论登记时先后)。
        两者都不传则返回全部。"""
        if a is not None and b is not None:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch "
                "WHERE (a=$a AND b=$b) OR (a=$b AND b=$a) ORDER BY chapter ASC",
                {"a": a, "b": b})
        elif a is not None:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch "
                "WHERE a=$a OR b=$a ORDER BY chapter ASC", {"a": a})
        elif b is not None:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch "
                "WHERE a=$b OR b=$b ORDER BY chapter ASC", {"b": b})
        else:
            rows = self._query(
                "SELECT a, b, chapter, kind, note FROM relation_touch ORDER BY chapter ASC")
        return [{"a": r.get("a"), "b": r.get("b"), "chapter": r.get("chapter"),
                 "kind": r.get("kind"), "note": r.get("note") or ""} for r in rows]

    def motif_terms(self) -> set[str]:
        """刻意母题/专名白名单(≥2字):母题名各部分 + 少量物名/地名/书名。
        跨章复读判定时放行——乱世铜炉式母题本应复现,只揪'动作/句式偷懒重打'。"""
        terms: set[str] = set()
        for m in self.list_motifs():
            name = (m.get("name") or "")
            for ch in "()（）":
                name = name.replace(ch, "|")
            for part in name.split("|"):
                p = part.strip()
                if len(p) >= 2:
                    terms.add(p)
        terms.update({"镇煞钉", "灵龙镇煞钉", "奈何谷", "大元炼真经",
                      "清潭派", "云阳真人", "三百六十", "老槐树"})
        return terms

    def _all_relations(self) -> list[dict]:
        """全量读角色关系(不带限知时间门):含已失效(until_chapter 非 NONE)的历史关系。
        供时间线工艺视图使用——需要画 since→until 全史甘特条,不能用 relations_at 的快照门控。
        与 relations_at 的关键区别:relations_at 只返回"某章仍开着"的关系,会漏失效历史;
        本方法 SELECT 全表,无 WHERE 时间过滤。"""
        return self._query(
            "SELECT meta::id(in) AS src, meta::id(out) AS dst, relation, "
            "since_chapter, until_chapter, note FROM character_relation")

    def relations_at(self, chapter: int) -> list[dict]:
        """某章已建立的角色关系(限知时间门:since_chapter <= chapter, until_chapter > chapter or NONE)"""
        return self._query(
            "SELECT meta::id(in) AS src, meta::id(out) AS dst, relation, since_chapter, "
            "until_chapter, note FROM character_relation "
            "WHERE since_chapter <= $ch AND (until_chapter IS NONE OR until_chapter > $ch)",
            {"ch": chapter})

    def evolve_relation(self, src_oid: str, dst_oid: str, new_relation: str,
                        since_chapter: int, note: str | None = None) -> None:
        """关系演变:关闭 src→dst 所有开区间关系,写入新关系。
        敌变友/师徒决裂等弧线均通过此方法表达。"""
        _, sl = _split(src_oid)
        _, dl = _split(dst_oid)
        # 1. 关闭所有仍开着的 src→dst 关系(until_chapter IS NONE)
        self._execute_write(
            "UPDATE character_relation SET until_chapter=$uc "
            "WHERE in=$s AND out=$d AND until_chapter IS NONE",
            {"uc": since_chapter,
             "s": RecordID("character", sl),
             "d": RecordID("character", dl)})
        # 2. 写入新关系
        self.add_character_relation(src_oid, dst_oid, new_relation, since_chapter, note)

    def end_relation(self, src_oid: str, dst_oid: str, until_chapter: int) -> None:
        """终止关系:设置 until_chapter,不新建替代关系。"""
        # R2.1: 验证 src/dst 实体存在
        if self.entity(src_oid) is None:
            raise ValueError(
                f"end_relation: src '{src_oid}' 不存在,无法终止不存在角色的关系。"
            )
        if self.entity(dst_oid) is None:
            raise ValueError(
                f"end_relation: dst '{dst_oid}' 不存在,无法终止不存在角色的关系。"
            )
        _, sl = _split(src_oid)
        _, dl = _split(dst_oid)
        self._execute_write(
            "UPDATE character_relation SET until_chapter=$uc "
            "WHERE in=$s AND out=$d AND until_chapter IS NONE",
            {"uc": until_chapter,
             "s": RecordID("character", sl),
             "d": RecordID("character", dl)})

    def add_world_rule(self, name: str, category: str, source: str | None = None,
                       capabilities: list | None = None, cost: str | None = None,
                       limitations: list | None = None, exceptions: list | None = None,
                       scope: str = "global", established_chapter: int | None = None,
                       note: str | None = None) -> str:
        """添加/覆盖世界规则(同名幂等:先删后建)。返回规则名。"""
        self._execute_write("DELETE world_rule WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE world_rule SET name=$n, category=$cat, source=$src, "
            "capabilities=$caps, cost=$cost, limitations=$lims, exceptions=$excs, "
            "scope=$scp, established_chapter=$ec, note=$note",
            {"n": name, "cat": category, "src": source,
             "caps": capabilities or [], "cost": cost, "lims": limitations or [],
             "excs": exceptions or [], "scp": scope, "ec": established_chapter, "note": note})
        return name

    def list_world_rules(self, category: str | None = None) -> list[dict]:
        """列世界规则(可按类别过滤)。"""
        if category:
            return self._query("SELECT * FROM world_rule WHERE category=$cat", {"cat": category})
        return self._query("SELECT * FROM world_rule")

    def get_world_rule(self, name: str) -> dict | None:
        rows = self._query("SELECT * FROM world_rule WHERE name=$n LIMIT 1", {"n": name}) or []
        return rows[0] if rows else None

    def patch_world_rule(self, name: str, fields: dict) -> bool:
        """局部更新世界规则;不存在返回 False。"""
        if not self.get_world_rule(name):
            return False
        allowed = {k: v for k, v in (fields or {}).items()
                   if k in ("category", "source", "capabilities", "cost", "limitations",
                            "exceptions", "scope", "established_chapter", "note", "name")}
        if not allowed:
            return True
        sets = ", ".join(f"{k}=${k}" for k in allowed)
        self._execute_write(f"UPDATE world_rule SET {sets} WHERE name=$__n",
                            {**allowed, "__n": name})
        return True

    def delete_world_rule(self, name: str) -> None:
        self._execute_write("DELETE world_rule WHERE name=$n", {"n": name})

    def add_item(self, name: str, category: str | None = None,
                 description: str | None = None, current_owner: str | None = None,
                 symbolic_state: str = "active",
                 special_properties: list | None = None,
                 first_chapter: int | None = None,
                 state_history: list | None = None) -> str:
        """添加/覆盖物品(同名幂等:先删后建)。返回物品名。
        state_history:P1-9——DELETE+CREATE 覆盖会清空状态流转史;端点层 PATCH 语义读回旧
        state_history 经此参数透传保留(缺省 None → [] 供全新物品)。"""
        self._execute_write("DELETE item WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE item SET name=$n, category=$cat, description=$desc, "
            "current_owner=$co, symbolic_state=$ss, state_history=$sh, "
            "special_properties=$sp, first_chapter=$fc",
            {"n": name, "cat": category, "desc": description, "co": current_owner,
             "ss": symbolic_state, "sh": state_history or [],
             "sp": special_properties or [], "fc": first_chapter})
        return name

    def list_items(self, state: str | None = None) -> list[dict]:
        if state:
            return self._query("SELECT * FROM item WHERE symbolic_state=$st", {"st": state})
        return self._query("SELECT * FROM item")

    def get_item(self, name: str) -> dict | None:
        rows = self._query("SELECT * FROM item WHERE name=$n LIMIT 1", {"n": name}) or []
        return rows[0] if rows else None

    def patch_item(self, name: str, fields: dict) -> bool:
        if not self.get_item(name):
            return False
        allowed = {k: v for k, v in (fields or {}).items()
                   if k in ("category", "description", "current_owner", "symbolic_state",
                            "special_properties", "first_chapter", "name")}
        if not allowed:
            return True
        sets = ", ".join(f"{k}=${k}" for k in allowed)
        self._execute_write(f"UPDATE item SET {sets} WHERE name=$__n",
                            {**allowed, "__n": name})
        return True

    def update_item_state(self, name: str, new_state: str, chapter: int,
                          note: str = "") -> None:
        """更新物品符号状态(active/lost/destroyed/unknown),追加 state_history。"""
        self._execute_write(
            "UPDATE item SET symbolic_state=$ns, state_history = "
            "array::append(state_history, {state:$ns, chapter:$ch, note:$note}) "
            "WHERE name=$n",
            {"ns": new_state, "ch": chapter, "note": note, "n": name})

    def delete_item(self, name: str) -> None:
        self._execute_write("DELETE item WHERE name=$n", {"n": name})

    def add_term(self, name: str, category: str | None = None,
                 definition: str | None = None, aliases: list | None = None,
                 first_mention_chapter: int | None = None) -> str:
        """添加/覆盖术语(同名幂等:先删后建)。返回术语名。"""
        self._execute_write("DELETE term WHERE name=$n", {"n": name})
        self._execute_write(
            "CREATE term SET name=$n, category=$cat, definition=$def, "
            "aliases=$al, first_mention_chapter=$fmc",
            {"n": name, "cat": category, "def": definition,
             "al": aliases or [], "fmc": first_mention_chapter})
        return name

    def list_terms(self) -> list[dict]:
        return self._query("SELECT * FROM term")

    def get_term(self, name: str) -> dict | None:
        rows = self._query("SELECT * FROM term WHERE name=$n LIMIT 1", {"n": name}) or []
        return rows[0] if rows else None

    def patch_term(self, name: str, fields: dict) -> bool:
        if not self.get_term(name):
            return False
        allowed = {k: v for k, v in (fields or {}).items()
                   if k in ("category", "definition", "aliases", "first_mention_chapter", "name")}
        if not allowed:
            return True
        sets = ", ".join(f"{k}=${k}" for k in allowed)
        self._execute_write(f"UPDATE term SET {sets} WHERE name=$__n",
                            {**allowed, "__n": name})
        return True

    def delete_term(self, name: str) -> None:
        self._execute_write("DELETE term WHERE name=$n", {"n": name})

    def get_motif(self, motif_id: str) -> dict | None:
        mid = (motif_id or "").strip()
        if not mid:
            return None
        rows = self._query(
            "SELECT meta::id(id) AS id, name, theme, echoes, unfolding FROM "
            "type::record('motif',$m) LIMIT 1", {"m": mid}) or []
        if rows:
            return rows[0]
        # 兼容 name 查找
        rows = self._query(
            "SELECT meta::id(id) AS id, name, theme, echoes, unfolding FROM motif "
            "WHERE name=$n LIMIT 1", {"n": mid}) or []
        return rows[0] if rows else None

    def patch_motif(self, motif_id: str, fields: dict) -> bool:
        row = self.get_motif(motif_id)
        if not row:
            return False
        mid = row["id"]
        allowed = {k: v for k, v in (fields or {}).items()
                   if k in ("name", "theme", "echoes", "unfolding")}
        if not allowed:
            return True
        self._update_by("motif", mid, allowed)
        return True

    # ── 设定库发现:搜索 + 健康度 ──

    def codex_search(self, q: str, limit: int = 40) -> list[dict]:
        """跨设定类型子串检索(name/alias/text/attribute)。返回 [{type, id, label, ref, subtitle}]。"""
        needle = (q or "").strip().lower()
        if not needle:
            return []
        lim = max(1, min(int(limit or 40), 100))
        out: list[dict] = []

        def _hit(kind, ref, label, subtitle=""):
            out.append({
                "type": kind, "id": f"{kind}:{ref}", "ref": ref,
                "label": label or str(ref), "subtitle": subtitle or "",
            })

        for e in self.characters():
            local = e.id.split(":", 1)[-1]
            aliases = " ".join((e.traits or {}).get("aliases") or [])
            hay = f"{e.name} {aliases} {local}".lower()
            if needle in hay:
                _hit("character", local, e.name, "角色")
            if len(out) >= lim:
                return out[:lim]
        for f in self.list_factions() or []:
            aliases = " ".join(f.get("aliases") or []) if isinstance(f.get("aliases"), list) else ""
            hay = f"{f.get('name') or ''} {aliases} {f.get('leader') or ''}".lower()
            if needle in hay:
                _hit("faction", f.get("name"), f.get("name"), "势力")
            if len(out) >= lim:
                return out[:lim]
        for it in self.list_items() or []:
            hay = f"{it.get('name') or ''} {it.get('description') or ''}".lower()
            if needle in hay:
                _hit("item", it.get("name"), it.get("name"), "物件")
            if len(out) >= lim:
                return out[:lim]
        for t in self.list_terms() or []:
            aliases = " ".join(t.get("aliases") or []) if isinstance(t.get("aliases"), list) else ""
            hay = f"{t.get('name') or ''} {aliases} {t.get('definition') or ''}".lower()
            if needle in hay:
                _hit("term", t.get("name"), t.get("name"), "术语")
            if len(out) >= lim:
                return out[:lim]
        for w in self.list_world_rules() or []:
            hay = f"{w.get('name') or ''} {w.get('category') or ''} {w.get('note') or ''}".lower()
            if needle in hay:
                _hit("world_rule", w.get("name"), w.get("name"), "世界规则")
            if len(out) >= lim:
                return out[:lim]
        for p in self.list_promises() or []:
            hay = f"{p.get('text') or ''} {p.get('id') or ''}".lower()
            if needle in hay:
                _hit("promise", p.get("id"), (p.get("text") or "")[:40], "伏笔")
            if len(out) >= lim:
                return out[:lim]
        for m in self.list_motifs() or []:
            hay = f"{m.get('name') or ''} {m.get('theme') or ''}".lower()
            if needle in hay:
                _hit("motif", m.get("id"), m.get("name"), "母题")
            if len(out) >= lim:
                return out[:lim]
        try:
            for r in self.list_open_propositions():
                eid = str(r.get("entity_id") or "").split(":")[-1]
                attr = str(r.get("attribute") or "")
                hay = f"{eid} {attr} {r.get('value') or ''}".lower()
                if needle in hay:
                    _hit("proposition", r.get("id"), f"{eid}·{attr}", "命题")
                if len(out) >= lim:
                    return out[:lim]
        except Exception:
            pass
        return out[:lim]

    def codex_health(self) -> dict:
        """设定库健康度:条目计数 + 稀疏档案 + 无关系角色 + 开区间命题。"""
        chars = self.characters()
        sparse = 0
        for e in chars:
            tr = e.traits or {}
            if not (tr.get("appearance") or tr.get("personality_detail") or tr.get("surface_goal")):
                sparse += 1
        isolated = 0
        try:
            rel_rows = self._all_relations() or []
            linked = set()
            for r in rel_rows:
                if r.get("src"):
                    linked.add(str(r["src"]).split(":")[-1] if ":" in str(r["src"]) else str(r["src"]))
                if r.get("dst"):
                    linked.add(str(r["dst"]).split(":")[-1] if ":" in str(r["dst"]) else str(r["dst"]))
            for e in chars:
                local = e.id.split(":", 1)[-1]
                if local not in linked and e.name not in linked:
                    isolated += 1
        except Exception:
            isolated = 0
        props = 0
        try:
            props = len(self.list_open_propositions())
        except Exception:
            props = 0
        return {
            "characters": len(chars),
            "factions": len(self.list_factions() or []),
            "items": len(self.list_items() or []),
            "terms": len(self.list_terms() or []),
            "world_rules": len(self.list_world_rules() or []),
            "promises": len(self.list_promises() or []),
            "motifs": len(self.list_motifs() or []),
            "propositions_open": props,
            "sparse_dossiers": sparse,
            "isolated_characters": isolated,
        }


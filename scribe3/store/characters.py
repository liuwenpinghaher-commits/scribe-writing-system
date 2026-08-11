"""SurrealStore mixin: characters."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class CharactersMixin:

    def add_entity(self, e: Entity) -> Entity:
        _, local = _split(e.id)
        if e.kind == "character":
            self._execute_write(
                "CREATE type::record('character', $local) SET name=$name, aliases=$al, "
                "backstory=$bs, backstory_secret=$bss, personality_tags=$pt, "
                "importance=$importance, appearance=$appearance, "
                "personality_detail=$personality_detail, abilities=$abilities, "
                "weaknesses=$weaknesses, first_appearance=$first_appearance, "
                "surface_goal=$surface_goal, deep_need=$deep_need, "
                "internal_conflict=$internal_conflict, fear=$fear",
                {"local": local, "name": e.name, "al": e.traits.get("aliases", []),
                 "bs": e.traits.get("backstory"),
                 "pt": e.traits.get("personality_tags", []),
                 "bss": e.traits.get("backstory_secret", False),
                 "importance": e.traits.get("importance"),
                 "appearance": e.traits.get("appearance"),
                 "personality_detail": e.traits.get("personality_detail"),
                 "abilities": e.traits.get("abilities", []),
                 "weaknesses": e.traits.get("weaknesses", []),
                 "first_appearance": e.traits.get("first_appearance"),
                 "surface_goal": e.traits.get("surface_goal"),
                 "deep_need": e.traits.get("deep_need"),
                 "internal_conflict": e.traits.get("internal_conflict"),
                 "fear": e.traits.get("fear")})
        elif e.kind == "place":
            self._execute_write("CREATE type::record('place', $local) SET name=$name",
                                {"local": local, "name": e.name})
        # S-2：角色/地点节点写 → 对应表 CDC
        if e.kind == "character":
            _emit_cache_invalidation("character", getattr(self, "db_name", None), store=self)
        return e

    def entity(self, oid: str) -> Entity | None:
        try:
            table, local = _split(oid)        # 迁移数据的 entity 串可能无标准前缀→容忍
        except (KeyError, ValueError):
            return None
        rows = self._query("SELECT name FROM type::record($tbl,$local)",
                           {"tbl": table, "local": local})
        if not rows:
            return None
        return Entity(oid, TBL2KIND.get(table, table), rows[0].get("name", ""))

    def characters(self) -> list[Entity]:
        rows = self._query(
            "SELECT meta::id(id) AS local, name, backstory, backstory_secret, aliases, personality_tags, "
            "importance, appearance, personality_detail, abilities, weaknesses, "
            "first_appearance, surface_goal, deep_need, internal_conflict, fear FROM character "
            "WHERE archived = NONE OR archived != true")
        return [Entity(f"role:{r['local']}", "character", r["name"],
                       traits={"backstory": r.get("backstory"),
                               "backstory_secret": r.get("backstory_secret", False),
                               "aliases": r.get("aliases") or [],
                               "personality_tags": r.get("personality_tags") or [],
                               "importance": r.get("importance"),
                               "appearance": r.get("appearance"),
                               "personality_detail": r.get("personality_detail"),
                               "abilities": r.get("abilities"),
                               "weaknesses": r.get("weaknesses") or [],
                               "first_appearance": r.get("first_appearance"),
                               "surface_goal": r.get("surface_goal"),
                               "deep_need": r.get("deep_need"),
                               "internal_conflict": r.get("internal_conflict"),
                               "fear": r.get("fear")}) for r in rows]

    def _all_char_states_bulk(self) -> list[dict]:
        """批量查全表所有角色弧光记录,一次往返。
        供 timeline() 弧光泳道使用——替代逐角色 list_char_states 循环(N 角色→N 次单查)。
        返回与 list_char_states 字段完全一致,额外保留 character_id 供 Python 侧分组。"""
        return self._query(
            "SELECT meta::id(id) AS id, character_id, chapter, change_type, summary, "
            "before_state, after_state, trigger_event, arc_phase, affects_voice, confidence, "
            "lie_belief "
            "FROM char_state ORDER BY chapter ASC")

    def add_character_relation(self, src_oid: str, dst_oid: str, relation: str,
                               since_chapter: int, note: str | None = None) -> None:
        # R2.1: 验证 src/dst 实体存在,防悬挂边
        if self.entity(src_oid) is None:
            raise ValueError(
                f"add_character_relation: src '{src_oid}' 不存在,拒绝写入悬挂边。请先建立角色实体。"
            )
        if self.entity(dst_oid) is None:
            raise ValueError(
                f"add_character_relation: dst '{dst_oid}' 不存在,拒绝写入悬挂边。请先建立角色实体。"
            )
        _, sl = _split(src_oid)
        _, dl = _split(dst_oid)
        self._execute_write(
            "RELATE $s->character_relation->$d SET relation=$r, since_chapter=$sc, note=$n",
            {"s": RecordID("character", sl), "d": RecordID("character", dl),
             "r": relation, "sc": since_chapter, "n": note})

    def add_entity_relation(self, a: str, b: str, relation_type: str,
                            perception_a: str | None = _UNSET,
                            perception_b: str | None = _UNSET,
                            truth: str | None = _UNSET,
                            truth_secret: bool = _UNSET,
                            since_chapter: int | None = None) -> None:
        """Upsert 通用实体关系。

        自然键 = (a, b, relation_type, since_chapter, 仍开着即 until_chapter IS NONE):
        命中则 MERGE,未命中才 CREATE——与 store.add_faction 的 upsert 思路一致。这是
        app.py `POST /entity-relations` 的掩码哨兵(truth==_SECRET_MASK 时 pop)能够
        真正"不覆盖真值"的前提:若每次都无条件新插一行,旧行虽不会被掩码字符串污染,
        但也没法就地更正 perception_a/perception_b 等字段——那不是真的"防回写毁数据",
        只是"从不修改"。`perception_a`/`perception_b`/`truth`/`truth_secret` 用模块级
        `_UNSET` 哨兵区分"调用方未传"(MERGE 不碰旧值)与"显式传 None/False"(写空/
        取消 secret),与 add_faction 同一思路。`a`/`b`/`relation_type`/`since_chapter`
        是定位关系用的自然键,不支持"部分更新"语义——每次调用都必须显式给出(与
        add_faction 的 `name` 地位相同:它是键,不是可合并字段)。

        relation_type 必须在 `codex_schema.ENTITY_RELATION_TYPES` 词表内,否则
        `ValueError`(app.py 映射 422;migration 085 的 DB 侧 ASSERT 是最后一道防线)。
        """
        if relation_type not in _ENTITY_RELATION_TYPES:
            raise ValueError(
                f"add_entity_relation: relation_type {relation_type!r} 非法"
                f"(合法值: {list(_ENTITY_RELATION_TYPES)})")

        content: dict = {}
        for k, v in (("perception_a", perception_a), ("perception_b", perception_b),
                     ("truth", truth), ("truth_secret", truth_secret)):
            if v is not _UNSET:
                content[k] = v
        content["a"] = a
        content["b"] = b
        content["relation_type"] = relation_type
        content["since_chapter"] = since_chapter

        if since_chapter is None:
            existing = self._query(
                "SELECT id FROM entity_relation WHERE a=$a AND b=$b AND relation_type=$rt "
                "AND until_chapter IS NONE AND since_chapter IS NONE LIMIT 1",
                {"a": a, "b": b, "rt": relation_type})
        else:
            existing = self._query(
                "SELECT id FROM entity_relation WHERE a=$a AND b=$b AND relation_type=$rt "
                "AND until_chapter IS NONE AND since_chapter=$sc LIMIT 1",
                {"a": a, "b": b, "rt": relation_type, "sc": since_chapter})

        if existing:
            self._execute_write("UPDATE $rid MERGE $content",
                                {"rid": existing[0]["id"], "content": content})
        else:
            if truth_secret is _UNSET:
                content["truth_secret"] = True   # 新行安全默认:未标注一律先当作主编独知
            self._execute_write("CREATE entity_relation CONTENT $content", {"content": content})

    def list_entity_relations(self, entity: str | None = None) -> list[dict]:
        """列全部实体关系(不做时态过滤);entity 给定则只看 a 或 b 命中该引用的关系。"""
        if entity:
            return self._query(
                "SELECT * FROM entity_relation WHERE a=$e OR b=$e", {"e": entity})
        return self._query("SELECT * FROM entity_relation")

    def entity_relations_at(self, chapter: int, entity: str | None = None) -> list[dict]:
        """某章仍生效的实体关系(限知时间门,仿 relations_at):
        since_chapter 为空或 <= chapter,且 until_chapter 为空或 > chapter。"""
        where = ("(since_chapter IS NONE OR since_chapter <= $ch) AND "
                 "(until_chapter IS NONE OR until_chapter > $ch)")
        if entity:
            return self._query(
                f"SELECT * FROM entity_relation WHERE ({where}) AND (a=$e OR b=$e)",
                {"ch": chapter, "e": entity})
        return self._query(f"SELECT * FROM entity_relation WHERE {where}", {"ch": chapter})

    def end_entity_relation(self, a: str, b: str, until_chapter: int) -> None:
        """终止关系:设置 until_chapter,不新建替代关系(仿 end_relation)。
        关闭 a→b 方向全部仍开着的关系(不分 relation_type,与 end_relation 对 character
        的语义一致)。"""
        self._execute_write(
            "UPDATE entity_relation SET until_chapter=$uc "
            "WHERE a=$a AND b=$b AND until_chapter IS NONE",
            {"uc": until_chapter, "a": a, "b": b})

    def delete_entity_relation(self, a: str, b: str) -> None:
        """硬删 a→b 方向全部关系(REST DELETE /entity-relations 用;不分 relation_type)。"""
        self._execute_write(
            "DELETE entity_relation WHERE a=$a AND b=$b", {"a": a, "b": b})

    def add_char_state(self, character_id: str, chapter: int, change_type: str,
                       summary: str, before_state: dict | None = None,
                       after_state: dict | None = None, trigger_event: str | None = None,
                       arc_phase: str | None = None, affects_voice: bool | None = None,
                       confidence: str = "confirmed",
                       ingest_seq: int | None = None,
                       lie_belief: int | None = None) -> None:
        """记录角色弧光质变点(能力/关系/性格变化)。
        affects_voice=True 时自动创建 voice_evolution_flag(该更新声音了)。
        ingest_seq:由 ingest 自动回写时传入,供 purge_ingest 幂等清理;手动种的不传。
        lie_belief:该章结束时对核心错误信念的信奉度(0-100,migration 054);
        钳制由调用方负责(ingest 抽取路径入库前 clamp 到 [0,100])。"""
        _, local = _split(character_id)
        self._execute_write(
            "CREATE char_state SET character_id=$cid, chapter=$ch, change_type=$ct, "
            "summary=$sum, before_state=$bs, after_state=$as, trigger_event=$te, "
            "arc_phase=$ap, affects_voice=$av, confidence=$conf, lie_belief=$lb"
            + (", ingest_seq=$iseq" if ingest_seq is not None else ""),
            {"cid": character_id, "ch": chapter, "ct": change_type, "sum": summary,
             "bs": before_state, "as": after_state, "te": trigger_event,
             "ap": arc_phase, "av": affects_voice, "conf": confidence, "lb": lie_belief,
             **({"iseq": ingest_seq} if ingest_seq is not None else {})})
        if affects_voice:
            # 审计 C-2:透传 ingest_seq——ingest 路径产的 flag 随 purge 幂等,手动的保留
            self.add_voice_flag(character_id, chapter, summary, ingest_seq=ingest_seq)

    def char_state_at(self, character_id: str, chapter: int) -> dict:
        """返回角色在某章时刻的完整状态快照(合并所有 CharState 到该章)。"""
        rows = self._query(
            "SELECT * FROM char_state WHERE character_id=$cid AND chapter <= $ch "
            "ORDER BY chapter ASC", {"cid": character_id, "ch": chapter})
        if not rows:
            return {"character_id": character_id, "as_of_chapter": chapter,
                    "abilities": {}, "relations": {}, "personality": "", "arc_phases": []}
        abilities = {}
        relations = {}
        personality = ""
        phases = []
        for r in rows:
            after = r.get("after_state") or {}
            if r["change_type"] in ("ability", "composite"):
                abilities.update(after.get("ability_snapshot") or {})
            if r["change_type"] in ("relation", "composite"):
                relations.update(after.get("relation_snapshot") or {})
            if r["change_type"] in ("personality", "composite"):
                personality = after.get("personality_snapshot") or personality
            if r.get("arc_phase"):
                phases.append({"chapter": r["chapter"], "phase": r["arc_phase"],
                               "summary": r.get("summary", "")})
        return {"character_id": character_id, "as_of_chapter": chapter,
                "abilities": abilities, "relations": relations,
                "personality": personality, "arc_phases": phases}

    def list_char_states(self, character_id: str) -> list[dict]:
        """列角色全部弧光记录(含 before/after/trigger,演进史完整展示)。"""
        return self._query(
            "SELECT meta::id(id) AS id, character_id, chapter, change_type, summary, "
            "before_state, after_state, trigger_event, arc_phase, affects_voice, confidence, "
            "lie_belief "
            "FROM char_state WHERE character_id=$cid ORDER BY chapter ASC",
            {"cid": character_id})

    def set_char_anchors(self, character_id: str, anchors: dict) -> None:
        """写角色弧光锚。局部更新:只写传入的键,未传的字段不动;
        键限 _ANCHOR_KEYS 白名单(SET 片段来自常量元组,注入安全)。"""
        sets, vars_ = [], {}
        for k in _ANCHOR_KEYS:
            if k in anchors:
                sets.append(f"{k}=${k}")
                vars_[k] = anchors[k]
        if not sets:
            return
        _, local = _split(character_id)
        vars_["_l"] = local
        self._execute_write(
            f"UPDATE type::record('character',$_l) SET {', '.join(sets)}", vars_)

    def char_anchors(self, character_id: str) -> dict:
        """读单角色的弧光锚(七键)。角色不存在返回 {}。"""
        _, local = _split(character_id)
        rows = self._query(
            "SELECT ghost, lie, truth, want, need, arc_type, private_agenda "
            "FROM type::record('character',$_l)", {"_l": local})
        return rows[0] if rows else {}

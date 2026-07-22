"""SurrealStore mixin: voice_craft."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class VoiceCraftMixin:

    def add_craft_rule(self, kind: str, pattern: str, note: str = "") -> None:
        self._execute_write(
            "CREATE craft_rule SET kind=$k, pattern=$p, note=$n",
            {"k": kind, "p": pattern, "n": note})

    def list_craft_rules(self) -> list[dict]:
        return self._query("SELECT meta::id(id) AS id, kind, pattern, note FROM craft_rule")

    def delete_craft_rule(self, rid: str) -> None:
        self._execute_write("DELETE type::record('craft_rule',$r)", {"r": rid})

    def seed_craft_rules(self) -> None:
        """首书(乱世铜炉系)种子:scribe2 实战的升华正则8条 + 法器四件套。幂等(已有则跳过)。"""
        if self.list_craft_rules():
            return
        for p in ["天地为炉|万物为铜|在炉里", r"原来.{0,30}(就|早就|从一开始)",
                  r"从.{1,18}那一刻起", r"像.{0,12}[滴颗].{0,8}眼泪", "影子被拉得很长",
                  r"(有些|有的).{0,14}(就再也|再也)", r"他知道[，,].{0,4}(回不去|不一样了)",
                  "走下去|刀山火海"]:
            self.add_craft_rule("purple_regex", p, "乱世铜炉升华句(scribe2实证)")
        self.add_craft_rule(
            "artifact_craft",
            "法器/法术首次出场须四件套:专名+工艺工序+术数+义理(至少齐3项)",
            "范例:灵龙镇煞钉·阳铜黑狗血七七四十九天炼成·三百六十支围太极阵·画井为狱镇魂锁煞")

    def add_voice_flag(self, character: str, seq: int, reason: str,
                       ingest_seq: int | None = None) -> None:
        # seq 是退场方(021 起改名为 trigger_chapter)。只写真源 trigger_chapter。
        # character_id 规范化(批D P1-11 后端跟进):ingest 的 voice_shift 路径传裸名(who),
        # 而 fold_voice_flags/add_char_state 一律用 role: 前缀 id 匹配 → 裸名 flag 永不被 fold
        # (主书历史裸名 flag 致前端 fold 空操作)。此处统一在写入层补 role: 前缀,幂等:
        # 已带前缀(add_char_state 传 role:xxx / ingest arc 经 _resolve_char)不二次加前缀。
        cid = character if ":" in character else f"role:{character}"
        self._execute_write(
            "CREATE voice_evolution_flag SET character=$c, "
            "trigger_chapter=$s, reason=$r, status='open'"
            + (", ingest_seq=$i" if ingest_seq is not None else ""),
            {"c": cid, "s": seq, "r": reason,
             **({"i": ingest_seq} if ingest_seq is not None else {})})

    def list_voice_flags(self, status: str = "open") -> list[dict]:
        return self._query(
            "SELECT meta::id(id) AS id, character, trigger_chapter, reason, status "
            "FROM voice_evolution_flag WHERE status=$st", {"st": status})

    def resolve_voice_flag(self, flag_id: str) -> bool:
        """关闭声音演变 flag:将 status 从 'open' 改为 'done'。返回 True 若存在,False 若不存在。"""
        rows = self._query(
            "SELECT id FROM type::record('voice_evolution_flag',$fid) LIMIT 1", {"fid": flag_id})
        if not rows:
            return False
        self._execute_write(
            "UPDATE type::record('voice_evolution_flag',$fid) SET status='done'",
            {"fid": flag_id})
        return True

    def fold_voice_flags(self, character_id: str, complete_fn) -> dict:
        """半自动声音演变消化:将该角色的开放 voice_evolution_flag 折叠进 voice_profile。

        1. 取该角色 open flags;若无则直接返回 {"folded": 0}。
        2. 取当前 voice_profile(可为 None)。
        3. 构建 prompt → 调 complete_fn → 解析 JSON。
           解析失败(坏 JSON / 缺 style_summary) → fail-soft:不改 profile,返回 {"folded": 0, "degraded": True}。
        4. 成功:set_voice_profile + resolve_voice_flag(每条 flag)。
        5. 返回 {"folded": n, "profile": updated_profile}。

        complete_fn 签名: (prompt: str) -> str(与 ingest_chapter 同签名)。
        """
        from scribe3.critique import build_voice_fold_prompt, parse_voice_profile_from_fold

        # 1. 取该角色 open flags
        all_open = self.list_voice_flags("open")
        char_flags = [f for f in all_open if f.get("character") == character_id]
        if not char_flags:
            return {"folded": 0}

        # 2. 取当前 voice_profile(保留原样用于 fail-soft 回退)
        current_profile = self.get_voice_profile(character_id)

        # 3. 构建 prompt + 调用 LLM + 解析
        try:
            prompt = build_voice_fold_prompt(current_profile, char_flags)
            reply = complete_fn(prompt)
            updated = parse_voice_profile_from_fold(reply)
        except Exception as e:
            logging.getLogger("scribe3.store").warning(
                "fold_voice_flags: complete_fn 或 prompt 失败(soft) character=%s: %s",
                character_id, e)
            return {"folded": 0, "degraded": True}

        if updated is None:
            # 解析失败:fail-soft,不改现有 profile
            return {"folded": 0, "degraded": True}

        # 4. 成功:先更新 profile,再 resolve 每条 flag
        # 若当前 profile 存在,合并现有字段(新值覆盖旧值)
        if current_profile:
            merged = dict(current_profile)
            merged.update(updated)
        else:
            merged = updated

        self.set_voice_profile(character_id, merged)

        for f in char_flags:
            flag_id = f.get("id")
            if flag_id:
                try:
                    self.resolve_voice_flag(flag_id)
                except Exception as e:
                    logging.getLogger("scribe3.store").warning(
                        "fold_voice_flags: resolve_voice_flag(%s) 失败(soft): %s", flag_id, e)

        return {"folded": len(char_flags), "profile": merged}

    def set_voice_profile(self, character_id: str, profile: dict) -> None:
        """设置角色声音指纹(9节结构:style_summary/catchphrases/sentence_patterns/
        vocabulary_profile/tone_rules/internal_monologue_style/ooc_signals/
        reference_lines/version)。"""
        _, local = _split(character_id)
        self._execute_write(
            "UPSERT type::record('voice_profile', $local) SET character_id=$cid, "
            "style_summary=$ss, catchphrases=$cp, sentence_patterns=$sp, "
            "vocabulary_profile=$vp, tone_rules=$tr, internal_monologue_style=$im, "
            "ooc_signals=$os, reference_lines=$rl, version=$v",
            {"local": local, "cid": character_id,
             "ss": profile.get("style_summary"), "cp": profile.get("catchphrases"),
             "sp": profile.get("sentence_patterns"), "vp": profile.get("vocabulary_profile"),
             "tr": profile.get("tone_rules"), "im": profile.get("internal_monologue_style"),
             "os": profile.get("ooc_signals"), "rl": profile.get("reference_lines"),
             "v": profile.get("version", 1)})

    def get_voice_profile(self, character_id: str) -> dict | None:
        """获取角色声音指纹(9节)。

        兜底(Caveat 2):focalizer 可能传【裸名】(如"焦三"而非 role:焦三)。_split 对
        无冒号入参会抛 ValueError → 旧组装链 _voice_anchor_block(app.py)由此触发 500。
        voice_profile 的 local id 恒由 set_voice_profile 经 _split 从规范 record id 派生,
        裸名永远存不进库,故裸名一律安全兜底为"无 profile"返回 None(让上层优雅跳过),
        绝不抛 ValueError。带冒号的规范 record id 走原路,行为一字不变。"""
        if ":" not in (character_id or ""):
            return None
        _, local = _split(character_id)
        rows = self._query(
            "SELECT * FROM type::record('voice_profile', $local)", {"local": local})
        return rows[0] if rows else None

    def list_voice_profiles(self) -> list[dict]:
        """列出所有角色声音指纹的紧凑视图(用于 prompt 注入)。
        返回 [{character_id, style_summary, catchphrases, tone_rules}]。"""
        rows = self._query(
            "SELECT character_id, style_summary, catchphrases, tone_rules FROM voice_profile")
        return rows if rows else []

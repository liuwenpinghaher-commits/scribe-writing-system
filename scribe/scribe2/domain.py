from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from .store import Store


def _cjk(s: str) -> int:
    return sum(1 for ch in (s or "") if "一" <= ch <= "鿿")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_SLOP = ["嘴角勾起", "一抹弧度", "眼底闪过", "一丝", "暖流涌上心头", "命运的齿轮",
         "空气仿佛凝固", "千言万语", "般的存在", "值得一提的是", "不禁", "缓缓地",
         "微微一笑", "深邃的眼眸", "嘴角扬起"]


def _slop_density(text: str) -> float:
    """简易 AI 腔密度:禁用套话命中次数 / 每千字。"""
    if not text:
        return 0.0
    hits = sum(text.count(p) for p in _SLOP)
    return round(hits / max(1, _cjk(text)) * 1000, 3)


class Domain:
    """领域 repo:Store 之上的小说语义。结构实体走 store.create;内容实体走 put_content(自动嵌入)。"""

    def __init__(self, store: Store):
        self.s = store

    # ---- work ----
    def create_work(self, title: str, genre: str = "", owner: str = "u1") -> str:
        return self.s.create("work", {"title": title, "genre": genre, "owner": owner})

    def get_work(self, wid: str) -> dict | None:
        return self.s.get("work", wid)

    def list_works(self, owner: str = "u1") -> list[dict]:
        return self.s.list("work", "owner = $o", {"o": owner})

    # ---- volume / chapter ----
    def create_volume(self, work: str, seq: int, title: str = "") -> str:
        return self.s.create("volume", {"work": self._wref(work), "seq": seq, "title": title})

    def add_chapter(self, work: str, seq: int, title: str = "", volume: str | None = None) -> str:
        return self.s.create("chapter", {
            "work": self._wref(work), "seq": seq, "title": title,
            "volume": (f"volume:{volume}" if volume else None), "status": "draft"})

    def list_chapters(self, work: str) -> list[dict]:
        rows = self.s.list("chapter", "work = $w ORDER BY seq ASC", {"w": self._wref(work)})
        for c in rows:
            c["volume_id"] = c.get("volume")  # 前端契约别名
        return rows

    # ---- snapshot 版本树 ----
    def save_prose(self, work: str, chapter: str, content: str, locked: bool = False,
                   created_by: str = "human", branch_label: str = "human-final") -> str:
        existing = self.s.list("snapshot", "chapter = $c", {"c": f"chapter:{chapter}"})
        ver = len(existing) + 1
        sid = self.s.create("snapshot", {
            "work": self._wref(work), "chapter": f"chapter:{chapter}",
            "version": ver, "content": content, "locked": bool(locked),
            "is_human_locked": 1 if locked else 0,
            "created_by": created_by, "branch_label": branch_label})
        # 字数随定稿(human-final)走,落到章上供作品库汇总
        if branch_label == "human-final":
            self.s.update("chapter", chapter, {"word_count": _cjk(content)})
        return sid

    def list_snapshots(self, chapter: str) -> list[dict]:
        return self.s.list("snapshot", "chapter = $c ORDER BY version ASC",
                           {"c": f"chapter:{chapter}"})

    def _final_snaps(self, chapter: str) -> list[dict]:
        return [s for s in self.list_snapshots(chapter)
                if s.get("branch_label", "human-final") == "human-final"]

    def latest_prose(self, chapter: str) -> str:
        snaps = self._final_snaps(chapter)
        return snaps[-1]["content"] if snaps else ""

    def get_chapter(self, work: str, seq: int) -> dict | None:
        ch = next((c for c in self.list_chapters(work) if c.get("seq") == seq), None)
        if not ch:
            return None
        cid = self._idpart(ch["id"])
        ch = dict(ch)
        ch["snapshots"] = self.list_snapshots(cid)
        ch["chapter_id"] = cid
        return ch

    def set_chapter_status(self, work: str, seq: int, status: str) -> None:
        ch = next((c for c in self.list_chapters(work) if c.get("seq") == seq), None)
        if ch:
            self.s.update("chapter", self._idpart(ch["id"]), {"status": status})

    def move_chapter(self, work: str, seq: int, direction: str) -> bool:
        chs = self.list_chapters(work)
        i = next((k for k, c in enumerate(chs) if c.get("seq") == seq), None)
        if i is None:
            return False
        j = i - 1 if direction == "up" else i + 1
        if j < 0 or j >= len(chs):
            return False
        a, b = chs[i], chs[j]
        sa, sb = a.get("seq"), b.get("seq")
        self.s.update("chapter", self._idpart(a["id"]), {"seq": sb})
        self.s.update("chapter", self._idpart(b["id"]), {"seq": sa})
        return True

    # ---- 段落(正文按段存 + 回填引用了哪些设定/角色)----
    def save_segments(self, work: str, chapter: str, content: str,
                      created_by: str = "human") -> int:
        self.s.db.query("DELETE FROM segment WHERE chapter = $c;", {"c": f"chapter:{chapter}"})
        names = [c.get("name") for c in self.list_characters(work) if c.get("name")] + \
                [s.get("name") for s in self.list_settings(work) if s.get("name")]
        char_names = {c.get("name") for c in self.list_characters(work)}
        paras = [p.strip() for p in re.split(r"\n\s*\n", content or "") if p.strip()]
        for i, p in enumerate(paras):
            refs = [{"name": n, "kind": ("character" if n in char_names else "setting")}
                    for n in names if n and n in p]
            self.s.create("segment", {
                "work": self._wref(work), "chapter": f"chapter:{chapter}", "seq": i,
                "text": p, "created_by": created_by,
                "citation_refs": json.dumps(refs, ensure_ascii=False)})
        return len(paras)

    def list_segments(self, chapter: str) -> list[dict]:
        return self.s.list("segment", "chapter = $c ORDER BY seq ASC",
                           {"c": f"chapter:{chapter}"})

    # ---- 分支(branch_label 聚合,最新一版)----
    def list_branches(self, chapter: str) -> list[dict]:
        by_label: dict[str, dict] = {}
        for s in self.list_snapshots(chapter):
            by_label[s.get("branch_label", "human-final")] = s
        return [{"label": k, "content": v.get("content", ""),
                 "created_by": v.get("created_by", ""), "locked": v.get("locked", False)}
                for k, v in by_label.items()]

    def create_branch(self, work: str, chapter: str, label: str, content: str) -> str:
        return self.save_prose(work, chapter, content, created_by="branch", branch_label=label)

    def merge_branch(self, work: str, chapter: str, label: str) -> bool:
        snaps = [s for s in self.list_snapshots(chapter) if s.get("branch_label") == label]
        if not snaps:
            return False
        self.save_prose(work, chapter, snaps[-1]["content"], branch_label="human-final")
        return True

    # ---- 反馈(作者意见,LoRA 训练信号)----
    def save_feedback(self, work: str, seq: int, nl_critique: str) -> str:
        return self.s.create("feedback", {"work": self._wref(work), "seq": seq,
                                          "nl_critique": nl_critique})

    # ---- 作品库汇总(章数/字数/待看札记/待决方案)----
    def work_summaries(self, owner: str = "u1") -> list[dict]:
        out = []
        for w in self.list_works(owner):
            wid = self._idpart(w["id"])
            chs = self.list_chapters(wid)
            ins = self.s.list("insight", "work = $w AND status = 'new'", {"w": f"work:{wid}"})
            opts = self.s.list("option_set", "work = $w AND chosen = NONE", {"w": f"work:{wid}"})
            out.append({**w, "id": wid,
                        "chapter_count": len(chs),
                        "word_count": sum(c.get("word_count") or 0 for c in chs),
                        "new_insight_count": len(ins),
                        "pending_optionset_count": len(opts)})
        return out

    # ---- 内容实体:设定(契约:name/type/content;存 stype 避开 SurrealDB 关键字 type)
    # Codex 2.0:fields 为按类型的结构化自定义字段(力量体系 cost/limitations/会出什么乱子 等)----
    def add_setting(self, work: str, name: str, desc: str = "", type_: str = "设定",
                    fields: dict | None = None) -> str:
        fields = dict(fields or {})
        # 结构化字段值并进 text,供检索召回(尤其力量体系的 cost/limitations)
        extra = "；".join(str(v) for v in fields.values() if v)
        text = "；".join(x for x in [f"{name}:{desc}" if desc else name, extra] if x)
        return self.s.put_content("setting", work=self._wref(work), text=text,
                                  name=name, stype=type_, content=desc,
                                  fields=json.dumps(fields, ensure_ascii=False))

    def list_settings(self, work: str) -> list[dict]:
        rows = self.s.list("setting", "work = $w", {"w": self._wref(work)})
        for s in rows:
            s["type"] = s.get("stype", "设定")  # 前端契约别名
            try:
                s["fields"] = json.loads(s.get("fields") or "{}")
            except Exception:
                s["fields"] = {}
        return rows

    def search(self, work: str, query: str, k: int = 6) -> list[dict]:
        return self.s.search_knowledge(self._wref(work), query, k=k)

    # ==== 写作层移植:生成上下文实体 ====
    @staticmethod
    def _idpart(rid) -> str:
        """SurrealDB RecordID/字符串 → 纯 id hex(供 store.update)。"""
        if hasattr(rid, "id"):
            return str(rid.id)
        s = str(rid)
        return s.split(":", 1)[1].strip("⟨⟩`") if ":" in s else s

    @staticmethod
    def _wref(work) -> str:
        """裸 hex / 'work:hex' / RecordID → 统一 'work:hex'(写引用与 WHERE 查询用)。
        让所有方法同时接受 create_work 返回的裸 hex 与 list_works/get_work 返回的 'work:hex',
        避免双前缀('work:work:hex')导致主编 agentic 工具链查空。"""
        return f"work:{Domain._idpart(work)}"

    # ---- 北极星(每书一条,upsert) ----
    def set_intent(self, work: str, reader_feeling: str = "", core_emotional_arc: str = "",
                   why_write: str = "", central_promise: str = "",
                   red_lines: list | None = None) -> None:
        data = {"work": self._wref(work), "reader_feeling": reader_feeling,
                "core_emotional_arc": core_emotional_arc, "why_write": why_write,
                "central_promise": central_promise, "red_lines": red_lines or []}
        existing = self.s.list("author_intent", "work = $w", {"w": self._wref(work)})
        if existing:
            self.s.update("author_intent", self._idpart(existing[0]["id"]), data)
        else:
            self.s.create("author_intent", data)

    def get_intent(self, work: str) -> dict | None:
        rows = self.s.list("author_intent", "work = $w", {"w": self._wref(work)})
        if not rows:
            return None
        it = rows[0]
        it["do_not_betray"] = it.get("red_lines") or []  # 前端契约别名
        return it

    # ---- 角色(Codex 2.0:内核 wound/lie/want/need + 核心矛盾 + 声音样本 + 弧光)----
    _CHAR_DEFAULTS = {"voice_samples": list, "core_contradiction": str, "wound": str,
                      "lie": str, "want": str, "need": str, "arc": str, "fear": str,
                      "aliases": list, "pinned": bool}

    def add_character(self, work: str, name: str, motivation: str = "", voice: str = "", *,
                      voice_samples: list | None = None, core_contradiction: str = "",
                      wound: str = "", lie: str = "", want: str = "", need: str = "",
                      arc: str = "", fear: str = "", aliases: list | None = None) -> str:
        vs = list(voice_samples or [])
        al = list(aliases or [])
        # 声音样本/核心矛盾/创伤/别名一并进 text,供 FTS+向量检索召回(别名也能搜到)
        text = "；".join(x for x in [name, *al, motivation, voice, core_contradiction, wound, *vs] if x)
        return self.s.put_content(
            "character", work=self._wref(work), text=text,
            name=name, motivation=motivation, voice=voice,
            voice_samples=vs, core_contradiction=core_contradiction, wound=wound,
            lie=lie, want=want, need=need, arc=arc, fear=fear, aliases=al)

    def list_characters(self, work: str) -> list[dict]:
        rows = self.s.list("character", "work = $w", {"w": self._wref(work)})
        for c in rows:  # 旧记录缺字段时补默认,保证前端/注入契约稳定
            for k, typ in self._CHAR_DEFAULTS.items():
                if k not in c or c[k] is None:
                    c[k] = typ()
        return rows

    def relevant_characters(self, work: str, seq: int, *, recent: int = 3, limit: int = 12) -> list[dict]:
        """本章相关角色(相关性注入,替掉"全塞前15个"):
        信号 = 开着的伏笔所关联的角色 ∪ 近 recent 章梗概里点名的角色;
        人少(≤6)或无任何信号(早期)→ 全给。聚焦在场人物,省上下文、提质量。"""
        chars = self.list_characters(work)
        if len(chars) <= 6:
            return chars
        names = {c.get("name"): c for c in chars if c.get("name")}
        picked: dict = {}
        for f in self.list_foreshadows_status(work):   # 开着的伏笔关联的角色,本章要照顾
            if f.get("state") in ("planted", "triggered"):
                for nm in (f.get("links") or []):
                    if nm in names:
                        picked[nm] = names[nm]
        mems = self.list_chapter_memories(work, upto=seq - 1)[-recent:]   # 近章梗概点名(含别名)
        blob = " ".join((m.get("text") or "") for m in mems)
        for nm, c in names.items():
            hits = [nm] + list(c.get("aliases") or [])
            if any(h and h in blob for h in hits):
                picked[nm] = c
        for nm, c in names.items():        # 钉住(pin)的总在场
            if c.get("pinned"):
                picked[nm] = c
        if not picked:
            return chars[:limit]
        return list(picked.values())[:limit]

    def set_character_pin(self, work: str, name: str, pinned: bool) -> None:
        """钉住/取消钉住角色(钉住=写作时总注入,手动控制相关性)。"""
        c = next((c for c in self.list_characters(work) if c.get("name") == name), None)
        if c:
            self.s.update("character", self._idpart(c["id"]), {"pinned": bool(pinned)})

    def upsert_character(self, work: str, name: str, motivation: str = "", voice: str = "", *,
                         voice_samples: list | None = None, core_contradiction: str = "",
                         wound: str = "", lie: str = "", want: str = "", need: str = "",
                         arc: str = "", fear: str = "", aliases: list | None = None) -> str:
        """按名 upsert(对话式'改'的基础):同名则合并更新(空串不覆盖、voice_samples 非 None 才覆盖),
        否则新建。实现=删旧+并入新字段重建(自动重嵌入)。"""
        existing = next((c for c in self.list_characters(work) if c.get("name") == name), None)
        base = {k: (existing.get(k) if existing else "") for k in
                ("motivation", "voice", "core_contradiction", "wound", "lie", "want", "need", "arc", "fear")}
        for k, v in dict(motivation=motivation, voice=voice, core_contradiction=core_contradiction,
                         wound=wound, lie=lie, want=want, need=need, arc=arc, fear=fear).items():
            if v:  # 非空才覆盖,保留既有
                base[k] = v
        vs = list(voice_samples) if voice_samples is not None else ((existing or {}).get("voice_samples") or [])
        al = list(aliases) if aliases is not None else ((existing or {}).get("aliases") or [])
        if existing:
            self.s.delete("character", self._idpart(existing["id"]))
        return self.add_character(work, name, base["motivation"], base["voice"], voice_samples=vs, aliases=al,
                                  core_contradiction=base["core_contradiction"], wound=base["wound"],
                                  lie=base["lie"], want=base["want"], need=base["need"],
                                  arc=base["arc"], fear=base["fear"])

    # ---- 母题 Motif(核心意象的隐喻网:世界观+主题+命名+物质回声 四位一体)----
    def add_motif(self, work: str, name: str, metaphor_unfolding: str = "",
                  bound_theme: str = "", material_echoes: list | None = None,
                  naming_logic: str = "") -> str:
        echoes = list(material_echoes or [])
        text = "；".join(x for x in [name, metaphor_unfolding, bound_theme, *echoes] if x)
        return self.s.put_content(
            "motif", work=self._wref(work), text=text, name=name,
            metaphor_unfolding=metaphor_unfolding, bound_theme=bound_theme,
            material_echoes=echoes, naming_logic=naming_logic)

    def list_motifs(self, work: str) -> list[dict]:
        rows = self.s.list("motif", "work = $w", {"w": self._wref(work)})
        for m in rows:
            if not isinstance(m.get("material_echoes"), list):
                m["material_echoes"] = []
            for k in ("metaphor_unfolding", "bound_theme", "naming_logic"):
                m.setdefault(k, "")
        return rows

    # ---- 伏笔 ----
    def plant_foreshadow(self, work: str, summary: str, chapter: int,
                         importance: str = "normal", *, promise: str = "", ftype: str = "伏笔",
                         intended_effect: str = "", audience_knows: bool = False,
                         payoff_effect: str = "", links: list | None = None) -> str:
        """埋设承诺线。promise=对读者的承诺(灵魂);ftype=类型;intended_effect=想要的读者效果
        (惊讶/悬念/戏剧反讽/不祥/好奇);audience_knows=读者是否提前知道(真=戏剧反讽式悬念);
        payoff_effect=回收要达到的效果;links=关联实体(角色/设定,把伏笔焊到人/物上)。"""
        return self.s.put_content("foreshadow", work=self._wref(work), text=summary,
                                  summary=summary, chapter=chapter,
                                  importance=importance, state="planted",
                                  promise=promise, ftype=ftype,
                                  intended_effect=intended_effect, audience_knows=bool(audience_knows),
                                  payoff_effect=payoff_effect, links=list(links or []))

    def list_open_foreshadows(self, work: str) -> list[dict]:
        return self.s.list("foreshadow",
                           "work = $w AND state IN ['planted', 'triggered']",
                           {"w": self._wref(work)})

    def advance_foreshadow(self, fid: str, to_state: str) -> None:
        self.s.update("foreshadow", fid, {"state": to_state})

    def set_foreshadow_payoff(self, work: str, fid: str, chapter: int) -> None:
        """回收承诺:标记 paid + 记录回收章(承诺线 payoff 节点,供时间线渲染跨度)。"""
        self.s.update("foreshadow", fid, {"state": "paid", "payoff_chapter": chapter})

    def update_foreshadow(self, work: str, fid: str, *, summary: str | None = None,
                          promise: str | None = None, ftype: str | None = None,
                          importance: str | None = None, intended_effect: str | None = None,
                          audience_knows: bool | None = None, payoff_effect: str | None = None,
                          links: list | None = None) -> None:
        """编辑承诺线明细。空串/None 不覆盖(保留原值);links 非 None 才覆盖。"""
        patch: dict = {}
        if summary: patch["summary"] = summary; patch["text"] = summary
        if promise: patch["promise"] = promise
        if ftype: patch["ftype"] = ftype
        if importance: patch["importance"] = importance
        if intended_effect: patch["intended_effect"] = intended_effect
        if audience_knows is not None: patch["audience_knows"] = bool(audience_knows)
        if payoff_effect: patch["payoff_effect"] = payoff_effect
        if links is not None: patch["links"] = list(links)
        if patch:
            self.s.update("foreshadow", fid, patch)

    def add_foreshadow_echo(self, work: str, fid: str, chapter: int) -> list[int]:
        """伏笔中途强化(echo):深伏笔不能只埋一次,记下偶尔提一嘴的章。"""
        cur = self.s.get("foreshadow", fid)
        echoes = sorted(set(list((cur or {}).get("echoes") or []) + [chapter]))
        self.s.update("foreshadow", fid, {"echoes": echoes})
        return echoes

    def add_foreshadow_beat(self, work: str, fid: str, chapter: int, kind: str = "reinforce", *,
                            guidance: str = "", subtlety: int = 0, effect: str = "", anchor: str = "") -> list[dict]:
        """加一个承诺线节点(plant/reinforce/misdirect/twist/payoff)。
        每节点带 guidance(此处具体怎么写)+ subtlety(隐蔽度1-5)+ effect(想要的局部效果)+ anchor(正文锚点)。
        同步骨架:reinforce→echoes,payoff→payoff_chapter+state=paid(时间线/状态沿用骨架)。"""
        cur = self.s.get("foreshadow", fid) or {}
        beats = list(cur.get("beats") or [])
        beats.append({"chapter": chapter, "kind": kind, "guidance": guidance,
                      "subtlety": subtlety, "effect": effect, "anchor": anchor, "done": False})
        patch: dict = {"beats": beats}
        if kind == "reinforce":
            patch["echoes"] = sorted(set(list(cur.get("echoes") or []) + [chapter]))
        elif kind == "payoff":
            patch["payoff_chapter"] = chapter
            patch["state"] = "paid"
        self.s.update("foreshadow", fid, patch)
        return beats

    def list_foreshadows_status(self, work: str, overdue_span: int = 15) -> list[dict]:
        """全部伏笔 + echoes + 超期告警(planted/triggered 且跨度>阈值未回收=overdue)。"""
        rows = self.s.list("foreshadow", "work = $w", {"w": self._wref(work)})
        maxc = max((c.get("seq") or 0 for c in self.list_chapters(work)), default=0)
        for f in rows:
            f["echoes"] = list(f.get("echoes") or [])
            f["promise"] = f.get("promise") or ""
            f["ftype"] = f.get("ftype") or "伏笔"
            f["payoff_chapter"] = f.get("payoff_chapter")
            f["intended_effect"] = f.get("intended_effect") or ""
            f["audience_knows"] = bool(f.get("audience_knows"))
            f["payoff_effect"] = f.get("payoff_effect") or ""
            f["links"] = list(f.get("links") or [])
            f["beats"] = list(f.get("beats") or [])
            planted = f.get("chapter") or 0
            f["overdue"] = bool(f.get("state") in ("planted", "triggered")
                                and maxc - planted > overdue_span)
        return rows

    # ---- 记忆:章梗概(可检索)+ 全局主线(scope 区分) ----
    def save_chapter_memory(self, work: str, seq: int, summary: str) -> str:
        scope = f"chapter:{seq}"
        existing = self.s.list("memory_entry", "work = $w AND scope = $s",
                               {"w": self._wref(work), "s": scope})
        if existing:
            rid = self._idpart(existing[0]["id"])
            self.s.update("memory_entry", rid, {"text": summary, "seq": seq})
            return rid
        return self.s.put_content("memory_entry", work=self._wref(work), text=summary,
                                  scope=scope, seq=seq)

    def list_chapter_memories(self, work: str, upto: int | None = None) -> list[dict]:
        rows = [r for r in self.s.list("memory_entry", "work = $w", {"w": self._wref(work)})
                if r.get("seq") is not None]
        if upto is not None:
            rows = [r for r in rows if r["seq"] <= upto]
        return sorted(rows, key=lambda r: r["seq"])

    def set_global_memory(self, work: str, text: str) -> None:
        existing = self.s.list("memory_entry", "work = $w AND scope = 'global'",
                               {"w": self._wref(work)})
        if existing:
            self.s.update("memory_entry", self._idpart(existing[0]["id"]), {"text": text})
        else:
            self.s.put_content("memory_entry", work=self._wref(work), text=text, scope="global")

    def get_global_memory(self, work: str) -> str:
        rows = self.s.list("memory_entry", "work = $w AND scope = 'global'",
                           {"w": self._wref(work)})
        return rows[0]["text"] if rows else ""

    # ---- 一致性 flag ----
    def list_consistency_flags(self, work: str, status: str = "open") -> list[dict]:
        return self.s.list("consistency_flag", "work = $w AND status = $s",
                           {"w": self._wref(work), "s": status})

    def add_consistency_flag(self, work: str, seq: int, detail: str,
                             error_class: str = "", severity: str = "warning") -> str:
        return self.s.create("consistency_flag", {
            "work": self._wref(work), "seq": seq, "detail": detail,
            "error_class": error_class, "severity": severity, "status": "open"})

    def resolve_consistency_flag(self, fid: str, status: str = "fixed") -> None:
        self.s.update("consistency_flag", fid, {"status": status})

    # ==== WaveB:编辑功能 CRUD ====
    # ---- 札记 insight ----
    def add_insight(self, work: str, summary: str, suggested_action: str = "",
                    severity: str = "info") -> str:
        return self.s.create("insight", {"work": self._wref(work), "summary": summary,
                             "suggested_action": suggested_action, "severity": severity,
                             "status": "new", "created_at": _now()})

    def list_insights(self, work: str, status: str = "new") -> list[dict]:
        return self.s.list("insight", "work = $w AND status = $s",
                           {"w": self._wref(work), "s": status})

    def act_insight(self, iid: str, act: str) -> None:
        self.s.update("insight", iid, {"status": "acked" if act == "ack" else "dismissed"})

    # ---- 划词交互:批注 annotation / 高亮 highlight(锚在选中文字 quote)----
    def add_annotation(self, work: str, seq: int, quote: str, note: str = "",
                       target: str = "self") -> str:
        return self.s.create("annotation", {"work": self._wref(work), "seq": seq,
                             "quote": quote, "note": note, "target": target,
                             "created_at": _now()})

    def list_annotations(self, work: str, seq: int | None = None) -> list[dict]:
        if seq is None:
            return self.s.list("annotation", "work = $w ORDER BY created_at ASC",
                               {"w": self._wref(work)})
        return self.s.list("annotation", "work = $w AND seq = $s ORDER BY created_at ASC",
                           {"w": self._wref(work), "s": seq})

    def delete_annotation(self, aid: str) -> None:
        self.s.delete("annotation", aid)

    def add_highlight(self, work: str, seq: int, quote: str, color: str = "amber") -> str:
        return self.s.create("highlight", {"work": self._wref(work), "seq": seq,
                             "quote": quote, "color": color, "created_at": _now()})

    def list_highlights(self, work: str, seq: int) -> list[dict]:
        return self.s.list("highlight", "work = $w AND seq = $s ORDER BY created_at ASC",
                           {"w": self._wref(work), "s": seq})

    def delete_highlight(self, hid: str) -> None:
        self.s.delete("highlight", hid)

    # ---- 方案 option_set ----
    def add_option_set(self, work: str, decision_point, options) -> str:
        return self.s.create("option_set", {"work": self._wref(work),
                             "decision_point": json.dumps(decision_point, ensure_ascii=False)
                             if not isinstance(decision_point, str) else decision_point,
                             "options": json.dumps(options, ensure_ascii=False)
                             if not isinstance(options, str) else options,
                             "chosen": None, "created_at": _now()})

    def list_option_sets(self, work: str) -> list[dict]:
        return self.s.list("option_set", "work = $w AND chosen = NONE", {"w": self._wref(work)})

    def choose_option(self, oid: str, chosen: str) -> None:
        self.s.update("option_set", oid, {"chosen": chosen})

    # ---- 议题 thread ----
    def add_thread(self, work: str, trigger: str, topic: str = "", messages=None) -> str:
        return self.s.create("thread", {"work": self._wref(work), "trigger": trigger,
                             "topic": topic, "messages": json.dumps(messages or [], ensure_ascii=False),
                             "status": "open", "created_at": _now()})

    def list_threads(self, work: str, status: str | None = None) -> list[dict]:
        if status:
            return self.s.list("thread", "work = $w AND status = $s",
                               {"w": self._wref(work), "s": status})
        return self.s.list("thread", "work = $w", {"w": self._wref(work)})

    def resolve_thread(self, tid: str, resolution: str = "") -> None:
        self.s.update("thread", tid, {"status": "resolved", "resolution": resolution})

    # ---- 素材 material(内容实体,可检索)----
    def add_material(self, work: str, content: str, type_: str = "snippet",
                     scope: str = "work", title: str = "") -> str:
        return self.s.put_content("material", work=self._wref(work), text=content,
                                  type=type_, title=title, content=content,
                                  tags="", status="pending", scope=scope)

    def list_materials(self, work: str) -> list[dict]:
        return self.s.list("material", "work = $w", {"w": self._wref(work)})

    def update_material(self, mid: str, patch: dict) -> None:
        self.s.update("material", mid, patch)

    def delete_material(self, mid: str) -> None:
        self.s.delete("material", mid)

    # ---- 想象 imagination(内容实体)----
    def add_imagination(self, work: str, raw_text: str) -> str:
        return self.s.put_content("imagination", work=self._wref(work), text=raw_text,
                                  raw_text=raw_text, status="captured", created_at=_now())

    def list_imaginations(self, work: str) -> list[dict]:
        return self.s.list("imagination", "work = $w", {"w": self._wref(work)})

    def set_imagination_status(self, iid: str, status: str) -> None:
        self.s.update("imagination", iid, {"status": status})

    # ---- 偏好信号 preference ----
    def add_preference(self, work: str, source: str, polarity: str = "+", signal=None) -> str:
        return self.s.create("preference_signal", {"work": self._wref(work), "source": source,
                             "polarity": polarity, "signal": json.dumps(signal or {}, ensure_ascii=False),
                             "created_at": _now()})

    # ---- 跨会话记忆 agent_memory ----
    def write_agent_memory(self, owner: str, work: str | None, namespace: str, key: str,
                           value, confidence: float = 1.0) -> str:
        rid = self.s.create("agent_memory", {"owner": owner,
                            "work": self._wref(work) if work else None, "namespace": namespace,
                            "key": key, "value": json.dumps(value, ensure_ascii=False)
                            if not isinstance(value, str) else value,
                            "confidence": confidence, "updated_at": _now()})
        return rid

    def list_agent_memory(self, owner: str, work: str | None = None,
                          namespace: str | None = None) -> list[dict]:
        rows = self.s.list("agent_memory", "owner = $o", {"o": owner})
        if work:
            wref = self._wref(work)
            rows = [r for r in rows if r.get("work") == wref]   # 按书隔离
        if namespace:
            rows = [r for r in rows if r.get("namespace") == namespace]
        return rows

    # ---- 技能 agent_skill ----
    def propose_skill(self, work: str, name: str, spec=None) -> str:
        return self.s.create("agent_skill", {"work": self._wref(work), "name": name,
                             "spec": json.dumps(spec or {}, ensure_ascii=False)
                             if not isinstance(spec, str) else spec,
                             "status": "proposed", "created_by": "agent",
                             "approved_by_human": False, "created_at": _now()})

    def list_agent_skills(self, work: str, status: str | None = None) -> list[dict]:
        rows = self.s.list("agent_skill", "work = $w", {"w": self._wref(work)})
        if status:
            rows = [r for r in rows if r.get("status") == status]
        return rows

    def act_skill(self, sid: str, action: str) -> str:
        mp = {"approve": "approved", "activate": "active", "retire": "retired"}
        st = mp.get(action, action)
        patch = {"status": st}
        if action == "approve":
            patch["approved_by_human"] = True
        self.s.update("agent_skill", sid, patch)
        return st

    # ---- 实体关系 entity_relation ----
    def add_relation(self, work: str, src: str, dst: str, relation: str,
                     **kw) -> str:
        return self.s.create("entity_relation", {"work": self._wref(work), "src_entity": src,
                             "dst_entity": dst, "relation": relation, **kw})

    def list_relations(self, work: str, upto: int | None = None) -> list[dict]:
        rows = self.s.list("entity_relation", "work = $w", {"w": self._wref(work)})
        if upto is not None:
            rows = [r for r in rows if (r.get("valid_from_chapter") or 0) <= upto]
        return rows

    def relations_of(self, work: str, entity: str) -> list[dict]:
        """某实体的所有关系(作为 src 或 dst),供设定详情显示;手动加的关系也会进关系图谱(打通)。"""
        return [r for r in self.list_relations(work)
                if r.get("src_entity") == entity or r.get("dst_entity") == entity]

    # ---- 统一线模型:通用实体节点 entity_beat(角色弧光/母题复现/设定逐章发展,与伏笔 beats 同构)----
    def add_entity_beat(self, work: str, etype: str, entity: str, chapter: int,
                        kind: str = "develop", *, guidance: str = "", effect: str = "") -> str:
        """给任一实体(character/motif/setting/place…)加一个逐章节点:kind=引入/develop/复现/use/兑现;
        guidance=本章具体怎么处理;effect=想要效果。写作时按章注入,把"伏笔节点指令"泛化到所有线。"""
        return self.s.create("entity_beat", {"work": self._wref(work), "etype": etype,
                             "entity": entity, "chapter": chapter, "kind": kind,
                             "guidance": guidance, "effect": effect, "done": False})

    def list_entity_beats(self, work: str, etype: str | None = None, entity: str | None = None) -> list[dict]:
        rows = self.s.list("entity_beat", "work = $w", {"w": self._wref(work)})
        if etype:
            rows = [r for r in rows if r.get("etype") == etype]
        if entity:
            rows = [r for r in rows if r.get("entity") == entity]
        return sorted(rows, key=lambda r: r.get("chapter") or 0)

    def add_exemplar(self, work: str, text: str, technique: str = "") -> str:
        """存一段范文(style_exemplar):带技法标注的标杆片段,注入生成上下文作正面锚(few-shot)。"""
        return self.s.create("style_exemplar", {"work": self._wref(work), "text": text, "technique": technique})

    def list_exemplars(self, work: str) -> list[dict]:
        return self.s.list("style_exemplar", "work = $w", {"w": self._wref(work)})

    _RESOLVE_KINDS = {"兑现", "payoff", "use", "resolve", "回收"}

    def entity_lines_health(self, work: str, span: int = 15) -> list[dict]:
        """统一健康检测(把伏笔的"看断线"泛化到所有线):各实体线 久未推进=stale、
        久未推进且未兑现=overdue(悬空)。供泳道顶部健康条 + 注入告警。"""
        maxc = max((c.get("seq") or 0 for c in self.list_chapters(work)), default=0)
        by_line: dict = {}
        for b in self.list_entity_beats(work):
            by_line.setdefault((b.get("etype"), b.get("entity")), []).append(b)
        out = []
        for (et, ent), bs in by_line.items():
            bs = sorted(bs, key=lambda b: b.get("chapter") or 0)
            last = max((b.get("chapter") or 0) for b in bs)
            resolved = any(b.get("kind") in self._RESOLVE_KINDS for b in bs)
            gap = maxc - last
            out.append({"etype": et, "entity": ent, "beats": bs, "last_chapter": last,
                        "resolved": resolved, "stale": gap > span,
                        "overdue": (not resolved) and gap > span})
        return out

    # ---- 角色状态轨迹 char_state ----
    def add_char_state(self, work: str, character: str, chapter_seq: int,
                       state_desc: str = "", change_type: str = "") -> str:
        return self.s.create("char_state", {"work": self._wref(work), "character": character,
                             "chapter_seq": chapter_seq, "state_desc": state_desc,
                             "change_type": change_type})

    def list_char_states(self, work: str, character: str) -> list[dict]:
        rows = self.s.list("char_state", "work = $w AND character = $c",
                           {"w": self._wref(work), "c": character})
        return sorted(rows, key=lambda r: r.get("chapter_seq") or 0)

    def latest_char_states_upto(self, work: str, seq: int) -> list[dict]:
        """Progressions 时间门:取各角色在 chapter_seq<=seq 时的最新状态(防剧透注入)。"""
        rows = self.s.list("char_state", "work = $w", {"w": self._wref(work)})
        latest: dict[str, dict] = {}
        for r in sorted(rows, key=lambda x: x.get("chapter_seq") or 0):
            if (r.get("chapter_seq") or 0) <= seq:
                latest[r.get("character", "")] = r  # 后者覆盖前者=取最新生效
        return list(latest.values())

    # ---- 场景出场追踪(复用段落 citation_refs 自动检测,一份数据双用)----
    def entity_appearances(self, work: str, name: str) -> list[int]:
        """某实体(角色/设定名)出现在哪些章(从各章段落的引用聚合)。"""
        seqs: set[int] = set()
        for ch in self.list_chapters(work):
            cid = self._idpart(ch["id"])
            if any(name in (s.get("citation_refs") or "") for s in self.list_segments(cid)):
                if ch.get("seq") is not None:
                    seqs.add(ch["seq"])
        return sorted(seqs)

    # ---- 时间线 timeline_event ----
    def add_timeline_event(self, work: str, chapter_seq: int, description: str) -> str:
        return self.s.create("timeline_event", {"work": self._wref(work),
                             "chapter_seq": chapter_seq, "description": description})

    def list_timeline(self, work: str) -> list[dict]:
        rows = self.s.list("timeline_event", "work = $w", {"w": self._wref(work)})
        return sorted(rows, key=lambda r: r.get("chapter_seq") or 0)

    # ==== WaveC:质量/成本/impact/任务态 ====
    def record_cost(self, work: str, tokens: int, cost_usd: float = 0.0) -> None:
        self.s.create("quality_snapshot", {"work": self._wref(work), "scope": "cost",
                      "tokens": tokens, "cost_usd": cost_usd, "calls": 1, "created_at": _now()})

    def get_cost(self, work: str) -> dict:
        rows = self.s.list("quality_snapshot", "work = $w AND scope = 'cost'", {"w": self._wref(work)})
        return {"calls": len(rows), "tokens": sum(r.get("tokens") or 0 for r in rows),
                "cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 6)}

    def impact(self, work: str, name: str) -> list[dict]:
        out = []
        for ch in self.list_chapters(work):
            content = self.latest_prose(self._idpart(ch["id"]))
            if name and name in content:
                idx = content.find(name)
                out.append({"seq": ch.get("seq"), "title": ch.get("title", ""),
                            "snippet": content[max(0, idx - 10):idx + 30]})
        return out

    def compute_quality(self, work: str) -> dict:
        chs = self.list_chapters(work)
        proses = [self.latest_prose(self._idpart(c["id"])) for c in chs]
        words = sum(_cjk(p) for p in proses)
        fores = self.s.list("foreshadow", "work = $w", {"w": self._wref(work)})
        planted = len(fores)
        paid = len([f for f in fores if f.get("state") == "paid"])
        flags_open = self.list_consistency_flags(work, "open")
        by_class: dict[str, int] = {}
        for f in flags_open:
            by_class[f.get("error_class", "other")] = by_class.get(f.get("error_class", "other"), 0) + 1
        slops = [_slop_density(p) for p in proses if p]
        avg_slop = round(sum(slops) / len(slops), 4) if slops else 0.0
        weakest = sorted(
            [{"seq": c.get("seq"), "words": _cjk(p),
              "slop_density": _slop_density(p),
              "open_flags": len([f for f in flags_open if f.get("seq") == c.get("seq")])}
             for c, p in zip(chs, proses)],
            key=lambda x: (-x["open_flags"], -x["slop_density"]))[:3]
        return {"chapters": len(chs), "words": words, "avg_slop_density": avg_slop,
                "foreshadow": {"planted": planted, "paid": paid,
                               "payoff_rate": round(paid / planted, 2) if planted else 0.0},
                "consistency": {"open_flags": len(flags_open), "by_class": by_class,
                                "score": round(1 - min(1, len(flags_open) / max(1, len(chs))), 2),
                                "weighted": len(flags_open)},
                "weakest_chapters": weakest, "cost": self.get_cost(work)}

    def snapshot_quality(self, work: str) -> None:
        q = self.compute_quality(work)
        self.s.create("quality_snapshot", {"work": self._wref(work), "scope": "work",
                      "words": q["words"], "slop_density": q["avg_slop_density"],
                      "consistency_score": q["consistency"]["score"],
                      "foreshadow_payoff": q["foreshadow"]["payoff_rate"],
                      "created_at": _now()})

    def list_quality_history(self, work: str, scope: str = "work") -> list[dict]:
        rows = self.s.list("quality_snapshot", "work = $w AND scope = $s",
                           {"w": self._wref(work), "s": scope})
        return sorted(rows, key=lambda r: r.get("created_at") or "")

    # ---- 章编排任务态 ----
    _TASK_NEXT = {
        "PLANNING": ["AWAITING_OUTLINE_CHOICE"],
        "AWAITING_OUTLINE_CHOICE": ["DRAFTING"],
        "DRAFTING": ["AWAITING_REVIEW"],
        "AWAITING_REVIEW": ["REVISING", "DONE"],
        "REVISING": ["AWAITING_REVIEW"],
        "DONE": [],
    }

    def get_task(self, work: str, seq: int) -> dict:
        rows = self.s.list("chapter_task", "work = $w AND seq = $q",
                           {"w": self._wref(work), "q": seq})
        if rows:
            t = rows[0]
            return {**t, "next": self._TASK_NEXT.get(t.get("status", "PLANNING"), [])}
        return {"seq": seq, "status": "PLANNING", "detail": "",
                "next": self._TASK_NEXT["PLANNING"]}

    def advance_task(self, work: str, seq: int, to: str, detail: str = "") -> dict:
        rows = self.s.list("chapter_task", "work = $w AND seq = $q",
                           {"w": self._wref(work), "q": seq})
        cur = rows[0].get("status", "PLANNING") if rows else "PLANNING"
        if to not in self._TASK_NEXT.get(cur, []):
            raise ValueError(f"非法状态转移 {cur}→{to}")
        if rows:
            self.s.update("chapter_task", self._idpart(rows[0]["id"]), {"status": to, "detail": detail})
        else:
            self.s.create("chapter_task", {"work": self._wref(work), "seq": seq,
                          "status": to, "detail": detail})
        return self.get_task(work, seq)

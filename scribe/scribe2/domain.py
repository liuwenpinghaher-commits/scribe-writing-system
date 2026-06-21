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

    # ---- 内容实体:设定(契约:name/type/content;存 stype 避开 SurrealDB 关键字 type)----
    def add_setting(self, work: str, name: str, desc: str = "", type_: str = "设定") -> str:
        text = f"{name}:{desc}" if desc else name
        return self.s.put_content("setting", work=self._wref(work), text=text,
                                  name=name, stype=type_, content=desc)

    def list_settings(self, work: str) -> list[dict]:
        rows = self.s.list("setting", "work = $w", {"w": self._wref(work)})
        for s in rows:
            s["type"] = s.get("stype", "设定")  # 前端契约别名
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

    # ---- 角色(含声音指纹;内容实体,可语义检索) ----
    def add_character(self, work: str, name: str, motivation: str = "", voice: str = "") -> str:
        text = "；".join(x for x in [name, motivation, voice] if x)
        return self.s.put_content("character", work=self._wref(work), text=text,
                                  name=name, motivation=motivation, voice=voice)

    def list_characters(self, work: str) -> list[dict]:
        return self.s.list("character", "work = $w", {"w": self._wref(work)})

    # ---- 伏笔 ----
    def plant_foreshadow(self, work: str, summary: str, chapter: int,
                         importance: str = "normal") -> str:
        return self.s.put_content("foreshadow", work=self._wref(work), text=summary,
                                  summary=summary, chapter=chapter,
                                  importance=importance, state="planted")

    def list_open_foreshadows(self, work: str) -> list[dict]:
        return self.s.list("foreshadow",
                           "work = $w AND state IN ['planted', 'triggered']",
                           {"w": self._wref(work)})

    def advance_foreshadow(self, fid: str, to_state: str) -> None:
        self.s.update("foreshadow", fid, {"state": to_state})

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

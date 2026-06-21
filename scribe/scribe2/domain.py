from __future__ import annotations
import json
import re
from .store import Store


def _cjk(s: str) -> int:
    return sum(1 for ch in (s or "") if "一" <= ch <= "鿿")


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
        return self.s.create("volume", {"work": f"work:{work}", "seq": seq, "title": title})

    def add_chapter(self, work: str, seq: int, title: str = "", volume: str | None = None) -> str:
        return self.s.create("chapter", {
            "work": f"work:{work}", "seq": seq, "title": title,
            "volume": (f"volume:{volume}" if volume else None), "status": "draft"})

    def list_chapters(self, work: str) -> list[dict]:
        return self.s.list("chapter", "work = $w ORDER BY seq ASC", {"w": f"work:{work}"})

    # ---- snapshot 版本树 ----
    def save_prose(self, work: str, chapter: str, content: str, locked: bool = False,
                   created_by: str = "human", branch_label: str = "human-final") -> str:
        existing = self.s.list("snapshot", "chapter = $c", {"c": f"chapter:{chapter}"})
        ver = len(existing) + 1
        sid = self.s.create("snapshot", {
            "work": f"work:{work}", "chapter": f"chapter:{chapter}",
            "version": ver, "content": content, "locked": bool(locked),
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
                "work": f"work:{work}", "chapter": f"chapter:{chapter}", "seq": i,
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
        return self.s.create("feedback", {"work": f"work:{work}", "seq": seq,
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

    # ---- 内容实体:设定 ----
    def add_setting(self, work: str, name: str, desc: str = "", type_: str = "设定") -> str:
        text = f"{name}:{desc}" if desc else name
        return self.s.put_content("setting", work=f"work:{work}", text=text, name=name, stype=type_)

    def list_settings(self, work: str) -> list[dict]:
        return self.s.list("setting", "work = $w", {"w": f"work:{work}"})

    def search(self, work: str, query: str, k: int = 6) -> list[dict]:
        return self.s.search_knowledge(f"work:{work}", query, k=k)

    # ==== 写作层移植:生成上下文实体 ====
    @staticmethod
    def _idpart(rid) -> str:
        """SurrealDB RecordID/字符串 → 纯 id hex(供 store.update)。"""
        if hasattr(rid, "id"):
            return str(rid.id)
        s = str(rid)
        return s.split(":", 1)[1].strip("⟨⟩`") if ":" in s else s

    # ---- 北极星(每书一条,upsert) ----
    def set_intent(self, work: str, reader_feeling: str = "", core_emotional_arc: str = "",
                   why_write: str = "", central_promise: str = "",
                   red_lines: list | None = None) -> None:
        data = {"work": f"work:{work}", "reader_feeling": reader_feeling,
                "core_emotional_arc": core_emotional_arc, "why_write": why_write,
                "central_promise": central_promise, "red_lines": red_lines or []}
        existing = self.s.list("author_intent", "work = $w", {"w": f"work:{work}"})
        if existing:
            self.s.update("author_intent", self._idpart(existing[0]["id"]), data)
        else:
            self.s.create("author_intent", data)

    def get_intent(self, work: str) -> dict | None:
        rows = self.s.list("author_intent", "work = $w", {"w": f"work:{work}"})
        return rows[0] if rows else None

    # ---- 角色(含声音指纹;内容实体,可语义检索) ----
    def add_character(self, work: str, name: str, motivation: str = "", voice: str = "") -> str:
        text = "；".join(x for x in [name, motivation, voice] if x)
        return self.s.put_content("character", work=f"work:{work}", text=text,
                                  name=name, motivation=motivation, voice=voice)

    def list_characters(self, work: str) -> list[dict]:
        return self.s.list("character", "work = $w", {"w": f"work:{work}"})

    # ---- 伏笔 ----
    def plant_foreshadow(self, work: str, summary: str, chapter: int,
                         importance: str = "normal") -> str:
        return self.s.put_content("foreshadow", work=f"work:{work}", text=summary,
                                  summary=summary, chapter=chapter,
                                  importance=importance, state="planted")

    def list_open_foreshadows(self, work: str) -> list[dict]:
        return self.s.list("foreshadow",
                           "work = $w AND state IN ['planted', 'triggered']",
                           {"w": f"work:{work}"})

    def advance_foreshadow(self, fid: str, to_state: str) -> None:
        self.s.update("foreshadow", fid, {"state": to_state})

    # ---- 记忆:章梗概(可检索)+ 全局主线(scope 区分) ----
    def save_chapter_memory(self, work: str, seq: int, summary: str) -> str:
        scope = f"chapter:{seq}"
        existing = self.s.list("memory_entry", "work = $w AND scope = $s",
                               {"w": f"work:{work}", "s": scope})
        if existing:
            rid = self._idpart(existing[0]["id"])
            self.s.update("memory_entry", rid, {"text": summary, "seq": seq})
            return rid
        return self.s.put_content("memory_entry", work=f"work:{work}", text=summary,
                                  scope=scope, seq=seq)

    def list_chapter_memories(self, work: str, upto: int | None = None) -> list[dict]:
        rows = [r for r in self.s.list("memory_entry", "work = $w", {"w": f"work:{work}"})
                if r.get("seq") is not None]
        if upto is not None:
            rows = [r for r in rows if r["seq"] <= upto]
        return sorted(rows, key=lambda r: r["seq"])

    def set_global_memory(self, work: str, text: str) -> None:
        existing = self.s.list("memory_entry", "work = $w AND scope = 'global'",
                               {"w": f"work:{work}"})
        if existing:
            self.s.update("memory_entry", self._idpart(existing[0]["id"]), {"text": text})
        else:
            self.s.put_content("memory_entry", work=f"work:{work}", text=text, scope="global")

    def get_global_memory(self, work: str) -> str:
        rows = self.s.list("memory_entry", "work = $w AND scope = 'global'",
                           {"w": f"work:{work}"})
        return rows[0]["text"] if rows else ""

    # ---- 一致性 flag ----
    def list_consistency_flags(self, work: str, status: str = "open") -> list[dict]:
        return self.s.list("consistency_flag", "work = $w AND status = $s",
                           {"w": f"work:{work}", "s": status})

    def resolve_consistency_flag(self, fid: str, status: str = "fixed") -> None:
        self.s.update("consistency_flag", fid, {"status": status})

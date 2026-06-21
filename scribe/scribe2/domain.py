from __future__ import annotations
from .store import Store


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
    def save_prose(self, work: str, chapter: str, content: str, locked: bool = False) -> str:
        existing = self.s.list("snapshot", "chapter = $c", {"c": f"chapter:{chapter}"})
        ver = len(existing) + 1
        return self.s.create("snapshot", {
            "work": f"work:{work}", "chapter": f"chapter:{chapter}",
            "version": ver, "content": content, "locked": bool(locked)})

    def list_snapshots(self, chapter: str) -> list[dict]:
        return self.s.list("snapshot", "chapter = $c ORDER BY version ASC",
                           {"c": f"chapter:{chapter}"})

    def latest_prose(self, chapter: str) -> str:
        snaps = self.list_snapshots(chapter)
        return snaps[-1]["content"] if snaps else ""

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

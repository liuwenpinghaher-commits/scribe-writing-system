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

"""S7 · 章节正文持久化(manuscript)TDD —— 写书的地基(scribe3 此前不存生成的章节)。"""


def test_save_and_get_chapter(store):
    store.save_chapter(1, "雨砸在乱葬岗上。", title="对峙", focalizer="role:老道")
    ch = store.get_chapter(1)
    assert ch and ch["prose"].startswith("雨砸") and ch["title"] == "对峙"
    assert ch["focalizer"] == "role:老道"


def test_save_chapter_upsert(store):
    store.save_chapter(1, "初稿。")
    store.save_chapter(1, "改稿。", title="对峙")     # 同 seq 覆盖
    ch = store.get_chapter(1)
    assert ch["prose"] == "改稿。" and ch["title"] == "对峙"
    assert len(store.list_chapters()) == 1


def test_list_chapters_ordered(store):
    store.save_chapter(2, "二", title="继路")
    store.save_chapter(1, "一", title="对峙")
    seqs = [c["seq"] for c in store.list_chapters()]
    assert seqs == [1, 2]


def test_get_missing_chapter(store):
    assert store.get_chapter(99) is None

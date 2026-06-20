from scribe2.store import Store
from scribe2.domain import Domain

def test_work_volume_chapter(db):
    d = Domain(Store(db)); d.s.init_schema()
    w = d.create_work("雨夜", genre="悬疑")
    v = d.create_volume(w, seq=1, title="上卷")
    d.add_chapter(w, seq=2, title="二", volume=v)
    d.add_chapter(w, seq=1, title="一", volume=v)
    chs = d.list_chapters(w)
    assert [c["seq"] for c in chs] == [1, 2]
    assert d.get_work(w)["title"] == "雨夜"

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

def test_snapshots_versioning(db):
    d = Domain(Store(db)); d.s.init_schema()
    w = d.create_work("书"); c = d.add_chapter(w, 1, "一")
    d.save_prose(w, c, "初稿。", locked=False)
    d.save_prose(w, c, "改稿。", locked=True)
    snaps = d.list_snapshots(c)
    assert [s["version"] for s in snaps] == [1, 2]
    assert d.latest_prose(c) == "改稿。"
    assert snaps[1]["locked"] is True

def test_setting_and_search(db):
    d = Domain(Store(db)); d.s.init_schema()
    w = d.create_work("书")
    d.add_setting(w, name="断魂剑", desc="会让持有者失忆的古剑")
    d.add_setting(w, name="码头", desc="雨夜常起雾")
    hits = d.search(w, "失忆的剑", k=2)
    assert hits and "断魂剑" in (hits[0].get("text") or "")

"""多书支持 · 一书一 DB(NS=scribe3 / db=<slug>),注册表在 db=_reg。TDD 隔离。"""
from scribe3.ontology import Entity
from scribe3.store import SurrealStore, create_work, list_works


def test_create_and_list_works(store):
    create_work("拾骨记", slug="shigu", url=store.url)
    works = list_works(url=store.url)
    assert any(w["title"] == "拾骨记" and w["slug"] == "shigu" for w in works)


def test_list_auto_registers_main(store):
    works = list_works(url=store.url)   # 空注册表 → 自动登记 main
    assert any(w["slug"] == "main" for w in works)


def test_books_are_isolated(store):
    create_work("书甲", slug="booka", url=store.url)
    create_work("书乙", slug="bookb", url=store.url)
    a = SurrealStore(url=store.url, ns="scribe3", db="booka")
    b = SurrealStore(url=store.url, ns="scribe3", db="bookb")
    try:
        a.add_entity(Entity("role:甲角", "character", "甲角"))
        assert len(a.characters()) == 1, "书甲有1角色"
        assert len(b.characters()) == 0, "书乙隔离,无角色"
    finally:
        a.close(); b.close()


def test_delete_and_guard_main(store):
    import pytest
    from scribe3.store import delete_work
    create_work("待删", slug="todel", url=store.url)
    delete_work("todel", url=store.url)
    assert not any(w["slug"] == "todel" for w in list_works(url=store.url))
    with pytest.raises(ValueError):
        delete_work("main", url=store.url)


def test_rename_and_stats(store):
    from scribe3.store import rename_work
    create_work("旧名", slug="ren1", url=store.url)
    rename_work("ren1", "新名", url=store.url)
    assert any(w["slug"] == "ren1" and w["title"] == "新名" for w in list_works(url=store.url))
    store.save_chapter(1, "一二三四五。", title="x")
    s = store.stats()
    assert s["chapter_count"] == 1 and s["word_count"] == 6

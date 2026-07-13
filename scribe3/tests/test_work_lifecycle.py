"""作品生命周期:软删(废弃箱)+ 重名硬拦(store 层)。TDD 隔离——只用 `store`
fixture 起的临时内存 SurrealDB(见 conftest.py),绝不触碰生产库。"""
import pytest

from scribe3.store import (archive_work, archived_works, create_work,
                            delete_work, list_works, rename_work,
                            restore_work)


def test_archive_hides_from_list_and_shows_in_archived(store):
    create_work("待废弃之书", slug="w1", url=store.url)
    archive_work("w1", url=store.url)
    assert not any(w["slug"] == "w1" for w in list_works(url=store.url))
    arch = archived_works(url=store.url)
    row = next(w for w in arch if w["slug"] == "w1")
    assert row["archived_at"] is not None


def test_restore_reappears_in_list(store):
    create_work("待恢复之书", slug="w2", url=store.url)
    archive_work("w2", url=store.url)
    restore_work("w2", url=store.url)
    assert any(w["slug"] == "w2" for w in list_works(url=store.url))
    assert not any(w["slug"] == "w2" for w in archived_works(url=store.url))


def test_archive_main_forbidden(store):
    list_works(url=store.url)  # 触发 main 自动登记
    with pytest.raises(ValueError):
        archive_work("main", url=store.url)


def test_delete_unarchived_forbidden(store):
    create_work("未废弃之书", slug="w3", url=store.url)
    with pytest.raises(ValueError):
        delete_work("w3", url=store.url)


def test_archive_then_delete_purges_registry_and_db(store):
    create_work("待永久删除之书", slug="w4", url=store.url)
    archive_work("w4", url=store.url)
    delete_work("w4", url=store.url)
    assert not any(w["slug"] == "w4" for w in list_works(url=store.url))
    assert not any(w["slug"] == "w4" for w in archived_works(url=store.url))


def test_create_duplicate_title_rejected(store):
    create_work("撞名之书", slug="w5", url=store.url)
    with pytest.raises(ValueError):
        create_work("撞名之书", slug="w5b", url=store.url)
    # strip 后比对也应命中
    with pytest.raises(ValueError):
        create_work("  撞名之书  ", slug="w5c", url=store.url)


def test_archived_book_does_not_occupy_title(store):
    create_work("可复用书名", slug="w6", url=store.url)
    archive_work("w6", url=store.url)
    result = create_work("可复用书名", slug="w6b", url=store.url)
    assert result["slug"] == "w6b"
    assert any(w["slug"] == "w6b" and w["title"] == "可复用书名"
               for w in list_works(url=store.url))


def test_rename_duplicate_rejected_but_self_rename_allowed(store):
    create_work("甲书", slug="w7a", url=store.url)
    create_work("乙书", slug="w7b", url=store.url)
    with pytest.raises(ValueError):
        rename_work("w7b", "甲书", url=store.url)
    # 改成自己原名允许
    rename_work("w7a", "甲书", url=store.url)
    assert any(w["slug"] == "w7a" and w["title"] == "甲书"
               for w in list_works(url=store.url))


def test_restore_conflict_with_active_same_title(store):
    create_work("重名争夺战", slug="w8", url=store.url)
    archive_work("w8", url=store.url)
    create_work("重名争夺战", slug="w8b", url=store.url)
    with pytest.raises(ValueError):
        restore_work("w8", url=store.url)

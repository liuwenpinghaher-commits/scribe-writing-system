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


# ===== API 层(TestClient)=====
#
# 隔离说明:app.py 里 /works 系列端点直调 store 模块级函数(list_works/create_work/
# archive_work/restore_work/delete_work/archived_works),这些函数的 url 参数默认读
# `SCRIBE3_SURREAL_URL` 环境变量(生产默认 ws://127.0.0.1:8001/rpc)。因此仅靠
# `A.set_store(store)`(只覆盖 /chat 等走 _store_for("main") 缓存的端点)不足以隔离
# works 端点——必须 monkeypatch.setenv("SCRIBE3_SURREAL_URL", store.url),让这些
# 模块函数的默认 url 指向本测试起的临时内存 SurrealDB。此写法沿用仓内既有先例
# test_gapfix.py(同一坑,同一解)。

import scribe3.app as A
from fastapi.testclient import TestClient


def _api_client(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SURREAL_URL", store.url)
    return TestClient(A.app)


def test_api_delete_moves_to_archive_box(store, monkeypatch):
    create_work("接口删除之书", slug="a1", url=store.url)
    c = _api_client(store, monkeypatch)
    r = c.delete("/works/a1")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "archived": True}
    slugs = [w["slug"] for w in c.get("/works").json()]
    assert "a1" not in slugs, "废弃后不应出现在正常作品列表"
    arch_slugs = [w["slug"] for w in c.get("/works/archived").json()["works"]]
    assert "a1" in arch_slugs, "废弃后应出现在废弃箱"


def test_api_delete_main_forbidden_400(store, monkeypatch):
    list_works(url=store.url)  # 触发 main 自动登记
    c = _api_client(store, monkeypatch)
    r = c.delete("/works/main")
    assert r.status_code == 400


def test_api_restore_reappears(store, monkeypatch):
    create_work("接口恢复之书", slug="a2", url=store.url)
    c = _api_client(store, monkeypatch)
    c.delete("/works/a2")
    r = c.post("/works/a2/restore")
    assert r.status_code == 200
    slugs = [w["slug"] for w in c.get("/works").json()]
    assert "a2" in slugs


def test_api_restore_conflict_409(store, monkeypatch):
    create_work("接口撞名恢复", slug="a3", url=store.url)
    c = _api_client(store, monkeypatch)
    c.delete("/works/a3")
    create_work("接口撞名恢复", slug="a3b", url=store.url)
    r = c.post("/works/a3/restore")
    assert r.status_code == 409


def test_api_purge_wrong_title_422(store, monkeypatch):
    create_work("接口永删之书", slug="a4", url=store.url)
    c = _api_client(store, monkeypatch)
    c.delete("/works/a4")
    r = c.request("DELETE", "/works/a4/purge", json={"confirm_title": "错的名字"})
    assert r.status_code == 422


def test_api_purge_unarchived_409(store, monkeypatch):
    create_work("接口未废弃永删", slug="a5", url=store.url)
    c = _api_client(store, monkeypatch)
    r = c.request("DELETE", "/works/a5/purge", json={"confirm_title": "接口未废弃永删"})
    assert r.status_code == 409


def test_api_purge_success_really_deletes(store, monkeypatch):
    create_work("接口真删之书", slug="a6", url=store.url)
    c = _api_client(store, monkeypatch)
    c.delete("/works/a6")
    r = c.request("DELETE", "/works/a6/purge", json={"confirm_title": "接口真删之书"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "purged": True}
    assert not any(w["slug"] == "a6" for w in archived_works(url=store.url))
    assert not any(w["slug"] == "a6" for w in list_works(url=store.url))


def test_api_create_duplicate_409(store, monkeypatch):
    create_work("接口撞名新建", slug="a7", url=store.url)
    c = _api_client(store, monkeypatch)
    r = c.post("/works", json={"title": "接口撞名新建"})
    assert r.status_code == 409


def test_api_rename_duplicate_409(store, monkeypatch):
    create_work("接口甲书", slug="a8a", url=store.url)
    create_work("接口乙书", slug="a8b", url=store.url)
    c = _api_client(store, monkeypatch)
    r = c.patch("/works/a8b", json={"title": "接口甲书"})
    assert r.status_code == 409

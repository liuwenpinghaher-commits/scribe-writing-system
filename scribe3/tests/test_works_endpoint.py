"""书库入口不能被逐本统计查询串行卡死。"""
from __future__ import annotations

from collections import OrderedDict

import scribe3.app as A


class _LoadedStore:
    def __init__(self, slug: str):
        self.slug = slug

    def stats(self):
        return {"chapter_count": 1, "word_count": 120}

    def get_intent(self):
        return {"total_word_goal": 50_000}


def test_works_does_not_open_every_book_database_just_to_render_library(monkeypatch):
    """冷启动书库只列注册表；不能为每本书建连接、迁移并统计。"""
    calls = []
    monkeypatch.setattr(A, "list_works", lambda: [
        {"slug": "book_a", "title": "甲"},
        {"slug": "book_b", "title": "乙"},
    ])
    monkeypatch.setattr(A, "_stores", OrderedDict())
    monkeypatch.setattr(A, "_store_for", lambda slug: calls.append(slug))

    rows = A.works()

    assert calls == []
    assert all(row["stats_pending"] is True for row in rows)
    assert all("word_count" not in row for row in rows)


def test_works_reuses_loaded_book_statistics_without_claiming_zero(monkeypatch):
    """已打开的书仍展示真实统计；未加载的书显式标为待加载。"""
    monkeypatch.setattr(A, "list_works", lambda: [
        {"slug": "book_a", "title": "甲"},
        {"slug": "book_b", "title": "乙"},
    ])
    monkeypatch.setattr(A, "_stores", OrderedDict(book_a=_LoadedStore("book_a")))

    rows = A.works()

    assert rows[0]["word_count"] == 120
    assert rows[0]["total_word_goal"] == 50_000
    assert rows[1]["stats_pending"] is True
    assert "word_count" not in rows[1]

"""SurrealDB 2.1.4 迁移语法护栏：禁止再引入 2.1 不支持的 ASYNC RETRY / FULLTEXT / COUNT INDEX。"""
from __future__ import annotations

from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def test_017_no_async_retry_syntax():
    text = (MIGRATIONS / "017_async_events.surql").read_text(encoding="utf-8")
    assert "ASYNC RETRY" not in text
    assert "DEFINE EVENT" in text


def test_070_078_use_search_analyzer_not_fulltext():
    for name in ("070_material_memory.surql", "078_memory_fabric.surql"):
        text = (MIGRATIONS / name).read_text(encoding="utf-8")
        assert "FULLTEXT ANALYZER" not in text, name
        assert "SEARCH ANALYZER" in text, name


def test_075_no_count_index_on_2_1():
    text = (MIGRATIONS / "075_chapter_record_range_count.surql").read_text(encoding="utf-8")
    assert "ON chapter COUNT" not in text

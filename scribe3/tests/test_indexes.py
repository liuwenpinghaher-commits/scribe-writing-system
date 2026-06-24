"""Test performance index existence (E枢纽 索引)."""
import pytest


class TestUniqueIndexes:
    """UNIQUE 索引拒绝重复值——需要先清洗重复数据

    通过检查重复数据来验证唯一约束的可行性。
    """

    def test_chapter_has_no_duplicate_seq(self, store):
        rows = store._query("SELECT seq, count() AS c FROM chapter GROUP BY seq")
        duplicates = [r for r in rows if r.get("c", 0) > 1]
        assert len(duplicates) == 0, f"重复的 chapter.seq: {duplicates}"

    def test_motif_has_no_duplicate_name(self, store):
        rows = store._query("SELECT name, count() AS c FROM motif GROUP BY name")
        duplicates = [r for r in rows if r.get("c", 0) > 1]
        assert len(duplicates) == 0, f"重复的 motif.name: {duplicates}"

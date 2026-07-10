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


class TestChapterScanPlans:
    def test_record_range_uses_record_id_scan(self, store):
        plan = str(store._raw_query(
            "EXPLAIN SELECT seq FROM chapter:1..=4 ORDER BY seq"))
        assert "RecordIdScan" in plan, plan

    def test_chapter_count_index_is_ready_and_countscan_fast_path_is_selected(self, store):
        info = store._raw_query("INFO FOR INDEX idx_chapter_count ON chapter")
        assert (info.get("building") or {}).get("status") == "ready", info
        plan = str(store._raw_query(
            "EXPLAIN SELECT count() FROM chapter GROUP ALL"))
        # SurrealDB 3.1.5 对无条件全表 count 即使指定 WITH INDEX,
        # 仍优先使用内建 CountScan;它只数 record key,不反序列化行。
        assert "CountScan" in plan and "TableScan" not in plan, plan

    def test_active_chapter_count_index_is_selected(self, store):
        plan = str(store._raw_query(
            "EXPLAIN SELECT count() FROM chapter "
            "WHERE archived = NONE OR archived != true GROUP ALL"))
        assert "IndexCountScan" in plan, plan

"""B23 · crash-safe 分阶段 journal + resume 协议测试。

对标 oh-story short-analyze/output-contract.md:73-88 的分阶段输出契约:
Stage 开始置 last_stage_in_progress=N → 干活 → 通过才 append stages_completed[];
resume 时 in_progress 非空则该 Stage 从头重跑(没有部分完成态,只有"完整完成"或"从头重来")。
"""
import json

from scribe3.pipeline_journal import PipelineJournal


class TestPipelineJournal:
    def test_start_and_complete_stage(self, tmp_path):
        j = PipelineJournal(tmp_path / "j.json")
        j.start_stage("ingest_ch3")
        assert j.in_progress() == "ingest_ch3"
        j.complete_stage("ingest_ch3")
        assert j.in_progress() is None
        assert "ingest_ch3" in j.stages_completed()

    def test_crash_resume_point(self, tmp_path):
        p = tmp_path / "j.json"
        j1 = PipelineJournal(p)
        j1.start_stage("ingest_ch1"); j1.complete_stage("ingest_ch1")
        j1.start_stage("ingest_ch2")   # 崩溃:未 complete
        j2 = PipelineJournal(p)        # 新实例=重启
        assert j2.resume_point() == "ingest_ch2"
        assert "ingest_ch1" in j2.stages_completed()

    def test_all_complete_resume_none(self, tmp_path):
        p = tmp_path / "j.json"
        j = PipelineJournal(p)
        j.start_stage("a"); j.complete_stage("a")
        assert PipelineJournal(p).resume_point() is None

    def test_should_skip_completed(self, tmp_path):
        p = tmp_path / "j.json"
        j = PipelineJournal(p)
        j.start_stage("a"); j.complete_stage("a")
        j2 = PipelineJournal(p)
        assert j2.should_skip("a") is True and j2.should_skip("b") is False

    def test_atomic_write_no_partial_file(self, tmp_path):
        # journal 文件本身写入必须原子(临时文件+rename),崩在写journal时不留半截JSON
        p = tmp_path / "j.json"
        j = PipelineJournal(p)
        j.start_stage("a")
        assert json.loads(p.read_text())  # 任何时刻文件都是合法 JSON

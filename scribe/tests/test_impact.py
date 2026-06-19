"""影响分析/角色时间线 自检:引用过某名字的章节按序返回。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def test_chapters_citing():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    d.upsert_character(w, "沈砚")
    d.upsert_setting(w, "地点", "归墟")
    # 第2章提到沈砚;第5章提到沈砚+归墟;第3章不提
    c2 = d.save_chapter(w, 2, "二")
    d.save_segments(w, c2, "沈砚推开门。", created_by="ai")
    c3 = d.save_chapter(w, 3, "三")
    d.save_segments(w, c3, "雨下了一夜。", created_by="ai")
    c5 = d.save_chapter(w, 5, "五")
    d.save_segments(w, c5, "沈砚走进归墟,风很大。", created_by="ai")

    shen = d.chapters_citing(w, "沈砚")
    assert [c["seq"] for c in shen] == [2, 5], shen  # 按 seq 序,排除第3章
    assert shen[0]["snippet"].startswith("沈砚")
    gx = d.chapters_citing(w, "归墟")
    assert [c["seq"] for c in gx] == [5], gx
    assert d.chapters_citing(w, "不存在的人") == []
    print("  ✓ test_chapters_citing")


if __name__ == "__main__":
    test_chapters_citing()
    print("\n通过。")

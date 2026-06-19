"""章节重排 自检:相邻交换 seq,内容(title)随之换位,边界空操作。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def test_move_chapter():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    for s, t in [(1, "A"), (2, "B"), (3, "C")]:
        d.save_chapter(w, s, t)
    order = lambda: [(c["seq"], c["title"]) for c in d.list_chapters(w)]  # noqa: E731
    assert order() == [(1, "A"), (2, "B"), (3, "C")]
    # B 上移:seq1↔seq2 → 第1章变 B,第2章变 A
    assert d.move_chapter(w, 2, -1) is True
    assert order() == [(1, "B"), (2, "A"), (3, "C")]
    # 第1章再上移到顶 = 边界空操作
    assert d.move_chapter(w, 1, -1) is False
    assert order() == [(1, "B"), (2, "A"), (3, "C")]
    # C 下移到底 = 边界空操作
    assert d.move_chapter(w, 3, 1) is False
    # A(现 seq2)下移:seq2↔seq3
    assert d.move_chapter(w, 2, 1) is True
    assert order() == [(1, "B"), (2, "C"), (3, "A")]
    print("  ✓ test_move_chapter")


if __name__ == "__main__":
    test_move_chapter()
    print("\n通过。")

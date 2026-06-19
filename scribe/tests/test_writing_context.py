"""LP-1 写作上下文注入 自检(确定性部分:北极星/红线/角色/设定/反AI腔)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_writing_context():
    import scribe_mcp.api as api
    from scribe_mcp.db import Database
    db = Database(":memory:")
    api.db = db  # 指向内存库
    w = db.create_work("u9", "测试书", "玄幻")
    db.set_author_intent(w, reader_feeling="脊背发凉", do_not_betray=["主角不能圣母"])
    db.upsert_character(w, "艾琳")
    db.upsert_setting(w, "地点", "归墟")  # 签名:(work_id, type_, name)
    ctx = api._writing_context(w, "u9", 1)
    assert "脊背发凉" in ctx
    assert "主角不能圣母" in ctx
    assert "艾琳" in ctx and "归墟" in ctx
    assert "AI 腔" in ctx
    # 无北极星的新书:不报错、仅含反AI腔
    w2 = db.create_work("u9", "空书")
    ctx2 = api._writing_context(w2, "u9", 1)
    assert "AI 腔" in ctx2 and "北极星" not in ctx2
    print("  ✓ test_writing_context")


if __name__ == "__main__":
    test_writing_context()
    print("\n通过。")

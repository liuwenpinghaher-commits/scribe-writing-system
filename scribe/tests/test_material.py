"""C4 素材库 自检:增改查删、owner/work 作用域隔离、出处追踪。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def test_materials():
    d = Database(":memory:")
    w1 = d.create_work("u", "书1")
    w2 = d.create_work("u", "书2")
    # 本书素材 + 跨作品素材
    m_book = d.add_material("u", "snippet", "雨夜", "霉味与滴水声", work_id=w1)
    m_owner = d.add_material("u", "quote", "金句", "沉默是最重的回答", work_id=None)
    # 书1 可见两者;书2 只见 owner 级(防串味)
    ids1 = {m["id"] for m in d.list_materials("u", w1)}
    ids2 = {m["id"] for m in d.list_materials("u", w2)}
    assert m_book in ids1 and m_owner in ids1
    assert m_book not in ids2 and m_owner in ids2

    # 处理:打标签+状态
    d.update_material(m_book, tags=["氛围", "感官"], status="processed")
    assert d.get_material(m_book)["status"] == "processed"

    # 出处追踪
    d.add_material_ref(m_book, "setting_item", "set-123", "distill_setting")
    refs = d.list_material_refs(m_book)
    assert refs and refs[0]["ref_type"] == "distill_setting"

    # 删除级联清出处
    d.delete_material(m_book)
    assert d.get_material(m_book) is None
    assert d.list_material_refs(m_book) == []
    print("  ✓ test_materials")


if __name__ == "__main__":
    test_materials()
    print("\n通过。")

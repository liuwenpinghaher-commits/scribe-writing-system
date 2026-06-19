"""多方案 OptionSet 自检(选项式核心):创建/选择/校验/防重复。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def _setup():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    db = Database(tmp.name)
    return db, db.create_work("u", "书")


def test_create_and_choose():
    db, w = _setup()
    oid = db.create_option_set(w, "本章转折怎么走", [
        {"id": "A", "approach": "正面硬刚", "tradeoff": "爽但损耗信息差"},
        {"id": "B", "approach": "示弱设局", "tradeoff": "慢但更意外"},
    ])
    assert len(db.list_open_option_sets(w)) == 1
    res = db.choose_option(oid, "B", rationale="要意外")
    assert res["chosen"] == "B"
    assert db.list_open_option_sets(w) == [], "已选的不应再出现在待选"


def test_validation():
    db, w = _setup()
    # 少于 2 个方案应拒绝
    try:
        db.create_option_set(w, "x", [{"id": "A"}])
        raise AssertionError("单方案未被拒绝")
    except ValueError:
        pass
    oid = db.create_option_set(w, "x", [{"id": "A"}, {"id": "B"}])
    # 选不存在的 id
    try:
        db.choose_option(oid, "Z")
        raise AssertionError("非法选项 id 未被拒绝")
    except ValueError:
        pass
    db.choose_option(oid, "A")
    # 重复选择应拒绝
    try:
        db.choose_option(oid, "B")
        raise AssertionError("重复选择未被拒绝")
    except ValueError:
        pass


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

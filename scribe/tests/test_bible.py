"""设定圣经(角色)+ 一致性标记 自检。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def _db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    return Database(tmp.name)


def test_character_upsert_and_isolation():
    db = _db()
    a = db.create_work("u", "A"); b = db.create_work("u", "B")
    db.upsert_character(a, "林越", traits={"trait": "孤傲"},
                        voice_profile={"catchphrase": "无妨"})
    db.upsert_character(a, "林越", motivation="复仇")  # upsert 同一角色
    chars = db.list_characters(a)
    assert len(chars) == 1 and chars[0]["motivation"] == "复仇"
    assert db.list_characters(b) == [], "串味!A 书角色出现在 B 书"


def test_consistency_flag_lifecycle():
    db = _db()
    w = db.create_work("u", "书")
    fid = db.raise_consistency_flag(w, "item_state_contradiction", chapter_seq=42,
                                    severity="major", detail="发夹已遗失却再次出现")
    assert len(db.list_consistency_flags(w, "open")) == 1
    db.resolve_consistency_flag(fid, "confirmed")
    assert db.list_consistency_flags(w, "open") == []
    assert len(db.list_consistency_flags(w, "confirmed")) == 1
    try:
        db.resolve_consistency_flag(fid, "bogus")
        raise AssertionError("非法 status 未被拦截")
    except ValueError:
        pass


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

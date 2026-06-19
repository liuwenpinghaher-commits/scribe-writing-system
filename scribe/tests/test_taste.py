"""跨书品味模型自检(多本书 §2.7)—— owner 级跨书共享、book 级隔离、防串味。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.taste import TasteStore  # noqa: E402


def _setup():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    db = Database(tmp.name)
    a = db.create_work("u", "A书"); b = db.create_work("u", "B书")
    return db, TasteStore(db.conn), a, b


def test_owner_signal_shared_across_books():
    db, ts, a, b = _setup()
    # owner 级信号(不绑书):喜欢克制的文风
    ts.record_signal("u", source="feedback", polarity="+", weight=1.5,
                     signal={"pref": "克制文风"}, work_id=None)
    # 两本书都应看到这条 owner 级信号
    for w in (a, b):
        srcs = [s["source"] for s in ts.get_effective_signals("u", w)]
        assert "feedback" in srcs, "owner 级信号应跨书可见"


def test_book_signal_isolated():
    db, ts, a, b = _setup()
    # A 书专属信号(如该书特有的暗黑基调偏好)
    ts.record_signal("u", source="option_choice", polarity="+", weight=1.0,
                     signal={"pref": "A书暗黑"}, work_id=a)
    a_sigs = ts.get_effective_signals("u", a)
    b_sigs = ts.get_effective_signals("u", b)
    assert any(s["work_id"] == a for s in a_sigs), "A 书应看到自己的信号"
    assert all(s["work_id"] != a for s in b_sigs), "串味!A 书的 book 级信号泄漏到 B 书"


def test_aggregate_merges_owner_and_book():
    db, ts, a, b = _setup()
    ts.record_signal("u", "feedback", "+", 2.0, work_id=None)        # owner 底色
    ts.record_signal("u", "feedback", "-", 0.5, work_id=a)           # A 书内的负向
    agg_a = ts.aggregate("u", a)
    agg_b = ts.aggregate("u", b)
    # A 书:owner(+2.0) + 本书(-0.5) = 1.5
    assert abs(agg_a["feedback"] - 1.5) < 1e-9
    # B 书:只有 owner(+2.0)
    assert abs(agg_b["feedback"] - 2.0) < 1e-9


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

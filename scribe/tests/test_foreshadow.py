"""伏笔 F-T-P 状态机自检(纯 stdlib,可离线验证)。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.foreshadow import ForeshadowStore  # noqa: E402


def _setup():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    db = Database(tmp.name)
    wid = db.create_work("u", "书")
    return db, ForeshadowStore(db.conn), wid


def test_valid_lifecycle():
    db, fs, wid = _setup()
    fid = fs.plant(wid, "主角左手有胎记", foreshadow_chapter=3)
    assert fs.get(fid)["state"] == "planted"
    fs.transition(fid, "triggered", chapter=40)
    assert fs.get(fid)["state"] == "triggered"
    fs.transition(fid, "paid", chapter=88)
    r = fs.get(fid)
    assert r["state"] == "paid" and r["payoff_chapter"] == 88 and r["trigger_chapter"] == 40


def test_illegal_transition_rejected():
    db, fs, wid = _setup()
    fid = fs.plant(wid, "某伏笔", 1)
    # planted 不能直接 paid(必须先 triggered)
    try:
        fs.transition(fid, "paid")
        raise AssertionError("非法转移 planted→paid 未被拦截")
    except ValueError:
        pass
    # 终态不可再转移
    fs.transition(fid, "abandoned")
    try:
        fs.transition(fid, "triggered")
        raise AssertionError("终态 abandoned 仍可转移")
    except ValueError:
        pass


def test_overdue_warning():
    db, fs, wid = _setup()
    f_norm = fs.plant(wid, "普通伏笔", foreshadow_chapter=10, importance="normal")
    f_crit = fs.plant(wid, "关键伏笔", foreshadow_chapter=10, importance="critical")
    # 当前第 40 章,阈值 50:普通(需50)未超;关键(50/2=25)已超
    over = {r["id"] for r in fs.overdue(wid, current_chapter=40, threshold=50)}
    assert f_crit in over and f_norm not in over
    # 第 70 章:两者都超
    over2 = {r["id"] for r in fs.overdue(wid, current_chapter=70, threshold=50)}
    assert f_crit in over2 and f_norm in over2


def test_payoff_rate():
    db, fs, wid = _setup()
    a = fs.plant(wid, "a", 1); b = fs.plant(wid, "b", 2); fs.plant(wid, "c", 3)
    fs.transition(a, "triggered"); fs.transition(a, "paid")
    fs.transition(b, "abandoned")
    # paid=1, abandoned=1, planted=1 → 1/3
    assert abs(fs.payoff_rate(wid) - 1 / 3) < 1e-9


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

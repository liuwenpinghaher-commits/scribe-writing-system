"""C1-1 TasteModel 真学习 自检:信号→learned_preferences;时间衰减;owner/book 合并。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.taste import TasteStore  # noqa: E402


def test_build_and_get():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    ts = TasteStore(d.conn)
    # 正向:接受了"更紧张、句子更短";"节奏明快" —— 跨书底色
    ts.record_signal("u", "feedback_accept", "+", signal={"text": "更紧张，句子更短"}, work_id=None)
    ts.record_signal("u", "option_choice", "+", signal={"text": "节奏明快"}, work_id=w)
    # 负向:拒绝了"大段抒情"
    ts.record_signal("u", "feedback", "-", signal={"text": "大段抒情"}, work_id=w)
    ts.record_signal("u", "intentional", "+", signal={}, work_id=w)

    m = ts.build_taste_model("u", w)
    lp = m["learned_preferences"]
    assert "更紧张" in lp["prefers"] and "句子更短" in lp["prefers"], lp
    assert "节奏明快" in lp["prefers"]
    assert "大段抒情" in lp["avoids"], lp
    assert "容忍看似偏离的写法" in lp["prefers"]  # intentional 弱正信号
    assert m["signal_count"] == 4

    got = ts.get_taste_model("u", w)
    assert "更紧张" in got["prefers"] and "大段抒情" in got["avoids"]
    # 防串味:另一本书不应拿到本书级负向"大段抒情"(它是 work=w 级)
    w2 = d.create_work("u", "书2")
    got2 = ts.get_taste_model("u", w2)
    assert "大段抒情" not in got2["avoids"], got2
    # 但跨书底色"更紧张"(owner级)应出现在书2
    assert "更紧张" in got2["prefers"], got2
    print("  ✓ test_build_and_get")


if __name__ == "__main__":
    test_build_and_get()
    print("\n通过。")

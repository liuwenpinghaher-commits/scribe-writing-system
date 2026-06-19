"""C3-1 LLM 层 自检:成本估算、token 兜底、路由、账本(不打真实网络)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp import llm  # noqa: E402
from scribe_mcp.db import Database  # noqa: E402


def test_cost_and_route():
    c = llm.estimate_cost("doubao-seed-2.0-pro", 1000, 1000)
    assert c == round(0.0008 + 0.002, 6)
    assert llm.estimate_cost("未知模型", 1000, 0) == round(0.001, 6)  # 回退价
    assert llm.model_for("draft") == "doubao-seed-2.0-pro"
    assert llm.model_for("不存在角色") == llm.ROLE_MODEL["default"]
    assert llm._approx_tokens("一二三四五六七八") >= 4


def test_ledger():
    d = Database(":memory:")
    led = llm.TokenLedger(d.conn)
    w = d.create_work("u", "书")
    led.record(w, "draft", "doubao-seed-2.0-pro", 1000, 500)
    led.record(w, "critique", "doubao-seed-2.0-pro", 200, 100)
    led.record(None, "chat", "doubao-seed-2.0-pro", 50, 50)  # 未归属
    t = led.total_cost(w)
    assert t["calls"] == 2 and t["tokens"] == 1800 and t["cost_usd"] > 0
    assert led.total_cost()["calls"] == 3  # 全局含未归属
    print("  ✓ test_cost_and_route / test_ledger")


if __name__ == "__main__":
    test_cost_and_route()
    test_ledger()
    print("\n通过。")

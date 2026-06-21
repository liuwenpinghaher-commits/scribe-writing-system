"""主编 agentic 集成 smoke:真调 Hermes /v1/responses,验证主编自己调 scribe2 MCP 工具
查 SurrealDB 真实数据回答。需:SurrealDB:8001 在跑、Hermes:8642 已挂 scribe2、数据已迁。
跑:cd scribe && .venv/bin/python tools/chief_agentic_smoke.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe2.conn import connect, domain_from  # noqa: E402
from scribe2.llm import hermes_responses_events  # noqa: E402


def main():
    d = domain_from(connect())
    w = next((x for x in d.list_works("u1") if x["title"] == "九原渡"), None)
    if not w:
        print("✗ SurrealDB 无《九原渡》,先跑 migrate_jiuyuandu.py")
        return 1
    wid = w["id"]
    instr = ("你是《九原渡》的主编。涉及书里人物/设定/伏笔时,务必调用 scribe2 工具查真实数据,"
             f"不要凭空编。当前 work_id={wid},查数据时把它传给工具。")
    msg = "渡叔这个人物的核心动机是什么?他和小满是什么关系?简短回答。"
    tools_called, answer = [], []
    for ev in hermes_responses_events(msg, instr):
        t = ev.get("type", "")
        if t == "response.output_item.added":
            it = ev.get("item", {}) or {}
            if it.get("type") == "function_call":
                tools_called.append(it.get("name", ""))
        elif t == "response.output_text.delta":
            answer.append(ev.get("delta", ""))
    ans = "".join(answer)
    scribe2_tools = [t for t in tools_called if "scribe2" in t]
    ok_tool = bool(scribe2_tools)
    ok_data = ("渡叔" in ans or "小满" in ans or "三不渡" in ans)
    print(f"主编调用的 scribe2 工具: {scribe2_tools or '(无)'}")
    print(f"回复含真实数据: {ok_data}")
    print(f"回复预览: {ans[:200]}")
    if ok_tool and ok_data:
        print("✓ 主编 agentic 工具调用端到端通过(真调 scribe2 MCP + 真实数据)")
        return 0
    print("✗ 主编未调 scribe2 工具或未用真实数据")
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""B3 写工具审批:门控集合 + 执行派发。

WRITE_GATED 里的工具被 MCP server 改为入队待批(不直接落库);
唯一真正落库点是 execute_write —— REST approve 批准后调用。
各分支与 scribe_mcp/server.py 对应工具体一一对应。
"""
from __future__ import annotations

# 碰正典内容的写工具:必须审批。新增此类工具务必加进本集合,否则绕过审批。
WRITE_GATED = {
    "upsert_setting", "save_chapter", "save_snapshot", "upsert_character",
    "plant_foreshadow", "advance_foreshadow", "set_author_intent",
}


def execute_write(db, fs, tool_name: str, args: dict) -> dict:
    """按 tool_name 派发到真实写函数;返回与对应 MCP 工具相同的结果 dict。"""
    a = args
    if tool_name == "upsert_setting":
        return {"setting_id": db.upsert_setting(a["work_id"], a["type"], a["name"], a.get("content"))}
    if tool_name == "save_chapter":
        return {"chapter_id": db.save_chapter(a["work_id"], a["seq"], a.get("title", ""),
                                              a.get("outline"), a.get("status", "draft"))}
    if tool_name == "save_snapshot":
        return {"snapshot_id": db.save_snapshot(a["work_id"], a["chapter_id"], a["content"],
                                                a.get("created_by", "ai"), a.get("parent_id"),
                                                a.get("branch_label", "ai-draft"))}
    if tool_name == "upsert_character":
        return {"character_id": db.upsert_character(a["work_id"], a["name"], a.get("traits"),
                                                    a.get("motivation", ""), a.get("voice_profile"))}
    if tool_name == "set_author_intent":
        return {"intent_id": db.set_author_intent(
            a["work_id"], reader_feeling=a["reader_feeling"], why_write=a.get("why_write", ""),
            central_promise=a.get("central_promise", ""), do_not_betray=a.get("do_not_betray"))}
    if tool_name == "plant_foreshadow":
        return {"foreshadow_id": fs.plant(a["work_id"], a["summary"], a["foreshadow_chapter"],
                                          a.get("importance", "normal"))}
    if tool_name == "advance_foreshadow":
        fs.transition(a["foreshadow_id"], a["to_state"], a.get("chapter"))
        return {"ok": True, "state": a["to_state"]}
    raise ValueError(f"未注册的写工具: {tool_name}")

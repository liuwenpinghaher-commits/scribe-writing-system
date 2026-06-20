"""Scribe 领域 MCP Server(stdio)—— 把领域工具暴露给 Hermes Agent。

依据:工程8(Hermes 通过 config.yaml mcp_servers 消费本服务)、工程0 spike S2。
运行:`python -m scribe_mcp.server`(需安装 mcp:`uv pip install mcp`)。
状态:【未端到端验证】—— 需 Hermes 环境联调(工程0 S2/S4/S5)。数据层 db.py 已单测。
"""
from __future__ import annotations

import os
from pathlib import Path

from .db import Database
from .foreshadow import ForeshadowStore
from .taste import TasteStore
from .pending import WRITE_GATED  # noqa: F401  (门控集合,文档/契约用)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover - 环境缺失时给清晰提示
    raise SystemExit("缺少 mcp 包,请先 `uv pip install mcp`。数据层 db.py 可独立单测。") from e

# 默认落到 scribe/scribe.db(绝对路径,与启动 cwd 无关 —— Hermes 子进程 cwd 不确定)
_DB_PATH = os.environ.get("SCRIBE_DB") or str(Path(__file__).resolve().parent.parent / "scribe.db")
db = Database(_DB_PATH)
foreshadows = ForeshadowStore(db.conn)
taste = TasteStore(db.conn)
mcp = FastMCP("scribe")


def _gate(tool_name: str, args: dict) -> dict:
    """写类工具统一入口:入队待批,不直接落库。"""
    pid = db.enqueue_pending_write(args["work_id"], tool_name, args)
    return {"status": "awaiting_approval", "pending_id": pid,
            "note": "已提交,待作者在 scribe 里确认后写入"}


@mcp.tool()
def create_work(owner_id: str, title: str, premise: str = "", genre: str = "") -> dict:
    """新建一本书,返回 work_id(多本书:owner_id 为归属边界)。"""
    wid = db.create_work(owner_id, title, premise, genre)
    return {"work_id": wid}


@mcp.tool()
def list_works(owner_id: str) -> list[dict]:
    """列出某作者的全部作品(作品库)。"""
    return db.list_works(owner_id)


@mcp.tool()
def set_author_intent(work_id: str, reader_feeling: str, why_write: str = "",
                      central_promise: str = "", do_not_betray: list | None = None) -> dict:
    """设置/更新北极星(这本书要让读者感受什么 + 绝不背叛的红线)。(写操作,需作者审批)"""
    return _gate("set_author_intent", {"work_id": work_id, "reader_feeling": reader_feeling,
                 "why_write": why_write, "central_promise": central_promise, "do_not_betray": do_not_betray})


@mcp.tool()
def capture_imagination(work_id: str, raw_text: str, type: str = "") -> dict:
    """// 零摩擦捕获一个想象/创意/方向(raw_text 永不修改)。"""
    return {"imagination_id": db.capture_imagination(work_id, raw_text, type)}


@mcp.tool()
def save_chapter(work_id: str, seq: int, title: str = "", outline: dict | None = None,
                 status: str = "draft") -> dict:
    """保存/更新一章的元信息与大纲(按 work+seq upsert)。(写操作,需作者审批)"""
    return _gate("save_chapter", {"work_id": work_id, "seq": seq, "title": title,
                 "outline": outline, "status": status})


@mcp.tool()
def get_chapter(work_id: str, seq: int) -> dict | None:
    """读取某章。"""
    return db.get_chapter(work_id, seq)


@mcp.tool()
def upsert_setting(work_id: str, type: str, name: str, content: dict | None = None) -> dict:
    """写入/更新一条设定(设定圣经的真理源,供自动注入/校验)。(写操作,需作者审批)"""
    return _gate("upsert_setting", {"work_id": work_id, "type": type, "name": name, "content": content})


@mcp.tool()
def list_settings(work_id: str) -> list[dict]:
    """列出本书全部设定(仅本书,防串味)。"""
    return db.list_settings(work_id)


@mcp.tool()
def save_feedback(work_id: str, target_type: str, target_id: str, nl_critique: str) -> dict:
    """记录作者的一条自然语言意见(待解析为指令→定向重写)。"""
    return {"feedback_id": db.save_feedback(work_id, target_type, target_id, nl_critique)}


@mcp.tool()
def save_snapshot(work_id: str, chapter_id: str, content: str, created_by: str = "ai",
                  parent_id: str | None = None, branch_label: str = "ai-draft") -> dict:
    """保存一个正文版本快照(AI 不能覆盖 human-locked,见 工程9)。(写操作,需作者审批)"""
    return _gate("save_snapshot", {"work_id": work_id, "chapter_id": chapter_id, "content": content,
                 "created_by": created_by, "parent_id": parent_id, "branch_label": branch_label})


@mcp.tool()
def list_snapshots(chapter_id: str) -> list[dict]:
    """列出某章的版本树。"""
    return db.list_snapshots(chapter_id)


# ---- 设定圣经:角色 ----
@mcp.tool()
def upsert_character(work_id: str, name: str, traits: dict | None = None,
                     motivation: str = "", voice_profile: dict | None = None) -> dict:
    """写入/更新角色档案(含声音指纹 voice_profile,供写作保持/OOC 检测)。(写操作,需作者审批)"""
    return _gate("upsert_character", {"work_id": work_id, "name": name, "traits": traits,
                 "motivation": motivation, "voice_profile": voice_profile})


@mcp.tool()
def list_characters(work_id: str) -> list[dict]:
    """列出本书角色(仅本书,防串味)。"""
    return db.list_characters(work_id)


# ---- 伏笔 F-T-P 状态机 ----
@mcp.tool()
def plant_foreshadow(work_id: str, summary: str, foreshadow_chapter: int,
                     importance: str = "normal") -> dict:
    """埋一个伏笔(state=planted)。importance: normal/critical。(写操作,需作者审批)"""
    return _gate("plant_foreshadow", {"work_id": work_id, "summary": summary,
                 "foreshadow_chapter": foreshadow_chapter, "importance": importance})


@mcp.tool()
def advance_foreshadow(foreshadow_id: str, to_state: str, chapter: int | None = None) -> dict:
    """推进伏笔状态:triggered/paid/abandoned(非法转移会报错)。(写操作,需作者审批)"""
    work_id = db.work_id_of_foreshadow(foreshadow_id)
    return _gate("advance_foreshadow", {"work_id": work_id, "foreshadow_id": foreshadow_id,
                 "to_state": to_state, "chapter": chapter})


@mcp.tool()
def list_open_foreshadows(work_id: str) -> list[dict]:
    """列出未了结(planted/triggered)的伏笔。"""
    return foreshadows.list_open(work_id)


@mcp.tool()
def overdue_foreshadows(work_id: str, current_chapter: int, threshold: int = 50) -> list[dict]:
    """主动揪出埋了太久没回收的伏笔(主编札记用)。"""
    return foreshadows.overdue(work_id, current_chapter, threshold)


# ---- 一致性标记(门槛,后台) ----
@mcp.tool()
def raise_consistency_flag(work_id: str, error_class: str, chapter_seq: int | None = None,
                           severity: str = "minor", detail: str = "") -> dict:
    """登记一条一致性疑点(error_class 见设计 00 §5)。"""
    return {"flag_id": db.raise_consistency_flag(work_id, error_class, chapter_seq, severity, detail)}


@mcp.tool()
def list_consistency_flags(work_id: str, status: str = "open") -> list[dict]:
    """列出一致性标记(默认 open)。"""
    return db.list_consistency_flags(work_id, status)


# ---- 检索(实现4:语义召回,本书隔离)----
_vec = {"store": None}  # 延迟初始化(避免未用时加载 fastembed)


def _get_vec():
    if _vec["store"] is None:
        from .vec import VecStore, embed
        dim = len(embed(["probe"])[0])
        _vec["store"] = VecStore(db.conn, dim)
    return _vec["store"]


@mcp.tool()
def index_segment(work_id: str, segment_id: str, text: str) -> dict:
    """把一段正文编入语义索引(供后续 search_book 召回)。"""
    from .vec import embed
    vec = _get_vec()
    vec.add(segment_id, work_id, embed([text])[0], content=text)
    return {"ok": True}


@mcp.tool()
def search_book(work_id: str, query: str, k: int = 5) -> list[dict]:
    """按语义召回本书相关正文片段(仅本书,防串味)。返回 [{segment_id, distance, content}]。"""
    from .vec import embed
    vec = _get_vec()
    hits = vec.knn(work_id, embed([query])[0], k)
    return [{"segment_id": s, "distance": d, "content": c} for s, d, c in hits]


# ---- 多方案 OptionSet(协作回路:AI 出选项,人拍板)----
@mcp.tool()
def propose_options(work_id: str, decision_point: str, options: list[dict]) -> dict:
    """在关键决定点给作者 2–4 个有差异的方案(每个含 id/approach/tradeoff),等作者选。"""
    return {"option_set_id": db.create_option_set(work_id, decision_point, options)}


@mcp.tool()
def list_open_options(work_id: str) -> list[dict]:
    """列出待作者选择的多方案。"""
    return db.list_open_option_sets(work_id)


# ---- 反平庸(内核3:AI 腔检测)----
@mcp.tool()
def check_ai_slop(text: str) -> dict:
    """检测文本里的 AI 腔病症(顿悟升华/情感直说/不是…而是/套话比喻等)。"""
    from .antislop import detect, slop_density
    return {"hits": detect(text), "density_per_1k": round(slop_density(text), 2)}


# ---- 主编札记(主动引擎)----
@mcp.tool()
def add_insight(work_id: str, kind: str, summary: str, severity: str = "info",
                suggested_action: str = "") -> dict:
    """主编主动记一条札记(如发现伏笔超期/主线偏离/孤立设定)。安静呈现,不打断作者。"""
    return {"insight_id": db.add_proactive_insight(work_id, kind, summary,
                                                   severity=severity, suggested_action=suggested_action)}


@mcp.tool()
def check_chapter(work_id: str, seq: int) -> dict:
    """门槛自动校验某章(符号状态矛盾 + AI 腔),产出 consistency_flag。写完一章应调一次。"""
    from .consistency import run_auto_check
    return {"new_flags": len(run_auto_check(db, work_id, seq))}


@mcp.tool()
def run_full_review(work_id: str, current_chapter: int) -> dict:
    """全文体检:扫超期伏笔等,生成主编札记(去重)。"""
    from .review import run_proactive_review
    return {"new_insights": len(run_proactive_review(db, work_id, current_chapter))}


# ---- 品味信号(内核2,跨书) ----
@mcp.tool()
def record_preference(owner_id: str, source: str, polarity: str = "+", weight: float = 1.0,
                      work_id: str | None = None, signal: dict | None = None) -> dict:
    """记录作者偏好信号。work_id 省略=owner 级跨书共享;否则按书。"""
    return {"signal_id": taste.record_signal(owner_id, source, polarity, weight, signal, work_id)}


if __name__ == "__main__":
    mcp.run()  # stdio

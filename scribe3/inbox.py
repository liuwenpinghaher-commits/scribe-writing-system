"""决策收件箱纯函数层。

与 I/O / Surreal 解耦：app_impl.decision_inbox 负责拉源与懒回填，
本模块负责 idea 文案推导、条目装配、排序与 degraded 去重。

风险闭环：旧库 unclear idea 无 question 时，
idea_unclear_question 按 question → note 问句 → 原文模板 → 默认句 推导，
needs_question_backfill 标记应写回的行。
"""
from __future__ import annotations

from typing import Any

DEFAULT_UNCLEAR_QUESTION = "能再说具体一点吗？（落到哪一章 / 想改什么）"

# 数字越小越靠前；未知 kind 落末尾
KIND_PRIORITY: dict[str, int] = {
    "needs_human": 10,
    "pilot_parked": 20,
    "pilot_outline": 30,
    "pilot_delivered": 40,
    "idea_unclear": 50,
    "idea_setting": 60,
    "idea_revise": 70,
    "pulse_decision": 80,
    "promotable_lesson": 90,
    "daily_digest": 100,
}


def _strip(v: Any) -> str:
    return (str(v) if v is not None else "").strip()


def idea_unclear_question(row: dict | None) -> str:
    """为 unclear 想法推导展示/落库用的澄清问句。

    优先级：
    1. 已有 question 字段
    2. note 本身像问句（含 ?/？）
    3. 有正文时用「关于「…」——能再说具体点吗？」模板
    4. DEFAULT_UNCLEAR_QUESTION
    """
    r = row or {}
    q = _strip(r.get("question"))
    if q:
        return q[:200]
    note = _strip(r.get("note"))
    if note and (("?" in note) or ("？" in note)):
        return note[:200]
    text = _strip(r.get("text"))
    if text:
        snippet = text[:40] + ("…" if len(text) > 40 else "")
        return f"关于「{snippet}」——能再说具体点吗？"
    if note:
        return note[:200]
    return DEFAULT_UNCLEAR_QUESTION


def needs_question_backfill(row: dict | None) -> bool:
    """旧库 unclear 行缺 question 时需懒回填。"""
    r = row or {}
    if _strip(r.get("status")) != "unclear":
        return False
    return not _strip(r.get("question"))


def idea_kind(route_kind: str | None, status: str | None) -> str:
    """inbox item.kind：unclear 优先于 route_kind。"""
    st = _strip(status)
    rk = _strip(route_kind) or "unclear"
    if st == "unclear" or rk == "unclear":
        return "idea_unclear"
    if rk == "setting":
        return "idea_setting"
    if rk == "revise":
        return "idea_revise"
    return f"idea_{rk}" if rk else "idea_unclear"


def idea_inbox_item(row: dict) -> dict:
    """idea 表行 → 收件箱条目（含 action / resolve）。"""
    rid = _strip(row.get("id"))
    text = _strip(row.get("text"))
    status = _strip(row.get("status"))
    route_kind = _strip(row.get("route_kind"))
    note = _strip(row.get("note"))
    kind = idea_kind(route_kind, status)
    backfilled = False
    if kind == "idea_unclear":
        had_q = bool(_strip(row.get("question")))
        q = idea_unclear_question(row)
        backfilled = not had_q
        msg = f"想法待澄清：{q}"
        if text:
            msg += f"（原文：{text[:60]}{'…' if len(text) > 60 else ''}）"
        chat = f"这条想法不够清楚：{q}——原文是「{text[:80]}」。帮我一起澄清，再决定落到哪一章/改什么。"
    else:
        label = {"setting": "动设定", "revise": "改旧章"}.get(route_kind, route_kind or "想法")
        msg = f"想法待批（{label}）：{text[:100]}{'…' if len(text) > 100 else ''}"
        if note:
            msg += f" · {note[:60]}"
        chat = f"这条想法「{text[:80]}」路由为{label}（{note or '无备注'}）——帮我评估要不要做、怎么做。"

    item: dict[str, Any] = {
        "id": f"idea:{rid}" if rid else f"idea:anon:{hash(text) & 0xFFFF:x}",
        "kind": kind,
        "message": msg,
        "action": {"kind": "chat", "payload": chat},
    }
    if rid:
        item["resolve"] = {"kind": "idea_resolve", "payload": rid}
    if kind == "idea_unclear" and backfilled:
        item["question_backfilled"] = True
    return item


def sort_items(items: list[dict], focus_seq: int | None = None) -> None:
    """就地排序：焦点章优先，再按 KIND_PRIORITY，再按 seq/id。"""

    def key(it: dict) -> tuple:
        kind = it.get("kind") or ""
        pri = KIND_PRIORITY.get(kind, 500)
        seq = it.get("seq")
        focus_boost = 0
        if focus_seq is not None and seq is not None:
            try:
                focus_boost = 0 if int(seq) == int(focus_seq) else 1
            except (TypeError, ValueError):
                focus_boost = 1
        try:
            seq_k = int(seq) if seq is not None else 10**9
        except (TypeError, ValueError):
            seq_k = 10**9
        return (focus_boost, pri, seq_k, str(it.get("id") or ""))

    items.sort(key=key)


def dedupe_degraded(sources: list[str] | None) -> list[str]:
    """degraded_sources 保序去重。"""
    out: list[str] = []
    seen: set[str] = set()
    for s in sources or []:
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out

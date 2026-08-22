"""决策收件箱纯函数层。

与 I/O / Surreal 解耦：app_impl.decision_inbox 负责拉源与懒回填，
本模块负责 idea 文案推导、条目装配、排序与 degraded 去重。

风险闭环：旧库 unclear idea 无 question 时，
idea_unclear_question 按 question → note 问句 → 原文模板 → 默认句 推导，
needs_question_backfill 标记应写回的行。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

DEFAULT_UNCLEAR_QUESTION = "能再说具体一点吗？（落到哪一章 / 想改什么）"

# 数字越小越靠前；未知 kind 落末尾
KIND_PRIORITY: dict[str, int] = {
    "needs_human": 10,
    "hermes_approval": 12,
    "pilot_parked": 20,
    "selection_l2": 22,
    "selection_l1": 24,
    "selection_failed": 26,
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


def selection_inbox_item(tier: str, chapter: int, body: dict | None) -> dict | None:
    """选择环落盘结果 → 收件箱。已点选/已终选不进；等人或失败要进。"""
    b = body if isinstance(body, dict) else {}
    v = _strip(b.get("verdict"))
    t = _strip(tier).lower() or "l1"
    if t == "l1":
        if v == "picked":
            return None
        if v == "all_failed":
            return {
                "id": f"selection_l1:{chapter}:failed",
                "kind": "selection_failed",
                "seq": chapter,
                "tier": "L1",
                "message": f"第 {chapter} 章轻选失败，请在主编「选择」里重跑。",
                "action": {"kind": "open_select", "payload": chapter, "tier": "l1"},
            }
        if v == "awaiting_pick" or (b.get("variants") and v != "picked"):
            n = len(b.get("variants") or [])
            return {
                "id": f"selection_l1:{chapter}",
                "kind": "selection_l1",
                "seq": chapter,
                "tier": "L1",
                "message": f"第 {chapter} 章轻选有 {n or 2} 条短包待点选（采用为草稿种子）。",
                "action": {"kind": "open_select", "payload": chapter, "tier": "l1"},
            }
        return None
    # L2
    if v in {"finalized", "picked"}:
        return None
    if v == "all_failed":
        return {
            "id": f"selection_l2:{chapter}:failed",
            "kind": "selection_failed",
            "seq": chapter,
            "tier": "L2",
            "message": f"第 {chapter} 章三候选生成失败，请在主编「选择」里重跑。",
            "action": {"kind": "open_select", "payload": chapter, "tier": "l2"},
        }
    if v == "all_filtered":
        return {
            "id": f"selection_l2:{chapter}:filtered",
            "kind": "selection_l2",
            "seq": chapter,
            "tier": "L2",
            "message": f"第 {chapter} 章三候选均被过滤，请在主编「选择」里强制重出或改驱动。",
            "action": {"kind": "open_select", "payload": chapter, "tier": "l2"},
        }
    if v == "awaiting_human" or (b.get("candidates") and v not in {"finalized", "picked"}):
        n = len([c for c in (b.get("candidates") or []) if not c.get("filtered")])
        return {
            "id": f"selection_l2:{chapter}",
            "kind": "selection_l2",
            "seq": chapter,
            "tier": "L2",
            "message": f"第 {chapter} 章选择环有 {n or 3} 条整章候选待终选（须留理由）。",
            "action": {"kind": "open_select", "payload": chapter, "tier": "l2"},
        }
    return None


_L1_NAME = re.compile(r"select_l1_ch(\d+)")
_L2_NAME = re.compile(r"select_ch(\d+)")


def _latest_select_result_files(work: str) -> tuple[dict[int, Path], dict[int, Path]]:
    """journal 目录里每章最新 L1 / L2 结果文件（按 mtime）。"""
    base = os.environ.get("SCRIBE3_LOOP_JOURNAL_DIR") or os.path.expanduser(
        "~/.scribe3-loop-journals"
    )
    root = Path(base) / work
    l1: dict[int, Path] = {}
    l2: dict[int, Path] = {}
    if not root.is_dir():
        return l1, l2
    for fp in root.glob("select_l1_ch*.result.json"):
        m = _L1_NAME.search(fp.name)
        if not m:
            continue
        ch = int(m.group(1))
        prev = l1.get(ch)
        if prev is None or fp.stat().st_mtime >= prev.stat().st_mtime:
            l1[ch] = fp
    for fp in root.glob("select_ch*.result.json"):
        if "select_l1_ch" in fp.name:
            continue
        m = _L2_NAME.search(fp.name)
        if not m:
            continue
        ch = int(m.group(1))
        prev = l2.get(ch)
        if prev is None or fp.stat().st_mtime >= prev.stat().st_mtime:
            l2[ch] = fp
    return l1, l2


def load_selection_inbox_items(work: str) -> tuple[list[dict], bool]:
    """扫选择环落盘 → 收件箱条目。返回 (items, degraded)。"""
    out: list[dict] = []
    degraded = False
    try:
        l1, l2 = _latest_select_result_files(work)
    except Exception:
        return [], True
    for ch, fp in l1.items():
        try:
            body = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            degraded = True
            continue
        it = selection_inbox_item("l1", ch, body)
        if it:
            out.append(it)
    for ch, fp in l2.items():
        try:
            body = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            degraded = True
            continue
        it = selection_inbox_item("l2", ch, body)
        if it:
            out.append(it)
    return out, degraded


def mark_select_result_verdict(path: Path | str, verdict: str) -> None:
    """终选后把落盘 verdict 改掉，避免收件箱一直挂着。"""
    p = Path(path)
    if not p.is_file():
        return
    body = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        return
    body["verdict"] = verdict
    p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")


def hermes_approval_inbox_item(pending: dict | None, *, seq: int | None = None) -> dict | None:
    """在途 Hermes 待批写入 → 收件箱。终态/过期不应进来。"""
    if not isinstance(pending, dict):
        return None
    run_id = _strip(pending.get("run_id"))
    if not run_id:
        return None
    msg = _strip(pending.get("message")) or "主编有一条写入等待你批准。"
    item: dict[str, Any] = {
        "id": f"hermes_approval:{run_id}",
        "kind": "hermes_approval",
        "message": f"主编待批准写入：{msg[:120]}",
        "action": {"kind": "open_chief", "payload": seq, "run_id": run_id},
        "run_id": run_id,
        "approval_id": pending.get("approval_id"),
    }
    if seq is not None:
        item["seq"] = seq
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

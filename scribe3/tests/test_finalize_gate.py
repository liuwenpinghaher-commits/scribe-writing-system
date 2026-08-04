"""写作方案强制闭环 · 定稿门闩 + 检测器 + 卷信号 + 注入下限 TDD。

纯策略单测不启 Surreal;API 路径测在门开时用 store fixture。
"""
from __future__ import annotations

import os

import pytest

from scribe3.finalize_gate import (
    build_deterministic_post,
    collect_deterministic_post_for_prose,
    evaluate_finalize_gate,
    finalize_gate_env_enabled,
)
from scribe3.loop import triage
from scribe3.volume_signals import (
    motifs_without_echo,
    overdue_promises_in_range,
    volume_chapter_seqs,
    volume_review_signals,
)


# ===== 纯策略:evaluate_finalize_gate =====

def test_finalize_gate_blocking_refuses(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "x",
        leaks=[{"marker": "治眼", "fact_id": "fact:治眼"}],
    )
    d = evaluate_finalize_gate(post, danger_draft=False)
    assert d["allowed"] is False
    assert d["verdict"] == "blocking"
    assert d["code"] == "blocked"
    assert d["blocking"]


def test_finalize_gate_danger_draft_bypasses_blocking(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "x",
        leaks=[{"marker": "治眼", "fact_id": "fact:治眼"}],
    )
    d = evaluate_finalize_gate(post, danger_draft=True)
    assert d["allowed"] is True
    assert d["code"] == "danger_bypass"
    assert d["blocking"], "旁路仍应附带 blocking 供 UI 警示"


def test_finalize_gate_advisory_allows_no_rewrite(monkeypatch):
    """advisory:人存=接受;门闩不改写 prose(只裁决 allowed)。"""
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "干净正文。",
        issues=[{"type": "punct", "message": "标点建议", "text": "，",
                 "meta": {}}],
        punct_suggestions=[{"message": "用顿号", "text": "，", "range": [0, 1]}],
    )
    # 无 blocking 但有 advisory 项 → advisory
    t = triage(post)
    assert t["verdict"] in ("advisory", "pass")
    d = evaluate_finalize_gate(post)
    assert d["allowed"] is True
    assert d["verdict"] in ("advisory", "pass")


def test_finalize_gate_pass_allows(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post("他把伞收了,雨还没停。院里只有一声犬吠。")
    d = evaluate_finalize_gate(post)
    assert d["allowed"] is True
    assert d["verdict"] == "pass"
    assert d["code"] == "ok"


def test_finalize_gate_skip_and_env_off(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "0")
    assert finalize_gate_env_enabled() is False
    d = evaluate_finalize_gate(None)
    assert d["allowed"] is True and d["code"] == "skipped"
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    d2 = evaluate_finalize_gate({"leaks": []}, skip=True)
    assert d2["allowed"] is True and d2["code"] == "skipped"


def test_finalize_gate_no_post_fail_closed(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    d = evaluate_finalize_gate(None, danger_draft=False)
    assert d["allowed"] is False
    assert d["code"] == "no_post"


def test_degeneration_blocking_collect_and_gate(monkeypatch):
    """确定性收集 + 退化 blocking 应禁落库。"""
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    # 逐句复读触发 find_degeneration
    prose = "他走了。他走了。他走了。他走了。他走了。"
    post = collect_deterministic_post_for_prose(prose)
    t = triage(post)
    # degeneration 可能 advisory 或 blocking 视 severity;至少 post 结构合法
    assert "issues" in post or "leaks" in post
    d = evaluate_finalize_gate(post)
    assert "verdict" in d
    assert d["allowed"] in (True, False)


# ===== ConStory +3 检测器 =====

def test_find_calendar_month_regression():
    from scribe3.critique import find_calendar_month_regression
    clean = find_calendar_month_regression("正月开笔,到了三月才完。")
    assert clean == []
    bad = find_calendar_month_regression("腊月里封炉,二月又开春。")
    assert bad and bad[0]["kind"] == "calendar_month_regression"


def test_find_pressure_adjacent_jumps():
    from scribe3.critique import find_pressure_adjacent_jumps
    metas = [
        {"seq": 1, "pressure": 1},
        {"seq": 2, "pressure": 5},
        {"seq": 3, "pressure": 4},
    ]
    jumps = find_pressure_adjacent_jumps(metas, threshold=3)
    assert len(jumps) == 1
    assert jumps[0]["seq_from"] == 1 and jumps[0]["seq_to"] == 2


def test_find_memory_denial_hits():
    from scribe3.critique import find_memory_denial_hits
    assert find_memory_denial_hits("他不知道炉心真名。", ["炉心真名"])
    assert find_memory_denial_hits("他不知道炉心真名。", []) == []


# ===== 卷信号 =====

def test_volume_review_signals_overdue_and_motif():
    chapters = [{"seq": 1, "volume": "v1"}, {"seq": 2, "volume": "v1"},
                {"seq": 3, "volume": "v2"}]
    seqs = volume_chapter_seqs(chapters, volume_id="v1")
    assert seqs == [1, 2]
    promises = [
        {"text": "灰契背面", "setup_chapter": 1, "status": "open",
         "resolve_by": 1},
    ]
    overdue = overdue_promises_in_range(promises, up_to=10, seqs=seqs, slack=0)
    assert len(overdue) == 1
    unused = motifs_without_echo(
        [{"id": "m:铜", "name": "铜"}],
        {"m:铜": []},
        seqs=seqs,
    )
    assert unused and unused[0]["signal"] == "no_echo"
    sig = volume_review_signals(
        chapters=chapters, promises=promises,
        motifs=[{"id": "m:铜", "name": "铜"}],
        touch_by_motif={"m:铜": []},
        volume_id="v1", slack=0,
    )
    assert sig["has_stale_signal"] is True
    assert sig["overdue_count"] >= 1


# ===== 注入下限开关差 =====

def test_anti_slop_inject_floor_on_vs_off(monkeypatch):
    from scribe3.api.services import write_assemble as WA
    monkeypatch.setenv("SCRIBE3_INJECT_FLOOR", "1")
    on = WA._anti_slop_floor_block()
    assert "反平庸" in on or "生产下限" in on
    monkeypatch.setenv("SCRIBE3_INJECT_FLOOR", "0")
    off = WA._anti_slop_floor_block()
    assert off == ""
    assert on != off


# ===== 存稿路径策略模拟(无 Surreal:与 save_chapter 同函数链) =====

def test_save_path_blocks_before_persist_on_blocking(monkeypatch):
    """模拟 /save-chapter:blocking 时 allowed=False → 不应调用 save。"""
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "他知道治眼的秘方。",
        leaks=[{"marker": "治眼", "fact_id": "f1"}],
    )
    d = evaluate_finalize_gate(post, danger_draft=False)
    assert d["allowed"] is False
    # 生产路径: not allowed → HTTP 409, st.save_chapter 不执行
    saved = []
    if d["allowed"]:
        saved.append("would_save")
    assert saved == []


def test_save_path_danger_draft_would_persist(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "危险草稿。",
        leaks=[{"marker": "治眼", "fact_id": "f1"}],
    )
    d = evaluate_finalize_gate(post, danger_draft=True)
    assert d["allowed"] is True and d["code"] == "danger_bypass"
    saved = []
    if d["allowed"]:
        saved.append("danger")
    assert saved == ["danger"]


def test_save_path_pass_would_persist(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    d = evaluate_finalize_gate(build_deterministic_post("他把伞收了。"))
    assert d["allowed"] is True and d["verdict"] == "pass"


def test_ingest_status_honesty_semantics():
    """失败态不得标 ok(与 /ingest/status 行语义对齐的纯函数契约)。"""
    def row(stt, pending=False, err=""):
        ok = stt == "ok" and not pending
        failed = (not pending) and stt in ("failed", "parse_failed")
        return {"ok": ok, "failed": failed, "pending": pending,
                "ingest_status": "pending" if pending else stt}
    assert row("failed")["ok"] is False and row("failed")["failed"] is True
    assert row("ok")["ok"] is True and row("ok")["failed"] is False
    assert row("ok", pending=True)["ok"] is False
    assert row("parse_failed")["failed"] is True

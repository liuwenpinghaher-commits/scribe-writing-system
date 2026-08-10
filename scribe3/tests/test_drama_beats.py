"""戏剧节拍纯函数单测 · PR-1（无 Surreal / 无网络 / 无 LLM）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scribe3.drama_beats import (
    DEFAULT_HARD_PRESSURE,
    HIGH_ROLES,
    MIN_FIELD,
    OVERLAP_FAKE_THRESHOLD,
    TURN_COST_LEX,
    drama_score,
    jaccard_cjk,
    resolve_hard_pressure,
    synopsis_overlap_ratio,
    validate_drama_beats,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "drama_beats"


def _load(name: str) -> dict:
    with open(FIX / name, encoding="utf-8") as f:
        return json.load(f)


def test_lexicons_locked():
    """设计初版词表锁定，防 silent shrink。"""
    assert "失败" in TURN_COST_LEX
    assert "空过" in TURN_COST_LEX
    assert "两难" in TURN_COST_LEX
    assert "推进" in HIGH_ROLES
    assert "高压" in HIGH_ROLES
    assert OVERLAP_FAKE_THRESHOLD == pytest.approx(0.72)
    assert MIN_FIELD == 4
    assert DEFAULT_HARD_PRESSURE == 4


def test_cjk_jaccard_and_synopsis_overlap():
    assert jaccard_cjk("", "甲") == 0.0
    # 完全相同 → 1.0
    s = "旧库侧门前高压对峙"
    assert jaccard_cjk(s, s) == pytest.approx(1.0)
    # 假节拍 fixture 的 texts 与 synopsis 应 ≥ 0.72
    fake = _load("synopsis_fake.json")
    texts = [b["text"] for b in fake["beats"]]
    ratio = synopsis_overlap_ratio(texts, fake["synopsis"])
    assert ratio >= fake["expect"]["overlap_min"]


def test_good_v2_passes_high_pressure():
    fx = _load("good_v2.json")
    r = validate_drama_beats(
        fx["beats"],
        chapter_pressure=fx["chapter_pressure"],
        role=fx["role"],
        synopsis=fx["synopsis"],
        chapter_hook=fx["chapter_hook"],
        hard_pressure=4,
        compat_v1=False,
    )
    assert r["ok"] is True, r
    assert r["drama_weak"] is False
    assert r["metrics"]["gcd_scene_count"] >= fx["expect"]["min_gcd_scenes"]
    assert r["metrics"]["has_cost"] is True
    assert r["metrics"]["has_hook"] is True
    assert r["metrics"]["is_high"] is True
    sc = drama_score(fx["beats"], chapter_hook=fx["chapter_hook"])
    assert sc["complete"] is True


def test_v1_text_only_compat_weak_pass():
    fx = _load("v1_text_only.json")
    r = validate_drama_beats(
        fx["beats"],
        chapter_pressure=fx["chapter_pressure"],
        role=fx["role"],
        synopsis=fx["synopsis"],
        hard_pressure=4,
        compat_v1=True,
    )
    assert r["ok"] is True, r
    assert r["drama_weak"] is True
    assert any("v1" in w or "compat" in w for w in r["warnings"])


def test_v1_text_only_without_compat_fails_high():
    fx = _load("v1_text_only.json")
    r = validate_drama_beats(
        fx["beats"],
        chapter_pressure=fx["chapter_pressure"],
        role=fx["role"],
        synopsis=fx["synopsis"],
        hard_pressure=4,
        compat_v1=False,
    )
    assert r["ok"] is False, r
    assert r["errors"], r


def test_synopsis_fake_high_without_compat():
    fx = _load("synopsis_fake.json")
    r = validate_drama_beats(
        fx["beats"],
        chapter_pressure=fx["chapter_pressure"],
        role=fx["role"],
        synopsis=fx["synopsis"],
        hard_pressure=4,
        compat_v1=False,
    )
    assert r["metrics"]["overlap"] >= OVERLAP_FAKE_THRESHOLD
    assert r["ok"] is False, r
    assert any("synopsis_fake" in e or "gcd" in e or "cost" in e for e in r["errors"]) or r["errors"]


def test_synopsis_fake_compat_weak():
    fx = _load("synopsis_fake.json")
    r = validate_drama_beats(
        fx["beats"],
        chapter_pressure=fx["chapter_pressure"],
        role=fx["role"],
        synopsis=fx["synopsis"],
        hard_pressure=4,
        compat_v1=True,
    )
    assert r["ok"] is True, r
    assert r["drama_weak"] is True


def test_hook_always_advisory_never_blocks():
    """KD-NQ-16：缺钩子只 warning，不进 errors。"""
    beats = [
        {
            "id": "b1",
            "kind": "scene",
            "goal": "夺回被扣的半页账角证据",
            "conflict": "看守以刀拦路并索要真名",
            "turn": "她没能夺回，被迫弃刀逃走",
            "cost": "账角失落，身份代价升级",
            "hook": "",
            "text": "夺证失败逃走。",
        }
    ]
    r = validate_drama_beats(
        beats,
        chapter_pressure=5,
        role="高压",
        chapter_hook="",
        hard_pressure=4,
        compat_v1=False,
    )
    assert "chapter_hook_missing" in r["warnings"]
    assert not any("hook" in e for e in r["errors"])
    # 其余 GCD/cost 齐则仍可 ok
    assert r["ok"] is True, r


def test_bridge_exempt_from_cost_but_scene_needs_cost():
    beats = [
        {
            "id": "b1",
            "kind": "bridge",
            "text": "换场到巷口，无戏。",
        },
        {
            "id": "b2",
            "kind": "scene",
            "goal": "在巷口完成暗语交接脱身",
            "conflict": "对方突然改口要全名对质",
            "turn": "她拒绝全交，两难之下只递半页",
            "cost": "",  # 空 cost，但 turn 命中「两难/拒绝」
            "hook": "远处锣响，巡夜逼近。",
            "text": "暗语改口，半页过手。",
        },
    ]
    r = validate_drama_beats(
        beats,
        chapter_pressure=4,
        role="推进",
        hard_pressure=4,
        compat_v1=False,
    )
    assert r["ok"] is True, r
    assert r["metrics"]["turn_cost_lex"] is True


def test_low_role_rel_tension_required():
    beats = [
        {
            "id": "b1",
            "kind": "scene",
            "goal": "整理昨日见闻写成条录",
            "conflict": "笔墨不够",  # 弱冲突且无关系张力词
            "turn": "写完收笔",
            "cost": "无",
            "text": "整理条录。",
        }
    ]
    r = validate_drama_beats(
        beats,
        chapter_pressure=2,
        role="关系回收",
        hard_pressure=4,
        compat_v1=False,
    )
    # conflict 长度够 MIN_FIELD 时 tension_ok=True；缩冲突
    beats2 = [
        {
            "id": "b1",
            "kind": "scene",
            "goal": "想与旧友重逢说话",
            "conflict": "雨",  # < MIN_FIELD 且无 REL 词
            "turn": "未说话就离开了",
            "cost": "无",
            "text": "未遇。",
        }
    ]
    r2 = validate_drama_beats(
        beats2,
        chapter_pressure=2,
        role="关系回收",
        hard_pressure=4,
        compat_v1=False,
    )
    assert r2["ok"] is False
    assert any("rel_tension" in e for e in r2["errors"])

    beats3 = [
        {
            "id": "b1",
            "kind": "scene",
            "goal": "试探旧友是否还信任自己",
            "conflict": "对方疏远且隐瞒近况",
            "turn": "和解未成，双方沉默",
            "cost": "信任裂痕加深",
            "text": "试探失败。",
            "hook": "她把旧物放回盒底。",
        }
    ]
    r3 = validate_drama_beats(
        beats3,
        chapter_pressure=2,
        role="关系回收",
        hard_pressure=4,
        compat_v1=False,
    )
    assert r3["ok"] is True, r3


def test_hard_pressure_env_override(monkeypatch):
    monkeypatch.setenv("SCRIBE3_DRAMA_HARD_PRESSURE", "3")
    assert resolve_hard_pressure(None) == 3
    monkeypatch.delenv("SCRIBE3_DRAMA_HARD_PRESSURE", raising=False)
    assert resolve_hard_pressure(5) == 5
    assert resolve_hard_pressure(None) == 4 or resolve_hard_pressure(None) >= 3


def test_goal_uniqueness_warning():
    same_goal = "必须在子时前夺回那半页账角"
    beats = [
        {
            "id": "b1",
            "kind": "scene",
            "goal": same_goal,
            "conflict": "守门人持刀盘问来历出处",
            "turn": "第一次没能得手被迫后撤",
            "cost": "时间代价空过半个时辰",
            "text": "一探失败。",
        },
        {
            "id": "b2",
            "kind": "scene",
            "goal": same_goal,
            "conflict": "雨幕中有人截走信使包袱",
            "turn": "再次失败两难：要么暴露要么放弃",
            "cost": "身份几乎暴露",
            "hook": "第三声梆子响了。",
            "text": "再探失败。",
        },
    ]
    r = validate_drama_beats(
        beats,
        chapter_pressure=4,
        role="推进",
        hard_pressure=4,
        compat_v1=False,
    )
    assert r["ok"] is True, r
    assert any("goal_overlap" in w for w in r["warnings"])


def test_empty_beats_not_ok():
    r = validate_drama_beats([], chapter_pressure=4, role="推进", compat_v1=True)
    assert r["ok"] is False
    assert "beats_empty" in r["errors"]

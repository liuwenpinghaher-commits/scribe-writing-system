"""P0: 同正文指纹 skip purge + ingest 角色入收件箱门槛(无 Surreal)。"""
from __future__ import annotations

import hashlib

from scribe3.ingest import (
    _prose_fingerprint,
    _should_queue_character_candidate,
    ingest_chapter,
)


def test_should_queue_character_candidate_gates_noise():
    assert _should_queue_character_candidate("焦三") is True
    assert _should_queue_character_candidate("柳怀玉") is True
    # 路人/称谓
    assert _should_queue_character_candidate("老者") is False
    assert _should_queue_character_candidate("婆子") is False
    assert _should_queue_character_candidate("卖灯草的婆子") is False
    assert _should_queue_character_candidate("那汉子") is False
    assert _should_queue_character_candidate("掌柜") is False
    assert _should_queue_character_candidate("李掌柜") is False  # 后缀
    # 过短/过长/非中文
    assert _should_queue_character_candidate("甲") is False
    assert _should_queue_character_candidate("一二三四五六七") is False
    assert _should_queue_character_candidate("Alice") is False
    assert _should_queue_character_candidate("") is False


def test_prose_fingerprint_stable():
    a = _prose_fingerprint("焦三在乱岗取出尸丹。")
    b = _prose_fingerprint("焦三在乱岗取出尸丹。")
    c = _prose_fingerprint("焦三在乱岗取出尸丹！")
    assert a == b and len(a) == 16
    assert a != c


class _SkipStore:
    """最小 store:get_chapter + _query 回指纹,不跑真 LLM。"""

    def __init__(self, prose: str, fp: str | None):
        self.prose = prose
        self.fp = fp
        self.db_name = "main"
        self.calls = 0

    def get_chapter(self, seq):
        return {"seq": seq, "prose": self.prose}

    def _query(self, sql, params=None):
        return [{"ingest_prose_fp": self.fp, "ingest_status": "ok"}]

    def list_motifs(self):
        self.calls += 1
        return []

    def open_promises(self):
        self.calls += 1
        return []

    def characters(self):
        self.calls += 1
        return []


def test_ingest_skips_same_prose_fp():
    prose = "焦三在乱岗取出尸丹。"
    fp = _prose_fingerprint(prose)
    st = _SkipStore(prose, fp)
    called = []

    def boom(_p):
        called.append(1)
        raise AssertionError("同指纹不应再调 LLM")

    r = ingest_chapter(st, 1, boom, work="main", force=False)
    assert r["skipped"] is True
    assert r["reason"] == "same_prose_fp"
    assert r["prose_fp"] == fp
    assert r["applied"] == 0
    assert called == []
    assert st.calls == 0  # 未进入 motif/promise 收集


def test_ingest_force_bypasses_same_prose_fp(monkeypatch):
    prose = "焦三在乱岗取出尸丹。"
    fp = _prose_fingerprint(prose)
    st = _SkipStore(prose, fp)

    monkeypatch.setenv("SCRIBE3_UNIFIED_CHAPTER_ANALYSIS", "0")
    monkeypatch.setattr(
        "scribe3.ingest.apply_delta", lambda *a, **k: 0,
    )
    monkeypatch.setattr(
        "scribe3.ingest.grep_back_verify",
        lambda d, p: {"delta": d, "annotated": []},
    )
    # force 路径可能 import mark; 失败也不应炸
    monkeypatch.setattr(
        "scribe3.api.services.ingest_bg.mark_chapter_ingest_status",
        lambda *a, **k: None,
        raising=False,
    )

    def fake(p):
        return '{"learned":[],"did":[],"voice_shift":[],"events":[]}'

    r = ingest_chapter(st, 1, fake, work="main", force=True, max_attempts=1)
    assert r.get("skipped") is not True
    assert r.get("parse_failed") is not True
    assert st.calls > 0  # 进入了 motif/promise 收集
    assert r.get("prose_fp") == fp

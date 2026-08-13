"""P1：secret_guard 独立段 + reveal_secret_ids 覆盖。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.prompt_blocks import _secret_guard_block
from scribe3.chapter_meta_codec import (
    CHAPTER_META_ALLOWED,
    coerce_chapter_json_list,
)
from scribe3.context_budget import (
    L0_NEVER_CUT,
    NOVEL_PROMPT_HARD,
    generation_physical_order_names,
    join_generation_segments,
)


class _F:
    def __init__(self, secret, leak_markers, *, fid="", entity_id="", attribute=""):
        self.secret = secret
        self.leak_markers = leak_markers
        self.id = fid
        self.entity_id = entity_id
        self.attribute = attribute


class _St:
    def __init__(self, facts, *, reveal=None, boom_facts=False):
        self._f = facts
        self._reveal = reveal
        self.boom_facts = boom_facts

    def facts_at(self, ch):
        if self.boom_facts:
            raise RuntimeError("facts_at down")
        return self._f

    def get_chapter(self, seq):
        return {"reveal_secret_ids": list(self._reveal or [])}


SECRETS = [
    _F(True, ["沈错", "替兄顶罪"], fid="fact:a", entity_id="role:沈错", attribute="true_name"),
    _F(True, ["铜炉鬼"], fid="fact:b", entity_id="role:冷锅婆", attribute="true_name"),
    _F(False, ["公开"]),
]


def test_hard_budget_and_never_name():
    assert NOVEL_PROMPT_HARD == 48000
    assert "secret_guard" in L0_NEVER_CUT
    order = generation_physical_order_names()
    assert order.index("prefix") < order.index("secret_guard")
    assert order.index("secret_guard") < order.index("narrative_contract")


def test_block_hides_markers_when_no_reveal():
    text = _secret_guard_block(_St(SECRETS), chapter=3)
    assert "沈错" in text and "替兄顶罪" in text and "铜炉鬼" in text
    assert "公开" not in text
    assert "绝不明写" in text
    assert "本章揭示" not in text


def test_reveal_secret_ids_drops_that_fact_only():
    text = _secret_guard_block(_St(SECRETS, reveal=["fact:a"]), chapter=3)
    assert "沈错" not in text or "已批准揭开" in text
    assert "替兄顶罪" not in text
    assert "铜炉鬼" in text
    assert "绝不明写" in text
    assert "本章揭示" in text
    assert "role:沈错" in text


def test_reveal_by_entity_id():
    text = _secret_guard_block(_St(SECRETS, reveal=["role:冷锅婆"]), chapter=3)
    assert "铜炉鬼" not in text
    assert "替兄顶罪" in text


def test_reveal_all_has_note_without_ban_list():
    text = _secret_guard_block(
        _St(SECRETS, reveal=["fact:a", "fact:b"]), chapter=3,
    )
    assert "本章揭示" in text
    assert "绝不明写" not in text
    assert "铜炉鬼" not in text
    assert "替兄顶罪" not in text


def test_no_secret_still_empty():
    assert _secret_guard_block(_St([_F(False, ["x"])]), chapter=1) == ""
    assert _secret_guard_block(_St([]), chapter=1) == ""


def test_facts_at_still_fail_loud():
    try:
        _secret_guard_block(_St([], boom_facts=True), chapter=1)
    except RuntimeError as e:
        assert "facts_at down" in str(e)
    else:
        raise AssertionError("facts_at 失败必须 fail-loud")


def test_reveal_list_codec_and_whitelist():
    assert "reveal_secret_ids" in CHAPTER_META_ALLOWED
    assert coerce_chapter_json_list('["fact:a","fact:a"," "]') == ["fact:a"]
    assert coerce_chapter_json_list(None) == []
    src = (
        Path(__file__).resolve().parents[1] / "store/chapters.py"
    ).read_text(encoding="utf-8")
    assert "reveal_secret_ids" in src
    assert "coerce_chapter_json_list(r.get(\"reveal_secret_ids\"))" in src


def test_v1_pushes_secret_guard_not_inside_prefix():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert src.count('_push("secret_guard"') == 1
    assert '_push("secret_guard", "redline", _secret_guard_txt)' in src
    # 不得再拼进 prefix
    assert 'prefix += _domain_input(\n        f"chapter:{chapter}:secret-guard"' not in src
    assert "_secret_guard_block(st, chapter)" in src


def test_join_reports_independent_domain_length():
    guard = _secret_guard_block(_St(SECRETS), chapter=3)
    assert guard
    _out, rep = join_generation_segments([
        {"name": "prefix", "layer": "redline", "text": "IDENT"},
        {"name": "secret_guard", "layer": "redline", "text": guard},
    ])
    assert rep["domain_lengths"]["secret_guard"] == len(guard)
    assert "IDENT" in _out
    assert _out.index("IDENT") < _out.index("核心悬念")

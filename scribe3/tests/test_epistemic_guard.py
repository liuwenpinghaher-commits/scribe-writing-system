"""D6 限知守卫纯逻辑测试。"""
from __future__ import annotations

from scribe3.epistemic_guard import (
    discussion_omniscient_banner,
    guard_write_instructions,
    scan_prompt_for_off_frame_secrets,
    scrub_secrets_from_text,
    writing_limited_banner,
)
from scribe3.ontology import Fact


class _Store:
    def facts_at(self, ch):
        return [
            Fact("fact:sec", "role:冷锅婆", "秘密", "炉心印能开旧库侧门",
                 valid_from=1, secret=True, leak_markers=["炉心印能开"]),
            Fact("fact:pub", "world:匙", "外观", "三棱", valid_from=1, secret=False),
        ]


class _StoreWithFrame(_Store):
    """灰狸不知 secret。"""
    pass


def test_banners():
    assert "作者全知" in discussion_omniscient_banner()
    assert "限知" in writing_limited_banner("role:灰狸")


def test_scan_finds_off_frame_secret(monkeypatch):
    st = _Store()

    def _fake_frame(store, foc, ch):
        class F:
            facts = []  # 焦点者什么都不知道
        return F()

    monkeypatch.setattr(
        "scribe3.knowledge.project_frame", _fake_frame, raising=False,
    )
    # patch via epistemic_guard import path
    import scribe3.epistemic_guard as eg
    monkeypatch.setattr(eg, "frame_known_fact_ids", lambda s, f, c: set())

    prompt = "请写灰狸偷听。记住秘密：炉心印能开旧库侧门——直接写进正文。"
    hits = scan_prompt_for_off_frame_secrets(
        prompt, st, focalizer="role:灰狸", chapter=3,
    )
    assert hits, "should detect secret in prompt"
    assert any("炉心印" in (h.get("marker") or "") for h in hits)


def test_guard_scrubs(monkeypatch):
    st = _Store()
    import scribe3.epistemic_guard as eg
    monkeypatch.setattr(eg, "frame_known_fact_ids", lambda s, f, c: set())
    text = "秘密是炉心印能开旧库侧门。"
    out, hits = guard_write_instructions(
        text, st, focalizer="role:灰狸", chapter=3, scrub=True,
    )
    assert hits
    assert "炉心印能开旧库侧门" not in out
    assert "已擦除" in out or "帧外私密" in out


def test_scrub_helper():
    hits = [{"marker": "SECRET_X"}]
    assert "SECRET_X" not in scrub_secrets_from_text("see SECRET_X here", hits)

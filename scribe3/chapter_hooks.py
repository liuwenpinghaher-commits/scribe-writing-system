"""章末钩子 SSOT 解析（IA KD-IA-5）。

权威顺序（设计 Accepted rev.3.1）：
  ``beats_meta.chapter_hook`` → 末拍 ``hook`` → synopsis 解析的 meta.hook → 上章 end_hook

戏剧合同（``_drama_block`` / ``format_drama_block``）与
``ensure_narrative_drive`` / ``compose`` 种子 **必须** 共用本模块，禁止各写一套。
"""
from __future__ import annotations

from typing import Any


def _s(v: Any) -> str:
    return str(v or "").strip()


def last_beat_hook(beats: Any) -> str:
    """从 beats 列表从后往前找第一个非空 hook。"""
    if not isinstance(beats, list):
        return ""
    for b in reversed(beats):
        if isinstance(b, dict):
            h = _s(b.get("hook"))
            if h:
                return h
    return ""


def resolve_chapter_hook(
    chapter: dict | None = None,
    *,
    beats_meta: dict | None = None,
    beats: list | None = None,
    synopsis_meta: dict | None = None,
    synopsis: str = "",
    prev_end_hook: str = "",
) -> str:
    """按 SSOT 优先级解析章末钩子字符串（可空）。

    参数可从完整章 dict 推断，也可显式覆盖各层。
    """
    ch = chapter if isinstance(chapter, dict) else {}

    meta = beats_meta
    if meta is None:
        raw = ch.get("beats_meta")
        meta = raw if isinstance(raw, dict) else {}
    if not isinstance(meta, dict):
        meta = {}

    bm_hook = _s(meta.get("chapter_hook"))
    if bm_hook:
        return bm_hook

    beat_list = beats if beats is not None else ch.get("beats")
    lb = last_beat_hook(beat_list)
    if lb:
        return lb

    sm = synopsis_meta if isinstance(synopsis_meta, dict) else None
    if sm is None and (synopsis or ch.get("synopsis")):
        try:
            from scribe3.brief import parse_chapter_meta
            sm = parse_chapter_meta(synopsis or ch.get("synopsis") or "") or {}
        except Exception:
            sm = {}
    if isinstance(sm, dict):
        syn_hook = _s(sm.get("hook"))
        if syn_hook:
            return syn_hook

    return _s(prev_end_hook)

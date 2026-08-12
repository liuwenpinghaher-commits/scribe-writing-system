"""Open 伏笔 touch soft advisory（F7 · 不定稿 blocking）。

纯函数：给定 open promises + 正文，返回 advisory 列表。
与 craft-loop CL-B6-H2 对齐：本章应对 open 有 touch/clue 或显式不推进。
"""
from __future__ import annotations

import re
from typing import Any


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


_STOP = frozenset({
    "本章", "回收", "伏笔", "开放", "要", "的", "了", "在", "是", "与", "和",
})


def promise_keywords(text: str) -> list[str]:
    """从伏笔文案抽粗关键词（≥2 字片段，去常见虚词）。"""
    t = (text or "").strip()
    if not t:
        return []
    parts = re.split(r"[\s,，。；;：:、/|]+", t)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) >= 2 and p not in _STOP:
            out.append(p)
    compact = _norm(t)
    # 滑动 2–4 字窗口，覆盖「齿边缺口」「铜匙」等
    for n in (4, 3, 2):
        if len(compact) < n:
            continue
        for i in range(0, len(compact) - n + 1):
            chunk = compact[i : i + n]
            if chunk not in _STOP and not all(c in "的了在是要与和" for c in chunk):
                out.append(chunk)
    seen: set[str] = set()
    uniq: list[str] = []
    for k in out:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq[:40]


def prose_touches_promise(prose: str, promise_text: str) -> bool:
    """正文是否触碰该伏笔关键词（场面路径；meta/SEO 段不计）。"""
    ok, _ = prose_touches_promise_scene(prose, promise_text)
    return ok


def prose_touches_promise_scene(
    prose: str,
    promise_text: str,
    *,
    anti_hits: list | None = None,
) -> tuple[bool, str]:
    """Return (touched, reason). Meta spans and SEO lists do not count."""
    body = prose or ""
    if not body.strip() or not (promise_text or "").strip():
        return False, "empty"
    hits = anti_hits
    if hits is None:
        try:
            from scribe3.anti_meta_narration import scan_anti_meta
            hits = scan_anti_meta(body).get("hits") or []
        except Exception:
            hits = []
    kws = sorted(promise_keywords(promise_text), key=len, reverse=True)
    _verb = re.compile(r"[着了过]|是|在|把|被|说|看|摸|推|藏|问|退|疼|闪")
    for kw in kws:
        if len(kw) < 2:
            continue
        start = 0
        while True:
            i = body.find(kw, start)
            if i < 0:
                break
            j = i + len(kw)
            # meta span?
            try:
                from scribe3.anti_meta_narration import is_meta_span
                if is_meta_span(body, i, j, hits):
                    start = j
                    continue
            except Exception:
                pass
            # sentence window for SEO list
            lo = body.rfind("\n", 0, i)
            lo = 0 if lo < 0 else lo + 1
            hi = body.find("\n", j)
            if hi < 0:
                hi = len(body)
            sent = body[lo:hi]
            # 顿号/逗号分隔 ≥3 token 且无动词启发式 → SEO
            parts = [p for p in re.split(r"[、，,]", sent) if p.strip()]
            if len(parts) >= 3 and not _verb.search(sent):
                start = j
                continue
            return True, "scene"
        # continue next kw
    return False, "no_hit"


def open_promise_touch_advisories(
    prose: str,
    promises: list[dict[str, Any]] | None,
    *,
    chapter_skip_mark: bool = False,
) -> list[dict[str, Any]]:
    """返回 soft advisory 列表；永不 blocking。

    chapter_skip_mark: 作者显式「本章不推进伏笔」时返回空。
    """
    if chapter_skip_mark:
        return []
    items: list[dict[str, Any]] = []
    for p in promises or []:
        if not isinstance(p, dict):
            continue
        if (p.get("status") or "open") != "open":
            continue
        text = str(p.get("text") or p.get("body") or "").strip()
        if not text:
            continue
        if prose_touches_promise(prose, text):
            continue
        pid = p.get("id") or p.get("promise_id") or ""
        items.append({
            "kind": "open_promise_untouched",
            "severity": "advisory",
            "blocking": False,
            "promise_id": pid,
            "text": text[:80],
            "message": f"本章未触碰开放伏笔：「{text[:40]}」——可埋线索，或标记本章不推进。",
        })
    return items

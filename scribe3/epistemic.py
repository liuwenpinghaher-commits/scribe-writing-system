"""限知门：这一章这个人看得见什么。"""
from __future__ import annotations

from typing import Any


def visible_to(store: Any, work: str, chapter: int, viewer: str) -> list[str]:
    """返回 viewer 在这一章看得见的命题 id。查询失败往上抛，不悄悄放行。

    viewer 空 / chief / author = 作者位，仍不含 secret 命题。
    角色 id = 走既有限知帧。
    """
    n = int(chapter or 0)
    who = str(viewer or "").strip()
    if not who or who in ("chief", "author", "主编"):
        ids: list[str] = []
        for f in (store.facts_at(n or 99999) or []):
            secret = bool(getattr(f, "secret", False) if not isinstance(f, dict) else f.get("secret"))
            if secret:
                continue
            fid = getattr(f, "id", None) if not isinstance(f, dict) else f.get("id")
            if fid:
                ids.append(str(fid))
        return ids
    from scribe3.knowledge import project_frame
    frame = project_frame(store, who, n)
    if isinstance(frame, dict):
        vis = frame.get("visible") or frame.get("ids") or []
        return [str(x) for x in vis]
    if isinstance(frame, (list, tuple, set)):
        return [str(x) for x in frame]
    return []

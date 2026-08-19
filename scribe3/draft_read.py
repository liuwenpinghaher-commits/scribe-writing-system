"""草稿读合同：版本表优先，章字段兜底。零 I/O。"""
from __future__ import annotations


def resolve_latest_draft(
    version: dict | None,
    chapter: dict | None,
    frozen_draft: dict | None = None,
) -> dict:
    """DraftTab 真源：版本表 → 冻结 chapter_draft → 旧章字段。"""
    if isinstance(version, dict) and str(version.get("prose") or "").strip():
        out = dict(version)
        out.setdefault("source", "chapter_version")
        return out
    if isinstance(frozen_draft, dict):
        text = str(
            frozen_draft.get("text")
            or frozen_draft.get("prose")
            or (frozen_draft.get("artifact") or {}).get("text")
            or ""
        )
        if text.strip():
            return {
                "prose": text,
                "summary": "",
                "seq": frozen_draft.get("seq") or (chapter or {}).get("seq"),
                "stage": "draft",
                "source": "chapter_draft",
                "sha": frozen_draft.get("sha"),
                "status": frozen_draft.get("status"),
            }
    ch = chapter if isinstance(chapter, dict) else {}
    draft = str(ch.get("draft") or "")
    if not draft.strip():
        return {}
    return {
        "prose": draft,
        "summary": "",
        "seq": ch.get("seq"),
        "stage": "draft",
        "source": "chapter.draft",
    }

"""38 行归位 SSOT + 组织后正文读取。无 I/O 外的副作用；bodies 为只读文件。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_BODIES = Path(__file__).resolve().parent / "bodies"
FEMALE_ID = "female-audience-writing"

# agent-references 25 同源文件名（磁盘核对）
AR_FILES = frozenset({
    "anti-ai-writing", "banned-words", "character-basics", "character-design-methods",
    "character-relations", "dialogue-mastery", "emotional-arc-design", "emotional-methods",
    "format-and-structure", "genre-catalog", "genre-core-mechanics", "genre-readers",
    "genre-writing-formulas", "hooks-chapter", "hooks-suspense", "opening-design",
    "outline-conflict", "outline-methods", "outline-rhythm", "plot-core-methods",
    "quality-checklist", "reversal-toolkit", "style-combat-face", "style-genre-modules",
    "writing-craft",
})

# (n, file, layer, action, title, ui)
_ROWS: tuple[tuple[int, str, str, str, str, str], ...] = (
    (1, "anti-ai-writing", "L_critique", "keep-in-critique", "AI 指纹与去 AI", "show"),
    (2, "artifact-protocols", "L_workflow", "ingest-to-panel", "产物模板映射", "show"),
    (3, "banned-words", "L_critique", "keep-in-critique", "禁用词与毒句式", "show"),
    (4, "character-basics", "story", "ingest-to-fields", "主配反派卡", "show"),
    (5, "character-design-methods", "story", "ingest-to-fields", "人设三层反差", "show"),
    (6, "character-relations", "story", "ingest-to-fields", "关系与感情线", "show"),
    (7, "commercial-core-methods", "catalog", "ingest-to-catalog", "卖点与留存", "show"),
    (8, "cross-book-recall", "L_workflow", "reuse", "跨书召回纪律", "show"),
    (9, "dialogue-mastery", "L_skill", "merge-into-skill", "对话功能与权力", "show"),
    (10, "emotional-arc-design", "story", "ingest-to-fields", "卷级情绪弧", "show"),
    (11, "emotional-methods", "L_move", "lift-to-move", "羁绊三板斧", "show"),
    (12, "female-audience-writing", "archive", "archive-only", "女频手册", "hidden"),
    (13, "format-and-structure", "micro", "reuse", "一段一戏与标点", "show"),
    (14, "genre-catalog", "catalog", "ingest-to-catalog", "题材骨架", "show"),
    (15, "genre-core-mechanics", "catalog", "ingest-to-catalog", "核心梗与冲突网", "show"),
    (16, "genre-readers", "catalog", "ingest-to-catalog", "读者与平台", "show"),
    (17, "genre-writing-formulas", "catalog", "ingest-to-catalog", "21 公式（只读）", "show"),
    (18, "hooks-chapter", "serial", "ingest-to-panel", "章钩类型", "show"),
    (19, "hooks-paragraph", "serial", "ingest-to-panel", "段钩拆分", "show"),
    (20, "hooks-suspense", "serial", "reuse", "悬念与分层钩", "show"),
    (21, "opening-design", "story", "ingest-to-panel", "开篇与黄金三章", "show"),
    (22, "outline-conflict", "story", "ingest-to-panel", "大纲冲突", "show"),
    (23, "outline-methods", "story", "ingest-to-panel", "五步大纲", "show"),
    (24, "outline-rhythm", "story", "ingest-to-panel", "大纲节奏", "show"),
    (25, "outline-structure-theory", "catalog", "ingest-to-catalog", "幕结构", "show"),
    (26, "plot-core-methods", "story", "ingest-to-panel", "小纲与高潮", "show"),
    (27, "plot-emotion-system", "serial", "ingest-to-panel", "递进对抗", "show"),
    (28, "plot-frameworks", "catalog", "ingest-to-catalog", "题材循环框架", "show"),
    (29, "plot-special-topics", "story", "ingest-to-fields", "金手指拆分", "show"),
    (30, "quality-checklist", "L_workflow", "ingest-to-panel", "质量清单", "show"),
    (31, "reversal-toolkit", "L_move", "merge-into-triangle", "六类反转", "show"),
    (32, "state-tracking", "story", "reuse", "本节速记", "show"),
    (33, "style-combat-face", "catalog", "merge-into-triangle", "装逼打脸", "show"),
    (34, "style-craft", "micro", "reuse", "镜头与白描", "show"),
    (35, "style-genre-modules", "L_rule", "reuse", "分题材风格", "show"),
    (36, "workflow-daily", "L_workflow", "ingest-to-panel", "日更步骤", "show"),
    (37, "workflow-revision", "L_workflow", "ingest-to-panel", "回炉步骤", "show"),
    (38, "writing-craft", "micro", "merge-into-triangle", "身体与物件三拍", "show"),
)


def _row(n: int, fid: str, layer: str, action: str, title: str, ui: str) -> dict[str, Any]:
    return {
        "n": n,
        "id": fid,
        "file": f"{fid}.md",
        "title": title,
        "layer": layer,
        "action": action,
        "ui": ui,
        "ar": fid in AR_FILES,
    }


CATALOG: list[dict[str, Any]] = [_row(*t) for t in _ROWS]


def list_catalog(*, include_hidden: bool = False) -> list[dict[str, Any]]:
    """可见编目。默认隐藏女频（ui=hidden）。"""
    rows = list(CATALOG)
    if not include_hidden:
        rows = [r for r in rows if r.get("ui") != "hidden"]
    return rows


def visible_count() -> int:
    return len(list_catalog(include_hidden=False))


def get_row(fid: str) -> dict[str, Any] | None:
    s = (fid or "").strip()
    for r in CATALOG:
        if r["id"] == s or r["file"] == s:
            return dict(r)
    return None


def read_body(fid: str) -> str:
    """读组织后正文。未知/路径穿越 → ValueError。"""
    s = (fid or "").strip()
    if not s or "/" in s or "\\" in s or ".." in s:
        raise ValueError(f"非法编目 id {fid!r}")
    if s.endswith(".md"):
        s = s[:-3]
    row = get_row(s)
    if not row:
        known = "、".join(r["id"] for r in CATALOG)
        raise ValueError(f"未知编目 {fid!r}（可用:{known}）")
    p = _BODIES / f"{row['id']}.md"
    if not p.is_file():
        raise ValueError(f"编目正文缺失 {row['id']}")
    return p.read_text(encoding="utf-8")

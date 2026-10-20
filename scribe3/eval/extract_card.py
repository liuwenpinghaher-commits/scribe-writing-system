"""Give one chapter of 乱世铜炉, emit a 21-section craft card.

Holdout gold cards are never read. Few-shot, if any, comes from the dev split.
"""
from __future__ import annotations

import json
from pathlib import Path

from scribe3.eval.card_schema import CARD_HEADINGS, canonical_heading

ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent
GOLD_DIR = ROOT / "docs/worlds/乱世铜炉-拆文/章卡"
SOURCE = ROOT / "docs/worlds/乱世铜炉-全文.md"


class HoldoutGoldBlocked(RuntimeError):
    pass


def _holdout_set() -> set[int]:
    doc = json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))
    return set(doc["holdout"])


def _chapters() -> dict:
    return json.loads((EVAL / "chapters.json").read_text(encoding="utf-8"))


def chapter_meta(seq: int) -> dict:
    rows = _chapters()["chapters"]
    return next(c for c in rows if c["seq"] == seq)


def load_source_slice(seq: int) -> str:
    meta = chapter_meta(seq)
    if meta.get("span_empty"):
        return ""
    src = SOURCE if SOURCE.exists() else (ROOT / "乱世铜炉.md")
    text = src.read_text(encoding="utf-8")
    lines = text.splitlines()
    start, end = meta["start"], meta["end"]
    sliced = "\n".join(lines[start : end + 1])
    if not sliced.strip() and seq == 0:
        return text
    return sliced


def load_gold_card(seq: int) -> str:
    if seq in _holdout_set():
        raise HoldoutGoldBlocked(f"holdout seq {seq} gold is frozen; do not read")
    path = GOLD_DIR / f"{seq}.md"
    return path.read_text(encoding="utf-8")


def parse_card(md: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in md.splitlines():
        if line.startswith("## "):
            if current is not None:
                parts[current] = "\n".join(buf).strip()
            current = canonical_heading(line[3:].strip())
            buf = []
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        parts[current] = "\n".join(buf).strip()
    return parts


def missing_headings(parts: dict[str, str]) -> list[str]:
    return [h for h in CARD_HEADINGS if h not in parts]


def empty_shell_card(seq: int, title: str) -> str:
    lines = [f"# {seq} {title}", ""]
    for h in CARD_HEADINGS:
        lines.append(f"## {h}")
        if h == "打开书":
            lines.append("正文几乎没有。")
        elif h == "这场戏有没有翻":
            lines.append("没翻。正文几乎没有。")
        elif h == "书证":
            lines.append("本节行距过短，无句可引。")
        else:
            lines.append("正文未写到。")
        lines.append("")
    return "\n".join(lines)


def build_extract_prompt(*, seq: int, title: str, source: str, fewshot: str | None) -> str:
    shot = ""
    if fewshot:
        shot = "下面是另一节的合格卡，只学骨架，不要抄它的专名和情节。\n\n" + fewshot.strip() + "\n\n"
    headings = "\n".join(f"## {h}" for h in CARD_HEADINGS)
    return f"""你只拆这一节。不要读别的章。不要编正文没有的日子。

序号 {seq}。标题：{title}

原文：
{source}

{shot}按下面 21 个二级标题写一张卡。每段只问一件事。没有就写没有或正文未写到。
「打开书」必须写清：谁的夜或白日；发生哪一件事；读完地、人、日子变成什么样；这一节是谁的眼睛在看，还是说书的人站在外头评。不要只写情节摘要。
书证每条必须是原文短句，行号用本节里能搜到的句子，写成 L数字。不要网站广告。
专名原样记下。学结构，不要把这本故事搬进下一本。

# {seq} {title}
{headings}
"""


def pick_dev_fewshot(exclude: int) -> str | None:
    """Dev only. Prefer a complete 打开书 skeleton, not the shortest early card."""
    holdout = _holdout_set()
    meta = {c["seq"]: c for c in _chapters()["chapters"]}
    fallback = None
    for seq in range(214):
        if seq == exclude or seq in holdout:
            continue
        if meta[seq].get("r1_skip_reason"):
            continue
        path = GOLD_DIR / f"{seq}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if fallback is None:
            fallback = text
        ob = parse_card(text).get("打开书", "")
        if "读完" in ob and len(ob) >= 400:
            return text[:8000]
    return None if fallback is None else fallback[:8000]


def extract_card(seq: int, *, complete_fn, use_fewshot: bool = True, source: str | None = None) -> str:
    meta = chapter_meta(seq)
    title = meta["title"]
    if source is None and (meta.get("span_empty") or meta.get("r1_skip_reason") == "empty_shell"):
        return empty_shell_card(seq, title)
    body = load_source_slice(seq) if source is None else source
    fewshot = pick_dev_fewshot(seq) if use_fewshot else None
    # Never feed holdout gold into the prompt: pick_dev_fewshot already skips.
    prompt = build_extract_prompt(seq=seq, title=title, source=body, fewshot=fewshot)
    return complete_fn(prompt)

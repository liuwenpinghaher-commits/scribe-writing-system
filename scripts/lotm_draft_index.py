#!/usr/bin/env python3
"""Draft 诡秘之主 00-index.md from local fulltext (gitignore).

Usage:
  python3 scripts/lotm_draft_index.py
  python3 scripts/lotm_draft_index.py --source docs/worlds/诡秘之主-全文.md --out docs/worlds/诡秘之主-拆文/00-index.md

Does NOT commit. Refuses if source missing. Agent must still spot-check per PROMPTS 第0轮.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "docs/worlds/诡秘之主-全文.md"
DEFAULT_OUT = ROOT / "docs/worlds/诡秘之主-拆文/00-index.md"

# Common LOTM / Qidian chapter-title shapes at line start.
TITLE_RE = re.compile(
    r"^\s*(?P<title>"
    r"(?:第[零〇一二三四五六七八九十百千\d]+章"
    r"|第\d+章"
    r"|Chapter\s+\d+"
    r").*?)\s*$"
)


def cn_or_int_chapno(title: str) -> str:
    m = re.search(r"第([零〇一二三四五六七八九十百千\d]+)章", title)
    if not m:
        m = re.search(r"Chapter\s+(\d+)", title, re.I)
    return m.group(1) if m else ""


def draft(source: Path, out: Path, force: bool) -> int:
    if not source.is_file():
        print(f"BLOCKED: missing fulltext {source}", file=sys.stderr)
        return 2
    if out.is_file() and not force:
        print(f"refuse overwrite existing {out} (pass --force)", file=sys.stderr)
        return 3

    lines = source.read_text(encoding="utf-8").splitlines()
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        m = TITLE_RE.match(line)
        if m:
            hits.append((i, m.group("title").strip()))

    if len(hits) < 10:
        print(
            f"too few title hits ({len(hits)}); check TITLE_RE vs real chapter headings",
            file=sys.stderr,
        )
        return 4

    rows = []
    for seq, (start, title) in enumerate(hits):
        end = (hits[seq + 1][0] - 1) if seq + 1 < len(hits) else len(lines)
        nlines = end - start
        mark = "空壳" if nlines < 20 else ""
        chap = cn_or_int_chapno(title)
        rows.append((seq, chap, title, start, end, nlines, mark))

    out.parent.mkdir(parents=True, exist_ok=True)
    first_t = rows[0][2]
    last_t = rows[-1][2]
    body = [
        f"正表共 {len(rows)} 节（脚本草稿；须按 PROMPTS 第0轮人工/代理抽查）。",
        f"第一题是 {first_t}。",
        f"最后一题是 {last_t}。",
        "",
        f"原文：`{source.as_posix()}`；末行 = {len(lines)}。",
        "行数 = 结束行 − 起始行；结束行 = 下一章题行 − 1。",
        "",
        "## 正表",
        "",
        "| 序号 | 卷 | 章号 | 分册 | 标题原文 | 起始行 | 结束行 | 行数 | 标记 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for seq, chap, title, start, end, nlines, mark in rows:
        # volume left blank for human fill (诡秘多卷)
        body.append(
            f"| {seq} | | {chap} | | {title} | {start} | {end} | {nlines} | {mark} |"
        )
    body.append("")
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"wrote {out} chapters={len(rows)} source_lines={len(lines)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    return draft(args.source, args.out, args.force)


if __name__ == "__main__":
    sys.exit(main())

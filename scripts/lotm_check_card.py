#!/usr/bin/env python3
"""Validate one lotm thick card: required H2 sections + >=3 L-line citations."""
from __future__ import annotations
import re, sys
from pathlib import Path

REQUIRED = [
    "打开书", "这场戏有没有翻", "日子", "这一节落在哪一天", "人", "地与走",
    "这一节新讲明的规矩", "钱与人情", "话", "热怎么变冷", "怎么起、怎么收",
    "叙述怎么插手", "这一节放了什么", "这一节收了什么", "谁比谁多知道",
    "留给下一节的日子", "这一节回不去的事", "这一节人怎么叫人",
    "可搬走的一条作法", "专名原样记下、下一本换自己的名", "书证",
]
L_RE = re.compile(r"\bL\d+\b")

def check(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    missing = [h for h in REQUIRED if f"## {h}" not in text]
    # open book must have punctuation and not be huge paste
    m = re.search(r"## 打开书\n([\s\S]*?)(?:\n## |\Z)", text)
    open_body = (m.group(1) if m else "").strip()
    cites = L_RE.findall(text)
    ok = True
    if missing:
        print(f"FAIL missing sections: {missing}")
        ok = False
    if len(open_body) < 40:
        print("FAIL 打开书 too short")
        ok = False
    if len(open_body) > 8000:
        print("FAIL 打开书 looks like whole-chapter paste")
        ok = False
    if not any(p in open_body for p in "，。；：、！？"):
        print("FAIL 打开书 missing Chinese punctuation")
        ok = False
    if len(cites) < 3:
        print(f"FAIL book evidence L-cites={len(cites)} need >=3")
        ok = False
    if ok:
        print(f"OK {path} L-cites={len(cites)} open_chars={len(open_body)}")
        return 0
    return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: lotm_check_card.py path/to/seq.md", file=sys.stderr)
        sys.exit(2)
    sys.exit(check(Path(sys.argv[1])))

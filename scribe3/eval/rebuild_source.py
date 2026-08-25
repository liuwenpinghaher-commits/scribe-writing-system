"""Rebuild 乱世铜炉 chapter spans against the surviving 30812-line source.

The 拆文 L 号 was cut from a 35538-line dump that is gone. This script copies the
surviving Z-Library text into the gitignored 全文.md and remaps 00-index titles
onto it. Empty-shell gold cards stay flagged so R1 does not treat them as real scenes.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "docs/worlds/乱世铜炉-拆文/00-index.md"
DEST = ROOT / "docs/worlds/乱世铜炉-全文.md"
EVAL = Path(__file__).resolve().parent
HOLDOUT_SEED = 20260826
HOLDOUT_N = 43

DEFAULT_SOURCES = (
    Path.home() / "Downloads/范文分析/乱世铜炉+(又是十三)+(Z-Library).txt",
    Path.home() / "Downloads/写作/重构方案讨论/历史改进版本资料/乱世铜炉+(又是十三)+(Z-Library).txt",
)

_PUNCT = re.compile(r"[\s　:：\(\)（）\[\]【】\-—·,，、\.。!！?？'\"“”‘’]+")
_ZH_NUM = "零一二三四五六七八九十百"


def compact(s: str) -> str:
    return _PUNCT.sub("", s)


def parse_index() -> list[dict]:
    rows = []
    for m in re.finditer(
        r"^\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*(\d+)\s*\|\s*(\d+)\s*\|([^|]*)\|",
        INDEX.read_text(encoding="utf-8"),
        re.M,
    ):
        rows.append(
            {
                "seq": int(m.group(1)),
                "volume": m.group(2).strip(),
                "chapter": m.group(3).strip(),
                "part": m.group(4).strip(),
                "title": m.group(5).strip(),
                "old_start": int(m.group(6)),
                "old_end": int(m.group(7)),
                "note": m.group(8).strip(),
            }
        )
    return rows


def title_keys(title: str) -> list[str]:
    t = title.replace("正传 ", "").replace("正传", "")
    t = t.replace("地六十七", "第六十七")
    t = t.replace("二十六章", "第二十六章")
    t = t.replace("二十七章", "第二十七章")
    t = t.replace("四十一章", "第四十一章")
    c = compact(t)
    keys = [c]
    # drop trailing couplet after 章名
    m = re.match(r"(第[零一二三四五六七八九十百]+章.{0,24})", c)
    if m:
        keys.append(m.group(1))
    return keys


def look_like_heading(s: str) -> bool:
    if not s or len(s) > 90:
        return False
    if s.startswith("“") or s.startswith("「") or s.startswith("‘"):
        return False
    return ("章" in s) or ("外篇" in s) or s.startswith("引子")


def find_heading(lines: list[str], keys: list[str], after: int) -> int | None:
    best = None
    for i in range(after, len(lines)):
        s = lines[i].strip()
        if not look_like_heading(s):
            continue
        c = compact(s)
        for k in keys:
            if not k:
                continue
            if k in c or (len(c) >= 8 and c in k):
                return i
        # looser: chapter number + one distinctive token
        for k in keys:
            tok = re.sub(r"^第[零一二三四五六七八九十百]+章", "", k)
            tok = tok.replace("上", "").replace("中", "").replace("下", "")
            if len(tok) >= 2 and tok in c and "第" in c and "章" in c:
                best = i
                break
        if best is not None:
            return best
    return None


# Manual aliases: (seq, 0-based line in NEW file). Used when the surviving dump
# merged 上中下 into one heading or dropped a 4-line stub.
ALIASES: dict[int, int] = {
    0: 23,      # 引子（贺客）
    38: 6179,   # 第三十八章(风云) — no 上中下 headings
    41: 6538,   # 第三十九章(岔路)
    43: 6767,   # 第四十章（野游）
    57: 10141,  # 第十章 仇怨
    58: 10282,
    59: 10553,
    60: 10668,
    61: 10795,
    62: 10895,
    63: 10974,
    64: 11053,
    67: 11363,
    68: 11458,
    73: 12416,
    74: 12547,
    88: 14551,
    89: 14688,
    182: 25593, # 遁甲（下）；母本多一节「中」并进上
    183: 15267,  # 随水转（上）；补号落在正序第二十八章
    206: 28490,  # 依稀故人（上）
    207: 29073,  # 觉明者（上）
    208: 28563,  # 依稀故人（中）
    209: 29240,  # 觉明者（中）
    210: 28732,  # 依稀故人（下）
    211: 29401,  # 觉明者（下）
}


def load_source() -> tuple[str, list[str]]:
    if DEST.exists():
        text = DEST.read_text(encoding="utf-8")
    else:
        src = next((p for p in DEFAULT_SOURCES if p.exists()), None)
        if src is None:
            raise FileNotFoundError("乱世铜炉全文不在仓库；请把 Z-Library txt 放到 docs/worlds/乱世铜炉-全文.md")
        text = src.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        if not text.endswith("\n"):
            text += "\n"
        DEST.parent.mkdir(parents=True, exist_ok=True)
        DEST.write_text(text, encoding="utf-8")
    lines = text.splitlines()
    return text, lines


def gold_empty_shell(seq: int) -> bool:
    card = ROOT / f"docs/worlds/乱世铜炉-拆文/章卡/{seq}.md"
    if not card.exists():
        return False
    t = card.read_text(encoding="utf-8")
    return "正文几乎没有" in t


def map_chapters(rows: list[dict], lines: list[str]) -> list[dict]:
    # fill 依稀故人（补）
    for i, ln in enumerate(lines):
        if "依稀故人" in ln and "补" in compact(ln) and look_like_heading(ln.strip()):
            ALIASES[212] = i
            break

    mapped: list[dict] = []
    cursor = 0
    for row in rows:
        start: int | None
        if row["seq"] in ALIASES:
            start = ALIASES[row["seq"]]
        else:
            found = find_heading(lines, title_keys(row["title"]), cursor)
            start = found
        mapped.append({**row, "start": start, "end": None, "matched_title": None, "how": "alias" if row["seq"] in ALIASES else "title"})
        if start is not None:
            mapped[-1]["matched_title"] = lines[start].strip()
            cursor = start + 1

    # Infer 上中下 that share one heading: 38-40 风云, and any still-missing
    # siblings between two matched neighbors, by old-length proportion.
    for i, row in enumerate(mapped):
        if row["start"] is not None:
            continue
        if gold_empty_shell(row["seq"]) or "空壳" in row["note"]:
            continue
        if "补" in row["title"]:
            continue
        prev_i = next((j for j in range(i - 1, -1, -1) if mapped[j]["start"] is not None), None)
        next_i = next((j for j in range(i + 1, len(mapped)) if mapped[j]["start"] is not None), None)
        if prev_i is None or next_i is None:
            continue
        # only infer inside a run that starts at prev and ends before next
        run = mapped[prev_i:next_i]
        if not all(r["start"] is None or r is mapped[prev_i] for r in run[1:]):
            # mixed; skip
            pass
        span_start = mapped[prev_i]["start"]
        span_end = mapped[next_i]["start"]
        old_total = sum(r["old_end"] - r["old_start"] + 1 for r in run)
        if old_total <= 0:
            continue
        acc = 0
        for r in run:
            length = r["old_end"] - r["old_start"] + 1
            r["start"] = span_start + int(round(acc * (span_end - span_start) / old_total))
            r["how"] = "proportion" if r is not mapped[prev_i] else r["how"]
            r["matched_title"] = r["matched_title"] or lines[r["start"]].strip()
            acc += length

    for row in mapped:
        if row["start"] is None:
            continue
        later = [r["start"] for r in mapped if r["start"] is not None and r["start"] > row["start"]]
        row["end"] = (min(later) - 1) if later else (len(lines) - 1)
    # Gold 213 is 闻风而动（上）; 母本后面还有（下）和未完待续，不并进上。
    wind = next((i for i, ln in enumerate(lines) if "闻风而动" in ln and "下" in compact(ln) and look_like_heading(ln.strip())), None)
    for row in mapped:
        if row["seq"] == 213 and wind is not None and row["start"] is not None:
            row["end"] = wind - 1

    for row in mapped:
        if row["start"] is not None:
            continue
        row["how"] = "empty_shell" if (gold_empty_shell(row["seq"]) or "空壳" in row["note"]) else "missing_heading"
        nxt = next((r["start"] for r in mapped if r["seq"] > row["seq"] and r.get("start") is not None), None)
        row["start"] = nxt if nxt is not None else len(lines)
        row["end"] = row["start"] - 1
        row["matched_title"] = ""

    out = []
    for row in mapped:
        span_empty = row["end"] < row["start"]
        claimed_empty = gold_empty_shell(row["seq"]) or "空壳" in row["note"]
        length = (row["end"] - row["start"] + 1) if not span_empty else 0
        if span_empty:
            skip = "empty_shell"
        elif claimed_empty and length >= 20:
            skip = "source_gold_mismatch"
        else:
            skip = None
        out.append(
            {
                "seq": row["seq"],
                "volume": row["volume"],
                "title": row["title"],
                "old_start": row["old_start"],
                "old_end": row["old_end"],
                "start": row["start"],
                "end": row["end"],
                "matched_title": row["matched_title"],
                "how": row["how"],
                "gold_empty_shell": claimed_empty,
                "span_empty": span_empty,
                "r1_skip_reason": skip,
            }
        )
    return out


def spotcheck_quotes(text: str) -> list[dict]:
    checks = [
        (5, "夜幕渐落。客人们却还迟迟没有散去。"),
        (89, "但在时闻盂眼中，看到却是完全两样的景象"),
        (110, "许了六两银子酬金"),
        (260, "纯当是社戏里武生演武了"),
        (827, "正是宋雍熙元年"),
        (8110, "北宋，雍熙三年。"),
        (14273, "已经叫了二十一声"),
        (18355, "从她的手指间隙慢慢蠕动出来"),
        (20231, "茶中有蛊"),
        (22045, "除非自保"),
        (25156, "淳化二年冬"),
        (35538, "好好亲近亲近"),
        (8008, "崎岖的山道上"),
        (7906, "便也同意了秦苏的建议"),
        (35504, "酒壶堕地"),
        (18264, "刀却突然停住了"),
        (34146, "向着单嫣后脑"),
        (244, "不过，村长，这酬劳嘛"),
        (13033, "阵法完了"),
        (14032, "你要爹爹还是要皮影儿"),
    ]
    out = []
    for old_l, q in checks:
        locs = []
        start = 0
        while True:
            p = text.find(q, start)
            if p < 0:
                break
            locs.append(text[:p].count("\n") + 1)
            start = p + 1
        out.append({"old_L": old_l, "quote": q, "new_lines": locs, "hit": bool(locs)})
    return out


def build_holdout(rows: list[dict], nlines: int, source_sha: str) -> dict:
    rng = random.Random(HOLDOUT_SEED)
    all_seq = [r["seq"] for r in rows]
    holdout = sorted(rng.sample(all_seq, HOLDOUT_N))
    dev = sorted(set(all_seq) - set(holdout))
    return {
        "seed": HOLDOUT_SEED,
        "n_total": len(all_seq),
        "n_holdout": len(holdout),
        "n_dev": len(dev),
        "source_path": "docs/worlds/乱世铜炉-全文.md",
        "source_lines": nlines,
        "source_sha256": source_sha,
        "holdout": holdout,
        "dev": dev,
    }


def main() -> None:
    text, lines = load_source()
    rows = parse_index()
    chapters = map_chapters(rows, lines)
    source_sha = hashlib.sha256(DEST.read_bytes()).hexdigest()
    holdout_path = EVAL / "holdout.json"
    if holdout_path.exists():
        holdout_blob = holdout_path.read_text(encoding="utf-8")
        holdout = json.loads(holdout_blob)
        if holdout.get("seed") != HOLDOUT_SEED or not holdout.get("holdout"):
            raise SystemExit("holdout.json 已存在但种子不对，拒绝改写")
        if holdout_blob[-1] != "\n":
            holdout_blob += "\n"
    else:
        holdout = build_holdout(rows, len(lines), source_sha)
        holdout_blob = json.dumps(holdout, ensure_ascii=False, indent=2) + "\n"
        holdout_path.write_text(holdout_blob, encoding="utf-8")
    (EVAL / "holdout.sha256").write_text(
        hashlib.sha256(holdout_blob.encode()).hexdigest() + "\n", encoding="utf-8"
    )

    holdout_set = set(holdout["holdout"])
    for ch in chapters:
        ch["split"] = "holdout" if ch["seq"] in holdout_set else "dev"

    missed = [c["seq"] for c in chapters if c["start"] is None]
    (EVAL / "chapters.json").write_text(
        json.dumps(
            {
                "source_lines": len(lines),
                "source_sha256": source_sha,
                "chapters": chapters,
                "missed": missed,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    spots = spotcheck_quotes(text)
    (EVAL / "citation_spotcheck.json").write_text(
        json.dumps(spots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    hits = sum(1 for s in spots if s["hit"])
    print(f"chapters={len(chapters)} missed={missed} quotes={hits}/{len(spots)}")
    print("holdout sha256", hashlib.sha256(holdout_blob.encode()).hexdigest())


if __name__ == "__main__":
    main()

"""《诡秘之主》章界 / 探针集。评测只读。禁止把全文入库。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent
INDEX = ROOT / "docs/worlds/诡秘之主-拆文/00-index.md"
GOLD_DIR = ROOT / "docs/worlds/诡秘之主-拆文/章卡"
SOURCE = ROOT / "docs/worlds/诡秘之主-全文.md"
PROBE_SEED = 20260826
PROBE_N = 20

_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|",
    re.M,
)


def parse_index(text: str | None = None) -> list[dict]:
    raw = INDEX.read_text(encoding="utf-8") if text is None else text
    rows = []
    for m in _ROW.finditer(raw):
        rows.append(
            {
                "seq": int(m.group(1)),
                "start": int(m.group(2)),
                "end": int(m.group(3)),
                "volume": m.group(4).strip(),
                "title": m.group(5).strip(),
            }
        )
    return rows


def chapters_doc() -> dict:
    return json.loads((EVAL / "chapters_lotm.json").read_text(encoding="utf-8"))


def chapter_meta(seq: int) -> dict:
    return next(c for c in chapters_doc()["chapters"] if c["seq"] == seq)


def load_source_slice(seq: int) -> str:
    meta = chapter_meta(seq)
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    start, end = meta["start"], meta["end"]  # 1-based inclusive
    return "\n".join(lines[start - 1 : end])


def load_gold_card(seq: int) -> str:
    return (GOLD_DIR / f"{seq}.md").read_text(encoding="utf-8")


def probe_blob() -> bytes:
    data = (EVAL / "probe_lotm.json").read_bytes()
    if not data.endswith(b"\n"):
        data += b"\n"
    return data


def probe_sha256() -> str:
    return hashlib.sha256(probe_blob()).hexdigest()


def verify_probe_hash() -> str:
    expected = (EVAL / "probe_lotm.sha256").read_text(encoding="utf-8").strip()
    got = probe_sha256()
    if got != expected:
        raise RuntimeError(f"probe_lotm.json hash drifted: {got} != {expected}")
    return got


def probe_seqs() -> list[int]:
    verify_probe_hash()
    return list(json.loads((EVAL / "probe_lotm.json").read_text(encoding="utf-8"))["probe"])


def pick_mixed_fewshot(*, exclude: int, book: str) -> str | None:
    """Dev cards from both books. Never holdout 铜炉, never LOTM probe."""
    from scribe3.eval.extract_card import parse_card

    holdout = set(json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"])
    probe = set(json.loads((EVAL / "probe_lotm.json").read_text(encoding="utf-8"))["probe"])
    tonglu_gold = ROOT / "docs/worlds/乱世铜炉-拆文/章卡"
    candidates: list[tuple[int, str, Path]] = []
    for seq in range(214):
        if seq in holdout:
            continue
        if book == "tonglu" and seq == exclude:
            continue
        path = tonglu_gold / f"{seq}.md"
        if path.exists():
            candidates.append((seq, "tonglu", path))
    for seq in range(1394):
        if seq in probe:
            continue
        if book == "lotm" and seq == exclude:
            continue
        path = GOLD_DIR / f"{seq}.md"
        if path.exists():
            candidates.append((seq, "lotm", path))
    fallback = None
    for seq, _src, path in candidates:
        text = path.read_text(encoding="utf-8")
        if fallback is None:
            fallback = text
        ob = parse_card(text).get("打开书", "")
        if "读完" in ob and len(ob) >= 400:
            return text[:8000]
    return None if fallback is None else fallback[:8000]

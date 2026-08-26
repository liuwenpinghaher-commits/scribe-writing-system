"""Author preference pairs — the only asset in this loop that compounds.

Four rounds of mechanical gates produced three rounds of gaming; the author's
verdict was right every time. So we stop encoding rules and start recording
judgements: each round keeps the draft the author picked, the one they rejected,
and *why*, in their words.

Downstream this feeds two things that actually move a model: long in-context
exemplars drawn from `chosen`, and, once there is enough of it, SFT/DPO data.
Nothing here is a gate.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date as _date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFS_DIR = ROOT / "docs/craft-prefs"
PREFS_FILE = PREFS_DIR / "prefs.jsonl"

# 批注必须具体到能照着改。「不好」「一般」「不行」这类不收。
MIN_NOTE_CHARS = 8
_VAGUE = frozenset({"不好", "一般", "不行", "差", "凑合", "还行", "没感觉"})


@dataclass
class Pref:
    id: str
    round: str
    premise_id: str
    genre: str
    chosen: str
    rejected: str
    notes: list[str] = field(default_factory=list)
    author: str = "作者"
    date: str = ""

    def __post_init__(self) -> None:
        if not self.date:
            self.date = _date.today().isoformat()


def validate_pref(row: dict, *, check_files: bool = True) -> None:
    for k in ("id", "round", "premise_id", "genre", "chosen", "rejected", "notes"):
        if not row.get(k):
            raise ValueError(f"pref missing {k}")
    if row["chosen"] == row["rejected"]:
        raise ValueError(f"chosen == rejected in {row['id']}")
    notes = row["notes"]
    if not isinstance(notes, list) or not notes:
        raise ValueError(f"notes empty in {row['id']}")
    for nt in notes:
        s = (nt or "").strip()
        if len(s) < MIN_NOTE_CHARS or s in _VAGUE:
            raise ValueError(f"note too vague in {row['id']}: {nt!r}")
    if check_files:
        for k in ("chosen", "rejected"):
            if not (ROOT / row[k]).exists():
                raise ValueError(f"{k} not found: {row[k]}")


def load_prefs(path: Path | None = None) -> list[dict]:
    f = path or PREFS_FILE
    if not f.exists():
        return []
    rows = [json.loads(ln) for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for r in rows:
        validate_pref(r, check_files=False)
    return rows


def append_pref(pref: Pref | dict, path: Path | None = None, *, check_files: bool = True) -> dict:
    row = asdict(pref) if isinstance(pref, Pref) else dict(pref)
    validate_pref(row, check_files=check_files)
    f = path or PREFS_FILE
    if any(r["id"] == row["id"] for r in load_prefs(f)):
        raise ValueError(f"duplicate pref id {row['id']}")
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def next_id(path: Path | None = None) -> str:
    return f"pref-{len(load_prefs(path)) + 1:04d}"


def chosen_texts(path: Path | None = None) -> list[str]:
    """作者选中的稿子，用作 in-context 示范池。"""
    out = []
    for r in load_prefs(path):
        p = ROOT / r["chosen"]
        if p.exists():
            out.append(p.read_text(encoding="utf-8"))
    return out

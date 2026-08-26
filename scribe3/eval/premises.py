"""External premises. The model does not invent the situation."""
from __future__ import annotations

import json
import random
from pathlib import Path

from scribe3.eval.motif_split import BLACKLIST_TERMS

EVAL = Path(__file__).resolve().parent
PREMISES_PATH = EVAL / "premises.json"

FLOW_WORDS: tuple[str, ...] = ("盘点", "对账", "例会", "清点", "流程")

REQUIRED = ("id", "genre", "person", "event", "fear", "cast", "info_gap")
PERSON_REQUIRED = ("name", "age", "job", "cares")
CAST_REQUIRED = ("name", "jargon", "speech_habit", "tic", "catchphrase", "never_says")
LEN_BANDS = ("惜字", "中等", "啰嗦")  # 退役，仅留给旧数据读取


def load_premises() -> list[dict]:
    doc = json.loads(PREMISES_PATH.read_text(encoding="utf-8"))
    return list(doc["premises"])


def validate_premise(row: dict) -> None:
    for k in REQUIRED:
        if k not in row or row[k] in ("", None):
            raise ValueError(f"premise missing {k}")
    person = row["person"]
    for k in PERSON_REQUIRED:
        if k not in person or person[k] in ("", None):
            raise ValueError(f"person missing {k}")
    blob = json.dumps(row, ensure_ascii=False)
    for t in BLACKLIST_TERMS:
        if t in blob:
            raise ValueError(f"blacklist {t} in premise {row['id']}")
    for w in FLOW_WORDS:
        if w in row["event"]:
            raise ValueError(f"flow word {w} in event {row['id']}")
    cast = row["cast"]
    if len(cast) < 3:
        raise ValueError(f"cast < 3 in {row['id']}")
    bands = []
    for c in cast:
        for k in CAST_REQUIRED:
            if not c.get(k):
                raise ValueError(f"cast missing {k} in {row['id']}")
        if len(c["jargon"]) < 5:
            raise ValueError(f"jargon < 5 in {row['id']} {c['name']}")
        bands.append(c["speech_habit"])
    # 档位标签（惜字/中等/啰嗦）已退役：模型会把它直接执行成句长，三个角色
    # 一起坍缩成同一个模子。改为各写各的行为，只要求彼此不同。
    if len(set(bands)) != len(bands):
        raise ValueError(f"speech_habit not unique in {row['id']}")
    tics = [c["tic"] for c in cast]
    if len(set(tics)) != len(tics):
        raise ValueError(f"tic not unique in {row['id']}")
    gap = row["info_gap"]
    for k in ("knows", "does_not_know", "hides"):
        if not gap.get(k):
            raise ValueError(f"info_gap missing {k} in {row['id']}")


def draw_premises(n: int = 3, seed: int = 20260826, exclude: tuple[str, ...] = ()) -> list[dict]:
    rows = load_premises()
    for r in rows:
        validate_premise(r)
    banned = set(exclude)
    rng = random.Random(seed)
    order = [r for r in rows if r["id"] not in banned]
    rng.shuffle(order)
    picked: list[dict] = []
    seen_genre: set[str] = set()
    for row in order:
        if row["genre"] in seen_genre:
            continue
        picked.append(row)
        seen_genre.add(row["genre"])
        if len(picked) >= n:
            break
    if len(picked) < n:
        raise RuntimeError("not enough distinct genres")
    return picked

"""章纲 13 槽 SSOT（chapter_spine.v1）。纯函数，零 I/O。

禁止占用 chapter_brief / GET /chapter-brief。
"""
from __future__ import annotations

import re
from typing import Any

from scribe3.narrative_contract import _PLACEHOLDERS, cn_len, cn_strip

SCHEMA = "chapter_spine.v1"

SPINE_SLOTS: tuple[str, ...] = (
    "setting", "cast", "bite", "goal", "obstacle", "inciting",
    "escalation", "choice", "decision", "cost", "info_gap", "lines",
    "hook", "forbid",
)
# 仅作长槽拆句的启发式，不再当落库硬顶。完整一句不因字数作废。
SLOT_MAX_CN = 40
REQUIRED_CORE = ("goal", "obstacle", "inciting", "escalation", "choice", "decision", "cost")
REQUIRED_TAIL = ("info_gap", "lines", "hook")
ASSEMBLED_SYNOPSIS_CAP = 400

SLOT_LABELS: dict[str, str] = {
    "setting": "时空",
    "cast": "在场",
    "bite": "咬上章",
    "goal": "本章要",
    "obstacle": "挡",
    "inciting": "触发",
    "escalation": "升级",
    "choice": "选择",
    "decision": "决断",
    "cost": "代价",
    "info_gap": "信息差",
    "lines": "动哪条线",
    "hook": "钩",
    "forbid": "禁令",
}
LABEL_TO_SLOT = {v: k for k, v in SLOT_LABELS.items()}
LABEL_TO_SLOT["要"] = "goal"
LABEL_TO_SLOT["本章欲望"] = "goal"
LABEL_TO_SLOT["对立"] = "obstacle"
LABEL_TO_SLOT["阻力"] = "obstacle"
LABEL_TO_SLOT["结果"] = "cost"
LABEL_TO_SLOT["代价/结果"] = "cost"
LABEL_TO_SLOT["钩/禁令"] = "hook"

# 不再为某本旧书写死锁。作者点锁走 chapter.prose_lock。
FROZEN_PROSE_CHAPTERS: frozenset[tuple[str, int]] = frozenset()

_LINE_RE = re.compile(
    r"^(?:promise|storyline):(?P<id>[^\s]+)(?:\s+(?P<delta>.+))?$",
    re.I,
)


def slot_text(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        bits = []
        for it in val:
            if isinstance(it, dict):
                bits.append(str(it.get("delta") or it.get("id") or "").strip())
            else:
                bits.append(str(it or "").strip())
        return "；".join(x for x in bits if x)
    if isinstance(val, dict):
        return str(val.get("delta") or val.get("id") or val.get("text") or "").strip()
    return str(val).strip()


def is_prose_locked(work: str, seq: int, ch: dict | None = None) -> bool:
    if (str(work or ""), int(seq)) in FROZEN_PROSE_CHAPTERS:
        return True
    return bool((ch or {}).get("prose_lock"))


def normalize_choice(raw: Any) -> str:
    t = cn_strip(raw)
    if not t or t in _PLACEHOLDERS or t in ("无", "没有", "无选择", "暂无选择"):
        return ""
    return str(raw or "").strip()


def parse_choice_ab(raw: Any) -> tuple[str, str] | None:
    text = normalize_choice(raw)
    if not text:
        return None
    for sep in (" vs ", " VS ", "vs", " / ", "／", "还是", "要么", "对", "或"):
        if sep == "要么":
            m = re.split(r"要么|要麼", text)
            if len(m) >= 3:
                a, b = m[1].strip(" ，,：:"), m[2].strip(" ，,：:")
                if a and b:
                    return a, b
            continue
        if sep in text:
            left, right = text.split(sep, 1)
            a, b = left.strip(" ，,：:"), right.strip(" ，,：:")
            if a and b:
                return a, b
    return None


def normalize_bound_lines(raw: Any) -> list[dict[str, str]]:
    items: list = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str) and raw.strip():
        for part in re.split(r"[；;\n]+", raw.strip()):
            part = part.strip()
            if part:
                items.append(part)
    out: list[dict[str, str]] = []
    for it in items:
        if isinstance(it, dict):
            kind = str(it.get("kind") or "").strip().lower()
            pid = str(it.get("id") or "").strip()
            delta = str(it.get("delta") or "").strip()
            if kind in ("promise", "storyline") and pid:
                out.append({"kind": kind, "id": pid, "delta": delta})
            continue
        s = str(it or "").strip()
        m = _LINE_RE.match(s)
        if not m:
            continue
        kind = "promise" if s.lower().startswith("promise:") else "storyline"
        out.append({"kind": kind, "id": m.group("id").strip(), "delta": (m.group("delta") or "").strip()})
    return out


def empty_spine() -> dict[str, Any]:
    row = {k: "" for k in SPINE_SLOTS}
    row["schema"] = SCHEMA
    row["lines"] = []
    return row


def coerce_spine(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str) and raw.strip():
        import json
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            raw = {}
    if not isinstance(raw, dict):
        return empty_spine()
    out = empty_spine()
    for k in SPINE_SLOTS:
        if k == "lines":
            out[k] = normalize_bound_lines(raw.get(k))
        elif k == "choice":
            out[k] = normalize_choice(raw.get(k))
        else:
            out[k] = slot_text(raw.get(k))[:200]
    if raw.get("schema"):
        out["schema"] = str(raw.get("schema"))
    return out


def assemble_synopsis_from_spine(spine: dict | None) -> str:
    src = coerce_spine(spine)
    lines = []
    for k in SPINE_SLOTS:
        if k == "forbid" and not slot_text(src.get(k)):
            continue
        label = SLOT_LABELS[k]
        body = slot_text(src.get(k))
        if k == "lines":
            bits = []
            for it in src.get("lines") or []:
                bits.append(f"{it.get('kind')}:{it.get('id')} {it.get('delta') or ''}".strip())
            body = "；".join(bits)
        if not body:
            continue
        lines.append(f"{label}：{body}")
    text = "\n".join(lines)
    if cn_len(text) > ASSEMBLED_SYNOPSIS_CAP:
        # 按行裁到帽
        kept: list[str] = []
        n = 0
        for ln in lines:
            add = cn_len(ln)
            if n + add > ASSEMBLED_SYNOPSIS_CAP:
                break
            kept.append(ln)
            n += add
        text = "\n".join(kept)
    return text


def assemble_beat_text(beat: dict | None) -> str:
    b = beat if isinstance(beat, dict) else {}
    parts = []
    for key, lab in (("goal", "要"), ("conflict", "挡"), ("turn", "变"),
                     ("choice", "选"), ("cost", "付"), ("underwater", "水下")):
        val = normalize_choice(b.get(key)) if key == "choice" else slot_text(b.get(key))
        if val:
            parts.append(f"{lab}：{val}")
    return "\n".join(parts)


_LABEL_LINE = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?(?P<lab>时空|在场|咬上章|本章要|本章欲望|要|挡|对立|阻力|"
    r"触发|升级|选择|决断|代价|代价/结果|结果|信息差|动哪条线|钩|禁令|钩/禁令)\s*[：:]\s*"
    r"(?P<body>.*?)(?=\n\s*(?:#{1,3}\s*)?(?:时空|在场|咬上章|本章要|本章欲望|要|挡|对立|"
    r"阻力|触发|升级|选择|决断|代价|代价/结果|结果|信息差|动哪条线|钩|禁令|钩/禁令)\s*[：:]|\Z)",
    re.S,
)


def parse_spine_labels(text: str) -> dict[str, Any]:
    """从中文标签行抽出 spine。够 4–13 必填才算 13 槽新稿。"""
    out = empty_spine()
    for m in _LABEL_LINE.finditer(text or ""):
        lab = re.sub(r"\s+", "", m.group("lab"))
        key = LABEL_TO_SLOT.get(lab)
        if not key:
            continue
        body = (m.group("body") or "").strip()
        if key == "lines":
            out[key] = normalize_bound_lines(body)
        elif key == "choice":
            out[key] = normalize_choice(body)
        else:
            out[key] = body.split("\n", 1)[0].strip()
    filled = sum(1 for k in REQUIRED_CORE + REQUIRED_TAIL if slot_text(out.get(k)))
    out["_filled"] = filled
    out["_source"] = "llm_13slot" if filled >= 8 else ""
    return out


def looks_like_13slot(text: str) -> bool:
    got = parse_spine_labels(text)
    return int(got.get("_filled") or 0) >= 8


MUST_LAND_KEYS: tuple[tuple[str, str], ...] = (
    ("choice", "选择"),
    ("decision", "决断"),
    ("cost", "代价"),
    ("info_gap", "信息差"),
    ("forbid", "禁令"),
    ("hook", "钩"),
    ("bite", "咬上章"),
    ("lines", "动哪条线"),
)


def format_must_land(
    spine: dict | None,
    ore: list | None = None,
    chapter: dict | None = None,
) -> str:
    """下游必须兑现的短原子清单。无槽则空串。ore 缺省时 load_ore(chapter)。"""
    src = coerce_spine(spine) if spine else empty_spine()
    lines: list[str] = []
    for k, lab in MUST_LAND_KEYS:
        if k == "lines":
            bits = []
            for it in src.get("lines") or []:
                bits.append(
                    f"{it.get('kind')}:{it.get('id')} {it.get('delta') or ''}".strip()
                )
            body = "；".join(bits)
        else:
            body = slot_text(src.get(k))
            if k == "choice" and isinstance(chapter, dict):
                meta = chapter.get("beats_meta") if isinstance(chapter.get("beats_meta"), dict) else {}
                staged = str((meta or {}).get("staged_choice") or "").strip()
                if staged:
                    body = staged
        if body:
            lines.append(f"{lab}：{body}")
    try:
        from scribe3.fate_dearer import load_clock, load_ore, load_place, load_world_fact
        ch = chapter if isinstance(chapter, dict) else {}
        atoms = ore if ore is not None else load_ore(ch)
        clock = load_clock(ch)
        place = load_place(ch)
        fact = load_world_fact(ch)
        if clock.get("span"):
            lines.append(f"时长：{clock.get('span')} · delta={clock.get('delta')}")
        if place.get("name"):
            lines.append(f"地点：{place.get('name')} · delta={place.get('delta')}")
        if fact.get("text"):
            lines.append(f"世界事实：{fact.get('text')}")
        if atoms:
            bits = [str(x.get("atom") or "")[:20] for x in atoms if isinstance(x, dict)]
            bits = [b for b in bits if b]
            if bits:
                lines.append("矿：" + "；".join(bits))
    except Exception:
        pass
    if not lines:
        return ""
    return (
        "【必须落地】下面这些短原子必须在下一层出现，禁止只写巷/门/烟：\n"
        + "\n".join(lines)
        + "\n兑现选择与代价；信息差进「知道/没察觉」；禁令不得说出口；钩须在章末仍悬着。"
    )


_PROSE_LABEL_HEAD = re.compile(
    r"^(?:时空|在场|咬上章|本章要|挡|触发|升级|选择|决断|代价|信息差|"
    r"动哪条线|钩|禁令|时长|增量|地点|地点增量|世界事实)\s*[：:]"
)


def strip_spine_labels_from_prose(text: str) -> str:
    """剥正文开头连续标签行，避免 extra『必须以时空：开头』漏进读者层。"""
    lines = (text or "").splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if _PROSE_LABEL_HEAD.match(s):
            i += 1
            continue
        break
    return "\n".join(lines[i:]).lstrip()


def is_v1(raw: Any) -> bool:
    if not isinstance(raw, dict) and not (isinstance(raw, str) and raw.strip().startswith("{")):
        return False
    d = coerce_spine(raw)
    if d.get("schema") != SCHEMA:
        # 允许漏写 schema：有核心槽即视为 v1
        if not any(slot_text(d.get(k)) for k in REQUIRED_CORE):
            return False
    return any(slot_text(d.get(k)) for k in REQUIRED_CORE)


def load_chapter_spine(ch: dict | None) -> dict[str, Any]:
    """有 v1 则返回。无 spine 返回空槽，禁止用肥 synopsis 冒充章纲。"""
    src = ch if isinstance(ch, dict) else {}
    raw = src.get("chapter_spine")
    if is_v1(raw):
        return coerce_spine(raw)
    return empty_spine()


def known_line_ids_from_store(st: Any) -> set[tuple[str, str]]:
    """本书已有 promise / storyline id。st 空则空集。"""
    out: set[tuple[str, str]] = set()
    if st is None:
        return out
    try:
        for p in (st.list_promises() or []):
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id") or "").strip()
            if pid:
                out.add(("promise", pid))
    except Exception:
        pass
    try:
        for row in (st.list_storylines() or []):
            if not isinstance(row, dict):
                continue
            sid = str(row.get("id") or "").strip()
            if sid:
                out.add(("storyline", sid))
    except Exception:
        pass
    return out


def filter_brief_only_fields(
    fields: dict | None,
    existing: dict | None = None,
) -> dict[str, Any]:
    """brief_only：只留 chapter_spine；空四仪才投影。禁止 synopsis/beats/prose。"""
    src = fields if isinstance(fields, dict) else {}
    keep: dict[str, Any] = {}
    if src.get("chapter_spine"):
        keep["chapter_spine"] = src["chapter_spine"]
    prev = (existing or {}).get("narrative_contract") or {}
    if isinstance(prev, str) and prev.strip():
        import json
        try:
            prev = json.loads(prev)
        except (TypeError, ValueError):
            prev = {}
    if not isinstance(prev, dict):
        prev = {}
    empty_prev = not any(str(prev.get(k) or "").strip() for k in ("desire", "obstacle", "turn", "cost"))
    if empty_prev and src.get("narrative_contract"):
        keep["narrative_contract"] = src["narrative_contract"]
    incoming_bm = src.get("beats_meta")
    if isinstance(incoming_bm, dict):
        prev_bm = (existing or {}).get("beats_meta")
        if not isinstance(prev_bm, dict):
            prev_bm = {}
        bm = dict(prev_bm)
        for k in ("clock", "place"):
            if incoming_bm.get(k):
                bm[k] = incoming_bm[k]
        # ore/seeds 禁止走 brief_only 覆盖；保留已有
        if bm:
            keep["beats_meta"] = bm
    return keep

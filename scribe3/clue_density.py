"""线索密度闸：纯函数，零 I/O。不验字数面积。"""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from scribe3.chapter_spine import (
    REQUIRED_CORE,
    REQUIRED_TAIL,
    SLOT_MAX_CN,
    SPINE_SLOTS,
    coerce_spine,
    normalize_bound_lines,
    normalize_choice,
    parse_choice_ab,
    slot_text,
)
from scribe3.drama_beats import TURN_COST_LEX
from scribe3.iceberg_leak import ICEBERG_LEAK_WORDS
from scribe3.narrative_contract import CONFLICT_LEX, cn_len, cn_strip
from scribe3.narrative_drive import _CONFLICT_LEX as DRIVE_CONFLICT_LEX

_EXTRA_ACTION = (
    "拨", "交", "勾", "咳", "还", "塞", "推", "揭", "挡", "讨",
    "举", "认", "开", "关", "埋", "兑",
    "按", "撕", "报", "熔", "锁",
)
_OBJECT_NEAR = (
    "铜", "焦", "账", "门", "角", "声", "爹", "匙", "纸", "灰", "债", "名",
    "核", "裂", "权", "海", "箱", "腕", "令", "罩", "泡", "锚", "度",
)
# 万界整词：揭开大遮蔽 / 观测伪真空 必须过闸，不必借「帘+角」。
WORLD_VERB = ("观测", "坍缩", "成核", "锚定", "冗余", "退相干", "烛照")
WORLD_PHRASE = (
    "大遮蔽", "成核点", "相位锚", "伪真空", "真真空", "指针态",
    "场核", "逻辑豁免", "融合点", "金縢",
)
_SINGLE_NEED_NEAR = frozenset({"还", "咳", "交", "开", "关"})

COST_CONSEQ_LEX = (
    "暴露", "未兑", "更死", "更险", "亏", "伤", "代价", "没开",
    "锁死", "被迫", "两难", "空过", "收不回", "清了",
)
SENSORY_PAD = (
    "烟", "青苔", "檐口", "指腹", "空气里", "温凉", "巷口风",
    "锅沿", "灰星", "气味",
)
_WALK_ONLY = ("走了", "站着", "看着", "蹲着")

WORKING_MIN_ATOMS = 6
WORKING_MIN_DENSITY = 0.45  # 金样 G1 校准；0.55 会误杀短干章纲
WORKING_MAX_PADDING = 0.25
WORKING_BEAT_MIN_ATOMS = 8


def _union_action_lex() -> tuple[str, ...]:
    bag = set(CONFLICT_LEX) | set(DRIVE_CONFLICT_LEX) | set(TURN_COST_LEX) | set(_EXTRA_ACTION)
    return tuple(sorted(bag, key=len, reverse=True))


ACTION_LEX = _union_action_lex()


def split_sents(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[。！？\n；;]", text or "") if str(s).strip()]


def split_sents_slotwise(spine: dict) -> list[str]:
    out: list[str] = []
    for k in SPINE_SLOTS:
        body = slot_text(spine.get(k))
        if not body:
            continue
        parts = split_sents(body)
        if not parts:
            out.append(body)
        elif cn_len(body) <= SLOT_MAX_CN + 8:
            out.append(body)
        else:
            out.extend(parts)
    return out


def names_from_cast(spine: dict | None, extras: list[str] | None = None) -> list[str]:
    blob = slot_text((spine or {}).get("cast"))
    names = [p.strip() for p in re.split(r"[、，,；;\s/]+", blob) if p.strip()]
    for e in extras or []:
        if e and e not in names:
            names.append(str(e))
    aliases = {
        "覃灰七": "灰七", "冷锅婆": "婆子", "灰狸": "狸",
    }
    extra: list[str] = []
    for n in names:
        if n in aliases:
            extra.append(aliases[n])
        for k, v in aliases.items():
            if n == v:
                extra.append(k)
    return names + extra


def _has_who(sent: str, names: list[str], prev_had_name: bool) -> bool:
    if any(n and n in sent for n in names):
        return True
    if any(n in sent for n in (
        "灰七", "婆子", "灰狸", "冷锅婆", "覃灰七",
        "柳岸青", "沈烛", "赫斯", "兰因",
    )):
        return True
    if prev_had_name and ("他" in sent or "她" in sent):
        return True
    return False


def _action_hit(sent: str) -> str:
    for w in WORLD_VERB:
        if w in sent:
            return w
    for w in ACTION_LEX:
        if w not in sent:
            continue
        if w in _SINGLE_NEED_NEAR:
            i = sent.find(w)
            window = sent[max(0, i - 2): i + len(w) + 3]
            if not any(o in window for o in _OBJECT_NEAR) and not any(
                p in sent for p in WORLD_PHRASE
            ):
                continue
        return w
    return ""


def _has_object_or_cost(sent: str) -> bool:
    if any(c in sent for c in COST_CONSEQ_LEX):
        return True
    if any(p in sent for p in WORLD_PHRASE):
        return True
    if any(o in sent for o in _OBJECT_NEAR):
        return True
    return False


def is_atom_field(text: Any, *, cast: list[str] | None = None) -> bool:
    sent = slot_text(text)
    if not sent:
        return False
    if not _action_hit(sent):
        return False
    return _has_object_or_cost(sent)


def _is_padding(sent: str) -> bool:
    if _action_hit(sent) and _has_object_or_cost(sent):
        return False
    if any(w in sent for w in _WALK_ONLY) and not _action_hit(sent):
        return True
    return any(p in sent for p in SENSORY_PAD) and not _action_hit(sent)


def collect_atoms(sents: list[str], *, who_names: list[str]) -> list[str]:
    atoms: list[str] = []
    prev_name = False
    for sent in sents:
        key = cn_strip(sent)
        if any(key and (key in cn_strip(a) or cn_strip(a) in key) for a in atoms):
            continue
        who = _has_who(sent, who_names, prev_name)
        if any(n in sent for n in who_names) or any(n in sent for n in (
            "灰七", "婆子", "灰狸", "冷锅婆",
            "柳岸青", "沈烛", "赫斯",
        )):
            prev_name = True
        extra = (
            ("因" in sent and ("所以" in sent or "必须" in sent))
            or ("不能" in sent or "不得" in sent or "不知" in sent)
            or ("未" in sent and any(o in sent for o in _OBJECT_NEAR))
        )
        if extra and (who or _action_hit(sent) or "不知" in sent or "不能" in sent or "不得" in sent):
            atoms.append(sent)
            continue
        if who and _action_hit(sent) and _has_object_or_cost(sent):
            atoms.append(sent)
    return atoms


@dataclass
class DensityReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    atoms: int = 0
    sentences: int = 0
    density: float = 0.0
    padding: float = 0.0
    missing: list[dict[str, Any]] = field(default_factory=list)

    def as_missing(self) -> list[dict[str, Any]]:
        if self.missing:
            return list(self.missing)
        out = []
        for e in self.errors:
            mid = e.split(":")[0]
            out.append({"id": mid, "detail": e})
        return out

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def chapter_design_mode() -> str:
    """on | off。设置 DB → env → 默认 on。非法 typo → off。"""
    raw = ""
    try:
        from scribe3.settings import get_setting
        raw = str(get_setting("SCRIBE3_CHAPTER_DESIGN") or "").strip().lower()
    except Exception:
        raw = ""
    if not raw:
        raw = str(os.environ.get("SCRIBE3_CHAPTER_DESIGN") or "").strip().lower()
    if raw in ("on", "1", "true", "yes"):
        return "on"
    if raw in ("off", "0", "false", "no"):
        return "off"
    if not raw:
        return "on"
    return "off"


def design_book_mode() -> str:
    """on | off。CHAPTER_DESIGN 关则本旗也关。空→on，typo→off。"""
    if chapter_design_mode() != "on":
        return "off"
    raw = ""
    try:
        from scribe3.settings import get_setting
        raw = str(get_setting("SCRIBE3_DESIGN_BOOK") or "").strip().lower()
    except Exception:
        raw = ""
    if not raw:
        raw = str(os.environ.get("SCRIBE3_DESIGN_BOOK") or "").strip().lower()
    if raw in ("on", "1", "true", "yes"):
        return "on"
    if raw in ("off", "0", "false", "no"):
        return "off"
    if not raw:
        return "on"
    return "off"


@dataclass(frozen=True)
class BindableLine:
    kind: str
    id: str
    text: str


@dataclass(frozen=True)
class DesignBook:
    seq: int = 1
    title: str = ""
    focus_names: tuple[str, ...] = ()
    character_names: frozenset[str] = frozenset()
    item_names: frozenset[str] = frozenset()
    place_names: frozenset[str] = frozenset()
    term_names: frozenset[str] = frozenset()
    bindable_lines: tuple[BindableLine, ...] = ()
    prev_place_name: str = ""
    prev_hook: str = ""
    prev_setting: str = ""
    must_happen: str = ""


_FOCUS_RE = re.compile(r"焦点[:：\s]*([\u4e00-\u9fff]{2,4})")
_MUST_RE = re.compile(r"本章发生[:：]\s*(.+)")
_CAST_PAREN = re.compile(r"[（(][^）)]*[）)]")
_CAST_TAIL = re.compile(r"[。．.！!？?：:]+$")
_CAST_META = re.compile(r"无新造|禁止新造|无对手|无见证|^无$")
_TOPIC_STOP = frozenset({
    "开始", "复制", "他的", "未开", "谁先", "这个", "那个",
    "没有", "一个", "他们", "她们", "自己", "还是", "不是",
    "挂上", "一句", "本章", "推进", "门外", "门里", "一分",
})
_PLACE_SUFFIX = ("伪真空口", "灯亭", "裂口", "边缘")
_TRAVEL_MARK = ("到", "下山", "搬", "运", "换域", "抬往", "送至", "离开", "折返", "走回", "赶回", "步行")
_QTY_PREFIX = ("两个", "一名", "几个", "一位", "两名", "三名")
_MECH_TAIL = frozenset("箱锁核缝灯门库峰亭口锚")
_WIN_SKIP = frozenset("的了在是年月日后前与和把被将从到无")
_LR_MARK = ("左半身", "右半身", "左手", "右手", "左边", "右边", "左", "右")
_FALSE_PREV = ("上章", "上一口", "余烬", "接上")
_CLOCK_PLACE_KEYS = frozenset({
    "place.name", "place.delta", "place.stay_reason",
    "clock.span", "clock.delta", "clock.freeze_reason",
})
_ALLOW_BY_ERR = {
    "cast_invented": frozenset({"cast", "conflict", "goal"}),
    "place_name_mismatch": frozenset({"setting"}),
    "place_travel_unsaid": frozenset({"setting"}),
    "clock_jump_unsaid": frozenset({"setting"}),
    "bite_false_prev": frozenset({"bite"}),
    "bite_off_hook": frozenset({"bite"}),
    "line_delta_empty": frozenset({"lines"}),
    "line_off_topic": frozenset({"lines"}),
    "line_wrong_bind": frozenset({"lines"}),
    "choice_mirror": frozenset({"choice"}),
    "spine_choice": frozenset({"choice"}),
    "choice_not_staged": frozenset({"choice"}),
    "goal_off_must": frozenset({"goal", "choice", "decision"}),
}
DESIGN_BOOK_ERR_IDS = frozenset({
    "cast_invented", "place_name_mismatch", "place_travel_unsaid",
    "clock_jump_unsaid", "bite_false_prev", "bite_off_hook",
    "line_delta_empty", "line_off_topic", "line_wrong_bind", "choice_mirror",
    "goal_off_must", "design_book_missing",
})


def extract_focus_names(extra: str, ch: Any = None) -> tuple[str, ...]:
    out: list[str] = []
    foc = str((ch or {}).get("focalizer") or "").strip() if isinstance(ch, dict) else ""
    if foc.lower().startswith("role:"):
        foc = foc.split(":", 1)[-1]
    if 2 <= cn_len(foc) <= 4:
        out.append(foc)
    for m in _FOCUS_RE.finditer(extra or ""):
        out.append(m.group(1))
    return tuple(dict.fromkeys(out))


def extract_must_happen(extra: str = "", ch: Any = None) -> str:
    """本章必须发生：章上 beats_meta.must_happen，或 extra「本章发生：…」。空则不考。"""
    if isinstance(ch, dict):
        raw = ch.get("must_happen")
        if str(raw or "").strip():
            return str(raw).strip()
        meta = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
        hit = str((meta or {}).get("must_happen") or "").strip()
        if hit:
            return hit
    m = _MUST_RE.search(extra or "")
    if m:
        return str(m.group(1) or "").strip()
    return ""


def _book_proper_grams(book: DesignBook | None, extra_text: str = "") -> set[str]:
    bag: set[str] = set()
    for p in WORLD_PHRASE:
        bag |= _char_ngrams(p, 2)
    if book:
        for name in book.item_names | book.place_names | book.term_names:
            bag |= _char_ngrams(str(name), 2)
        for ln in book.bindable_lines:
            bag |= _char_ngrams(ln.text, 2)
    if extra_text:
        bag |= _char_ngrams(extra_text, 2)
    return bag - _TOPIC_STOP


def topic_grams(text: str, book: DesignBook | None = None, *, line_text: str = "") -> set[str]:
    grams = _char_ngrams(text or "", 2) - _TOPIC_STOP
    proper = _book_proper_grams(book, line_text)
    hit = grams & proper
    return hit if hit else grams


def topics_overlap(a: str, b: str, book: DesignBook | None = None) -> bool:
    return bool(topic_grams(a, book, line_text=b) & topic_grams(b, book, line_text=a))


def place_core(name: str) -> str:
    t = cn_strip(name)[:20]
    for suf in _PLACE_SUFFIX:
        if t.endswith(suf) and len(t) - len(suf) >= 2:
            return t[:-len(suf)]
    return t


def same_landmark(a: str, b: str) -> bool:
    ca, cb = place_core(a), place_core(b)
    if not ca or not cb:
        return False
    short, long_ = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
    if len(short) < 2:
        return False
    return short in long_


def _strip_lr(s: str) -> str:
    t = _ab_norm_side(s)
    for m in _LR_MARK:
        t = t.replace(m, "")
    return cn_strip(t)


def choice_is_mirror(ab: tuple[str, str] | None) -> bool:
    if not ab:
        return False
    a, b = _strip_lr(ab[0]), _strip_lr(ab[1])
    return bool(a) and a == b


def _split_cast_chunks(cast_text: str) -> list[str]:
    # 先去掉括号说明，再切；禁止按 / 切，避免「物件/机制」把「机制）」切成人名。
    text = _CAST_PAREN.sub("", slot_text(cast_text))
    parts = re.split(r"[、，,；;]+", text)
    out: list[str] = []
    for raw in parts:
        p = raw.strip()
        if not p:
            continue
        p = re.sub(r"^(焦点|对手|见证)\s*[=：:]*\s*", "", p).strip()
        p = _CAST_TAIL.sub("", p).strip()
        if _CAST_META.search(p):
            continue
        if p:
            out.append(p)
    return out


def _strip_qty(p: str) -> str:
    for q in _QTY_PREFIX:
        if p.startswith(q):
            return p[len(q):]
    return p


def cast_person_tokens(cast_text: str) -> list[str]:
    """人名启发式：去焦点/对手/见证与数量词；3 字默认当人。"""
    people: list[str] = []
    for chunk in _split_cast_chunks(cast_text):
        p = _strip_qty(chunk)
        n = cn_len(p)
        if n == 3:
            people.append(p)
        elif n in (2, 4):
            people.append(p)
        elif n > 4:
            t = cn_strip(p)
            for i in range(0, max(0, len(t) - 2)):
                people.append(t[i:i + 3])
    return people


def _allow_names(book: DesignBook | None) -> set[str]:
    allow: set[str] = set(WORLD_PHRASE)
    if book:
        allow |= set(book.character_names)
        allow |= set(book.focus_names)
        allow |= set(book.item_names)
        allow |= set(book.place_names)
        allow |= set(book.term_names)
    return {str(x) for x in allow if str(x).strip()}


def _covered_by_allow(token: str, allow: set[str]) -> bool:
    t = cn_strip(token)
    if not t:
        return True
    if t in allow:
        return True
    if any(t == w or w in t or t in w for w in WORLD_PHRASE):
        return True
    for name in allow:
        n = cn_strip(name)
        if cn_len(n) < 2:
            continue
        if t == n or t in n or n in t:
            return True
    return False


def invented_cast_names(cast_text: str, book: DesignBook | None) -> list[str]:
    allow = _allow_names(book)
    invented: list[str] = []
    for chunk in _split_cast_chunks(cast_text):
        p = _strip_qty(chunk)
        if _covered_by_allow(p, allow):
            continue
        n = cn_len(p)
        if n == 3:
            invented.append(p)
        elif n in (2, 4):
            if p and p[-1] in _MECH_TAIL:
                continue
            invented.append(p)
        elif n > 4:
            t = cn_strip(p)
            for i in range(0, max(0, len(t) - 2)):
                tri = t[i:i + 3]
                if _covered_by_allow(tri, allow):
                    continue
                if tri[-1] in _MECH_TAIL:
                    continue
                if any(c in _WIN_SKIP for c in tri):
                    continue
                invented.append(tri)
                break
    return invented


def must_unmet(spine: dict | None, book: DesignBook | None) -> bool:
    """有「必须发生」时，本章要/选择/决断必须兑现那一组两边。空则不考。"""
    if book is None:
        return False
    must = str(book.must_happen or "").strip()
    if not must:
        return False
    src = coerce_spine(spine)
    blob = " ".join((
        slot_text(src.get("goal")),
        slot_text(src.get("choice")),
        slot_text(src.get("decision")),
    ))
    ab = parse_choice_ab(must)
    if ab:
        return not (
            topics_overlap(blob, ab[0], book) and topics_overlap(blob, ab[1], book)
        )
    return not topics_overlap(blob, must, book)


def line_wrong_bind(spine: dict | None, book: DesignBook, bound: list[dict]) -> bool:
    title = str(book.title or "")
    goal = slot_text((spine or {}).get("goal"))
    bound_ids = {(it.get("kind"), it.get("id")) for it in bound}
    bound_texts = [
        ln.text for ln in book.bindable_lines
        if (ln.kind, ln.id) in bound_ids
    ]
    unbound_texts = [
        ln.text for ln in book.bindable_lines
        if (ln.kind, ln.id) not in bound_ids
    ]

    def hits_any(probe: str, texts: list[str]) -> bool:
        return any(topics_overlap(probe, t, book) for t in texts)

    must = str(book.must_happen or "").strip()
    if must:
        return hits_any(must, unbound_texts) and not hits_any(must, bound_texts)
    if title.strip() and hits_any(title, unbound_texts) and not hits_any(title, bound_texts):
        return True
    title_hits_any_line = hits_any(title, [ln.text for ln in book.bindable_lines])
    if not title_hits_any_line and hits_any(goal, unbound_texts) and not hits_any(goal, bound_texts):
        return True
    return False


def design_allow_keys(errors: list[str] | None) -> tuple[set[str] | None, set[str] | None]:
    """(spine/beat keys, clock/place keys). None = 不限制（今日行为）。"""
    spine: set[str] = set()
    meta: set[str] = set()
    hit_book = False
    for e in errors or []:
        mid = str(e).split(":")[0]
        if mid in _ALLOW_BY_ERR:
            hit_book = True
            spine |= set(_ALLOW_BY_ERR[mid])
        if mid.startswith("place_") or mid == "clock_jump_unsaid":
            meta |= set(_CLOCK_PLACE_KEYS)
    if not hit_book and not meta:
        return None, None
    return (spine or None), (meta or None)


def evaluate_design_continuity(
    spine: dict | None,
    *,
    book: DesignBook | None,
    clock: dict | None,
    place: dict | None,
) -> list[str]:
    if design_book_mode() != "on" or book is None:
        return []
    src = coerce_spine(spine)
    errs: list[str] = []
    if invented_cast_names(src.get("cast") or "", book):
        errs.append("cast_invented")
    if place is not None:
        pname = str(place.get("name") or "")
        try:
            pdelta = int(place.get("delta") if place.get("delta") is not None else -1)
        except (TypeError, ValueError):
            pdelta = -1
        prev = book.prev_place_name
        travel_blob = " ".join((
            slot_text(src.get("setting")),
            pname,
            book.prev_setting,
        ))
        traveled = any(m in travel_blob for m in _TRAVEL_MARK)
        if pdelta == 0 and prev and not same_landmark(pname, prev) and not traveled:
            errs.append("place_name_mismatch")
        if pdelta >= 1 and not traveled:
            errs.append("place_travel_unsaid")
    if clock is not None and place is not None:
        try:
            cdelta = int(clock.get("delta") if clock.get("delta") is not None else -1)
        except (TypeError, ValueError):
            cdelta = -1
        if (
            cdelta >= 2
            and book.prev_place_name
            and same_landmark(str(place.get("name") or ""), book.prev_place_name)
            and not str(clock.get("freeze_reason") or "").strip()
            and not str(place.get("stay_reason") or "").strip()
        ):
            errs.append("clock_jump_unsaid")
    bite = slot_text(src.get("bite"))
    if int(book.seq or 1) <= 1:
        if any(m in bite for m in _FALSE_PREV):
            errs.append("bite_false_prev")
    elif book.prev_hook and not topics_overlap(bite, book.prev_hook, book):
        errs.append("bite_off_hook")
    bound = normalize_bound_lines(src.get("lines"))
    if not any(str(it.get("delta") or "").strip() for it in bound):
        errs.append("line_delta_empty")
    else:
        by_id = {(ln.kind, ln.id): ln for ln in book.bindable_lines}
        for it in bound:
            delta = str(it.get("delta") or "").strip()
            if not delta:
                continue
            ln = by_id.get((it.get("kind"), it.get("id")))
            if ln and not topics_overlap(delta, ln.text, book):
                errs.append("line_off_topic")
                break
    if book.bindable_lines and line_wrong_bind(src, book, bound):
        errs.append("line_wrong_bind")
    ab = parse_choice_ab(src.get("choice"))
    if choice_is_mirror(ab):
        errs.append("choice_mirror")
    if must_unmet(src, book):
        errs.append("goal_off_must")
    return errs


def clue_density_mode() -> str:
    """off | shadow | on。非法值当 off。设置 DB → env → 默认 on。"""
    raw = ""
    try:
        from scribe3.settings import get_setting
        raw = str(get_setting("SCRIBE3_CLUE_DENSITY") or "").strip().lower()
    except Exception:
        raw = ""
    if raw in ("on", "1", "true", "yes"):
        return "on"
    if raw == "shadow":
        return "shadow"
    if raw in ("off", "0", "false", "no"):
        return "off"
    if not raw:
        return "on"
    return "off"


def _design_exam() -> bool:
    return chapter_design_mode() == "on"


def _has_content_payload(text: Any) -> bool:
    """本章要 / 代价：有动作+物件，或点名世界机制。"""
    if is_atom_field(text):
        return True
    sent = slot_text(text)
    return bool(sent) and any(p in sent for p in WORLD_PHRASE)


def project_four_ok(spine: dict) -> bool:
    g = slot_text(spine.get("goal"))
    o = slot_text(spine.get("obstacle"))
    t = slot_text(spine.get("escalation") or spine.get("decision"))
    c = slot_text(spine.get("cost"))
    return all(cn_len(x) >= 4 for x in (g, o, t, c))


def evaluate_spine(
    spine: dict | None,
    *,
    known_line_ids: set[tuple[str, str]] | None = None,
    exam: str | None = None,
) -> DensityReport:
    src = coerce_spine(spine)
    errs: list[str] = []
    design = (exam == "design") or (exam is None and _design_exam())
    for k in REQUIRED_CORE + REQUIRED_TAIL:
        body = slot_text(src.get(k))
        if not cn_strip(body):
            errs.append(f"spine_slots:{k}")
    if not parse_choice_ab(src.get("choice")):
        errs.append("spine_choice")
    bound = normalize_bound_lines(src.get("lines"))
    if not bound:
        errs.append("lines_unbound")
    elif known_line_ids is not None:
        if any((it["kind"], it["id"]) not in known_line_ids for it in bound):
            errs.append("lines_unbound")
    sents = split_sents_slotwise(src)
    names = names_from_cast(src)
    atoms = collect_atoms(sents, who_names=names)
    pad = [s for s in sents if _is_padding(s)]
    density = len(atoms) / max(len(sents), 1)
    padding = len(pad) / max(len(sents), 1)
    if padding > WORKING_MAX_PADDING:
        errs.append("spine_padding")
    if not project_four_ok(src):
        errs.append("spine_slots:four")
    if design:
        if slot_text(src.get("goal")) and not _has_content_payload(src.get("goal")):
            errs.append("spine_goal_thin")
        if slot_text(src.get("cost")) and not _has_content_payload(src.get("cost")):
            errs.append("spine_cost_thin")
    else:
        if len(atoms) < WORKING_MIN_ATOMS:
            errs.append("spine_atoms")
        if density < WORKING_MIN_DENSITY:
            errs.append("spine_density")
    missing = []
    seen: set[str] = set()
    for e in errs:
        mid = e.split(":")[0]
        if mid not in seen:
            seen.add(mid)
            missing.append({"id": mid, "detail": e})
    return DensityReport(
        ok=not errs, errors=errs, atoms=len(atoms),
        sentences=len(sents), density=density, padding=padding, missing=missing,
    )


def enter_sentences(text: str | None) -> int:
    raw = text or ""
    n = 0
    for m in re.finditer(r"(?:进场|空气里|烟囱)[^\n。]{0,80}", raw):
        n += 1
    return n


def _beat_blob(b: dict) -> str:
    return " ".join(slot_text(b.get(k)) for k in (
        "goal", "conflict", "turn", "choice", "cost", "underwater", "text",
    ))


_REALIZE_STOP = frozenset({
    "灰七", "灰狸", "婆子", "冷锅婆", "覃灰七", "狸",
    "自己", "门外", "门里", "一分", "还是", "不是",
    "没有", "一个", "这个", "那个", "他们", "她们",
})
_RARE_MARK = (
    "断", "咳", "焦", "假", "账", "匙", "咬合", "暴露",
    "撕", "拔", "揭", "拨", "塞", "推回", "硌",
    "观测", "坍缩", "成核", "锚定", "冗余",
)


def _content_tokens(text: str, *, min_len: int = 2) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in re.findall(r"[\u4e00-\u9fff]{2,6}", text or ""):
        if p in _REALIZE_STOP or p in seen or len(p) < min_len:
            continue
        seen.add(p)
        out.append(p)
    return out


_AB_PREFIX = re.compile(r"^(?:只把|只将|只|把|将|自己|亲自)")
_CHOICE_VERBS = (
    "交", "按", "还", "塞", "推", "揭", "拨", "拔",
    "开", "关", "焊", "锁", "撕", "报", "按回",
)
_VERB_STEM = {"按回": "按"}
_DIR_COMPL = ("出去", "回去", "过来", "起来", "住", "给")
_REFLEX = frozenset({"自", "己", "自己"})
_OBJ_BUCKETS = (frozenset({"核", "碎片", "场核", "成核", "成核点"}),)


def _ab_norm_side(s: str) -> str:
    return _AB_PREFIX.sub("", cn_strip(s))


def _char_ngrams(s: str, n: int = 2) -> set[str]:
    t = cn_strip(s)
    return {t[i:i + n] for i in range(0, max(0, len(t) - n + 1))}


def _verb_stems(s: str) -> set[str]:
    raw = {v for v in _CHOICE_VERBS if v and v in (s or "")}
    return {_VERB_STEM.get(v, v) for v in raw}


def _obj_residue(s: str) -> str:
    t = _ab_norm_side(s)
    for d in _DIR_COMPL:
        t = t.replace(d, "")
    for v in sorted(_CHOICE_VERBS, key=len, reverse=True):
        t = t.replace(v, "")
    t = cn_strip(t)
    if not t or t in _REFLEX or all(c in "自己" for c in t):
        return ""
    return t


def _obj_compatible(a: str, b: str) -> bool:
    ra, rb = _obj_residue(a), _obj_residue(b)
    if ra == rb:
        return True
    if ra and rb:
        if ra in rb or rb in ra:
            return True
        for bucket in _OBJ_BUCKETS:
            if any(x in ra for x in bucket) and any(x in rb for x in bucket):
                return True
    return False


def _side_same(a: str, b: str) -> bool:
    na, nb = _ab_norm_side(a), _ab_norm_side(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    ga, gb = _char_ngrams(na, 2), _char_ngrams(nb, 2)
    if ga and gb and len(ga & gb) >= 2:
        return True
    va, vb = _verb_stems(na), _verb_stems(nb)
    if va and vb and va == vb and _obj_compatible(na, nb):
        return True
    return False


def _ab_same(left: tuple[str, str], right: tuple[str, str]) -> bool:
    a1, b1 = left
    a2, b2 = right
    return (
        (_side_same(a1, a2) and _side_same(b1, b2))
        or (_side_same(a1, b2) and _side_same(b1, a2))
    )


def beats_realize_spine(
    beats: list | None,
    spine: dict | None,
    *,
    designated_beat: int | None = None,
) -> list[str]:
    """同一份稿内：指定拍必须演出章的那一个 A vs B。"""
    if not spine:
        return []
    src = coerce_spine(spine)
    errs: list[str] = []
    ab = parse_choice_ab(src.get("choice"))
    if not ab:
        return []
    staged: list[tuple[int, tuple[str, str]]] = []
    rows = [b for b in (beats or []) if isinstance(b, dict)]
    for i, b in enumerate(rows):
        cab = parse_choice_ab(b.get("choice"))
        if cab:
            staged.append((i, cab))
    if not staged:
        return ["choice_not_staged"]
    n = len(rows)
    want = designated_beat if (
        isinstance(designated_beat, int) and 1 <= designated_beat <= n
    ) else (2 if n >= 2 else 1)
    idx = want - 1
    cab = parse_choice_ab(rows[idx].get("choice")) if 0 <= idx < n else None
    if not cab:
        return errs + ["choice_not_staged"]
    if not _ab_same(cab, ab):
        errs.append("choice_not_staged")
    for i, other in staged:
        if i != idx and not _ab_same(other, ab):
            errs.append("second_choice")
            break
    if chapter_design_mode() == "on":
        # 设计只认选择同源，不再逼拍去抄决断里的稀有切词。
        pass
    else:
        need_src = " ".join(
            slot_text(src.get(k)) for k in ("choice", "decision", "cost", "escalation")
        )
        rare = [
            t for t in _content_tokens(need_src, min_len=2)
            if any(m in t for m in _RARE_MARK)
        ]
        blob = " ".join(
            _beat_blob(b) if isinstance(b, dict) else str(b)
            for b in (beats or [])
        )
        hits = [t for t in rare if t in blob]
        if len(rare) >= 2 and len(hits) < min(2, len(rare)):
            errs.append("beat_off_spine")
    return errs


def evaluate_chapter_design(
    spine: dict | None,
    beats: list | None,
    *,
    known_line_ids: set | None = None,
    designated_beat: int | None = None,
    book: DesignBook | None = None,
    clock: dict | None = None,
    place: dict | None = None,
) -> DensityReport:
    exam = "design" if chapter_design_mode() == "on" else None
    spine_rep = evaluate_spine(spine, known_line_ids=known_line_ids, exam=exam)
    beat_rep = evaluate_beats(
        beats, spine=spine, designated_beat=designated_beat, exam=exam,
    )
    errs = list(spine_rep.errors) + list(beat_rep.errors)
    errs.extend(evaluate_design_continuity(
        spine, book=book, clock=clock, place=place,
    ))
    missing: list[dict[str, Any]] = []
    seen: set[str] = set()
    for e in errs:
        mid = e.split(":")[0]
        if mid not in seen:
            seen.add(mid)
            missing.append({"id": mid, "detail": e})
    return DensityReport(
        ok=not errs,
        errors=errs,
        atoms=int(spine_rep.atoms or 0) + int(beat_rep.atoms or 0),
        sentences=int(spine_rep.sentences or 0),
        density=spine_rep.density,
        padding=spine_rep.padding,
        missing=missing,
    )


def evaluate_beats(
    beats: list | None,
    *,
    spine: dict | None = None,
    designated_beat: int | None = None,
    exam: str | None = None,
) -> DensityReport:
    rows = [b for b in (beats or []) if isinstance(b, dict) or str(b).strip()]
    norm: list[dict] = []
    for b in rows:
        if isinstance(b, dict):
            row = dict(b)
            if "choice" not in row and row.get("dilemma"):
                row["choice"] = row.get("dilemma")
            row["choice"] = normalize_choice(row.get("choice"))
            norm.append(row)
        else:
            norm.append({"text": str(b)})
    errs: list[str] = []
    design = (exam == "design") or (exam is None and _design_exam())
    if len(norm) < 3:
        errs.append("beat_count")
    if not any(parse_choice_ab(b.get("choice")) for b in norm):
        errs.append("beat_choice")
    cast = names_from_cast(spine or {})
    atom_n = 0
    for i, b in enumerate(norm, 1):
        for k in ("goal", "conflict", "turn", "cost"):
            if not cn_strip(slot_text(b.get(k))):
                errs.append(f"beat_slots:{i}:{k}")
            elif not design:
                if not is_atom_field(b.get(k), cast=cast):
                    errs.append(f"beat_gcd:{i}:{k}")
                else:
                    atom_n += 1
            elif is_atom_field(b.get(k), cast=cast):
                atom_n += 1
        g, t = cn_strip(b.get("goal")), cn_strip(b.get("turn"))
        if g and t and (g in t or t in g):
            errs.append(f"beat_turn_missing:{i}")
        if enter_sentences(b.get("text") or "") > 1:
            errs.append(f"beat_enter_pad:{i}")
        blob = _beat_blob(b)
        if any(w in blob for w in ICEBERG_LEAK_WORDS):
            errs.append("beat_leak")
    for e in beats_realize_spine(norm, spine, designated_beat=designated_beat):
        errs.append(e)
    if (not design) and atom_n < WORKING_BEAT_MIN_ATOMS and len(norm) >= 3:
        if not any(e.startswith("beat_gcd") or e.startswith("beat_slots") for e in errs):
            errs.append("beat_atoms")
    missing = []
    seen: set[str] = set()
    for e in errs:
        mid = e.split(":")[0]
        if mid not in seen:
            seen.add(mid)
            missing.append({"id": mid, "detail": e})
    return DensityReport(ok=not errs, errors=errs, atoms=atom_n, missing=missing)


def adapt_v1_five_slot(synopsis: str) -> dict:
    """只读适配：从五槽 Markdown 抽出短句。不写回。"""
    from scribe3.narrative_contract import split_outline_parts
    parts = split_outline_parts(synopsis or "")
    out = {k: "" for k in SPINE_SLOTS}
    out["schema"] = "chapter_spine.v1"
    out["setting"] = (parts.get("日子") or "").split("。")[0][:40]
    out["goal"] = (parts.get("必须发生") or "").split("。")[0][:40]
    out["inciting"] = out["goal"]
    out["escalation"] = (parts.get("因") or "").split("。")[0][:40]
    out["hook"] = (parts.get("章末未决") or "").split("。")[0][:40]
    out["forbid"] = (parts.get("不能说") or "").split("。")[0][:40]
    out["lines"] = []
    return out

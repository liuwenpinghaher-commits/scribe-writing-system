"""命运 / 故事钟 / 地点闸：纯函数，零 I/O。不并入 clue_density.errors。"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from scribe3.chapter_spine import (
    SPINE_SLOTS,
    parse_choice_ab,
    slot_text,
)
from scribe3.clue_density import (
    ACTION_LEX,
    WORLD_PHRASE,
    WORLD_VERB,
    _OBJECT_NEAR,
    _SINGLE_NEED_NEAR,
    _content_tokens,
    evaluate_beats,
    evaluate_spine,
    split_sents,
)
from scribe3.deduce_helpers import (
    DEDUCTION_HEADINGS,
    has_five_layer_headings,
    is_heading_noise_role,
)
from scribe3.narrative_contract import cn_strip

SCHEMA_ORE = "beats_meta.ore.v1"
SCHEMA_SEEDS = "beats_meta.seeds.v1"
SCHEMA_WORLD_FACT = "beats_meta.world_fact.v1"
WHO_PAYS_MAX = 40
AXIS_TERMS_MIN, AXIS_TERMS_MAX = 2, 3
ORE_CAP, ORE_MAX_CN = 5, 40
SEED_CAP = 3

HESITATE_NARROW = (
    "没伸", "又收回", "手悬", "没敢", "犹豫", "缩回",
    "收回", "停住", "停在", "递到一半",
)
SETTING_TIME_STOP = frozenset({
    "当夜", "下午", "夜里", "后半夜", "清晨", "当天", "凌晨", "傍晚",
})
FATE_VERB_BAG = ("按回", "开箱", "焊死", "降温", "找箱", "拔") + WORLD_VERB
CLOCK_SPANS = ("beat", "scene", "day", "stretch", "leap")
TIME_ORE = ("多年", "后来", "童年", "夜里")
_MEMORY_RE = re.compile(r"想起|记得|回忆|忆起|去年|那年|往年|当年|旧年|儿时|从前|早年")

WAVE_1_IDS = frozenset({
    "who_pays_missing", "prop_action_stuck",
    "clock_required", "clock_frozen",
    "place_required", "place_frozen",
    "seed_orphan",
    "deduction_layers", "deduction_ore", "ore_unlanded",
    "cast_role_frozen",
    "world_fact_missing", "world_fact_same",
    "goal_off_world",
    "surface_claim_unpaid", "claim_paid_by_paraphrase",
    "gesture_echo",
})
WAVE_2_IDS = frozenset({
    "axis_terms_missing", "cost_off_axis", "cost_private_only", "cost_same_amplitude",
    "world_untouched", "world_catalog_empty",
    "cast_function_stuck",
    "beat_echo_prev", "beat_decision_homeless",
    "choice_unperformed", "action_reread",
    "clock_book_missing", "ink_over_span", "ink_under_span", "beat_span_mismatch",
})
# setting_radius_stuck 永不进 wave（仅 shadow 诊断，避免与 place_frozen 双硬）
FATE_IDS = WAVE_1_IDS | WAVE_2_IDS
MICRO_INK = ("指腹", "门缝", "呼吸")


def fate_dearer_mode() -> str:
    """off | shadow | on。设置 DB → env → 默认 on。"""
    raw = ""
    try:
        from scribe3.settings import get_setting
        raw = str(get_setting("SCRIBE3_FATE_DEARER") or "").strip().lower()
    except Exception:
        raw = ""
    if not raw:
        import os
        raw = str(os.environ.get("SCRIBE3_FATE_DEARER") or "").strip().lower()
    if raw in ("on", "1", "true", "yes"):
        return "on"
    if raw == "shadow":
        return "shadow"
    if raw in ("off", "0", "false", "no"):
        return "off"
    if not raw:
        return "on"
    return "off"


def fate_wave_ids(*, mode: str | None = None) -> frozenset[str]:
    """on 时硬拦的 id 集。设置/环境 SCRIBE3_FATE_WAVE，默认 2。"""
    m = mode if mode is not None else fate_dearer_mode()
    if m != "on":
        return frozenset()
    wave = ""
    try:
        from scribe3.settings import get_setting
        wave = str(get_setting("SCRIBE3_FATE_WAVE") or "").strip()
    except Exception:
        wave = ""
    if not wave:
        import os
        wave = str(os.environ.get("SCRIBE3_FATE_WAVE") or "2").strip()
    if wave in ("2", "all", "full"):
        return FATE_IDS
    return WAVE_1_IDS


@dataclass
class FateReport:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    mode: str = "shadow"
    overlap: dict[str, Any] = field(default_factory=dict)
    ore_n: int = 0
    seeds_n: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FateCtx:
    seq: int = 1
    who_pays: str = ""
    axis_terms: list[str] = field(default_factory=list)
    clock_start: str = ""
    clock_end: str = ""
    prev_clock: dict | None = None
    prev2_clock: dict | None = None
    prev_place: dict | None = None
    prev2_place: dict | None = None
    prev_spine: dict | None = None
    prev2_spine: dict | None = None
    prev_beats: list | None = None
    prev2_beats: list | None = None
    prev_seeds: list = field(default_factory=list)
    prev_world_fact: dict | None = None
    known_world_names: set[str] = field(default_factory=set)
    focalizer: str = ""
    wave: frozenset[str] = field(default_factory=frozenset)


def action_hits(text: str) -> set[str]:
    blob = text or ""
    bag = {v for v in FATE_VERB_BAG if v in blob}
    acts: set[str] = set(bag)
    for w in ACTION_LEX:
        if w not in blob:
            continue
        if any(w != b and w in b for b in bag):
            continue
        if w in _SINGLE_NEED_NEAR:
            # 金样「海用他母亲的口气咳」：海与咳同句即算，不限 ±2 字窗。
            sent = blob
            for s in split_sents(blob):
                if w in s:
                    sent = s
                    break
            if not any(o in sent for o in _OBJECT_NEAR):
                continue
        acts.add(w)
    return acts


def action_object_pair(text: str) -> tuple[frozenset[str], frozenset[str]]:
    blob = text or ""
    acts = action_hits(blob)
    objs: set[str] = set()
    for a in acts:
        i = blob.find(a)
        window = blob[max(0, i - 4): i + len(a) + 4]
        for tok in _content_tokens(window, min_len=2):
            if tok not in acts and tok not in ("自己", "不是", "没有"):
                objs.add(tok)
    return frozenset(acts), frozenset(objs)


def prop_action_stuck(this_text: str, prev_text: str) -> bool:
    acts, objs = action_object_pair(this_text)
    prev_acts, prev_objs = action_object_pair(prev_text)
    if not acts or not prev_acts:
        return False
    return acts == prev_acts and bool(objs & prev_objs)


def load_clock(ch: MappingLike) -> dict[str, Any]:
    src = _chapter_map(ch)
    raw = src.get("clock")
    if not isinstance(raw, dict):
        meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
        raw = meta.get("clock") if isinstance(meta.get("clock"), dict) else {}
    span = str(raw.get("span") or "").strip().lower()
    try:
        delta = int(raw.get("delta") if raw.get("delta") is not None else -1)
    except (TypeError, ValueError):
        delta = -1
    return {
        "span": span if span in CLOCK_SPANS else "",
        "delta": delta,
        "freeze_reason": str(raw.get("freeze_reason") or "").strip(),
    }


def load_place(ch: MappingLike) -> dict[str, Any]:
    src = _chapter_map(ch)
    raw = src.get("place")
    if not isinstance(raw, dict):
        meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
        raw = meta.get("place") if isinstance(meta.get("place"), dict) else {}
    try:
        delta = int(raw.get("delta") if raw.get("delta") is not None else -1)
    except (TypeError, ValueError):
        delta = -1
    return {
        "name": str(raw.get("name") or "").strip(),
        "delta": delta,
        "stay_reason": str(raw.get("stay_reason") or "").strip(),
    }


def load_world_fact(ch: MappingLike) -> dict[str, str]:
    src = _chapter_map(ch)
    raw = src.get("world_fact")
    if not isinstance(raw, dict):
        meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
        raw = meta.get("world_fact") if isinstance(meta.get("world_fact"), dict) else {}
    text = ""
    if isinstance(raw, dict):
        text = str(raw.get("text") or "").strip()
    elif raw:
        text = str(raw).strip()
    return {"text": text}


def clock_required(clock: dict) -> bool:
    return str(clock.get("span") or "") not in CLOCK_SPANS


def place_required(place: dict) -> bool:
    name = str(place.get("name") or "").strip()
    try:
        delta = int(place.get("delta"))
    except (TypeError, ValueError):
        return True
    return not name or delta not in (0, 1, 2)


def clock_frozen(this: dict, prev: dict | None, *, seq: int) -> bool:
    if seq < 3 or not prev:
        return False
    if this.get("freeze_reason") or prev.get("freeze_reason"):
        return False
    slow = {"beat", "scene"}
    if this.get("span") not in slow or prev.get("span") not in slow:
        return False
    return int(this.get("delta") or 0) == 0 and int(prev.get("delta") or 0) == 0


def place_frozen(this: dict, prev: dict | None, *, seq: int) -> bool:
    if seq < 3 or not prev:
        return False
    if this.get("stay_reason") or prev.get("stay_reason"):
        return False
    return int(this.get("delta") or 0) == 0 and int(prev.get("delta") or 0) == 0


def setting_place_tokens(setting: str) -> set[str]:
    return {t for t in _content_tokens(setting, min_len=2) if t not in SETTING_TIME_STOP}


def setting_radius_stuck(this: str, prev: str, prev2: str, *, seq: int) -> bool:
    if seq < 3:
        return False
    a, b, c = setting_place_tokens(this), setting_place_tokens(prev), setting_place_tokens(prev2)
    core = a & b & c
    if not core or (a - core):
        return False
    return any(tok in this and tok in prev and tok in prev2 for tok in core)


def extract_ore(
    deductions: list | None,
    scene_truth: str = "",
    *,
    spine: dict | None = None,
    claim=None,
) -> list[dict[str, str]]:
    from scribe3.world_surface import term_in, world_surface_mode
    use_claim = bool(claim and world_surface_mode() == "on" and getattr(claim, "must_show", ()))
    must = tuple(getattr(claim, "must_show", ()) or ()) if use_claim else ()
    prefer = ("知道", "没察觉", "以为", "做了")
    blob_skip = ""
    if spine:
        blob_skip = " ".join(slot_text(spine.get(k)) for k in ("info_gap", "hook"))
    out: list[dict[str, str]] = []

    def _want(sent: str, layer: str) -> bool:
        if use_claim:
            if layer.startswith("看到"):
                return False
            return any(term_in(sent, p) for p in must)
        hits = action_hits(sent)
        timed = any(t in sent for t in TIME_ORE)
        return bool(hits or (timed and _content_tokens(sent, min_len=2)))

    for d in deductions or []:
        if not isinstance(d, dict):
            continue
        who = str(d.get("character_name") or d.get("character_id") or "")
        if is_heading_noise_role(who):
            continue
        prose = str(d.get("prose") or "")
        current_layer = ""
        for raw_line in (prose or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            hit_h = next((h for h in DEDUCTION_HEADINGS if line.startswith(h) or h in line[:12]), "")
            if hit_h:
                current_layer = hit_h
                rest = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                if rest and rest != line:
                    line = rest
                else:
                    continue
            for sent in split_sents(line):
                if blob_skip and sent in blob_skip:
                    continue
                layer = current_layer
                if use_claim:
                    if not _want(sent, layer):
                        continue
                else:
                    hits = action_hits(sent)
                    timed = any(t in sent for t in TIME_ORE)
                    if not hits and not (timed and _content_tokens(sent, min_len=2)):
                        continue
                    if prefer and not any(
                        p in prose[max(0, prose.find(sent) - 40): prose.find(sent) + 8] or p in sent
                        for p in prefer
                    ):
                        if not hits:
                            continue
                atom = cn_strip(sent)[:ORE_MAX_CN]
                if not atom:
                    continue
                if not layer:
                    layer = next((h for h in DEDUCTION_HEADINGS if h in prose), "")
                out.append({"atom": atom, "who": who, "layer": layer})
                if len(out) >= ORE_CAP:
                    return out
    if scene_truth and len(out) < ORE_CAP:
        for sent in split_sents(scene_truth):
            if use_claim:
                if any(term_in(sent, p) for p in must):
                    out.append({"atom": cn_strip(sent)[:ORE_MAX_CN], "who": "", "layer": "scene_truth"})
                    break
            elif action_hits(sent):
                out.append({"atom": cn_strip(sent)[:ORE_MAX_CN], "who": "", "layer": "scene_truth"})
                break
    return out


def ore_unlanded(atoms: list[dict], text: str, *, hook: str = "", bite: str = "", claim=None) -> bool:
    from scribe3.world_surface import term_in, world_surface_mode
    use_claim = bool(claim and world_surface_mode() == "on" and getattr(claim, "must_show", ()))
    must = tuple(getattr(claim, "must_show", ()) or ()) if use_claim else ()
    if use_claim:
        world_atoms = [
            it for it in (atoms or [])
            if any(term_in(str(it.get("atom") or ""), p) for p in must)
        ]
        if not world_atoms:
            return True
        body = (text or "") + "\n" + (hook or "") + "\n" + (bite or "")
        sents = split_sents(body) or [body]
        for item in world_atoms:
            if _atom_lands(str(item.get("atom") or ""), body, sents, claim=claim):
                return False
        return True
    if not atoms:
        return False
    body = (text or "") + "\n" + (hook or "") + "\n" + (bite or "")
    sents = split_sents(body) or [body]
    for item in atoms:
        atom = str(item.get("atom") or "")
        if _atom_lands(atom, body, sents, claim=None):
            return False
    return True


def _atom_lands(atom: str, body: str, sents: list[str], *, claim=None) -> bool:
    if not atom:
        return False
    from scribe3.world_surface import term_in, world_surface_mode
    if claim and world_surface_mode() == "on" and getattr(claim, "must_show", ()):
        hits = [p for p in claim.must_show if term_in(atom, p)]
        if not hits:
            return False
        return all(term_in(body, p) for p in hits)
    if len(atom) >= 4 and atom[:4] in body:
        return True
    if atom in body:
        return True
    acts = action_hits(atom)
    objs = [t for t in _content_tokens(atom, min_len=2) if t not in acts]
    for sent in sents:
        if acts and any(a in sent for a in acts) and any(o in sent for o in objs):
            return True
    return False


def deduction_layers_ok(deductions: list | None) -> bool:
    rows = [d for d in (deductions or []) if isinstance(d, dict)]
    real = [d for d in rows if not is_heading_noise_role(d.get("character_id") or d.get("character_name") or "")]
    if not real:
        return False
    return all(has_five_layer_headings(d.get("prose")) for d in real)


_CHOICE_TOK_STOP = frozenset({
    "自己", "不是", "没有", "他的", "她的",
    "柳岸", "岸青", "一条", "少一", "青交", "青自", "青把",
})


def _choice_toks(text: str) -> list[str]:
    """选择核：去掉人名切段。beat_echo 另走 _echo_toks，不用二字汤。"""
    blob = cn_strip(text or "")
    toks = [t for t in _content_tokens(blob) if len(t) >= 2 and t not in _CHOICE_TOK_STOP]
    for i in range(len(blob) - 1):
        bi = blob[i:i + 2]
        if bi not in _CHOICE_TOK_STOP:
            toks.append(bi)
    return toks


def _echo_toks(text: str) -> set[str]:
    """跨章节拍复读：内容块 + 其内二字。不用全文滑窗（他他/声里会误杀海咳副歌）。"""
    blob = cn_strip(text or "")
    toks = [t for t in _content_tokens(blob) if len(t) >= 2]
    out = set(toks)
    for t in toks:
        if len(t) >= 4:
            for i in range(len(t) - 1):
                out.add(t[i:i + 2])
    return out


_DECISION_CORE_EXTRA = (
    "读码", "开箱", "撕开", "揭开", "揭出", "揭卷",
    "按回", "按到", "按进", "焊死", "降温", "周公码",
    "令牌", "烫码", "缺笔", "残卷",
)
_DECISION_CORE_STOP = frozenset({
    "自己", "不是", "没有", "柳岸", "岸青", "柳岸青",
    "不读", "不交",
})


def _decision_cores(dec: str) -> list[str]:
    """决断核：2–4 字动作/物件。禁止「不交海」当核、禁止 6 字整词落空。"""
    blob = dec or ""
    out: list[str] = []
    for a in action_hits(blob):
        if len(a) >= 2 and a not in out:
            out.append(a)
    for v in FATE_VERB_BAG + _DECISION_CORE_EXTRA:
        if v in blob and v not in out:
            out.append(v)
    for i in range(len(blob)):
        for length in (2, 3, 4):
            sl = blob[i:i + length]
            if not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", sl):
                continue
            if sl in _DECISION_CORE_STOP or sl in out:
                continue
            if sl in action_hits(sl) or sl in FATE_VERB_BAG or sl in _DECISION_CORE_EXTRA:
                out.append(sl)
    if not out:
        for i in range(len(blob)):
            for length in (2, 3, 4):
                sl = blob[i:i + length]
                if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", sl) and sl not in _DECISION_CORE_STOP:
                    out.append(sl)
    return out


def evaluate_prose_choice(prose: str, spine: dict | None, *, ch: dict | None = None) -> list[str]:
    from scribe3.clue_density import _side_same
    from scribe3.design_play import play_choice_ab

    staged = ""
    play = ""
    if isinstance(ch, dict):
        meta = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
        staged = str(meta.get("staged_choice") or "")
        play = str(meta.get("play") or "")
    ab = play_choice_ab(staged) or parse_choice_ab(staged) or play_choice_ab(play) or parse_choice_ab(
        (spine or {}).get("choice")
    )
    if not ab:
        return []
    sents = split_sents(prose)
    if not sents:
        return ["choice_unperformed"]
    use_staged = bool(staged)

    def hit_side(sent: str, side: str) -> bool:
        if use_staged:
            return bool(side) and (side in sent or _side_same(sent, side))
        toks = _choice_toks(side)
        return any(t in sent for t in toks)

    half = max(1, len(sents) // 2)
    saw_a = saw_b = False
    dec_late = False
    for i, si in enumerate(sents):
        if hit_side(si, ab[0]):
            saw_a = True
            if i >= half:
                dec_late = True
        if hit_side(si, ab[1]):
            saw_b = True
            if i >= half:
                dec_late = True
        side_i = "a" if hit_side(si, ab[0]) else ("b" if hit_side(si, ab[1]) else "")
        if not side_i:
            continue
        for k in range(i + 2, len(sents)):
            sk = sents[k]
            side_k = "b" if side_i == "a" and hit_side(sk, ab[1]) else (
                "a" if side_i == "b" and hit_side(sk, ab[0]) else ""
            )
            if not side_k:
                continue
            mid = sents[i + 1: k]
            if any(any(h in m for h in HESITATE_NARROW) for m in mid):
                return []
            if k >= half:
                return []
    if saw_a and saw_b and dec_late:
        return []
    return ["choice_unperformed"]


def duplicate_action_fingerprints(text: str, *, allow: set[str] | None = None) -> int:
    """情节复读：动词须 ≥2 字（方案 ACTION≥2）。1 字「裂/还/按」+「的声音」是误报。"""
    ban = allow or set()
    fps: list[tuple[int, tuple[str, str]]] = []
    for i, sent in enumerate(split_sents(text)):
        if _MEMORY_RE.search(sent):
            continue
        acts, objs = action_object_pair(sent)
        for a in acts:
            if len(a) < 2:
                continue
            for o in objs:
                if o in ban or o in _REREAD_OBJ_STOP:
                    continue
                if a in o:
                    continue
                if not re.fullmatch(r"[\u4e00-\u9fff]{2,8}", o):
                    continue
                fps.append((i, (a, o)))
    n = 0
    seen: dict[tuple[str, str], int] = {}
    for i, fp in fps:
        if fp in seen and i - seen[fp] > 1:
            n += 1
        else:
            seen[fp] = i
    return n


_SEED_PUNCT_RE = re.compile(r"[^\u4e00-\u9fff]")
_SEED_STOP = frozenset({
    "了一", "一下", "的纸", "了的", "在了", "是他", "他的", "她的",
    "没有", "不是", "自己", "一个", "那里", "这里", "然后",
    "一声", "一次", "一遍", "一条", "一道", "一位", "这个", "那个",
    "什么", "怎么", "还在", "还是", "已经", "可以", "因为", "所以",
    "在他", "看见", "听到", "他说", "她说", "声音", "然后",
    "青的", "出来", "那声", "点亮", "掌根", "骨内", "内侧", "骨内侧",
    "核点", "枪嘴", "银气", "火头", "针态",
})
_REREAD_OBJ_STOP = frozenset({
    "的声音", "没看", "一下", "一声", "自己", "不是", "没有",
    "那里", "这里", "然后", "还悬", "还在", "的什么", "之间",
})


def is_seed_atom(tok: str, *, known_names: set[str] | None = None) -> bool:
    """户口原子：纯汉字、非标点、非人名切段、非量词/代词。"""
    atom = (tok or "").strip()
    if len(atom) < 2:
        return False
    if _SEED_PUNCT_RE.search(atom):
        return False
    if atom in _SEED_STOP:
        return False
    if len(atom) == 2 and (atom.endswith("的") or atom.startswith("的")):
        return False
    if len(atom) == 2 and any(p.endswith(atom) and len(p) > 2 for p in WORLD_PHRASE):
        return False
    if atom in action_hits(atom):
        return False
    for name in known_names or ():
        n = str(name or "").strip()
        if not n:
            continue
        if atom == n:
            return False
        if len(n) >= 3 and len(atom) == 2 and atom in n:
            return False
    return True


def extract_seeds(
    prose: str,
    spine: dict | None,
    *,
    ore: list | None = None,
    known_names: set[str] | None = None,
) -> list[dict[str, str]]:
    spine_blob = " ".join(slot_text((spine or {}).get(k)) for k in SPINE_SLOTS)
    ore_blob = " ".join(str(x.get("atom") or "") for x in (ore or []) if isinstance(x, dict))
    names = set(known_names or set())
    ban = set(_content_tokens(spine_blob + " " + ore_blob)) | names
    body = prose or ""
    cands: list[tuple[int, int, str]] = []
    hay = body + " " + spine_blob
    world_hits = [p for p in WORLD_PHRASE if p and p in hay]
    if world_hits:
        # 万界：只收世界整词（正文或章纲），禁止二字汤。
        for phrase in world_hits:
            if is_seed_atom(phrase, known_names=names):
                n = hay.count(phrase)
                cands.append((2, n, phrase[:40]))
    else:
        for name in sorted(names, key=len, reverse=True):
            if name and name in body and name not in spine_blob and is_seed_atom(name, known_names=names):
                cands.append((1, body.count(name), name[:40]))
        grams = list(_content_tokens(body, min_len=2))
        for i in range(len(body) - 1):
            bi = body[i:i + 2]
            if re.fullmatch(r"[\u4e00-\u9fff]{2}", bi):
                grams.append(bi)
        for tok in grams:
            if tok in ban or not is_seed_atom(tok, known_names=names):
                continue
            n = body.count(tok)
            if n >= 2:
                cands.append((0, n, tok))
    cands.sort(key=lambda x: (-x[0], -x[1], -len(x[2])))
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for _, __, atom in cands:
        if atom in seen:
            continue
        seen.add(atom)
        out.append({"atom": atom})
        if len(out) >= SEED_CAP:
            break
    return out


def seed_orphan(prev_seeds: list, this_slots_blob: str, *, known_names: set[str] | None = None) -> bool:
    live: list[str] = []
    for item in prev_seeds or []:
        atom = str((item or {}).get("atom") or "")
        if not is_seed_atom(atom, known_names=known_names):
            continue
        live.append(atom)
    if not live:
        return False
    blob = this_slots_blob or ""
    for atom in live:
        key = atom[:4] if len(atom) >= 4 else atom
        if key and key in blob:
            return False
    return True


def parse_axis_terms(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()][:AXIS_TERMS_MAX]
    s = str(raw or "").strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()][:AXIS_TERMS_MAX]
        except (TypeError, ValueError):
            pass
    return [p.strip() for p in re.split(r"[/／、,，;；]+", s) if p.strip()][:AXIS_TERMS_MAX]


def _cast_focus_names(spine: dict | None, *, focalizer: str = "") -> list[str]:
    """焦点 / 对手第一名；切不出则 focalizer + cast 顿号第一名。见证豁免。"""
    blob = slot_text((spine or {}).get("cast"))
    names: list[str] = []
    if "焦点" in blob or "对手" in blob or "/" in blob or "／" in blob:
        parts = re.split(r"[/／]", blob)
        for p in parts:
            p = re.sub(r"^(焦点|对手|见证)\s*", "", p.strip())
            first = re.split(r"[、，,；;]", p)[0].strip()
            if first and first not in names:
                names.append(first)
            if len(names) >= 2:
                break
    if not names:
        foc = (focalizer or "").split(":")[-1].strip()
        if foc:
            names.append(foc)
        first = re.split(r"[、，,；;]", blob)[0].strip()
        first = re.sub(r"^(焦点|对手|见证)\s*", "", first)
        if first and first not in names:
            names.append(first)
    return [n for n in names if n][:2]


def cast_function_map(beats: list | None, name: str) -> set[str]:
    if not name:
        return set()
    bag: set[str] = set()
    for b in beats or []:
        if not isinstance(b, dict):
            continue
        blob = "".join(slot_text(b.get(k)) for k in ("goal", "conflict", "turn", "cost", "choice"))
        if name not in blob:
            continue
        for w in action_hits(blob):
            if len(w) >= 2:
                bag.add(w)
                continue
            i = blob.find(w)
            win = blob[i: i + len(w) + 2]
            if len(win) >= 2:
                bag.add(win[:2])
    return bag


def cast_function_stuck(
    this_beats: list | None,
    prev_beats: list | None,
    prev2_beats: list | None,
    spine: dict | None,
    *,
    seq: int,
    focalizer: str = "",
) -> bool:
    if seq < 3 or not prev_beats or not prev2_beats:
        return False
    for name in _cast_focus_names(spine, focalizer=focalizer):
        a, b, c = (
            cast_function_map(this_beats, name),
            cast_function_map(prev_beats, name),
            cast_function_map(prev2_beats, name),
        )
        if not a or not b or not c:
            continue
        if a <= b and (a & b) and b <= c and (b & c):
            return True
    return False


_EXTRACT_MARK = ("带走", "带他走", "要带他", "要带他走")
_BROKER_MARK = ("交出去", "交人", "换封口", "换活", "封口", "交令")


def _blob_for_cast_role(name: str, spine: dict | None, beats: list | None) -> str:
    bits: list[str] = []
    obst = slot_text((spine or {}).get("obstacle"))
    for clause in re.split(r"[；;]", obst):
        if name and name in clause:
            bits.append(clause.strip())
    for b in beats or []:
        if not isinstance(b, dict):
            continue
        conf = slot_text(b.get("conflict"))
        if name and name in conf:
            bits.append(conf)
    return "。".join(bits)


def _observer_in_clause(name: str, clause: str) -> bool:
    """仅当 WORLD_VERB 贴在该人名后（8 字内），才算 observer。"""
    if not name or name not in clause:
        return False
    i = clause.find(name)
    win = clause[i + len(name): i + len(name) + 8]
    return any(v in win for v in WORLD_VERB)


def cast_role_of(name: str, spine: dict | None, beats: list | None) -> frozenset[str]:
    """挡槽论元角色：pressor / extractor / broker / observer / unveiler。"""
    if not name:
        return frozenset()
    blob = _blob_for_cast_role(name, spine, beats)
    if not blob:
        return frozenset()
    roles: set[str] = set()
    if "按" in blob:
        roles.add("pressor")
    if any(m in blob for m in _EXTRACT_MARK):
        roles.add("extractor")
    if any(m in blob for m in _BROKER_MARK):
        roles.add("broker")
    clauses = [c for c in re.split(r"[；;。]", blob) if name in c]
    if any(_observer_in_clause(name, c) for c in clauses or [blob]):
        roles.add("observer")
    if any(v in blob for v in ("揭", "拨")) and any(p in blob for p in WORLD_PHRASE):
        roles.add("unveiler")
    return frozenset(roles)


def _cast_blocker_names(spine: dict | None) -> list[str]:
    """在场名单里除见证外的名字。顿号名单也能扫到沈烛/兰因，不只焦点。"""
    blob = slot_text((spine or {}).get("cast"))
    names: list[str] = []
    witnesses: set[str] = set()
    parts = re.split(r"[、，,；;/]+", blob)
    for raw in parts:
        p = raw.strip()
        if not p:
            continue
        if p.startswith("见证"):
            w = re.sub(r"^见证\s*", "", p).strip()
            if w:
                witnesses.add(w)
            continue
        p = re.sub(r"^(焦点|对手)\s*", "", p).strip()
        if p and p not in names:
            names.append(p)
    return [n for n in names if n not in witnesses]


def cast_role_frozen(
    this_spine: dict | None,
    this_beats: list | None,
    prev_spine: dict | None,
    prev_beats: list | None,
    prev2_spine: dict | None,
    prev2_beats: list | None,
    *,
    seq: int,
    focalizer: str = "",
) -> bool:
    """连续三章同一在场人物同一论元角色 → 冻住。见证豁免。"""
    if seq < 3 or not prev_spine or not prev2_spine:
        return False
    names = _cast_blocker_names(this_spine) or _cast_focus_names(this_spine, focalizer=focalizer)
    for name in names:
        a = cast_role_of(name, this_spine, this_beats)
        b = cast_role_of(name, prev_spine, prev_beats)
        c = cast_role_of(name, prev2_spine, prev2_beats)
        if not a or not b or not c:
            continue
        if a & b & c:
            return True
    return False


def world_fact_missing(fact: dict | None) -> bool:
    return not str((fact or {}).get("text") or "").strip()


def world_fact_same(
    this: dict | None,
    prev: dict | None,
    *,
    spine: dict | None = None,
    prev_spine: dict | None = None,
    axis_terms: list[str] | None = None,
) -> bool:
    cur = str((this or {}).get("text") or "").strip()
    old = str((prev or {}).get("text") or "").strip()
    if not cur or not old:
        return False
    if cn_strip(cur) == cn_strip(old):
        return True
    phrases = set(WORLD_PHRASE) | {t for t in (axis_terms or []) if t}
    if not any(p in cur and p not in old for p in phrases):
        return True
    cost = slot_text((spine or {}).get("cost"))
    prev_cost = slot_text((prev_spine or {}).get("cost"))
    if not cost or not prev_cost:
        return False
    ov = set(_content_tokens(cost)) & set(_content_tokens(prev_cost))
    new_phrase = any(p in cost and p not in prev_cost for p in phrases)
    return len(ov) >= 2 and not new_phrase


def evaluate_fate_spine(spine: dict | None, ctx: FateCtx, *, ch: dict | None = None) -> FateReport:
    mode = fate_dearer_mode()
    errs: list[str] = []
    src = spine if isinstance(spine, dict) else {}
    if not str(ctx.who_pays or "").strip():
        errs.append("who_pays_missing")
    terms = list(ctx.axis_terms or [])
    if len(terms) < AXIS_TERMS_MIN:
        errs.append("axis_terms_missing")
    if not (ctx.clock_start or "").strip() or not (ctx.clock_end or "").strip():
        errs.append("clock_book_missing")

    clock = load_clock(ch or {})
    place = load_place(ch or {})
    if clock_required(clock):
        errs.append("clock_required")
    if place_required(place):
        errs.append("place_required")
    if clock_frozen(clock, ctx.prev_clock, seq=int(ctx.seq or 1)):
        errs.append("clock_frozen")
    if place_frozen(place, ctx.prev_place, seq=int(ctx.seq or 1)):
        errs.append("place_frozen")

    this_blob = slot_text(src.get("goal")) + slot_text(src.get("inciting"))
    prev_blob = ""
    if ctx.prev_spine:
        prev_blob = slot_text(ctx.prev_spine.get("goal")) + slot_text(ctx.prev_spine.get("inciting"))
    if prev_blob and prop_action_stuck(this_blob, prev_blob):
        errs.append("prop_action_stuck")

    cost = slot_text(src.get("cost"))
    goal = slot_text(src.get("goal"))
    from scribe3.world_surface import load_world_claim, term_in, world_surface_mode
    claim = load_world_claim(ch or {})
    if set(terms) & set(WORLD_PHRASE) and goal and cost:
        if world_surface_mode() == "on" and claim:
            g_terms = tuple(claim.groups.get("goal") or ()) or tuple(WORLD_PHRASE)
            c_terms = tuple(claim.groups.get("cost") or ()) or tuple(WORLD_PHRASE)
            if not (
                any(term_in(goal, t) for t in g_terms)
                and any(term_in(cost, t) for t in c_terms)
            ):
                errs.append("goal_off_world")
        elif not (
            any(p in goal for p in WORLD_PHRASE)
            and any(p in cost for p in WORLD_PHRASE)
        ):
            errs.append("goal_off_world")
    if cost:
        hit_axis = any(t and t in cost for t in terms)
        hit_world = any(n and n in cost for n in (ctx.known_world_names or ()))
        if not hit_axis and not hit_world:
            errs.append("cost_private_only")
            if terms:
                errs.append("cost_off_axis")
        if ctx.prev_spine:
            prev_cost = slot_text(ctx.prev_spine.get("cost"))
            ov = set(_content_tokens(cost)) & set(_content_tokens(prev_cost))
            grams = set(_choice_toks(cost)) & set(_choice_toks(prev_cost))
            new_term = any(t in cost and t not in prev_cost for t in terms)
            new_world = any(
                n and n in cost and n not in prev_cost
                for n in (ctx.known_world_names or ())
            )
            same_axis = any(t and t in cost and t in prev_cost for t in terms)
            if (same_axis or len(ov) >= 2 or len(grams) >= 2) and not new_term and not new_world:
                errs.append("cost_same_amplitude")

    if ctx.prev_seeds:
        blob = " ".join(
            slot_text(src.get(k)) for k in ("bite", "info_gap", "hook", "forbid")
        )
        for it in src.get("lines") or []:
            if isinstance(it, dict):
                blob += " " + str(it.get("delta") or "")
        if seed_orphan(ctx.prev_seeds, blob + " " + slot_text(src.get("forbid"))):
            errs.append("seed_orphan")

    if ctx.known_world_names:
        probe = slot_text(src.get("info_gap")) + slot_text(src.get("cost"))
        if probe and not any(n in probe for n in ctx.known_world_names):
            errs.append("world_untouched")
    elif set(terms) & set(WORLD_PHRASE):
        # 仅万界轴用语才因空库 422；炉灰记开 WAVE-2 不误杀
        errs.append("world_catalog_empty")

    if ctx.prev_spine and ctx.prev2_spine:
        if setting_radius_stuck(
            slot_text(src.get("setting")),
            slot_text(ctx.prev_spine.get("setting")),
            slot_text(ctx.prev2_spine.get("setting")),
            seq=int(ctx.seq or 1),
        ):
            errs.append("setting_radius_stuck")

    this_beats = None
    if isinstance(ch, dict) and isinstance(ch.get("beats"), list):
        this_beats = ch.get("beats")
    if cast_function_stuck(
        this_beats,
        ctx.prev_beats,
        ctx.prev2_beats,
        src,
        seq=int(ctx.seq or 1),
        focalizer=ctx.focalizer,
    ):
        errs.append("cast_function_stuck")
    if cast_role_frozen(
        src,
        this_beats,
        ctx.prev_spine,
        ctx.prev_beats,
        ctx.prev2_spine,
        ctx.prev2_beats,
        seq=int(ctx.seq or 1),
        focalizer=ctx.focalizer,
    ):
        errs.append("cast_role_frozen")
    try:
        from scribe3.world_surface import gesture_echo, gesture_fingerprint, world_surface_mode
        if world_surface_mode() == "on" and int(ctx.seq or 1) >= 2:
            this_g = gesture_fingerprint(src, this_beats)
            prev_g = gesture_fingerprint(ctx.prev_spine, ctx.prev_beats)
            if gesture_echo(this_g, prev_g):
                errs.append("gesture_echo")
    except Exception:
        pass

    fact = load_world_fact(ch or {})
    if world_fact_missing(fact):
        errs.append("world_fact_missing")
    elif ctx.prev_world_fact and int(ctx.seq or 1) >= 2:
        if world_fact_same(
            fact,
            ctx.prev_world_fact,
            spine=src,
            prev_spine=ctx.prev_spine,
            axis_terms=list(ctx.axis_terms or []),
        ):
            errs.append("world_fact_same")

    return FateReport(ok=not errs, errors=errs, mode=mode)


_SECOND_BEAT = ("眼皮", "指腹", "门缝", "呼吸", "挡在")


def beat_span_mismatch(beats: list | None, clock: dict | None) -> bool:
    """leap/stretch 章三拍全是秒级微动作、无世界词 → 笔墨与跨度不配。"""
    span = str((clock or {}).get("span") or "")
    if span not in ("leap", "stretch"):
        return False
    rows = [b for b in (beats or []) if isinstance(b, dict)]
    if len(rows) < 3:
        return False

    def _micro(b: dict) -> bool:
        blob = "".join(slot_text(b.get(k)) for k in ("goal", "conflict", "turn"))
        if any(p in blob for p in WORLD_PHRASE):
            return False
        return any(m in blob for m in _SECOND_BEAT)

    return all(_micro(b) for b in rows[:3])


def evaluate_fate_beats(beats: list | None, spine: dict | None, ctx: FateCtx, *, ch: dict | None = None) -> FateReport:
    mode = fate_dearer_mode()
    errs: list[str] = []
    rows = [b for b in (beats or []) if isinstance(b, dict)]
    if ctx.prev_beats:
        prev_sets = []
        for b in ctx.prev_beats:
            if not isinstance(b, dict):
                continue
            prev_sets.append(_echo_toks(
                slot_text(b.get("goal")) + slot_text(b.get("conflict")) + slot_text(b.get("turn"))
            ))
        for b in rows:
            cur = _echo_toks(
                slot_text(b.get("goal")) + slot_text(b.get("conflict")) + slot_text(b.get("turn"))
            )
            for prev in prev_sets:
                union = cur | prev
                if not union:
                    continue
                if len(cur & prev) / len(union) >= 0.40:
                    errs.append("beat_echo_prev")
                    break
            if "beat_echo_prev" in errs:
                break
    dec = slot_text((spine or {}).get("decision"))
    if dec:
        toks = _decision_cores(dec)
        found = False
        for b in rows:
            if not parse_choice_ab(b.get("choice")):
                continue
            blob = " ".join(slot_text(b.get(k)) for k in ("goal", "turn", "choice", "cost"))
            if any(t and t in blob for t in toks):
                found = True
                break
        if not found:
            errs.append("beat_decision_homeless")
    if beat_span_mismatch(rows, load_clock(ch or {})):
        errs.append("beat_span_mismatch")
    return FateReport(ok=not errs, errors=errs, mode=mode)


def evaluate_fate_prose(
    text: str,
    ch: dict | None,
    ctx: FateCtx,
    *,
    kind: str = "draft",
) -> FateReport:
    mode = fate_dearer_mode()
    src = _chapter_map(ch)
    spine = src.get("chapter_spine") if isinstance(src.get("chapter_spine"), dict) else {}
    from scribe3.world_surface import (
        claim_paid,
        load_world_claim,
        world_surface_mode,
    )
    claim = load_world_claim(src)
    surface_on = world_surface_mode() == "on" and claim is not None
    ore = load_ore(src)
    errs: list[str] = []
    if not deduction_layers_ok(src.get("deductions")) and src.get("deductions"):
        errs.append("deduction_layers")
    if surface_on and kind in ("draft", "final") and (text or "").strip():
        extracted = extract_ore(
            src.get("deductions"), str(src.get("scene_truth") or ""),
            spine=spine, claim=claim,
        )
        ore = extracted
        if ore_unlanded(ore, text, hook=slot_text(spine.get("hook")), claim=claim):
            errs.append("ore_unlanded")
    else:
        if src.get("deductions") is not None and not ore:
            extracted = extract_ore(src.get("deductions"), str(src.get("scene_truth") or ""), spine=spine)
            if not extracted:
                errs.append("deduction_ore")
            ore = extracted
        if ore and ore_unlanded(ore, text, hook=slot_text(spine.get("hook"))):
            errs.append("ore_unlanded")
    if surface_on and kind in ("draft", "final") and (text or "").strip():
        pay = claim_paid(text, claim)
        if not pay.paid:
            errs.append("surface_claim_unpaid")
        if pay.paraphrase_only:
            errs.append("claim_paid_by_paraphrase")
    errs.extend(evaluate_prose_choice(text, spine, ch=src))
    allow = set()
    for n in re.split(r"[、，,；;/]", slot_text(spine.get("cast"))):
        if n.strip():
            allow.add(n.strip())
    allow |= set(ctx.known_world_names or ())
    if duplicate_action_fingerprints(text, allow=allow) >= 1:
        errs.append("action_reread")
    clock = load_clock(src)
    span = clock.get("span")
    choice_errs = [e for e in errs if e == "choice_unperformed"]
    if span in ("day", "stretch", "leap"):
        if _micro_ink_reread(text) or (
            "action_reread" in errs and (choice_errs or not parse_choice_ab(spine.get("choice")))
        ):
            errs.append("ink_over_span")
    if span == "beat" and (text or "").strip():
        no_choice = bool(choice_errs) or not parse_choice_ab((spine or {}).get("choice"))
        no_ore = (not ore) or ("ore_unlanded" in errs)
        if no_choice and no_ore:
            errs.append("ink_under_span")
    return FateReport(ok=not errs, errors=errs, mode=mode, ore_n=len(ore))


def _micro_ink_reread(text: str) -> bool:
    """日级以上：不相邻两句同现指腹/门缝/呼吸，且非闪回。"""
    sents = [s for s in split_sents(text or "") if not _MEMORY_RE.search(s)]
    seen: dict[str, int] = {}
    for i, sent in enumerate(sents):
        for tok in MICRO_INK:
            if tok not in sent:
                continue
            if tok in seen and i - seen[tok] > 1:
                return True
            seen.setdefault(tok, i)
    return False


def load_ore(ch: MappingLike) -> list[dict]:
    src = _chapter_map(ch)
    meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
    raw = meta.get("ore")
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def merge_ore(existing: MappingLike, ore: list[dict]) -> dict[str, Any]:
    meta = {}
    if isinstance(existing, dict):
        meta = dict(existing.get("beats_meta") or {}) if isinstance(existing.get("beats_meta"), dict) else {}
    meta["ore"] = ore
    meta["schema_ore"] = SCHEMA_ORE
    return meta


def parse_clock_place_labels(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """从大纲标签抽出 clock / place。较长标签优先。"""
    clock: dict[str, Any] = {}
    place: dict[str, Any] = {}
    pairs = (
        ("地点增量", "place_delta"),
        ("冻钟理由", "freeze_reason"),
        ("留驻理由", "stay_reason"),
        ("时长", "span"),
        ("增量", "clock_delta"),
        ("地点", "place_name"),
    )
    blob = text or ""
    for lab, key in pairs:
        m = re.search(
            rf"(?:^|\n)\s*{re.escape(lab)}\s*[:：]\s*(.+)",
            blob,
        )
        if not m:
            continue
        body = m.group(1).strip().split("\n", 1)[0].strip()
        if key == "span":
            span = body.split()[0].strip().lower() if body else ""
            if span in CLOCK_SPANS:
                clock["span"] = span
        elif key == "clock_delta":
            try:
                clock["delta"] = int(str(body).split()[0])
            except (TypeError, ValueError):
                pass
        elif key == "freeze_reason" and body:
            clock["freeze_reason"] = body[:80]
        elif key == "place_name" and body:
            place["name"] = body[:20]
        elif key == "place_delta":
            try:
                place["delta"] = int(str(body).split()[0])
            except (TypeError, ValueError):
                pass
        elif key == "stay_reason" and body:
            place["stay_reason"] = body[:80]
    return clock, place


def parse_world_fact_label(text: str) -> dict[str, str]:
    m = re.search(r"(?:^|\n)\s*世界事实\s*[:：]\s*(.+)", text or "")
    if not m:
        return {}
    body = m.group(1).strip().split("\n", 1)[0].strip()
    if not body:
        return {}
    return {"text": body}


def merge_world_fact(existing: MappingLike, fact: dict | None) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if isinstance(existing, dict):
        raw = existing.get("beats_meta")
        if isinstance(raw, dict):
            meta = dict(raw)
        elif existing.get("world_fact") or existing.get("clock") or existing.get("place"):
            meta = dict(existing)
    if fact and str(fact.get("text") or "").strip():
        meta["world_fact"] = {"text": str(fact.get("text") or "").strip()}
        meta["schema_world_fact"] = SCHEMA_WORLD_FACT
    return meta


def merge_clock_place(
    existing: MappingLike,
    clock: dict | None = None,
    place: dict | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if isinstance(existing, dict):
        raw = existing.get("beats_meta")
        if isinstance(raw, dict):
            meta = dict(raw)
        elif "span" in existing or "name" in existing:
            meta = dict(existing)
    if clock:
        prev = meta.get("clock") if isinstance(meta.get("clock"), dict) else {}
        nxt = dict(prev)
        nxt.update({k: v for k, v in clock.items() if v not in ("", None)})
        meta["clock"] = nxt
    if place:
        prev = meta.get("place") if isinstance(meta.get("place"), dict) else {}
        nxt = dict(prev)
        nxt.update({k: v for k, v in place.items() if v not in ("", None)})
        meta["place"] = nxt
    return meta


def merge_seeds(existing: MappingLike, seeds: list[dict]) -> dict[str, Any]:
    meta = {}
    if isinstance(existing, dict):
        meta = dict(existing.get("beats_meta") or {}) if isinstance(existing.get("beats_meta"), dict) else {}
    meta["seeds"] = seeds
    meta["schema_seeds"] = SCHEMA_SEEDS
    return meta


def persist_fate_kwargs(st, seq: int, fields: dict | None, existing: dict | None) -> dict[str, Any]:
    """所有 persist_fields_blocked 入口共用，禁止只传 fields。"""
    merged = {**(existing if isinstance(existing, dict) else {}), **(fields if isinstance(fields, dict) else {})}
    return {
        "fate_ctx": load_fate_context(st, int(seq or 1), merged),
        "chapter": merged,
    }


def load_fate_context(st, seq: int, ch: dict | None = None) -> FateCtx:
    ctx = FateCtx(seq=int(seq or 1))
    ctx.wave = fate_wave_ids()
    if isinstance(ch, dict):
        ctx.focalizer = str(ch.get("focalizer") or "")
    if st is None:
        return ctx
    try:
        intent = st.get_intent() if hasattr(st, "get_intent") else {}
    except Exception:
        intent = {}
    intent = intent if isinstance(intent, dict) else {}
    ctx.who_pays = str(intent.get("who_pays") or "")
    ctx.axis_terms = parse_axis_terms(intent.get("axis_terms"))
    ctx.clock_start = str(intent.get("clock_start") or "")
    ctx.clock_end = str(intent.get("clock_end") or "")
    names: set[str] = set()
    for meth in ("list_world_rules", "list_terms", "list_items"):
        try:
            fn = getattr(st, meth, None)
            rows = fn() if callable(fn) else []
            for row in rows or []:
                if isinstance(row, dict) and row.get("name"):
                    names.add(str(row["name"]))
        except Exception:
            pass
    ctx.known_world_names = names
    n = int(seq or 1)
    if n >= 2:
        try:
            prev = st.get_chapter(n - 1) or {}
        except Exception:
            prev = {}
        if isinstance(prev, dict):
            ctx.prev_spine = prev.get("chapter_spine") if isinstance(prev.get("chapter_spine"), dict) else None
            ctx.prev_beats = prev.get("beats") if isinstance(prev.get("beats"), list) else None
            ctx.prev_clock = load_clock(prev)
            ctx.prev_place = load_place(prev)
            meta = prev.get("beats_meta") if isinstance(prev.get("beats_meta"), dict) else {}
            seeds = meta.get("seeds")
            ctx.prev_seeds = [s for s in seeds if isinstance(s, dict)] if isinstance(seeds, list) else []
            ctx.prev_world_fact = load_world_fact(prev)
    if n >= 3:
        try:
            prev2 = st.get_chapter(n - 2) or {}
        except Exception:
            prev2 = {}
        if isinstance(prev2, dict):
            ctx.prev2_spine = prev2.get("chapter_spine") if isinstance(prev2.get("chapter_spine"), dict) else None
            ctx.prev2_beats = prev2.get("beats") if isinstance(prev2.get("beats"), list) else None
            ctx.prev2_clock = load_clock(prev2)
            ctx.prev2_place = load_place(prev2)
    return ctx


def prose_fate_blocked(
    text: str,
    ch: dict,
    ctx: FateCtx,
    *,
    kind: Literal["draft", "final"] = "draft",
) -> dict[str, Any] | None:
    if fate_dearer_mode() != "on":
        return None
    rep = evaluate_fate_prose(text, ch, ctx, kind=kind)
    hard = [e for e in rep.errors if e in (ctx.wave or fate_wave_ids())]
    if not hard:
        return None
    return {
        "code": "fate_blocked",
        "missing": hard,
        "message": _fate_block_message(hard),
        "fate": rep.as_dict(),
    }


def _fate_block_message(hard: list[str]) -> str:
    tip = ""
    if "who_pays_missing" in hard:
        tip = "。请先 s3_set_intent(who_pays=…)"
    return "命运闸：" + " / ".join(hard) + tip


def evaluate_write_contract(
    spine: dict | None,
    beats: list | None,
    ctx: FateCtx,
    ch: dict | None = None,
    *,
    known_line_ids: set | None = None,
) -> FateReport:
    """extra 与 persist 同一验收：密度 + 节拍 + 当前波次硬 id。"""
    mode = fate_dearer_mode()
    errs: list[str] = []
    dens = evaluate_spine(spine, known_line_ids=known_line_ids)
    if not dens.ok:
        errs.extend(list(dens.errors or []))
    if beats is not None:
        beat = evaluate_beats(beats, spine=spine)
        if not beat.ok:
            errs.extend(list(beat.errors or []))
    fate = evaluate_fate_spine(spine, ctx, ch=ch)
    wave = ctx.wave or WAVE_1_IDS
    errs.extend([e for e in fate.errors if e in wave])
    # 去重保序
    seen: set[str] = set()
    uniq: list[str] = []
    for e in errs:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    return FateReport(ok=not uniq, errors=uniq, mode=mode)


def contract_blocked(
    spine: dict | None,
    beats: list | None,
    ctx: FateCtx,
    ch: dict | None = None,
    *,
    known_line_ids: set | None = None,
) -> dict[str, Any] | None:
    """outline/beats persist 与 extra 同一验收。旗非 on 不拦。"""
    if fate_dearer_mode() != "on":
        return None
    rep = evaluate_write_contract(spine, beats, ctx, ch, known_line_ids=known_line_ids)
    wave = ctx.wave or WAVE_1_IDS
    hard = [
        e for e in rep.errors
        if e in wave or str(e).startswith(("spine_", "beat_", "lines_"))
    ]
    if not hard:
        return None
    return {
        "code": "fate_blocked",
        "missing": hard,
        "message": _fate_block_message(hard),
        "fate": rep.as_dict(),
    }


def spine_fate_blocked(spine: dict | None, ctx: FateCtx, *, ch: dict | None = None) -> dict[str, Any] | None:
    if fate_dearer_mode() != "on":
        return None
    rep = evaluate_fate_spine(spine, ctx, ch=ch)
    hard = [e for e in rep.errors if e in (ctx.wave or fate_wave_ids())]
    if not hard:
        return None
    return {
        "code": "fate_blocked",
        "missing": hard,
        "message": _fate_block_message(hard),
        "fate": rep.as_dict(),
    }


MappingLike = dict[str, Any] | None


def _chapter_map(ch: Any) -> dict[str, Any]:
    return ch if isinstance(ch, dict) else {}

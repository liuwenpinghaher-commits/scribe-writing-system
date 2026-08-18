"""水面世界命题：纯函数，零 I/O。闸只能否决，不能规定过闸金样句。"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from scribe3.chapter_spine import slot_text
from scribe3.clue_density import WORLD_PHRASE, is_atom_field, split_sents

# 作者/评委分离：闸可读水面并 422，不得向 ASK/extra 注入「必须有一句」金样。
JUDGE_MAY_VETO = True
JUDGE_MAY_NOT_AUTHOR = True

SCHEMA_WORLD_CLAIM = "beats_meta.world_claim.v1"

# 别名只留本模块。禁止把黑针/帘/丝登记为等价词。
CLAIM_ALIASES: dict[str, tuple[str, ...]] = {
    "单向可见": ("单向可见", "单向透明"),
    "指针态": ("指针态",),
    "成核点": ("成核点",),
    "场核": ("场核",),
    "大遮蔽": ("大遮蔽",),
    "真真空": ("真真空", "真真空泡"),
}
FORBIDDEN_ALIAS = frozenset({"黑针", "帘", "丝", "看清水", "涌出的东西"})

HARD_GROUPS = ("goal", "hook")
ALL_GROUPS = ("goal", "cost", "hook", "fact")

CHANGE_VERBS = ("变为", "撕成", "复制", "坍缩", "锚定", "退相干")
CHOICE_TRACE = (" vs ", "还是", "收回", "交", "按回")

PRESS_ROLES = frozenset({"pressor", "extractor"})
OBJECT_CLASS = {
    "world": WORLD_PHRASE,
    "body": ("腕", "腕骨", "肩", "指", "掌", "领"),
    "device": ("针", "碎片", "监测带", "箱"),
    "fabric": ("帘", "丝", "布", "袖", "衣"),
    "token": ("令", "牌", "符"),
    "name": ("名", "真名"),
}
_CLASS_PRIORITY = ("world", "body", "device", "fabric", "token", "name")

_EXTRA_AUTHOR_RE = re.compile(
    r"必须原样|原样使用|原样复述|必须有一句|必须以[「『\"']?时空"
)

assert not (
    FORBIDDEN_ALIAS
    & {a for variants in CLAIM_ALIASES.values() for a in variants}
), "CLAIM_ALIASES 不得登记黑针/帘/丝"


def world_surface_mode() -> str:
    """on | off。设置 DB → env → 默认 on。记录仪接线不看此旗。"""
    raw = ""
    try:
        from scribe3.settings import get_setting
        raw = str(get_setting("SCRIBE3_WORLD_SURFACE") or "").strip().lower()
    except Exception:
        raw = ""
    if not raw:
        raw = str(os.environ.get("SCRIBE3_WORLD_SURFACE") or "").strip().lower()
    if raw in ("off", "0", "false", "no"):
        return "off"
    return "on"


def alias_variants(term: str) -> tuple[str, ...]:
    return CLAIM_ALIASES.get(term, (term,))


def term_in(text: str, term: str) -> bool:
    blob = text or ""
    return any(a and a in blob for a in alias_variants(term))


def phrases_in(text: str) -> tuple[str, ...]:
    blob = text or ""
    out: list[str] = []
    for p in WORLD_PHRASE:
        if p in blob and p not in out:
            out.append(p)
    return tuple(out)


@dataclass(frozen=True)
class WorldClaim:
    id: str
    claim: str
    groups: dict[str, tuple[str, ...]]
    forbidden_paraphrase: tuple[str, ...] = ()

    @property
    def must_show(self) -> tuple[str, ...]:
        seen: list[str] = []
        for g in self.groups.values():
            for t in g:
                if t not in seen:
                    seen.append(t)
        return tuple(seen)


@dataclass
class ClaimPayReport:
    paid: bool = False
    group_hits: dict[str, list[str]] = field(default_factory=dict)
    paraphrase_only: bool = False
    dump_only: bool = False
    sentences: list[str] = field(default_factory=list)


def _is_dump_sentence(sent: str, must_show: tuple[str, ...]) -> bool:
    hits = [p for p in must_show if term_in(sent, p)]
    if len(hits) < 2:
        return False
    if any(v in sent for v in CHANGE_VERBS):
        return False
    if any(t in sent for t in CHOICE_TRACE):
        return False
    return True


def _is_pay_sentence(sent: str) -> bool:
    if not (sent or "").strip():
        return False
    if is_atom_field(sent):
        return True
    return any(v in sent for v in CHANGE_VERBS)


def claim_paid(text: str, claim: WorldClaim) -> ClaimPayReport:
    """只验水面。短槽不要走这个函数。"""
    sents = split_sents(text or "")
    must = claim.must_show
    dump_hits = False
    paying: list[str] = []
    for sent in sents:
        if _is_dump_sentence(sent, must):
            dump_hits = True
            continue
        if _is_pay_sentence(sent):
            paying.append(sent)
    group_hits: dict[str, list[str]] = {}
    for name in ALL_GROUPS:
        terms = tuple(claim.groups.get(name) or ())
        hits = [t for t in terms if any(term_in(s, t) for s in paying)]
        group_hits[name] = hits
    hard_ok = True
    for name in HARD_GROUPS:
        terms = tuple(claim.groups.get(name) or ())
        if terms and not group_hits.get(name):
            hard_ok = False
    para = False
    blob = text or ""
    if any(p in blob for p in (claim.forbidden_paraphrase or FORBIDDEN_ALIAS)):
        if not hard_ok:
            para = True
    paid = hard_ok and not para
    return ClaimPayReport(
        paid=paid,
        group_hits=group_hits,
        paraphrase_only=para,
        dump_only=dump_hits and not hard_ok,
        sentences=sents,
    )


_EXTRA_GOLD_BEAT = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s+)(?:拍\s*|第)\s*\d+"
    r"|(?:^|\n)\s*(?:拍\s*|第)\s*\d+\s*(?:拍|场)?\s*[:：]",
    re.I,
)
_ASK_CONTRACT_MARKERS = (
    "只输出上述标签行",
    "只输出各拍标签行",
    "【章设计合同】",
    "禁止场面预演",
    "禁止「全文≥N字」",
    "缺一不可",
)


def extra_gold(extra: str) -> list[str]:
    """只接受 caller extra。传入 ASK / 合同正文必须返回 []。"""
    blob = extra or ""
    if not blob.strip():
        return []
    if any(m in blob for m in _ASK_CONTRACT_MARKERS):
        return []
    from scribe3.chapter_spine import looks_like_13slot
    if looks_like_13slot(blob):
        return ["extra_gold"]
    if _EXTRA_GOLD_BEAT.search(blob):
        return ["extra_gold"]
    return []


def extra_gold_blocked(extra: str, stage: str | None) -> list[str]:
    stg = (stage or "").strip().lower()
    if stg == "plan":
        stg = "outline"
    if stg == "chapter_design":
        stg = "design"
    if stg not in ("design", "outline", "beats", "plan"):
        return []
    return extra_gold(extra)


def extra_authors(extra: str) -> list[str]:
    if not extra:
        return []
    # ASK/合同里的「禁止必须原样…」不算作者命令
    cleaned = re.sub(r"禁止[^。\n]{0,80}(?:必须原样|原样使用|原样复述|必须有一句|必须以)", "", extra)
    return ["extra_authors"] if _EXTRA_AUTHOR_RE.search(cleaned) else []


def groups_from_spine(ch: Mapping[str, Any] | None) -> dict[str, tuple[str, ...]]:
    src = ch if isinstance(ch, dict) else {}
    spine = src.get("chapter_spine") if isinstance(src.get("chapter_spine"), dict) else {}
    fact = ""
    meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
    wf = meta.get("world_fact")
    if isinstance(wf, dict):
        fact = str(wf.get("text") or "")
    elif wf:
        fact = str(wf)
    return {
        "goal": phrases_in(slot_text(spine.get("goal"))),
        "cost": phrases_in(slot_text(spine.get("cost"))),
        "hook": phrases_in(slot_text(spine.get("hook"))),
        "fact": phrases_in(fact),
    }


def coerce_world_claim(raw: Mapping[str, Any], ch: Mapping[str, Any] | None = None) -> WorldClaim | None:
    src = dict(raw or {})
    groups_raw = src.get("groups")
    groups: dict[str, tuple[str, ...]] = {}
    # 显式 groups（含四组全空）不得回填 spine；缺 groups 才从短槽抽。
    if isinstance(groups_raw, dict):
        for k in ALL_GROUPS:
            vals = groups_raw.get(k) or ()
            groups[k] = tuple(str(x) for x in vals if str(x).strip())
    else:
        groups = groups_from_spine(ch)
    if not any(groups.get(k) for k in ALL_GROUPS):
        return None
    forbid = src.get("forbidden_paraphrase") or tuple(FORBIDDEN_ALIAS)
    return WorldClaim(
        id=str(src.get("id") or "wc.derived"),
        claim=str(src.get("claim") or ""),
        groups=groups,
        forbidden_paraphrase=tuple(str(x) for x in forbid if str(x).strip()),
    )


def load_world_claim(ch: Mapping[str, Any] | None) -> WorldClaim | None:
    src = ch if isinstance(ch, dict) else {}
    meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
    raw = meta.get("world_claim")
    if isinstance(raw, dict) and (raw.get("groups") or raw.get("claim")):
        return coerce_world_claim(raw, src)
    derived = groups_from_spine(src)
    if not any(derived.values()):
        return None
    return WorldClaim(
        id="wc.derived",
        claim=str((meta.get("world_fact") or {}).get("text") if isinstance(meta.get("world_fact"), dict) else "") or "",
        groups=derived,
        forbidden_paraphrase=tuple(FORBIDDEN_ALIAS),
    )


def merge_world_claim(existing: Mapping[str, Any] | None, claim: WorldClaim | None) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if isinstance(existing, dict):
        raw = existing.get("beats_meta")
        meta = dict(raw) if isinstance(raw, dict) else {}
    if claim is None:
        return meta
    meta["world_claim"] = {
        "id": claim.id,
        "claim": claim.claim,
        "groups": {k: list(v) for k, v in claim.groups.items()},
        "forbidden_paraphrase": list(claim.forbidden_paraphrase),
    }
    meta["schema_world_claim"] = SCHEMA_WORLD_CLAIM
    return meta


def _obj_class(blob: str) -> str:
    for cls in _CLASS_PRIORITY:
        toks = OBJECT_CLASS.get(cls) or ()
        if any(t in blob for t in toks):
            return cls
    return "other"


@dataclass(frozen=True)
class GesturePrint:
    roles: frozenset[str]
    obj_class: str
    actor: str


def gesture_fingerprint(spine: dict | None, beats: list | None) -> list[GesturePrint]:
    from scribe3.fate_dearer import _blob_for_cast_role, _cast_blocker_names, cast_role_of

    out: list[GesturePrint] = []
    for name in _cast_blocker_names(spine):
        roles = cast_role_of(name, spine, beats)
        if not roles:
            continue
        blob = _blob_for_cast_role(name, spine, beats)
        out.append(GesturePrint(roles=roles, obj_class=_obj_class(blob), actor=name))
    return out


def gesture_echo(this: list[GesturePrint], prev: list[GesturePrint] | None) -> bool:
    if not this or not prev:
        return False
    prev_by = {p.actor: p for p in prev}
    for cur in this:
        old = prev_by.get(cur.actor)
        if not old:
            continue
        if cur.roles & old.roles & PRESS_ROLES:
            return True
    return False


def surface_of(ch: Mapping[str, Any] | None) -> str:
    src = ch if isinstance(ch, dict) else {}
    return str(src.get("prose") or src.get("draft") or "")

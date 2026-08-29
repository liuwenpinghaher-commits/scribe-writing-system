"""主角色弧光锚生成。写入只走 store.set_char_anchors，不新开旁路。

lie 必须从这个角色自己的命题里立出来，禁止通用人生格言。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Mapping

from scribe3.arc_signals import _char_id, _char_importance, _char_name, is_main_cast_importance
from scribe3.codex_generate import (
    _call_llm,
    _field_in_portrait,
    facts_for_portrait,
    format_portrait_facts,
)

LlmFn = Callable[..., str]
log = logging.getLogger("scribe3.codex_anchors")

ANCHOR_KEYS = ("ghost", "lie", "truth", "want", "need", "arc_type")
ANCHOR_TRIES = 3


def lie_grounded(lie: str, facts) -> bool:
    text = str(lie or "").strip()
    blob = format_portrait_facts(facts)
    if not text or not blob:
        return False
    return _field_in_portrait(text, blob)


def build_anchor_prompt(name: str, facts_text: str, *, retry_hint: str = "") -> str:
    who = (name or "这个人").strip() or "这个人"
    bits = [
        f"根据下面已经发生在{who}身上的事，立他的错误信念（lie）。",
        "lie 必须是这本书里这个人信错的那条，用这些命题里的词来写，"
        "不要写成通用人生格言，不要写「人活着就是为了…」。",
        "同时给 ghost / truth / want / need / arc_type。",
        '只输出一行 JSON：{"ghost":"…","lie":"…","truth":"…","want":"…",'
        '"need":"…","arc_type":"disillusionment"}。',
    ]
    if retry_hint:
        bits.append(retry_hint)
    if (facts_text or "").strip():
        bits.append(facts_text.strip())
    return "\n".join(bits)


def parse_anchor_payload(raw: str) -> dict[str, str]:
    text = str(raw or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return {}
    if not isinstance(obj, dict):
        return {}
    return {k: str(obj.get(k) or "").strip() for k in ANCHOR_KEYS}


def _oid_of(row: Mapping[str, Any] | None) -> str:
    src = row if isinstance(row, dict) else {}
    raw = str(src.get("id") or src.get("oid") or "").strip()
    if raw:
        return raw if ":" in raw else f"role:{raw}"
    name = str(src.get("name") or "").strip()
    return f"role:{name}" if name else ""


def generate_char_anchors(
    st,
    row: Mapping[str, Any] | None,
    *,
    llm_fn: LlmFn,
    persist: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    src = dict(row or {})
    name = str(src.get("name") or "").strip()
    oid = _oid_of(src)
    if not name and oid:
        name = oid.split(":")[-1]
        src["name"] = name
    if oid and not src.get("id"):
        src["id"] = oid

    existing: dict = {}
    if st is not None and hasattr(st, "char_anchors") and oid:
        try:
            existing = st.char_anchors(oid) or {}
        except Exception:
            existing = {}
    if (existing.get("lie") or "").strip() and not force:
        return {
            "ok": True, "skipped": True, "status": "ready",
            "name": name, "id": oid,
        }

    facts = facts_for_portrait(st, "character", src)
    blob = format_portrait_facts(facts)
    if not blob:
        return {
            "ok": False, "code": "no_facts", "name": name, "id": oid,
            "message": "这个人没有自己的命题，立不出错误信念",
        }

    hint = ""
    parsed: dict[str, str] = {}
    for _rnd in range(ANCHOR_TRIES):
        raw = _call_llm(llm_fn, build_anchor_prompt(name, blob, retry_hint=hint), 1024)
        parsed = parse_anchor_payload(raw)
        lie = parsed.get("lie") or ""
        if lie and lie_grounded(lie, facts):
            break
        hint = "刚才的 lie 没有落在这些命题里。从命题里抄一句他信错的话，不要另编格言。"
        parsed = {}

    lie = (parsed.get("lie") or "").strip()
    if not lie or not lie_grounded(lie, facts):
        return {
            "ok": False, "code": "ungrounded", "name": name, "id": oid,
            "message": "lie 没有落在这个人自己的命题里",
        }

    anchors = {k: v for k, v in parsed.items() if str(v).strip()}
    if persist and st is not None and hasattr(st, "set_char_anchors") and oid:
        st.set_char_anchors(oid, anchors)
    return {
        "ok": True, "name": name, "id": oid,
        "anchors": anchors, "source": "llm",
    }


def generate_missing_main_anchors(
    st,
    *,
    llm_fn: LlmFn,
    persist: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    if st is None or not hasattr(st, "characters"):
        return {"items": items}
    for char in st.characters() or []:
        imp = _char_importance(char)
        if not is_main_cast_importance(imp):
            continue
        name = _char_name(char)
        oid = _char_id(char) or (f"role:{name}" if name else "")
        traits = getattr(char, "traits", None)
        row = {"name": name, "id": oid, "importance": imp}
        if isinstance(traits, dict):
            row.update({k: v for k, v in traits.items() if v not in (None, "", [], {})})
        try:
            out = generate_char_anchors(
                st, row, llm_fn=llm_fn, persist=persist, force=force,
            )
        except Exception as e:
            log.warning("generate_char_anchors %s failed: %s", name, e)
            out = {"ok": False, "code": "exception", "name": name, "id": oid,
                   "message": str(e)}
        if out.get("skipped"):
            continue
        items.append({
            "name": name, "id": oid,
            "ok": bool(out.get("ok")),
            "status": ("ok" if out.get("ok") else out.get("code") or "fail"),
            "lie": ((out.get("anchors") or {}).get("lie") if out.get("ok") else ""),
            "message": out.get("message"),
        })
    return {"items": items}

"""chapter_state.v1：章末世界快照。只抄不编，每条人物/物件必须带正文锚句。"""
from __future__ import annotations

from typing import Any

SCHEMA_NAME = "chapter_state.v1"
FACT_KEYS = ("seq", "characters", "objects", "open_loops", "timeline", "imagery", "narrative_pov")
_GENDER_OK = frozenset({"", "男", "女"})


def snapshot_body(rec: dict[str, Any] | None) -> dict[str, Any]:
    """从冻结信封里抽出事实层，供注入 prompt。缺失则空快照。"""
    if not isinstance(rec, dict):
        return {}
    out: dict[str, Any] = {}
    for k in FACT_KEYS:
        if k in rec:
            out[k] = rec.get(k)
    return out


def check_chapter_state_schema(state: dict[str, Any]) -> dict[str, Any]:
    """形状闸。ok / code / message，与 structural._fail 同构。"""
    if not isinstance(state, dict):
        return {"ok": False, "code": "state_shape", "message": "章末态不是对象"}
    try:
        seq = int(state.get("seq") or 0)
    except (TypeError, ValueError):
        return {"ok": False, "code": "state_seq", "message": "seq 必须是整数", "field": "seq"}
    if seq < 1:
        return {"ok": False, "code": "state_seq", "message": "seq 必须 ≥1", "field": "seq"}

    chars = state.get("characters")
    if not isinstance(chars, list) or not chars:
        return {"ok": False, "code": "state_chars", "message": "characters 不能空"}
    for i, ch in enumerate(chars):
        if not isinstance(ch, dict):
            return {"ok": False, "code": "state_char_shape", "message": f"characters[{i}] 不是对象"}
        if not str(ch.get("name") or "").strip():
            return {"ok": False, "code": "state_char_name", "message": f"characters[{i}] 缺 name", "field": f"characters[{i}].name"}
        if not str(ch.get("state") or "").strip():
            return {"ok": False, "code": "state_char_state", "message": f"characters[{i}] 缺 state", "field": f"characters[{i}].state"}
        if not str(ch.get("quote") or "").strip():
            return {"ok": False, "code": "quote_missing", "message": f"characters[{i}] 缺 quote", "field": f"characters[{i}].quote"}
        g = str(ch.get("gender") or "").strip()
        if g not in _GENDER_OK:
            return {"ok": False, "code": "state_gender", "message": f"characters[{i}] gender 只许空/男/女", "field": f"characters[{i}].gender"}

    objs = state.get("objects")
    if objs is None:
        objs = []
        state["objects"] = objs
    if not isinstance(objs, list):
        return {"ok": False, "code": "state_objects", "message": "objects 必须是列表"}
    for i, obj in enumerate(objs):
        if not isinstance(obj, dict):
            return {"ok": False, "code": "state_obj_shape", "message": f"objects[{i}] 不是对象"}
        if not str(obj.get("name") or "").strip():
            return {"ok": False, "code": "state_obj_name", "message": f"objects[{i}] 缺 name", "field": f"objects[{i}].name"}
        if not str(obj.get("location") or "").strip():
            return {"ok": False, "code": "state_obj_loc", "message": f"objects[{i}] 缺 location", "field": f"objects[{i}].location"}
        if not str(obj.get("quote") or "").strip():
            return {"ok": False, "code": "quote_missing", "message": f"objects[{i}] 缺 quote", "field": f"objects[{i}].quote"}

    loops = state.get("open_loops")
    if loops is None:
        loops = []
        state["open_loops"] = loops
    if not isinstance(loops, list):
        return {"ok": False, "code": "state_loops", "message": "open_loops 必须是列表"}
    for i, loop in enumerate(loops):
        if not isinstance(loop, dict):
            return {"ok": False, "code": "state_loop_shape", "message": f"open_loops[{i}] 不是对象"}
        if not str(loop.get("text") or "").strip():
            return {"ok": False, "code": "state_loop_text", "message": f"open_loops[{i}] 缺 text", "field": f"open_loops[{i}].text"}
        try:
            frm = int(loop.get("from_seq") or 0)
            due = int(loop.get("due_seq") or 0)
        except (TypeError, ValueError):
            return {"ok": False, "code": "state_loop_seq", "message": f"open_loops[{i}] from_seq/due_seq 必须是整数"}
        if frm < 1 or due < frm:
            return {"ok": False, "code": "state_loop_seq", "message": f"open_loops[{i}] due_seq 必须 ≥ from_seq ≥ 1"}

    timeline = state.get("timeline")
    if timeline in (None, ""):
        state["timeline"] = {"at": "", "elapsed_from_prev": ""}
    elif not isinstance(timeline, dict):
        return {"ok": False, "code": "state_timeline", "message": "timeline 必须是对象"}

    imagery = state.get("imagery")
    if imagery in (None, ""):
        state["imagery"] = []
    elif not isinstance(imagery, list):
        return {"ok": False, "code": "state_imagery", "message": "imagery 必须是列表"}

    pov = str(state.get("narrative_pov") or "").strip()
    if pov and pov not in ("first", "third"):
        return {"ok": False, "code": "state_pov", "message": "narrative_pov 只许 first/third/空", "field": "narrative_pov"}

    return {"ok": True}

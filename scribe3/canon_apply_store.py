"""将 ChangeItem / candidate 应用到 SurrealStore（真写）。"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from scribe3.canon_loop import ChangeItem, item_requires_human_approval

_log = logging.getLogger("scribe3.canon_apply")


def apply_item_to_store(st: Any, item: ChangeItem | dict) -> dict[str, Any]:
    """对单个已批准 item 写 Surreal。失败返回 status=error。"""
    if isinstance(item, dict):
        module = (item.get("module") or "").strip().lower()
        op = (item.get("op") or "patch").strip()
        target = (item.get("target") or "").strip()
        field = item.get("field")
        after = item.get("after")
        item_id = item.get("id") or ""
        layer = item.get("layer") or "L1"
    else:
        module = (item.module or "").strip().lower()
        op = (item.op or "patch").strip()
        target = (item.target or "").strip()
        field = item.field
        after = item.after
        item_id = item.id
        layer = item.layer

    if item_requires_human_approval(layer, module):
        # caller must have checked approval; still re-assert module
        pass

    bare = target.split(":")[-1] if target else ""
    try:
        if module == "character":
            return _apply_character(st, bare, target, field, after, op)
        if module == "world_rule":
            return _apply_world_rule(st, bare or target, field, after, op)
        if module == "faction":
            return _apply_faction(st, bare or target, field, after, op)
        if module == "item":
            return _apply_item(st, bare or target, field, after, op)
        if module == "term":
            return _apply_term(st, bare or target, field, after, op)
        if module == "fact":
            return _apply_fact(st, target, field, after, op)
        if module == "knowledge":
            return _apply_knowledge(st, target, field, after)
        if module == "relation":
            return _apply_relation(st, target, field, after)
        if module == "promise":
            return _apply_promise(st, target, field, after, op)
        if module == "motif":
            return _apply_motif(st, target, field, after, op)
        if module == "char_state":
            return _apply_char_state(st, target, field, after)
        if module == "intent":
            return _apply_intent(st, field, after)
        return {"status": "error", "error": f"unsupported module {module}", "item_id": item_id}
    except Exception as e:
        _log.warning("apply_item_to_store fail module=%s target=%s: %s", module, target, e)
        return {"status": "error", "error": str(e)[:200], "item_id": item_id, "module": module}


def _apply_character(st, bare, target, field, after, op) -> dict:
    from scribe3.ontology import Entity
    oid = target if target.startswith("role:") else f"role:{bare}"
    local = bare
    if op == "add" or (hasattr(st, "entity") and st.entity(oid) is None):
        name = after.get("name") if isinstance(after, dict) else local
        if isinstance(after, dict):
            name = after.get("name") or local
            traits = {k: v for k, v in after.items() if k != "name"}
        else:
            traits = {field: after} if field else {}
        st.add_entity(Entity(oid, "character", str(name or local), traits=traits if isinstance(traits, dict) else {}))
        if traits and hasattr(st, "update_record"):
            st.update_record(oid, traits if isinstance(traits, dict) else {field or "note": after})
        return {"status": "written", "module": "character", "oid": oid, "op": "add"}
    fields = after if isinstance(after, dict) else ({field: after} if field else {"note": after})
    if hasattr(st, "update_record"):
        st.update_record(oid, fields)
    elif hasattr(st, "patch_character"):
        st.patch_character(oid, **fields)
    else:
        raise RuntimeError("no character write API")
    return {"status": "written", "module": "character", "oid": oid, "fields": list(fields.keys())}


def _apply_world_rule(st, name, field, after, op) -> dict:
    if op == "add" or (hasattr(st, "list_world_rules") and not any(
        (r.get("name") == name) for r in (st.list_world_rules() or [])
    )):
        kwargs = after if isinstance(after, dict) else {}
        cat = kwargs.get("category") or "social"
        st.add_world_rule(
            name=name,
            category=cat,
            source=kwargs.get("source"),
            capabilities=kwargs.get("capabilities"),
            cost=kwargs.get("cost") if not field else (after if field == "cost" else kwargs.get("cost")),
            limitations=kwargs.get("limitations"),
            exceptions=kwargs.get("exceptions"),
            scope=kwargs.get("scope") or "global",
            established_chapter=kwargs.get("established_chapter"),
            note=kwargs.get("note") if not field else (after if field == "note" else kwargs.get("note")),
        )
        if field and field not in ("category", "name") and not isinstance(after, dict):
            if hasattr(st, "patch_world_rule"):
                st.patch_world_rule(name, {field: after})
        return {"status": "written", "module": "world_rule", "name": name, "op": "add"}
    fields = after if isinstance(after, dict) else ({field: after} if field else {"note": after})
    if hasattr(st, "patch_world_rule"):
        st.patch_world_rule(name, fields)
    return {"status": "written", "module": "world_rule", "name": name, "fields": list(fields.keys())}


def _apply_faction(st, name, field, after, op) -> dict:
    if op == "add":
        kw = after if isinstance(after, dict) else {}
        st.add_faction(name, **{k: v for k, v in kw.items() if k != "name"})
        return {"status": "written", "module": "faction", "name": name, "op": "add"}
    # patch via re-add fields if available
    if hasattr(st, "add_faction"):
        kw = after if isinstance(after, dict) else ({field: after} if field else {})
        try:
            st.add_faction(name, **kw)
        except Exception:
            pass
    return {"status": "written", "module": "faction", "name": name}


def _apply_item(st, name, field, after, op) -> dict:
    if op == "add" or not hasattr(st, "patch_item"):
        kw = after if isinstance(after, dict) else {}
        st.add_item(name=name, category=kw.get("category"), description=kw.get("description") or (after if isinstance(after, str) else None),
                    current_owner=kw.get("current_owner"), symbolic_state=kw.get("symbolic_state"),
                    special_properties=kw.get("special_properties"), first_chapter=kw.get("first_chapter"))
        if field and not isinstance(after, dict) and hasattr(st, "patch_item"):
            st.patch_item(name, {field: after})
        return {"status": "written", "module": "item", "name": name}
    fields = after if isinstance(after, dict) else ({field: after} if field else {"description": after})
    st.patch_item(name, fields)
    return {"status": "written", "module": "item", "name": name}


def _apply_term(st, name, field, after, op) -> dict:
    if op == "add":
        kw = after if isinstance(after, dict) else {}
        st.add_term(name=name, category=kw.get("category"),
                    definition=kw.get("definition") or (after if isinstance(after, str) else None),
                    aliases=kw.get("aliases"), first_mention_chapter=kw.get("first_mention_chapter"))
        return {"status": "written", "module": "term", "name": name}
    fields = after if isinstance(after, dict) else ({field: after} if field else {"definition": after})
    if hasattr(st, "patch_term"):
        st.patch_term(name, fields)
    return {"status": "written", "module": "term", "name": name}


def _apply_fact(st, target, field, after, op) -> dict:
    from scribe3.ontology import Fact
    # target may be fact:oid or entity; field=attribute; after=value
    if isinstance(after, dict):
        entity = after.get("entity") or target
        attr = after.get("attribute") or field or "note"
        value = after.get("value") or after.get("after") or ""
        secret = bool(after.get("secret"))
        oid = after.get("oid") or target if str(target).startswith("fact:") else f"fact:{uuid.uuid4().hex[:8]}"
    else:
        entity = target if ":" in str(target) else f"role:{target}"
        attr = field or "note"
        value = after
        secret = False
        oid = f"fact:{uuid.uuid4().hex[:8]}"
    st.add_fact(Fact(oid, str(entity), str(attr), str(value), secret=secret))
    return {"status": "written", "module": "fact", "oid": oid}


def _apply_knowledge(st, knower, proposition, via) -> dict:
    from scribe3.ontology import KnowledgeEdge
    knower_id = knower if str(knower).startswith("role:") or knower == "reader" else f"role:{knower}"
    prop = proposition if str(proposition).startswith("fact:") else f"fact:{proposition}"
    # ensure prop exists lightly
    if hasattr(st, "entity") and st.entity(prop) is None and hasattr(st, "add_fact"):
        from scribe3.ontology import Fact
        try:
            st.add_fact(Fact(prop, knower_id, "from_knowledge", str(via or "knows")))
        except Exception:
            pass
    via_s = via if isinstance(via, str) else "saw"
    st.add_knowledge(KnowledgeEdge(knower_id, prop, since_chapter=1, acquired_via=via_s if via_s in (
        "saw", "told", "inferred", "given", "learned") else "saw"))
    return {"status": "written", "module": "knowledge", "knower": knower_id, "proposition": prop}


def _apply_relation(st, target, field, after) -> dict:
    # target "role:A|role:B" or after dict
    if isinstance(after, dict):
        src = after.get("src") or after.get("a") or ""
        dst = after.get("dst") or after.get("b") or ""
        rel = after.get("relation") or field or "关联"
        since = int(after.get("since_chapter") or 1)
    else:
        parts = (target or "").split("|")
        src, dst = (parts + ["", ""])[:2]
        rel = field or str(after) or "关联"
        since = 1
    if not src.startswith("role:"):
        src = f"role:{src}"
    if not dst.startswith("role:"):
        dst = f"role:{dst}"
    st.add_character_relation(src, dst, rel, since_chapter=since)
    return {"status": "written", "module": "relation", "src": src, "dst": dst}


def _apply_promise(st, target, field, after, op) -> dict:
    if op in ("add", "plant") or not target:
        text = after if isinstance(after, str) else (after or {}).get("text") or target
        setup = int((after or {}).get("setup_chapter") or 1) if isinstance(after, dict) else 1
        row = st.plant_promise(str(text), setup)
        return {"status": "written", "module": "promise", "promise": row}
    if op == "advance" and hasattr(st, "advance_promise"):
        ch = int(after) if not isinstance(after, dict) else int(after.get("payoff_chapter") or 1)
        st.advance_promise(target, ch)
        return {"status": "written", "module": "promise", "id": target, "op": "advance"}
    return {"status": "error", "error": "promise op unsupported"}


def _apply_motif(st, target, field, after, op) -> dict:
    if hasattr(st, "add_motif") and op == "add":
        name = after.get("name") if isinstance(after, dict) else (target or after)
        st.add_motif(name=str(name))
        return {"status": "written", "module": "motif", "name": name}
    if hasattr(st, "patch_motif") and target:
        fields = after if isinstance(after, dict) else ({field: after} if field else {})
        st.patch_motif(target, fields)
        return {"status": "written", "module": "motif", "id": target}
    return {"status": "error", "error": "motif write unavailable"}


def _apply_char_state(st, target, field, after) -> dict:
    oid = target if str(target).startswith("role:") else f"role:{target}"
    if isinstance(after, dict):
        st.add_char_state(
            character_id=oid,
            chapter=int(after.get("chapter") or 1),
            change_type=after.get("change_type") or field or "arc",
            summary=after.get("summary") or after.get("after") or "",
        )
    else:
        st.add_char_state(character_id=oid, chapter=1, change_type=field or "arc", summary=str(after))
    return {"status": "written", "module": "char_state", "character_id": oid}


def _apply_intent(st, field, after) -> dict:
    fields = after if isinstance(after, dict) else ({field: after} if field else {})
    if hasattr(st, "set_intent"):
        st.set_intent(fields)
        return {"status": "written", "module": "intent", "fields": list(fields.keys())}
    return {"status": "error", "error": "no set_intent"}

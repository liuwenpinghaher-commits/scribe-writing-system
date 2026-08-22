"""DED-09：讨论产出相对正典的矛盾提示，不阻断。"""
from __future__ import annotations

from typing import Any


def validate_discussion_claims(text: str, canon_snapshot: dict | None = None) -> list[dict[str, Any]]:
    """打开讨论稿，问：有没有跟已经立下的人/规矩对着干。"""
    flags: list[dict[str, Any]] = []
    body = str(text or "")
    snap = canon_snapshot if isinstance(canon_snapshot, dict) else {}
    known: set[str] = set()
    chars = snap.get("characters") or snap.get("character_names") or []
    if isinstance(chars, dict):
        known.update(str(k) for k in chars.keys())
    else:
        for c in chars:
            if isinstance(c, dict):
                known.add(str(c.get("name") or c.get("id") or ""))
            else:
                known.add(str(c))
    known = {n.strip() for n in known if n and str(n).strip()}
    rules = snap.get("world_rules") or {}
    rule_names: list[str] = []
    if isinstance(rules, dict):
        rule_names = [str(k) for k in rules.keys() if k]
    elif isinstance(rules, list):
        for r in rules:
            if isinstance(r, dict) and r.get("name"):
                rule_names.append(str(r["name"]))
            elif r:
                rule_names.append(str(r))
    deny = ("不是", "并无", "没有这号", "不存在", "从未立过")
    for name in list(known)[:40]:
        if len(name) < 2:
            continue
        for d in deny:
            if name in body and d in body and body.find(d) - 20 <= body.find(name) <= body.find(d) + 40:
                flags.append({
                    "code": "contradict_character",
                    "target": name,
                    "message": f"讨论里否认了已经立档的人「{name}」。",
                })
                break
    for name in rule_names[:20]:
        if len(name) < 2:
            continue
        for d in deny:
            if name in body and d in body:
                flags.append({
                    "code": "contradict_world_rule",
                    "target": name,
                    "message": f"讨论里否认了已经立下的规矩「{name}」。",
                })
                break
    return flags

"""Assemble generator/judge context from a live store. Soft-fail on missing pieces."""
from __future__ import annotations

from typing import Any


def _clean_name(n: str) -> str:
    s = str(n or "").strip()
    if s.startswith("role:"):
        s = s[5:]
    return s.strip()


def _names(rows: list[Any]) -> list[str]:
    out: list[str] = []
    for r in rows or []:
        n = ""
        if isinstance(r, dict):
            n = r.get("name") or r.get("id") or r.get("label") or ""
        else:
            n = getattr(r, "name", None) or getattr(r, "id", None) or ""
            if not n:
                n = str(r or "")
        n = _clean_name(n)
        if n:
            out.append(n)
    return out


def secret_list(st: Any) -> list[str]:
    """本章还不能拆穿的事：红线 + 标了私密的命题。"""
    out: list[str] = []
    getter = getattr(st, "get_intent", None)
    if callable(getter):
        try:
            red = (getter() or {}).get("red_lines") or ""
        except Exception:
            red = ""
        for line in str(red).splitlines():
            hit = line.strip()
            if hit:
                out.append(hit)
    secrets_fn = getattr(st, "_secret_proposition_values", None)
    if callable(secrets_fn):
        try:
            for v in secrets_fn() or []:
                s = str(v or "").strip()
                if s:
                    out.append(s)
        except Exception:
            pass
    seen: set[str] = set()
    uniq: list[str] = []
    for item in out:
        if item not in seen:
            seen.add(item)
            uniq.append(item)
    return uniq


def available_cast(st: Any) -> list[str]:
    for name in ("list_characters", "characters", "list_character_names"):
        fn = getattr(st, name, None)
        if callable(fn):
            try:
                return _names(fn() or [])
            except Exception:
                continue
    return []


def available_lines(st: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for name in ("list_promises", "promises"):
        fn = getattr(st, name, None)
        if not callable(fn):
            continue
        try:
            rows = fn() or []
        except Exception:
            rows = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            pid = str(r.get("id") or r.get("promise_id") or "")
            text = str(r.get("text") or r.get("body") or r.get("title") or "")
            if pid:
                out.append({"kind": "promise", "id": pid, "text": text})
    return out


def prev_hook_quote(store: Any, seq: int) -> str | None:
    if int(seq) <= 1:
        return None
    fn = getattr(store, "get_frozen", None)
    if not callable(fn):
        return None
    contract = fn("chapter_contract", int(seq) - 1)
    if not isinstance(contract, dict):
        return None
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    hook = fields.get("hook") if isinstance(fields.get("hook"), dict) else {}
    q = hook.get("quote")
    return str(q) if q else None


def prev_play_with_hook(quote: str) -> dict[str, Any]:
    """Contract-shaped stub whose hook.quote is the bite source."""
    q = str(quote or "")
    return {"fields": {"hook": {"text": q, "quote": q}}}


def make_duty(prev: dict[str, Any] | None = None, *, seq: int = 2, **fields: Any) -> dict[str, Any]:
    """Mechanical bite: copy previous hook.quote. LLM never invents this field."""
    hook = None
    if int(seq) > 1 and isinstance(prev, dict):
        if "fields" in prev:
            hook = ((prev.get("fields") or {}).get("hook") or {}).get("quote")
        elif "text" in prev:
            # allow passing a play; bite still comes from a contract hook if present
            hook = (prev.get("hook") or {}).get("quote") if isinstance(prev.get("hook"), dict) else None
    return {
        "seq": int(seq),
        "who": list(fields.get("who") or ["沈烛若"]),
        "must_happen": fields.get("must_happen") or "办事",
        "bill": fields.get("bill") or "付账",
        "forbidden_reveal": list(fields.get("forbidden_reveal") or ["秘密"]),
        "bite_from_prev": None if int(seq) == 1 else hook,
        "focalizer": fields.get("focalizer") or "沈烛若",
        "available_cast": list(fields.get("available_cast") or ["沈烛若"]),
        "available_lines": list(fields.get("available_lines") or []),
        "line_to_touch": fields.get("line_to_touch"),
    }


def build_ctx(store: Any, seq: int, *, focalizer: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "seq": int(seq),
        "focalizer": focalizer,
        "available_cast": available_cast(store),
        "available_lines": available_lines(store),
        "prev_hook_quote": prev_hook_quote(store, seq),
        "secret_list": secret_list(store),
    }
    if extra:
        ctx.update(extra)
    return ctx

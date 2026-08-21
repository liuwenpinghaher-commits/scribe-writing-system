"""讨论查阅：进程内闭集只读工具。work 只信 HTTP 请求，不信模型参数。"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

log = logging.getLogger("scribe3.discuss")

DISCUSS_TOOL_NAMES = frozenset({
    "s3_setting_completeness",
    "s3_list_promises",
    "s3_resolve_entities",
    "s3_character_state",
    "s3_get_chapter",
    "s3_semantic_recall",
    "s3_chapter_recall",
    "s3_list_chapters",
})

MAX_DISCUSS_TOOL_ROUNDS = 4
_CHAPTER_SYNOPSIS_CHARS = 800
_BEAT_TEXT_CHARS = 200
_PROSE_HEAD = 800
_PROSE_TAIL = 400
_PROSE_CAP = 1200
_STRIP_CHAPTER_KEYS = (
    "prose", "draft", "play", "narrative_contract", "scene_truth",
    "deductions", "post_analysis", "pressure_drive",
)

# 可单测计数；不复用 cross_work_rejections。
discuss_work_rewrite_count = 0
discuss_tool_blocked_count = 0
discuss_tool_rounds_last = 0


def reset_discuss_metrics_for_test() -> None:
    global discuss_work_rewrite_count, discuss_tool_blocked_count, discuss_tool_rounds_last
    discuss_work_rewrite_count = 0
    discuss_tool_blocked_count = 0
    discuss_tool_rounds_last = 0


def record_discuss_work_rewrite(*, attempted: str, pinned: str) -> None:
    global discuss_work_rewrite_count
    discuss_work_rewrite_count += 1
    log.info(
        "discuss_work_rewrite attempted=%s pinned=%s count=%s",
        attempted[:80], pinned, discuss_work_rewrite_count,
    )


def record_discuss_tool_blocked(name: str) -> None:
    global discuss_tool_blocked_count
    discuss_tool_blocked_count += 1
    log.info("discuss_tool_blocked name=%s count=%s", name, discuss_tool_blocked_count)


def record_discuss_tool_rounds(n: int) -> None:
    global discuss_tool_rounds_last
    discuss_tool_rounds_last = int(n)
    log.info("discuss_tool_rounds n=%s", n)


def can_execute_discuss_round(round_number: int) -> bool:
    """round_number 从 1 计。第 5 批及以后不执行。"""
    return 1 <= int(round_number) <= MAX_DISCUSS_TOOL_ROUNDS


def _normalize_work(work: str | None) -> str:
    from scribe3.api.app_impl import _normalize_work as _nw
    return _nw(work)


def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if hasattr(obj, "id") and hasattr(obj, "entity_id"):
        return {
            "id": getattr(obj, "id", None),
            "entity": getattr(obj, "entity_id", None),
            "attribute": getattr(obj, "attribute", None),
            "value": getattr(obj, "value", None),
            "secret": bool(getattr(obj, "secret", False)),
            "valid_from": getattr(obj, "valid_from", None),
            "valid_to": getattr(obj, "valid_to", None),
        }
    return str(obj)[:500]


def _mask_secret(value: Any, is_secret: bool) -> Any:
    if is_secret:
        return "🔒 私密"
    return value


def _recall_rows(facts) -> list[dict]:
    rows = []
    for f in facts or []:
        if isinstance(f, dict):
            secret = bool(f.get("secret") or f.get("is_secret"))
            rows.append({
                "id": f.get("id"),
                "entity": f.get("entity") or f.get("entity_id"),
                "attribute": f.get("attribute"),
                "value": _mask_secret(f.get("value"), secret),
                "is_secret": secret,
                "valid_from": f.get("valid_from"),
                "valid_to": f.get("valid_to"),
            })
            continue
        secret = bool(getattr(f, "secret", False))
        rows.append({
            "id": getattr(f, "id", None),
            "entity": getattr(f, "entity_id", None),
            "attribute": getattr(f, "attribute", None),
            "value": _mask_secret(getattr(f, "value", None), secret),
            "is_secret": secret,
            "valid_from": getattr(f, "valid_from", None),
            "valid_to": getattr(f, "valid_to", None),
        })
    return rows


def _clip(text: Any, n: int) -> str:
    s = str(text or "")
    if len(s) <= n:
        return s
    return s[:n]


def project_chapter_for_discuss(ch: dict | None, *, include_prose: bool = False) -> dict:
    """讨论读章默认无正文。include_prose=true 时头 800 + 尾 400，总帽 1200。"""
    raw = dict(ch or {})
    prose = raw.get("prose") or ""
    prose_s = str(prose)
    beats_in = raw.get("beats") or []
    beats = []
    if isinstance(beats_in, list):
        for b in beats_in:
            if isinstance(b, dict):
                item = dict(b)
                if "text" in item:
                    item["text"] = _clip(item.get("text"), _BEAT_TEXT_CHARS)
                beats.append(item)
            else:
                beats.append(_clip(b, _BEAT_TEXT_CHARS))
    out = {
        "seq": raw.get("seq"),
        "title": raw.get("title") or "",
        "synopsis": _clip(raw.get("synopsis"), _CHAPTER_SYNOPSIS_CHARS),
        "beats": beats,
        "has_prose": bool(prose_s.strip()),
        "prose_chars": len(prose_s),
    }
    foc = raw.get("focalizer")
    if foc:
        out["focalizer"] = foc
    if include_prose and prose_s:
        if len(prose_s) <= _PROSE_CAP:
            out["prose"] = prose_s
        else:
            head = prose_s[:_PROSE_HEAD]
            tail = prose_s[-_PROSE_TAIL:]
            out["prose"] = head + "…[中间已截断]…" + tail
            if len(out["prose"]) > _PROSE_CAP + 20:
                out["prose"] = out["prose"][:_PROSE_CAP]
    for k in _STRIP_CHAPTER_KEYS:
        if k == "prose" and include_prose:
            continue
        out.pop(k, None)
        assert k not in out or (k == "prose" and include_prose)
    return out


def _dispatch(name: str, st, args: dict) -> Any:
    if name == "s3_setting_completeness":
        return st.setting_completeness() if hasattr(st, "setting_completeness") else {}
    if name == "s3_list_promises":
        return _jsonable(st.list_promises() if hasattr(st, "list_promises") else [])
    if name == "s3_resolve_entities":
        text = str(args.get("text") or "")
        chapter = args.get("chapter")
        if chapter is None:
            chapter = 9999
        return _jsonable(st.resolve_entities(text, int(chapter)))
    if name == "s3_character_state":
        cid = str(args.get("character_id") or "")
        chapter = int(args.get("chapter") or 0)
        if hasattr(st, "char_state_at"):
            return _jsonable(st.char_state_at(cid, chapter) or {})
        return {}
    if name == "s3_get_chapter":
        seq = int(args.get("seq") or 0)
        ch = st.get_chapter(seq) if hasattr(st, "get_chapter") else {}
        include = args.get("include_prose")
        flag = include is True or str(include).lower() in ("1", "true", "yes")
        return project_chapter_for_discuss(ch if isinstance(ch, dict) else {}, include_prose=flag)
    if name == "s3_semantic_recall":
        query = str(args.get("query") or "")
        k = int(args.get("k") or 5)
        chapter = args.get("chapter")
        kw = {}
        if chapter is not None and str(chapter) != "":
            kw["chapter"] = int(chapter)
        facts = st.semantic_recall(query, k, **kw) if hasattr(st, "semantic_recall") else []
        return _recall_rows(facts)
    if name == "s3_chapter_recall":
        query = str(args.get("query") or "")
        k = int(args.get("k") or 5)
        rows = st.chapter_recall(query, k) if hasattr(st, "chapter_recall") else []
        return _jsonable(rows)
    if name == "s3_list_chapters":
        rows = st.list_chapters() if hasattr(st, "list_chapters") else []
        out = []
        for row in rows or []:
            d = dict(row) if isinstance(row, dict) else {"title": str(row)}
            prose = str(d.get("prose") or "")
            item = {
                "seq": d.get("seq"),
                "title": d.get("title") or "",
                "volume": d.get("volume") or d.get("volume_id"),
                "focalizer": d.get("focalizer"),
                "has_prose": bool(prose.strip()),
                "prose_chars": len(prose),
            }
            out.append(item)
        return out
    raise ValueError(f"undispatched {name}")


def execute_discuss_tool(
    name: str,
    arguments: dict | None,
    *,
    work: str,
    store=None,
    store_for: Callable[[str], Any] | None = None,
) -> dict:
    """执行一把讨论工具。模型传入的 work 一律丢弃，命中请求书。"""
    trusted = _normalize_work(work)
    args = dict(arguments or {})
    attempted = args.pop("work", None)
    if attempted not in (None, "", trusted):
        record_discuss_work_rewrite(attempted=str(attempted), pinned=trusted)
    if not name or name not in DISCUSS_TOOL_NAMES:
        record_discuss_tool_blocked(str(name or ""))
        return {"error": "tool_not_allowed", "name": name}
    if store is not None:
        st = store
    elif store_for is not None:
        st = store_for(trusted)
    else:
        from scribe3.api.app_impl import _store_for
        st = _store_for(trusted)
    try:
        result = _dispatch(name, st, args)
    except Exception as e:
        log.warning("discuss tool %s failed: %s", name, e, exc_info=True)
        return {"error": type(e).__name__, "message": str(e)[:200], "name": name}
    payload = _jsonable(result)
    if isinstance(payload, dict):
        payload.setdefault("work", getattr(st, "db_name", None) or trusted)
        return payload
    return {"data": payload, "work": getattr(st, "db_name", None) or trusted}


def discuss_function_tools() -> list[dict]:
    """Responses `type=function` 闭集，不含 work 参数、不含 MCP。"""
    return [
        {
            "type": "function",
            "name": "s3_setting_completeness",
            "description": "这本书设定还缺哪些维度",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "type": "function",
            "name": "s3_list_promises",
            "description": "列出伏笔开着哪些",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "type": "function",
            "name": "s3_resolve_entities",
            "description": "把代词或别名解析成这本书里的人/设定",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "chapter": {"type": "integer"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "s3_character_state",
            "description": "某人在某章时刻的状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "chapter": {"type": "integer"},
                },
                "required": ["character_id", "chapter"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "s3_get_chapter",
            "description": "读某章结构。默认无正文；不要为了复述去读整章。",
            "parameters": {
                "type": "object",
                "properties": {
                    "seq": {"type": "integer"},
                    "include_prose": {"type": "boolean"},
                },
                "required": ["seq"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "s3_semantic_recall",
            "description": "按语义检索设定（秘密字段保持打码）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer"},
                    "chapter": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "s3_chapter_recall",
            "description": "哪几章接近这句话",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "s3_list_chapters",
            "description": "章清单（序号/标题/结构元数据，无正文）",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


def dumps_tool_result(payload: Any, *, cap: int = 8000) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        text = str(payload)
    if len(text) > cap:
        return text[:cap] + "…"
    return text

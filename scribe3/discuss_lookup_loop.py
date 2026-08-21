"""讨论查阅循环：Scribe 进程内执行闭集，最多四轮，不打 MCP。"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from scribe3.discuss_tools import (
    MAX_DISCUSS_TOOL_ROUNDS,
    can_execute_discuss_round,
    discuss_function_tools,
    dumps_tool_result,
    execute_discuss_tool,
    record_discuss_tool_rounds,
)

log = logging.getLogger("scribe3.discuss")

_STOP_LOOKUP_HINT = "停止查阅，根据已有结果回答。"


def _parse_args(raw: Any) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            v = json.loads(raw)
            return dict(v) if isinstance(v, dict) else {}
        except Exception:
            return {}
    return {}


def _fingerprint(name: str, args: dict) -> tuple[str, str]:
    try:
        blob = json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        blob = str(args)
    return (name or "", blob)


def collect_function_calls(event: dict) -> dict | None:
    source = event.get("type") or event.get("event") or ""
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    if source == "response.output_item.added" and item.get("type") == "function_call":
        name = item.get("name") or event.get("name") or ""
        if isinstance(name, str) and "_s3_" in name:
            name = name[name.index("s3_"):]
        return {
            "name": name,
            "arguments": _parse_args(item.get("arguments") or event.get("arguments")),
            "call_id": item.get("call_id") or event.get("call_id") or "",
        }
    if source in {"tool.start", "tool.started"}:
        name = event.get("name") or event.get("tool_name") or ""
        if isinstance(name, str) and "_s3_" in name:
            name = name[name.index("s3_"):]
        if name:
            return {
                "name": name,
                "arguments": _parse_args(event.get("arguments")),
                "call_id": event.get("call_id") or "",
            }
    return None


def _response_id_from(event: dict) -> str | None:
    source = event.get("type") or event.get("event") or ""
    if source == "response.completed":
        resp = event.get("response") or {}
        rid = resp.get("id") if isinstance(resp, dict) else None
        return str(rid) if rid else None
    if source == "run.completed":
        rid = event.get("response_id") or event.get("run_id")
        return str(rid) if rid else None
    rid = event.get("response_id")
    return str(rid) if rid else None


def _default_events_iter(message, instructions: str, **kwargs):
    from scribe3.api.app_impl import _response_events_iter, _responses_events
    from scribe3.llm import hermes_responses_events
    fn = _responses_events or hermes_responses_events
    return _response_events_iter(fn, message, instructions, **kwargs)


def _function_output_input(calls: list[dict], results: list[Any]) -> list[dict]:
    items = []
    for call, result in zip(calls, results):
        cid = call.get("call_id") or f"call-{call.get('name')}"
        items.append({
            "type": "function_call_output",
            "call_id": cid,
            "output": dumps_tool_result(result),
        })
    return items


def discuss_lookup_events(
    message,
    instructions: str,
    *,
    work: str,
    api_base: str | None = None,
    events_iter: Callable[..., Iterable] | None = None,
    execute: Callable[..., dict] | None = None,
    session_key: str | None = None,
    conversation: str | None = None,
    previous_response_id: str | None = None,
    store: bool = True,
    context_revision: int | None = None,
    context_hash: str | None = None,
    adapter=None,
) -> Iterator[dict]:
    """驱动 Hermes Responses（function 闭集）并在本进程执行工具。

    yield 的是 HermesEventAdapter 后的 app 事件（与 chat_agentic_stream 相同形状）。
    """
    from scribe3.hermes_runtime import HermesEventAdapter
    from scribe3.llm import HERMES, HERMES_DISCUSS

    ev_fn = events_iter or _default_events_iter
    exec_fn = execute or execute_discuss_tool
    adp = adapter or HermesEventAdapter(phase="discuss", filter_tools=False)
    base = api_base or HERMES_DISCUSS or HERMES
    tools = discuss_function_tools()
    executed_rounds = 0
    seen_fps: set[tuple[str, str]] = set()
    pending_input = message
    prev = previous_response_id
    last_resp = previous_response_id
    force_stop = False

    while True:
        use_tools = tools if not force_stop else []
        kwargs = {
            "with_tools": True,
            "function_tools": use_tools,
            "api_base": base,
            "session_key": session_key,
            "conversation": conversation,
            "previous_response_id": prev,
            "store": store,
            "context_revision": context_revision,
            "context_hash": context_hash,
        }
        calls: list[dict] = []
        for ev in ev_fn(pending_input, instructions, **kwargs):
            if not isinstance(ev, dict):
                continue
            got = collect_function_calls(ev)
            if got:
                calls.append(got)
            rid = _response_id_from(ev)
            if rid:
                last_resp = rid
            app_ev = adp.adapt(ev)
            yield app_ev

        if force_stop or not calls:
            break

        fps = {_fingerprint(c.get("name") or "", c.get("arguments") or {}) for c in calls}
        if fps and fps <= seen_fps:
            log.info("discuss lookup repeated fingerprints; stop continue")
            break
        seen_fps |= fps

        nxt = executed_rounds + 1
        if not can_execute_discuss_round(nxt):
            record_discuss_tool_rounds(executed_rounds)
            force_stop = True
            pending_input = [{"type": "message", "role": "user", "content": _STOP_LOOKUP_HINT}]
            prev = last_resp
            continue

        results = []
        for call in calls:
            payload = exec_fn(
                call.get("name") or "",
                call.get("arguments") or {},
                work=work,
            )
            results.append(payload)
            yield {
                "kind": "tool.output",
                "name": call.get("name") or "",
                "call_id": call.get("call_id") or "",
                "output": dumps_tool_result(payload, cap=400),
                "source_type": "scribe.discuss.execute",
            }
        executed_rounds = nxt
        record_discuss_tool_rounds(executed_rounds)
        pending_input = _function_output_input(calls, results)
        prev = last_resp
        if executed_rounds >= MAX_DISCUSS_TOOL_ROUNDS:
            # 下一次若再要工具，走 force_stop 分支。先续一轮把结果喂回去（仍带 tools）。
            pass

    if last_resp:
        yield {"kind": "lookup.done", "response_id": last_resp, "rounds": executed_rounds}

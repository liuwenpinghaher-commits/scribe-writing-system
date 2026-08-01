"""严格解析 Qwen/Hermes XML 工具调用，不把任意模型文本当作可执行动作。"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from types import SimpleNamespace
from typing import Iterable
from uuid import uuid4


_TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def _decode_tool_call_payload(raw: str) -> tuple[str, dict] | None:
    """解码 Hermes JSON 形式或 TokenPlan/Qwen 的“函数名换行 JSON”形式。

    两种形式都必须把参数解析为 JSON object；函数名不在这里信任，仍由调用方的
    ``allowed_names`` 白名单裁决。因此不能把自由文本或半截 JSON 提升为执行动作。
    """
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        lines = raw.strip().splitlines()
        if len(lines) < 2:
            return None
        name = lines[0].strip()
        try:
            arguments = json.loads("\n".join(lines[1:]).strip())
        except (TypeError, ValueError):
            return None
        if not isinstance(name, str) or not name or not isinstance(arguments, dict):
            return None
        return name, arguments
    if not isinstance(payload, dict) or set(payload) != {"name", "arguments"}:
        return None
    name = payload.get("name")
    arguments = payload.get("arguments")
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return None
    return name, arguments


def extract_xml_tool_calls(
    content: str | None,
    *,
    allowed_names: Iterable[str],
) -> tuple[list[SimpleNamespace], str]:
    """从完整的模型文本中提取已注册函数的严格 XML 调用。

    只有完整 JSON、白名单函数名和 object arguments 三项同时成立时才构造调用；
    无效块保留在可见文本中，避免把模型文字误记成工具事实。重复的同名同参
    调用只保留一个，避免部分 Qwen 响应重发同一 XML 块造成重复世界写。
    """
    raw = content or ""
    allowed = {str(name) for name in allowed_names if isinstance(name, str) and name}
    calls: list[SimpleNamespace] = []
    accepted_ranges: list[tuple[int, int]] = []
    seen: set[tuple[str, str]] = set()

    def accept(name: str, arguments: dict, span: tuple[int, int]) -> None:
        """记录已通过函数白名单的调用；重复调用仍从可见文本中移除。"""
        encoded = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprint = (name, encoded)
        if span not in accepted_ranges:
            accepted_ranges.append(span)
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        call_id = "xml_" + uuid4().hex
        calls.append(SimpleNamespace(
            id=call_id,
            call_id=call_id,
            type="function",
            function=SimpleNamespace(name=name, arguments=encoded),
        ))

    for match in _TOOL_CALL.finditer(raw):
        decoded = _decode_tool_call_payload(match.group(1))
        if decoded is None:
            continue
        name, arguments = decoded
        if name not in allowed:
            continue
        accept(name, arguments, match.span())

    # TokenPlan/Qwen 偶尔在 reasoning 文本中输出 Anthropic 风格数组，而不是 XML。
    # 仅接受整个数组中每一项都严格为 {id,name,args}，且每个 name 都在 Hermes 注册
    # 白名单内的情况；任何夹杂说明文本、额外字段或未注册工具的数组一律保留为文本。
    decoder = json.JSONDecoder()
    for index, char in enumerate(raw):
        if char != "[":
            continue
        try:
            payload, end = decoder.raw_decode(raw[index:])
        except (TypeError, ValueError):
            continue
        if not isinstance(payload, list) or not payload:
            continue
        decoded_calls: list[tuple[str, dict]] = []
        for item in payload:
            if not isinstance(item, dict) or set(item) != {"id", "name", "args"}:
                decoded_calls = []
                break
            name, arguments = item.get("name"), item.get("args")
            if (not isinstance(item.get("id"), str) or not isinstance(name, str)
                    or name not in allowed or not isinstance(arguments, dict)):
                decoded_calls = []
                break
            decoded_calls.append((name, arguments))
        if not decoded_calls:
            continue
        span = (index, index + end)
        for name, arguments in decoded_calls:
            accept(name, arguments, span)

    if not accepted_ranges:
        return calls, raw
    visible_parts: list[str] = []
    cursor = 0
    for start, end in accepted_ranges:
        visible_parts.append(raw[cursor:start])
        cursor = end
    visible_parts.append(raw[cursor:])
    return calls, "".join(visible_parts).strip()

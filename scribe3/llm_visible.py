"""LLM 正式输出：剥 thinking / 推理字段，只留可见正文。

所有补全、流式、字数闸、用量账、落库前都必须走这里。
reasoning_* / <think> 既不计覆盖地板，也不进正文/日志。
"""
from __future__ import annotations

import re
from typing import Any, Mapping

_THINK_BLOCK = re.compile(
    r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>",
    re.IGNORECASE,
)
_THINK_UNCLOSED = re.compile(
    r"<think(?:ing)?>[\s\S]*\Z",
    re.IGNORECASE,
)
_OPEN = re.compile(r"<think(?:ing)?>", re.IGNORECASE)
_CLOSE = re.compile(r"</think(?:ing)?>", re.IGNORECASE)
REASONING_KEYS = (
    "reasoning_content", "reasoning", "reasoning_text",
    "thinking", "thinking_content", "thought", "reasoning_details",
)
_REASONING_USAGE_KEYS = ("reasoning_tokens", "thoughts_tokens")

# 正式输出额度之外再留思考。关 thinking 不加。供应商硬顶 32k。
THINKING_HEADROOM_MIN = 4096
PROVIDER_MAX_TOKENS_HARD = 32_768


def with_thinking_headroom(
    max_tokens: int | None,
    *,
    thinking: str | None = None,
) -> int | None:
    """调用方传入的是正式输出预算；思考开着时加上至少 4k、至多再加一倍。"""
    if max_tokens is None:
        return None
    try:
        n = int(max_tokens)
    except (TypeError, ValueError):
        return max_tokens
    if n <= 0:
        return n
    if str(thinking or "").strip().lower() == "disabled":
        return n
    extra = max(n, THINKING_HEADROOM_MIN)
    return min(PROVIDER_MAX_TOKENS_HARD, n + extra)


def strip_thinking_markup(text: str | None) -> str:
    """去掉正文里夹带的 think 标签块；未闭合的尾巴也丢。"""
    raw = text or ""
    out = _THINK_BLOCK.sub("", raw)
    return _THINK_UNCLOSED.sub("", out)


def _int_tok(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _content_from_message(message: Mapping[str, Any] | None) -> str:
    if not isinstance(message, Mapping):
        return ""
    content = message.get("content")
    if isinstance(content, list):
        bits: list[str] = []
        for part in content:
            if isinstance(part, str):
                bits.append(part)
                continue
            if not isinstance(part, Mapping):
                continue
            kind = str(part.get("type") or "")
            if kind in ("", "text", "output_text"):
                bits.append(str(part.get("text") or part.get("content") or ""))
        return "".join(bits)
    return content if isinstance(content, str) else ""


def visible_message_text(message: Mapping[str, Any] | None) -> str:
    """只取正式 content。reasoning / thinking 字段一律丢弃。"""
    return strip_thinking_markup(_content_from_message(message)).strip()


def visible_delta_text(delta: Mapping[str, Any] | None) -> str:
    """流式 delta：只认 content。推理字段当空串。"""
    if not isinstance(delta, Mapping):
        return ""
    content = delta.get("content")
    if isinstance(content, list):
        return visible_message_text({"content": content})
    if not isinstance(content, str):
        return ""
    return content


def reasoning_tokens_of(usage: Mapping[str, Any] | None) -> int:
    if not isinstance(usage, Mapping):
        return 0
    n = 0
    for key in _REASONING_USAGE_KEYS:
        n = max(n, _int_tok(usage.get(key)))
    for nest_key in ("completion_tokens_details", "output_tokens_details"):
        nest = usage.get(nest_key)
        if isinstance(nest, Mapping):
            for key in _REASONING_USAGE_KEYS:
                n = max(n, _int_tok(nest.get(key)))
    return n


def visible_usage(usage: dict | None) -> dict | None:
    """用量账只记正式输出 token；reasoning_tokens 从 completion/total 里扣掉。"""
    if not isinstance(usage, dict):
        return usage
    out = dict(usage)
    reasoning = reasoning_tokens_of(out)
    if not reasoning:
        return out
    for key in ("output_tokens", "completion_tokens"):
        if key in out:
            out[key] = max(0, _int_tok(out[key]) - reasoning)
    if "total_tokens" in out:
        out["total_tokens"] = max(0, _int_tok(out["total_tokens"]) - reasoning)
    out.pop("reasoning_tokens", None)
    out.pop("thoughts_tokens", None)
    out.pop("completion_tokens_details", None)
    out.pop("output_tokens_details", None)
    return out


class VisibleStreamFilter:
    """跨 chunk 剥 <think>…</think>，只放出正式输出。"""

    def __init__(self) -> None:
        self._hold = ""
        self._in_think = False

    def feed(self, piece: str | None) -> str:
        if not piece:
            return ""
        self._hold += piece
        visible: list[str] = []
        while self._hold:
            if self._in_think:
                closed = _CLOSE.search(self._hold)
                if not closed:
                    if len(self._hold) > 24:
                        self._hold = self._hold[-24:]
                    return "".join(visible)
                self._hold = self._hold[closed.end():]
                self._in_think = False
                continue
            opened = _OPEN.search(self._hold)
            if not opened:
                hold_n = _incomplete_open_len(self._hold)
                emit = self._hold[: len(self._hold) - hold_n]
                self._hold = self._hold[len(self._hold) - hold_n:]
                if emit:
                    visible.append(emit)
                return "".join(visible)
            if opened.start():
                visible.append(self._hold[: opened.start()])
            self._hold = self._hold[opened.end():]
            self._in_think = True
        return "".join(visible)

    def flush(self) -> str:
        if self._in_think:
            self._hold = ""
            return ""
        leftover = self._hold
        self._hold = ""
        return leftover


def _incomplete_open_len(buf: str) -> int:
    low = buf.lower()
    for n in range(min(len(low), 10), 0, -1):
        tail = low[-n:]
        if tail.startswith("<") and (
            "<thinking".startswith(tail) or "<think".startswith(tail)
        ):
            return n
    return 0

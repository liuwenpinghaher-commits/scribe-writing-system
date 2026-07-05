"""移植自 scribe2/llm.py 的已验证 Hermes 客户端(greenfield 内核复用已验证资产)。

经 Hermes 网关 :8642 OpenAI 兼容端点取补全(由 Hermes 路由到 doubao),不直连火山。
含已验证的 600s 超时 + 3 次重试(瞬时超时/5xx/连接错重试,4xx 不重试)。
流式路径同:建链+首字节到达前的瞬时错重试,已开始 yield 后不重试(避免重发 delta)。
"""
from __future__ import annotations

import logging
import os
import time

import httpx

_RETRYABLE = (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError)
_MAX_RETRIES = 3

_log = logging.getLogger("scribe3.llm")


class CircuitBreaker:
    """LLM 调用熔断器:连续失败 threshold 次后熔断,冷却后试探(半开),成功则闭合。

    与重试互补:重试处理瞬时抖动,熔断器处理持续故障(如 doubao 服务降级)。
    熔断时 allow() 返回 False → 调用方应快速失败而非反复重试。
    """

    def __init__(self, threshold: int = 5, cooldown: float = 60.0):
        self.threshold = threshold
        self.cooldown = cooldown
        self.failure_count = 0
        self._opened_at: float | None = None

    def allow(self) -> bool:
        """当前是否允许 LLM 调用。熔断中返回 False。"""
        if self._opened_at is not None:
            if time.time() - self._opened_at < self.cooldown:
                return False
            # 冷却已过 → 半开(允许一次探针)
        return True

    def record_failure(self) -> None:
        """记录一次失败。达到阈值则熔断。"""
        self.failure_count += 1
        if self.failure_count >= self.threshold:
            self._opened_at = time.time()
            _log.warning("LLM 熔断器触发(连续 %d 次失败),冷却 %ds", self.failure_count, self.cooldown)

    def record_success(self) -> None:
        """记录一次成功。重置计数并闭合。"""
        self.failure_count = 0
        self._opened_at = None

HERMES = os.environ.get("HERMES_API", "http://127.0.0.1:8642/v1")
# 主编 agentic 走 scribe3 profile 专属网关 :8643(挂 scribe3 MCP);与 default :8642 隔离。
HERMES_RESPONSES = os.environ.get("HERMES_RESPONSES_API", "http://127.0.0.1:8643/v1")


def _api_key() -> str:
    k = os.environ.get("API_SERVER_KEY")
    if not k:
        try:
            for ln in open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8"):
                if ln.startswith("API_SERVER_KEY="):
                    k = ln.split("=", 1)[1].strip()
                    break
        except Exception as e:
            logging.getLogger("scribe3.llm").warning("读取 ~/.hermes/.env API_SERVER_KEY 失败: %s", e)
    return k or "local"


def _stream_with_retry(make_stream, max_retries: int = _MAX_RETRIES):
    """对'打开流 + 取到首个 yield 前'的瞬时错重试;已 yield 后不重试(避免重发 delta)。

    make_stream: () -> generator(每次调用新建一条 httpx.stream 并 yield delta/event)。"""
    last = None
    for attempt in range(max_retries):
        started = False
        try:
            for piece in make_stream():
                started = True
                yield piece
            return
        except _RETRYABLE as e:
            last = e
            if started:
                _log.warning("流式中途断(已输出,不重试): %s", e)
                raise
            _log.warning("流式建链瞬时错,重试 %d/%d: %s", attempt + 1, max_retries, e)
            continue
        except httpx.HTTPStatusError as e:
            last = e
            if started or (e.response is not None and e.response.status_code < 500):
                raise
            _log.warning("流式 5xx,重试 %d/%d: %s", attempt + 1, max_retries, e)
            continue
    raise last if last else RuntimeError("stream failed after retries")


def hermes_complete(prompt: str, system: str | None = None,
                    model: str = "doubao-seed-2.0-pro", timeout: float = 600.0,
                    max_tokens: int | None = None) -> str:
    """经 Hermes 取一段补全。max_tokens 硬上限控长。错误抛出不静默。"""
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
    body: dict = {"model": model, "messages": msgs, "stream": False}
    if max_tokens:
        body["max_tokens"] = max_tokens
    hdr = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}
    last: Exception | None = None
    for _ in range(_MAX_RETRIES):
        try:
            r = httpx.post(f"{HERMES}/chat/completions", timeout=timeout, headers=hdr, json=body)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last = e
            continue
        except httpx.HTTPStatusError as e:
            last = e
            if e.response is not None and e.response.status_code < 500:
                raise
            continue
    raise last if last else RuntimeError("hermes_complete failed")


def hermes_complete_stream(prompt: str, system: str | None = None,
                           model: str = "doubao-seed-2.0-pro", timeout: float = 600.0):
    """流式逐字补全:yield 每个 delta 文本片段(Hermes SSE)。主编对话用。
    建链瞬时错自动重试(与非流式重试语义一致),已 yield 后不重试。"""
    import json as _j
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]

    def make_stream():
        with httpx.stream("POST", f"{HERMES}/chat/completions", timeout=timeout,
                          headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
                          json={"model": model, "messages": msgs, "stream": True}) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    delta = _j.loads(payload)["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
                except Exception:
                    continue

    yield from _stream_with_retry(make_stream)


def hermes_responses_events(message: str, instructions: str, model: str | None = None,
                            timeout: float = 600.0, with_tools: bool = True):
    """主编 agentic:POST scribe3 网关(:8643)/v1/responses(可选 tools=scribe3 MCP + stream),逐事件 yield。
    server_label='scribe3' 引用 profile config 里挂的 scribe3 MCP,主编自动发现并调用 s3_ 工具。
    SSE 为 OpenAI Responses 标准(每条 data: 的 JSON 带 type 字段)。
    建链瞬时错自动重试,已 yield 后不重试。

    with_tools:审计 P0-2 门控。MCP 进程固定连 SCRIBE3_WORK 那本书;仅当当前请求的书 ==
    SCRIBE3_WORK 时才 with_tools=True 挂 s3_ 工具,否则挂上去会读/写错库(不可逆)。
    with_tools=False → body 不含 tools,退化为纯对话(无联查/无待批写),绝不串库。"""
    import json as _j
    body: dict = {"input": message, "instructions": instructions, "stream": True}
    if with_tools:
        body["tools"] = [{"type": "mcp", "server_label": "scribe3"}]
    if model:
        body["model"] = model

    def make_stream():
        with httpx.stream("POST", f"{HERMES_RESPONSES}/responses", timeout=timeout,
                          headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
                          json=body) as r:
            r.raise_for_status()
            for raw in r.iter_lines():
                if not raw or not raw.startswith("data:"):
                    continue
                payload = raw[5:].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    yield _j.loads(payload)
                except Exception:
                    continue

    yield from _stream_with_retry(make_stream)

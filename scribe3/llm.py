"""移植自 scribe2/llm.py 的已验证 Hermes 客户端(greenfield 内核复用已验证资产)。

经 Hermes 网关 :8642 OpenAI 兼容端点取补全(由 Hermes 路由到 doubao),不直连火山。
含已验证的 600s 超时 + 3 次重试(瞬时超时/5xx/连接错重试,4xx 不重试)。
流式路径同:建链+首字节到达前的瞬时错重试,已开始 yield 后不重试(避免重发 delta)。
"""
from __future__ import annotations

import logging
import os
import threading
import time

import httpx

_RETRYABLE = (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError)
_MAX_RETRIES = 3

_log = logging.getLogger("scribe3.llm")

# 审计 P1-12(方案原文"接线或删除二选一"):原 CircuitBreaker 死类已删(0.18 网关
# 自带重试/排队,持续故障由其兜);日调用帽在此单点接线——llm.py 是全部 LLM 出口
# (complete/stream/responses),比散在 app 端点层可靠。进程内计数,重启清零(帽是
# 成本保险丝不是账本)。
_DAILY_CALL_CAP = int(os.environ.get("SCRIBE3_DAILY_CALL_CAP", "500"))
_daily_lock = threading.Lock()
_daily = ["", 0]   # [day, count]


def _reset_daily_counter() -> None:
    with _daily_lock:
        _daily[0], _daily[1] = "", 0


def _tick_daily() -> None:
    """每次 LLM 调用前记一笔;超日帽抛错(调用方 fail-soft 链各自兜)。"""
    today = time.strftime("%Y-%m-%d")
    with _daily_lock:
        if _daily[0] != today:
            _daily[0], _daily[1] = today, 0
        if _daily[1] >= _DAILY_CALL_CAP:
            raise RuntimeError(
                f"LLM 日调用上限已达({_DAILY_CALL_CAP},SCRIBE3_DAILY_CALL_CAP 可调)")
        _daily[1] += 1

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
    _tick_daily()
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
    body: dict = {"model": model, "messages": msgs, "stream": False}
    if max_tokens:
        body["max_tokens"] = max_tokens
    hdr = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}
    last: Exception | None = None
    for _attempt in range(_MAX_RETRIES):
        try:
            r = httpx.post(f"{HERMES}/chat/completions", timeout=timeout, headers=hdr, json=body)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last = e
            # 审计 #81:非流式重试此前静默 continue,与流式路径日志语义对齐
            _log.warning("非流式瞬时错,重试 %d/%d: %s", _attempt + 1, _MAX_RETRIES, e)
            continue
        except httpx.HTTPStatusError as e:
            last = e
            if e.response is not None and e.response.status_code < 500:
                raise
            _log.warning("非流式 5xx,重试 %d/%d: %s", _attempt + 1, _MAX_RETRIES, e)
            continue
    raise last if last else RuntimeError("hermes_complete failed")


def hermes_complete_stream(prompt: str, system: str | None = None,
                           model: str = "doubao-seed-2.0-pro", timeout: float = 600.0):
    """流式逐字补全:yield 每个 delta 文本片段(Hermes SSE)。主编对话用。
    建链瞬时错自动重试(与非流式重试语义一致),已 yield 后不重试。"""
    import json as _j
    _tick_daily()
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
    _tick_daily()
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

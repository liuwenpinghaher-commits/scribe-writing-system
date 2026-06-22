"""移植自 scribe2/llm.py 的已验证 Hermes 客户端(greenfield 内核复用已验证资产)。

经 Hermes 网关 :8642 OpenAI 兼容端点取补全(由 Hermes 路由到 doubao),不直连火山。
含已验证的 600s 超时 + 3 次重试(瞬时超时/5xx/连接错重试,4xx 不重试)。
"""
from __future__ import annotations

import os

import httpx

HERMES = os.environ.get("HERMES_API", "http://127.0.0.1:8642/v1")


def _api_key() -> str:
    k = os.environ.get("API_SERVER_KEY")
    if not k:
        try:
            for ln in open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8"):
                if ln.startswith("API_SERVER_KEY="):
                    k = ln.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    return k or "local"


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
    for _ in range(3):
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
    """流式逐字补全:yield 每个 delta 文本片段(Hermes SSE)。主编对话用。"""
    import json as _j
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
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

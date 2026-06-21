"""写作层移植 Phase4:生成走 Hermes —— 调 hermes 网关 :8642 的 OpenAI 兼容
/v1/chat/completions(由 hermes 路由到 doubao),不再直连火山。这是设计文档 §1
"消除绕过 Hermes"的正解。complete_fn 注入 generate.generate_continue。
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
                    model: str = "doubao-seed-2.0-pro", timeout: float = 300.0) -> str:
    """经 Hermes 网关取一段补全(主笔)。错误抛出不静默。"""
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
    r = httpx.post(f"{HERMES}/chat/completions", timeout=timeout,
                   headers={"Authorization": f"Bearer {_api_key()}",
                            "Content-Type": "application/json"},
                   json={"model": model, "messages": msgs, "stream": False})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def hermes_responses_events(message: str, instructions: str, model: str | None = None,
                            timeout: float = 300.0):
    """主编 agentic:POST hermes /v1/responses(tools=scribe2 MCP + stream),逐事件 yield。
    挂 server_label:'scribe2' 引用 config.yaml 里挂的 scribe2 MCP,主编自动发现并调用其工具。
    SSE 为 OpenAI Responses 标准(每条 data: 的 JSON 带 type 字段)。"""
    import json as _j
    body: dict = {"input": message, "instructions": instructions, "stream": True,
                  "tools": [{"type": "mcp", "server_label": "scribe2"}]}
    if model:
        body["model"] = model
    with httpx.stream("POST", f"{HERMES}/responses", timeout=timeout,
                      headers={"Authorization": f"Bearer {_api_key()}",
                               "Content-Type": "application/json"},
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


def hermes_complete_stream(prompt: str, system: str | None = None,
                           model: str = "doubao-seed-2.0-pro", timeout: float = 300.0):
    """流式逐字补全:yield 每个 delta 文本片段(Hermes SSE)。"""
    import json as _j
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
    with httpx.stream("POST", f"{HERMES}/chat/completions", timeout=timeout,
                      headers={"Authorization": f"Bearer {_api_key()}",
                               "Content-Type": "application/json"},
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

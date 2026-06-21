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

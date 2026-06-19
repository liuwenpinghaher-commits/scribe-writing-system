"""LLM 接入层(工程3 · C3-1)—— 统一补全:重试退避 + 超时 + 成本账本 + 模型路由。

设计:把"怎么调模型"从业务代码剥离。业务只说"按角色补全",由本层决定模型/重试/记账。
- complete():带指数退避重试、超时;返回 (content, usage)。
- TokenLedger:把每次调用的 token 与估算成本落 token_records,供成本透明/熔断/可观测(C3-5/C6)。
- 模型路由:AgentRole→model(当前火山只有 doubao,留扩展位)。
HTTP 仍用 httpx;纯函数 estimate_cost / retry 逻辑可单测。
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import httpx

# 粗略价格表(USD / 1K tokens);火山 doubao 走包月,这里给象征性单价用于成本归因趋势
PRICING = {
    "doubao-seed-2.0-pro": {"in": 0.0008, "out": 0.002},
    "default": {"in": 0.001, "out": 0.003},
}

# 角色→模型(工程3 §3.3:旗舰/快/回退分层。火山单模型,先一对多映射,接口可演进)
ROLE_MODEL = {
    "draft": "doubao-seed-2.0-pro",
    "critique": "doubao-seed-2.0-pro",
    "summary": "doubao-seed-2.0-pro",
    "extract": "doubao-seed-2.0-pro",
    "chat": "doubao-seed-2.0-pro",
    "default": "doubao-seed-2.0-pro",
}


def model_for(role: str) -> str:
    return ROLE_MODEL.get(role, ROLE_MODEL["default"])


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICING.get(model, PRICING["default"])
    return round(prompt_tokens / 1000 * p["in"] + completion_tokens / 1000 * p["out"], 6)


def _approx_tokens(text: str) -> int:
    """无 usage 字段时的兜底估算:中文约 1.6 字/token。"""
    return max(1, int(len(text or "") / 1.6))


def complete(base_url: str, api_key: str, model: str, message: str, *,
             system: str | None = None, timeout: float = 120.0, retries: int = 2) -> dict:
    """单次补全(OpenAI 兼容)。指数退避重试。返回 {content, prompt_tokens, completion_tokens, model}。"""
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": message}]
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = httpx.post(f"{base_url}/chat/completions", timeout=timeout,
                           headers={"Authorization": f"Bearer {api_key}",
                                    "Content-Type": "application/json"},
                           json={"model": model, "messages": msgs, "stream": False})
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            pt = usage.get("prompt_tokens") or _approx_tokens(message + (system or ""))
            ct = usage.get("completion_tokens") or _approx_tokens(content)
            return {"content": content, "prompt_tokens": pt, "completion_tokens": ct, "model": model}
        except Exception as e:  # 网络/5xx/超时 → 退避重试
            last_err = e
            if attempt < retries:
                time.sleep(min(8.0, 0.8 * (2 ** attempt)))
    raise RuntimeError(f"LLM 调用失败(重试 {retries} 次后):{last_err}")


def complete_stream(base_url: str, api_key: str, model: str, message: str, *,
                    system: str | None = None, timeout: float = 120.0):
    """流式补全(OpenAI 兼容 SSE)。逐段 yield 文本增量。最后一段无 token 计数(调用方估算)。"""
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": message}]
    with httpx.stream("POST", f"{base_url}/chat/completions", timeout=timeout,
                      headers={"Authorization": f"Bearer {api_key}",
                               "Content-Type": "application/json"},
                      json={"model": model, "messages": msgs, "stream": True}) as r:
        r.raise_for_status()
        import json as _j
        for line in r.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                delta = _j.loads(payload)["choices"][0]["delta"].get("content")
            except Exception:
                delta = None
            if delta:
                yield delta


class TokenLedger:
    def __init__(self, conn):
        self.conn = conn

    def record(self, work_id: str | None, role: str, model: str,
               prompt_tokens: int, completion_tokens: int) -> float:
        cost = estimate_cost(model, prompt_tokens, completion_tokens)
        self.conn.execute(
            "INSERT INTO token_records(id,work_id,role,model,prompt_tokens,completion_tokens,"
            "cost_usd,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), work_id, role, model, prompt_tokens, completion_tokens, cost,
             datetime.now(timezone.utc).isoformat()))
        self.conn.commit()
        return cost

    def total_cost(self, work_id: str | None = None) -> dict:
        if work_id:
            row = self.conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(prompt_tokens+completion_tokens),0), "
                "COALESCE(SUM(cost_usd),0) FROM token_records WHERE work_id=?", (work_id,)).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(prompt_tokens+completion_tokens),0), "
                "COALESCE(SUM(cost_usd),0) FROM token_records").fetchone()
        return {"calls": row[0], "tokens": row[1], "cost_usd": round(row[2], 6)}

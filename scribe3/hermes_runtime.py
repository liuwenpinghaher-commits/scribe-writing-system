"""Hermes Agent runtime adapter for scribe3."""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import httpx

_log = logging.getLogger("scribe3.hermes_runtime")


def _strip_v1(url: str) -> str:
    url = url.rstrip("/")
    return url[:-3] if url.endswith("/v1") else url


def soul_layers_enabled() -> bool:
    """GAP-7：默认开启 SOUL 分层（可用 SCRIBE3_HERMES_SOUL_LAYERS=0 关闭）。"""
    raw = (os.environ.get("SCRIBE3_HERMES_SOUL_LAYERS") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def build_hermes_request_body(
    *,
    input_text: Any,
    instructions: str | None = None,
    stream: bool | None = None,
    store: bool | None = None,
    model: str | None = None,
    conversation: str | None = None,
    previous_response_id: str | None = None,
    tools: list | None = None,
    session_id: str | None = None,
    conversation_history: list | None = None,
) -> dict[str, Any]:
    """构造 Hermes 请求体（纯函数，可单测）。

    启用 SOUL 时始终包含 system / instructions / personality 三层。
    """
    body: dict[str, Any] = {"input": input_text}
    if instructions is not None:
        body["instructions"] = instructions
    if stream is not None:
        body["stream"] = bool(stream)
    if store is not None:
        body["store"] = bool(store)
    if model:
        body["model"] = model
    if conversation:
        body["conversation"] = conversation
    if previous_response_id:
        body["previous_response_id"] = previous_response_id
    if tools is not None:
        body["tools"] = tools
    if session_id:
        body["session_id"] = session_id
    if conversation_history is not None:
        body["conversation_history"] = conversation_history
    if soul_layers_enabled():
        body["system"] = (
            os.environ.get("SCRIBE3_HERMES_SYSTEM")
            or "You are Scribe3 writing runtime. Obey epistemic and craft gates."
        )
        body["personality"] = (
            os.environ.get("SCRIBE3_HERMES_PERSONALITY")
            or "冷静、可审计的小说主编；不编造未批准正典。"
        )
        if "instructions" not in body:
            body["instructions"] = ""
    return body


def _read_env_key(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or not line.startswith("API_SERVER_KEY="):
                continue
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        return None
    except Exception as exc:
        _log.warning("读取 Hermes API_SERVER_KEY 失败(%s): %s", path, exc)
    return None


def _iter_sse_json(lines):
    for raw in lines:
        if not raw or not raw.startswith("data:"):
            continue
        payload = raw[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            yield json.loads(payload)
        except Exception:
            continue


class HermesAuth:
    """Resolve Hermes API key without assuming profile and default keys are identical."""

    def __init__(self, *, home: str | Path | None = None, env: Mapping[str, str] | None = None):
        self.home = Path(home) if home is not None else Path(os.path.expanduser("~/.hermes"))
        self.env = env if env is not None else os.environ

    def api_key(self, profile: str | None = None) -> str:
        env_key = self.env.get("API_SERVER_KEY")
        if env_key:
            return env_key
        if profile:
            profile_key = _read_env_key(self.home / "profiles" / profile / ".env")
            if profile_key:
                return profile_key
        return _read_env_key(self.home / ".env") or "local"


def scribe3_session_key(work: str, *, thread_id: str | None = None,
                        scope: str | None = None) -> str:
    """Hermes X-Hermes-Session-Key 的**唯一格式源**(Minor #6 防三处重复漂移)。

    - thread_id → 主编讨论线程 key(work+thread,导航切章不换,主编历史连续);
    - scope → 其它会话面(如 runs 写 profile 长任务,work|runs 与讨论线程隔离)。
    app._hermes_session_key / app._run_session_key / HermesTurnContext.session_key 三处
    均经此函数拼串,格式改动只此一处。"""
    if thread_id is not None:
        return f"scribe3|work:{work}|thread:{thread_id}"
    return f"scribe3|work:{work}|{scope}"


@dataclass(frozen=True)
class HermesTurnContext:
    """一轮主编 turn 的会话连续 + 动态上下文游标(Task 11 产出)。

    为什么存在:把"哪条主编线程 / Hermes 会话续到哪 / 本轮动态上下文是哪一版"打包成一个不可变
    值对象,让 app 组装、llm/runtime 消费时不必散传一堆位置参数。

    - work/thread_id:稳定 session key 的唯一两维(切章/切焦点都不换)。
    - conversation_id/previous_response_id:Hermes 服务端会话续接锚。**设计约束**:Hermes
      Responses 服务端存储是 LRU 100 条,长线程这两个锚必然掉链——掉链是常态,不是异常;
      掉链后由 Scribe 侧 thread messages + working summary 重建,不依赖 Hermes SQLite。
    - context_session_id/context_revision/context_hash/envelope_hash:每轮动态上下文层
      (ContextEnvelope,默认关)的可观测游标;开启后随 X-Scribe-Context-* 头上报。
    """

    work: str
    thread_id: str
    conversation_id: str | None = None
    previous_response_id: str | None = None
    context_session_id: str = ""
    context_revision: int = 0
    context_hash: str = ""
    envelope_hash: str = ""

    @property
    def session_key(self) -> str:
        """稳定 session key 只含 work + thread —— 导航切章不换 Hermes session,主编历史连续。"""
        return scribe3_session_key(self.work, thread_id=self.thread_id)


class HermesRuntime:
    """Thin, testable boundary around Hermes HTTP runtime endpoints."""

    def __init__(self, *, api_base: str, profile: str = "default",
                 auth: HermesAuth | None = None):
        self.api_base = api_base.rstrip("/")
        self.root_url = _strip_v1(self.api_base)
        self.profile = profile
        self.auth = auth or HermesAuth()

    def _headers(self, *, session_key: str | None = None,
                 context_revision: int | None = None,
                 context_hash: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.auth.api_key(self.profile)}",
            "Content-Type": "application/json",
        }
        if session_key:
            headers["X-Hermes-Session-Key"] = session_key
        # 动态上下文层游标(Task 11):仅在本轮真带了 envelope 版本时上报,默认路径不发头,
        # 旧行为字节不变。revision 可能是 0(合法首版),故用 is not None 判发。
        if context_revision is not None:
            headers["X-Scribe-Context-Revision"] = str(context_revision)
        if context_hash:
            headers["X-Scribe-Context-Hash"] = context_hash
        return headers

    @staticmethod
    def _health_ok(health: dict[str, Any]) -> tuple[bool, bool, list[str]]:
        """(ok, degraded, degraded_reasons) — U-001(2026-07-13):
        判据是**网关能不能干活**,不是 health.status 字面。Hermes 的 readiness 里
        磁盘/负载这类周边检查一 degraded,整份 status 就变 'degraded';旧实现
        `ok = (status == 'ok')` 于是把「磁盘紧张」误判成「Hermes 离线」,前端常驻红字
        (实测:主编/写作/记忆检索全部正常)。
        现判据:status=='ok' 直接可用;status=='degraded' 时,只要 gateway 在跑
        (gateway_state=running 或 readiness.checks.gateway.status=ok)且 api_server 已连,
        仍算可用,只把降级原因列出来供 UI 显示黄字。其余(gateway 停了/连不上)才是不可用。"""
        raw = str(health.get("status") or "")
        checks = ((health.get("readiness") or {}).get("checks") or {})
        reasons = sorted(k for k, v in checks.items()
                         if isinstance(v, dict) and v.get("status") not in (None, "ok"))
        if raw == "ok":
            return True, False, reasons
        if raw != "degraded":
            return False, True, reasons or [raw or "unknown"]
        gw = checks.get("gateway") or {}
        gw_running = (health.get("gateway_state") == "running") or (gw.get("status") == "ok")
        # api_server 状态:真机在 platforms.api_server.state(实测 0.18.2);顶层 api_server
        # 是既有测试 fixture 的简化形状——两者都认,以真机为准优先。
        api_node = ((health.get("platforms") or {}).get("api_server")
                    or health.get("api_server") or {})
        api_connected = (api_node.get("state") == "connected")
        return bool(gw_running and api_connected), True, reasons

    def probe(self, *, timeout: float = 5.0) -> dict[str, Any]:
        status: dict[str, Any] = {
            "profile": self.profile,
            "api_base": self.api_base,
            "root_url": self.root_url,
            "ok": False,
            "degraded": False,
            "degraded_reasons": [],
            "health": {},
            "capabilities": {},
            "features": {},
            "skills": [],
            "toolsets": [],
        }
        try:
            health = httpx.get(
                f"{self.root_url}/health/detailed",
                timeout=timeout,
                headers=self._headers(),
            )
            health.raise_for_status()
            capabilities = httpx.get(
                f"{self.api_base}/capabilities",
                timeout=timeout,
                headers=self._headers(),
            )
            capabilities.raise_for_status()
            status["health"] = health.json()
            caps_payload = capabilities.json()
            status["capabilities"] = caps_payload
            if isinstance(caps_payload, dict):
                status["features"] = caps_payload.get("features") or caps_payload
            optional_errors: dict[str, str] = {}
            for key, path in (("skills", "skills"), ("toolsets", "toolsets")):
                try:
                    res = httpx.get(
                        f"{self.api_base}/{path}",
                        timeout=timeout,
                        headers=self._headers(),
                    )
                    res.raise_for_status()
                    payload = res.json()
                    if isinstance(payload, dict):
                        value = payload.get(key)
                        if value is None:
                            value = payload.get("data")
                    else:
                        value = payload
                    status[key] = value or []
                except Exception as exc:
                    optional_errors[key] = str(exc)[:160]
            if optional_errors:
                status["optional_errors"] = optional_errors
            ok, degraded, reasons = self._health_ok(status["health"] or {})
            status["ok"] = ok
            status["degraded"] = degraded
            status["degraded_reasons"] = reasons
        except Exception as exc:
            status["error"] = str(exc)[:200]
        return status

    def responses_events(self, message: Any, instructions: str, *,
                         model: str | None = None,
                         timeout: float = 600.0,
                         with_tools: bool = True,
                         conversation: str | None = None,
                         previous_response_id: str | None = None,
                         session_key: str | None = None,
                         store: bool = True,
                         context_revision: int | None = None,
                         context_hash: str | None = None,
                         server_label: str = "scribe3_read",
                         function_tools: list | None = None):
        if function_tools is not None:
            tools = list(function_tools)
        elif with_tools:
            tools = [{"type": "mcp", "server_label": server_label}]
        else:
            tools = None
        body = build_hermes_request_body(
            input_text=message,
            instructions=instructions,
            stream=True,
            store=bool(store),
            model=model,
            conversation=conversation,
            previous_response_id=previous_response_id,
            tools=tools,
        )

        with httpx.stream(
            "POST",
            f"{self.api_base}/responses",
            timeout=timeout,
            headers=self._headers(
                session_key=session_key,
                context_revision=context_revision,
                context_hash=context_hash,
            ),
            json=body,
        ) as response:
            response.raise_for_status()
            yield from _iter_sse_json(response.iter_lines())

    def create_run(self, input_text: str, *, instructions: str | None = None,
                   session_id: str | None = None,
                   conversation_history: list[dict[str, Any]] | None = None,
                   previous_response_id: str | None = None,
                   session_key: str | None = None,
                   timeout: float = 60.0) -> dict[str, Any]:
        body = build_hermes_request_body(
            input_text=input_text,
            instructions=instructions,
            session_id=session_id,
            conversation_history=conversation_history,
            previous_response_id=previous_response_id,
        )
        response = httpx.post(
            f"{self.api_base}/runs",
            timeout=timeout,
            headers=self._headers(session_key=session_key),
            json=body,
        )
        response.raise_for_status()
        return response.json()

    def run_status(self, run_id: str, *, session_key: str | None = None,
                   timeout: float = 30.0) -> dict[str, Any]:
        response = httpx.get(
            f"{self.api_base}/runs/{run_id}",
            timeout=timeout,
            headers=self._headers(session_key=session_key),
        )
        response.raise_for_status()
        return response.json()

    def run_events(self, run_id: str, *, session_key: str | None = None,
                   timeout: float = 600.0):
        with httpx.stream(
            "GET",
            f"{self.api_base}/runs/{run_id}/events",
            timeout=timeout,
            headers=self._headers(session_key=session_key),
        ) as response:
            response.raise_for_status()
            yield from _iter_sse_json(response.iter_lines())

    def approve_run(self, run_id: str, approval: dict[str, Any], *,
                    session_key: str | None = None,
                    timeout: float = 60.0) -> dict[str, Any]:
        response = httpx.post(
            f"{self.api_base}/runs/{run_id}/approval",
            timeout=timeout,
            headers=self._headers(session_key=session_key),
            json=approval,
        )
        response.raise_for_status()
        return response.json()

    def stop_run(self, run_id: str, *, session_key: str | None = None,
                 timeout: float = 30.0) -> dict[str, Any]:
        response = httpx.post(
            f"{self.api_base}/runs/{run_id}/stop",
            timeout=timeout,
            headers=self._headers(session_key=session_key),
        )
        response.raise_for_status()
        return response.json()


class HermesEventAdapter:
    """Normalize Hermes Responses SSE events for app-level streams."""

    def __init__(self, *, phase: str | None = None, filter_tools: bool = False):
        # Hermes Runs 的 MCP 事件在实际网关中可缺 call_id；为同一 SSE 流内的
        # started/completed 成对事件分配稳定审计 ID，不能因协议缺字段而丢失工具完成证据。
        self._anonymous_call_count = 0
        self._unresolved_call_ids: dict[str, deque[str]] = defaultdict(deque)
        # GAP-11：后验工具过滤默认 **关**（写路径/ai_run 必须放行 s3_add_*）。
        # 仅 discuss/agentic 显式 filter_tools=True + phase=discuss|agentic。
        self._phase = phase
        self._filter_tools = bool(filter_tools) and bool((phase or "").strip())
        self._blocked_calls: list[dict] = []

    def _maybe_block_tool(self, name: str, arguments: Any = "") -> dict[str, Any] | None:
        """若工具不在阶段白名单 → 返回 tool.blocked 事件；否则 None。

        phase 为空或 filter_tools=False 时 **不 enforce**（避免写路径静默丢 tool.started）。
        """
        if not self._filter_tools or not name:
            return None
        phase = (self._phase or "").strip()
        if not phase:
            return None
        try:
            from scribe3.run_tool_filter import filter_tool_calls
            out = filter_tool_calls(
                [{"name": name, "arguments": arguments}],
                phase=phase,
            )
            if out.get("enforced") and out.get("blocked"):
                blocked = {
                    "kind": "tool.blocked",
                    "name": name,
                    "reason": "not_in_allowlist",
                    "phase": phase,
                    "allowed": out.get("allowed"),
                }
                self._blocked_calls.append(blocked)
                return blocked
        except Exception:
            return None
        return None

    def _started_call_id(self, event: dict[str, Any], name: str,
                         item: dict[str, Any] | None = None) -> str | None:
        call_id = self._call_id(event, item)
        if not call_id:
            self._anonymous_call_count += 1
            call_id = f"synthetic:{self._anonymous_call_count}"
        if name:
            self._unresolved_call_ids[name].append(str(call_id))
        return str(call_id)

    def _completed_call_id(self, event: dict[str, Any], name: str,
                           item: dict[str, Any] | None = None) -> str | None:
        call_id = self._call_id(event, item)
        queued = self._unresolved_call_ids.get(name)
        if call_id:
            normalized = str(call_id)
            if queued:
                try:
                    queued.remove(normalized)
                except ValueError:
                    pass
            return normalized
        if queued:
            return queued.popleft()
        return None

    @staticmethod
    def _tool_name(event: dict[str, Any], item: dict[str, Any] | None = None) -> str:
        item = item or {}
        name = (
            event.get("name") or event.get("tool_name") or event.get("tool")
            or item.get("name") or item.get("tool_name") or item.get("tool") or ""
        )
        if isinstance(name, str) and "_s3_" in name:
            return name[name.index("s3_"):]
        return name if isinstance(name, str) else ""

    @staticmethod
    def _call_id(event: dict[str, Any], item: dict[str, Any] | None = None):
        item = item or {}
        return event.get("call_id") or event.get("tool_call_id") or item.get("call_id") or item.get("tool_call_id")

    @staticmethod
    def _tool_output(event: dict[str, Any], item: dict[str, Any] | None = None):
        item = item or {}
        if "output" in event:
            return event.get("output")
        if "result" in event:
            return event.get("result")
        if "output" in item:
            return item.get("output")
        if "result" in item:
            return item.get("result")
        return ""

    @staticmethod
    def _tool_output_available(event: dict[str, Any], item: dict[str, Any] | None = None) -> bool:
        """上游是否实际发送过工具结果字段，而不是把协议省略误读为空结果。"""
        item = item or {}
        return any(key in event or key in item for key in ("output", "result"))

    @staticmethod
    def _tool_completion_receipt(event: dict[str, Any]) -> dict[str, Any]:
        """保留 Hermes Runs 可证明的完成回执；不转存可能含敏感信息的错误文本。"""
        receipt: dict[str, Any] = {}
        if isinstance(event.get("duration"), (int, float)):
            receipt["duration"] = event["duration"]
        if "error" in event:
            receipt["error"] = bool(event.get("error"))
        return receipt

    def adapt(self, event: dict[str, Any]) -> dict[str, Any]:
        source_type = event.get("type") or event.get("event") or ""
        if source_type in {
            "response.reasoning.delta", "response.thinking.delta",
            "response.reasoning_summary.delta",
        }:
            return {"kind": "ignored", "source_type": source_type}
        if source_type in {"response.output_text.delta", "message.delta"}:
            from scribe3.llm_visible import strip_thinking_markup
            return {
                "kind": "text.delta",
                "delta": strip_thinking_markup(str(event.get("delta") or event.get("text") or "")),
                "source_type": source_type,
            }
        if source_type in {"tool.start", "tool.started"}:
            name = self._tool_name(event)
            blocked = self._maybe_block_tool(name, event.get("arguments", ""))
            if blocked:
                blocked["call_id"] = self._started_call_id(event, name)
                blocked["source_type"] = source_type
                if event.get("run_id") is not None:
                    blocked["run_id"] = event.get("run_id")
                return blocked
            out = {
                "kind": "tool.started",
                "name": name,
                "arguments": event.get("arguments", ""),
                "call_id": self._started_call_id(event, name),
                "source_type": source_type,
            }
            if event.get("run_id") is not None:
                out["run_id"] = event.get("run_id")
            return out
        if source_type in {"tool.complete", "tool.completed"}:
            name = self._tool_name(event)
            out = {
                "kind": "tool.output",
                "name": name,
                "call_id": self._completed_call_id(event, name),
                "output": self._tool_output(event),
                "output_available": self._tool_output_available(event),
                "completion": self._tool_completion_receipt(event),
                "source_type": source_type,
            }
            if event.get("run_id") is not None:
                out["run_id"] = event.get("run_id")
            return out
        if source_type == "approval.request":
            # Hermes MCP elicitation 事件常无 approval_id,只有 pattern_key/command/choices。
            # 用 run_id+timestamp 合成稳定 id,前端 key 与审批台账不致空。
            msg = event.get("message") or event.get("command") or event.get("description") or ""
            aid = event.get("approval_id") or event.get("id")
            if not aid:
                ts = event.get("timestamp") or ""
                aid = f"mcp:{event.get('run_id') or ''}:{ts}:{event.get('pattern_key') or 'elicitation'}"
            return {
                "kind": "approval.requested",
                "run_id": event.get("run_id"),
                "approval_id": aid,
                "call_id": self._call_id(event),
                "name": self._tool_name(event),
                "message": msg,
                "pattern_key": event.get("pattern_key"),
                "choices": event.get("choices"),
                "source_type": source_type,
            }
        if source_type in {"approval.resolved", "approval.responded"}:
            return {
                "kind": "approval.resolved",
                "run_id": event.get("run_id"),
                "approval_id": event.get("approval_id"),
                "call_id": self._call_id(event),
                "name": self._tool_name(event),
                "decision": event.get("decision") or event.get("choice"),
                "source_type": source_type,
            }
        if source_type == "response.output_item.added":
            item = event.get("item", {}) or {}
            if item.get("type") == "function_call":
                name = self._tool_name(event, item)
                blocked = self._maybe_block_tool(name, item.get("arguments", ""))
                if blocked:
                    blocked["call_id"] = self._started_call_id(event, name, item)
                    blocked["source_type"] = source_type
                    return blocked
                return {
                    "kind": "tool.started",
                    "name": name,
                    "arguments": item.get("arguments", ""),
                    "call_id": self._started_call_id(event, name, item),
                    "source_type": source_type,
                }
        if source_type == "response.output_item.done":
            item = event.get("item", {}) or {}
            if item.get("type") == "function_call_output":
                name = self._tool_name(event, item)
                return {
                    "kind": "tool.output",
                    "call_id": self._completed_call_id(event, name, item),
                    "output": self._tool_output(event, item),
                    "output_available": self._tool_output_available(event, item),
                    "source_type": source_type,
                }
            if item.get("type") == "function_call":
                return {
                    "kind": "tool.done",
                    "name": self._tool_name(event, item),
                    "arguments": item.get("arguments", ""),
                    "call_id": self._call_id(event, item),
                    "source_type": source_type,
                }
        if source_type == "response.completed":
            response = event.get("response", {}) or {}
            return {
                "kind": "run.completed",
                "response_id": response.get("id"),
                "usage": response.get("usage"),
                "source_type": source_type,
            }
        if source_type == "run.completed":
            out = {
                "kind": "run.completed",
                "run_id": event.get("run_id"),
                "usage": event.get("usage"),
                "source_type": source_type,
            }
            # Hermes Run 终态若给出下游模型标识，必须连同 usage 一起进入审计链。
            # 不能只在创建响应里短暂存在：审批恢复或 collector 重放会以终态事件覆写 response。
            if isinstance(event.get("model"), str) and event["model"]:
                out["model"] = event["model"]
            # Hermes Runs 终态原生携带最终回答时，这是工具链之后的判断说明，
            # 必须传给持久层供质量复核，不能只留 usage。旧协议未给该字段时保持兼容形状。
            if "output" in event:
                out["output"] = event.get("output")
            return out
        if source_type == "response.failed":
            response = event.get("response", {}) or {}
            return {
                "kind": "run.failed",
                "response_id": response.get("id"),
                "error": response.get("error") or event.get("error"),
                "source_type": source_type,
            }
        if source_type == "run.failed":
            return {
                "kind": "run.failed",
                "run_id": event.get("run_id"),
                "error": event.get("error"),
                "source_type": source_type,
            }
        return {"kind": "raw", "event": event, "source_type": source_type}

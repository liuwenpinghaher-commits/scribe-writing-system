"""Hermes Agent runtime adapter for scribe3."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping

import httpx

_log = logging.getLogger("scribe3.hermes_runtime")


def _strip_v1(url: str) -> str:
    url = url.rstrip("/")
    return url[:-3] if url.endswith("/v1") else url


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


class HermesRuntime:
    """Thin, testable boundary around Hermes HTTP runtime endpoints."""

    def __init__(self, *, api_base: str, profile: str = "default",
                 auth: HermesAuth | None = None):
        self.api_base = api_base.rstrip("/")
        self.root_url = _strip_v1(self.api_base)
        self.profile = profile
        self.auth = auth or HermesAuth()

    def _headers(self, *, session_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.auth.api_key(self.profile)}",
            "Content-Type": "application/json",
        }
        if session_key:
            headers["X-Hermes-Session-Key"] = session_key
        return headers

    def probe(self, *, timeout: float = 5.0) -> dict[str, Any]:
        status: dict[str, Any] = {
            "profile": self.profile,
            "api_base": self.api_base,
            "root_url": self.root_url,
            "ok": False,
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
            status["ok"] = (status["health"].get("status") == "ok")
        except Exception as exc:
            status["error"] = str(exc)[:200]
        return status

    def responses_events(self, message: Any, instructions: str, *,
                         model: str | None = None,
                         timeout: float = 600.0,
                         with_tools: bool = True,
                         conversation: str | None = None,
                         session_key: str | None = None,
                         store: bool = True,
                         server_label: str = "scribe3_read"):
        body: dict[str, Any] = {
            "input": message,
            "instructions": instructions,
            "stream": True,
            "store": bool(store),
        }
        if conversation:
            body["conversation"] = conversation
        if with_tools:
            body["tools"] = [{"type": "mcp", "server_label": server_label}]
        if model:
            body["model"] = model

        with httpx.stream(
            "POST",
            f"{self.api_base}/responses",
            timeout=timeout,
            headers=self._headers(session_key=session_key),
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
        body: dict[str, Any] = {"input": input_text}
        if instructions:
            body["instructions"] = instructions
        if session_id:
            body["session_id"] = session_id
        if conversation_history is not None:
            body["conversation_history"] = conversation_history
        if previous_response_id:
            body["previous_response_id"] = previous_response_id
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

    def adapt(self, event: dict[str, Any]) -> dict[str, Any]:
        source_type = event.get("type") or event.get("event") or ""
        if source_type in {"response.output_text.delta", "message.delta"}:
            return {
                "kind": "text.delta",
                "delta": event.get("delta", ""),
                "source_type": source_type,
            }
        if source_type in {"tool.start", "tool.started"}:
            out = {
                "kind": "tool.started",
                "name": self._tool_name(event),
                "arguments": event.get("arguments", ""),
                "call_id": self._call_id(event),
                "source_type": source_type,
            }
            if event.get("run_id") is not None:
                out["run_id"] = event.get("run_id")
            return out
        if source_type in {"tool.complete", "tool.completed"}:
            out = {
                "kind": "tool.output",
                "name": self._tool_name(event),
                "call_id": self._call_id(event),
                "output": self._tool_output(event),
                "source_type": source_type,
            }
            if event.get("run_id") is not None:
                out["run_id"] = event.get("run_id")
            return out
        if source_type == "approval.request":
            return {
                "kind": "approval.requested",
                "run_id": event.get("run_id"),
                "approval_id": event.get("approval_id"),
                "call_id": self._call_id(event),
                "name": self._tool_name(event),
                "message": event.get("message") or event.get("command") or event.get("description") or "",
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
                return {
                    "kind": "tool.started",
                    "name": self._tool_name(event, item),
                    "arguments": item.get("arguments", ""),
                    "call_id": self._call_id(event, item),
                    "source_type": source_type,
                }
        if source_type == "response.output_item.done":
            item = event.get("item", {}) or {}
            if item.get("type") == "function_call_output":
                return {
                    "kind": "tool.output",
                    "call_id": self._call_id(event, item),
                    "output": self._tool_output(event, item),
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
            return {
                "kind": "run.completed",
                "run_id": event.get("run_id"),
                "usage": event.get("usage"),
                "source_type": source_type,
            }
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

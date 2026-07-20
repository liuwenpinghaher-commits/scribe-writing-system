"""DeepSeek 官方无工具 Chat Completions 客户端。"""
from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

import httpx

from scribe3 import settings


OFFICIAL_API_BASE = "https://api.deepseek.com"
_CHAT_COMPLETIONS_URL = f"{OFFICIAL_API_BASE}/chat/completions"
_RETRYABLE_TRANSPORT_ERRORS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


@dataclass(frozen=True)
class ProviderIdentity:
    provider: str
    api_base: str
    model: str
    official: bool
    transport: str


@dataclass(frozen=True)
class CompletionResult:
    content: str
    model: str
    usage: dict[str, Any]
    finish_reason: str | None
    identity: ProviderIdentity


class DeepSeekError(RuntimeError):
    """不携带请求、header、响应正文或底层异常的安全错误基类。"""

    def __init__(
        self,
        message: str,
        *,
        identity: ProviderIdentity,
        status: str,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.identity = identity
        self.status = status
        self.status_code = status_code
        self.retryable = retryable


class DeepSeekConfigurationError(DeepSeekError):
    pass


class DeepSeekHTTPError(DeepSeekError):
    pass


class DeepSeekTransportError(DeepSeekError):
    pass


class DeepSeekResponseError(DeepSeekError):
    pass


class DeepSeekClient:
    """固定连接 DeepSeek 官方 API；注入 client 时由调用方管理其生命周期。"""

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._client = client

    @contextmanager
    def _client_scope(self):
        if self._client is not None:
            yield self._client
            return
        with httpx.Client() as client:
            yield client

    @staticmethod
    def _identity(model: str) -> ProviderIdentity:
        return ProviderIdentity(
            provider="deepseek",
            api_base=OFFICIAL_API_BASE,
            model=model,
            official=True,
            transport="httpx",
        )

    @staticmethod
    def _model(model: str | None) -> str:
        return model or str(settings.get_setting("llm.model"))

    @staticmethod
    def _api_key(identity: ProviderIdentity) -> str:
        value = settings.get_setting("DEEPSEEK_API_KEY")
        if not isinstance(value, str) or not value.strip():
            raise DeepSeekConfigurationError(
                "未配置 DEEPSEEK_API_KEY，无法调用 DeepSeek 官方接口",
                identity=identity,
                status="missing_api_key",
            )
        return value.strip()

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _retry_count() -> int:
        return max(0, int(settings.get_setting("llm.max_retries")))

    @staticmethod
    def _timeout() -> float:
        return float(settings.get_setting("llm.timeout_seconds"))

    @staticmethod
    def _safe_http_error(status_code: int, identity: ProviderIdentity) -> DeepSeekHTTPError:
        return DeepSeekHTTPError(
            f"DeepSeek 官方接口返回 HTTP {status_code}",
            identity=identity,
            status="http_error",
            status_code=status_code,
            retryable=status_code >= 500,
        )

    @staticmethod
    def _safe_transport_error(identity: ProviderIdentity) -> DeepSeekTransportError:
        return DeepSeekTransportError(
            "连接 DeepSeek 官方接口失败",
            identity=identity,
            status="transport_error",
            retryable=True,
        )

    @staticmethod
    def _safe_response_error(identity: ProviderIdentity) -> DeepSeekResponseError:
        return DeepSeekResponseError(
            "DeepSeek 官方接口返回无效补全结构",
            identity=identity,
            status="invalid_response",
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        thinking: str | None = None,
    ) -> CompletionResult:
        requested_model = self._model(model)
        identity = self._identity(requested_model)
        api_key = self._api_key(identity)
        body: dict[str, Any] = {
            "model": requested_model,
            "messages": messages,
            "stream": False,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        if thinking is not None:
            body["thinking"] = {"type": thinking}

        retries = self._retry_count()
        timeout = self._timeout()
        headers = self._headers(api_key)
        response: httpx.Response | None = None
        transport_exhausted = False

        with self._client_scope() as client:
            for attempt in range(retries + 1):
                transport_failed = False
                try:
                    response = client.post(
                        _CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=body,
                        timeout=timeout,
                    )
                except _RETRYABLE_TRANSPORT_ERRORS:
                    transport_failed = True

                if transport_failed:
                    if attempt < retries:
                        continue
                    transport_exhausted = True
                    break

                assert response is not None
                if response.status_code >= 500 and attempt < retries:
                    continue
                if response.status_code >= 400:
                    raise self._safe_http_error(response.status_code, identity)
                break

        if transport_exhausted:
            raise self._safe_transport_error(identity)
        if response is None:
            raise self._safe_transport_error(identity)

        invalid_json = False
        try:
            payload = response.json()
        except (TypeError, ValueError, json.JSONDecodeError):
            invalid_json = True
            payload = None
        if invalid_json or not isinstance(payload, Mapping):
            raise self._safe_response_error(identity)

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise self._safe_response_error(identity)
        first = choices[0]
        if not isinstance(first, Mapping):
            raise self._safe_response_error(identity)
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise self._safe_response_error(identity)
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise self._safe_response_error(identity)

        response_model = payload.get("model")
        result_model = response_model if isinstance(response_model, str) and response_model else requested_model
        result_identity = self._identity(result_model)
        usage = payload.get("usage")
        preserved_usage = dict(usage) if isinstance(usage, Mapping) else {}
        finish_reason = first.get("finish_reason")
        return CompletionResult(
            content=content,
            model=result_model,
            usage=preserved_usage,
            finish_reason=finish_reason if isinstance(finish_reason, str) else None,
            identity=result_identity,
        )

    def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        requested_model = self._model(model)
        identity = self._identity(requested_model)
        api_key = self._api_key(identity)
        body = {
            "model": requested_model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        headers = self._headers(api_key)
        retries = self._retry_count()
        timeout = self._timeout()
        transport_exhausted = False

        with self._client_scope() as client:
            for attempt in range(retries + 1):
                emitted = False
                transport_failed = False
                try:
                    with client.stream(
                        "POST",
                        _CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=body,
                        timeout=timeout,
                    ) as response:
                        if response.status_code >= 500:
                            if attempt < retries:
                                continue
                            raise self._safe_http_error(response.status_code, identity)
                        if response.status_code >= 400:
                            raise self._safe_http_error(response.status_code, identity)

                        for line in response.iter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            raw = line[5:].strip()
                            if raw == "[DONE]":
                                return
                            malformed = False
                            try:
                                payload = json.loads(raw)
                            except (TypeError, ValueError, json.JSONDecodeError):
                                malformed = True
                                payload = None
                            if malformed or not isinstance(payload, Mapping):
                                raise self._safe_response_error(identity)

                            event_model = payload.get("model")
                            if not isinstance(event_model, str) or not event_model:
                                event_model = requested_model
                            event_identity = self._identity(event_model)
                            choices = payload.get("choices")
                            if isinstance(choices, list) and choices:
                                choice = choices[0]
                                delta = choice.get("delta") if isinstance(choice, Mapping) else None
                                content = delta.get("content") if isinstance(delta, Mapping) else None
                                if isinstance(content, str) and content:
                                    emitted = True
                                    yield {
                                        "type": "delta",
                                        "delta": content,
                                        "model": event_model,
                                        "identity": event_identity,
                                    }
                            usage = payload.get("usage")
                            if isinstance(usage, Mapping):
                                emitted = True
                                yield {
                                    "type": "usage",
                                    "usage": dict(usage),
                                    "model": event_model,
                                    "identity": event_identity,
                                }
                        return
                except _RETRYABLE_TRANSPORT_ERRORS:
                    transport_failed = True

                if transport_failed:
                    if emitted or attempt >= retries:
                        transport_exhausted = True
                        break
                    continue

        if transport_exhausted:
            raise self._safe_transport_error(identity)


__all__ = [
    "CompletionResult",
    "DeepSeekClient",
    "DeepSeekConfigurationError",
    "DeepSeekError",
    "DeepSeekHTTPError",
    "DeepSeekResponseError",
    "DeepSeekTransportError",
    "OFFICIAL_API_BASE",
    "ProviderIdentity",
]

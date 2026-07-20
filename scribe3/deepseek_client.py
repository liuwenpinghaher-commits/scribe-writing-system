"""DeepSeek 官方无工具 Chat Completions 客户端。"""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from scribe3 import settings


OFFICIAL_API_BASE = "https://api.deepseek.com"
_CHAT_COMPLETIONS_URL = f"{OFFICIAL_API_BASE}/chat/completions"
_RETRYABLE_REQUEST_ERRORS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.ProxyError,
    httpx.RemoteProtocolError,
)


def _iter_sse_data(lines: Iterable[str]) -> Iterator[str]:
    """按 SSE 空行组帧，同一帧的多个 data 字段以换行连接。"""
    data_lines: list[str] = []
    first_line = True
    for line in lines:
        if first_line:
            first_line = False
            if line.startswith("\ufeff"):
                line = line[1:]
        if line == "":
            if data_lines:
                yield "\n".join(data_lines)
                data_lines.clear()
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if field != "data":
            continue
        if separator and value.startswith(" "):
            value = value[1:]
        data_lines.append(value)
    if data_lines:
        yield "\n".join(data_lines)


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
    def _client_scope(self) -> Iterator[httpx.Client]:
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
        if not isinstance(value, str) or not value:
            raise DeepSeekConfigurationError(
                "未配置 DEEPSEEK_API_KEY，无法调用 DeepSeek 官方接口",
                identity=identity,
                status="missing_api_key",
            )
        if any(not 0x21 <= ord(char) <= 0x7E for char in value):
            raise DeepSeekConfigurationError(
                "DEEPSEEK_API_KEY 包含 HTTP header 不允许的字符",
                identity=identity,
                status="invalid_api_key",
            )
        return value

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _retry_count(retry_count: int | None = None) -> int:
        value = settings.get_setting("llm.max_retries") if retry_count is None else retry_count
        return max(0, int(value))

    @staticmethod
    def _timeout(timeout_seconds: float | None = None) -> float:
        value = settings.get_setting("llm.timeout_seconds") if timeout_seconds is None else timeout_seconds
        return float(value)

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
    def _safe_transport_error(
        identity: ProviderIdentity,
        *,
        retryable: bool,
    ) -> DeepSeekTransportError:
        return DeepSeekTransportError(
            "连接 DeepSeek 官方接口失败",
            identity=identity,
            status="transport_error",
            retryable=retryable,
        )

    @staticmethod
    def _safe_request_error(
        error: httpx.RequestError,
        identity: ProviderIdentity,
    ) -> DeepSeekTransportError:
        return DeepSeekClient._safe_transport_error(
            identity,
            retryable=isinstance(error, _RETRYABLE_REQUEST_ERRORS),
        )

    @staticmethod
    def _safe_response_error(
        identity: ProviderIdentity,
        *,
        status: str = "invalid_response",
    ) -> DeepSeekResponseError:
        return DeepSeekResponseError(
            "DeepSeek 官方接口返回无效补全结构",
            identity=identity,
            status=status,
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        thinking: str | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
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

        retries = self._retry_count(retry_count)
        timeout = self._timeout(timeout_seconds)
        headers = self._headers(api_key)
        response: httpx.Response | None = None
        failure: DeepSeekError | None = None

        with self._client_scope() as client:
            for attempt in range(retries + 1):
                try:
                    response = client.post(
                        _CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=body,
                        timeout=timeout,
                    )
                except httpx.RequestError as error:
                    failure = self._safe_request_error(error, identity)
                else:
                    if response.status_code >= 400:
                        failure = self._safe_http_error(response.status_code, identity)
                    else:
                        failure = None
                        break

                if failure.retryable and attempt < retries:
                    response = None
                    continue
                response = None
                break

        if failure is not None:
            raise failure
        if response is None:
            raise self._safe_transport_error(identity, retryable=False)

        try:
            payload = response.json()
        except (TypeError, ValueError):
            payload = None
        if not isinstance(payload, Mapping):
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
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
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
        retries = self._retry_count(retry_count)
        timeout = self._timeout(timeout_seconds)
        final_failure: DeepSeekError | None = None

        with self._client_scope() as client:
            for attempt in range(retries + 1):
                sent_delta = False
                done = False
                pending_usage: dict[str, Any] | None = None
                attempt_failure: DeepSeekError | None = None
                try:
                    with client.stream(
                        "POST",
                        _CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=body,
                        timeout=timeout,
                    ) as response:
                        if response.status_code >= 400:
                            attempt_failure = self._safe_http_error(
                                response.status_code,
                                identity,
                            )
                        else:
                            for raw in _iter_sse_data(response.iter_lines()):
                                if raw.strip() == "[DONE]":
                                    done = True
                                    break

                                try:
                                    payload = json.loads(raw)
                                except (TypeError, ValueError):
                                    payload = None
                                if not isinstance(payload, Mapping):
                                    attempt_failure = self._safe_response_error(identity)
                                    break
                                if payload.get("error") is not None:
                                    attempt_failure = self._safe_response_error(
                                        identity,
                                        status="provider_error",
                                    )
                                    break

                                event_model = payload.get("model")
                                if not isinstance(event_model, str) or not event_model:
                                    event_model = requested_model
                                event_identity = self._identity(event_model)
                                recognized = False
                                choices = payload.get("choices")
                                if isinstance(choices, list):
                                    recognized = True
                                    if choices:
                                        choice = choices[0]
                                        delta = choice.get("delta") if isinstance(choice, Mapping) else None
                                        if not isinstance(delta, Mapping):
                                            attempt_failure = self._safe_response_error(identity)
                                            break
                                        content = delta.get("content")
                                        if content is not None and not isinstance(content, str):
                                            attempt_failure = self._safe_response_error(identity)
                                            break
                                        if content:
                                            sent_delta = True
                                            yield {
                                                "type": "delta",
                                                "delta": content,
                                                "model": event_model,
                                                "identity": event_identity,
                                            }

                                usage = payload.get("usage")
                                if isinstance(usage, Mapping):
                                    recognized = True
                                    pending_usage = {
                                        "type": "usage",
                                        "usage": dict(usage),
                                        "model": event_model,
                                        "identity": event_identity,
                                    }
                                if not recognized:
                                    attempt_failure = self._safe_response_error(identity)
                                    break
                except httpx.RequestError as error:
                    attempt_failure = self._safe_request_error(error, identity)

                if attempt_failure is not None:
                    if attempt_failure.retryable and not sent_delta and attempt < retries:
                        continue
                    final_failure = attempt_failure
                    break
                if not done:
                    final_failure = self._safe_response_error(
                        identity,
                        status="incomplete_stream",
                    )
                    break
                if not sent_delta:
                    final_failure = self._safe_response_error(identity)
                    break
                if pending_usage is not None:
                    yield pending_usage
                return

        if final_failure is not None:
            raise final_failure


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

"""Qwen 官方无工具 Chat Completions 客户端。

模块名、``DeepSeekClient`` 和异常类名暂作兼容导出；运行时供应商身份以 Qwen 为准。
"""
from __future__ import annotations

import json
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from scribe3 import settings


OFFICIAL_PROVIDER = "qwen"
DEFAULT_MODEL = "deepseek-v4-flash-0731"
OFFICIAL_API_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
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
    response_id: str | None = None


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
        response_id: str | None = None,
        usage: Mapping[str, Any] | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.identity = identity
        self.status = status
        self.status_code = status_code
        self.retryable = retryable
        self.response_id = response_id
        self.usage = dict(usage) if isinstance(usage, Mapping) else None
        self.model = model

    def with_observed_metadata(
        self,
        *,
        identity: ProviderIdentity,
        response_id: str | None,
        usage: Mapping[str, Any] | None,
        model: str | None,
    ):
        """只补安全供应商元数据；绝不挂原始 response/request。"""
        self.identity = identity
        self.response_id = response_id
        self.usage = dict(usage) if isinstance(usage, Mapping) else None
        self.model = model
        return self


class DeepSeekConfigurationError(DeepSeekError):
    pass


class DeepSeekHTTPError(DeepSeekError):
    pass


class DeepSeekTransportError(DeepSeekError):
    pass


class DeepSeekResponseError(DeepSeekError):
    pass


class _HardDeadlineElapsed(RuntimeError):
    """同步 HTTP transport 未响应关闭时的本地总时限信号。"""


class DeepSeekClient:
    """固定连接 Qwen 官方服务；类名仅为旧调用方保留兼容。"""

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._client = client

    @staticmethod
    def _close_in_background(client: httpx.Client) -> None:
        """尽力释放失控请求的 transport，但永不把 close 的等待带回调用方。"""
        def close() -> None:
            try:
                client.close()
            except Exception:
                pass

        threading.Thread(target=close, daemon=True).start()

    @contextmanager
    def _client_scope(self, *, defer_owned_close: bool = False) -> Iterator[httpx.Client]:
        if self._client is not None:
            yield self._client
            return
        client = httpx.Client()
        try:
            yield client
        finally:
            if defer_owned_close:
                self._close_in_background(client)
            else:
                client.close()

    @staticmethod
    def _identity(model: str) -> ProviderIdentity:
        return ProviderIdentity(
            provider=OFFICIAL_PROVIDER,
            api_base=OFFICIAL_API_BASE,
            model=model,
            official=True,
            transport="httpx",
        )

    def identity(self, model: str | None = None) -> ProviderIdentity:
        """解析并返回官方供应商身份；不读取 key，不创建 transport。"""
        return self._identity(self._model(model))

    @staticmethod
    def _model(model: str | None) -> str:
        return str(settings.get_setting("llm.model")) if model is None else model

    @staticmethod
    def _api_key(identity: ProviderIdentity) -> str:
        value = settings.get_setting("DEEPSEEK_API_KEY")
        if not isinstance(value, str) or not value:
            raise DeepSeekConfigurationError(
                "未配置 Qwen API 密钥（兼容设置键 DEEPSEEK_API_KEY），无法调用 Qwen 官方服务",
                identity=identity,
                status="missing_api_key",
            )
        if any(not 0x21 <= ord(char) <= 0x7E for char in value):
            raise DeepSeekConfigurationError(
                "Qwen API 密钥（兼容设置键 DEEPSEEK_API_KEY）包含 HTTP header 不允许的字符",
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
            f"Qwen 官方服务接口返回 HTTP {status_code}",
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
            "连接 Qwen 官方服务接口失败",
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
        response_id: str | None = None,
        usage: Mapping[str, Any] | None = None,
        model: str | None = None,
    ) -> DeepSeekResponseError:
        return DeepSeekResponseError(
            "Qwen 官方服务接口返回无效补全结构",
            identity=identity,
            status=status,
            response_id=response_id,
            usage=usage,
            model=model,
        )

    @staticmethod
    def _post_with_hard_deadline(
        client: httpx.Client,
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
        hard_deadline: bool,
    ) -> httpx.Response:
        """执行一次 POST；hard deadline 不依赖底层 transport 响应 ``close``。

        httpx 的 read timeout 不是总时限，且有些 transport 会忽略另一线程的
        ``client.close()``。质量作业必须能按期变为可重试失败，不能永久停在 running。
        底层线程只保存结果、不写状态，并设为 daemon，避免阻塞服务退出。
        """
        if not hard_deadline:
            return client.post(url, headers=headers, json=body, timeout=timeout)

        completed = threading.Event()
        result: dict[str, Any] = {}

        def request() -> None:
            try:
                result["response"] = client.post(
                    url, headers=headers, json=body, timeout=timeout,
                )
            except BaseException as exc:  # 仅转交至等待请求的线程，不在后台抛出。
                result["error"] = exc
            finally:
                completed.set()

        worker = threading.Thread(target=request, daemon=True)
        worker.start()
        if not completed.wait(timeout):
            DeepSeekClient._close_in_background(client)
            raise _HardDeadlineElapsed("provider request exceeded hard deadline")
        error = result.get("error")
        if error is not None:
            raise error
        response = result.get("response")
        if response is None:
            raise RuntimeError("provider transport returned no response")
        return response

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
        response_format: dict[str, Any] | None = None,
        hard_deadline: bool = False,
    ) -> CompletionResult:
        requested_model = self._model(model)
        identity = self._identity(requested_model)
        api_key = self._api_key(identity)
        body: dict[str, Any] = {
            "model": requested_model,
            "messages": messages,
            "stream": False,
        }
        from scribe3.llm_visible import with_thinking_headroom
        send_max = with_thinking_headroom(max_tokens, thinking=thinking)
        if send_max is not None:
            body["max_tokens"] = send_max
        if temperature is not None:
            body["temperature"] = temperature
        if thinking is not None:
            body["thinking"] = {"type": thinking}
        if response_format is not None:
            body["response_format"] = response_format

        retries = self._retry_count(retry_count)
        timeout = self._timeout(timeout_seconds)
        headers = self._headers(api_key)
        response: httpx.Response | None = None
        failure: DeepSeekError | None = None

        with self._client_scope(defer_owned_close=hard_deadline) as client:
            for attempt in range(retries + 1):
                try:
                    response = self._post_with_hard_deadline(
                        client, url=_CHAT_COMPLETIONS_URL, headers=headers, body=body,
                        timeout=timeout, hard_deadline=hard_deadline,
                    )
                except _HardDeadlineElapsed:
                    failure = self._safe_transport_error(identity, retryable=False)
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
        from scribe3.llm_visible import visible_message_text, visible_usage
        content = visible_message_text(message)
        if not content:
            raise self._safe_response_error(identity)

        response_model = payload.get("model")
        result_model = response_model if isinstance(response_model, str) and response_model else requested_model
        result_identity = self._identity(result_model)
        usage = payload.get("usage")
        preserved_usage = visible_usage(dict(usage) if isinstance(usage, Mapping) else {})
        finish_reason = first.get("finish_reason")
        response_id = payload.get("id")
        return CompletionResult(
            content=content,
            model=result_model,
            usage=preserved_usage,
            finish_reason=finish_reason if isinstance(finish_reason, str) else None,
            identity=result_identity,
            response_id=(response_id if isinstance(response_id, str) and response_id else None),
        )

    def _complete_raw(self, messages: list[dict[str, Any]], **kwargs) -> CompletionResult:
        return self.complete(messages, **kwargs)

    def complete_json_with_result(
        self,
        messages: list[dict[str, Any]],
        *,
        schema: type,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        thinking: str | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
        max_repairs: int = 2,
        hard_deadline: bool = False,
    ):
        import json as _json
        from pydantic import ValidationError as _ValidationError

        schema_contract = _json.dumps(
            schema.model_json_schema(), ensure_ascii=False, separators=(",", ":"),
        )
        # response_format 是供应商能力声明，不是模型逐次遵循的证明。质量等需要可审计
        # 结构的调用必须在首轮就给出完整 Schema；只在失败后补约束会白白损失一次真实调用。
        # 合同另起 user turn，保留调用方原始 system/user 任务的角色和顺序。
        initial_messages = messages + [{
            "role": "user",
            "content": (
                "只返回一个有效 JSON 对象，不得添加解释、Markdown 或代码围栏。"
                f"必须符合此 JSON Schema：{schema_contract}"
            ),
        }]
        result = self._complete_raw(
            initial_messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking=thinking,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            response_format={"type": "json_object"},
            hard_deadline=hard_deadline,
        )
        content = (result.content or "").strip()
        if not content:
            raise ValueError("LLM 返回空响应，无法解析 JSON")

        def repair_messages(reason: str) -> list[dict[str, Any]]:
            # 不把非 JSON 回应回灌成 assistant turn：部分推理模型会沿着该文本继续解释。
            # 重新发送原任务与明确 schema，让修复调用独立地满足结构化合同。
            return initial_messages + [{
                "role": "user",
                "content": (
                    f"上一轮结构化输出失败（{reason}）。只返回一个有效 JSON 对象，"
                    f"不得添加解释、Markdown 或代码围栏。必须符合此 JSON Schema：{schema_contract}"
                ),
            }]

        for attempt in range(max_repairs + 1):
            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                if start < 0 or end <= start:
                    raise ValueError("响应中未找到 JSON 对象")
                payload = _json.loads(content[start:end])
            except (ValueError, _json.JSONDecodeError) as exc:
                if attempt >= max_repairs:
                    raise ValueError(f"JSON 格式修复 {max_repairs} 次后仍失败: {exc}") from exc
                repair_result = self._complete_raw(
                    repair_messages("无法解析为 JSON 对象"),
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    thinking=thinking,
                    timeout_seconds=timeout_seconds,
                    retry_count=retry_count,
                    response_format={"type": "json_object"},
                    hard_deadline=hard_deadline,
                )
                result = repair_result
                content = (repair_result.content or "").strip()
                if not content:
                    raise ValueError("LLM 修复请求返回空响应")
                continue

            try:
                return schema.model_validate(payload), result
            except _ValidationError as exc:
                if attempt >= max_repairs:
                    raise ValueError(f"JSON schema 校验失败: {exc}") from exc
                repair_result = self._complete_raw(
                    repair_messages(f"字段不符合要求: {exc.errors()[:3]}"),
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    thinking=thinking,
                    timeout_seconds=timeout_seconds,
                    retry_count=retry_count,
                    response_format={"type": "json_object"},
                    hard_deadline=hard_deadline,
                )
                result = repair_result
                content = (repair_result.content or "").strip()
                if not content:
                    raise ValueError("LLM 修复请求返回空响应")
                continue

        raise ValueError("JSON 格式修复次数耗尽")

    def complete_json(
        self,
        messages: list[dict[str, Any]],
        *,
        schema: type,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        thinking: str | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
        max_repairs: int = 2,
        hard_deadline: bool = False,
    ):
        """兼容旧调用方：只返回已校验 schema，元数据走 complete_json_with_result。"""
        parsed, _result = self.complete_json_with_result(
            messages, schema=schema, model=model, max_tokens=max_tokens,
            temperature=temperature, thinking=thinking, timeout_seconds=timeout_seconds,
            retry_count=retry_count, max_repairs=max_repairs, hard_deadline=hard_deadline,
        )
        return parsed

    def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        thinking: str | None = None,
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
        from scribe3.llm_visible import with_thinking_headroom
        send_max = with_thinking_headroom(max_tokens, thinking=thinking)
        if send_max is not None:
            body["max_tokens"] = send_max
        if thinking is not None:
            body["thinking"] = {"type": thinking}
        headers = self._headers(api_key)
        retries = self._retry_count(retry_count)
        timeout = self._timeout(timeout_seconds)
        final_failure: DeepSeekError | None = None

        with self._client_scope() as client:
            for attempt in range(retries + 1):
                sent_delta = False
                emitted_event = False
                done = False
                observed_usage: dict[str, Any] | None = None
                from scribe3.llm_visible import VisibleStreamFilter, visible_delta_text, visible_usage
                visible_filter = VisibleStreamFilter()
                terminal_model = requested_model
                terminal_identity = identity
                terminal_response_id: str | None = None
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
                                payload_response_id = payload.get("id")
                                if payload_response_id is not None:
                                    if (not isinstance(payload_response_id, str)
                                            or not payload_response_id):
                                        attempt_failure = self._safe_response_error(identity)
                                        break
                                    if terminal_response_id is None:
                                        terminal_response_id = payload_response_id
                                    elif terminal_response_id != payload_response_id:
                                        # 单条供应商流中 id 漂移表示响应被混线，不得
                                        # 任选一个冒充可审计 provider_request_id。
                                        attempt_failure = self._safe_response_error(identity)
                                        break

                                event_model = payload.get("model")
                                if not isinstance(event_model, str) or not event_model:
                                    event_model = requested_model
                                event_identity = self._identity(event_model)
                                terminal_model = event_model
                                terminal_identity = event_identity
                                recognized = False
                                delta_event: dict[str, Any] | None = None
                                choices = payload.get("choices")
                                if isinstance(choices, list):
                                    recognized = True
                                    if choices:
                                        choice = choices[0]
                                        delta = choice.get("delta") if isinstance(choice, Mapping) else None
                                        if not isinstance(delta, Mapping):
                                            attempt_failure = self._safe_response_error(identity)
                                            break
                                        raw_content = delta.get("content")
                                        if raw_content is not None and not isinstance(raw_content, str) and not isinstance(raw_content, list):
                                            attempt_failure = self._safe_response_error(identity)
                                            break
                                        content = visible_filter.feed(visible_delta_text(delta))
                                        if content:
                                            delta_event = {
                                                "type": "delta",
                                                "delta": content,
                                                "model": event_model,
                                                "identity": event_identity,
                                            }
                                            if terminal_response_id is not None:
                                                delta_event["response_id"] = terminal_response_id

                                usage = payload.get("usage")
                                if isinstance(usage, Mapping):
                                    recognized = True
                                    observed_usage = visible_usage(dict(usage))
                                    emitted_event = True
                                    yield {
                                        "type": "usage",
                                        "usage": observed_usage,
                                        "model": event_model,
                                        "identity": event_identity,
                                    }
                                if payload.get("error") is not None:
                                    attempt_failure = self._safe_response_error(
                                        terminal_identity,
                                        status="provider_error",
                                    )
                                    break
                                if not recognized:
                                    attempt_failure = self._safe_response_error(identity)
                                    break
                                if delta_event is not None:
                                    sent_delta = True
                                    emitted_event = True
                                    yield delta_event
                except httpx.RequestError as error:
                    attempt_failure = self._safe_request_error(error, identity)

                if attempt_failure is not None:
                    attempt_failure.with_observed_metadata(
                        identity=terminal_identity,
                        response_id=terminal_response_id,
                        usage=observed_usage,
                        model=terminal_model,
                    )
                    if attempt_failure.retryable and not emitted_event and attempt < retries:
                        continue
                    final_failure = attempt_failure
                    break
                if not done:
                    final_failure = self._safe_response_error(
                        terminal_identity,
                        status="incomplete_stream",
                        response_id=terminal_response_id,
                        usage=observed_usage,
                        model=terminal_model,
                    )
                    break
                leftover = visible_filter.flush()
                if leftover:
                    sent_delta = True
                    emitted_event = True
                    tail = {
                        "type": "delta",
                        "delta": leftover,
                        "model": terminal_model,
                        "identity": terminal_identity,
                    }
                    if terminal_response_id is not None:
                        tail["response_id"] = terminal_response_id
                    yield tail
                if not sent_delta:
                    final_failure = self._safe_response_error(
                        terminal_identity,
                        response_id=terminal_response_id,
                        usage=observed_usage,
                        model=terminal_model,
                    )
                    break
                done_event = {
                    "type": "done",
                    "model": terminal_model,
                    "identity": terminal_identity,
                }
                # 供应商 payload 没有 id 时不生成本地替代值；保持旧事件形状。
                if terminal_response_id is not None:
                    done_event["response_id"] = terminal_response_id
                yield done_event
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
    "DEFAULT_MODEL",
    "OFFICIAL_API_BASE",
    "OFFICIAL_PROVIDER",
    "ProviderIdentity",
]

"""Scribe LLM 路由门面。

无工具 Chat Completions 统一委托已审查的 Qwen 官方服务客户端；
Hermes 只保留 Responses 工具面与 Runs 边界。超时、重试、流式首 delta 后不重试及
安全错误由官方客户端实现；本门面保留旧签名和调用计数语义。
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict

import httpx

from scribe3.deepseek_client import (
    DEFAULT_MODEL,
    OFFICIAL_API_BASE,
    OFFICIAL_PROVIDER,
    DeepSeekClient,
    DeepSeekError,
    DeepSeekResponseError,
    ProviderIdentity,
)
from scribe3.hermes_runtime import HermesAuth, HermesRuntime

_RETRYABLE = (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError)

_log = logging.getLogger("scribe3.llm")

# 审计 P1-12(方案原文"接线或删除二选一"):原 CircuitBreaker 死类已删(0.18 网关
# 自带重试/排队,持续故障由其兜);日调用帽在此单点接线——llm.py 是全部 LLM 出口
# (complete/stream/responses),比散在 app 端点层可靠。
# H-10(v018 审查):计数升级为跨进程共享 SQLite 台账(scribe3/usage.py)——app 与
# MCP stdio 进程同记一本账,日帽是真正的系统级保险丝;台账故障 fail-open 回退
# 进程内计数。另:重试/agentic 网关内多轮/流式断连已耗 token 都只计 1 笔,
# 帽 ≠ 精确 token 成本;token 真实用量见 store.usage_summary()(/ai/usage)。
# Phase 2 设置中心迁移:模型/超时/重试/日帽全部改从 settings 读,热生效(无需重启)。


def _cap() -> int:
    from scribe3.settings import get_setting
    return get_setting("SCRIBE3_DAILY_CALL_CAP")


def default_model() -> str:
    from scribe3.settings import get_setting
    return get_setting("llm.model")


def default_timeout() -> float:
    from scribe3.settings import get_setting
    return get_setting("llm.timeout_seconds")


def max_retries() -> int:
    from scribe3.settings import get_setting
    return get_setting("llm.max_retries")


def official_qwen_provider_identity(model: str | None = None) -> dict:
    """返回无工具 Qwen 路由的安全官方身份；只确定模型，不读取 API key。"""
    return asdict(DeepSeekClient().identity(model))


def official_deepseek_provider_identity(model: str | None = None) -> dict:
    """旧函数名兼容层；返回的真实供应商身份始终是 Qwen。"""
    return official_qwen_provider_identity(model)


def _provider_identity_for_usage(
    model: str | None,
    *,
    client=None,
    error: Exception | None = None,
) -> ProviderIdentity:
    if isinstance(error, DeepSeekError):
        return error.identity
    if client is not None:
        try:
            identity = client.identity(model)
            if isinstance(identity, ProviderIdentity):
                return identity
        except Exception:
            pass
    resolved_model = model if model is not None else default_model()
    return ProviderIdentity(
        provider=OFFICIAL_PROVIDER,
        api_base=OFFICIAL_API_BASE,
        model=str(resolved_model if resolved_model is not None else DEFAULT_MODEL),
        official=True,
        transport="httpx",
    )


def _record_provider_usage(
    identity: ProviderIdentity,
    *,
    status: str,
    http_status: int | None = None,
    usage: dict | None = None,
) -> None:
    """台账是旁路证据；任何写账故障都不能改变 LLM 主调用结果。"""
    try:
        from scribe3 import usage as usage_mod
        usage_mod.record_provider_usage(
            provider=identity.provider,
            model=identity.model,
            transport=identity.transport,
            status=status,
            http_status=http_status,
            usage=usage,
        )
    except Exception as error:
        _log.warning("官方供应商 usage 写账失败(忽略): %s", type(error).__name__)


def _record_provider_failure(
    error: Exception,
    *,
    model: str | None,
    client=None,
) -> None:
    identity = _provider_identity_for_usage(model, client=client, error=error)
    status = error.status if isinstance(error, DeepSeekError) else "failed"
    http_status = error.status_code if isinstance(error, DeepSeekError) else None
    _record_provider_usage(
        identity,
        status=status,
        http_status=http_status,
        usage=(error.usage if isinstance(error, DeepSeekError) else None),
    )


def _compat_retry_count(total_attempts: int | None = None) -> int:
    """旧设置/门面表示总尝试次数，兼容客户端表示首次之后的重试次数。"""
    attempts = max_retries() if total_attempts is None else total_attempts
    return max(0, int(attempts) - 1)


def _reset_daily_counter() -> None:
    from scribe3 import usage as _usage
    _usage.reset_today()


def _tick_daily() -> None:
    """每次 LLM 调用前记一笔(共享台账);超日帽抛错(调用方 fail-soft 链各自兜)。"""
    from scribe3 import usage as _usage
    _usage.tick(_cap())


def daily_remaining() -> int | None:
    """B4:剩余日帽额度；cap=0(无限)返回 None，供多发操作跳过预检。"""
    from scribe3 import usage as _usage
    cap = _cap()
    if cap == 0:
        return None
    used, _scope = _usage.used_today()
    return max(0, cap - used)

HERMES = os.environ.get("HERMES_API", "http://127.0.0.1:8642/v1")
# 主编 agentic 走 scribe3 profile 专属网关 :8643(挂 scribe3 MCP);与 default :8642 隔离。
HERMES_RESPONSES = os.environ.get("HERMES_RESPONSES_API", "http://127.0.0.1:8643/v1")
HERMES_RESPONSES_PROFILE = os.environ.get("HERMES_RESPONSES_PROFILE", "scribe3")
# 会改状态的长任务 Runs 走独立写 profile。Hermes Runs 不支持 per-run tools 裁剪,
# 工具面必须靠 gateway profile/platform_toolsets 隔离。
HERMES_RUNS = os.environ.get("HERMES_RUNS_API", "http://127.0.0.1:8644/v1")
HERMES_RUNS_PROFILE = os.environ.get("HERMES_RUNS_PROFILE", "scribe3_write")


def _stream_with_retry(make_stream, max_retries: int | None = None):
    """对'打开流 + 取到首个 yield 前'的瞬时错重试;已 yield 后不重试(避免重发 delta)。

    make_stream: () -> generator(每次调用新建一条 httpx.stream 并 yield delta/event)。"""
    if max_retries is None:
        from scribe3.settings import get_setting
        max_retries = get_setting("llm.max_retries")
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


def hermes_complete_result(prompt: str, system: str | None = None,
                           model: str | None = None, timeout: float | None = None,
                           max_tokens: int | None = None,
                           retries_override: int | None = None,
                           thinking: str | None = None,
                           temperature: float | None = None,
                           official_api: bool = False):
    """Qwen 官方无工具补全，返回带安全 provider 证据的完整结果。"""
    _tick_daily()
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": prompt}]
    retry_count = _compat_retry_count(retries_override)
    client = DeepSeekClient()
    try:
        result = client.complete(
            msgs,
            model=model,
            max_tokens=max_tokens if max_tokens else None,
            temperature=temperature,
            thinking=thinking,
            timeout_seconds=timeout,
            retry_count=retry_count,
        )
    except Exception as error:
        _record_provider_failure(error, model=model, client=client)
        raise
    _record_provider_usage(
        result.identity,
        status="completed",
        http_status=200,
        usage=result.usage,
    )
    return result


def hermes_complete(prompt: str, system: str | None = None,
                    model: str | None = None, timeout: float | None = None,
                    max_tokens: int | None = None,
                    retries_override: int | None = None,
                    thinking: str | None = None,
                    temperature: float | None = None,
                    official_api: bool = False) -> str:
    """Qwen 官方无工具补全；旧名与 ``official_api`` 仅作兼容。"""
    return hermes_complete_result(
        prompt, system, model=model, timeout=timeout, max_tokens=max_tokens,
        retries_override=retries_override, thinking=thinking,
        temperature=temperature, official_api=official_api,
    ).content


def hermes_complete_stream(prompt: str, system: str | None = None,
                           model: str | None = None, timeout: float | None = None,
                           history: list[dict] | None = None):
    """Qwen 官方流式补全；对旧消费者仅 yield delta 文本。
客户端的 usage 事件不会被当作文本 yield；已 yield 后断流由客户端直接上抛。

    history(U-009 主编速答失忆修复):按序插在 system 与本轮 user 之间的既往轮次
    ([{"role": "user"|"assistant", "content": str}, ...])。None/[] = 旧行为(单轮)。
    此前 msgs 恒为 [system, 当前一句]——模型从未见过自己上一轮说了什么,作者选了主编
    自己给的"方向C",主编反问"方向C是什么"。预算截断是调用方的责任,这里只拼接。"""
    _tick_daily()
    msgs = ([{"role": "system", "content": system}] if system else []) \
        + [m for m in (history or [])
           if m.get("role") in ("user", "assistant") and m.get("content")] \
        + [{"role": "user", "content": prompt}]

    client = DeepSeekClient()
    identity = _provider_identity_for_usage(model, client=client)
    ledger_finalized = False
    terminal_seen = False
    usage: dict = {}
    usage_received = False
    provider_response_id: str | None = None
    event_model = model
    try:
        for event in client.stream(
            msgs,
            model=model,
            timeout_seconds=timeout,
            retry_count=_compat_retry_count(),
        ):
            event_identity = event.get("identity")
            if isinstance(event_identity, ProviderIdentity):
                identity = event_identity
            if isinstance(event.get("model"), str) and event["model"]:
                event_model = event["model"]
            if isinstance(event.get("response_id"), str) and event["response_id"]:
                provider_response_id = event["response_id"]
            if event.get("type") == "usage" and isinstance(event.get("usage"), dict):
                if not usage_received:
                    usage = dict(event["usage"])
                    usage_received = True
            elif event.get("type") == "done":
                terminal_seen = True
                ledger_finalized = True
                _record_provider_usage(
                    identity,
                    status="completed",
                    http_status=200,
                    usage=usage,
                )
                break
            elif event.get("type") == "delta" and event.get("delta"):
                yield event["delta"]
    except GeneratorExit:
        if not ledger_finalized:
            ledger_finalized = True
            _record_provider_usage(
                identity,
                status="cancelled",
                usage=usage if usage_received else None,
            )
        raise
    except Exception as error:
        if not ledger_finalized:
            ledger_finalized = True
            _record_provider_failure(error, model=model, client=client)
        raise
    if not terminal_seen:
        ledger_finalized = True
        error = DeepSeekResponseError(
            "Qwen 官方服务流未完整结束",
            identity=identity,
            status="incomplete_stream",
            response_id=provider_response_id,
            usage=usage if usage_received else None,
            model=event_model or identity.model,
        )
        _record_provider_failure(error, model=model, client=client)
        raise error


def hermes_responses_events(message, instructions: str, model: str | None = None,
                            timeout: float = 600.0, with_tools: bool = True,
                            max_tokens: int | None = None,
                            conversation: str | None = None,
                            previous_response_id: str | None = None,
                            session_key: str | None = None,
                            store: bool = True,
                            context_revision: int | None = None,
                            context_hash: str | None = None,
                            server_label: str = "scribe3_read"):
    """主编 agentic:POST scribe3 网关(:8643)/v1/responses(可选 tools=scribe3 MCP + stream),逐事件 yield。
    默认 server_label='scribe3_read',普通 Responses 写作/讨论只暴露只读 s3_ 工具。
    SSE 为 OpenAI Responses 标准(每条 data: 的 JSON 带 type 字段)。
    建链瞬时错自动重试,已 yield 后不重试。

    with_tools:H-01 work-scoped MCP 开关。为 True 时 body 挂指定 scribe3 MCP 面;调用方必须在
    instructions 内钉死当前 work,让所有 s3_ 工具显式传 work 参数。with_tools=False →
    直连 Qwen 官方服务的 chat completions 流。Hermes Responses 网关会按 profile 默认
    挂载 MCP,仅省略 body.tools 不能真正禁用工具，纯生成必须物理绕开该代理层。"""
    _tick_daily()
    if not with_tools:
        messages = [{"role": "system", "content": instructions}]
        if isinstance(message, list):
            messages.extend(message)
        else:
            messages.append({"role": "user", "content": message})
        usage: dict = {}
        usage_received = False
        client = DeepSeekClient()
        identity = _provider_identity_for_usage(model, client=client)
        ledger_finalized = False
        terminal_seen = False
        event_model = model
        provider_response_id: str | None = None
        stream_kwargs = {
            "model": model,
            "timeout_seconds": timeout,
            "retry_count": _compat_retry_count(),
        }
        if max_tokens is not None:
            stream_kwargs["max_tokens"] = max_tokens
        try:
            for event in client.stream(
                messages,
                **stream_kwargs,
            ):
                event_identity = event.get("identity")
                if isinstance(event_identity, ProviderIdentity):
                    identity = event_identity
                if isinstance(event.get("model"), str) and event["model"]:
                    event_model = event["model"]
                if isinstance(event.get("response_id"), str) and event["response_id"]:
                    provider_response_id = event["response_id"]
                if event.get("type") == "delta" and event.get("delta"):
                    delta_event = {
                        "type": "response.output_text.delta",
                        "delta": event["delta"],
                        "trace": asdict(identity),
                    }
                    if provider_response_id is not None:
                        delta_event["response_id"] = provider_response_id
                    if event_model is not None:
                        delta_event["model"] = event_model
                    if usage_received:
                        delta_event["usage"] = dict(usage)
                    yield delta_event
                elif event.get("type") == "usage" and isinstance(event.get("usage"), dict):
                    if not usage_received:
                        usage = dict(event["usage"])
                        usage_received = True
                elif event.get("type") == "done":
                    if isinstance(event.get("response_id"), str) and event["response_id"]:
                        provider_response_id = event["response_id"]
                    terminal_seen = True
                    ledger_finalized = True
                    _record_provider_usage(
                        identity,
                        status="completed",
                        http_status=200,
                        usage=usage,
                    )
                    break
        except GeneratorExit:
            if not ledger_finalized:
                ledger_finalized = True
                _record_provider_usage(
                    identity,
                    status="cancelled",
                    usage=usage if usage_received else None,
                )
            raise
        except Exception as error:
            if not ledger_finalized:
                ledger_finalized = True
                _record_provider_failure(error, model=model, client=client)
            raise
        if not terminal_seen:
            ledger_finalized = True
            error = DeepSeekResponseError(
                "Qwen 官方服务流未完整结束",
                identity=identity,
                status="incomplete_stream",
                response_id=provider_response_id,
                usage=usage if usage_received else None,
                model=event_model or identity.model,
            )
            _record_provider_failure(error, model=model, client=client)
            raise error
        yield {
            "type": "response.completed",
            "response": {
                "id": provider_response_id,
                "model": event_model,
                "usage": usage,
            },
            "trace": asdict(identity),
        }
        return

    runtime = HermesRuntime(api_base=HERMES_RESPONSES, profile=HERMES_RESPONSES_PROFILE, auth=HermesAuth())

    def make_stream():
        yield from runtime.responses_events(
            message,
            instructions,
            model=model,
            timeout=timeout,
            with_tools=with_tools,
            conversation=conversation,
            previous_response_id=previous_response_id,
            session_key=session_key,
            store=store,
            context_revision=context_revision,
            context_hash=context_hash,
            server_label=server_label,
        )

    yield from _stream_with_retry(make_stream)

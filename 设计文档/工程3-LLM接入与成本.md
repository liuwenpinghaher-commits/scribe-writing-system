# 工程3 · LLM 接入与成本

> **所属系统**:Scribe · 人机协同 · 百万字 · 写小说系统
> **文档编号**:工程3
> **基线日期**:2026 年 6 月
> **上游依据**:
> - [00-总纲与数据模型](00-总纲与数据模型.md)(原则 §3、数据模型 §4、文档公约 §7)
> - [设计哲学-第一性原理与LLM能力衔接](设计哲学-第一性原理与LLM能力衔接.md)(§2 能力矩阵——选型据此)
> - [实现3-编排引擎](实现3-编排引擎.md)(LLMRouter 的直接消费方)
> **本文件是旧 13 的完整改写**,不是叠加——旧结构已废弃,内容按协作回路重新组织。

---

## 目录

1. 在回路中的位置与职责
2. 设计目标与百万字挑战
3. 详细设计
   - 3.1 Provider 抽象层(接口 / 实现 / 注册)
   - 3.2 统一 `complete` 与 `stream_complete` 接口
   - 3.3 Agent 角色路由表与降级链
   - 3.4 选型原则与禁止事项
   - 3.5 两层缓存机制(Prompt 前缀缓存 + 结果缓存)
   - 3.6 成本计量系统(TokenLedger + DDL + 端到端伪代码)
   - 3.7 预算管理与告警(状态机 + 超预算降级)
   - 3.8 可靠性机制(重试 / 超时 / 限流 / 故障切换)
   - 3.9 百万字 Token 量级估算公式
   - 3.10 成本控制策略汇总
4. 数据契约
5. 对外接口
6. 失败模式与缓解
7. MVP vs 完整版
8. 证据与引用
9. 开放问题

---

## 1. 在回路中的位置与职责

### 1.1 在协作回路中的角色

```
        人(想象 + 意见)
              │
    ┌─────────▼─────────┐
    │  内核层 / 编排层    │  ← 实现3-编排引擎、各 Agent
    └─────────┬─────────┘
              │  complete(agentRole, prompt, opts)
              ▼
    ┌─────────────────────┐
    │   工程3 · LLM接入层  │  ← 本文档
    │  路由·缓存·计量·限流  │
    └──┬──────────┬───────┘
       │          │
 ┌─────▼──┐  ┌───▼──────┐
 │Anthropic│  │ OpenAI   │  … 更多 Provider
 └─────────┘  └──────────┘
```

**LLM 接入层是所有 Agent 调用 LLM 的唯一出口**。它对上层屏蔽多家 Provider 的 API 差异,对内实施按角色路由、双层缓存降本、成本计量与预算控制、可靠性保障。

### 1.2 负责什么

| 职责 | 说明 |
|---|---|
| **Provider 抽象** | 统一接口,屏蔽 Claude / GPT / 自托管模型的 SDK 差异 |
| **模型路由** | 按 AgentRole 分配档位(写作旗舰、规划/审校/摘要/抽取快模型) |
| **流式支持** | 向上层提供 async generator 流式接口(前端 SSE) |
| **双层缓存** | Prompt 前缀缓存(Provider 侧) + 结果缓存(应用侧),降低重复 token 消耗 |
| **成本计量** | 每次调用记录 token 数,聚合到 per-Work / per-Chapter / per-AgentRole 粒度 |
| **预算控制** | 设定预算上限;超限时告警并自动触发降级链(对接实现3编排引擎) |
| **可靠性** | 重试、超时、速率限制令牌桶、降级链、跨 Provider 故障切换 |
| **可观测性** | 每次调用记录请求唯一 ID、模型 ID、延迟、token 数 |

### 1.3 不负责什么

- **不构造 prompt 内容**——prompt 由各 Agent 负责,本层只接收最终 messages
- **不做上下文裁剪/拼装**——由实现4(记忆与检索)的 `assembleContext` 完成
- **不持久化章节正文或任何业务实体**——数据层职责
- **不调度 Agent**——实现3(编排引擎)职责

---

## 2. 设计目标与百万字挑战

### 2.1 设计目标

| 目标 | 度量方式 |
|---|---|
| **质量**:写作 Agent 用旗舰模型,产出连贯、风格一致的正文 | 工程6 质量度量(BooookScore 类指标)≥ 基准线 |
| **成本可控**:高频非写作调用用快模型,整体费用可预算 | per-万字综合成本 ≤ 预算上限(实测后标定) |
| **可靠性**:单次调用失败不中断生成流程 | P99 端到端重试成功率 ≥ 99% |
| **透明可观测**:每笔 token 消耗可追溯 | 粒度:per-Work / per-Chapter / per-AgentRole |
| **可扩展**:新增 Provider 或切换默认模型代价极小 | 新增 = 实现一个 Provider 类 + 注册,接口变更量 = 0 |

### 2.2 百万字下的五大挑战

**挑战 1:调用次数与累积成本**

百万字约 333 章(按每章 3000 字)。每章完整生成涉及大纲生成、正文生成、审校、摘要更新、实体/伏笔抽取等至少 5–8 次独立 LLM 调用。

```
333 章 × 8 次/章 = ~2664 次 LLM 调用
实际 token 总量 ≈ 正文 token 数的 4–8 倍(含上下文注入)
```

【设计决策】必须在路由层精细区分"哪个 Agent 用什么档位",不能全用旗舰模型。

**挑战 2:旗舰模型速率限制(TPM)**

高并发或多 Agent 并行时,单 Provider 旗舰模型的每分钟 token 限额(TPM)是真实瓶颈。需要内置速率限制令牌桶,触及上限时自动排队或路由到备选。

**挑战 3:稳定前缀的 Prompt 缓存价值极高**

每章生成都携带相对稳定的"设定前缀"(角色档案、世界规则、全局写作规范)。若 Provider 支持 prompt caching(如 Anthropic),将设定前缀置于缓存区可大幅降低 input token 成本。百万字尺度下此优化价值显著。【需复核:各 Provider caching 最新可用性、最小 block 长度、计费规则】

**挑战 4:跨章节成本监控**

若不加控制,单部百万字作品的 LLM 费用可能远超预算。需要 per-Work / per-Chapter 粒度的实时计量与预算告警,超限时自动触发降级策略。

**挑战 5:模型快速迭代**

LLM 领域版本更新频繁。接入层必须做到"仅改配置、不改业务代码"即可切换或新增模型。

---

## 3. 详细设计

### 3.1 Provider 抽象层

#### 3.1.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│            上层调用方(编排引擎 / 各 Agent)                         │
│   complete(agentRole, prompt, opts) / stream_complete(...)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
             ┌───────────────▼────────────────┐
             │          LLMRouter              │
             │  路由决策 + 缓存检查 + 预算检查   │
             │  + 速率限制 + 计量记录           │
             └───┬─────────────┬──────────────┘
                 │             │
     ┌───────────▼──┐   ┌──────▼────────────┐   ┌──────────────┐
     │Anthropic      │   │ OpenAIProvider    │   │ VLLMProvider │
     │Provider       │   │                   │   │ (自托管备用) │
     └───────────────┘   └───────────────────┘   └──────────────┘
         │                      │
     Anthropic API          OpenAI API
```

所有 Provider 实现同一 `LLMProvider` 抽象基类。`LLMRouter` 只与抽象接口交互,不关心底层 API 差异。

#### 3.1.2 LLMProvider 抽象接口

```python
# llm/provider_base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Any, Optional


@dataclass
class LLMRequest:
    """
    统一请求结构。由 LLMRouter 组装后传给具体 Provider。
    """
    messages: list[dict]            # OpenAI-style messages 格式
    model_id: str                   # 具体模型 ID,由路由层填充
    max_tokens: int = 4096
    temperature: float = 0.8
    stop_sequences: list[str] = field(default_factory=list)
    stream: bool = False
    system_prompt: Optional[str] = None
    # Prompt 前缀缓存控制(Provider 支持时使用;具体格式由各 Provider 实现翻译)
    cache_control: Optional[dict] = None
    # 透传给 Provider 的额外参数(Provider 特有、不在标准字段内的功能)
    extra: dict = field(default_factory=dict)


@dataclass
class LLMUsage:
    """
    Token 用量。各 Provider 均需将计费 token 数映射到此结构。
    cached_input_tokens:命中 prompt cache 的 input tokens,
    计费方式因 Provider 而异【需复核各家最新计费规则】。
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_input_tokens: int = 0    # 命中 Provider 侧 prompt cache 的部分
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """
    统一响应结构。
    """
    content: str
    usage: LLMUsage
    model_id: str                   # 实际使用的模型(降级后可能与请求不同)
    finish_reason: str              # stop / max_tokens / tool_calls 等
    raw_response: Any = None        # 原始 Provider 响应,供调试
    request_id: str = ""            # Provider 返回的请求唯一 ID,用于账单核对


class LLMProvider(ABC):
    """
    所有 LLM Provider 必须实现此接口。
    实现类职责:
    1. 将 LLMRequest 翻译为 Provider 原生 API 调用
    2. 将原生响应翻译回 LLMResponse / token stream
    3. 将原生错误映射为本模块统一异常类型
    """

    provider_name: str  # 子类必须设置,如 "anthropic" / "openai"

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """非流式完成。返回完整 LLMResponse。"""
        ...

    @abstractmethod
    async def stream_complete(
        self, request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """
        流式完成。yield 每个增量文本片段(delta text)。
        调用方拼接;用量统计在 stream 结束时通过 get_stream_usage() 上报。
        """
        ...

    @abstractmethod
    async def get_stream_usage(self) -> LLMUsage:
        """
        流结束后返回本次流式调用的完整用量。
        若 Provider 不支持,返回 LLMUsage(0,0,0,0),由路由层本地估算兜底。
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Provider 可用性探测,用于故障切换判断。"""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """返回此 Provider 当前配置可用的 model_id 列表。"""
        ...
```

#### 3.1.3 AnthropicProvider 实现要点

```python
# llm/providers/anthropic_provider.py

import anthropic
from llm.provider_base import LLMProvider, LLMRequest, LLMResponse, LLMUsage


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude API 封装。
    支持:Messages API、流式输出、prompt caching (cache_control)。
    注意:具体模型 ID、context window、pricing 以 Anthropic 官方文档为准【需复核】。
    """

    provider_name = "anthropic"

    def __init__(self, api_key: str, default_timeout: int = 120):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._timeout = default_timeout
        self._last_stream_usage: LLMUsage | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        kwargs = self._build_kwargs(request)
        resp = await self._client.messages.create(**kwargs)
        usage = LLMUsage(
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            # cache_read_input_tokens 字段名以 Anthropic 官方 SDK 为准【需复核】
            cached_input_tokens=getattr(resp.usage, "cache_read_input_tokens", 0),
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        )
        return LLMResponse(
            content=resp.content[0].text,
            usage=usage,
            model_id=resp.model,
            finish_reason=resp.stop_reason or "stop",
            raw_response=resp,
            request_id=resp.id,
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        kwargs = self._build_kwargs(request)
        self._last_stream_usage = None
        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
            final_msg = await stream.get_final_message()
            self._last_stream_usage = LLMUsage(
                prompt_tokens=final_msg.usage.input_tokens,
                completion_tokens=final_msg.usage.output_tokens,
                cached_input_tokens=getattr(
                    final_msg.usage, "cache_read_input_tokens", 0
                ),
                total_tokens=(
                    final_msg.usage.input_tokens + final_msg.usage.output_tokens
                ),
            )

    async def get_stream_usage(self) -> LLMUsage:
        return self._last_stream_usage or LLMUsage()

    def _build_kwargs(self, request: LLMRequest) -> dict:
        kwargs: dict = {
            "model": request.model_id,
            "max_tokens": request.max_tokens,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        if request.system_prompt:
            kwargs["system"] = request.system_prompt
        if request.stop_sequences:
            kwargs["stop_sequences"] = request.stop_sequences
        # Prompt caching:cache_control 由 PromptCacheBuilder 注入到 messages 块中
        # 此处无需额外处理,Anthropic SDK 识别 content block 中的 cache_control 字段
        return kwargs

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model="claude-haiku-3-5-20241022",  # 用最轻量模型做探测【需复核 ID】
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        return list(self._model_registry.keys())
```

#### 3.1.4 OpenAIProvider 骨架(与 Anthropic 对称)

```python
# llm/providers/openai_provider.py

from openai import AsyncOpenAI
from llm.provider_base import LLMProvider, LLMRequest, LLMResponse, LLMUsage


class OpenAIProvider(LLMProvider):
    """
    OpenAI API 封装。
    注意:模型 ID、定价、速率限制以 OpenAI 官方文档为准【需复核】。
    prompt caching:OpenAI 对长 prompt 自动缓存,无需显式标记【需复核最新机制】。
    """

    provider_name = "openai"

    def __init__(self, api_key: str, default_timeout: int = 90):
        self._client = AsyncOpenAI(api_key=api_key)
        self._timeout = default_timeout
        self._last_stream_usage: LLMUsage | None = None

    def _map_usage(self, openai_usage) -> LLMUsage:
        # prompt_tokens_details.cached_tokens 字段名以 OpenAI SDK 为准【需复核】
        cached = getattr(
            getattr(openai_usage, "prompt_tokens_details", None),
            "cached_tokens",
            0,
        )
        return LLMUsage(
            prompt_tokens=openai_usage.prompt_tokens,
            completion_tokens=openai_usage.completion_tokens,
            cached_input_tokens=cached,
            total_tokens=openai_usage.total_tokens,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=request.model_id,
            messages=self._build_messages(request),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=request.stop_sequences or None,
        )
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            usage=self._map_usage(resp.usage),
            model_id=resp.model,
            finish_reason=choice.finish_reason or "stop",
            raw_response=resp,
            request_id=resp.id,
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        self._last_stream_usage = None
        stream = await self._client.chat.completions.create(
            model=request.model_id,
            messages=self._build_messages(request),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            if chunk.usage:
                self._last_stream_usage = self._map_usage(chunk.usage)

    async def get_stream_usage(self) -> LLMUsage:
        return self._last_stream_usage or LLMUsage()

    async def health_check(self) -> bool:
        try:
            await self._client.chat.completions.create(
                model="gpt-4o-mini",  # 探测用轻量模型【需复核 ID】
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        return list(self._model_registry.keys())

    def _build_messages(self, request: LLMRequest) -> list[dict]:
        msgs = []
        if request.system_prompt:
            msgs.append({"role": "system", "content": request.system_prompt})
        msgs.extend(request.messages)
        return msgs
```

#### 3.1.5 Provider 注册与工厂

```python
# llm/provider_registry.py

from dataclasses import dataclass
from llm.provider_base import LLMProvider

PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai":    OpenAIProvider,
    # "google":  GoogleProvider,   # 按需扩展
    # "local":   VLLMProvider,     # 自托管 fallback
}


@dataclass
class ProviderConfig:
    provider_name: str
    init_kwargs: dict       # 透传给 Provider.__init__ 的参数(api_key 等)


def build_provider(config: ProviderConfig) -> LLMProvider:
    """
    新增 Provider = 实现 LLMProvider + 在 PROVIDER_REGISTRY 注册。
    业务代码零改动。
    """
    cls = PROVIDER_REGISTRY[config.provider_name]
    return cls(**config.init_kwargs)
```

---

### 3.2 统一 `complete` 与 `stream_complete` 接口

#### 3.2.1 AgentRole 枚举与 CompletionOpts

```python
# llm/router.py

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, AsyncGenerator


class AgentRole(str, Enum):
    """
    Agent 角色枚举。与实现3(编排引擎)中的 Agent 命名对齐。
    路由层根据此枚举选择模型档位。
    """
    OUTLINE   = "OutlineAgent"    # 卷/章大纲生成(规划类)
    PLANNING  = "PlanningAgent"   # 事件细化与节拍排布(规划类)
    WRITING   = "WritingAgent"    # 正文生成(写作类 → 旗舰模型)
    OPTIONS   = "OptionsAgent"    # 多方案生成(写作类 → 旗舰模型)
    REVIEW    = "ReviewAgent"     # 审校与一致性检查(快模型)
    SUMMARY   = "SummaryAgent"    # MemoryEntry 摘要更新(快模型)
    EXTRACT   = "ExtractAgent"    # 实体/事件/伏笔/PreferenceSignal 抽取(快模型)
    FEEDBACK  = "FeedbackAgent"   # 解析 FeedbackNote 为结构化指令(快模型)


@dataclass
class CompletionOpts:
    """
    调用方可选的覆盖参数。不填则使用路由策略默认值。
    """
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False
    # 强制模型/Provider(仅调试/人工干预使用,生产禁止)
    force_model: Optional[str] = None
    force_provider: Optional[str] = None
    # 业务上下文(用于成本计量)
    work_id: Optional[str] = None
    chapter_id: Optional[str] = None
    # 结果缓存控制
    skip_cache: bool = False
    # 停止词
    stop_sequences: list[str] = field(default_factory=list)
    # 请求超时覆盖(秒)
    timeout_seconds: Optional[int] = None


@dataclass
class CompletionResult:
    """complete() / stream_complete() 后的统一返回值。"""
    content: str
    usage: LLMUsage
    model_id: str
    provider_name: str
    cached: bool = False        # True = 命中应用侧结果缓存(未实际调用 API)
    request_id: str = ""
    latency_ms: float = 0.0
```

#### 3.2.2 LLMRouter 接口签名

```python
class LLMRouter:
    """
    LLM 接入层核心类。
    调用方(编排引擎 / 各 Agent)通过依赖注入获取单例。
    对外只暴露 complete / stream_complete 两个入口。
    """

    async def complete(
        self,
        agent_role: AgentRole,
        prompt: str | list[dict],
        opts: CompletionOpts = CompletionOpts(),
    ) -> CompletionResult:
        """
        统一非流式完成接口。

        执行顺序:
        1. 查应用侧结果缓存(skip_cache=False 且 temperature≈0 时)
        2. 路由决策(_resolve_route):按 AgentRole + 预算状态选择 Provider + 模型
        3. 预算预检(估算本次 token 消耗,触发降级或拒绝)
        4. 速率限制令牌桶申请
        5. 调用 Provider.complete(),含重试逻辑
        6. 写入 TokenLedger(计量)
        7. 写入应用侧结果缓存
        8. 返回 CompletionResult

        异常:
        - BudgetExceededError       — 超出预算且无降级选项
        - ProviderUnavailableError  — 所有 Provider 均不可用
        - RateLimitTimeoutError     — 速率限制等待超时
        """
        ...

    async def stream_complete(
        self,
        agent_role: AgentRole,
        prompt: str | list[dict],
        opts: CompletionOpts = CompletionOpts(),
    ) -> AsyncGenerator[str, None]:
        """
        流式完成接口。yield 增量文本片段。

        用法示例:
            async for chunk in router.stream_complete(AgentRole.WRITING, msgs, opts):
                await sse_send(chunk)

        内部行为与 complete() 相同,区别在于:
        - 调用 Provider.stream_complete() 而非 complete()
        - 成本计量在流结束后统一上报(通过 provider.get_stream_usage())
        - 若 Provider 不支持流式用量上报,用本地 tokenizer 估算兜底
        """
        ...
```

#### 3.2.3 调用示例(编排引擎视角)

```python
# 在 WritingAgent 中:非流式
result = await router.complete(
    agent_role=AgentRole.WRITING,
    prompt=assembled_messages,      # 由 assembleContext(实现4) 拼装完成
    opts=CompletionOpts(
        work_id=work.id,
        chapter_id=chapter.id,
        max_tokens=2000,
        temperature=0.85,
        skip_cache=True,            # 写作生成需要新鲜输出
    ),
)
draft_text = result.content

# 流式写作(前端实时显示)
async for chunk in router.stream_complete(
    agent_role=AgentRole.WRITING,
    prompt=assembled_messages,
    opts=CompletionOpts(
        work_id=work.id,
        chapter_id=chapter.id,
        stream=True,
        skip_cache=True,
    ),
):
    await sse_bus.publish(f"work:{work.id}", {"type": "text_chunk", "data": chunk})

# 在 ExtractAgent 中:可缓存的结构化任务
result = await router.complete(
    agent_role=AgentRole.EXTRACT,
    prompt=extract_messages,
    opts=CompletionOpts(
        work_id=work.id,
        chapter_id=chapter.id,
        temperature=0.1,            # 接近确定性,提升结果缓存命中率
        max_tokens=800,
    ),
)
```

---

### 3.3 Agent 角色路由表与降级链

#### 3.3.1 模型档位定义

```python
# llm/model_tiers.py

from enum import Enum

class ModelTier(str, Enum):
    """
    模型档位,与具体型号解耦。型号在 Provider 配置文件中绑定。
    """
    FLAGSHIP = "flagship"   # 最强写作能力,成本最高
    FAST     = "fast"       # 快速、低成本,适合结构化 / 摘要 / 抽取任务
    ULTRA    = "ultra"      # 超强推理,可选 — 用于深度分析型审校(按需启用)
    FALLBACK = "fallback"   # 降级备用;可为本地自托管轻量模型
```

#### 3.3.2 角色 → 档位 → 降级链 路由表

| Agent 角色 | 任务特征 | 主路由档位 | 降级档位 1 | 降级档位 2 | 备注 |
|---|---|---|---|---|---|
| `WritingAgent` | 正文生成,质量决定性 | `flagship` | `fast` | `fallback` | 降级须告警用户 |
| `OptionsAgent` | 多方案生成(给人选) | `flagship` | `fast` | `fallback` | 同写作,质量敏感 |
| `OutlineAgent` | 卷/章大纲,结构化输出 | `fast` | `fallback` | — | 结构清晰,快模型胜任 |
| `PlanningAgent` | 事件细化与节拍排布 | `fast` | `fallback` | — | 高频调用,成本敏感 |
| `ReviewAgent` | 审校 + 一致性标记 | `fast` | `fallback` | — | 深度审校可升 `ultra` |
| `SummaryAgent` | MemoryEntry 摘要更新 | `fast` | `fallback` | — | 高频、结构清晰 |
| `ExtractAgent` | 实体/事件/伏笔/偏好抽取 | `fast` | `fallback` | — | JSON 输出,快模型足够 |
| `FeedbackAgent` | 解析 FeedbackNote | `fast` | `fallback` | — | 结构化解析任务 |

**降级触发条件汇总**:

| 触发场景 | 降级行为 |
|---|---|
| 主路由 Provider 返回 5xx / 网络超时 | 切换到同档位备选 Provider(故障切换) |
| 主路由 Provider 429 速率限制 | 等待令牌桶恢复,或降到下一档位 |
| 当前 Chapter 预算超限 | `WritingAgent` 降 `fast`;其他降 `fallback` |
| 当前 Work 预算达到硬限比例 | 所有 Agent 降 `fallback`,并向用户告警 |
| 人工强制降级(管理员操作) | 覆盖路由,记录覆盖原因到 `system_alerts` |

#### 3.3.3 路由策略 YAML 配置

```yaml
# config/llm_routing.yaml
# 注意:以下模型 ID 均为示例占位,实际型号以各 Provider 官方文档为准【需复核】

providers:
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      flagship: "claude-opus-4-8-20261001"      # 示例占位【需复核】
      fast:     "claude-sonnet-4-6-20261001"     # 示例占位【需复核】
      fallback: "claude-haiku-3-5-20241022"      # 示例占位【需复核】
    rate_limits:
      flagship_tpm: 400000    # 【需复核 Anthropic 实际限额】
      fast_tpm:    2000000    # 【需复核】
    health_check_interval_s: 30
    priority: 1               # 主 Provider

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      flagship: "gpt-4o-2026-latest"             # 示例占位【需复核】
      fast:     "gpt-4o-mini-2026-latest"        # 示例占位【需复核】
      fallback: "gpt-4o-mini-2026-latest"
    rate_limits:
      flagship_tpm: 300000    # 【需复核 OpenAI 实际限额】
      fast_tpm:    2000000    # 【需复核】
    health_check_interval_s: 30
    priority: 2               # 备选 Provider(故障切换)

routing_rules:
  WritingAgent:
    primary_tier: flagship
    fallback_chain: [fast, fallback]
    primary_provider: anthropic
    fallback_providers: [openai]

  OptionsAgent:
    primary_tier: flagship
    fallback_chain: [fast, fallback]
    primary_provider: anthropic
    fallback_providers: [openai]

  OutlineAgent:
    primary_tier: fast
    fallback_chain: [fallback]
    primary_provider: anthropic
    fallback_providers: [openai]

  PlanningAgent:
    primary_tier: fast
    fallback_chain: [fallback]
    primary_provider: anthropic
    fallback_providers: [openai]

  ReviewAgent:
    primary_tier: fast
    fallback_chain: [fallback]
    primary_provider: anthropic
    fallback_providers: [openai]
    deep_review_tier: ultra   # 深度审校时可配置升级

  SummaryAgent:
    primary_tier: fast
    fallback_chain: [fallback]
    primary_provider: anthropic
    fallback_providers: [openai]

  ExtractAgent:
    primary_tier: fast
    fallback_chain: [fallback]
    primary_provider: anthropic
    fallback_providers: [openai]

  FeedbackAgent:
    primary_tier: fast
    fallback_chain: [fallback]
    primary_provider: anthropic
    fallback_providers: [openai]
```

#### 3.3.4 路由决策伪代码

```python
def _resolve_route(
    self,
    agent_role: AgentRole,
    opts: CompletionOpts,
    forced_tier: ModelTier | None = None,
) -> tuple[LLMProvider, ModelConfig]:
    """
    路由决策核心逻辑。
    返回 (provider 实例, 模型配置) 元组。
    """
    # 0. 调试用强制覆盖(生产禁止)
    if opts.force_model or opts.force_provider:
        return self._resolve_forced(opts)

    # 1. 查路由规则表
    rule = self._routing_rules[agent_role]

    # 2. 确定有效档位(可能被预算管理器强制降级)
    effective_tier = forced_tier or rule.primary_tier

    # 3. 按降级链 × Provider 优先级遍历,找第一个可用的组合
    tier_chain     = [effective_tier] + rule.fallback_chain
    provider_chain = [rule.primary_provider] + rule.fallback_providers

    for tier in tier_chain:
        for provider_name in provider_chain:
            provider     = self._providers[provider_name]
            model_config = self._model_configs[provider_name][tier]

            if not self._health_tracker.is_healthy(provider_name):
                continue
            if self._rate_limiter.can_proceed(provider_name, tier):
                return provider, model_config

    raise ProviderUnavailableError(
        f"所有 Provider 均不可用或超速率限制: role={agent_role}"
    )
```

---

### 3.4 选型原则与禁止事项

#### 3.4.1 正确的选型姿势

1. **在自有语料上实测**:根据设计哲学 §2 的能力矩阵,在自建的验证语料集上,用工程6(质量度量)对候选模型跑实测指标,以实测数据决定档位配置。工程6 是选型的唯一合法依据。
2. **分角色评估**:写作角色评"叙事连贯性与风格控制";规划角色评"结构遵从度与 JSON 格式正确率";审校角色评"一致性错误检出精确率与召回率"(00 §5 枚举的 19 类)。
3. **成本权衡**:若某快模型在规划任务上的错误率使写作 Agent 多返工一轮,节省的成本得不偿失,应升档。
4. **定期重评**:每季度或主要新模型发布时重跑工程6 评估,必要时调整路由配置文件。

#### 3.4.2 严格禁止的选型行为

> 以下行为在本文档及整个 Scribe 设计体系中**明令禁止**,代码审查应指出并拒绝。

- **禁止**引用"某模型一致性错误密度最低"类外部排行榜数据作为路由策略配置依据。设计哲学经对抗式验证已证伪此类数据的可靠性——其具体数值属未经证实的声称,**不可信**。
- **禁止**在未做自有语料实测的情况下,凭外部 benchmark 排名直接将某模型提升为 `flagship`。
- **禁止**将"模型参数量最大 = 最适合写作"作为路由依据——中文叙事、网文节奏等任务上的实际表现差异无法仅凭参数量推断。
- **禁止**在文档或代码注释中编造任何具体模型价格——价格标【需复核】并给出"如何算"的方法。

---

### 3.5 两层缓存机制

缓存分两层,目标和机制不同,相互不替代。

#### 3.5.1 层一:Prompt 前缀缓存(Provider 侧,降低 input token 计费)

**目标**:将每章生成中相对稳定的"设定上下文"标记为可缓存块,利用 Provider 的 prompt caching 功能,在同一作品的多次章节调用间复用,降低 input token 计费。

**稳定 vs 不稳定内容划分**:

```
[可缓存的稳定前缀]
  ├── 全局写作规范(系统级固定,所有 Agent 共享)
  ├── Story Bible 中的角色基础档案(同作品内多章可复用)
  └── 世界规则条目(整部作品通用)

[不可缓存的动态内容]
  ├── 当前章节大纲(每章不同)
  ├── 最近 N 章摘要(每章更新)
  └── 本次调用的个性化指令(每次可能不同)
```

**PromptCacheBuilder 实现**:

```python
# llm/prompt_cache.py

class PromptCacheBuilder:
    """
    在构造 LLMRequest 前,为稳定前缀 message block 添加 Provider 对应的缓存标记。
    各 Provider 的缓存标记格式不同,由各 Provider 实现负责翻译:
    - Anthropic:在 content block 中添加 {"cache_control": {"type": "ephemeral"}}
    - OpenAI:长前缀自动缓存,无需显式标记(以官方最新文档为准【需复核】)
    """

    def mark_cacheable_prefix(
        self,
        messages: list[dict],
        provider_name: str,
        stable_token_threshold: int = 1024,
    ) -> list[dict]:
        """
        为前缀 messages 中满足条件的稳定块添加缓存标记。

        规则:
        - 仅对 token 数超过 stable_token_threshold 的 block 标记
          (过小的 block 缓存收益不大,Provider 也可能有最小 block 要求【需复核】)
        - 稳定 block 的判断:调用方在组装 messages 时通过
          block 的 metadata 字段 stable=True 显式标注
        - 标记位置:稳定块的末尾 content block 添加 cache_control

        注意:过于频繁更新 Story Bible 会导致缓存失效,
        详见 §6.3 失败模式。
        """
        if provider_name == "anthropic":
            return self._mark_anthropic(messages, stable_token_threshold)
        # OpenAI 自动处理,不需要显式标记
        return messages

    def _mark_anthropic(
        self, messages: list[dict], threshold: int
    ) -> list[dict]:
        """
        Anthropic cache_control 注入。
        在 stable=True 的 message block 的最后一个 content item 添加:
        {"cache_control": {"type": "ephemeral"}}
        具体 API 格式以 Anthropic 官方文档为准【需复核】。
        """
        result = []
        for msg in messages:
            if msg.get("_stable") and self._estimate_tokens(msg) >= threshold:
                msg = self._inject_cache_control(msg)
            result.append(msg)
        return result
```

**百万字价值估算方法(方法论,不含单价)**:

```
设:
  每章 WritingAgent 调用中,稳定前缀占 input tokens 的比例 = P_stable
  333 章的缓存命中率 = C_hit

可缓存 input tokens ≈ 每章平均 input × P_stable × 333 章 × C_hit
节省费用 = 可缓存 tokens × (正常 input 单价 - cache 命中单价)
         【单价以各 Provider 官方定价页为准,此处不编造具体数字】

建议:在前 50 章实跑后,从 token_records 表统计:
  cached_prompt_tokens / (prompt_tokens + cached_prompt_tokens) = 实际命中率
用实际命中率代入上式,得到可信的 cache 节省估算。
```

#### 3.5.2 层二:结果缓存(应用侧,相同请求复用完整响应)

**目标**:对语义完全相同的请求(相同 prompt hash + 相同模型配置),直接返回缓存的 completion,跳过 API 调用。

**适用场景**:
- `ExtractAgent` / `SummaryAgent` 对同一段未改动正文重复调用(如流程重跑)
- `ReviewAgent` 对未改动章节的重复审校
- 调试阶段反复运行同一章流程

**不适用场景**:
- `WritingAgent` / `OptionsAgent` 正文/多方案生成——需要新鲜创意输出,默认 `skip_cache=True`
- temperature > 0 的开放性生成——相同 prompt 也期望不同输出时不缓存

```python
# llm/result_cache.py

import hashlib
import json

class ResultCache:
    """
    应用侧结果缓存。
    后端:MVP 用本地 LRU dict;增强版/完整版用 Redis(TTL 可配)。
    """

    def _make_cache_key(
        self,
        agent_role: AgentRole,
        messages: list[dict],
        model_id: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """
        缓存键 = SHA256(agent_role + messages + model_id + max_tokens + temperature)
        temperature 精度截断到 0.01,避免浮点差异导致 key 不匹配。
        """
        payload = json.dumps(
            {
                "role": agent_role,
                "messages": messages,
                "model": model_id,
                "max_tokens": max_tokens,
                "temperature": round(temperature, 2),
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    async def get(self, key: str) -> CompletionResult | None:
        """命中返回 CompletionResult(cached=True),未命中返回 None。"""
        ...

    async def set(
        self, key: str, result: CompletionResult, ttl_seconds: int = 86400
    ) -> None:
        """写入缓存。TTL 默认 24h,ExtractAgent 可配更长(内容稳定)。"""
        ...

    async def invalidate_by_chapter(self, chapter_id: str) -> None:
        """章节正文更新后,使该章节所有相关缓存失效。"""
        ...

    async def invalidate_by_work(self, work_id: str) -> None:
        """作品设定重大更新时,批量失效。"""
        ...
```

**缓存命中时的 usage 处理**:
- `CompletionResult.cached = True`
- `usage.prompt_tokens = 0, completion_tokens = 0`(未调用 API,真实消耗为 0)
- `TokenLedger` 记录此调用为 `result_cached=True`,不计入货币成本,计入"缓存节省统计"

---

### 3.6 成本计量系统

#### 3.6.1 TokenLedger 设计

```python
# llm/token_ledger.py

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid


@dataclass
class TokenRecord:
    """
    每次 LLM 调用的 token 记录。持久化到 DB。
    不含单价——成本报告层在查询时叠加当时的价格参数。
    """
    id: str                       # UUID v7
    work_id: str | None           # 关联 Work.id(00 §4 规范实体)
    chapter_id: str | None        # 关联 Chapter.id
    agent_role: str               # AgentRole 枚举值
    provider_name: str
    model_id: str                 # 实际使用的模型 ID(降级后可能与请求不同)
    prompt_tokens: int            # 实际计费 input tokens(未命中 prompt cache 部分)
    completion_tokens: int
    cached_prompt_tokens: int     # 命中 Provider prompt cache 的 input tokens
    result_cached: bool           # 是否命中应用侧结果缓存
    latency_ms: float
    created_at: datetime
    request_id: str               # Provider 返回的请求 ID,用于账单核对
    downgraded_from: str | None   # 若发生降级,记录原始档位(供分析)


class TokenLedger:
    """
    Token 消耗账本。
    - 写入:每次 LLM 调用完成后由 LLMRouter 调用
    - 读取:成本报告 API / 预算管理器实时计数器
    - 设计约束:写入路径必须低延迟(异步写 DB + 同步更新 Redis 计数器)
    """

    async def record(
        self,
        work_id: str | None,
        chapter_id: str | None,
        agent_role: str,
        provider_name: str,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        cached_prompt_tokens: int = 0,
        result_cached: bool = False,
        latency_ms: float = 0.0,
        request_id: str = "",
        downgraded_from: str | None = None,
    ) -> None:
        record = TokenRecord(
            id=str(uuid.uuid7()),
            work_id=work_id,
            chapter_id=chapter_id,
            agent_role=agent_role,
            provider_name=provider_name,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_prompt_tokens=cached_prompt_tokens,
            result_cached=result_cached,
            latency_ms=latency_ms,
            created_at=datetime.now(timezone.utc),
            request_id=request_id,
            downgraded_from=downgraded_from,
        )
        # 异步写 DB(不阻塞生成主流程)
        await self._db.insert_async("token_records", asdict(record))
        # 同步更新 Redis 实时计数器(预算检查使用)
        await self._budget_manager.on_tokens_used(
            work_id=work_id,
            chapter_id=chapter_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    async def get_work_summary(self, work_id: str) -> dict:
        """
        作品维度 token 消耗聚合。
        返回结构:
        {
            "total_prompt_tokens":      int,
            "total_completion_tokens":  int,
            "total_cached_prompt_tokens": int,
            "by_agent_role": {
                "WritingAgent": {"prompt": ..., "completion": ...},
                ...
            },
            "by_chapter": [
                {"chapter_id": ..., "prompt": ..., "completion": ..., "latency_p50_ms": ...},
                ...
            ],
            "result_cache_hit_count":   int,
            "result_cache_saved_tokens": int,
        }
        使用此数据 × 当前单价 = 货币成本(单价不存储在此表中)
        """
        ...

    async def get_chapter_summary(self, chapter_id: str) -> dict:
        """章节维度聚合,供预算检查和成本看板使用。"""
        ...

    async def get_cost_trend(
        self, work_id: str, window_chapters: int = 50
    ) -> dict:
        """
        最近 window_chapters 章的成本趋势。
        用于自动成本外推(见 §3.10.4 分级校验)。
        """
        ...
```

#### 3.6.2 token_records 表 DDL

```sql
-- 成本计量持久化表
-- 不含单价字段;单价在报告查询层叠加,避免价格变更导致历史数据失真
CREATE TABLE token_records (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id               UUID REFERENCES work(id) ON DELETE SET NULL,
    chapter_id            UUID REFERENCES chapter(id) ON DELETE SET NULL,
    agent_role            VARCHAR(50) NOT NULL,
    provider_name         VARCHAR(50) NOT NULL,
    model_id              VARCHAR(100) NOT NULL,
    prompt_tokens         INTEGER NOT NULL DEFAULT 0,
    completion_tokens     INTEGER NOT NULL DEFAULT 0,
    cached_prompt_tokens  INTEGER NOT NULL DEFAULT 0,
    result_cached         BOOLEAN NOT NULL DEFAULT FALSE,
    latency_ms            REAL,
    request_id            VARCHAR(200),
    downgraded_from       VARCHAR(50),    -- 若降级,记录原始档位
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 按作品聚合
CREATE INDEX idx_token_records_work_id     ON token_records(work_id);
-- 按章节聚合
CREATE INDEX idx_token_records_chapter_id  ON token_records(chapter_id);
-- 时间序列 / 趋势查询
CREATE INDEX idx_token_records_created_at  ON token_records(created_at DESC);
-- 复合索引:作品 + 时间(成本趋势报告)
CREATE INDEX idx_token_records_work_time   ON token_records(work_id, created_at DESC);

-- 系统告警表
CREATE TABLE system_alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id     UUID REFERENCES work(id) ON DELETE SET NULL,
    alert_type  VARCHAR(50) NOT NULL,   -- budget_warning / model_downgrade / cache_miss_spike
    message     TEXT NOT NULL,
    metadata    JSONB,
    resolved    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_system_alerts_work_id    ON system_alerts(work_id);
CREATE INDEX idx_system_alerts_created_at ON system_alerts(created_at DESC);
```

#### 3.6.3 complete() 端到端计量伪代码

```python
# llm/router.py — complete() 方法核心逻辑展开
import time
from dataclasses import replace

async def complete(
    self, agent_role: AgentRole, prompt: str | list[dict], opts: CompletionOpts
) -> CompletionResult:

    messages = self._normalize_prompt(prompt)

    # ── Step 1: 应用侧结果缓存检查 ──────────────────────────────────
    should_cache = (
        not opts.skip_cache
        and (opts.temperature or self._default_temperature(agent_role)) <= 0.15
    )
    cache_key = None
    if should_cache:
        cache_key = self._result_cache._make_cache_key(
            agent_role, messages,
            model_id="*",       # 先不绑定模型,命中即返回
            max_tokens=opts.max_tokens or 4096,
            temperature=opts.temperature or 0.1,
        )
        cached_result = await self._result_cache.get(cache_key)
        if cached_result:
            await self._ledger.record(
                work_id=opts.work_id, chapter_id=opts.chapter_id,
                agent_role=agent_role.value, provider_name="cache",
                model_id="cache", prompt_tokens=0, completion_tokens=0,
                result_cached=True, latency_ms=0,
            )
            return cached_result

    # ── Step 2: 路由决策 ─────────────────────────────────────────────
    provider, model_config = self._resolve_route(agent_role, opts)

    # ── Step 3: 预算预检 ─────────────────────────────────────────────
    estimated_tokens = self._tokenizer.estimate(messages, model_config.model_id)
    allowed, forced_tier = await self._budget_manager.check_and_maybe_downgrade(
        work_id=opts.work_id,
        chapter_id=opts.chapter_id,
        estimated_tokens=estimated_tokens,
        current_tier=model_config.tier,
    )
    if not allowed:
        raise BudgetExceededError(
            f"work={opts.work_id} chapter={opts.chapter_id} 已超预算且无降级可用"
        )
    downgraded_from = None
    if forced_tier:
        downgraded_from = model_config.tier.value
        provider, model_config = self._resolve_route(
            agent_role, opts, forced_tier=forced_tier
        )
        await self._alert_manager.send_downgrade_alert(
            work_id=opts.work_id,
            original_tier=downgraded_from,
            downgrade_tier=forced_tier.value,
            reason="budget_exceeded",
        )

    # ── Step 4: 速率限制令牌桶申请 ───────────────────────────────────
    acquired = await self._rate_limiter.acquire(
        provider_name=provider.provider_name,
        tier=model_config.tier.value,
        estimated_tokens=estimated_tokens,
        timeout_seconds=opts.timeout_seconds or 30.0,
    )
    if not acquired:
        raise RateLimitTimeoutError(
            f"速率限制等待超时: provider={provider.provider_name} tier={model_config.tier}"
        )

    # ── Step 5: 构造请求 + Prompt 前缀缓存标记 ──────────────────────
    request = LLMRequest(
        messages=self._prompt_cache_builder.mark_cacheable_prefix(
            messages, provider.provider_name
        ),
        model_id=model_config.model_id,
        max_tokens=opts.max_tokens or model_config.default_max_tokens,
        temperature=opts.temperature or model_config.default_temperature,
        stop_sequences=opts.stop_sequences,
        system_prompt=self._extract_system(messages),
    )

    # ── Step 6: 调用 Provider(含重试) ──────────────────────────────
    start = time.monotonic()
    try:
        response = await self._call_with_retry(provider, request)
    except ProviderUnavailableError:
        # 当前 Provider 不可用,尝试降级链中的下一个
        self._health_tracker.record_failure(provider.provider_name)
        provider_fallback, model_config_fallback = self._resolve_route(
            agent_role, opts, skip_provider=provider.provider_name
        )
        response = await self._call_with_retry(provider_fallback, request_with(
            request, model_id=model_config_fallback.model_id
        ))
        provider = provider_fallback
        model_config = model_config_fallback
    latency_ms = (time.monotonic() - start) * 1000

    # ── Step 7: 计量记录 ─────────────────────────────────────────────
    await self._ledger.record(
        work_id=opts.work_id,
        chapter_id=opts.chapter_id,
        agent_role=agent_role.value,
        provider_name=provider.provider_name,
        model_id=response.model_id,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        cached_prompt_tokens=response.usage.cached_input_tokens,
        result_cached=False,
        latency_ms=latency_ms,
        request_id=response.request_id,
        downgraded_from=downgraded_from,
    )

    # ── Step 8: 写入应用侧结果缓存 ───────────────────────────────────
    result = CompletionResult(
        content=response.content,
        usage=response.usage,
        model_id=response.model_id,
        provider_name=provider.provider_name,
        cached=False,
        request_id=response.request_id,
        latency_ms=latency_ms,
    )
    if should_cache and cache_key:
        await self._result_cache.set(cache_key, result)

    return result
```

---

### 3.7 预算管理与告警

#### 3.7.1 预算层级与配置

```python
# llm/budget_manager.py

from dataclasses import dataclass

@dataclass
class BudgetConfig:
    """
    预算配置。Work 创建时由用户设定,或使用系统默认值。
    token_limit 的合理绝对值需在实际运行中标定后设定【需复核】;
    本设计只定义结构和语义。
    """
    # 系统级(防意外超量)
    system_daily_token_limit: int       # 每日全局 token 上限【按运营成本设定】

    # 作品级
    work_token_budget: int              # 单部作品整体 token 预算【需实测标定】
    work_warn_threshold_pct: float = 0.80    # 达到 80% 发出警告
    work_hard_limit_pct:     float = 0.95    # 达到 95% 触发强制降级

    # 章节级(细粒度防单章失控)
    chapter_token_budget: int           # 单章 token 预算(含所有 Agent 调用)【需实测标定】
    chapter_warn_threshold_pct: float = 0.90
```

#### 3.7.2 预算状态机

```
Normal ──[达 warn_pct]──→ Warning ──[达 hard_pct]──→ Degraded
                                                        │
                                         [无降级可用]   │
                                                        ▼
                                                    Blocked
         (Degraded / Blocked 在预算重置或手动解除后恢复 Normal)
```

```python
class BudgetManager:

    async def check_and_maybe_downgrade(
        self,
        work_id: str | None,
        chapter_id: str | None,
        estimated_tokens: int,
        current_tier: ModelTier,
    ) -> tuple[bool, ModelTier | None]:
        """
        返回 (is_allowed, forced_downgrade_tier):
        - (True,  None)         : 正常,无需降级
        - (True,  ModelTier.X)  : 允许但强制降级到 X
        - (False, None)         : 完全阻断,拒绝调用
        """
        budget_cfg = await self._get_budget_config(work_id)

        # 章节级检查
        if chapter_id:
            chapter_usage = await self._get_chapter_usage(chapter_id)
            projected = chapter_usage + estimated_tokens
            if projected > budget_cfg.chapter_token_budget:
                if current_tier == ModelTier.FLAGSHIP:
                    return True, ModelTier.FAST
                elif current_tier == ModelTier.FAST:
                    return True, ModelTier.FALLBACK
                else:
                    return False, None   # fallback 也超限,拒绝

        # 作品级检查
        if work_id:
            work_usage = await self._get_work_usage(work_id)
            work_ratio = work_usage / budget_cfg.work_token_budget
            if work_ratio >= budget_cfg.work_hard_limit_pct:
                if current_tier != ModelTier.FALLBACK:
                    return True, ModelTier.FALLBACK
            elif work_ratio >= budget_cfg.work_warn_threshold_pct:
                await self._alert_manager.send_budget_warning(work_id, work_ratio)

        return True, None

    async def on_tokens_used(
        self,
        work_id: str | None,
        chapter_id: str | None,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """每次调用完成后,更新 Redis 实时计数器(用于下次预算检查)。"""
        total = prompt_tokens + completion_tokens
        if work_id:
            await self._redis.incrby(f"budget:work:{work_id}:tokens", total)
        if chapter_id:
            await self._redis.incrby(f"budget:chapter:{chapter_id}:tokens", total)
```

#### 3.7.3 告警机制

```python
class AlertManager:
    """
    告警通道:
    - MVP:写入 system_alerts 表 + SSE 推送到前端
    - 完整版:可扩展 Email / Webhook / Slack
    """

    async def send_budget_warning(self, work_id: str, usage_ratio: float) -> None:
        msg = f"作品 {work_id} token 用量已达 {usage_ratio:.0%},请注意成本控制"
        await self._persist_alert(work_id, "budget_warning", msg)
        await self._sse_bus.publish(
            f"work:{work_id}",
            {"type": "budget_warning", "ratio": usage_ratio, "msg": msg}
        )

    async def send_downgrade_alert(
        self,
        work_id: str | None,
        original_tier: str,
        downgrade_tier: str,
        reason: str,
    ) -> None:
        msg = (
            f"作品 {work_id}:因 {reason},模型已从 {original_tier} "
            f"降级至 {downgrade_tier}。正文质量可能受影响,建议检查预算设置。"
        )
        await self._persist_alert(work_id, "model_downgrade", msg, metadata={
            "original_tier": original_tier,
            "downgrade_tier": downgrade_tier,
            "reason": reason,
        })
        await self._sse_bus.publish(
            f"work:{work_id}",
            {"type": "model_downgrade", "original": original_tier,
             "current": downgrade_tier, "msg": msg}
        )

    async def send_cache_miss_spike_alert(
        self, work_id: str, miss_rate: float
    ) -> None:
        """Prompt cache 命中率跌破阈值时告警(见 §6.3)。"""
        msg = (
            f"作品 {work_id}:prompt cache 命中率仅 {miss_rate:.0%},低于预期。"
            f"请检查 Story Bible 更新频率。"
        )
        await self._persist_alert(work_id, "cache_miss_spike", msg)

    async def _persist_alert(
        self,
        work_id: str | None,
        alert_type: str,
        message: str,
        metadata: dict | None = None,
    ) -> None:
        await self._db.insert("system_alerts", {
            "work_id": work_id,
            "alert_type": alert_type,
            "message": message,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc),
        })
```

---

### 3.8 可靠性机制

#### 3.8.1 重试策略

```python
# llm/retry.py
# 使用 tenacity 库实现带抖动的指数退避重试

from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type, before_sleep_log
)
import logging

logger = logging.getLogger("llm.retry")

# 5xx / 网络超时:指数退避 + 抖动,最多 3 次
TRANSIENT_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
    retry=retry_if_exception_type((ProviderTemporaryError, NetworkTimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

# 速率限制:等令牌桶恢复,不做指数退避,最多 5 次等待
RATE_LIMIT_RETRY = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=5, max=60),
    retry=retry_if_exception_type(ProviderRateLimitError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

# 不可重试的错误(直接抛出):
#   AuthenticationError — API Key 无效
#   InvalidRequestError — prompt 格式错误
#   ContentPolicyError  — 内容过滤拦截
```

#### 3.8.2 超时配置

```python
# llm/timeout_config.py

TIMEOUT_CONFIG: dict[str, dict] = {
    # 非流式调用最大等待时间(秒)
    "non_stream": {
        ModelTier.FLAGSHIP: 120,   # 旗舰模型首 token 延迟较高,给足余量
        ModelTier.FAST:      45,
        ModelTier.ULTRA:    180,   # 深度推理可能更慢
        ModelTier.FALLBACK:  30,
    },
    # 流式调用:首 token 超时
    "stream_first_token": {
        ModelTier.FLAGSHIP: 30,
        ModelTier.FAST:     15,
        ModelTier.ULTRA:    45,
        ModelTier.FALLBACK: 10,
    },
    # 流式调用:相邻 chunk 间最大间隔(检测流中断)
    "stream_chunk_interval_s": 20,
}
```

#### 3.8.3 速率限制令牌桶

```python
# llm/rate_limiter.py

import asyncio
import time

class TokenBucket:
    """单个令牌桶:容量 = TPM,补充速率 = TPM/60(每秒)。"""

    def __init__(self, capacity: int, refill_rate_per_sec: float):
        self._capacity   = capacity
        self._refill_rate = refill_rate_per_sec
        self._tokens     = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                wait_needed = (tokens - self._tokens) / self._refill_rate
                if time.monotonic() + wait_needed > deadline:
                    return False
                await asyncio.sleep(min(wait_needed, deadline - time.monotonic()))

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._refill_rate
        )
        self._last_refill = now


class TokenBucketRateLimiter:
    """
    为每个 (provider_name, tier) 组合维护一个令牌桶。
    tpm_config 示例: {("anthropic", "flagship"): 400000, ...}
    TPM 数值以各 Provider 官方文档为准【需复核实际限额】。
    """

    def __init__(self, tpm_config: dict[tuple[str, str], int]):
        self._buckets = {
            key: TokenBucket(capacity=tpm, refill_rate_per_sec=tpm / 60.0)
            for key, tpm in tpm_config.items()
        }

    async def acquire(
        self,
        provider_name: str,
        tier: str,
        estimated_tokens: int,
        timeout_seconds: float = 30.0,
    ) -> bool:
        """
        申请令牌。True = 成功;False = 超时未获得。
        若该 (provider, tier) 无配置限额,直接放行(返回 True)。
        """
        bucket = self._buckets.get((provider_name, tier))
        if bucket is None:
            return True
        return await bucket.acquire(estimated_tokens, timeout=timeout_seconds)

    def can_proceed(self, provider_name: str, tier: str) -> bool:
        """非阻塞检查:当前是否有足够令牌(用于路由决策快速判断)。"""
        bucket = self._buckets.get((provider_name, tier))
        if bucket is None:
            return True
        return bucket._tokens >= 1  # 简化检查
```

#### 3.8.4 故障切换流程

```
Provider A 调用失败(5xx / 超时 N 次后仍失败)
        │
        ▼
HealthTracker.record_failure("A")
若连续失败次数 ≥ failure_threshold → 短路(unhealthy, circuit_break_duration=30s)
        │
        ▼
_resolve_route() 跳过 unhealthy Provider
        │
        ├── 同档位 Provider B 可用 → 返回结果,token_records.provider_name="B"
        │
        └── 同档位 B 也不可用 → 尝试降档位 Provider A / B
                    │
                    ├── 降档成功 → 告警(model_downgrade) + 返回结果
                    └── 全失败  → 抛出 ProviderUnavailableError


class HealthTracker:
    """
    短路熔断器。
    - 连续 failure_threshold 次失败 → unhealthy,短路 circuit_break_duration 秒
    - 后台每 30s 发一次 health_check(),成功则恢复 healthy
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        circuit_break_duration_s: float = 30.0,
    ):
        self._failure_counts:  dict[str, int]   = {}
        self._unhealthy_until: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def record_failure(self, provider_name: str) -> None:
        async with self._lock:
            self._failure_counts[provider_name] = (
                self._failure_counts.get(provider_name, 0) + 1
            )
            if self._failure_counts[provider_name] >= self._failure_threshold:
                self._unhealthy_until[provider_name] = (
                    time.monotonic() + self._circuit_break_duration_s
                )

    async def record_success(self, provider_name: str) -> None:
        async with self._lock:
            self._failure_counts[provider_name]  = 0
            self._unhealthy_until[provider_name] = 0.0

    def is_healthy(self, provider_name: str) -> bool:
        until = self._unhealthy_until.get(provider_name, 0.0)
        return time.monotonic() >= until
```

---

### 3.9 百万字 Token 量级估算公式

> **本节仅给出估算方法和公式框架,不提供任何具体模型单价数字。**
> 实际成本 = token 数 × 当时 Provider 官方单价。单价以 Anthropic / OpenAI 等各 Provider 官方定价页为准,请在使用时自行查阅【需复核】。

#### 3.9.1 正文 Output Token 估算

```
百万字正文 ≈ 100 万汉字
中文 tokenization:1 汉字 ≈ 1.2–2.0 token(因模型 tokenizer 不同【需复核】)
→ 正文 completion tokens ≈ 120 万 ~ 200 万
→ 取保守中值:T_writing_output ≈ 160 万 completion tokens(± 20%)
```

#### 3.9.2 各 Agent 每章 Input Token 构成

```
WritingAgent 每章 input token 来源:
  ┌──────────────────────────────────────────────────────────┐
  │ a. 全局 system prompt + 写作规范           : ~500 tk      │
  │ b. Story Bible 相关条目(检索注入)          : ~800–2000 tk │  ← 稳定,可缓存
  │ c. 当前章节大纲 + beat_targets             : ~200–400 tk  │
  │ d. 近期 N 章 MemoryEntry 摘要(实现4注入)  : ~600–1200 tk │
  │ e. 相关 Foreshadow 状态(门槛1注入)        : ~200–400 tk  │
  │ f. TimelineEvent 相关事件                  : ~200–400 tk  │
  │ g. 写作任务指令 + TasteModel 偏好注入      : ~300–500 tk  │  ← 内核2注入
  └──────────────────────────────────────────────────────────┘
  → 每章 WritingAgent input ≈ 2800–5400 tokens
  → 取均值:~4000 tokens/章

333 章 × 4000 tokens = T_writing_input ≈ 133 万 input tokens

OptionsAgent(多方案生成,关键章触发,假设 30% 章节触发一次):
  每次 input ≈ WritingAgent 同级别 ~4000 tokens,output ≈ 2500 tokens(3 方案)
  0.30 × 333 × 4000 = T_options_input ≈ 40 万 input tokens
  0.30 × 333 × 2500 = T_options_output ≈ 25 万 completion tokens
```

#### 3.9.3 其他 Agent 每章估算

```
OutlineAgent(章大纲):
  input ≈ 2000 tokens, output ≈ 400 tokens
  333 章 → input: 67 万,output: 13 万

PlanningAgent(节拍细化):
  input ≈ 2000 tokens, output ≈ 300 tokens
  333 章 → input: 67 万,output: 10 万

ReviewAgent(审校,含重写触发前的一次校验):
  input ≈ 5000 tokens(含章节正文),output ≈ 500 tokens
  333 章 → input: 167 万,output: 17 万

SummaryAgent(摘要更新):
  input ≈ 4000 tokens, output ≈ 400 tokens
  333 章 → input: 133 万,output: 13 万

ExtractAgent(实体/伏笔/偏好抽取):
  input ≈ 5000 tokens, output ≈ 300 tokens(JSON)
  333 章 → input: 167 万,output: 10 万

FeedbackAgent(FeedbackNote 解析,假设平均每章触发 0.5 次):
  input ≈ 1500 tokens, output ≈ 300 tokens
  0.5 × 333 × 1500 = input: 25 万, output: 5 万
```

#### 3.9.4 汇总公式

```
T_total_input  = T_writing_input + T_options_input + T_other_input
               = 133 万 + 40 万 + (67+67+167+133+167+25) 万
               = 133 + 40 + 626 = 799 万 input tokens

T_total_output = T_writing_output + T_options_output + T_other_output
               = 160 万 + 25 万 + (13+10+17+13+10+5) 万
               = 160 + 25 + 68 = 253 万 completion tokens

T_total = 799 万 + 253 万 ≈ 1050 万 tokens(数量级:~1000 万)

input : output ≈ 3.2 : 1

审校重写额外成本:
  假设 20% 章节触发一次重写(WritingAgent 再调用一次):
  额外 T_rewrite_input  ≈ 0.20 × 333 × 4000 = 27 万
  额外 T_rewrite_output ≈ 0.20 × 333 × 1600 = 11 万
  → 含重写: T_total ≈ 1050 + 38 = ~1090 万 tokens

成本估算公式(需自行填入 Provider 当时单价):
  成本 = T_flagship_input  × P_flagship_input
       + T_flagship_output × P_flagship_output
       + T_fast_input      × P_fast_input
       + T_fast_output     × P_fast_output
       - 缓存节省(见 §3.5.1 公式)

  其中:
    T_flagship_input  = T_writing_input + T_options_input + 重写 input
    T_flagship_output = T_writing_output + T_options_output + 重写 output
    T_fast_input      = 其余 Agent input 之和
    T_fast_output     = 其余 Agent output 之和
    P_*               = Provider 官方单价【需复核,此处不编造】
```

#### 3.9.5 估算参数不确定范围

| 参数 | 保守估算 | 乐观估算 | 主要不确定因素 |
|---|---|---|---|
| 正文 output tokens / 百万汉字 | 200 万 | 120 万 | 模型 tokenizer 效率 |
| 每章 WritingAgent input | 5400 tokens | 2800 tokens | Story Bible 大小 |
| OptionsAgent 触发率 | 50% 章节 | 15% 章节 | 关键章比例 |
| 多 Agent 调用次数/章 | 8 次 | 5 次 | 审校重写轮次 |
| Prompt cache 命中率 | 60% | 90% | 前缀稳定性 |
| 审校重写率 | 40% 章节 | 10% 章节 | 质量阈值设定 |

> **强烈建议**:写完前 50 章后,从 `token_records` 表实际统计每章各 Agent 真实消耗,用实测数据修正估算,再推算剩余章节成本上限。这是防止成本严重偏差的唯一可靠手段。

---

### 3.10 成本控制策略

#### 3.10.1 快模型分担策略(最高优先级)

```
成本最大来源(按 input token × 单价):
  1. WritingAgent input:133 万 × 旗舰单价        ← 最贵,但不可压缩(质量核心)
  2. ReviewAgent input: 167 万 × 快模型单价
  3. SummaryAgent input:133 万 × 快模型单价
  4. ExtractAgent input:167 万 × 快模型单价

优化手段:
  - ReviewAgent / SummaryAgent / ExtractAgent / FeedbackAgent
    严格使用 fast 档位(快模型单价通常显著低于旗舰)
  - 若快模型在审校任务上的质量下限不可接受(见工程6 实测),
    可对 ReviewAgent 启用 ultra 档——但此时要重新核算成本
  - WritingAgent 仅在"过渡章节"(情节连接强、创意要求低)时降 fast,
    且必须在告警用户后才降级(质量优先)
```

#### 3.10.2 缓存命中率优化

```python
# 提升缓存命中率的具体措施

## 措施 1:Story Bible 稳定化分层
# 将注入内容按更新频率分层:
#   - 极稳定层(角色基础档案、世界法则):整部作品通用 → 每章都用 prompt cache 标记
#   - 中等稳定层(角色当前状态 CharState):每 5–10 章变化一次 → 谨慎标记
#   - 不稳定层(本章大纲、最近摘要):每章变化 → 不标记
# 分层越清晰,缓存命中率越高

## 措施 2:ExtractAgent / SummaryAgent 结果缓存最大化
# temperature = 0.1(接近确定性)→ 相同输入大概率产生相同输出 → 应用侧缓存命中
# 目标:ExtractAgent 跨运行结果缓存命中率 > 70%

## 措施 3:批量化小调用
# 多个实体抽取任务合并为一次 ExtractAgent 调用
# 减少 API 调用次数 → 降低每次的 system prompt 重复消耗
# 但单次 prompt 不超过 ExtractAgent 合理的 max_tokens 上限

## 措施 4:缓存监控 + 自动告警
# TokenLedger 实时统计 cached_prompt_tokens / (prompt_tokens + cached_prompt_tokens)
# 若命中率低于 30% 持续 10 章 → AlertManager.send_cache_miss_spike_alert()
```

#### 3.10.3 分级校验策略(按章节重要性)

```
全量校验(每章全套 5 个 Agent):成本最高,质量最稳
  OutlineAgent + WritingAgent + ReviewAgent + SummaryAgent + ExtractAgent

分级校验(按章节类型):

  关键章(触发条件:卷首/卷尾、Chapter.beat_targets 含三幕节点、OptionsAgent 触发章):
    → 全量校验 + 深度 ReviewAgent(可升 ultra 档)
    → OptionsAgent 产出多方案供人选

  普通章(过渡/铺垫/连接):
    → 省略深度 ReviewAgent,使用轻量一致性检查(fast 档,低 max_tokens)
    → SummaryAgent 每 3 章更新一次(而非每章)
    → ExtractAgent 仅在检测到新实体或新伏笔时调用(FeedbackAgent 判断)

预估节省(方法论):
  设 40% 章节为普通章,每章省 2 次 Agent 调用:
  节省调用数 = 0.40 × 333 × 2 = 266 次
  节省成本   = 266 × 平均调用成本【需用实测单价计算】
```

#### 3.10.4 写作-审校-重写循环的成本上限

```python
# 必须设置硬性循环上限,防止意外成本暴增

MAX_REWRITE_ROUNDS = config.get("max_rewrite_rounds", 2)  # 默认最多重写 2 次

async def chapter_generation_loop(chapter_id: str) -> None:
    for round_idx in range(MAX_REWRITE_ROUNDS + 1):
        # 生成正文
        draft = await writing_agent.generate(chapter_id)
        # 审校
        flags: list[ConsistencyFlag] = await review_agent.review(chapter_id, draft)
        
        if not flags:
            break   # 审校通过,退出循环
        
        if round_idx == MAX_REWRITE_ROUNDS:
            # 超出上限:不再重写,进入人工审核队列
            for flag in flags:
                await db.update(flag, status="needs_human_review")
            await db.update_chapter_status(chapter_id, "pending_human_review")
            await alert_manager.send_budget_warning(
                work_id, usage_ratio=0.0  # 触发"待人审"通知
            )
            break
        
        # 未超上限:触发重写
        await writing_agent.rewrite(chapter_id, flags)
```

#### 3.10.5 50 章后成本趋势自动报告

```python
# 每完成 50 章,自动生成成本趋势报告并推送给用户

async def maybe_emit_cost_trend_report(work_id: str, completed_chapters: int):
    if completed_chapters % 50 != 0:
        return

    summary = await ledger.get_cost_trend(work_id, window_chapters=50)
    avg_tokens_per_chapter = summary["avg_tokens_per_chapter"]
    remaining_chapters     = summary["estimated_remaining_chapters"]
    projected_remaining    = avg_tokens_per_chapter * remaining_chapters

    work_budget = await budget_manager.get_work_budget(work_id)
    used_so_far = await ledger.get_work_total_tokens(work_id)
    remaining_budget = work_budget - used_so_far

    if projected_remaining > remaining_budget * 1.2:
        # 预测超支 20%,发出趋势告警
        await alert_manager.send_budget_warning(
            work_id,
            usage_ratio=used_so_far / work_budget,
        )
        # 同时推送成本预测数据到前端
        await sse_bus.publish(f"work:{work_id}", {
            "type": "cost_trend_report",
            "completed_chapters": completed_chapters,
            "avg_tokens_per_chapter": avg_tokens_per_chapter,
            "projected_remaining_tokens": projected_remaining,
            "remaining_budget_tokens": remaining_budget,
            "recommendation": "建议启用分级校验策略或调整预算设置",
        })
```

#### 3.10.6 成本控制策略总表

| 策略 | 预期效果 | 实现复杂度 | MVP 阶段 |
|---|---|---|---|
| 快模型分担非写作 Agent | 显著降低规划/审校成本 | 低(路由配置) | ✓ 包含 |
| Story Bible 前缀 prompt cache | 降低 WritingAgent input 成本 | 中(Provider caching 对接) | 延后 |
| 结果缓存(ExtractAgent/SummaryAgent) | 减少重复抽取调用 | 低(Redis) | 延后 |
| 分级校验(按章节重要性) | 减少 ~30% 总调用次数 | 中(章节分级逻辑) | 延后 |
| 重写轮次硬上限 | 防止单章成本失控 | 低(循环计数器) | ✓ 包含 |
| per-Work 预算告警 + 降级 | 防止整部作品成本失控 | 中(BudgetManager) | 延后(增强版) |
| 50 章成本趋势报告 | 精确预算外推 | 低(聚合查询) | 延后 |
| 多 API Key 负载均衡 | 扩容旗舰模型 TPM | 中 | 延后(完整版) |

---

## 4. 数据契约

### 4.1 消费的规范实体(00 §4,只读)

| 实体 | 字段 | 用途 |
|---|---|---|
| `Work` | `id` | 作品维度预算管理 key |
| `Chapter` | `id`, `status` | 章节维度成本计量 key |
| `MemoryEntry` | (由实现4组装后注入 prompt) | 本层不直接访问 |
| `TasteModel` | (由内核2注入 prompt 前) | 本层不直接访问 |

本层不直接访问 `Segment`、`Character`、`SettingItem` 等实体——上层 Agent 负责从实现4 获取并组装 prompt,本层只接收最终 messages。

### 4.2 写入的运营数据(非规范模型实体)

| 表 | 写入时机 | 说明 |
|---|---|---|
| `token_records` | 每次 LLM 调用完成后 | Token 计量持久化(DDL 见 §3.6.2) |
| `system_alerts` | 预算警告 / 降级 / 缓存命中率异常 | 告警记录(DDL 见 §3.6.2) |

`token_records` 外键 `work_id` / `chapter_id` 与 00 §4 规范模型对齐;但表本身属于运营/计量数据,不纳入规范模型。

---

## 5. 对外接口

### 5.1 核心 Python 接口(供实现3编排引擎消费)

```python
class LLMRouter:

    async def complete(
        self,
        agent_role: AgentRole,
        prompt: str | list[dict],
        opts: CompletionOpts = CompletionOpts(),
    ) -> CompletionResult:
        """唯一的非流式完成入口。全部 Agent 均通过此接口调用 LLM。"""

    async def stream_complete(
        self,
        agent_role: AgentRole,
        prompt: str | list[dict],
        opts: CompletionOpts = CompletionOpts(),
    ) -> AsyncGenerator[str, None]:
        """流式完成入口。用于前端实时显示正文生成。"""

    async def get_work_cost_summary(self, work_id: str) -> WorkCostSummary:
        """作品累计 token 消耗与预算状态。供前端成本看板使用。"""

    async def get_chapter_cost_summary(self, chapter_id: str) -> ChapterCostSummary:
        """章节级 token 消耗明细。"""

    async def set_work_budget(self, work_id: str, budget_config: BudgetConfig) -> None:
        """设置作品预算配置。通常在 Work 创建时调用。"""

    async def health_check_all_providers(self) -> dict[str, bool]:
        """探测所有已配置 Provider 的可用性。供工程1 健康检查端点调用。"""
```

### 5.2 内部接口(模块内)

```python
# 路由决策
LLMRouter._resolve_route(agent_role, opts, forced_tier=None) -> (LLMProvider, ModelConfig)

# 预算检查 + 降级决策
BudgetManager.check_and_maybe_downgrade(...) -> (bool, ModelTier | None)

# 速率限制令牌桶
TokenBucketRateLimiter.acquire(provider, tier, tokens, timeout) -> bool

# Prompt 前缀缓存标记
PromptCacheBuilder.mark_cacheable_prefix(messages, provider_name) -> list[dict]

# 缓存键
ResultCache._make_cache_key(agent_role, messages, model_id, ...) -> str

# 健康状态
HealthTracker.is_healthy(provider_name) -> bool
HealthTracker.record_failure(provider_name) -> None
HealthTracker.record_success(provider_name) -> None
```

### 5.3 REST API 端点(与工程5-API 对齐)

```
GET  /api/v1/works/{work_id}/cost
     → WorkCostSummary {
         total_prompt_tokens, total_completion_tokens,
         total_cached_prompt_tokens,
         by_agent_role: {...},
         by_chapter:   [...],
         result_cache_hit_count,
         budget_status: "normal" | "warning" | "degraded" | "blocked",
       }

GET  /api/v1/chapters/{chapter_id}/cost
     → ChapterCostSummary {
         total_tokens, by_agent_role,
         latency_p50_ms, latency_p99_ms,
       }

GET  /api/v1/system/llm/health
     → { "anthropic": true, "openai": false, ... }

POST /api/v1/works/{work_id}/budget
     Body: BudgetConfig
     → 201 Created

GET  /api/v1/works/{work_id}/alerts?limit=20
     → AlertRecord[]

GET  /api/v1/works/{work_id}/cost/trend?window=50
     → CostTrendReport {
         avg_tokens_per_chapter,
         projected_remaining_tokens,
         remaining_budget_tokens,
         warning: bool,
       }
```

---

## 6. 失败模式与缓解

### 6.1 Provider 全量不可用

**症状**:所有已配置 Provider 均返回 5xx 或连接超时。

**后果**:整个生成流程中断。

**缓解**:
1. `HealthTracker` 后台持续探测(每 30s),一旦任一 Provider 恢复立即解除短路。
2. 配置本地/自托管 vLLM 作为 `fallback` 档位,作为最后防线(可选)。
3. 编排引擎在收到 `ProviderUnavailableError` 时,将当前章任务放回延迟队列(而非丢弃),等待恢复后自动重试。

### 6.2 成本估算严重低估

**症状**:实际每章 token 消耗显著高于 §3.9 估算(如 ReviewAgent 大量触发重写)。

**后果**:百万字作品实际成本数倍于预期。

**缓解**:
1. 重写轮次硬上限(§3.10.4),防止单链路无界循环。
2. 每 50 章自动生成成本趋势报告(§3.10.5),超出预算 120% 时主动告警并建议策略调整。
3. 分级校验(§3.10.3)在成本超警戒线时自动启用。

### 6.3 Prompt Cache 失效导致成本上升

**症状**:Story Bible 频繁更新导致缓存每次都 miss,稳定前缀假设不成立。

**后果**:预期的 prompt cache 节省未实现,input token 成本高于估算。

**缓解**:
1. `TokenLedger` 实时监控 `cached_prompt_tokens / total_prompt_tokens` 命中率。
2. 命中率持续低于 30%,发出 `cache_miss_spike_alert`(§3.7.3)。
3. 将 Story Bible 中"高频更新"字段(如 `CharState`)与"极稳定"字段(如基础档案)物理分离——只对极稳定部分启用 cache 标记(§3.5.1)。

### 6.4 速率限制导致生成停滞

**症状**:旗舰模型 TPM 耗尽,`WritingAgent` 调用持续等待令牌桶。

**后果**:章节生成时延大幅上升,用户体验变差。

**缓解**:
1. 令牌桶精准预估消耗,避免因过度估算而提前拦截。
2. 非实时任务(`ExtractAgent` / `SummaryAgent`)安排在写作任务间隙执行,避免与 `WritingAgent` 竞争 TPM。
3. 多 API Key 负载均衡(完整版,需确认 Provider 服务条款合规性【需复核】)。

### 6.5 路由配置错误(档位搞反)

**症状**:`WritingAgent` 被误路由到 `fallback` 档位,正文质量显著下降。

**后果**:质量崩坏可能写了十章才被发现。

**缓解**:
1. 路由配置文件加 Pydantic schema 校验,防止非法配置在 CI/CD 阶段通过。
2. `token_records` 的 `model_id` 字段记录实际使用的模型——前端成本看板可展示"模型使用分布",异常降级一目了然。
3. 生产配置变更走 config review 流程,禁止热改生产路由表。

### 6.6 百万字主题漂移(边界说明)

**症状**:长程生成偏离主线,但 LLM 层本身运作正常。

**说明**:这是实现3(编排引擎)/ 实现4(记忆与检索) 的问题,LLM 接入层只保证调用正确执行和 prompt 完整传递——**本层无法检测主题漂移**。若 prompt 携带了正确的 `TasteModel`、`AuthorIntent`、`MemoryEntry` 上下文,漂移问题应在上层解决。

---

## 7. MVP vs 完整版

### 7.1 MVP(验证核心闭环)

**目标**:能跑通"单 Provider(Anthropic)+ 按角色路由两档模型 + 基础 token 计量"的完整闭环。

**包含**:
- `LLMProvider` 抽象 + `AnthropicProvider` 实现
- `LLMRouter.complete()` 非流式版本
- 按 `AgentRole` 路由到 `flagship` / `fast` 两档
- `TokenLedger` 写入(仅写,无聚合 API)
- 本地 LRU dict 结果缓存(TTL 1h)
- 基础重试(3 次指数退避,`tenacity`)
- 基础超时配置(硬编码)
- 重写轮次硬上限(循环计数器)

**不包含(延后)**:
- 流式输出(MVP 先轮询)
- 多 Provider 故障切换
- 预算管理与告警(`BudgetManager`)
- Prompt 前缀缓存标记
- Redis 缓存
- 速率限制令牌桶
- 成本看板 REST API

### 7.2 增强版(十万字量级)

在 MVP 基础上增加:
- `stream_complete` 流式接口 + 前端 SSE
- `OpenAIProvider` 备选 + `HealthTracker` 短路熔断
- Redis 结果缓存(TTL 可配)
- 速率限制令牌桶(基础版)
- `BudgetManager` per-Work 预算告警
- `TokenLedger` 聚合查询 API + 前端成本看板

### 7.3 完整版(百万字)

在增强版基础上增加:
- Prompt 前缀缓存标记(对接 Anthropic / OpenAI caching)
- `BudgetManager` per-Chapter 精细预算 + 自动降级链
- 分级校验策略(按章节重要性)
- 50 章成本趋势自动报告
- 多 API Key 负载均衡(旗舰模型 TPM 扩容)
- `system_alerts` 前端告警面板
- 成本预测 API(外推剩余章节)
- 可选:本地 vLLM 自托管 `fallback` 档位

---

## 8. 证据与引用

| 结论 | 证据级别 | 来源 |
|---|---|---|
| 百万字问题必须靠"分层规划 + 检索 + 压缩",不能靠长上下文 | **【已核实】** | arXiv 2505.12572, 2412.13575, 2506.16445, 2508.03137 |
| 写作 Agent 用旗舰模型、规划/审校/摘要/抽取用快模型(方向性) | **【已核实(方向性)】** | 设计哲学 §2 能力矩阵;具体型号须自有语料实测【需复核】 |
| "某模型一致性错误密度最低"类排行不可用于选型 | **【已核实(被证伪)】** | 设计哲学对抗式验证;调研文档 §1.1 注 |
| 多模型路由以平衡质量/成本是业界最佳实践方向 | **【已核实(方向性)】** | 设计哲学 §2;调研文档 §3.1 |
| Provider 抽象层架构模式 | **【稳定知识】** | 业界通行做法(Adapter 模式),无需特定论文背书 |
| Prompt 前缀缓存可降低 input token 成本 | **【需复核】** | 各 Provider caching 功能以官方最新文档为准 |
| 成本估算需在自有语料实测后校准 | **【已核实】** | arXiv 2505.12572(压缩比对不同语料泛化性受限) |
| per-章最大重写轮次 = 2 | **【设计决策】** | 本团队综合判断;需在实测中调整 |
| 分级校验策略(关键章 vs 普通章) | **【设计决策】** | 本团队综合,无外部背书 |
| token_records 不存储单价,在报告层叠加 | **【设计决策】** | 避免历史价格变更导致数据失真 |
| 模型具体单价、context window、rate limit 所有数字 | **【需复核】** | 以 Anthropic / OpenAI 官方定价页及文档为准,本文不编造 |

---

## 9. 开放问题

> 标注类型:【复核】= 需查官方文档;【实验】= 需在 Scribe 实际运行中验证;【决策】= 待团队拍板。

**【复核】P1 — 各 Provider Prompt Caching 最新状态**
Anthropic 和 OpenAI 的 prompt caching 功能:最小可缓存 block 长度、计费系数(缓存命中 vs 正常 input 的折扣比例)、并发调用间是否共享缓存、TTL 是否可配?以 2026 年官方最新文档为准,确认后更新 §3.5.1 和 §3.10.2 的估算参数。

**【复核】P1 — 各档位模型的实际 TPM / RPM 限额**
§3.3.3 中 `flagship_tpm` / `fast_tpm` 均为示例占位。需查 Anthropic / OpenAI 实际限额,结合 Scribe 预期并发量设计令牌桶容量。

**【实验】P1 — 每章实际 token 消耗基准测量**
§3.9 的估算基于理论假设,需在跑通 MVP 后以实际运行数据(50+ 章)校准:
- 每章 `WritingAgent` 实际 input tokens(Story Bible 注入大小随进展的增长曲线)
- `ReviewAgent` 触发重写比例(对总成本影响最大的变量)
- `ExtractAgent` 结果缓存命中率(验证 temperature=0.1 设定是否有效)

**【实验】P1 — Prompt Cache 实际命中率**
Story Bible 实际更新频率 vs. 缓存 TTL 的关系:若更新过频繁,cache 节省可能远低于预期。需测量前 50 章的 `cached_prompt_tokens / total_prompt_tokens` 实际比值。

**【决策】P2 — 章节"重要性分级"的编码规则**
§3.10.3 依赖"关键章 vs 普通章"分级。草案规则:卷首/卷尾章、`beat_targets` 含三幕节点的章节为关键章。需与实现1(分层规划)联动确认,并编码到 `OutlineAgent` 的输出 schema 中。

**【决策】P2 — per-Chapter / per-Work 预算默认值**
`chapter_token_budget` 和 `work_token_budget` 的合理绝对值依赖实际单价与作者预期成本。MVP 阶段建议采用"宽松默认值 + 用户可调"策略,在 50 章实测后给出推荐默认值。

**【实验】P2 — 快模型在规划/审校任务上的质量下限**
需在工程6 的评估系统上测试:快模型 vs 旗舰模型在"ConStory 19 类错误检出精确率"上的差距——若差距超过可接受阈值,需考虑将 `ReviewAgent` 升档,此时要重新核算成本模型。

**【实验】P3 — OptionsAgent 触发率对成本的影响**
§3.9 假设 30% 章节触发 `OptionsAgent`(多方案生成)。实际触发率取决于内核1(作者协作回路)对"关键决策点"的判断逻辑。需在原型阶段测量真实触发率并更新成本估算。

**【复核】P3 — 多 API Key 负载均衡的 Provider 服务条款合规性**
使用多个 API Key 或多账户分散 TPM 限制在技术上可行,但需确认各 Provider 服务条款是否允许此使用模式,避免违规封号。

---

*本文档与以下文档存在直接接口依赖,变更时应同步:*
- **[实现3-编排引擎](实现3-编排引擎.md)**:调用 `complete()` 的主要消费方,`AgentRole` 枚举变化需联动
- **[实现2-写作生成](实现2-写作生成.md)**:`WritingAgent` / `OptionsAgent` 的 prompt 结构影响 prompt cache 命中率
- **[工程6-质量度量](工程6-质量度量.md)**:质量评估指标驱动 `ReviewAgent` 重写决策,间接影响本模块成本
- **[工程2-交互与编辑器](工程2-交互与编辑器.md)**:成本看板 REST API 和预算告警 SSE 的前端消费方
- **[工程5-API](工程5-API.md)**:cost / budget / health / alerts 端点的契约定义
- **[工程1-架构与技术栈](工程1-架构与技术栈.md)**:可观测性要求(token 用量监控、Provider 健康状态)

---

## 与主编(内核0)的对齐增补

主编([内核0](内核0-主编智能体.md))是 `complete()` 的最高层消费者。三处对齐:

1. **新增两个 AgentRole 的路由**:`AdvisorAgent`(评议/责编,产 DiscussionThread/ProactiveInsight)→ 需强推理,路由**前沿模型**;`ChiefEditor`(主编对话)→ 前沿模型。沿用旗舰/快模型分档。
2. **Hermes 多 Provider 复用(对齐 [工程8](工程8-HermesAgent复用方案.md))**:`complete()` 抽象可直接落到 Hermes Agent 的 18+ Provider 路由(`hermes model` 无代码切换;`delegate_task` 可为子Agent 指定不同 model 降本),减少自写 Provider 适配代码。
3. **Hermes 模型作个性化档(对齐 [内核0 §3.7](内核0-主编智能体.md))**:贴合你文风的起草/暗黑题材/隐私敏感/海量低成本 → 路由自托管 **Hermes 4 + LoRA**;最难全局判断与顶级文笔 → 前沿模型。选型须用 [工程10](工程10-可观测日志与评测.md) 在自有语料实测,**严禁用未验证排行**。

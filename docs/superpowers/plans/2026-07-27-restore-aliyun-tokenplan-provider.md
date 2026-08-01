# Restore Aliyun TokenPlan Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 恢复所有无工具写作与 Hermes 写作 profile 到阿里云 TokenPlan，且审计身份、模型和错误提示与真实链路一致。

**Architecture:** 无工具正文路径继续通过 `deepseek_client.py` 的兼容导出调用阿里云 OpenAI 兼容端点；模块名和旧设置键只保留兼容性，不得改变审计身份。工具与审批路径仍由四个 Hermes profile 按现有 MCP 边界运行。

**Tech Stack:** FastAPI、httpx、Hermes Agent、pytest、React/Vitest。

## Global Constraints

- 不回显、提交或转写任何 API key。
- 不修改 MCP 工具权限、审批门控或 SurrealDB 数据。
- Provider 身份必须为 `qwen`、端点必须为 TokenPlan 官方兼容端点、模型为 `qwen3.8-max-preview`。

---

### Task 1: 恢复无工具写作的 TokenPlan 契约

**Files:**
- Modify: `scribe3/tests/test_deepseek_client.py`
- Modify: `scribe3/deepseek_client.py`
- Modify: `scribe3/llm.py`
- Modify: `scribe3/settings.py`

**Interfaces:**
- Consumes: `DeepSeekClient` 兼容导出及 `DEEPSEEK_API_KEY` 的既有受掩码设置存储。
- Produces: `ProviderIdentity(provider="qwen", api_base="https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1", model="qwen3.8-max-preview", official=True, transport="httpx")`。

- [x] **Step 1: 写回归测试**

将 `test_deepseek_client.py` 的默认模型、身份、错误提示断言改为上述 TokenPlan 契约。

- [x] **Step 2: 验证 RED**

运行：`scribe3/.venv/bin/python -m pytest scribe3/tests/test_deepseek_client.py -q`

预期：因现代码仍指向 DeepSeek 而失败。

- [x] **Step 3: 最小恢复实现**

恢复 TokenPlan 的常量、设置默认值、无工具流说明与安全错误提示；不改调用接口。

- [x] **Step 4: 验证 GREEN**

运行：`scribe3/.venv/bin/python -m pytest scribe3/tests/test_deepseek_client.py -q`

预期：全部通过。

### Task 2: 恢复四个 Hermes profile 并做真实最小探测

**Files:**
- Modify: `/Users/miaoma/.hermes/profiles/scribe3/config.yaml`
- Modify: `/Users/miaoma/.hermes/profiles/scribe3_write/config.yaml`
- Modify: `/Users/miaoma/.hermes/profiles/scribe3_deduce/config.yaml`
- Modify: `/Users/miaoma/.hermes/profiles/scribe3_deduce_preview/config.yaml`

**Interfaces:**
- Consumes: TokenPlan 的现有 API 凭证与 Hermes `alibaba-coding-plan`/自定义 OpenAI 兼容配置能力。
- Produces: 四个 profile 均指向同一 TokenPlan 端点与模型，且保留原有 toolset 配置。

- [x] **Step 1: 验证配置前置条件**

只检查 TokenPlan 凭证是否存在，不输出其值。

- [x] **Step 2: 写入 profile 配置**

仅替换 `model` 入口的 provider、base_url、api_key 引用和 model；不得覆盖其他 YAML 节点。

- [x] **Step 3: 重启并验证运行时**

通过现有后端 profile 重启入口重启四个 Hermes gateway，再对每个 profile 发起最小无副作用请求，确认真实返回的模型与 provider。

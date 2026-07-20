# Scribe3 小说质量 P0 运行时基础 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 停止让全量 Hermes 文档镜像阻塞业务，先交付真正无限的调用语义、官方 DeepSeek 的统一无工具生成链和可核验的供应商身份，为后续 Creative Context Engine 与质量闭环提供可信运行时基础。

**Architecture:** 保留 Hermes 作为需要工具、审批和 Runs 的 agent runtime；所有不需要工具的生成、参考分析与质量评价统一通过一个官方 DeepSeek 客户端。调用次数台账继续记录使用量，但 `SCRIBE3_DAILY_CALL_CAP=0` 表示无限且不再阻断；API 与 UI 用显式 `unlimited` 契约展示，不把 `0` 误解为零额度。

**Tech Stack:** Python 3.14、FastAPI、httpx、SQLite、React、Vitest、pytest。

## Global Constraints

- SurrealDB 与现有 Scribe3 领域模型是唯一业务权威；Hermes 证据缓存不得进入小说业务召回。
- 不升级 SurrealDB 或 Hermes Agent；不执行 `hermes update`。
- 不接入、不预留 Spectron；不新增可视化伴侣。
- 不读取、打印、写入测试报告或提交任何真实 secret；DeepSeek key 使用本地受限权限设置存储（父目录 0700、数据库文件 0600）与审计掩码，当前不宣称静态加密。
- `SCRIBE3_DAILY_CALL_CAP=0` 表示产品调用次数无限；仍记录 calls、tokens、供应商限流与费用证据。
- 所有无工具核心生成、参考分析和质量评价必须走 `https://api.deepseek.com`，默认模型为 `deepseek-chat`；缺 key 时 fail loud，不允许静默回退到 Doubao 或 Hermes 默认供应商。
- Hermes 只保留给确实需要 MCP 工具、审批或 Runs 的路径；这些路径必须标记为 `hermes_gateway`，不得冒充官方 DeepSeek。
- 所有行为修改必须按 RED → GREEN 完成；测试不得访问真实网络或真实设置数据库。

---

### Task 1: 冻结过度证据抓取并重排进度

**Files:**
- Modify: `.superpowers/sdd/progress.md`
- Modify: `docs/superpowers/plans/2026-07-19-hermes-official-evidence-cache-and-capability-audit.md`

**Interfaces:**
- Consumes: 已生成的 `website-20260719T222857Z` 官网快照与已提交的证据工具。
- Produces: 明确的 `stopped_sufficient` 状态，以及不会继续运行 `hermes_evidence.cli all` 的执行边界。

- [ ] **Step 1: 在旧计划中记录调整决定**

在 Task 7 前增加“2026-07-20 Scope Adjustment”，逐字写明：官网365篇零失败快照作为按需能力审计的足够证据；不再要求 release/main/website 三套全量快照共同生成 `current.json`；Tasks 8–10只审计 Runs、approval、Memory Provider lifecycle、context boundary、provider identity；Task 11不再把全量镜像完整性作为业务实施前置门。

- [ ] **Step 2: 更新持久进度台账**

把 Evidence Task 7 标为 `stopped_sufficient`，Tasks 8–10 标为 `narrowed_non_blocking`，并新增本计划任务清单。不得把 Task 7 写成 `complete`，因为 `current.json` 从未生成。

- [ ] **Step 3: 验证措辞与进程边界**

Run:

```bash
rg -n 'stopped_sufficient|narrowed_non_blocking|365|current.json|不再.*all' \
  .superpowers/sdd/progress.md \
  docs/superpowers/plans/2026-07-19-hermes-official-evidence-cache-and-capability-audit.md
pgrep -af 'scribe3\.hermes_evidence\.cli all' || true
```

Expected: 文档包含全部边界；无 `all` 进程。

- [ ] **Step 4: Commit**

```bash
git add .superpowers/sdd/progress.md docs/superpowers/plans/2026-07-19-hermes-official-evidence-cache-and-capability-audit.md docs/superpowers/plans/2026-07-20-scribe3-quality-p0-runtime-foundation.md
git commit -m "docs: refocus execution on novel quality runtime"
```

### Task 2: 实现 `0 = unlimited` 后端契约

**Files:**
- Modify: `scribe3/usage.py`
- Modify: `scribe3/llm.py`
- Modify: `scribe3/settings.py`
- Modify: `scribe3/app.py`
- Modify: `scribe3/tests/test_usage_budget.py`
- Modify: `scribe3/tests/test_settings.py`
- Modify: `scribe3/tests/test_settings_api.py`
- Modify: `scribe3/tests/test_selection.py`

**Interfaces:**
- Produces: `usage.tick(cap: int) -> str`，当 `cap == 0` 时只记账、不阻断。
- Produces: `llm.daily_remaining() -> int | None`，无限时返回 `None`。
- Produces: `/ai/usage.cap = {cap, used_today, remaining, unlimited, scope}`。

- [ ] **Step 1: 写失败测试**

新增测试，要求：默认 cap 为0；`tick(0)` 连续调用仍增加 `used_today`；`daily_remaining()` 返回 `None`；`/ai/usage` 返回 `unlimited: true` 与 `remaining: null`；选择环在无限模式下不返回429。

- [ ] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_usage_budget.py \
  scribe3/tests/test_settings.py \
  scribe3/tests/test_settings_api.py \
  scribe3/tests/test_selection.py -q
```

Expected: 新增断言因当前 `0` 会立即阻断、默认仍为500而失败。

- [ ] **Step 3: 最小实现**

`usage.tick()` 仅在 `cap > 0` 时比较上限；无论有限或无限都原子递增。设置默认改为0，说明改为“0=无限，正整数=成本保险丝”。`daily_remaining()` 在cap为0时返回`None`。选择环只在remaining非`None`且不足时拦截。`/ai/usage`新增布尔字段`unlimited`。

- [ ] **Step 4: 运行 GREEN**

Run Task 2 Step 2 同一命令。

Expected: 全部通过，且测试未访问真实网络。

- [ ] **Step 5: Commit**

```bash
git add scribe3/usage.py scribe3/llm.py scribe3/settings.py scribe3/app.py \
  scribe3/tests/test_usage_budget.py scribe3/tests/test_settings.py \
  scribe3/tests/test_settings_api.py scribe3/tests/test_selection.py
git commit -m "feat: make zero LLM call cap unlimited"
```

### Task 3: 让前端正确呈现无限用量

**Files:**
- Modify: `scribe3/web/src/ChiefDock.jsx`
- Modify: `scribe3/web/src/settings/SettingsView.jsx`
- Modify: `scribe3/web/src/__tests__/chiefDock-ui.test.jsx`
- Modify: `scribe3/web/src/settings/__tests__/settingsView.test.jsx`

**Interfaces:**
- Consumes: `/ai/usage.cap.unlimited` 与 nullable `remaining`。
- Produces: 无限模式显示“今日已用 N 发 · 不限次数”，不显示 `N/0` 或0%日帽。

- [ ] **Step 1: 写失败测试**

为 ChiefDock 与 SettingsView 增加 `unlimited:true` fixture，断言界面出现“不限次数”，且不存在 `/ 0`、`日帽 0`。

- [ ] **Step 2: 运行 RED**

Run:

```bash
cd scribe3/web && npm test -- --run \
  src/__tests__/chiefDock-ui.test.jsx \
  src/settings/__tests__/settingsView.test.jsx
```

Expected: 当前组件仍渲染 `used/0`，新增断言失败。

- [ ] **Step 3: 最小实现并运行 GREEN**

两个组件以 `cap.unlimited === true` 为唯一无限判断；有限模式保持原显示。再次运行 Step 2 命令，Expected: PASS。

- [ ] **Step 4: Commit**

```bash
git add scribe3/web/src/ChiefDock.jsx scribe3/web/src/settings/SettingsView.jsx \
  scribe3/web/src/__tests__/chiefDock-ui.test.jsx \
  scribe3/web/src/settings/__tests__/settingsView.test.jsx
git commit -m "feat: display unlimited LLM usage honestly"
```

### Task 4: 建立唯一的官方 DeepSeek 无工具客户端

**Files:**
- Create: `scribe3/deepseek_client.py`
- Create: `scribe3/tests/test_deepseek_client.py`
- Modify: `scribe3/settings.py`

**Interfaces:**
- Produces: `DeepSeekClient.complete(messages, *, model=None, max_tokens=None, temperature=None, thinking=None) -> CompletionResult`。
- Produces: `DeepSeekClient.stream(messages, *, model=None) -> Iterator[dict]`。
- Produces: `ProviderIdentity(provider, api_base, model, official, transport)`；不得包含key。

- [ ] **Step 1: 写失败测试**

测试固定官方base、默认`deepseek-chat`、Authorization只进入请求header而不进入结果或异常、缺key fail loud、4xx不重试、5xx/连接错误按设置重试、空choices/空content抛结构化错误、usage与缓存token字段被保留、流式delta和最终usage可解析。

- [ ] **Step 2: 运行 RED**

Run: `scribe3/.venv/bin/python -m pytest scribe3/tests/test_deepseek_client.py -q`

Expected: FAIL because module is missing.

- [ ] **Step 3: 最小实现**

使用注入的`httpx.Client`或模块级httpx接口以便测试；只从`settings.get_setting("DEEPSEEK_API_KEY")`取key；所有公开结果与日志只含`ProviderIdentity`、模型、usage和状态，不含header值。默认模型设置改为`deepseek-chat`。

- [ ] **Step 4: 运行 GREEN**

Run Step 2 同一命令与 `scribe3/.venv/bin/python -m pytest scribe3/tests/test_settings.py -q`。

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add scribe3/deepseek_client.py scribe3/tests/test_deepseek_client.py scribe3/settings.py
git commit -m "feat: add official DeepSeek completion client"
```

### Task 5: 将所有无工具补全统一路由到官方 DeepSeek

**Files:**
- Modify: `scribe3/llm.py`
- Modify: `scribe3/tests/test_llm_stream.py`
- Modify: `scribe3/tests/test_usage_budget.py`
- Modify: `scribe3/app.py`

**Interfaces:**
- Consumes: `DeepSeekClient`。
- Preserves: `hermes_complete(...)`、`hermes_complete_stream(...)` 兼容签名，内部改为官方DeepSeek；`official_api`参数保留一个兼容周期但不再改变路由。
- Preserves: `hermes_responses_events(..., with_tools=True)` 与 Runs 仍走Hermes。

- [ ] **Step 1: 写失败测试**

测试普通 `hermes_complete` 与 `hermes_complete_stream` 不传 `official_api` 也访问官方base；缺key直接失败；不得调用`HermesAuth`；`with_tools=True`仍调用Hermes Responses；返回trace含官方供应商身份。

- [ ] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_llm_stream.py scribe3/tests/test_usage_budget.py -q
```

Expected: 默认路径仍指向Hermes，新增测试失败。

- [ ] **Step 3: 最小实现与 GREEN**

让两个无工具兼容函数委托`DeepSeekClient`，保持现有重试、流式“不在首delta后重试”与调用计数语义。运行 Step 2 命令，Expected: PASS。

- [ ] **Step 4: 静态确认无工具调用边界**

Run:

```bash
rg -n 'hermes_complete\(|hermes_complete_stream\(' scribe3 --glob '*.py'
rg -n 'api\.deepseek\.com|DeepSeekClient|HermesRuntime' scribe3/llm.py scribe3/deepseek_client.py
```

Expected: 所有旧调用点经过兼容门面进入官方客户端；工具/Runs边界仍清晰。

- [ ] **Step 5: Commit**

```bash
git add scribe3/llm.py scribe3/app.py scribe3/tests/test_llm_stream.py scribe3/tests/test_usage_budget.py
git commit -m "refactor: route tool-free generation through DeepSeek"
```

### Task 6: 暴露不含密钥的供应商真实性证据

**Files:**
- Modify: `scribe3/app.py`
- Modify: `scribe3/tests/test_usage_budget.py`
- Modify: `scribe3/web/src/settings/SettingsView.jsx`
- Modify: `scribe3/web/src/settings/__tests__/settingsView.test.jsx`

**Interfaces:**
- Produces: `/ai/usage.provider = {provider, api_base, model, official, transport, key_present}`。
- Security: `key_present`仅为布尔值，只表示 DB/env 中存在密钥记录，不表示语法有效或服务可用；响应序列化结果不得匹配secret模式。

- [ ] **Step 1: 写失败测试**

后端断言供应商为`deepseek`、base为`https://api.deepseek.com`、`official:true`、`transport:"direct"`、key仅布尔表示；前端断言显示“官方 DeepSeek · deepseek-chat · 直连”。

- [ ] **Step 2: 运行 RED**

Run:

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_usage_budget.py -q
cd scribe3/web && npm test -- --run src/settings/__tests__/settingsView.test.jsx
```

Expected: provider字段与UI尚不存在，测试失败。

- [ ] **Step 3: 最小实现与 GREEN**

从`DeepSeekClient.identity()`和设置元数据构造只读响应，不读取或返回key内容；前端只消费该公开结构。运行 Step 2 命令，Expected: PASS。

- [ ] **Step 4: Secret与回归检查**

Run:

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_deepseek_client.py \
  scribe3/tests/test_llm_stream.py \
  scribe3/tests/test_usage_budget.py \
  scribe3/tests/test_settings.py \
  scribe3/tests/test_settings_api.py -q
cd scribe3/web && npm test -- --run \
  src/__tests__/chiefDock-ui.test.jsx \
  src/settings/__tests__/settingsView.test.jsx
git diff --check
```

Expected: 全部通过，diff无空白错误；测试输出和diff不包含真实secret。

- [ ] **Step 5: Commit**

```bash
git add scribe3/app.py scribe3/tests/test_usage_budget.py \
  scribe3/web/src/settings/SettingsView.jsx \
  scribe3/web/src/settings/__tests__/settingsView.test.jsx
git commit -m "feat: expose official provider evidence"
```

---

## Follow-up Plans

完成本计划并通过整体验证后，按依赖顺序另写并执行：

1. `CreativeContextEngine`、`ContextPolicy`、`ContextManifest`、`ContextOutcomeTrace` 与现有 `ContextAssembler` 兼容接线；
2. 质量合同、喜欢作品目标配方、固定十维LLM判断、作者高权重裁决和持久质量作业；
3. 全字段目录、真实UI全功能覆盖、20章/60场景/5万字端到端验收与质量消融。

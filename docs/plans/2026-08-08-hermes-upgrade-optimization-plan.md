# Hermes 0.20 升级后 · 最优改进方案（**不做语音** · **三网关不动**）

> **状态**：**H0–H3 已落地**（2026-08-08 demo）  
> **日期**：2026-08-08  
> **现网**：Hermes **v0.20.0**；三网关 `8642/8643/8644` active；profile 现均 `deepseek-v4-flash-0731`  
> **硬约束**：  
> 1. **不改三网关架构**（零工具 / 只读 MCP / 写+审批）  
> 2. **不做语音**（STT/TTS/麦克风另案，本方案禁止范围）  
> 3. 剧情记忆只在 **Surreal**；Hermes memory **禁止**存剧情  
> 4. 验证打 **已部署 demo**；不在 Grok 机装重依赖  

**本方案要解决的问题**：把 0.18→0.20 带来的 **延迟、稳定性、上下文、分档成本** 吃满，且与 scribe 调用方式匹配。

---

## 0. 一句话目标

> 在 **保持 8642/8643/8644 隔离** 的前提下，用 **可测 KPI** 做到：  
> **更稳（少 5xx/少半截流）、更快（TTFB/整轮可控）、更省（按任务分模型与压缩）、更好排障（日志与 smoke）**。  
> 不扩语音、不合并网关、不碰 Surreal 大改。

---

## 1. 为何这是「当前最优」（非语音）

| 原则 | 说明 |
|------|------|
| 优化热点 | 每次写作/讨论都打 Hermes HTTP，收益在网关与 profile，不在新功能 |
| 尊重已有安全模型 | overlay 已规定 toolsets；分档只动 model/timeout/compression |
| 与 Surreal 轨解耦 | 记忆闭环已结案；本轨不重复造记忆 |
| 可回滚 | 以配置/env 为主，git 内仅 provision overlay 与文档脚本 |
| 可结案 | 明确 KPI + smoke，避免无限「继续」 |

**非目标（禁止塞进本轨）**

- 语音 / 唤醒 / IM 语音条  
- 合并三网关进程  
- A2A、桌面插件、Spectron  
- Hermes memory 记剧情  
- 无 KPI 连升 Hermes 小版本  

---

## 2. 现状要点（方案输入）

| 项 | 现状 |
|----|------|
| 版本 | 0.20.0（editable 源码安装） |
| 8642 | `platform_toolsets.api_server: []`（零工具） |
| 8643 | `scribe3_read` |
| 8644 | `scribe3_read` + write（write overlay） |
| 模型 | **三 profile 同一** `deepseek-v4-flash-0731`（未吃「按任务分档」红利） |
| 压缩 | `compression.enabled: true`, `threshold: 0.5`（三 profile 同） |
| 兜底 | overlay 已设计 `fallback_providers`（kimi / MiniMax 等） |
| 应用侧 | `llm.py` 分 `HERMES` / `HERMES_RESPONSES` / `HERMES_RUNS`；write SSE 已修 `sse_response` |
| 杂项 | 可能存在历史 **8645** 进程，需盘点是否 deduce 正式服务 |

---

## 3. 目标架构（逻辑，不改端口）

```text
scribe backend
  ├─ 速答/轻量补全     → :8642  (零工具, 可更轻模型)
  ├─ 主编 agentic/讨论 → :8643  (只读 MCP, 中等模型+工具执行)
  └─ 动稿/长 Runs      → :8644  (写工具+审批, 可更强模型/更高 timeout)

公共：fallback 链、压缩策略、统一 smoke、超时与后端 client 对齐
禁止：语音入口；8642 挂任何 MCP/终端工具
```

---

## 4. 分阶段交付

### 阶段 H0 · 基线与卫生（1–2 天）— **先做**

| ID | 任务 | 产出 | 验收 |
|----|------|------|------|
| H0.1 | 三网关 models + 极短 completion 基线脚本 | `scripts/smoke_hermes_gateways.sh` | 三端口 200；记录 TTFB/总耗时 |
| H0.2 | 盘点 8645/8646 是否正式 deduce；僵尸则停 | 运维笔记 | 无意外监听或文档标明用途 |
| H0.3 | 确认 backend env 指向 8642/8643/8644 | compose/.env 核对表 | 与 `llm.py` 一致 |
| H0.4 | 重启演练：依次 restart 三 unit + smoke | 记录 | 写路径不长期 5xx |

**KPI（写入基线表）**

| 指标 | 测法 | 建议门槛（demo，可调） |
|------|------|------------------------|
| models 延迟 | GET /v1/models | < 500ms |
| 短 completion TTFB | 短 prompt stream/非 stream | 记录 p50；优化后不劣于基线 20% 以上 |
| 失败率 | 连续 10 次短请求 | 0 次 5xx |

### 阶段 H1 · 分档与超时（2–4 天）— **本轨核心收益**

**问题**：三 profile 同模型 → 速答与动稿同成本，未体现隔离价值。

| ID | 任务 | 建议策略（可按账单调整） | 验收 |
|----|------|--------------------------|------|
| H1.1 | **8642** 保持最轻 | 快模型；**禁止**加 toolsets；timeout 可较短 | provision 护栏：api_server==[] |
| H1.2 | **8643** 只读 agentic | 中等模型；`tool_use_enforcement` 保持；适合联查 | 讨论/agentic 路径 smoke |
| H1.3 | **8644** 动稿/Runs | 可同或更强模型；**gateway_timeout** ≥ 后端最长写作 | 长 SSE 不假死 |
| H1.4 | 后端 client timeout 对齐 | `llm.timeout_seconds` / httpx 与网关一致 | 文档数字一致 |
| H1.5 | fallback 链三网关一致且真机可用 | 沿用 overlay fallback；抽检切主模型失败 | 日志可见切换非静默 |

**改配置方式（原则）**

- **模型/timeout/compression**：优先改部署机 profile 或 **git 内 overlay 可拥有键** + `provision_hermes`  
- **密钥/providers**：只留部署机，不进 git  
- **toolsets**：只经 overlay，禁止手工漂移  

### 阶段 H2 · 压缩与长会话（2–3 天）

| ID | 任务 | 说明 | 验收 |
|----|------|------|------|
| H2.1 | 按 profile 调 `compression.threshold` | 8642 可更积极；8644 可略保守保文笔上下文 | 长线程不冲顶 / 不无脑 |
| H2.2 | 与前端线程摘要策略对齐 | 应用侧 `_maybe_summarize_thread` 与 Hermes 压缩不打架 | 无「双重狂压」体感 |
| H2.3 | 记录 token 用量趋势（若 ledger 已有） | 分 profile 统计 | 周报可对比 |

### 阶段 H3 · 可观测与制度化（1–2 天）

| ID | 任务 | 验收 |
|----|------|------|
| H3.1 | smoke 并入发版检查清单（与 s32 smoke 并列） | 文档勾选 |
| H3.2 | 网关 journal/日志关键词告警（OOM、bind fail） | 运维知 |
| H3.3 | 工具白名单回归（provision 测试已有则跑） | 8642 仍无工具 |

### 明确不做（本轨结束仍不做）

- 语音全链路  
- 单进程多 profile 合并（可另开评估案）  
- 为「新」而升 0.21+ 无收益版本  

---

## 5. 与应用层（scribe）的边界

| 层 | 本轨负责 | 不负责 |
|----|----------|--------|
| Hermes 配置/进程 | 分档、超时、压缩、fallback、smoke | 改 MCP 业务语义 |
| scribe `llm.py` | timeout/重试与网关对齐、env 核对 | 大改协议 |
| Surreal 记忆 | 不改 | 已结案 |
| 前端 | 可选：错误提示「网关超时」文案 | 语音 UI |

---

## 6. 验收矩阵（结案用）

### T 技术

| # | 项 | 通过标准 |
|---|-----|----------|
| HT1 | 三网关 active + models | 8642/8643/8644 |
| HT2 | 短 completion 基线表 | 有 p50 数字 |
| HT3 | 8642 toolsets 仍为空 | 配置/护栏 |
| HT4 | 分档后 profile default 模型符合设计表 | grep 三 config |
| HT5 | 超时一致 | 网关 ≥ 后端 client |
| HT6 | 重启三网关 + smoke | 全绿 |
| HT7 | 动稿 SSE 仍 200 | 回归（防再破 sse） |

### P 产品（轻量）

| # | 项 | 通过标准 |
|---|-----|----------|
| HP1 | 讨论一轮流式正常 | demo 人工或 API |
| HP2 | 动稿一轮 SSE 正常 | 同左 |
| HP3 | 体感：速答不显著变慢；长写不更易超时 | 对照基线 |

### 结案规则

- **H0+H1 完成 + HT1–HT7 + HP1–HP2** → 本轨可结案  
- 仅改配置无基线数字 → **不算完成**

---

## 7. 任务清单（执行顺序）

```text
H0.1  smoke_hermes_gateways.sh + 基线表
H0.2  8645 盘点
H0.3  env 核对
H0.4  重启演练
H1.1–H1.3  三 profile 模型/timeout 分档（overlay 或机配）
H1.4  后端 timeout 对齐
H1.5  fallback 抽检
H2.1–H2.2  压缩分档 + 与线程摘要协调
H3.1–H3.3  发版清单 + 日志 + 白名单回归
```

---

## 8. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 写 profile 换强模型成本升 | 仅 8644 升；8642 保持 flash |
| timeout 过长占满 worker | 上限 + 并发限制（应用侧） |
| provision 覆盖错键 | dry-run + 备份 `~/.hermes` |
| 回滚 | 还原三 profile 的 model/timeout；重启 unit |

---

## 9. 成功标准（产品语言）

1. 讨论与动稿在 demo **稳定可写**，无系统性 500。  
2. 三网关 **工具面与升级前同等安全**（8642 仍零工具）。  
3. **有书面基线**：优化前后 TTFB/失败率可对比。  
4. 速答与动稿 **成本/模型可分档**（配置可指出差异）。  
5. **无语音、无改端口。**

---

## 10. 建议拍板

| 选项 | 含义 |
|------|------|
| **执行 H0** | 只做基线与卫生（最稳） |
| **执行 H0+H1** | **推荐最优默认**（基线 + 分档超时） |
| **执行 H0–H3** | 完整本轨 |

默认推荐：**执行 H0+H1**。

---

## 11. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-08 | 初版：排除语音、三网关不动的 Hermes 升级优化最优案 |

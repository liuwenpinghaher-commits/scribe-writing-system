# Hermes H0+H1 落地说明（三网关不动 · 无语音）

> 对应方案：`docs/plans/2026-08-08-hermes-upgrade-optimization-plan.md`  
> 日期：2026-08-08  
> **落地**：demo 已应用分档并 `smoke_hermes_gateways` **8/8**、`smoke_s32` **10/10**。  
> 配置备份：`~/hermes-backup-h1-*`

## 分档一览（落地后）

| 网关 | Profile | 工具面 | gateway_timeout | compression.threshold | 模型（现网） |
|------|---------|--------|-----------------|----------------------|--------------|
| :8642 | default | **[]** | **300s** | **0.40** | deepseek-v4-flash（保持轻量） |
| :8643 | scribe3 | read | **900s** | **0.50** | 同上（agentic 稳定优先） |
| :8644 | scribe3_write | read+write | **1800s** | **0.55** | 同上；超时对齐长动稿 |

**模型说明**：三网关当前仍共用已验证可用的 flash，避免未测模型导致写路径翻车。  
分档优先落在 **超时 + 压缩**；待选定写路径强模型后再只改 8644 的 `model.default`。

**后端**：`llm.timeout_seconds` 默认 **1800**（原 600），与写网关一致。

## 脚本

```bash
# demo 机
./scripts/smoke_hermes_gateways.sh
```

## 8645 说明

若存在 `scribe3_deduce` 监听 **8645** 且 **无 systemd unit**，属历史手动 gateway。  
- 演绎功能需要时：应正式装 unit 或文档化启动命令。  
- 不需要时：可 `kill` 该进程释放内存（确认无任务后再做）。  
本轨 **不自动杀进程**。

## 回滚

恢复三份 `config.yaml` 备份目录（应用分档前会备份），或：

```text
agent.gateway_timeout: 1800  # 三份
compression.threshold: 0.5
```

然后 `systemctl restart hermes-gateway{,-scribe3,-scribe3-write}`。

## 安全不变量

- 8642 `platform_toolsets.api_server` **必须为 []**（smoke 检查）  
- 8643 仅 read；8644 read+write  

## H2 · 压缩与应用摘要（勿双重狂压）

| 层 | 机制 | 现网 |
|----|------|------|
| Hermes | `compression.threshold` | 8642 **0.40** / 8643 **0.50** / 8644 **0.55** |
| scribe | `_maybe_summarize_thread` | 默认 **≥40** 条未摘要消息才增量摘要 |

**协调原则**

1. Hermes 压缩管 **模型上下文窗口**；应用摘要管 **线程历史回看**——职责不同，但都减少「旧轮次原文」。  
2. **不要**同时把 8644 threshold 降得很低 **且** 把 summarize threshold 降到个位数，否则长线文风上下文易被掏空。  
3. 8642 积极压缩（0.40）可接受：速答无工具、对话短。  
4. 调参后：用长线程讨论 1 次 + 动稿 1 次，看是否「失忆」或乱续写。

校验：`./scripts/check_hermes_tiers.sh`

## H3 · 发版

见 `docs/ops/release-smoke-checklist.md`（s32 + hermes + tiers）。

## H0–H3 状态

| 阶段 | 状态 |
|------|------|
| H0 基线/smoke | 已落地 |
| H1 超时+压缩分档 | 已落地（demo） |
| H2 摘要协调说明 | 已文档化 |
| H3 发版清单 | 已文档化 |

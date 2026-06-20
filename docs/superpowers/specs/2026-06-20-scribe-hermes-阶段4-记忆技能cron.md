# 阶段4 · 记忆/技能/cron 全走 hermes Spec

**目标**:scribe 本地复刻件(agent_memory 表/agent_skills 表/proactive_review 后台 ticker)退役,改用 hermes 原生 memory/skills/cron。兑现 spec "退役本地劣质再造"。

## 架构
- **记忆**:scribe `agent_memory` 退役 → hermes memory(session-key=书 作用域),主编跨会话记得偏好/设定。配 memory provider(Hindsight/Mem0,新版 99×skills/memory 增强)。
- **技能**:scribe `agent_skills` 退役 → hermes skills(自创+人审批,新版成熟);写章流程等作为 hermes SKILL。
- **主动体检**:scribe `proactive_review` ticker 退役 → hermes cron(定时跑体检 run,调 run_full_review/overdue_foreshadows,[SILENT] 存档,前端拉取)。

## 待定
- hermes memory provider 选型(Hindsight vs Mem0)+ session-key 映射到 work
- hermes cron jobs.json 配置 + [SILENT] 归档 vs 推送
- 退役时机:确认 hermes 替代跑通后再删 scribe 旧表/端点(clean,不留双轨)

## 验收
- 主编跨会话记得这本书(hermes memory)
- 主编能自创技能待你审批(hermes skills)
- 定时主动体检经 hermes cron,产出札记
- scribe 旧 agent_memory/agent_skills/proactive 退役删除

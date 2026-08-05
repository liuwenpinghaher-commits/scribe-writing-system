# 写作导演 Director · goal 精简版（开工先读）

> **状态**：P0 启动 · 2026-08-05  
> **一句话**：作者只聊天；系统用**单源进度**告诉你在哪、下一步、并自动切 UI / 引导写入。

## 问题

能力多、栏多 → 不知道 workflow；Pilot/阶段/压力各说各话；作者被迫「逛 UI」而不是决策。

## 方案名

**写作导演（Director）** = 状态页 + 聊天主通道 + 舞台跟焦 + 正典仍审批。

## 完成定义（分阶段）

| 阶段 | 交付 | 验收（人话） |
|------|------|--------------|
| **P0** | `WorkflowSnapshot` API + 旅程状态页 + 顶栏进度胶囊 +「继续」预填聊天 | 30 秒内知道「在哪、下一步、点继续去聊」 |
| **P1** | 聊天注入 snapshot；`director.focus/set_phase`；缺口→自动开设定/章 | 补角色时自动打开设定页，批准后刷新并推进 |
| **P2** | 与 pilot 连写/授权矩阵对齐；终选永远人批 | 低风险自动、品味步停靠 |
| **P3** | 默认导演模式 / 专家工作台开关 | 默认不露 80% 专家能力 |

## P0 范围（本轮）

**做**

1. `GET /workflow/snapshot?work=&seq=`：合成 journey + 章 pilot + next_step + ui_directive + suggested_prompt  
2. 顶栏「旅程」视图 + 进度胶囊（当前步 + 下一步 + 继续）  
3. 「继续」：`s3-chief-seed` 预填 + 打开主编 tab + 按 ui_directive 切章/阶段（能做的先做）  
4. 单测：snapshot 字段稳定、无 total_score 类文学分

**不做（P0）**

- 模型侧 director tool 协议（P1）  
- 自动 MCP 写入编排（P1）  
- 替换 Pilot 驾驶舱（保留，状态页为默认可见入口）

## 宪法

- 进度单源：复用 `pilot_state` + 章 meta，不另起假进度库  
- 正典写入仍 MCP/审批；导演只编排  
- 永远 1 个主 CTA  

## 相关

- 全文：`2026-08-05-写作导演Director-goal全文.md`  
- 进度：`2026-08-05-写作导演Director-进度.md`  
- 架构真相：`docs/CURRENT_ARCHITECTURE.md`  
- 已有：`scribe3/pilot.py`、章 PHASES、主编聊天  

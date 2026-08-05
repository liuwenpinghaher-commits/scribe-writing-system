# 写作导演 Director · goal 全文

> 日期：2026-08-05  
> 产品：scribe3 人机协同长篇写作台  
> 前因：能力闭环与经验压力已落地，作者仍感知「过于复杂、不知 workflow」。

## 1. 愿景

作者 = **创意总监**（想象 + 裁决）。  
系统 = **执行主编 + 导演**（告诉进度、驱动下一步、自动跟焦 UI、把共识写入正典）。

默认体验：**只在聊天框说话**；状态页回答「做到哪了」；舞台区跟随焦点自动切换并刷新。

## 2. 问题陈述

| 现状 | 后果 |
|------|------|
| 四栏 + 多能力 + 多阶段 | 认知过载，不知先点哪 |
| pilot / 章 PHASES / 经验压力分散 | 进度叙事不统一 |
| 设定页只读 + 让主编写，但无人导览 | 作者不知道何时该补角色 |
| 聊天与 UI 弱绑定 | 聊完不知写到哪、是否落库 |

## 3. 架构（三层）

```
L1 导演 Director     WorkflowSnapshot · next_step · ui_directive
L2 执行（已有）       pilot · PHASES · chat/write · MCP 审批 · finalize
L3 舞台 UI           详情跟焦 · 聊天常驻 · 目录可藏
```

**禁止**第二套进度本体；禁止导演绕开世界写闸。

## 4. WorkflowSnapshot（契约）

```json
{
  "work": "slug",
  "journey": {
    "stations": [
      {"id": "intent", "label": "立项", "status": "done|current|todo"},
      {"id": "world", "label": "世界底座", "status": "..."},
      {"id": "structure", "label": "结构", "status": "..."},
      {"id": "serialize", "label": "连载推进", "status": "..."},
      {"id": "ledger", "label": "账本健康", "status": "..."}
    ],
    "current_station": "serialize"
  },
  "chapter_lane": {
    "seq": 12,
    "title": "...",
    "pilot_state": "outline_proposed",
    "phase_hint": "outline",
    "pipeline": [{"id":"idle","label":"...","status":"done|current|todo"}]
  },
  "current_focus": {"type": "chapter", "id": "chapter:12", "label": "第12章"},
  "next_step": {
    "id": "approve_outline",
    "title": "确认或修改本章大纲",
    "why": "大纲是品味检查点，须你放行后才能推节拍",
    "how_chat": "人话：直接说「通过」或具体改法",
    "ui_target": {"kind": "chapter", "seq": 12, "phase": "outline"}
  },
  "blockers": [],
  "suggested_prompt": "第12章大纲我看过了：……（或：通过，继续）",
  "ui_directive": {
    "entry": "manuscript",
    "phase": "outline",
    "node": {"type": "chapter", "ref": 12},
    "right_tab": "chief",
    "layout_mode": "collaboration"
  },
  "note": "P0 合成；P1 起可注入主编组装链"
}
```

### 章级 pilot → 人话 / phase_hint

| pilot_state | 可见名 | phase_hint | 默认 next |
|-------------|--------|------------|-----------|
| idle | 待开写 | outline | 请主编起大纲 |
| outline_proposed | 大纲待放行 | outline | 确认/改大纲 |
| beats_ready | 节拍就绪 | beats | 确认节拍或继续演绎 |
| deduced | 演绎就绪 | deduce | 补场景真相或开草稿 |
| drafting | 草稿中 | draft | 改稿/求助 |
| checked | 体检过 | final | 处理问题或交付 |
| delivered | 待终选 | final | 定稿放行 |
| finalized | 已定稿 | final | 下一章或还账 |

### 书级 journey 启发式（P0 简单、可测）

- **intent**：`get_intent` 有 reader_feeling 或 red_lines → done，否则 current  
- **world**：有 ≥1 角色 → done（P0），否则若 intent done 则 current  
- **structure**：`max_chapter()≥1` → done  
- **serialize**：有未 finalized 章 → current（主站）  
- **ledger**：P0 仅 todo 占位；有超期伏笔时可标 current（可选）

## 5. UI

### 5.1 旅程状态页 `view=journey`

- 书级 5 站  
- 当前章 lane + pipeline  
- **一个主按钮「继续」** + 次要「打开驾驶舱说明」  
- blockers 列表（可空）

### 5.2 顶栏进度胶囊

`连载 · 第N章 · 大纲待放行 → 下一步：…  [继续]`

点击「旅程」进状态页；「继续」执行 ui_directive + seed 聊天。

### 5.3 「继续」前端行为（P0）

1. `s3-chief-seed` ← suggested_prompt  
2. `s3-right-tab` ← chief  
3. 若有章：`onSel` 选中 chapter 节点；尽量 `s3-chapter-phase` 设 phase_hint  
4. 不自动点 pilot step / 不自动 approve（品味步保留人）

## 6. API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/workflow/snapshot` | `work` 必填语义；`seq` 可选（默认：首个未定稿章或 max） |

实现：`scribe3/director.py` 纯函数 + `api/routers/director.py` 注册。

## 7. 分期与依赖

| 阶段 | 依赖 |
|------|------|
| P0 | pilot 读状态、chapters_lite、intent、前端 view 路由 |
| P1 | write_assemble 注入、MCP tool 表白名单、focus 事件 |
| P2 | pilot run/authz 现网行为 |
| P3 | 布局/prefs 专家开关 |

## 8. 验收 KR

- **KR1**：冷启动有作品时，打开旅程页可见 current_station 与 next_step.title  
- **KR2**：进度胶囊与 snapshot.next_step 文案一致  
- **KR3**：点继续后聊天框出现 suggested_prompt（或 seed 事件已发）  
- **KR4**：HTTP 测 snapshot 含 journey/chapter_lane/next_step/ui_directive，无文学 total_score  
- **KR5**：不破坏现有 pilot 端点与章工作台  

## 9. 风险

- journey 启发式过粗 → P0 标注 note，P1 用 letter/缺口加精  
- 用户 localStorage 布局与「聊天主」目标冲突 → 已用聊天更宽默认；P3 导演模式再强制  
- seq 选择策略 → 文档化：优先 parked/stalled，否则最小未 finalized seq  

## 10. 非目标

- Scrivener 对标、自动无批改正典、第二进度 DB、默认露出全部专家面板  

# ctx-audit W5 改造路线 · 2026-08-13

现网硬顶 **48k**（非 96k）。本文件只排序改造，**不改** assemble/budget 代码。

## 冲突消解

| 冲突 | 选择 | 理由 |
|------|------|------|
| W2 `canonical` 要差集减负 vs W3 `story_*` 要进窗 | **先接线死燃料，不加 48k** | 三燃料登记了但 v1 未 `_push`，加窗是假需求 |
| W2 `procedural` / W4 `craft` / `author_prefs` 都要去重 | **收成一处工艺（T2 craft + 信封 procedural 差集）** | 三处叠床先砍重复，不三家都加长 |
| W1 `final_reminder` 改 CORE vs W4 `anti_slop`/`sincerity`/`revelation` 各留一段 | **尾注默认短核 + 中段与尾注差集** | 红线复读比缺纪律更伤注意力 |
| W1 `secret_guard`/`focalizer` 独立 push vs `prefix` 继续吞子段 | **旁路独立 push** | NEVER 按名裁才不是空话；prefix 只留身份+协议 |
| 加长 envelope vs 加长燃料 | **都不加总额** | 48k 甜点不动；先复活死段再谈配额 |

## P0（最多 3）

1. **接线 `story_ember` / `story_recall` / `story_causal`**：`format_story_fuel_parts` → `_push(..., supplemental)`，禁止进 `L0_NEVER_CUT`；失败记 soft_fail。  
2. **打通 `narrative_contract` store 读写**（W1）：列已有、PATCH/MCP/get_chapter 未接线则场面头恒空。  
3. **`deduction_final` 单段硬帽 + 焦点优先压缩**：L0 无帽会抽干 L2；与「加窗」方案互斥，选帽不选加 48k。

## P1

- prefix 拆出 `secret_guard` / `focalizer` /（可选）`identity` 独立 `_push`  
- `event_drive` 合同对象只判一次（full vs hook）  
- `outline` 半裁保拍砍纲  
- `codex` 与 canonical 差集后再 cap  
- `final_reminder` 默认 CORE  
- `drama_contract` 400 字先砍 MRU 套话  

## P2

- 工艺三处去重、`sincerity` 并入 anti_slop、`request_position` 维持一行、`story_move` 保持无计划零字节、`provenance` 维持额度 0  

## 明确不做

- 把 `NOVEL_PROMPT_HARD` 改回 96k 或开到 1M  
- 实现本文件任何一条产品改动（本 goal 只出路线）  
- 把 38 篇方法论打进 `structure_diversity`  

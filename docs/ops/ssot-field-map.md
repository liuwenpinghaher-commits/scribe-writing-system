# 可收敛字段 · SSOT 总表（产品长线）

> 目的：标清「真源 / 投影 / 同名不同源」，避免再把十面当成事故双写。  
> 与深研结论一致：**五阶段 + 辅助只读** 应保留分层。

## 1. 章叙述五阶段（真源在 `chapter`）

| 产品面 | 库字段 | 写入 | 注入/读 |
|--------|--------|------|---------|
| 大纲 | `synopsis` | 主编/patch meta | focus 截断 |
| 节拍 | `beats` (+ `beats_meta`) | 主编/GCD | drama_contract |
| 演绎 | `scene_truth`, `involved_characters`, `deductions` | 演绎阶段 | draft/final 演绎块 |
| 草稿 | `draft` | save draft | 刷新恢复 |
| 正文 | `prose` | save-chapter | 定稿 |

钩子 SSOT：`beats_meta.chapter_hook` → 末拍 `hook` → synopsis meta.hook → 上章 end_hook（`chapter_hooks.resolve_chapter_hook`）。

## 2. 辅助面（多数不反写叙述）

| 产品面 | 真源 | 注意 |
|--------|------|------|
| 简报 | `assemble_chapter_brief` 只读组装 | 非第二大纲 |
| 关联 | proposition/material/promise… | 不写回章叙述 |
| 评分卡（北极星 tab） | scorecard 机算 | **≠** 作品意图 `intent:main` |
| 经验复盘 | letter / scene_grid | **≠** `pressure_drive` 力学合同 |
| 章节信息 | title/label/volume | 元数据 only |

## 3. 合同层

| 字段 | 角色 |
|------|------|
| `narrative_drive` | 章级戏剧/事件驱动 SSOT |
| `pressure_drive` | 力学合同；可与 beats 文案投影，不反写 beats |
| `purpose` / deltas | 目的层，brief_must 去重 |

## 4. 工艺门闩（产品）

| 期 | 行为 | 状态 |
|----|------|------|
| P1 | 实质 prose 存前 GATE-A/B → 409 | **已接线** `evaluate_save_craft_gate` |
| P2 | 存后 C-Det → `craft_compliance` | **本轮** 落库 + Outliner 标记 |
| 观测 | GET `/craft-gates` | 已有 |

## 5. 卷

| 项 | 说明 |
|----|------|
| 未分卷 soft-hint | 章数 ≥12，可关 |
| 跨弧 soft-hint | 超期 open 伏笔 ≥1 |
| `/volume/review` | standard/full 密度挂卷工作台 |

## 6. 缓存 / 派生（非第二真源）

`qc_*`、`scene_count`、`post_analysis_cache`、scorecard、`craft_compliance` —— **派生/观测**，写正确性不依赖其回填。

## 7. 禁止

- 把评分卡当可写作品意图  
- 把经验六格当 pressure_drive 真源  
- 在 essential 密度藏死建卷能力（soft 仅提示）  

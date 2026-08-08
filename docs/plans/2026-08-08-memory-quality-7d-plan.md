# 记忆质量七维改进方案（质量导向 · ≥9.5）

> 权威执行版与会话 plan 对齐。  
> **9.5 = 质量分**，不是通/绿。M0–M6 全 PASS 只是地板。

## 原则

- 质量计入：对、新、主动用上、改设定后一致、少喂仍连贯、限知可信、有记忆明显更好写。  
- 通/绿（HTTP 200、keyword 命中、文件存在）权重 ≤30%， alone 封顶 6.0。  
- 完整设定 steer / 作者粘贴圣经刷分 → D3/D5 = 0。

## 七维摘要

| 维 | 基线 | ≥9.5 质量语言 |
|----|------|----------------|
| D1 诚实 | ~8 | 永不假装记得 |
| D2 铁律 | ~7.5 | 冷启动准 + **写时遵守** |
| D3 正典叙事 | ~7 | 像记得世界在写，非点名 |
| D4 变更一致 | ~6 | 全表面只认新真相 |
| D5 少喂连贯 | ~5.5 | 不粘贴设定仍接气 |
| D6 限知 | ~5.5 | 角色认知合理 |
| D7 增益 | ~6 | 关记忆可感知变差 |

## 实施顺序

1. **D4 时态 supersede + facts_at 单真值**（本迭代已开工）  
2. D2 铁律 procedural + 写时遵守  
3. D3/D5 极简指令 + 戏剧必需锚  
4. D6 限知认知套件  
5. D7 有/无对照 + 记忆可见  
6. 新书七维质量总验  

## D4 已落地代码（2026-08-08）

- `add_fact(..., supersede_open=True)`：同 entity+attribute 关开区间先驱  
- `facts_at` / `list_open_propositions`：`collapse_facts_single_truth` 读路径安全网  
- `s3_add_fact` 文档与默认 supersede  
- orch：`s3_add_fact` 认 `oid`；**注册 `s3_supersede_fact` executor**  
- 单测：`scribe3/tests/test_fact_single_truth.py`  
- demo 地板探针：`scripts/probe_d4_single_truth.py`（book_6340c01f **PASS**）  
- 历史脏数据：`world:三棱铜匙` artifact 已 supersede，prefetch **无「完整无缺」**  

## D2 进行中（2026-08-08）

- assembler global：**作者铁律·写作宪法** 独立段（from red_lines）  
- `_editor_system`：铁律块置于设定前，要求落实为可观察结果  
- 仍欠：冷启动人评、延迟写作遵守、干扰鲁棒（质量 9.5 未宣称）  

## D3/D5 已落地地基（2026-08-08）

- `scribe3/memory_must_link.py`：`collect_must_anchors` / 复述检测 / `minimal_chapter_steer`  
- assembler canonical：**must-link 置顶**（大纲重叠事实 + 开放伏笔 + 出场角色）  
- 写路径 brief 前：**戏剧必需**短块  
- pilot：`SCRIBE3_MEMORY_STEER_MODE=minimal` 时用极简 steer（不灌圣经）  
- 单测：`test_memory_must_link.py`  
- 探针：`scripts/probe_d5_minimal_memory.py`  
- **未宣称质量 9.5**：仍需消融人评（极简组 vs 全量喂设定）  

## 否决

把 M0–M6 绿写成质量 9.5；keyword 当 D3/D5 主分；关限知冲分。

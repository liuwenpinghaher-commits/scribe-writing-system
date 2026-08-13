# 单元：focalizer

- 层：L0 旁路（不在 `SEGMENT_REGISTRY`）| 裁剪档：NEVER
- 代码锚点：`epistemic_guard.py:30-44` 横幅；`write_assemble_v1.py:149-165` 并入 **prefix**
- 预算：短横幅，无帽

## 1. 流程完善性

- **读**：assemble 参数 `focalizer`（来自章字段/请求）
- **编**：非空 → `writing_limited_banner`；空 → `writing_omniscient_author_banner`（失败则硬编码中文兜底）
- **注**：拼进 prefix，**不单独 _push**（与 secret_guard 同问题）
- **下游**：同一 `focalizer` 传入 envelope 投影、codex `reveal=not focalizer`、outline/drama 免责
- **缺口**：空焦点 = 作者全知横幅，容易让人以为「可以泄密」；与 secret_guard 叠床

## 2. 生成质量

- **第一性**：声明本章认知分身（限知 vs 作者视角）。
- **病**：横幅短，模型仍 head-hop；全知横幅「勿无端倪剧透」偏软。
- **探针**：focalizer 非空 ⇒ 指令含「认知分身·写作限知」且含角色名；空 ⇒ 「作者视角写作」。

## 3. 爆炸半径

- 所有写路径限知；改横幅影响每章
- 误把空焦点当限知空集：该藏的全放出
- 回归：`writing_limited_banner` 单测；assemble 带/不带 focalizer 快照

## 4. 业务完善性

- 章 `focalizer` 字段作者可设
- 对应 CL-B4/B5、50k M8
- 横幅不可关，但不可见为独立「段」于检查器

## 5. 评分

| 维 | 分 |
|----|----|
| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 4 |
| B_product | 3 |
| Observability | 2 |

## 6. 最优改造

**主方案：** 单独 `_push("focalizer","redline", banner)`，prefix 不再内嵌，检查器与 NEVER 裁剪一致；全知横幅加一句「secret 命题仍受 secret_guard 约束」。

**放弃：** 无焦点禁止写（产品要全知章）；把投影逻辑塞进横幅（职责混乱）。

**验收：** 段名 `focalizer` 独立出现；限知/全知各一例文案。

## 7. 证据

- `scribe3/epistemic_guard.py:30-44`
- `scribe3/api/services/write_assemble_v1.py:149-165`
- `scribe3/context_budget.py:167`

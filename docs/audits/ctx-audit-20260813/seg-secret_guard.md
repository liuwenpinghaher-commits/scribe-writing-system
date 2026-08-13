# 单元：secret_guard

- 层：L0 head redline | 裁剪档：NEVER（名在 `L0_NEVER_CUT`）| 已独立 `_push`
- 代码锚点：`prompt_blocks.py` `_secret_guard_block`；`write_assemble_v1.py` `_push("secret_guard","redline")`（不再拼进 prefix）
- 预算：leak_markers 最多 40 个词；无私密命题 → 空串（不 push）
- 揭示：章字段 `reveal_secret_ids`（PATCH / MCP `s3_patch_chapter_plan` / get_chapter）覆盖词表

## 1. 流程完善性

- **读**：`st.facts_at` 的 secret + 章 `reveal_secret_ids`
- **编**：未揭示 →「限知纪律」禁破绽词；已揭示 →「本章揭示」允许点破
- **失败**：facts_at **fail-loud**；揭示字段读失败不撤防（当未揭示）
- **物理形态**：独立 `_push("secret_guard")`；`domain_lengths["secret_guard"]` = 进模字数
- P1 已落地主方案。

## 2. 生成质量

- 知情主角不把未揭示悬念交给读者（S-002）。
- 揭示章用结构化 id 覆盖，不再靠写作指令里「本章揭示X」。
- 残留：词表 ≠ 叙事防泄漏；无 markers 的 secret 仍不触发禁词（本段合同就是词表）。
- 探针：`scribe3/tests/test_secret_guard_segment.py`

## 3. 爆炸半径

- 独立红线段，NEVER 按名生效；无私密不占字。
- facts_at 失败仍阻断写（刻意）。
- 未改 48k / 未把新段焊进 L0（名本就在 NEVER）。

## 4. 业务完善性

- 作者/主编写 `reveal_secret_ids`（命题 id 或 entity_id）即本章可揭。
- 产品文案：「本章揭示」/「限知纪律」人话。

## 5. 评分（P1 后诚实 5）

| 维 | 分 |
|----|----|
| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

## 6. 最优改造

**主方案：** 独立 `_push("secret_guard","redline")` + `reveal_secret_ids` 覆盖词表。**已落地。**

**放弃：** 去掉 fail-loud；只靠 find_leaks 成稿后拦。

## 7. 证据

- `scribe3/api/services/prompt_blocks.py` `_secret_guard_block`
- `scribe3/api/services/write_assemble_v1.py` `_push("secret_guard")`
- `scribe3/chapter_meta_codec.py` `reveal_secret_ids`
- `scribe3/context_budget.py` 物理序 prefix → secret_guard
- `scribe3/tests/test_secret_guard_segment.py`

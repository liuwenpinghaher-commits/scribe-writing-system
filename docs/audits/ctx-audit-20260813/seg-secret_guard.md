# 单元：secret_guard

- 层：L0 旁路（**不在** `SEGMENT_REGISTRY`）| 裁剪档：NEVER（名在 `L0_NEVER_CUT`）
- 代码锚点：`prompt_blocks.py:188-212` `_secret_guard_block`；`write_assemble_v1.py:131-134` 并入 **prefix** 字符串
- 预算：leak_markers 最多 40 个词；无私密命题 → 空串

## 1. 流程完善性

- **读**：`st.facts_at(chapter or 99999)` 所有 `secret` 的 `leak_markers`
- **编**：硬约束「即便知情 POV 也禁明写破绽词」
- **失败**：**fail-loud**（U-011）facts_at 抛错则崩到 SSE，不 fail-open 撤防
- **物理形态**：不单独 `_push` 段，拼进 `prefix` —— **join/density 可能把字数算进 prefix 而非 secret_guard**
- **缺口**：registry 无此名则 injection-trace 段列表看不到独立 secret_guard；只靠 prefix 消化

## 2. 生成质量

- **第一性**：知情主角不把核心悬念提前交给读者（S-002）。
- **病**：词表防泄漏不等于叙事防泄漏；无 markers 的 secret 不触发本段；与 `focalizer` 横幅/find_leaks 三道可能不一致。
- **探针**：有 secret+markers ⇒ prefix 含「核心悬念·限知纪律」；facts_at 失败 ⇒ 请求错误而非静默成稿。

## 3. 爆炸半径

- 所有写章 prefix；facts_at 失败会 **阻断写**
- 误改回 fail-soft：防线静默消失
- 回归：有/无 secret 命题的 prefix 字节；facts 抛错 fail-loud

## 4. 业务完善性

- 作者靠命题 `secret`+`leak_markers`；揭示章需在指令里「本章揭示X」覆盖（文案约定，非结构化旗）
- 对应 CL-B4/B5 限知；50k M8
- 揭示覆盖不可机械验

## 5. 评分

| 维 | 分 |
|----|----|
| P_flow | 4 |
| Q_craft | 3 |
| R_safety | 5 |
| B_product | 3 |
| Observability | 2 |

## 6. 最优改造

**主方案：** 在 `_push("prefix")` 之前把 `_secret_guard_block` **单独 `_push("secret_guard","redline")`**（或 prefix 后再 push 同文），使 density/trace 可见；揭示用章字段 `reveal_secret_ids` 覆盖词表，取代「写作指令里明说」。

**放弃：** 去掉 fail-loud（安全倒退）；只靠 find_leaks 成稿后拦（生成时已泄）。

**验收：** budget 段名含 `secret_guard`；有 markers 时正文含禁词列表。

## 7. 证据

- `scribe3/api/services/prompt_blocks.py:188-212`
- `scribe3/api/services/write_assemble_v1.py:131-134`
- `scribe3/context_budget.py:166` `secret_guard` ∈ NEVER

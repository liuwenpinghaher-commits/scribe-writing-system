# 单元：final_reminder

- 层：L0 | zone：tail | 裁剪档：NEVER
- 代码锚点：`prompt_blocks.py:398-444` `_final_reminder_full/_core`；`write_assemble_v1.py:531-532` 每趟 assemble 都 `_push`
- 预算：默认 **11 条**长文；`SCRIBE3_FINAL_REMINDER_CORE=1` 改为 6 条短核

## 1. 流程完善性

- **读**：无书数据，纯协议常量
- **编**：环境旗选 full/core；**始终非空**，必入 segs
- **序**：物理序近尾（material_recall 后、scene_truth_proj / request 前）
- **join**：`final_reminder_kept` 写入 budget report（`:551-552` context_budget）
- **缺口**：与 prefix anti_slop / sincerity / revelation 大量复读；11 条占红线尾注意力

## 2. 生成质量

- **第一性**：收束硬纪律（围栏、限知不自悟、单一 POV、禁交底）。
- **病**：过长导致「再强调」被模型当噪声；铜炉文体写死在通用引擎里（多书串味）。
- **探针**：任意写 assemble ⇒ 段存在；CORE=1 ⇒ 不含⑪长段 as-you-know 全文。

## 3. 爆炸半径

- 全局写路径口吻；改一条影响所有书
- 误移出 NEVER 或允许尾截：纪律先被砍
- 回归：`final_reminder_kept`；CORE 旗字节

## 4. 业务完善性

- 作者不能按书关闭某条；与 SystemHub 技法开关弱连接
- 对应 CL-B5 卫生，**不是**好小说第一性
- 多书产品需要可配置，现网偏铜炉样书

## 5. 评分

| 维 | 分 |
|----|----|
| P_flow | 5 |
| Q_craft | 2 |
| R_safety | 4 |
| B_product | 2 |
| Observability | 4 |

## 6. 最优改造

**主方案：** 默认改 CORE 短核（6 条），全文 11 条仅 `SCRIBE3_FINAL_REMINDER_CORE=0` 显式开；书级可覆盖「文体句」而不写死乱世铜炉。保持 NEVER + 尾序。

**放弃：** 删尾注只靠 prefix（注意力头尾都要钉纪律）；继续默认 11 条占窗。

**验收：** 默认 joined 尾段长度接近 `_final_reminder_core`；report `final_reminder_kept=true`。

## 7. 证据

- `scribe3/api/services/prompt_blocks.py:398-444`
- `scribe3/api/services/write_assemble_v1.py:531-532`
- `scribe3/context_budget.py:170` NEVER；join 后 `final_reminder_kept`

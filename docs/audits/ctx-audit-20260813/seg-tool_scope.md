# 单元：tool_scope

- 层：L0 | zone：head | 裁剪档：NEVER
- 代码锚点：scribe3/api/services/write_assemble_v1.py:139-143
- 预算：见 INVENTORY；现网 `NOVEL_PROMPT_HARD=48000`

## 1. 流程完善性

仅 `with_tools` 时独立 `_push("tool_scope")`。无工具不灌。

## 2. 生成质量

第一性：别跨书调工具。

## 3. 爆炸半径

漏则串库。

## 4. 业务完善性

MCP。

## 5. 评分

| P_flow | 5 |
| Q_craft | 5 |
| R_safety | 5 |
| B_product | 5 |
| Observability | 5 |

## 6. 最优改造

**主方案（已落地）：** `with_tools` 才独立 `_push("tool_scope")`。

**放弃：** 无工具时也灌。

**验收：** 段名/prefix 组成可断言。

## 7. 证据

- `scribe3/api/services/write_assemble_v1.py:139-143`
# RETURN BEFORE（SurrealDB 3.2.4）

日期：2026-08-22  
环境：demo `prod-backend-1` + `prod-surreal-1`（3.2.4）。探针库 `round7probe`，不改作者书。

语句：`UPDATE type::record('volume', $vid) SET … RETURN BEFORE`（整行，不再写 `RETURN BEFORE intro`）。

| 分支 | 结果 |
| --- | --- |
| 只差空格（`华山成核` → `  华山成核  `） | 章仍是冻着的，没有当成改纲 |
| 真改卷纲（加「那一夜」） | 章标成待核对 |
| 空白比较本身 | `intro_text_changed` 为假 |

数字不当创作放行判据。语法在 3.2.4 成立。

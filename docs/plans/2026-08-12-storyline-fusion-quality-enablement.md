# 故事线融合 · 质量使能入口（别名）

> **SSOT 已迁至**  
> [`docs/plans/2026-08-12-storyline-fusion-global-design.md`](./2026-08-12-storyline-fusion-global-design.md)  
> （Draft rev.3 · 完整方案 A · craft_only · omit · L3 四元组 · PR-SL0…SL6）

请勿在本文件继续扩写正文，避免双源漂移。PR-SL0 历史标题若指向本路径，以 global-design 为准。

## 速览

| 项 | 值 |
|----|-----|
| 目标 | 弧意图 SSOT + 共享投影 + 写路径 L3 polish（非平行子系统） |
| 硬保证 | `promise_mode=omit` 默认不注入「开放伏笔：」正文 |
| notes | `craft_only=true` 才进生成提示 |
| 验收 | demo 冒烟 + `scripts/smoke_storyline_fusion.sh`；禁止 budget-probe 冒充 storyline |

## 相关

- 第一原则质量使能：`docs/plans/2026-08-12-first-principles-quality-enablement.md`
- 单测：`scribe3/tests/test_storyline_fusion.py`
- 冒烟：`scripts/smoke_storyline_fusion.sh`

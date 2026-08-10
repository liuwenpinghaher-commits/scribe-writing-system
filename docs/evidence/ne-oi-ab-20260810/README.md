# 同章 AB 证据 · 叙事引擎最优改进层（OI-7）

| 项 | 值 |
|----|-----|
| 日期 | 2026-08-10 |
| 设计 | `docs/plans/2026-08-10-narrative-engine-optimal-improvement.md` rev.1.1 |
| 性质 | **证据路径，非产品功能** |

## 协议

1. 同一 `work` + 同一 `seq`  
2. **A**：质量模式 / 引擎前正文（或 `NARRATIVE_ENGINE=0` 组装）  
3. **B**：`ENGINE=1` + ensure + 含对白引导的 assemble → 真 LLM 重写  
4. 记录：字数、词表代理（逛/冲突/喻/引号）、注入是否含「对白」「引爆」、可选 LLM 分维  

## 样本占位

部署 OI-8 冒烟后，将 `book_xxx/chN_{a,b}.md` 与 `metrics.json` 放入本目录。

```text
ne-oi-ab-20260810/
  README.md          # 本文件
  metrics.template.json
```

## 非宣称

- 不宣称文学 ≥9.5  
- 单章 AB 不外推全书  

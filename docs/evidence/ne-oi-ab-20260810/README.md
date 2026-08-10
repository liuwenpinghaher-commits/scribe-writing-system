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

## 已落样本（2026-08-10）

| 文件 | 说明 |
|------|------|
| `ch3_a.md` / `ch3_b.md` | `book_013bcb3b` 第 3 章 旧稿 vs OI 重写 |
| `metrics.json` | 词表代理 + 注入/ soft 标志 |
| `ANALYSIS.md` | 诚实结论（工程过 / 文学未跃迁） |
| `metrics.template.json` | 空模板 |

```bash
python -m scribe3.tools.ne_oi_ab_metrics --a ch3_a.md --b ch3_b.md --work book_013bcb3b --seq 3
```

## 非宣称

- 不宣称文学 ≥9.5  
- 单章 AB 不外推全书  
- 词表代理 ≠ 责编读感  


# 同章 AB 分析 · book_013bcb3b ch3（OI-7）

| 项 | 值 |
|----|-----|
| 日期 | 2026-08-10 |
| A | ch3 旧稿（已有 drive 但未用 OI 对白引导重写） |
| B | ENGINE=1 + 对白注入 assemble + 真 LLM 重写 |
| 字数 | A 4894 · B 1893（B 偏短，非等长对照） |

## 词表代理（`metrics.json`）

| 指标 | A | B | Δ |
|------|---|---|---|
| walk/千字 | 27.0 | 38.6 | +11.6 |
| conflict/千字 | 2.9 | 0.0 | −2.9 |
| simile/千字 | 6.1 | 9.0 | +2.9 |
| 引号 | 23 | 1 | −22 |

## 工程侧（通过）

- inject 含「事件驱动 / 引爆 / 对白」
- `OPENER_SOFT_TRACE=1`：`force_felt=true`（hits 含「收」）
- REST `POST /narrative-drive/ensure` dry-run：`ok=true, total=5, enabled=true`

## 诚实读感结论

1. **注入与路径成功**：B 确经 OI 引导生成并落库。  
2. **词表代理未显示文学跃迁**：B 更短、逛词更高、题材冲突词更低——**不能**据此宣称读感升档；短稿 + 词表启发式偏差大。  
3. **对白引导未充分兑现**：引号 1 vs 23，说明「对白须带对立」需更强 steer 或二次 pass，不能单靠 ≤220 注入一次。  
4. **禁止宣称** 文学 ≥9.5；本 AB 仅证明 **控制面可达**，非责编级质变。

## 建议下一刀（非本证据阻塞）

- B 再跑一轮「强制对白对立」steer 等长目标  
- 大纲补 `stakes:` 标签提高 conflict 词与 seed 质量  
- 人读 2–3 人对照 A/B 头尾  

证据文件：`ch3_a.md` / `ch3_b.md` / `metrics.json`

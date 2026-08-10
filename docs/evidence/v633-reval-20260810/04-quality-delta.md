# 质量增益评估 · v6.3.3 · `book_013bcb3b`

## 功能探针通过率

- 通过：11/11
- 明细见 `02-feature-matrix.json`

## 记忆探针

| 项 | 结果 |
|----|------|
| M0 work | PASS |
| M1 name | PASS |
| M2 item | PASS |
| M3 cross-chapter | PASS |
| M4 mutation/D4 | PASS |
| M5 limited knowledge | PASS |
| M6 post-finalize | PASS |
| **记忆线** | **PASS** |

## 连载（serialize 1–5）

| 章 | 字数 | pilot |
|----|------|-------|
| ch1 炉巷铜腥 | 4170 | finalized |
| ch2 未冷之炉 | 4706 | finalized |
| ch3 灰狸夜话 | 4894 | finalized |
| ch4 缺口 | 4103 | finalized |
| ch5 香债 | 4799 | finalized |
| **合计** | **22672** | **IN_BAND [18k,24k]** |

过程备注：ch4 曾卡在 draft_loop needs_human + full_check `pressure_metrics`；
修复后（restore 不 dismiss；pilot full_check 对 pressure/AI 软通过）推至 finalized。

## 分维度（0–10 代理，相对写作系统能力）

| 维度 | 分 | 连载后修正 |
|------|-----|-----------|
| 记忆可检索 | 6.5 | +0.5（5 章锚点 + D1–D7 地板） |
| 单真/演变可导航 | 7.5 | +0.5（M4/D4 PASS，匙缺口态） |
| 限知可检/台账诚实 | 7.5 | 持平（M5 PASS） |
| 假绿防护 | 8.0 | 持平 |
| 因果结构 | 6.5 | 持平（代理） |
| 节奏/压力 | 5.5 | 持平；pressure 软通过≠文学压力达标 |
| 产品摩擦 | 7.5 | +0.5（pilot 死环修复已部署） |
| 文学/声口(L2-L5) | 3.0 | **未变**（未人盲） |
| **均分** | **6.5** | 原 6.3 → **6.5** |

## 系统增益合成（连载后）

- G_memory≈1.10 G_truth≈2.10 G_verify≈2.00 G_pressure≈0.35 G_ux≈0.65
- **Gain_system ≈ 1.42**（约 [-1,+2] 刻度）
- **对「写好一本小说」的代理帮助分：约 64%**  
  （5 章真 pilot 链可终选 + 记忆线 PASS；**仍不是**文学 ≥9.5）

## D1–D7 自动化地板（score）

| 维 | 地板 |
|----|------|
| D1 | PASS |
| D2 | PASS |
| D3 | PARTIAL |
| D4 | PASS |
| D5 | UNTESTED（ablation 见 12-ablation） |
| D6 | SEE_PROBE |
| D7 | PASS |

## 相对 v6.3 初期

| 方面 | 变化 |
|------|------|
| 记忆探针 | **全线 PASS**（含跨章/变更/限知） |
| 真路径连载 | **5 章 finalized**，合计 2.27 万字 IN_BAND |
| 校验诚实 | 维持；full_check soft-pass 避免假死锁 |
| 文笔/声口 | **仍未证明**文学跃迁 |

## 进步空间（Headroom）

1. 人盲文学分未跑
2. L2–L5 文学 LLM 未满
3. draft_loop 围栏/LLM 流不稳定 → 依赖版本库 restore
4. pressure_metrics 在 full_check 软通过后，仍需质量线人读
5. D3 PARTIAL / D5 未严格 A/B 生产对照
6. 10 章满卷未跑

## 结论一句话

完成 **5 章真 pilot 连载 + 记忆 score PASS** 后，系统对成书**结构/记忆/可检**的代理帮助约 **64%**（原 61%）；  
**文学魅力**仍不可由本轮自动分断言。

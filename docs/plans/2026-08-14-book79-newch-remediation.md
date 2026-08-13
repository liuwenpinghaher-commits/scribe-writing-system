# book_79c0d45e 第 6–10 章排序改造（SSOT）

状态：**本目标 in-scope 项已落地 shipped。**  
评注：`docs/evidence/v634-newch-20260814/14-quality-findings.md`  
问题表：`docs/evidence/v634-newch-20260814/14-problem-table.md`  
不重开宣称公式，不改 `GATE_SAVE_MODE=soft`，不把 skip 说成过质控。  
**不做**：重写 6–10 文学稿；整包 142 飞行记录仪。

杠杆：先修挡读者的坏字节/重演检测和假绿，再修 scene_cover 误杀与词表，再对齐对照期望。

---

## 不做

- 不重写五章 2 万字当交付。
- 不实现 `docs/plans/2026-08-14-pipeline-runtime-analysis.md` 七个 PR。
- 不关 soft、不宣称人盲 ≥9.5。
- 不在 Grok 机全量测 / 本机 Surreal。

---

## In-scope（必须改到 shipped）

### N1 scene_cover 不再误杀逗号长句 — P0

**改**：`is_meta_span` 只把「顿号枚举 + 验收引导词」当 SEO；`beat_scene_keywords` 先抽 2 字核。  
**测**：`test_n1_*` 用 ch6 全文 + 现网三拍，`valid>=2`。  
**对应**：N-S1 N-S2。

### N2 炉契 / 刀鞘 / 门轴词表 — P0/P1

**改**：`FURNACE_MARKERS` 加「契就清」「念给全镇听」；`SHEATH_FORBIDDEN` 加「从尸身上解」；`门轴` 须近邻铜签/锁眼。  
**测**：`test_n2_*` 打 ch6/ch7 原文。  
**对应**：N-T1 N-T2 N-S8。

### N3 对照期望跟注入器 — P1

**改**：`expected_for("craft")` 恒 `always_engines`；`has_deduction` 认 `deductions[]`；`has_brief_must` 认大纲/节拍；storyline/discourse 认旗。  
**测**：`test_n3_*`。  
**对应**：N-S3。

### N4 skip 不得对照假绿 — P0

**改**：`skip_finalize_gate` 时 `actual=empty` + `skipped_by_flag`（期望仍 True → 红）。headline 仍「定稿门跳过」。  
**测**：`test_n4_*`。  
**对应**：N-S4。

### N5 替换符 + 场面重演检测 — P0

**改**：`sanitize_for_persist` 剥 U+FFFD；`find_restaged_scene`（前后半共享 ≥3 场面核）写入 `reasons`，save 文案加「疑似场面重演」。  
**测**：`test_n5_*` 用 ch6 全文。  
**对应**：N-S5 N-S6。

---

## Out-of-scope（写明，不装做已做）

| 项 | 理由 |
|----|------|
| 142 飞行记录仪 | 单独设计，七 PR |
| 重写 ch6 去重演 / 洗炉契讲义 | 文学稿 |
| 跨章刀鞘状态机（N-T3） | 需物件运行时，不在本闸 |

---

## 验收

- 仓库轻量测 `test_v634_newch_quality_gates.py` PASS（无 Surreal）。  
- demo health/ready + GET 6–10 无 fallback；不把 skip 写成过质控。

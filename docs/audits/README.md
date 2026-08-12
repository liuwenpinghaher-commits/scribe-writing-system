# 审计归档占位（OQ-6 / PR-EH-0）

工程健康度最优方案见：`docs/plans/2026-08-12-engineering-health-optimal-plan.md`。  
**结案（已修 / 分层锁 / 交付门）**：`docs/plans/2026-08-12-engineering-health-closure.md`。

本目录用于归档**外部完整 46 条审计原文**（若有 PDF/导出）。  
当前状态：

| 项 | 状态 |
|----|------|
| 方案 EH-** 稳定 ID 裁决表 | 已在方案文档 §1 |
| 结案 PASS 表 + commit 锚点 | **`2026-08-12-engineering-health-closure.md`**（main ≥ `cb64141`） |
| 外部原始 46 编号全文 | **未入库** — 有文件时放入本目录并在方案附录 A 回填映射 |
| 建议文件名 | `2026-08-12-engineering-health-external-audit.md` |

映射动作：将外部 P0/P1 措辞 → EH-01…EH-xx（见方案文档）。

---

## 分层 SSOT（工程健康度 · 禁止回潮）

1. **落库实现面**：仅 `scribe3/store/*` mixin 可使用 `_query` / `_execute_write` / `_raw_query`。  
2. **业务适配层禁止**直接调用上述私有方法（含 `quality/store.py`、`ingest*`、`pilot*`、`context_*`、router 等）。  
3. **回归钉**：`scribe3/tests/test_eh_residual.py::test_next_layer_adapters_no_private_store`。  
4. 新访问路径：先在 mixin 增加**公开 API**，再改调用方。  
5. **验收**：`./scripts/smoke_eh.sh` → `DEMO_EH_OK`（打已部署 demo，不起第二套库）。

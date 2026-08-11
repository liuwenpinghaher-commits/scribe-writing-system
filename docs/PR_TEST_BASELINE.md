# PR / 本地最低验证基线

> 与 `Makefile`、`scribe3/README.md` 配套。路径相对于仓库根 `写作 3.0/`。

## 每次改 MCP / 写门控

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q
```

必须全绿。关注：`commit_if_approved` 的 declined / written / **error（不假绿）**。

## 每次改前端 Codex / 北极星 / Chief 种子

```bash
cd scribe3/web && npm test -- src/views/CodexView.readonly.test.jsx src/lib/hermesRunIntent.test.js
```

（若本机 `npm test` 已配置 vitest run，可直接 `npm test` 全量。）

## 每次改 store / API 领域行为

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests -q --tb=line
```

耗时可先跑相关 `test_*.py`，合并前尽量全量。

## CI 向（可选）

```bash
make e2e-det          # 确定性 e2e
make e2e-frontend     # 前端 L2 冒烟（脚本拉临时后端）
```

`make e2e-real` 需本机 Hermes 凭证，不作为默认门禁。

## 业务流总控 + 分层 e2e

完整业务流 × 爆炸半径 × 执行单见  
[`docs/superpowers/plans/2026-07-23-business-flow-blast-radius-e2e-master.md`](./superpowers/plans/2026-07-23-business-flow-blast-radius-e2e-master.md)。

```bash
make test-author-paths   # MCP + emergency + P0 作者路径
make test-craft          # 工艺卫生 + 内容质量单测
make e2e-det             # 确定性六类失效
make e2e-craft-gates     # 反面书必须红
# make e2e-real          # 仅 Hermes 连通冒烟，≠ 质量验收
# craft_first_journey.mjs  # L3 工艺优先真旅程（需 Hermes + 前后端）
```

## 真人/融合 e2e（工艺优先）

长旅程与「正文是否遵守辅助信息」**不得**再用字数 / `form_fill=0` / 入口扫尾当 PASS。  
契约见 [`craft-first-verification-scheme-v3.md`](./craft-first-verification-scheme-v3.md)（GATE-A 书级齐套 → GATE-B 章脚手架 → GATE-C 正文合规审计 → 失败 RC 根因闭环）。  
旧 `artifacts/e2e-20260722-book_b4e72480` 结案 PASS 已作废，仅作反面对照。

```bash
# 工艺卫生门闩（不依赖 Hermes）
scribe3/.venv/bin/python -m pytest scribe3/tests/test_craft_compliance_gates.py -q

# 内容质量轨（闸绿 ≠ quality_pass）
scribe3/.venv/bin/python -m pytest scribe3/tests/test_content_quality.py -q

# 对运行中的书跑门闩（反面书应 --expect-fail）
scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work book_b4e72480 --expect-fail
```

**注意**：`craft gates` 绿只证明工艺卫生；章级验收还须 `verify_content_quality` + 内容评审（见 `docs/craft-first-verification-scheme-v3.md` §0.3）。
## 文档改动

若改栈/端口/主路径：同步 [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md)。

## 章节写路径锁纪律（人工清单 · 非阻塞 CI）

新章级写路径（loop / ingest / repair / run / 并行 deduce execute）必须经：

- `chapter_lock.acquire_chapter_lock` 或 `app_impl._acquire_op_mutex`

**保留独立表面（勿强并）**：`ingest_lease`、`approval_idempotency`、settings/sqlite busy。  
清单真源：[`guides/2026-08-11-lock-kinds.md`](./guides/2026-08-11-lock-kinds.md)。  
本条为 **PR 自检 NOTE**，**不加** grep 阻塞门禁。

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

## 真人/融合 e2e（工艺优先）

长旅程与「正文是否遵守辅助信息」**不得**再用字数 / `form_fill=0` / 入口扫尾当 PASS。  
契约见 [`craft-first-verification-scheme-v3.md`](./craft-first-verification-scheme-v3.md)（GATE-A 书级齐套 → GATE-B 章脚手架 → GATE-C 正文合规审计 → 失败 RC 根因闭环）。  
旧 `artifacts/e2e-20260722-book_b4e72480` 结案 PASS 已作废，仅作反面对照。

```bash
# 工艺门闩单测（不依赖 Hermes）
scribe3/.venv/bin/python -m pytest scribe3/tests/test_craft_compliance_gates.py -q

# 对运行中的书跑门闩（反面书应 --expect-fail）
scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work book_b4e72480 --expect-fail
```

## 文档改动

若改栈/端口/主路径：同步 [`CURRENT_ARCHITECTURE.md`](./CURRENT_ARCHITECTURE.md)。

# 工程健康度结案（Consolidation Lock）

| 字段 | 值 |
|------|-----|
| **状态** | **Accepted · rev.Done** |
| **日期** | 2026-08-12 |
| **main 锚点** | `cb64141`（QualityOps 业务层私有 store 清零） |
| **方案 SSOT** | [`2026-08-12-engineering-health-optimal-plan.md`](./2026-08-12-engineering-health-optimal-plan.md) |
| **验证** | 已部署 demo 冒烟（`scripts/smoke_eh.sh`）+ 过滤 pytest |

## 执行摘要

按 **生产风险 × 频率 × ROI** 实施的 PR-EH-0…11、residual 清零、适配层与 Quality 域公开 API 均已合入 **origin/main**。  
业务适配层（`scribe3/**` 除 `store/` / `tests/` / `tools/`）对 store 的 `._query` / `._execute_write` / `._raw_query` 调用数为 **0**。  
下一阶段以 **回归锁死** 为主，禁止无产品驱动的巨石空转搬家。

## 已完成对照（PASS + 锚点）

| 族 | 项 | 状态 | 主要路径 / 锚点 |
|----|-----|------|-----------------|
| 热路径 | purge_ingest / orphan 集合化 | PASS | `store/chapters.py` · `facts_knowledge.py` · `fae432b` 族 |
| 可观测 | emit / bridge fail-soft warning | PASS | `context_cache` · `codex_secret_bridge` · `7eb7cf9` |
| 安全 | Session Secure + XFP | PASS | `auth/routes.py` |
| 分层 | canon 破环 | PASS | `canon_types.py` |
| 分层 | router / 业务无私有 SurQL | PASS | `PilotOps` / `InfraOps` / `ContextOps` / `AdapterOps` / `QualityOps` · **`cb64141`** |
| 巨石文件 | pilot 阶段模块 | PASS | `api/services/pilot_actions/*` · `3d8941a` |
| 巨石文件 | write_assemble 上下文拆 | PASS | `write_assemble_context.py` · `b779f76` |
| 巨石文件 | rules_parts 共享 ns | PASS | `critique/rules_parts/*` |
| 契约 | residual + health batch | PASS | `tests/test_eh_residual.py` · `test_eh_health_batch.py` |
| 运维 | migration 131 幽灵 EVENT | PASS | demo `_migration` 含 `131_drop_ghost_async_events` |
| 产品契约 | REST≠MCP 审批 | DOC | `docs/adr/004-rest-no-approval.md` |

## 分层 SSOT（禁止回潮）

1. **允许**在 `scribe3/store/*` mixin 内使用 `_query` / `_execute_write` / `_raw_query`（唯一落库实现面）。  
2. **禁止**业务适配层（router、ingest、pilot、quality 适配器、context、lease 等）直接调用上述私有方法。  
3. **回归钉**：`scribe3/tests/test_eh_residual.py::test_next_layer_adapters_no_private_store`。  
4. 新增 store 访问必须先加 **公开 mixin 方法**，再改调用方。

## 刻意不做（Non-goals / INTENTIONAL）

| 项 | 裁决 | 理由 |
|----|------|------|
| REST ≡ MCP WRITE_GATED | INTENTIONAL | ADR-004；emergency 默认 403 |
| 全仓 os.environ 中心化 | WONT 短期 | EH-13；settings REGISTRY 渐进即可 |
| LIVE SELECT / 真 CDC | WONT 短期 | 轮询可接受；有 SLO 再议 |
| discuss soft → 硬裁 | DOC | OQ-2 产品未拍板 |
| tools/* CLI 私有调用 | 可选 Month+ | 非请求热路径 |
| write/rules 无产品驱动的再拆 | WONT 空转 | 已文件级可导航 |

## 下一阶段（见巩固方案）

| 包 | 内容 | 优先级 |
|----|------|--------|
| **A** | 本文 + smoke 脚本 + 交付 checklist | **已执行（本结案）** |
| **B** | 热路径 bare except → warning | Month 可选 |
| **C** | write/rules 语义拆 | 仅随产品改动 |

## 交付门（功能 PR）

合并 / 推 main 前建议：

```bash
# 过滤契约（勿 Grok 机全量）
.venv/bin/python -m pytest scribe3/tests/test_eh_residual.py scribe3/tests/test_eh_health_batch.py -q --tb=line

# demo 已部署栈
./scripts/smoke_eh.sh
```

输出应含 `DEMO_EH_OK`；失败不得宣称「EH 仍绿」。

## 相关提交（摘要）

| 提交 | 说明 |
|------|------|
| `fae432b` / `4d84e3e` | EH-0…11 主路径 |
| `154c7c5` / `680289d` | residual 首批 |
| `3d8941a` | 五模块清零 + pilot 阶段拆 |
| `b779f76` | infra/context + async retry + 再拆 |
| `2b2d93b` | AdapterOps 适配层 |
| `cb64141` | QualityOps · 业务层私有 0 |

# scribe3 架构拆分规范（权威 spec）

> **状态：实施完成（Phases A/B/C + services 下沉）**  
> **目标：降低审查与并行冲突；不改变产品语义与公开 URL。**  
> 关联：`docs/CURRENT_ARCHITECTURE.md` · PR 基线：`docs/PR_TEST_BASELINE.md`

## 1. 完成定义（Done）

| # | 标准 |
|---|------|
| S1 | 本文档列出全部 phase、非目标、兼容性规则与验证门槛 |
| S2 | HTTP 路由经 domain `APIRouter` 注册；`app_impl` 不再是多数 handler 的唯一物理宿主（行数大幅下降或仅剩组装/共享辅助） |
| S3 | `critique` / `mcp` 为包或多模块结构，对外 import 路径稳定（允许 re-export） |
| S4 | `store/misc.py` 不再作为新域持久化的默认垃圾桶；残留有文档归属 |
| S5 | `make test-baseline` 与 app/MCP/critique 相关回归通过 |

## 2. 兼容性铁律（搬迁 PR 禁止破坏）

1. **公开 URL 路径与 HTTP method 不变**（含 query 语义与 status code 契约）。
2. **产品语义不变**：审批门控、限知投影、`SCRIBE3_EMERGENCY_REST_WRITE`、LLM provider 行为。
3. **`import scribe3.app as A` + monkeypatch** 仍作用在同一可补丁命名空间（关键符号：`_stream_write`、`_responses_events`、`_complete_fn`、`_bg_ingest`、`_stores` 等）。
4. **禁止**按行数机械切 `app_impl_1/2/3`；必须按领域边界。
5. **禁止**微服务化 / 改 Surreal schema（除非搬迁绝对需要，默认不需要）。

## 3. 非目标

- 改审批、限知、REST 紧急写策略、LLM 供应商
- API 多进程拆分
- 前端 feature 目录全量重写（本 spec 后端优先）
- Hermes 拓扑重做

## 4. Phase 地图

### Phase A — 低耦合路由 + 入口接线

| 域 | 模块 | 代表路径 |
|----|------|----------|
| health | `api/health.py` | `/health` `/ready` |
| settings/gateway/ai | `api/routers/settings_gateway.py` | `/settings*` `/gateway*` `/ai/*` `/capabilities` |
| context | `api/routers/context_sessions.py` | `/context/*` |
| chat threads | `api/routers/chat_threads.py` | `/chat/threads*` `/maintenance/*` |
| memory | `api/routers/memory.py` | `/memory/*` |
| works | `api/routers/works.py` | `/works*` |
| events/timeline/search | `api/routers/world_read.py` | `/events*` `/timeline*` `/recall` `/graph` `/global-search`… |

### Phase B — 写作主路径 + 服务下沉

| 域 | 模块 | 代表路径 / 符号 |
|----|------|-----------------|
| write | `api/routers/write.py` + `api/services/write_stream.py` / `write_assemble.py` | `/chat/write*` 与 `_stream_write` / 组装指令 |
| chapters | `api/routers/chapters.py` | `/chapter*` `/loop*` `/outline*` `/select*` |
| pilot/inbox | `api/routers/pilot_inbox.py` + `api/services/pilot_runtime.py` | `/pilot*` 与 `_pilot_executor` |
| ingest bg | `api/services/ingest_bg.py` | `_bg_ingest` / `_enqueue_ingest` |
| lifecycle | `api/services/lifecycle.py` | 对象删除/归档 lifecycle |
| codex/materials | `api/routers/codex.py` `materials.py` | 世界设定 / 素材 |
| quality/ingest | `api/routers/quality.py` `ingest_import.py` | QC / import |

服务函数经 `app_impl._rebind_services()` 绑回 `app_impl` 全局，保证 `import scribe3.app as A` + monkeypatch 与 router `FunctionType` 重绑仍有效。

### Phase C — 工具与规则引擎分包 + store misc

| 组件 | 落地 |
|------|------|
| `critique/` | `repetition` / `structure_style` / `discipline_gate` / `rules_rest`；`rules.py` + `__init__.py` re-export |
| `mcp/` | `tools_read` / `tools_recall` / `tools_write`；`tools.py` 副作用注册 + re-export |
| `store/misc.py` | 已迁出 `motifs` / `unverified_ingest` / `progress_stats` / `character_arc`；misc 仅残留 ownership 文档块 |

### 接线

- `scribe3/app.py`：剥已抽路径 + `include_router` 一次；禁止双注册。
- `scribe3/api/app_impl.py`：共享核（中间件、store 缓存、AI run/Hermes 辅助、Pydantic 模型）+ `_rebind_services()`；**路由不在此文件**。

## 5. 验证门槛

```bash
make test-baseline          # MCP + web-readonly
pytest scribe3/tests/test_critique.py scribe3/tests/test_mcp.py -q
pytest scribe3/tests/test_app.py -q   # 或 make test-author-paths
# 可选：make e2e-det
```

另：OpenAPI/路由清单 before/after 比对；体积报告 before/after。

## 6. 基线 vs 目标（实施前 → 完成后）

| 文件 | 基线行数（约） | 完成后（约） |
|------|----------------|--------------|
| `api/app_impl.py` | ~11145 | ~1.6k 共享核 + service rebind（路由在 `api/routers/*`） |
| `api/models.py` | （无） | HTTP Pydantic 请求模型 |
| `api/services/*` | （无） | write_* / ingest / pilot / lifecycle / hermes / ai_run / prompt / thread / misc |
| `critique.py` | ~3189 | `critique/` 包（族模块 + re-export） |
| `mcp.py` | ~2193 | `mcp/`（tools_read/recall/write + server/gating） |
| `store/misc.py` | ~1145 | ~0.4k 残留 + motifs/progress/arc/unverified 分包 |

## 7. Task checklist（本轮）

- [x] 刷新权威 split spec
- [x] Phase A 低耦合 routers
- [x] Phase B write/chapters/pilot + **api/services 下沉**
- [x] Phase C critique 按检测族 / mcp 只读·召回·写 / store misc 迁出
- [x] app.py 单次挂载、无双注册
- [x] 全量验证与证据落盘（demo 冒烟 + 相关单测）

## 8. 历史

- Phase 0 / 0.5：薄 `app.py`、store 包化、health/intent 先行抽出（已完成）。
- 本文件为后续实施的**唯一完成标准**；与早期「1–2 周 Phase 1」叙述冲突时以**完成定义 §1** 为准。

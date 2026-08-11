# 章节锁 kind 清单（H8 · 收敛说明）

## 统一表面

产品写路径互斥优先走：

| API | 模块 | 说明 |
|-----|------|------|
| `acquire_chapter_lock` / `release_chapter_lock` | `scribe3.chapter_lock` | 章级锁 SSOT |
| `_acquire_op_mutex` | `api/app_impl.py` | HTTP 端点包装 → chapter_lock |
| `is_chapter_op_busy` | `novel_first_surface` | 只读 busy 探测 |

**合法 kind（`CHAPTER_OPS`）**：`loop` · `ingest` · `repair` · `run`

- `run`：通用写 / 并行 deduce / AI run 批
- `loop`：连载 loop
- `ingest`：回写 ingest
- `repair`：修复路径

同 `kind + work:seq` 重入 → `busy`（非静默双入）。

分布式：`SCRIBE3_DISTRIBUTED_LOCK=1` 且 store 注入时走 store；默认进程内 `concurrency_lock`。

## 仍独立 / 勿强并的表面

| 表面 | 原因 | 状态 |
|------|------|------|
| `ingest_lease` | 租约语义（TTL/续租）≠ 互斥锁 | 保留；busy 文案可映射 |
| `approval_idempotency` | 审批幂等键，非章写互斥 | 保留 |
| `settings` sqlite / usage PRAGMA busy | 库级 busy_timeout | 保留 |
| pilot 文档中的「_loop_inflight」叙述 | 实现已迁 chapter_lock / app 端点 | **文档口径**；代码以 `_acquire_op_mutex` 为准 |

## 已收敛

- chapters router 的 loop/repair/run 类写 → `_acquire_op_mutex`
- parallel deduce execute → `chapter_lock(kind=run)` 整批
- residual 测断言 busy 只读与 mutex 同源

## 原则

能经 `_acquire_op_mutex` / `chapter_lock` 的新写路径必须接线；不能改的在本清单登记，禁止再开第三套进程内 set。

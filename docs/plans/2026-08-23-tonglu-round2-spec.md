# 铜炉系统优化改造——下一轮实施Spec

## 1. 概述

### 1.1 本轮改造成果

* **完成率**：52.2%（82/157 条目已完成）

* **接线度**：92.1%（12模块中10个优秀，1个良好，1个需关注）

* **核心止血**：Stage 0 P0项完成率约85%，伏笔硬闸/章锁/ingest自愈/正典同步链等系统性修复到位

* **代码规模**：5 commits, 100 files, +7326/-187

* **新增测试**：4个新测试文件 + live测试扩展

* **DB迁移**：4个新迁移文件（161-164），幂等设计

### 1.2 下一轮目标

1. **修复3项BLOCKER**：解锁代码合并（上线阻断）
2. **补齐审查新发现的P0/P1**：消除多角色共识的高风险问题
3. **完成原spec未完成的P0项**：MAT-03 / CDX-10 / DED-02
4. **推进部分完成项**：从52.2%提升至≥85%完成率
5. **接线度短板修复**：Journey 73.5% → ≥90%

### 1.3 预计工作量

| Sprint               | 预计耗时        | 改动文件数      |
| -------------------- | ----------- | ---------- |
| Sprint 0（BLOCKER）    | 2-4小时       | 3-5个       |
| Sprint 1（新发现P0/P1）   | 4-6小时       | 8-12个      |
| Sprint 2（原spec未完成P0） | 2-3小时       | 4-6个       |
| Sprint 3（部分完成项补齐）    | 6-8小时       | 10-15个     |
| Sprint 4（P1未完成项）     | 8-12小时      | 15-20个     |
| Sprint 5（接线度短板）      | 6-8小时       | 8-12个      |
| **总计**               | **28-41小时** | **48-70个** |

***

## 2. Sprint 0：BLOCKER修复（必须立即修复，阻塞合并）

### B-01：advisory\_ttl 进程内 dict 多Worker不共享

**问题描述**：`_PENDING: dict` 是进程级全局变量，多Worker（gunicorn prefork）部署下各Worker各自维护不同副本。advisory在Worker1标记，Worker2的accept请求读不到，导致accept永远404。服务重启后所有pending advisory丢失——作者无法确认已生成的好稿。

**受影响代码**：

* `scribe3/advisory_ttl.py:8` — `_PENDING = {}` 模块级dict定义

* `scribe3/advisory_ttl.py` — `mark_advisory_pending()` / `check_advisory_pending()` 全部操作内存dict

**修复方案**：

1. 将 `_PENDING` dict 改为使用 migration 164 已建的 `advisory_pending` 表
2. `mark_advisory_pending(seq, advisory_id, ttl_hours=72)` → `INSERT INTO advisory_pending {seq, advisory_id, expires_at, created_at}`
3. `check_advisory_pending(seq, advisory_id)` → `SELECT * FROM advisory_pending WHERE seq=$seq AND advisory_id=$aid AND expires_at > time::now()`
4. `accept_advisory(seq)` → 查询DB + 删除记录
5. 可选：进程内保留一个1秒TTL快路径缓存减少热路径DB查询

**验证方法**：

* 单元测试：mock store验证 mark/check/accept 三步流转

* 集成测试：模拟两个Worker（不同进程），Worker1 mark → Worker2 accept 能成功

* 重启测试：mark后重启进程，accept仍能读到

**预估改动量**：\~40行代码修改，1个测试文件

***

### B-02：save\_chapter 乐观锁 TOCTOU 竞态

**问题描述**：`save_chapter` 乐观锁实现先 `get_chapter` 读rev校验，再重新 `get_chapter` 算 `next_rev`。两次读之间无原子保护——并发写可导致两个请求同时读到相同rev并通过校验，最后一个覆盖前一个。

**受影响代码**：

* `scribe3/store/chapters.py:278-283` — save\_chapter 方法中的双读逻辑

**修复方案**：

1. 删除两次 `get_chapter` 读取
2. 改为单条原子SurrealQL：

```sql
UPDATE chapter SET content=$content, rev=rev+1, updated_at=time::now()
  WHERE seq=$seq AND rev=$expected_rev
  RETURN AFTER
```

3. 返回行数为0即冲突，抛出 `ConflictError(409)` 让调用方重试
4. 消除中间的第二次读（NOTE #16 同步修复）

**验证方法**：

* 并发测试：asyncio.gather 同时发起2个 save\_chapter(same\_seq, same\_rev)，验证恰好1个成功1个409

* 回归测试：正常保存流程不受影响（rev正确递增）

**预估改动量**：\~25行代码修改

***

### B-03：母题phase推进未持久化（P0业务阻断）

**问题描述**：`motif_craft.schedule_motifs` 中根据touch数量推进phase（seed→echo→turn→payoff），但只在调度侧内存dict中设置，未回写store。母题永远停在seed阶段，LLM拿到的phase信号不对，反复以"埋种子"方式使用已该"转折"的母题，导致叙事节奏失控。

**受影响代码**：

* `scribe3/motif_craft.py` — `schedule_motifs()` 函数，phase计算后无store回写

**修复方案**：

1. 在 `schedule_motifs` 的 phase 推进逻辑后（循环末尾或返回前），加入持久化：

```python
for mid, row in updated_rows.items():
    if row["phase"] != row.get("original_phase"):
        await store.update_motif(mid, {"phase": row["phase"]})
```

2. 确保 `store.update_motif` 已有 `phase` 字段支持（检查 motif 表schema）
3. 增加日志：`log.info("motif %s phase advanced: %s → %s", mid, old, new)`

**验证方法**：

* 单元测试：mock store，验证 touch\_count 达阈值后 `update_motif` 被调用且参数正确

* E2E验证：连续5次 touch 同一母题后，查询 store 确认 phase 从 seed→echo

**预估改动量**：\~15行代码新增

***

## 3. Sprint 1：审查新发现的P0/P1问题

（原spec中没有，但本次审查新发现的问题）

### N-01：context\_snapshot ContextVar 全链路无 clear 调用

**来源角色**：C(LLM) + B(架构) 多角色共识\
**优先级**：P1（终审升级：C给出具体触发条件，风险真实）

**问题描述**：`snapshot_get_or_set` 使用 `contextvars.ContextVar` 缓存 build\_ctx 各槽位，但全链路无 `snapshot_clear()` 调用点。若同一协程连续服务多章请求，缓存不会失效，上一章数据注入下一章——跨章上下文污染（限知泄漏风险）。

**受影响代码**：

* `scribe3/playbook/context.py:860-864` — `snapshot_get_or_set` 定义

* `scribe3/context_snapshot.py:8` — ContextVar 声明

**修复方案**：

1. 在 `run_stage` 入口（或 `acquire_chapter_lock` 成功后）调用 `snapshot_clear()`
2. 在 `chat_write` 入口同样加 `snapshot_clear()`
3. 确保所有写路径入口（loop\_chapter/pilot\_step/chat\_write）均在开始前清空

**验证方法**：

* 单元测试：模拟同协程连续处理 seq=5 和 seq=6，验证第二次不命中第一次缓存

* grep确认：所有写路径入口均有 snapshot\_clear() 调用

**预估改动量**：\~10行（3处入口各加1行）

***

### N-02：revision\_letter\_digest + scene\_grid 未纳入 context\_budget

**来源角色**：C(LLM)\
**优先级**：P1

**问题描述**：新增 `revision_letter_digest`（最长800字）和 `scene_grid`（最长800字）两个槽位未注册到 `context_budget.py` 的预算分配表。极端情况1600token无管控注入可能令prompt超总顶。

**受影响代码**：

* `scribe3/playbook/context.py:914-923` — 两个新槽位定义

* `scribe3/playbook/context_budget.py` — L2\_DROP\_TIER 裁剪序列缺此二项

**修复方案**：

1. 在 `context_budget.py` 的 `L2_DROP_TIER` T3层注册 `"revision_letter_digest"` 和 `"scene_grid"`
2. 或在 `_letter_grid_block` 中加 token 估算：`clip_to_tokens(letter, 400)` / `clip_to_tokens(grid, 400)`

**验证方法**：

* 单元测试：构造超长 letter+grid，验证裁剪后总token不超预算

* 检查 L2\_DROP\_TIER 包含新槽位

**预估改动量**：\~10行

***

### N-03：final层 hint SCRIBE3\_HINT\_NO\_ACCUM 实为追加非替换

**来源角色**：C(LLM)\
**优先级**：P1

**问题描述**：final层 `SCRIBE3_HINT_NO_ACCUM` 生效时，rounds≥3后hint追加固定句子（"换个角度…"），但并未清空旧hint——是 `hint[0] + " 换个角度…"`。第4、5…轮hint越来越长，违反"不累积"设计意图。

**受影响代码**：

* `scribe3/playbook/pipeline.py:761-762` — hint追加逻辑

**修复方案**：
改为纯替换：

```python
hint[0] = "换个角度：贴着另一个在场的人看见的那一面，重写这一场。"
```

**验证方法**：

* 单元测试：模拟rounds=5，验证hint\[0]长度恒定（不随轮次增长）

**预估改动量**：\~3行

***

### N-04：SCRIBE3\_JOURNEY\_PRECHECK 默认关 + loop\_chapter不检查

**来源角色**：D(写作) + A(QA) 多角色共识\
**优先级**：P1

**问题描述**：`SCRIBE3_JOURNEY_PRECHECK` 默认"0"，仅pilot\_inbox入口检查。loop\_chapter/chat\_write不检查——作者可绕过检查直接写章，在无北极星的情况下LLM无方向约束。

**受影响代码**：

* `scribe3/feature_flags.py` — `SCRIBE3_JOURNEY_PRECHECK` 默认值

* `scribe3/api/routers/write.py` — chat\_write入口

* `scribe3/loop.py`（或对应loop\_chapter入口）

**修复方案**：

1. `feature_flags.py` 中将 `SCRIBE3_JOURNEY_PRECHECK` 默认值改为 `"1"`
2. 在 `loop_chapter` 和 `chat_write` 入口复用 pilot\_inbox 的 precheck 逻辑
3. 或抽出 `_journey_precheck(st)` 公共 gate 函数

**验证方法**：

* 测试：未设北极星时调用 loop\_chapter，验证返回 precheck 失败提示

* 不影响已设北极星的正常写作流程

**预估改动量**：\~20行

***

### N-05：inbox\_dismiss 进程内 set 多Worker不共享

**来源角色**：B(架构)\
**优先级**：P1/MAJOR

**问题描述**：`_MEM: set` 同样是进程内全局set，多Worker不共享。`filter_inbox` 依赖它过滤已dismiss项；Worker重启后丢失。

**受影响代码**：

* `scribe3/inbox_dismiss.py:7` — `_MEM: set` 定义

**修复方案**：

1. 始终写DB（store已有 `dismiss_inbox_item` 抽象）以DB为SSoT
2. 进程set仅做本请求内快路径缓存（请求结束即丢弃）
3. `filter_inbox` 改为先查DB已dismiss集合，再过滤

**验证方法**：

* 集成测试：dismiss后重启进程，验证filter\_inbox仍正确过滤

* 并发测试：两个Worker同时dismiss不同item，互相可见

**预估改动量**：\~30行

***

### N-06：pending\_proposals setattr注入隐藏属性

**来源角色**：B(架构)\
**优先级**：P1/MAJOR

**问题描述**：`_bucket()` 通过 `setattr(store, "_pending_proposals", ...)` 向外部传入的store对象注入隐藏属性。store作为长生命周期对象会泄漏提案引用直到进程结束。

**受影响代码**：

* `scribe3/pending_proposals.py:17-19` — `_bucket()` setattr逻辑

**修复方案**：

1. 提案落 `pending_proposal` 表（migration 162已就绪）
2. `save_pending_proposal()` → INSERT INTO pending\_proposal
3. `list_pending_proposals()` → SELECT FROM pending\_proposal WHERE status='pending'
4. 删除 setattr 逻辑，进程内dict仅做短暂快路径

**验证方法**：

* 查询DB验证提案持久化

* 重启后pending proposals不丢失

**预估改动量**：\~35行

***

### N-07：写路径章锁10分钟TTL可能不够

**来源角色**：B(架构)\
**优先级**：P1/MAJOR

**问题描述**：`_lock_chapter_run` 使用10分钟TTL，但SSE流式生成可能超过10分钟。锁过期后另一请求可获锁导致同章并行写。

**受影响代码**：

* `scribe3/api/routers/write.py:29-62` — `_lock_chapter_run` TTL设置

**修复方案**：

1. 引入锁续约heartbeat：SSE流式中每3分钟续约一次
2. 或上调TTL为20分钟（简单方案）
3. 或在流式中检测锁丢失后中止生成

**验证方法**：

* 构造>10分钟的模拟写入，验证锁不过期

* 正常写入（<10min）锁正确释放

**预估改动量**：\~15行（简单方案仅改TTL值）

***

### N-08：live.py 顶层 import 崩溃风险

**来源角色**：B(架构)\
**优先级**：P1/MAJOR

**问题描述**：将 `from surrealdb import AsyncSurreal` 从函数内lazy import提到模块顶层。若surrealdb包未安装，整个 `live.py` 模块import即崩——影响不依赖live功能的测试。

**受影响代码**：

* `scribe3/live.py:15` — 顶层import语句

**修复方案**：

```python
try:
    from surrealdb import AsyncSurreal
except ImportError:
    AsyncSurreal = None  # live功能不可用时降级
```

**验证方法**：

* 在无surrealdb环境下 `import scribe3.live` 不报错

* 有surrealdb时功能正常

**预估改动量**：\~5行

***

### N-09：\_QUALITY\_TTL 模块级缓存多Worker各自维护

**来源角色**：B(架构)\
**优先级**：P1/MAJOR

**问题描述**：`_QUALITY_TTL` 模块级缓存——多Worker各自缓存，save\_chapter后同Worker内5秒旧值，其它Worker更长。

**受影响代码**：

* `scribe3/api/routers/quality.py:111` — `_QUALITY_TTL` dict定义

**修复方案**：

1. TTL缩短至1-2秒
2. 在 `save_chapter` 成功后主动清缓存（同Worker同步清）
3. 或改用store端版本戳比对：save时version+1，查询时比对

**验证方法**：

* 保存章节后立即查quality，不应返回旧值

**预估改动量**：\~10行

***

### N-10：正典半包回滚 fact 类无处理

**来源角色**：D(写作)\
**优先级**：P1

**问题描述**：`_undo_applied` 覆盖character/faction/item/term/world\_rule五类，但fact类无回滚逻辑。ChangePack可含fact/knowledge条目，半批场景下被拒变更已落库的fact残留。

**受影响代码**：

* `scribe3/canon_loop.py` — `_undo_applied()` 函数

**修复方案**：
在 `_undo_applied` 中增加 fact 类分支：

```python
elif kind == "fact":
    await store.delete_fact(entity_id)
elif kind == "knowledge":
    await store.forget_knowledge(entity_id)
```

**验证方法**：

* 测试：构造含fact条目的ChangePack，apply半批失败后验证fact已回滚

**预估改动量**：\~10行

***

### N-11：CausalRootEditor 保存零反馈

**来源角色**：E(前端)\
**优先级**：P1

**问题描述**：CausalRootEditor保存因果根后无toast反馈，用户无法感知成功/失败。

**受影响代码**：

* `scribe3/web/src/views/TimelineView.jsx` — CausalRootEditor组件save逻辑

**修复方案**：

```jsx
try {
  await api.patchEventCausalRoot(eventId, { causal_root: value });
  showToast("因果根已保存", { tone: "success" });
} catch (e) {
  showToast("保存失败: " + e.message, { tone: "danger" });
}
```

**验证方法**：

* 手动测试：保存成功/失败均有toast提示

**预估改动量**：\~8行

***

### N-12：SSE重连后 liveTouchesTable 不匹配 `_reconnect`

**来源角色**：E(前端)\
**优先级**：P1

**问题描述**：SSE重连后派发 `{table:'_reconnect'}` 但 `liveTouchesTable()` 不匹配→重连后面板数据不自动拉新。

**受影响代码**：

* `scribe3/web/src/lib/api.js`（或 `liveTouchesTable` 所在文件）

* 涉及 `InsightView` / `TimelineView` / `CodexDirectory`

**修复方案**：
在 `liveTouchesTable` 函数开头加：

```javascript
if (t === '_reconnect') return true;  // 全量刷新语义
```

**验证方法**：

* 模拟SSE断线→重连后，各面板自动拉新数据

**预估改动量**：\~3行

***

## 4. Sprint 2：原spec未完成的P0项

### S2-01：MAT-03 — material.about\_entities 级联清理不完整

**原始编号**：MAT-03\
**未完成原因**：`_cleanup_record_refs` 扩展了faction/item/term/world\_rule的knows/relation清理，但遗漏了material表的about\_entities字段清理。

**补完方案**：
在 `_cleanup_record_refs` 或 `codex_ext.py` 的 delete 路径中加入：

```python
await self.query("UPDATE material SET about_entities -= $oid WHERE $oid IN about_entities", {"oid": entity_id})
```

**受影响代码**：

* `scribe3/store/connection.py:428-455` — `_cleanup_record_refs` 方法

**验证方法**：

* 测试：删除codex实体后查询material表，验证about\_entities不含已删ID

**预估改动量**：\~5行

***

### S2-02：CDX-10 — MCP s3\_delete\_codex 不走 lifecycle

**原始编号**：CDX-10\
**未完成原因**：MCP工具层独立于API路由，未import lifecycle逻辑。

**补完方案**：

1. 在 MCP 的 `s3_delete_codex` handler 中调用 `_cleanup_record_refs(entity_id)`
2. 或改为内部调用已有的 REST DELETE endpoint（走完整lifecycle）
3. 推荐方案2：MCP handler → 调用内部API → 复用完整删除链路

**受影响代码**：

* `scribe3/mcp/` 目录下对应的 delete 工具定义

**验证方法**：

* 通过MCP删除codex实体，验证关联数据正确级联清理

**预估改动量**：\~15行

***

### S2-03：DED-02 — thicken\_stage 本身未加锁

**原始编号**：DED-02\
**未完成原因**：pilot\_step加了锁，但 `stage_generate.py` 的 `thicken_stage` 本身未直接加锁。若有直接API/脚本调用则不安全。

**补完方案**：
在 `thicken_stage` 入口加锁：

```python
async def thicken_stage(store, seq, ...):
    async with acquire_chapter_lock("thicken", seq, store):
        # 原有逻辑
```

**受影响代码**：

* `scribe3/playbook/stage_generate.py` — `thicken_stage` 函数入口

**验证方法**：

* 并发测试：同时调用两次 thicken\_stage(same\_seq)，验证串行执行

**预估改动量**：\~5行

***

## 5. Sprint 3：原spec部分完成项补齐

### S3-01：DSH-05 — PromiseLedger 加载失败时静默消失

**原始编号**：DSH-05\
**缺了什么**：InsightView加了s3-live但未将catch改为error state展示（原有 `.catch(()=>setLed(null))` 未修改）。

**补齐方案**：

```jsx
.catch(err => {
  setLedError(err.message);
  setLed(null);
})
// 渲染时：{ledError && <ErrorState msg={ledError} onRetry={loadLedger} />}
```

***

### S3-02：CDX-06 — Apply后非fact实体不触发语义索引

**原始编号**：CDX-06\
**缺了什么**：`_sync_after_apply` 有digest同步但未显式触发向量embedding。语义索引走digest→fact间接路径可能不够直接。

**补齐方案**：
在 `_sync_after_apply` 末尾，对非fact类实体也调用 `store.semantic_index(entity_id, digest_text)`。

***

### S3-03：CDX-07 — Reject 不学习

**原始编号**：CDX-07\
**缺了什么**：`canon_candidates.py` 有expire逻辑但未见rejected去重预查改动。被拒候选可能反复出现。

**补齐方案**：
在 `list_candidates` 或 `generate_candidates` 时，预查 rejected 记录做去重：

```python
rejected_ids = await store.query("SELECT entity_hash FROM canon_candidate WHERE status='rejected' AND created_at > $cutoff")
candidates = [c for c in candidates if c.hash not in rejected_ids]
```

***

### S3-04：CDX-09 — faction删除不走完整lifecycle

**原始编号**：CDX-09\
**缺了什么**：补了 `_cleanup_record_refs` 级联清理，但缺少删除前的影响评估（lifecycle check）。

**补齐方案**：
删除前调用 `chapter_lifecycle_impact(entity_id)` 检查是否有活跃章节引用，若有则返回warning让用户确认。

***

### S3-05：ATL-02 — 势力删除无完整lifecycle保护

**原始编号**：ATL-02\
**缺了什么**：有级联清理但非完整lifecycle评估路径。

**补齐方案**：同CDX-09，在faction delete入口加 lifecycle impact check。

***

### S3-06：ATL-05 — 角色删除不级联清理命题

**原始编号**：ATL-05\
**缺了什么**：`_cleanup_record_refs` 扩展了knows/character\_relation清理，但未见显式 `DELETE proposition WHERE entity_id=$oid`。

**补齐方案**：
在 `_cleanup_record_refs` 中增加：

```python
await self.query("DELETE proposition WHERE entity_id = $oid OR subject = $oid", {"oid": oid})
```

***

### S3-07：ATL-08 — 关系图权重/方向前端无展示

**原始编号**：ATL-08\
**缺了什么**：后端加了weight+directed字段，但前端图渲染未改动。

**补齐方案**：
AtlasView 中 edge 渲染增加 weight→线粗 + directed→箭头方向映射。

***

### S3-08：PRM-05 — 伏笔超期无主动告警

**原始编号**：PRM-05\
**缺了什么**：`alerts.py` 提供了webhook能力，但 `agent_crons` 未增加 `check_overdue_promises` 定时任务。

**补齐方案**：
在 `agent_crons.py` 注册定时任务：

```python
@cron("0 9 * * *")  # 每日9点
async def check_overdue_promises(store):
    overdue = await store.open_promises(overdue_only=True)
    if len(overdue) >= 2:
        await send_alert(f"有{len(overdue)}条伏笔超期未兑现")
```

***

### S3-09：JNY-02 — 质量熔断状态对作者不可见

**原始编号**：JNY-02\
**缺了什么**：后端pipeline保留best\_art但前端JourneyView未见quality\_stalled展示。

**补齐方案**：
JourneyView 中消费 workflow/snapshot 的 `quality_stalled` 字段，展示"质量循环已保留最优稿"提示。

***

### S3-10：DIR-05 — Blocker双向闭环零测试覆盖

**原始编号**：DIR-05\
**缺了什么**：需确认"blocker产生→解除→允许写入"的完整双向测试。

**补齐方案**：
新增测试用例：

1. 设置3条超期伏笔 → 调用write → 验证409阻断
2. 兑现1条伏笔降至2条 → 调用write → 验证通过

***

### S3-11：MAN-03 — 永久删除未级联清理canon\_candidate

**原始编号**：MAN-03\
**缺了什么**：`delete_chapter_permanent` 未见清理该章相关的canon\_candidate。

**补齐方案**：
在 `delete_chapter_permanent` 中加入：

```python
await self.query("DELETE canon_candidate WHERE seq = $seq", {"seq": seq})
```

***

### S3-12：DED-15 — build\_ctx soft\_fail静默降级无限制指令

**原始编号**：DED-15\
**缺了什么**：build\_ctx有 `_guide_fail` 记录但未注入"⚠️不编造"限制指令。

**补齐方案**：
当 `_guide_fail` 触发时，向prompt追加提示：

```python
if ctx.get("_guide_fail"):
    ctx["safety_note"] = "⚠️ 部分设定数据加载失败，请勿编造未提供的角色/事件信息。"
```

***

### S3-13：DED-22 — grep\_back\_verify标"未明确"的learned类仍写入

**原始编号**：DED-22\
**缺了什么**：motif类已加unverified标记并drop，但learned类annotated事实仍写入。

**补齐方案**：
learned类也加 `confidence: "unverified"` 标记，并在 apply 时对 unverified 做降权处理。

***

### S3-14：CRS-03 — 记忆召回图通道未默认开

**原始编号**：CRS-03\
**缺了什么**：emotion\_module去重已做、recall加exclude\_kinds，但图通道未默认开、影子模式无自动切换。

**补齐方案**：
将 `SCRIBE3_GRAPH_RELATION_RECALL` 默认值改为 `"1"`。

***

### S3-15：CRS-05 — 限知门控：伏笔兑现的knows边未建

**原始编号**：CRS-05\
**缺了什么**：advance产proposition已做，但伏笔兑现时涉及角色的knows边未更新。

**补齐方案**：
在 `advance_promise` 末尾，对 `involved_characters` 中各角色增加 knows 边指向新fact。

***

### S3-16：CRS-06 — 级联删除MCP路径未覆盖

**原始编号**：CRS-06\
**缺了什么**：faction/item/term/world\_rule的REST路径有cleanup，但MCP路径无覆盖。

**补齐方案**：同S2-02，MCP删除走内部API复用完整链路。

***

## 6. Sprint 4：P1级未完成项

（原spec中P1级但未完成的条目，按影响排序）

### S4-01：SYS-11/12 — 幽灵配置清理

**编号**：SYS-11, SYS-12\
**说明**：`SCRIBE3_DESIGN_BOOK` 和 `SCRIBE3_STORYLINE_UI` 两个flag在代码中被引用但无实际功能。\
**方案**：从 `feature_flags.py` 和所有引用点移除或标注deprecated。

### S4-02：SYS-13 — SCRIBE3\_DEFAULT\_WORK裸environ绕过

**编号**：SYS-13\
**说明**：`app_impl.py` 中直接用 `os.environ` 绕过 flag 注册表读取 DEFAULT\_WORK。\
**方案**：改为通过 `get_flag("SCRIBE3_DEFAULT_WORK")` 读取。

### S4-03：DSH-06 — 伏笔setup章被删后UI仍显示

**编号**：DSH-06\
**说明**：前端PromiseLedger展示的promise可能引用已删除章节。\
**方案**：前端展示时检查chapter是否存在，不存在标记"⚠️原章已删"。

### S4-04：DIR-16 — Proposal reject无审计日志

**编号**：DIR-16\
**说明**：提案被拒时无audit trail。\
**方案**：在reject逻辑中加 `append_audit("proposal_reject", actor=..., proposal_id=...)`。

### S4-05：DIR-17 — idea路由LLM失败静默降级

**编号**：DIR-17\
**说明**：LLM生成idea失败时静默返回空，用户无感知。\
**方案**：失败时返回 `{"degraded": true, "reason": "LLM调用失败"}` 让前端展示降级提示。

### S4-06：DED-16 — volume\_ledger flag默认关

**编号**：DED-16\
**说明**：`SCRIBE3_VOLUME_LEDGER` 默认关闭，卷级统计不生效。\
**方案**：评估稳定性后改为默认开启。

### S4-07：DED-17 — recall\_service图通道默认关闭

**编号**：DED-17\
**说明**：`SCRIBE3_GRAPH_RELATION_RECALL` 默认关。\
**方案**：与S3-14合并处理，改为默认开启。

### S4-08：DED-24 — recent\_duty\_summary只看3章硬编码

**编号**：DED-24\
**说明**：`recent_duty_summary` 固定取最近3章，长章小说不够。\
**方案**：注册为flag `SCRIBE3_DUTY_SUMMARY_LOOKBACK` 默认3，允许运行时调整。

### S4-09：MOT-06 — 创建闭环无降级自动填占位

**编号**：MOT-06\
**说明**：母题创建时如LLM生成echo\_terms失败，无降级方案。\
**方案**：失败时填入 `["(待补充)"]` 占位 + 标记 `needs_human=True`。

### S4-10：MOT-07 — 过热抑制依赖LLM无硬保证

**编号**：MOT-07\
**说明**：motif\_overheat\_advisory的blocking:False，系统无硬拦。\
**方案**：将overheat advisory注入brief/write prompt的avoid\_overuse段，并在ingest post\_check中检测过热母题出现。

### S4-11：MAN-05 — 大纲/节拍无版本记录

**编号**：MAN-05\
**说明**：章节大纲修改后无版本历史。\
**方案**：复用 `chapter_versions` 机制，为outline变更创建版本快照。

### S4-12：CDX-17 — THICKEN\_GATE=0绕过无审计

**编号**：CDX-17\
**说明**：设置THICKEN\_GATE=0可绕过duty\_gate检查但无审计日志。\
**方案**：绕过时记录audit log。

***

## 7. Sprint 5：接线度短板修复

### 7.1 旅程模块（Journey）接线度提升：73.5% → ≥90%

**核心问题**：JourneyView仅消费1个核心API（workflow/snapshot），后端能力远超前端展现。

**改进方案**：

| # | 改进项                 | API来源                              | 预期效果                             |
| - | ------------------- | ---------------------------------- | -------------------------------- |
| 1 | 接入 `/chapter-pulse` | 已有API                              | 展示章节推进节奏/压力信号                    |
| 2 | 接入 pilot status     | `/pilot/status`                    | 展示当前写作状态（idle/writing/reviewing） |
| 3 | 接入 stage 进度         | `/chapters/{seq}/stage`            | 展示当前章节所处阶段                       |
| 4 | 增加SSE推送             | s3-live chapter表                   | 实时更新旅程进度                         |
| 5 | 质量熔断状态展示            | workflow/snapshot.quality\_stalled | 展示是否触发了质量循环保留                    |
| 6 | 增加伏笔债务概览            | `/promises/ledger`                 | 展示未兑现伏笔数量/超期情况                   |

**预期接线度**：6/6 新消费 → 前端→后端接线度从67%提升至\~90%

### 7.2 Atlas模块接线度微调

**问题**：`/char-states` POST 仅MCP调用，前端无入口。

**方案**：在角色详情面板（NodeDetail.jsx）增加"标记状态变化"入口按钮。

### 7.3 其他断线修复

| 项                                       | 修复                                |
| --------------------------------------- | --------------------------------- |
| `/orchestration/proposal/{pid}` GET 未消费 | ChiefDock审批流中展示pending proposal详情 |
| `s3-chapter-phase-hint` 无消费者            | 在WriteLayout中消费，展示当前章节阶段提示        |

***

## 8. 实施依赖图

```
Sprint 0 (BLOCKER)
├── B-01 advisory_ttl持久化 ─────────────┐
├── B-02 save_chapter原子锁 ────────────┤ 无依赖，可并行
└── B-03 母题phase持久化 ───────────────┘

Sprint 1 (新发现P0/P1)  ← 依赖 Sprint 0 完成（合并解锁后才进入）
├── N-01 snapshot_clear ─────────────────┐
├── N-02 context_budget注册 ─────────────┤ 无依赖，可并行
├── N-03 hint纯替换 ────────────────────┤
├── N-04 JOURNEY_PRECHECK默认开 ────────┤
├── N-05 inbox_dismiss改DB ─────────────┤
├── N-06 pending_proposals持久化 ────────┤ 与B-01同模式，可复用经验
├── N-07 章锁TTL上调 ──────────────────┤
├── N-08 live.py import保护 ────────────┤
├── N-09 quality TTL缩短 ───────────────┤
├── N-10 fact类回滚 ────────────────────┤
├── N-11 CausalRoot toast ──────────────┤
└── N-12 liveTouchesTable _reconnect ───┘

Sprint 2 (原spec P0)  ← 与 Sprint 1 可并行
├── S2-01 material.about_entities清理 ──┤
├── S2-02 MCP lifecycle ← 依赖 S3-16 ──┤
└── S2-03 thicken_stage加锁 ───────────┘

Sprint 3 (部分完成项)  ← 依赖 Sprint 1/2 核心完成
├── S3-01~S3-16 大部分可并行
└── S3-15 knows边 ← 依赖 S3-10（Blocker双向测试确认逻辑正确）

Sprint 4 (P1未完成)  ← 独立于 Sprint 3，可并行
└── S4-01~S4-12 互相独立

Sprint 5 (接线度)  ← 依赖 Sprint 3 后端改动就绪
└── JourneyView增厚 ← 依赖 S3-09（quality_stalled字段）
```

**并行建议**：

* Sprint 0 三项可完全并行

* Sprint 1 + Sprint 2 可同时启动（不同文件）

* Sprint 3/4 大部分互相独立

* Sprint 5 最好在前4个Sprint核心完成后再做（依赖后端数据稳定）

***

## 9. 验收标准

### Sprint 0 完成后

* [ ] BLOCKER清零：advisory\_ttl持久化到DB + save\_chapter原子化 + 母题phase回写

* [ ] 所有现有测试通过（`pytest tests/ -x`）

* [ ] 可合并到主分支

### Sprint 1-2 完成后

* [ ] P0清零：终审中所有P0项均已修复

* [ ] context\_snapshot无跨请求污染（新增测试证明）

* [ ] 进程内缓存全面改DB SSoT（advisory/dismiss/quality/proposals四处）

* [ ] JOURNEY\_PRECHECK默认开启且三入口覆盖

### Sprint 3-4 完成后

* [ ] 完成率从52.2%提升至≥85%（131/157+）

* [ ] 部分完成项（33项）中≥80%（26+项）转为已完成

* [ ] 级联删除覆盖所有路径（REST + MCP）

### Sprint 5 完成后

* [ ] JourneyView接线度从73.5%提升至≥90%

* [ ] 系统整体接线度从92.1%提升至≥95%

* [ ] 新增前端消费全部有对应SSE实时推送

### 全局验收

* [ ] `pytest tests/ --tb=short` 全绿

* [ ] 无新增 BLOCKER/P0

* [ ] migration 幂等性验证（跑两次不报错）

* [ ] 前端零幽灵调用维持（api.js所有方法有后端注册）

***

## 10. 风险点

### 10.1 技术难点

| 风险                        | 说明                                            | 缓解措施                            |
| ------------------------- | --------------------------------------------- | ------------------------------- |
| save\_chapter原子化回归        | 改为UPDATE WHERE rev=...后，所有调用方需处理ConflictError | 全局搜索save\_chapter调用方，确保有重试/提示逻辑 |
| advisory\_ttl持久化后性能       | 每次check\_advisory查DB多一次IO                     | 加1秒进程内缓存作快路径                    |
| context\_snapshot clear时机 | 在错误位置clear可能导致同一请求内重复计算                       | clear仅在写路径最外层入口，内部层不再clear      |
| JourneyView增厚             | 展示信息增加后信息密度可能过高                               | 采用渐进式展开（折叠面板）                   |

### 10.2 需要设计决策的项

| 项                         | 决策点                              | 建议                                             |
| ------------------------- | -------------------------------- | ---------------------------------------------- |
| 章锁续约 vs 上调TTL             | 续约更精确但实现复杂；上调简单但浪费               | **建议先上调TTL到20min**，后续有需要再加续约                   |
| Graph Recall默认开           | 开启后召回信息量增加，可能影响prompt预算          | **建议开启**，配合L2裁剪保障不超限                           |
| fact回滚粒度                  | 全量delete还是标记deleted              | **建议物理delete**（fact本身来自canon\_candidate，可重新生成） |
| 伏笔超期告警阈值                  | 2条还是3条触发告警                       | **建议2条告警、3条阻断**，梯度设计                           |
| MCP删除走内部API vs 直接加cleanup | 走API更安全但多一次HTTP；直接加cleanup快但分散维护 | **建议走内部API**，单一维护点                             |

### 10.3 回归风险

* `save_chapter` 改动涉及核心写路径，需重点回归测试

* `feature_flags` 默认值变更可能影响现有用户（建议加迁移提示）

* `advisory_ttl` 改DB后，已有的进程内pending advisory将丢失（需一次性迁移或接受重启丢失）

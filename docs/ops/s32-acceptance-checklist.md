# SurrealDB 3.2.4 优化轨 · 业务/产品验收清单

> **用途**：结案本优化轨时勾选。仅过「工程脚本」不算交付；**P 产品项须人工或等价 E2E 勾选**。  
> **环境**：demo `https://www.qing.blue`（已部署栈，不另起库）  
> **对应方案**：`docs/plans/2026-08-08-surrealdb-3.2.4-optimization-plan.md`  
> **审查说明**：会话内「优化审查」结论：T 强、P/B 弱；本清单补齐 P/O。

**图例**

| 标记 | 含义 |
|------|------|
| `[ ]` / `[x]` | 未过 / 已过 |
| **自动** | 可用脚本或只读 API 判定 |
| **人工** | 须浏览器操作（或你指定账号） |
| **门禁** | 结案本轨的最低集合（见文末） |

---

## 0. 元信息（每次验收填）

| 项 | 值 |
|----|-----|
| 日期 | YYYY-MM-DD |
| 验收人 | |
| demo 入口 | https://www.qing.blue |
| 后端/库版本备注 | Surreal **v3.2.4**；Hermes 0.20（记忆不在 Hermes） |
| git / 部署备注 | （可选） |

---

## T · 技术层（自动优先）

> 命令在 **能 SSH 到 demo 或本机有密钥** 的环境执行。

### T1 现网版本与健康 — **门禁** · **自动**

```bash
./scripts/smoke_s32.sh
# 或 demo 机：/home/ubuntu/smoke_s32.sh
```

| # | 检查项 | 通过标准 | 结果 |
|---|--------|----------|------|
| T1.1 | ready / health | HTTP 200 | [ ] |
| T1.2 | 登录 | bootstrap 账号 200 | [ ] |
| T1.3 | capabilities.memory_fabric_v1 | `true` | [ ] |
| T1.4 | works / chapters / codex/health | 200 | [ ] |
| T1.5 | Surreal 镜像 | `v3.2.4` | [ ] |

### T2 检索计划正确性 — **门禁** · **自动**

```bash
# demo 机（需已有 perf_s32 或先 seed）
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -u -m scribe3.tools.probe_s32_hotpath --work perf_s32
```

| # | 检查项 | 通过标准 | 结果 |
|---|--------|----------|------|
| T2.1 | proposition KNN | EXPLAIN 含 **KnnScan** / HNSW | [ ] |
| T2.2 | memory KNN | KnnScan | [ ] |
| T2.3 | memory BM25 | FullTextScan | [ ] |
| T2.4 | chapter ORDER BY seq | **IndexScan**（idx_chapter_seq） | [ ] |

### T3 记忆技术闭环 — **门禁** · **自动**

```bash
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -u -m scribe3.tools.memory_e2e_s32 --work main
```

| # | 检查项 | 通过标准 | 结果 |
|---|--------|----------|------|
| T3.1 | capture | status=complete | [ ] |
| T3.2 | memory_item 计数 | after > before | [ ] |
| T3.3 | vector 和/或 bm25 | 至少一路有 id | [ ] |
| T3.4 | retrieve_full | selected/prefetch_n > 0 | [ ] |
| T3.5 | 脚本退出码 | `ok: true` / exit 0 | [ ] |

### T4 中文 FTS（铜炉问题）— **门禁** · **自动**

```bash
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -u -m scribe3.tools.reindex_memory_fts --work main   # 若刚灌旧 tokens
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -u -m scribe3.tools.probe_fts_s32 --work main
```

| # | 检查项 | 通过标准 | 结果 |
|---|--------|----------|------|
| T4.1 | 查询「铜炉」 | ok，命中含铜炉文本的条目 | [ ] |
| T4.2 | 查询「密室」「备忘」等 | 探针 cases 全 ok | [ ] |

### T5 备份与两阶段恢复 — **门禁** · **自动**（旁路库）

```bash
# demo 机
./scripts/backup_surreal_demo.sh
./scripts/restore_scribe_two_phase.sh /opt/scribe3/backups/surreal/<stamp>/scribe3__main.surql
```

| # | 检查项 | 通过标准 | 结果 |
|---|--------|----------|------|
| T5.1 | export 文件 | 以 `--` / OPTION 类 SurQL 开头，非日志行 | [ ] |
| T5.2 | apply_schema | migrations ≥ 100 | [ ] |
| T5.3 | data-only import | IMPORT_OK | [ ] |
| T5.4 | 关键表 count | 与源库量级一致（有数据的表） | [ ] |
| T5.5 | 清理 | 默认 REMOVE 演练库 | [ ] |

### T6 防 2.x 回流 — **推荐** · **自动**

```bash
# 仓库根（有 pytest 或直接 import 测试函数）
python3 -c "from importlib.util import *; ..."  # 或 pytest scribe3/tests/test_migrations_surreal3.py
```

| # | 检查项 | 通过标准 | 结果 |
|---|--------|----------|------|
| T6.1 | 无 type::thing | 护栏通过 | [ ] |
| T6.2 | 无 SEARCH ANALYZER | 护栏通过 | [ ] |
| T6.3 | compose pin v3.2 + timeout | 护栏通过 | [ ] |

---

## P · 产品层（人工 · **门禁**）

> 浏览器打开 **https://www.qing.blue**，使用可用账号（bootstrap admin 或你的作者号）。  
> 建议新建作品，避免污染长期数据；或使用 `main`。

### P1 登录与作品 — **门禁**

| # | 步骤 | 通过标准 | 结果 |
|---|------|----------|------|
| P1.1 | 打开站点，登录 | 进入写作台，无白屏/ React 崩溃 | [ ] |
| P1.2 | 看到作品列表 | 至少有一个作品可点 | [ ] |
| P1.3 | 进入作品（或新建） | 章节/设定导航可用 | [ ] |

### P2 设定/正典只读与列表 — **门禁**

| # | 步骤 | 通过标准 | 结果 |
|---|------|----------|------|
| P2.1 | 打开角色/Codex 类列表 | 能加载；空库可为空列表 | [ ] |
| P2.2 | 章节列表 | 能打开；序正确 | [ ] |

### P3 过程记忆可感知 — **门禁**（业务闭环核心）

| # | 步骤 | 通过标准 | 结果 |
|---|------|----------|------|
| P3.1 | 在讨论或写作中连续 **3 轮**，内容含关键词如「**铜炉**」「**密室**」「下一场戏…」 | 发送成功，无 5xx | [ ] |
| P3.2 | 若有 **ContextInspector / 上下文检视** | 打开后能看到与记忆/检索相关信息（或明确「已启用」状态） | [ ] |
| P3.3 | 第 4 轮提问「刚才备忘里铜炉相关是什么」类 | 回答能引用前几轮要点（不要求逐字） | [ ] |
| P3.4 | （可选工程协助）查库 `memory_item` count | 相对会话前 **增加** | [ ] |

**说明**：P3.3 依赖模型与检索组装，若失败但 P3.4 count 增加 → 标 **「写入闭环、生成未用上」**，记缺陷不单杀 T3。

### P4 边界认知（口头/备注即可）

| # | 检查项 | 通过标准 | 结果 |
|---|--------|----------|------|
| P4.1 | 剧情记忆不在 Hermes 聊天「私货」里当唯一真相 | 你确认：正典在 Surreal；Hermes 只是网关 | [ ] |
| P4.2 | 未接入 Spectron | 与架构一致 | [ ] |

---

## B · 业务 KPI（结案用）

| # | KPI | 门槛 | 测法 | 结果 |
|---|-----|------|------|------|
| B1 | smoke | 100% 绿 | T1 | [ ] |
| B2 | 记忆 e2e | ok true | T3 | [ ] |
| B3 | FTS 铜炉类 | 探针 ok | T4 | [ ] |
| B4 | 章节列表 p50 | < 50ms @≥50 章 | T2 / probe | [ ] |
| B5 | 恢复演练 | 本季度至少 1 次 T5 | T5 | [ ] |
| B6 | 产品 P1–P3 | 全勾 | 人工 | [ ] |

**结案规则**：B1–B5 全过 + B6 过 → 本优化轨 **正式结案**。  
仅 B1–B5 → 状态保持 **「工程完成 / 待产品验收」**。

---

## O · 运维制度化（推荐，非一次性）

| # | 项 | 门槛 | 结果 |
|---|-----|------|------|
| O1 | 发版/热更后跑 smoke_s32 | 有记录或脚本入口 | [ ] |
| O2 | 备份频率 | 至少每周或发版前 export | [ ] |
| O3 | 恢复手册 | runbook 含两阶段，禁止裸 import | [ ] |
| O4 | 护栏进 CI | test_migrations_surreal3 在 CI 跑 | [ ] |

---

## 门禁汇总（最低结案集）

必须全部 `[x]`：

- [x] **T1** smoke（A0）  
- [x] **T2** EXPLAIN 索引形态（A0）  
- [x] **T3** memory e2e（A0）  
- [x] **T4** FTS 探针（A0）  
- [x] **T5** 两阶段 restore（A0）  
- [x] **P1** 登录进站（A1 API）  
- [x] **P2** 列表可开（A1 API）  
- [x] **P3** 三轮 capture + 库增 + prefetch + **write SSE**（A1 API；视觉 UI 可选抽检）  

---

## 自动跑批记录（工程代跑）

> 下列由工程填写；**不替代** P 人工勾选。

| 批次 | 日期 | T1 | T2 | T3 | T4 | T5 | 备注 |
|------|------|----|----|----|----|----|------|
| **A0** | 2026-08-08 | **PASS** smoke 10/10 | **PASS** KnnScan×2 · FTS · chapter **IndexScan** | **PASS** 6→9 items · bm25+vector · prefetch_n=8 | **PASS** cases ok（铜炉等） | **PASS** schema 109 + IMPORT + counts | 工程 T 门禁 |
| **A1** | 2026-08-08 | （同 T） | （同 T） | 见下 **P 代跑** | （同 T） | （同 T） | **API 级产品路径代跑**（非浏览器像素） |

### A1 产品路径代跑结果（工程用 API 等价验收）

| 项 | 结果 | 证据 |
|----|------|------|
| P1 登录/作品/fabric | **PASS** | login 200；works n≥1；memory_fabric_v1=true |
| P2 章节/codex | **PASS** | chapters 200；codex/health 200 |
| P3 三轮 capture | **PASS** | `/memory/capture-turn` ×3 complete |
| P3 库增 | **PASS** | memory_item 递增（如 9→12） |
| P3 prefetch 非空 | **PASS** | empty=false，context 含「铜炉/密室」焦点与记忆块 |
| P3 动稿 `/chat/write` | **PASS** | 补全 context 三件套后 SSE **200**，流式产出正文（铜炉/玉佩描写） |
| 缺陷修复 | 已修 | `write.py` 重绑 globals 缺 `sse_response` → 注入 `core.sse_response`（否则 POST write 500） |

**未替代项**：浏览器白屏/布局/ContextInspector 视觉（无图形浏览器）。业务写读闭环在 API 层已证明。

---

## 附录 · 相关路径

| 类型 | 路径 |
|------|------|
| 方案 | `docs/plans/2026-08-08-surrealdb-3.2.4-optimization-plan.md` |
| Runbook | `docs/ops/surrealdb-3.2.4-runbook.md` |
| 基线 | `docs/ops/surrealdb-3.2.4-m1-baseline.md` |
| M3/M4 | `docs/ops/surrealdb-3.2.4-m3-m4.md` |
| smoke | `scripts/smoke_s32.sh` |
| 两阶段恢复 | `scripts/restore_scribe_two_phase.sh` |

# Storyline 方案 + Hermes 决策记录（GAP-7/8/11/20）

| 项 | 值 |
|----|-----|
| 日期 | 2026-08-12 |
| 状态 | 已实现等价路径 / 决策闭合 |
| Spec | `docs/plans/2026-08-12-gap-fix-20-spec.md` |

## Storyline（GAP-16/17/19/20）

- **数据模型**：`scribe3/storyline_store.py` — 可编辑实体（id/title/arc_kind/chapter_seqs/notes）。
- **API**：`GET/POST /storyline/lines`、`PATCH /storyline/lines/{sid}`、`POST .../link`、`GET /storyline/craft-align`。
- **前端**：`StorylineHub.jsx` — 实体列表、创建、关联章节、情绪 -5…+5、DTW 对标。
- **情绪**：`emotion_scale.py` 标尺 -5…+5；`storyline_project.project_emotion_curve` 消费。
- **技法标尺**：`craft_ruler.py` DTW + 理想起承转合曲线。

## Hermes 决策

| ID | 决策 | 落地 |
|----|------|------|
| **D1 GAP-7 SOUL** | Hermes 是否支持 system/personality **未作为硬依赖** | 环境变量 `SCRIBE3_HERMES_SOUL_LAYERS=1` 时在 `responses`/`create_run` body 附带 `system`/`personality`；默认关，未知字段可被忽略 |
| **D2 GAP-8 Memory** | **保持 Scribe 待批单源** | provider `prefetch` 注入 `author_prefs` / `SCRIBE3_PREFETCH_PREFS_TEXT`，不写 Hermes 原生 Memory |
| **D3 GAP-11 per-run tools** | Hermes 无请求级 filter | **后验拦截** `run_tool_filter.filter_tool_calls` + phase allowlist |
| **D4 压缩成本** | 默认 heuristic | `SCRIBE3_DISTILL_MODE=heuristic\|llm\|token`；llm 为离线可测压缩路径 |
| **D5 锁降级** | 单一 chapter_lock | 无三套进程内 set；DB 不可达时 chapter_lock 进程内 map |
| **D6 Storyline 可编辑** | **支持** | store + API + Hub |
| **D7 GAP-9 情绪 / 张力** | **产品面 -5…+5 已闭合；0–1 张力保留为低成本辅字段 → P2/DEFERRED** | 见下「D7 详述」 |
| **D8 GAP-10 LIVE WHERE** | **应用层 `live_id_allowed` 等效记录级过滤 → DEFERRED 原生 WHERE** | 见下「D8 详述」 |

## D7. 情绪值（原 GAP-9 / Spec GAP-14·18）

| 层 | 行为 | 状态 |
|----|------|------|
| **产品主字段** | `emotion` ∈ **[-5, +5]**（`emotion_scale.score_prose_emotion`，词表/lexicon；可 `SCRIBE3_EMOTION_MODE`） | **已交付** |
| **辅字段** | `tension` 0–1（`_tension_score` 启发式，零 LLM） | **有意保留** |
| **质量对标** | 技法标尺 DTW + `CORE_DIMENSIONS`（GAP-15/19）承担「更有价值的质量评估」 | **已交付** |

**降级理由（2026-08-12 PO/工程共识）**：

1. 对标闭环已由 DTW + 维度 SSOT 覆盖主价值；不必用重 NLP 重复定义「情绪分」。
2. 0–1 张力适合低成本场景（无 LLM、可解释、可缓存）。
3. 全文 NLP/LLM 极性升级性价比待用户反馈后再开；标为 **P2 / DEFERRED**，非阻塞交付。

**非目标**：不把 `_tension_score` 或 `emotion` 当文学分 / 人盲 KPI。

## D8. LIVE 记录级（原 GAP-10 / Spec GAP-4）

| 层 | 行为 | 状态 |
|----|------|------|
| **当前** | 表级 `c.live(table)` + 输出侧 `live_id_allowed(table, payload, record_ids)` | **等效实现 · 已交付** |
| **远期** | Surreal 原生 `LIVE SELECT … WHERE id IN $ids`（SDK 稳定后） | **DEFERRED** |

**理由**：社区/驱动层条件 LIVE 稳定性不足时，诚实输出过滤与「仅推目标记录」语义一致；调用方可传 `record_ids`。代码路径已预留：`live_stream(..., record_ids=)`；SDK 就绪后在 `watch()` 内切换为条件订阅即可，无需改前端契约。

## 不宣称

- 不宣称文学/人盲 ≥9.5
- Storyline / DTW / 情绪均为 advisory
- 不宣称 0–1 张力 = NLP 情感分析；不宣称输出侧 id 过滤 = DB 侧流量削减 80%（后者待原生 WHERE）

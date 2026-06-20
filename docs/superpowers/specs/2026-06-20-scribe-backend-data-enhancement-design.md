# Scribe 后端数据支撑增强 · 设计 Spec

**日期**:2026-06-20
**关系**:前端产品级重构([2026-06-20-scribe-ui-rebuild-design.md](2026-06-20-scribe-ui-rebuild-design.md))的**配套后端**。前端的关系图谱与质量趋势若无这些增强,会渲染成扁平/空白。
**原则**:**只加字段 / 加端点 / 加表 —— 不破任何现有接口契约**(全部 additive)。复用现有 `db.py` / `memory.py` / `metrics.py` / `orchestrator` 模式。

## 1. 背景

经查证,3 个前端数据面被后端卡住:
- `entity_relations` 仅 src/dst/relation/valid_from,无类型/类别/权重/方向 → 关系图是"扁平球"。
- 无质量时序表,`work_quality_report` 实时算横截面 → 质量"随时间/修订趋势"无数据。
- 关系/时间线/状态仅在"接受章节→ingest"时由 LLM 抽取 → 旧书/未 ingest 的书全空,缺批量入口。

## 2. 增强一 · 关系丰富化

**Schema(ALTER TABLE,SQLite 增列,向后兼容)**:`entity_relations` 增
- `src_type TEXT` / `dst_type TEXT` —— 实体类型(角色/地点/阵营/物品/组织/概念)
- `relation_category TEXT` —— 关系类别(亲属/敌对/盟友/师徒/爱慕/从属/因果/其它)
- `weight REAL DEFAULT 1.0` —— 强度(出现次数或 LLM 估)
- `directed INTEGER DEFAULT 1` —— 是否有向

**抽取(`memory.py` ingest 提示扩展)**:JSON schema 增 `src_type/dst_type/category/strength/directed`;鲁棒解析补默认值(缺失则 type=未知、category=其它、weight=1、directed=1),不因字段缺失丢整条。

**DB / API**:`add_relation()` 增可选参数;`list_relations()` 返回新字段(additive,前端按需用)。`GET /relations` 契约不变,仅多字段。

**去重/累加**:同 (work, src, dst, relation) 已存在则 `weight += 1`、刷新 `valid_*`,避免重复边。

## 3. 增强二 · 质量历史(时序)

**新表 `quality_snapshots`**:
```
id TEXT PK, work_id TEXT, scope TEXT,        -- 'global' | 'chapter'
chapter_seq INTEGER,                          -- scope=chapter 时
words INTEGER, slop_density REAL,
consistency_score REAL, foreshadow_payoff REAL,
cost_usd REAL, created_at TEXT
```

**落点**:接受章节 / ingest 时写一笔(该章 + 全书 global),带时间戳 → 趋势随"修订/时间"累积。

**DB**:`add_quality_snapshot()` / `list_quality_snapshots(work_id, scope, upto)`。
**API(新增,additive)**:`GET /works/{id}/quality/history?scope=global|chapter` → 时序数组,供前端趋势图。

> 现 `GET /quality`(横截面)保留不变;history 是新增。

## 4. 增强三 · 批量分析全书

**端点(新增)**:`POST /works/{id}/analyze` —— 遍历全部有快照的章,逐章 `ingest_chapter`(抽取摘要/关系/时间线/状态)+ 写 `quality_snapshot`;填满空书。
- **幂等**:重跑前按章清理该章既有 char_states/timeline/relations(或 upsert),避免重复堆积。
- **成本**:每章 1 次 LLM;百章=百次,作为**显式用户动作 + 进度**;可走后台任务(复用 orchestrator/SSE 模式),返回任务态而非阻塞。
- **响应**:`{analyzed: n, relations: x, events: y, states: z}` 或任务 id。

## 5. 迁移与兼容

- `entity_relations` 增列、`quality_snapshots` 建表:启动时 `CREATE TABLE IF NOT EXISTS` + 幂等 `ALTER TABLE ... ADD COLUMN`(包 try/except,列已存在则跳过)。
- 旧数据:既有关系行新列为 NULL/默认,前端容错;跑一次 `/analyze` 即补全。
- **不动**:现有 70+ 端点签名与返回结构;仅新增 2 端点、加若干可选字段。

## 6. 测试

- `entity_relations` 增列后 `add_relation`(含类型/类别/权重)+ 去重累加 + `list_relations` 返回新字段。
- `quality_snapshots` 建表 + add/list + `GET /quality/history`。
- `POST /analyze` 在多章书上跑通,幂等重跑不堆重复,计数正确。
- 回归:现有 `test_agent_tables` / `test_metrics` / `test_orchestrator` 全过。

## 7. 非目标

- 不改既有端点契约 / 不删字段。
- 不做向量化关系推理、不做跨书图谱(单书范围)。
- 关系类型/类别用**轻枚举 + LLM 归类**,不建本体库(YAGNI)。

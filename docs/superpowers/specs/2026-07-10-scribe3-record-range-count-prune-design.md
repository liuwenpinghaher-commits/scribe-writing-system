# Scribe3 章节 Record Range、COUNT 索引与单书数据收敛设计

**日期：** 2026-07-10  
**仓库：** `/Users/miaoma/Downloads/写作 3.0`  
**业务子目录：** `scribe3/`  
**目标书：** 《纸命》（`book_c256380e`）

## 1. 目标

1. 将可以由章节 record id 顺序表达的读取改为 SurrealDB record range，使执行计划从 `TableScan` 收敛为 `RecordIdScan`。
2. 对章节总数和未归档章节总数建立 `COUNT` 索引；未归档计数必须命中 `IndexCountScan`，无条件全表计数在 SurrealDB 3.1.5 中验收 `ready` 索引与内建 `CountScan` 快路。
3. 收敛 NS=`scribe3` 的历史数据：只保留《纸命》数据库及其全部表、记录和新建单书备份，删除其他书库、测试库、探针库、注册记录、旧混合备份和非《纸命》运行日志。

## 2. 已验证的现状

- 正在运行的 SurrealDB 二进制版本为 `3.1.5 for macos on aarch64`。
- 《纸命》唯一注册项为 `book_c256380e`。
- 《纸命》当前 6 章的 record id 为 `chapter:1` 至 `chapter:6`；`meta::id(id)` 均为 `int`，且逐条与 `seq` 相等。
- 现有 `recent_proses()` 使用 `FROM chapter WHERE seq < $s`，真库 `EXPLAIN` 显示 `TableScan`。
- 等价的 `FROM chapter:..5` 真库 `EXPLAIN` 显示 `RecordIdScan`。
- 裸 `SELECT count() FROM chapter GROUP ALL` 使用 `CountScan`；带未归档条件的计数当前使用 `TableScan`。
- namespace 当前除 `_reg` 外有 10 个数据库：《纸命》 1 个和待删除库 9 个。
- `~/.scribe3-backups` 下有两份旧全库备份；`~/.scribe3-loop-journals` 下有 `main` 和 `loop-qa` 历史日志。

## 3. 方案选择

采用“《纸命》单库保险 → 代码与 Schema 迁移 → 真库验证 → 数据收敛 → 最终对账”的两阶段清理方案。

不采用以下方案：

- 先删库后改代码：缺少修改期间的单书回退点。
- 先给所有旧库应用迁移后再删除：对必然删除的数据产生无意义写入，并扩大失败面。

## 4. Record Range 设计

### 4.1 不改 record id

不执行章节 record id 重写。《纸命》已符合数值有序 id 前提，重写只会引入不必要的正文主表风险。

### 4.2 范围目标构造器

在 `scribe3/store.py` 增加一个仅供章节读查使用的内部辅助函数，负责生成以下目标：

- 全表 record id 范围：`chapter:..`
- 小于某章：`chapter:..{before_seq}`
- 闭区间：`chapter:{start_seq}..={end_seq}`

动态边界不能直接在 `chapter:$start..=$end` 中绑定，SurrealDB 3.1.5 对该形状返回 parse error。因此辅助函数先确认边界为正整数，再将十进制整数拼入目标字面量；不接受字符串、`bool`、浮点数或非正数。

### 4.3 查询迁移边界

迁移可以保持现有语义的章节读取：

- `list_chapters()`、`chapters_lite()`、`causal_debt_total()`、`max_chapter()`、跨章一致性正文收集、归档章列表、`outline()` 和需要遍历 chapter 的回填查询，从 `FROM chapter` 改为 `FROM chapter:..`。
- `recent_proses(before_seq, k)` 改用 `chapter:..{before_seq}`，保留末端不包含和归档过滤语义。
- 新增闭区间轻量取章方法，pilot 连写启动时一次获取 `start_seq..=until_seq` 的已有章节集合，避免逐章发出存在性查询。
- 直接点查保留 `type::record('chapter',$seq)`；该形状比 record range 更精确。
- HNSW 向量查询保留 `FROM chapter WHERE embedding <|...|>`，防止 record range 目标破坏向量索引计划。
- `count()` / `sum()` 聚合不改为 record range，分别由 COUNT 索引和缓存列聚合承担。

## 5. COUNT 索引设计

新增顺序为 `075` 的迁移，不修改已存在的 `072` 至 `074` 未提交迁移：

```surql
DEFINE INDEX IF NOT EXISTS idx_chapter_count
  ON chapter COUNT;

DEFINE INDEX IF NOT EXISTS idx_chapter_active_count
  ON chapter COUNT
  WHERE archived = NONE OR archived != true;
```

查询形状必须与索引匹配：

- `stats()` 将未归档章节数拆为独立的 `SELECT count() ... WHERE archived = NONE OR archived != true GROUP ALL`，使用 `idx_chapter_active_count`。
- 跨章一致性指纹将全表章节数拆为独立的 `SELECT count() ... GROUP ALL`，使用 `idx_chapter_count`。
- `math::sum(qc_word_count)` 仍需读取缓存整数列，不声称 COUNT 索引会加速求和。
- 章节删除影响清单中的 `$seq` 动态条件计数不建 `COUNT WHERE`；固定 COUNT 索引无法命中任意章参数，无效索引只会增加写成本。

## 6. 数据收敛设计

### 6.1 清理前保险和对账基线

1. 记录《纸命》所有表的记录数、章节 id/seq 对应、关键主表计数和章节正文摘要指纹。
2. 使用官方 `surreal export` 导出 NS=`scribe3` / DB=`book_c256380e`。
3. 导出先落在旧备份目录之外的临时路径，校验文件非空后再进入清理阶段，避免删除旧备份时误删新备份。

### 6.2 真库迁移

1. 仅对 `book_c256380e` 执行 `apply_schema()`。
2. 等待两个 COUNT 索引构建完成，确认 `INFO FOR INDEX` 状态可用。
3. 对范围取章、全章取章和两种计数查询执行 `EXPLAIN`。
4. 重跑《纸命》对账基线；任一指标变化就停止删库。

### 6.3 删除范围

保留：

- NS=`scribe3` / DB=`book_c256380e` 的全部表和记录。
- DB=`_reg` 中 `slug = 'book_c256380e'` 的唯一注册记录。
- 本轮新建的《纸命》单库备份。

删除：

- `__codex_probe_20260709__`
- `book_5ce0a5c4`
- `book_bfd18b78`
- `book_x`
- `codex_hermes_e2e_20260710`
- `loop-qa`
- `main`
- `material_inject_test`
- `tmp_advproof_img`
- `_reg.work` 中除 `book_c256380e` 外的所有记录
- `~/.scribe3-backups` 中现有两份旧全库备份
- `~/.scribe3-loop-journals/main`
- `~/.scribe3-loop-journals/loop-qa`

数据库删除使用显式库名白名单，不根据模糊前缀或现场枚举结果盲删。执行前再次确认白名单不含 `book_c256380e` 和 `_reg`。

### 6.4 清理后放置单书备份

旧备份删除并验证目录为空后，将临时《纸命》导出移入新的 `~/.scribe3-backups/<timestamp>/book_c256380e.surql`。新目录不含其他库导出。

## 7. 错误处理与中止条件

- 《纸命》单库导出失败或文件为空：不执行任何删除。
- 任一 TDD 用例失败：不应用生产迁移，不执行数据删除。
- 《纸命》真库迁移失败、索引未 ready 或 `EXPLAIN` 未命中目标 scan：不删除其他数据。
- 《纸命》迁移前后对账不一致：不删除其他数据，保留单库导出供恢复。
- 某个待删库删除失败：立即停止后续删除，报告已删和未删列表；不重试《纸命》。
- 旧备份或日志删除失败：数据库结果不回滚，如实报告残留路径。

## 8. TDD 与验证

### 8.1 RED

先增加会在现状下失败的用例：

- 范围目标拒绝非正整数、`bool` 和反向区间。
- 闭区间包含起止章，允许中间缺号，不返回区间外章节。
- `recent_proses()` 保持“小于 `before_seq`、最近 k 章、最终升序”的现有语义。
- 归档章节仍不进入正常章节列表和前文读取。
- pilot 区间已有章节一次预取，缺失章仍按旧语义创建。
- Schema 应包含两个 COUNT 索引。

### 8.2 GREEN

只实现足以使上述用例通过的辅助函数、查询改造、pilot 预取和 `075` 迁移，不进行无关重构。

### 8.3 执行计划验证

在隔离测试库和《纸命》真库都执行：

- 全章和有界范围查询的 `EXPLAIN` 包含 `RecordIdScan`。
- 无条件全章 COUNT 索引状态为 `ready`，且 `EXPLAIN` 使用内建 `CountScan` 快路、不出现 `TableScan`。SurrealDB 3.1.5 即使显式 `WITH INDEX idx_chapter_count` 也会保留该计划。
- 未归档计数的 `EXPLAIN` 包含 `IndexCountScan`。
- 合并 `count()+sum()` 的查询不作为 COUNT 索引验收证据，因为该形状会进入 `TableScan`。

### 8.4 回归验证

1. 范围查询、store 章节生命周期、pilot 和 migration/index 定向用例。
2. store 相关用例组。
3. 仓库 Python 全量回归；失败必须区分本次回归与已有工作树失败。
4. 《纸命》真库只读烟测：书列表、章节列表、第 1 至 6 章区间读取、stats 和关键主表计数。

## 9. 最终验收标准

- `INFO FOR NS` 中只剩 `_reg` 和 `book_c256380e`。
- `_reg.work` 中只有 `{slug: 'book_c256380e', title: '纸命'}`。
- 旧全库备份和 `main` / `loop-qa` 日志不存在。
- 新备份目录中只有《纸命》导出，文件非空。
- 《纸命》章节仍为 `chapter:1` 至 `chapter:6`，且 id 与 `seq` 一致。
- 《纸命》清理前后表计数、正文摘要指纹和关键业务读取一致。
- record range 查询命中 `RecordIdScan`。
- 无条件章节计数索引为 `ready` 且计划为 `CountScan`；未归档章节计数命中 `IndexCountScan`。
- 定向测试和全量回归结果被完整记录，任何失败如实报告。

## 10. 交付边界

- 本任务允许修改代码、测试和新增 migration，并执行用户已明确批准的数据删除。
- 不丢弃或覆盖工作树中与本任务无关的已有修改。
- 未经要求不 commit、不 push、不建分支。

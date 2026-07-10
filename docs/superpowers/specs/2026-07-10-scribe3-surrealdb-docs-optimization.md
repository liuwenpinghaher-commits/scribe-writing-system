# scribe3 SurrealDB 官方文档对照优化(2026-07-10)

> 依据:`docs/external/surrealdb-docs/`(853 页全量抓取,2026-07-09)+ surrealdb-py 2.0.0
> 源码实测 + SurrealDB 3.1.5 二进制实测。姊妹篇:2026-07-09 Hermes v018 审查文档。

## 证据基线

- SDK 实测:`BlockingWsSurrealConnection._send` 仅在 `socket is None` 时懒建 TCP;
  **signin/use 是 WS 连接级状态,懒重连不会重放**——任何掉线都是永久失败,
  这就是 2026-07-04 :8001 事故"后端必须重启"的根因。官方 Python 文档明确:
  无内建重连,须自行捕获连接类异常后重建连接(reference/python/concepts/error-handling)。
- 官方备份通道是 `surreal export`(一致性导出 SurrealQL 脚本);surrealkv 写入中
  热拷贝 data.db 目录不保证一致(running/file-backed、cli commands/export)。
- 写语句默认 `RETURN AFTER`(回传修改后整条记录);批量/大字段写官方建议
  `RETURN NONE` 免序列化返回体(statements/upsert:538-558、performance-best-practices:174)。
- `UPSERT <table> SET …` 无 ID 无 WHERE 时**永远新建**(v2.0.5+ 语义,最大坑);
  带显式 record id 才是"存在则更新"(statements/upsert:37-77)。
- 运维护栏:`--slow-log-threshold <duration>`(help 文本写 ms,3.1.5 实测要 duration
  形式如 `500ms`)、`--query-timeout`、`--transaction-timeout`(cli commands/start)。
- 事务模型:快照隔离,写写冲突后提交者失败须重试;事务保持短小(transactions-and-isolation)。

## 已落地(全部真机验证)

### S-1 连接韧性(:8001 事故根治)
- `store.py`:新增 `_connect/_reconnect/_raw_query` 单点——连接类异常白名单
  (`websockets.WebSocketException`/`ConnectionUnavailableError`/`OSError`/`EOFError`)
  → 重建连接(重放 signin/use)→ 重试一次;语法/校验错误绝不重试。
  全部 `self._db.query` 调用点(_query/_execute_write/apply_schema/grant_public)已收口。
- 本机 WS 无"已提交但响应丢失"分区窗口(服务端死=写未提交),且核心写为
  显式 id 的 UPSERT 幂等 → 写路径重试一次可接受(代码注释有论证)。
- 测试:`tests/test_store_reconnect.py` 4 项——socket 掐断读/写自愈、
  **整库进程同端口重启自愈**、非连接错误不重试。
- 真机验收:重启生产 :8001 后,后端**不重启**,`/ready` 与纸命 `/facts` 直接自愈。

### S-2 备份机制(生产库此前零备份)
- 新增 `scripts/surreal_backup.sh`:枚举 ns=scribe3 全部 db(书)→ 逐书
  `surreal export` 到 `~/.scribe3-backups/<时间戳>/<书>.surql`,保留最近 14 份
  (`SCRIBE3_BACKUP_KEEP` 可调;轮转用 `sort -r | tail -n +N`,BSD head 无负数)。
- 真机:11 本书全部导出成功(纸命 4.2MB / main 1.9MB / 铜炉试炼 2.1MB…),轮转正常。
- 恢复命令在脚本头注释(`surreal import --ns scribe3 --db <书> <文件>`)。

### S-3 热写路径 RETURN NONE
- `save_chapter`(回传含正文+512维向量+QC缓存)、`save_chapter_draft`(UPSERT 只改
  draft 但默认回传整章含向量)、`add_chat_message`(每轮)、`upsert_ai_run_trace`
  (每个 SSE 事件,raw_events 越滚越大)四个最热写点加 `RETURN NONE`。
  `_execute_write` 本就丢弃返回值,行为零变化,省 WS 序列化/传输。

### S-4 运维护栏(生产 :8001 重启携带)
- 新启动命令(已生效,写入 DEPLOY.md):
  `--slow-log-threshold 500ms --query-timeout 60s --transaction-timeout 30s --log info`,
  日志落 /tmp/scribe3-surreal.log。坑:`--slow-log-threshold` help 说毫秒数,
  3.1.5 实际要 duration(`500`→报 invalid duration,`500ms` 才对)。
- 清理 8 个上周六泄漏的内存测试 surreal 孤儿进程。

### 审计结论(查过,无需改)
- **裸 UPSERT 坑**:全仓审计,所有 UPSERT 均带显式 record id(`type::record(...)`/
  `intent:main`/`meta:manuscript`),无"无 ID 无 WHERE 永远新建"踩坑点。
- 索引覆盖:23 个迁移文件已定义 40+ 索引(含 HNSW×4、FULLTEXT+自定义分析器),
  热查询字段(chapter.seq UNIQUE/proposition.entity_id/chat_message.chapter 等)已覆盖。
- 中文 FTS:官方无 CJK 分词器(snowball 不含中文);本系统已用 jieba 预分词进
  tokens 字段 + FULLTEXT BM25,正是文档建议的 UDF/预处理路线,不动。

## 未采纳/留作后续(有依据的裁定)

- **记录范围查询替代 WHERE**(`chapter:1..=10` 免索引免表扫):需改 id 编码方案,
  属数据迁移级改动;单书章节数百量级收益小,不值风险。
- **COUNT 索引**:v3.0 已有 CountScan 快路径,现有计数查询规模小。
- **UPDATE/DELETE 不吃索引**(官方已知限制):`purge_ingest` 等删除操作作用于
  单书小表,暂不改 `DELETE (SELECT id …)` 子查询形。
- **CHANGEFEED/LIVE SELECT**:前端轮询目前够用;LIVE 仅单节点、不做聚合,
  若未来做多面板实时刷新再接。
- **SURREAL_SURREALKV_BLOCK_CACHE_CAPACITY 等内存调优**:默认(RAM/2-1GiB)
  对本机充裕,不动。
- **官方 agent-rules(.mdc)**:可选把 SurrealQL 规则文件放进 .cursor/rules 降低
  AI 生成 SurrealQL 的幻觉率;离线环境暂记不装。
- **数据目录迁名 ~/.scribe3-surreal**:用户决策项,未动(备份已缓解误删风险)。

## 验收

- `tests/test_store_reconnect.py` 4/4 绿;store 相关四套件 162 绿;全量回归见下。
- 真机:DB 重启后端自愈(/ready + 纸命 facts)、备份 11 书成功、护栏参数生效。

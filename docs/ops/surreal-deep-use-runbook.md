# Surreal 深度利用 · 运维 Runbook（demo / 可丢数据）

## 架构（最优）

| 层 | 机制 |
|----|------|
| **真表 CDC** | `proposition` / `chapter` / `material` / `memory_item` / `character` / `event` 建表即 `CHANGEFEED 1h INCLUDE ORIGINAL`（见 migrations 001/004/055/078） |
| **旁路双写** | `cache_watch`（125）+ `emit_invalidation(store=…)` / factory；consumer 同时 poll |
| **混合检索** | `SCRIBE3_HYBRID_SEARCH_NATIVE=1`：HNSW + tokens BM25 + `search::rrf`（扁平 `[{id,rrf_score}]`） |
| **章锁** | `SCRIBE3_DISTRIBUTED_LOCK=1` + store `try_create_inflight`；ingest 另有 `chapter_lock("ingest")` + lease |
| **观测** | `GET /health` → `changefeed` / `locks` / `surreal_flags` |

## Demo 推荐 env（`deploy/prod/.env`）

```
SCRIBE3_CHANGEFEED_CACHE=1
SCRIBE3_HYBRID_SEARCH_NATIVE=1
SCRIBE3_DB_INFLIGHT_LOCK=1
SCRIBE3_DISTRIBUTED_LOCK=1
SCRIBE3_DB_KNOWLEDGE_FRAME=1
SCRIBE3_STATS_VIEW=1
SCRIBE3_LIVE_GRANULAR=1
```

改 env 后 `compose recreate backend` **必须再** `./scripts/deploy_demo.sh hot`（热更靠 docker cp）。

## 库重建（数据可丢）

旧库 feed 冻住 / 无 CHANGEFEED 时：

```bash
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -m scribe3.tools.rebuild_db_native_changefeed --all --commit --yes
docker restart prod-backend-1
```

单库：`--db main`。会 `REMOVE DATABASE` + `apply_schema`。

**禁止**对生产有价值数据跑 `--all --commit`。  
**禁止**随意 `DEFINE DATABASE OVERWRITE … CHANGEFEED`（曾冻住 main feed）。

## 工程冒烟

```bash
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -m scribe3.tools.surreal_engineering_smoke --db main
# 期望 7+/N ok=True：rrf、CDC、dual-write、locks、hybrid、emit 合同
```

## Demo 种子（世界 + 可写章）

```bash
# 世界本体（角色/命题/事件）+ 第 1 章五阶段字段
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -m scribe3.seed_demo --db main

# 已有章也强制覆写大纲/节拍/草稿/正文
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -m scribe3.seed_demo --db main --force-chapter
```

验收（容器内）：

```bash
docker exec -e PYTHONPATH=/app prod-backend-1 python3 -c "
from scribe3.store import SurrealStore
st=SurrealStore(db='main')
ch=st.get_chapter(1)
assert ch and (ch.get('synopsis') or '').strip()
assert ch.get('beats') and (ch.get('prose') or '').strip()
print('writable_ok', ch.get('title'), ch.get('focalizer'), len(ch.get('prose') or ''))
"
```

- **世界**：焦三 / 老道 / 乱岗；私密「治眼」+ 读者知「追索」反讽点  
- **可写章**：synopsis、beats、scene_truth、draft、prose、focalizer=`role:焦三`

## 健康检查

```bash
curl -sS https://tonglu.example.com/api/health | jq .
# changefeed.alive、cursors 含真表、surreal_flags 全 true（demo）
```

## cache_watch 角色

- **补充**应用语义失效（跨表、未挂 feed 的写点、双写保险）
- **非唯一真相源**；真表 CDC 优先
- flag `SCRIBE3_CHANGEFEED_CACHE=0` 可关 worker（进程内 emit 仍失效本机缓存）

## 故障速查

| 现象 | 处理 |
|------|------|
| health db=down | 查 apply_schema / Surreal 日志；勿硬 DEFINE 已有 SCHEMAFULL |
| SHOW CHANGES 空 | 确认建表带 CHANGEFEED；旧库 rebuild |
| hybrid 全 Python 回退 | 查 rrf 入参为 `[{id}]`、返回扁平列表解析 |
| recreate 丢代码 | 再 hot |
| 锁永远 busy | cleanup inflight 脏行；检查 rid 对齐 |

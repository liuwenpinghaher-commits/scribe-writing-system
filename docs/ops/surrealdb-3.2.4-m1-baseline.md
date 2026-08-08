# SurrealDB 3.2.4 · M1 热路径基线 + M2 记忆闭环（实测）

> 环境：demo `prod-surreal-1` = **v3.2.4**，backend 内跑探针  
> 日期：2026-08-08  
> 负载作品：`perf_s32`（可销毁：`python -m scribe3.tools.seed_perf_fixture --destroy`）

## 1. 合成负载

| 项 | 数量 |
|----|------|
| character | 12 |
| proposition（含 embedding） | 20 |
| chapter | 10 |
| memory_item（capture） | 10 |
| seed 耗时 | ~5.5s（含 jieba/embed） |

脚本：`scribe3/tools/seed_perf_fixture.py`

## 2. 热路径 p50（warm 后 3 次，ms）

| 路径 | p50_ms | n |
|------|--------|---|
| list_characters | 0.76 | 12 |
| list_chapters | 1.03 | 10 |
| list_propositions | 2.09 | 20 |
| memory_items_active | 1.43 | 10 |
| semantic_recall | 2.93 | 5 |
| memory_vector | 1.92 | 5 |
| memory_bm25 | 1.28 | 5 |
| hybrid_recall | 5.27 | 5 |

结论：当前规模 **全部 < 10ms**，无 P0 延迟问题。

## 3. EXPLAIN（3.2.4）

| 查询 | plan_hint | 要点 |
|------|-----------|------|
| proposition `<|5,40|>` | **HNSW/KnnScan** | `index: idx_prop_vec`, k=5, ef=40, dim=512 |
| memory_item KNN + work/status | **HNSW/KnnScan** | `memory_embedding_idx` + Filter |
| memory BM25 `tokens @1@` | **FullTextScan** | `memory_fts_idx` |
| chapter ORDER BY seq | TableScan + topk_pushdown | 小表可接受 |

**D-022 复核通过**：生产用的 `<|K,EF|>` 在 3.2.4 上走 **KnnScan**，非暴力 TableScan。

## 4. T07 索引决策（本轮）

| 候选 | 决策 | 理由 |
|------|------|------|
| chapter.seq 索引 | **暂缓** | p50≈1ms；仅 TableScan+topk；等书到数百章再测 |
| 其它 | **不加** | 列表/KNN/FTS 已用现有索引且健康 |

## 5. M2 记忆闭环（work=`main`）

| 项 | 结果 |
|----|------|
| memory_item 0 → 3 | 是 |
| capture 3 次 | 全部 `complete` / episodic |
| memory_vector 命中 | 3 ids |
| MemoryRetriever.retrieve_full | selected=3，~9.6ms |
| ok | **true** |

脚本：`scribe3/tools/memory_e2e_s32.py`  
说明：bm25 对本组中文 query 可能 0 命中（分词/tokens 对齐），**向量 + retrieve_full 已证明闭环**。

## 6. 复跑命令（demo 机）

```bash
docker cp seed_perf_fixture.py prod-backend-1:/app/scribe3/tools/
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -u -m scribe3.tools.seed_perf_fixture
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -u -m scribe3.tools.probe_s32_hotpath --work perf_s32
docker exec -e PYTHONPATH=/app prod-backend-1 \
  python3 -u -m scribe3.tools.memory_e2e_s32 --work main
```

## 7. 更大负载复测（2026-08-08 续）

| 负载 | char 40 · prop 120 · chapter **80** · memory 40 |
|------|--------------------------------------------------|
| list_characters p50 | 0.81 ms |
| list_chapters p50 | **5.21 ms**（仍 TableScan+topk） |
| list_propositions p50 | 6.07 ms |
| semantic_recall | 6.47 ms · KnnScan |
| memory_vector / bm25 | 3.87 / 2.94 ms |
| hybrid_recall | **15.24 ms**（双路+融合，可接受） |

决策：落地 **109 idx_chapter_seq**、**110 idx_prop_valid_from**（预防性，新作品 apply_schema 即有）。

## 8. 下一步（可选）

- 千章级再 profile；hybrid 是否缓存 embedding  
- Python SDK 3 GA 评估

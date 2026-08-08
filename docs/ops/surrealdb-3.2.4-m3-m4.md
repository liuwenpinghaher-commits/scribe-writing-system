# M3 FTS 修复 + M4 备份恢复演练记录（2026-08-08）

## M3 · 全文检索

### 根因
jieba 对「铜炉」**单独**切为整词，**嵌在句中**常切为「铜」「炉」。索引与查询不一致 → BM25 查「铜炉」空命中。

### 修复
- 新增 `scribe3/text_tokens.tokenize_for_fts`：jieba + 词内字/bigram + 相邻单字跨词 bigram  
- 写入/查询统一：`add_memory_item`、`memory_bm25`、material FTS、supersede 重算  
- 存量：`python -m scribe3.tools.reindex_memory_fts`

### 探针结果（demo `main`，reindex 后）
| 查询 | ok | 命中 |
|------|-----|------|
| 铜炉 | ✅ | 2 |
| 密室 | ✅ | 1 |
| 备忘 | ✅ | 3 |
| 玉佩 | ✅ | 1 |
| 犹豫 | ✅ | 1 |
| 铜炉 密室 | ✅ | 1+ |

`memory_e2e`：bm25_ids 非空，vector + retrieve_full 仍绿。

### 检索权重默认（`settings.py`）
| key | default |
|-----|---------|
| memory.weight_structured | 2.0 |
| memory.weight_bm25 | 1.0 |
| memory.weight_vector | 1.0 |
| memory.weight_graph | 1.2 |
| memory.weight_recency | 0.8 |
| half_life_* | working 3d / episodic 30d / … |

本轮**不改默认权重**（探针通过即可）；需要偏全文时可把 `weight_bm25` 调到 1.2–1.5。

## M4 · 备份 / 恢复

### 已通过
| 项 | 结果 |
|----|------|
| export 到卷路径 `/data/export_*.surql` 再 `docker cp` | 清洁 SurQL（`-- OPTION IMPORT` 开头） |
| 备份目录 | `/opt/scribe3/backups/surreal/m4-clean/` 等 |

### 全量 import 旁路库
| 项 | 结果 |
|----|------|
| `surreal import` → 新 `restore_drill_*` DB | **失败**：`The field 'valid_from' does not exist` |
| 原因 | 3.2 export 的 SCHEMAFULL DEFINE 与行数据字段不完全对齐（运行时多 migration 叠层；export 快照的 FIELD 集不足） |

### 推荐恢复策略（scribe3）— **两阶段已跑通**
1. **逻辑备份**：`backup_surreal_demo.sh`  
2. **旁路/灾难恢复**：
   ```bash
   ./scripts/restore_scribe_two_phase.sh /path/to/scribe3__main.surql
   ```
   - 阶段 A：backend `create_work` + `apply_schema`（107 migration）  
   - 阶段 B：`surreal_export_data_only.py` 抽出 TABLE DATA（跳过 `_migration`）→ `surreal import`  
3. **不要**对全量 export（含不完整 DEFINE）直接 import 到空库  

### 两阶段演练结果（2026-08-08 demo）
| 步骤 | 结果 |
|------|------|
| apply_schema | migrations **107** SCHEMA_OK |
| data-only import | IMPORT_OK |
| character / memory_item | **1 / 6**（与源库一致） |
| _migration | 107 |
| 清理 REMOVE DATABASE | OK |

### 脚本
- `scripts/backup_surreal_demo.sh`  
- `scripts/surreal_export_data_only.py`  
- `scripts/restore_scribe_two_phase.sh`（**推荐**）  
- `scripts/restore_surreal_side_db.sh`（全量 import，易失败，仅作对照）  
- `scribe3/tools/probe_fts_s32.py` / `reindex_memory_fts.py`

# 延期产品 backlog 入口（O18–O23 / O30–O33）

安全禁令仍有效：不宣称文学 ≥9.5；默认不 hard park；不以 tokens_saved 为 KPI。

## 旗标（产品 soft **默认开**；硬门默认关）

| 旗 | 默认 | 含义 |
|----|------|------|
| `SCRIBE3_STORYLINE_UI` | **开** | 故事线 UI |
| `SCRIBE3_MULTI_HOP_GRAPH` | **开** | 事件图 k≥2 |
| `SCRIBE3_STAGE_MACHINE` | **开** | 章节阶段机（soft） |
| `SCRIBE3_STAGE_MACHINE_HARD` | **关** | 非法跳转 409（硬门，引导优先） |
| `SCRIBE3_PARALLEL_DEDUCE` | **开** | 并行演绎 plan |
| `SCRIBE3_AGENT_CRON_UI` | **开** | cron 产品面 |
| `SCRIBE3_BENCHMARK_LIB` | **开** | benchmark 库 |
| `SCRIBE3_STORYLINE_INJECT` | **开** | 写路径故事线 polish 段 |
| `SCRIBE3_SOFT_ACTIVATION` / `SOFT_PRECHECK` / `LITERARY_DISTILL` | **开** | P2 soft 能力 |

可用环境变量或设置页覆盖为 `0` 关闭。

## API

| 方法 | 路径 | 能力 |
|------|------|------|
| GET | `/storyline/gantt` | O30 Gantt 投影 |
| GET | `/storyline/emotion-curve` | O31 张力曲线 |
| POST | `/storyline/inject-preview` | O33 注入预览 |
| GET/POST | `/chapters/{seq}/stage` `/stage/advance` | O19 |
| POST | `/event-graph` body.`k` | O18 多跳 |
| POST | `/chapters/{seq}/deduce/parallel` | O22 plan |
| GET/POST | `/agent-crons` `/agent-crons/{name}/enable` | O23 |
| GET/POST/DELETE | `/benchmarks` | O32 |

## 前端薄面板

- `web/src/views/StorylineHub.jsx` — 跨章弧（参考）；挂在旅程底部，不占顶栏  
- `web/src/views/EventGraphPanel.jsx` — 多跳列表  
- `web/src/views/BenchmarkLibrary.jsx` — 参考库  
- 设置：Gateway/Admin 可链 cron 列表  

需登录；旗关时 UI 显示「未启用」。

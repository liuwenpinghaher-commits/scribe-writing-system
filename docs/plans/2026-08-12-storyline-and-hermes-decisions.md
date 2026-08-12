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

## 不宣称

- 不宣称文学/人盲 ≥9.5
- Storyline / DTW / 情绪均为 advisory

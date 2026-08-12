# Storyline 可视化与数据模型方案（GAP-16/17/19/20）

| 项 | 值 |
|----|-----|
| 日期 | 2026-08-12 |
| 状态 | 已实现 |
| Spec | `docs/plans/2026-08-12-gap-fix-20-spec.md` |

## 数据模型

- Surreal 表 `storyline`（migration `130_storyline.surql`）
- 字段：`title`, `arc_kind`, `chapter_seqs`, `notes`, `updated_at`
- Store mixin：`scribe3/store/storyline.py` → `SurrealStore`
- 降级：进程内 `storyline_store.py`（无 DB 时）

## API

| 方法 | 路径 |
|------|------|
| GET | `/storyline/gantt` |
| GET | `/storyline/emotion-curve`（emotion ∈ [-5,5]） |
| GET/POST | `/storyline/lines` |
| PATCH | `/storyline/lines/{sid}` |
| POST | `/storyline/lines/{sid}/link` |
| GET | `/storyline/craft-align`（DTW + CORE_DIMENSIONS） |

## 前端

- `StorylineHub.jsx` 使用 **recharts**（LineChart / BarChart）
- 情绪曲线主轴 -5…+5；理想曲线虚线叠加
- 维度轴分 bar 来自 `craft_ruler_report.core_dimensions`

## 对标算法

- `craft_ruler.dtw_distance` + `align_to_ideal`
- 维度 SSOT：`scribe3.quality.rubrics.CORE_DIMENSIONS`
- `emotional_effect` 轴映射 DTW 相似度

## 不宣称

- 非文学分、非 ≥9.5 证据

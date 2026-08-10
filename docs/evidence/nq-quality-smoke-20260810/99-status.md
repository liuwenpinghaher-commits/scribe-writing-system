# nq quality smoke · 2026-08-10

## 已完成（工程）

| 项 | 状态 |
|----|------|
| main 合入 nq 栈 + 卷章 IA | `9e39755` |
| demo hot 部署 | HEALTH 200 / ready true |
| 质量模式 env | 容器内已生效（见下） |
| migration `117_beats_meta.surql` | 已装入 backend 容器 |
| 新书 | `book_7d98d3b9`（炉灰记·质量模式冒烟） |

### 质量 env（demo 容器 printenv）

```
SCRIBE3_DRAMA_GATE=1
SCRIBE3_BEATS_SYNOPSIS_FALLBACK=0
SCRIBE3_CRAFT_NOVEL=1
SCRIBE3_PILOT_SOFT_PRESSURE=0
SCRIBE3_PILOT_SOFT_AI_GRADE=1
SCRIBE3_PARK_STROLL_BLOCKING=1
SCRIBE3_DRAMA_HARD_PRESSURE=4
SCRIBE3_BEATS_V2=1
SCRIBE3_DRAMA_GATE_COMPAT=0
SCRIBE3_PDC=1
SCRIBE3_PDC_BLOCKING=1
```

## 部分完成（连载）

| 项 | 状态 |
|----|------|
| ch1 草稿 | 版本库有 ~6597 字稿；pilot 在 draft_loop 因 advisory/422/502 未稳定 finalized |
| ch2 | 未完成 |
| 人读对照 book_013bcb3b | 待 ch1–2 finalized 后做 |

## 观察

1. 质量模式打开后 draft_loop 更「严/慢」；`SOFT_PRESSURE=0` + LLM 偶发 502 使 restore 链路易 thrash。
2. 一次样本 beat0 仍为 `{text}` 摘要形（兼容路径）；GCD v2 需在 expand 成功且 `BEATS_V2=1` 时复查。
3. `save-chapter` 曾 409（可能 lease/并发）；需人路径或脚本加强。

## 回滚质量 env

见 `deploy/prod/env.quality-mode-rollback.fragment` + 重启 backend。

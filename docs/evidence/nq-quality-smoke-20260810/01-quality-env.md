# 质量模式 env 快照

## 目标值（PR-10）

| Flag | 目标 |
|------|------|
| SCRIBE3_DRAMA_GATE | 1 |
| SCRIBE3_BEATS_SYNOPSIS_FALLBACK | 0 |
| SCRIBE3_CRAFT_NOVEL | 1 |
| SCRIBE3_PILOT_SOFT_PRESSURE | 0 |
| SCRIBE3_PILOT_SOFT_AI_GRADE | 1 |
| SCRIBE3_PARK_STROLL_BLOCKING | 1 |
| SCRIBE3_DRAMA_HARD_PRESSURE | 4 |
| SCRIBE3_BEATS_V2 | 1 |
| SCRIBE3_DRAMA_GATE_COMPAT | 0 |
| SCRIBE3_PDC | 1 |
| SCRIBE3_PDC_BLOCKING | 1 |

## Demo 生效确认

- [ ] 已写入 `/opt/scribe3/app/deploy/prod/.env`（备份 `.env.bak.*`）
- [ ] 已 `docker restart` / compose up backend
- [ ] 进程内快照（可选：容器 `novel_quality_flags_snapshot()` 或日志）

片段文件：`deploy/prod/env.quality-mode.fragment`

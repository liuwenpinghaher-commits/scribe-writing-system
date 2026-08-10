# 冒烟勾选（与脚本 checklist 同步）

生成：`./scripts/nq_quality_smoke_runbook.sh checklist`

```

对照书: book_013bcb3b（docs/evidence/v633-reval-20260810/）
样本:   铜炉同宇宙新卷（非无关新书）· 仅 2 章

前置
  [ ] PR-0…8 代码已热更 demo
  [ ] deploy/prod/.env 合并 env.quality-mode.fragment 并重启 backend
  [ ] migration 117_beats_meta 已应用（_migration + INFO FOR TABLE）
  [ ] curl /api/health 与 /api/ready = 200
  [ ] （可选）./scripts/smoke_s32.sh exit 0

质量旗生效（进程内）
  [ ] SCRIBE3_DRAMA_GATE=1
  [ ] SCRIBE3_BEATS_SYNOPSIS_FALLBACK=0
  [ ] SCRIBE3_CRAFT_NOVEL=1
  [ ] SCRIBE3_PILOT_SOFT_PRESSURE=0
  [ ] SCRIBE3_PILOT_SOFT_AI_GRADE=1
  [ ] SCRIBE3_PARK_STROLL_BLOCKING=1
  [ ] SCRIBE3_DRAMA_HARD_PRESSURE=4
  [ ] （推荐）BEATS_V2=1 · DRAMA_GATE_COMPAT=0 · PDC=1 · PDC_BLOCKING=1

连载 ch1–ch2（重；demo 机执行 · 勿 Grok 机默跑）
  [ ] 新书 slug 记入 03-book.md
  [ ] ch1 finalized 或可人读 prose → 04-serialize/ch01.md
  [ ] ch2 同上 → 04-serialize/ch02.md
  [ ] 每章 beats_meta.beats_source ≠ synopsis_segments
  [ ] 高压章 drama_validation 可审计
  [ ] E1 限知无帧外直说
  [ ] pressure soft 不再掩盖 blocking 终态

人读 / 人盲
  [ ] 戏剧推进中位 ≥4（对照基线）
  [ ] 比喻过多中位 ≤2
  [ ] 结果写入 05-human-read.md（真人；禁止 LLM 代填封顶）

收尾
  [ ] 99-status.md 写 PASS/FAIL + 缺口
  [ ] 若失败：合并 env.quality-mode-rollback.fragment 恢复可达
```

# 观测看板定义（第十轮，第十一轮板块一已可跑）

四个板块都能从现有接口或表里读到一部分；标了「需新增埋点」的，下一轮再补，不能拿空格子当已经在看。

推荐可视化：先用现有 debug 接口做简易脚本；量上来再进 Grafana。机器数字只给人看运行是否健康，**不得当作创作质量放行判据**。

## 1. 质量判定

| 指标 | 含义 | 数据来源 | 采集 |
| --- | --- | --- | --- |
| gate 触发率 | 走统一判定出口的章次 / 总判定章次 | 评价 JSON 的 `gate` 字段；旗 `SCRIBE3_QUALITY_GATE_UNIFIED` | 现有：评价 API 响应。按书按日计数即可 |
| vcode 分布 | pass / needs_human / fail 占比 | `playbook/pipeline.py` `_judge_vcode` 结果；关旗缺结论现默认 pass | 现有：写章 span / 判定日志。建议在 span 上记 `vcode`（已有则复用） |
| fail 原因 Top-5 | 人话原因出现次数 | `gate.message` / `hits`；作业 `error_message` | 现有字段。不要把空串当 fail（第十轮已修） |

**已可运行，已接入定时任务，日志持久化**：`python scripts/observability_quality_stats.py --book <book_id> --days 7`

默认打本机 `http://127.0.0.1:8000/debug/pipeline-events`。连不上时打印原因退出，不甩栈。铜炉上可把 `--base-url` 指到容器内后端。

可直接采：评价记录、质量作业状态、判定 span。需新增埋点：按日聚合的 vcode 直方图（若 span 尚未带该字段）。

## 2. 写作管线

| 指标 | 含义 | 数据来源 | 采集 |
| --- | --- | --- | --- |
| 执行时长 P50/P95 | 一章从开写到判定结束 | `GET /debug/pipeline-events`；`playbook_span_start` / `playbook_span_end` | 现有 span 墙钟。按 `step_key` 分位 |
| 重试率 | 同一章同一阶段重跑次数 | 质量作业 `retry`；playbook rewrite/force | 现有作业状态。需新增埋点：按章汇总 retry count |
| infra_fail 率 | 基础设施失败（解析/上游挂）占比 | `InfraError`；`label_playbook_fail` | 现有失败标签。按日 / 总章次 |

可直接采：pipeline-events、作业 queued/running/failed。需新增埋点：P95 预计算、infra_fail 日计数。

## 3. 反哺

| 指标 | 含义 | 数据来源 | 采集 |
| --- | --- | --- | --- |
| 成功率 | `ingest_status=ok` 的章 / 有反哺记录的章 | `chapter.ingest_status`；`GET /ingest/status` | 现有表字段 |
| 失败原因分布 | 失败条里的人话 | `ingest_message`（旧列已删） | 现有字段。按前缀或全文归类 |
| 平均设定学习条数 | 成功反哺时学到几条 | ingest 成功文案「学到了 N 条设定」；ingest 结果 `applied` | 现有文案可解析。更稳需把 `applied` 写成独立字段（需新增埋点） |

可直接采：ingest 状态接口。需新增埋点：结构化 `applied` 计数，避免从人话里抠数字。

## 4. 召回

| 指标 | 含义 | 数据来源 | 采集 |
| --- | --- | --- | --- |
| 精准召回命中率 | 问里至少命中一条设定的比例 | `GET /debug/recall-shadow`；写章/对话召回包 | 现有对照接口 |
| 空召回率 | 对得上的条数为 0 | 同上；写章 `codex_recall_empty` | 现有 |
| fallback 触发率 | 空召回后仍注入全景名片的比例 | 对话空召回 ADR；召回包是否保留名片 | 现有行为。需新增埋点：显式 `empty_fallback=true` 事件，便于按日统计 |

可直接采：`/debug/recall-shadow`、`/debug/pipeline-events?tag=recall_shadow`。需新增埋点：fallback 事件布尔字段。

## 与现有 playbook span 的关系

- **已能从 span / debug 接口直接采**：管线时长、失败标签、召回对照窗口、ingest 状态。
- **要新增埋点才好看板**：vcode 日分布、retry 按章汇总、applied 结构化计数、空召回 fallback 布尔。

## 部署

- 每日脚本：`deploy/prod/scripts/observability_cron.sh`
- systemd：`deploy/prod/systemd/scribe3-observability.timer` + `.service`（每天 03:00）
- 日志目录：`/var/log/scribe3/observability/quality_stats_YYYY-MM-DD.json`（可用 `OBSERVABILITY_LOG_DIR` 改）
- 环境变量：`SCRIBE3_ROOT` 指向包含 `scribe3/` 的目录；`EnvironmentFile=/etc/scribe3/env`
- Grafana 数据源：JSON file，指向 `/var/log/scribe3/observability/`
- Grafana 模板：`deploy/prod/grafana/quality-stats-panel.json`（gate 触发率 / vcode 分布 / fail Top-5 表）

### 前置要求

> systemd service 使用 `EnvironmentFile=/etc/scribe3/env`。首次部署前必须创建此文件：
>
> ```bash
> sudo mkdir -p /etc/scribe3
> sudo tee /etc/scribe3/env <<'EOF'
> SCRIBE3_ROOT=/opt/scribe3/app
> OBSERVABILITY_LOG_DIR=/var/log/scribe3/observability
> # 按需追加其他环境变量（如 SURREALDB_URL）
> EOF
> sudo chmod 600 /etc/scribe3/env
> ```
>
> 若该文件不存在，`scribe3-observability.service` 将在 timer 首次触发时立即失败（systemd 不会静默忽略缺失的 EnvironmentFile）。

机器数字只给人看运行是否健康，**不得当作创作质量放行判据**。

# Grafana 质量观测面板导入 Runbook

## 前置条件
- Grafana ≥ 7.0 已部署（demo/prod 机）
- JSON file datasource 插件已安装（`grafana-cli plugins install marcusolsson-json-datasource`）
- `/var/log/scribe3/observability/` 目录已创建且有数据（cron 至少执行过一次）
- `/etc/scribe3/env` 文件已创建（见 observability-dashboard.md §前置要求）

## 步骤

1. 创建 JSON 数据源：
   - Grafana → Configuration → Data Sources → Add → JSON
   - URL: `file:///var/log/scribe3/observability/`
   - Save & Test

2. 导入面板模板：
   - Grafana → Dashboards → Import
   - Upload JSON file: `deploy/prod/grafana/quality-stats-panel.json`
   - 选择刚创建的 JSON 数据源
   - Import

3. 验证：
   - 面板显示 gate 触发率 / vcode 分布 / fail Top-5
   - 数据非空（至少有 1 天的 JSON 文件）

## 完成标志
- 面板可正常加载
- 截图保存至 `docs/evidence/grafana-import-live.png`
- round13-debts.md 标记"Grafana 导入=已完成"

# Hermes 管理台入口(Dashboard Entry)设计文档

日期:2026-07-12
状态:已与作者确认方向,待实施
背景:作者要求对 Hermes 进行系统化管理(模型/服务商/agent/skill/MCP/cron 等全部)。经调研,Hermes 官方 Web Dashboard(`hermes dashboard`)即机器级管理面:一个服务管理机器上全部 profile(侧边栏切换器,Config/API Keys/Skills/MCP/Models 页跟随;深链 `?profile=<name>`;本机 127.0.0.1 默认免鉴权),Models 页含服务商密钥、模型选择、自动模型列表、11 辅助槽与用量分析。已确认路线:**薄层 + 官方 Dashboard**——scribe3 不重建任何 Hermes 管理能力,只做入口与网关进程管控(后者 Dashboard 明确不管,已由设置中心网关区承担)。

## 已确认决策

1. 「模型与服务商」不在 scribe3 自建(原 gateway_models.py CRUD 方案整体取消),由 Dashboard Models 页原生承担。
2. scribe3 侧交付物 = 一张「Hermes 管理台」入口卡 + 网关卡片显示当前主模型(只读)。
3. Dashboard 进程由 scribe3 可一键拉起(nohup + 轮询铁律),不自动随 scribe3 启动。

## 交付内容

### 1. 后端(app.py + 复用 gateway_files 的 config 解析)

| 端点 | 语义 |
|---|---|
| `GET /gateway/dashboard/status` | 探活 Dashboard(默认 `http://127.0.0.1:9119`,新设置项 `gateway.dashboard_url` 登记 REGISTRY/restart 类;`<500` 即在线,同 /gateway/status 语义) |
| `POST /gateway/dashboard/start` | 预检 hermes CLI 存在 → nohup `hermes dashboard --no-open >> /tmp/scribe3-hermes-dashboard.log 2>&1 &` → 轮询 ≤30s → 如实报成败与日志路径;登记 KNOWN_REST_WRITE_ROUTES(danger:拉起进程) |
| `GET /gateway/model-summary` | 只读:解析三份 config.yaml(root/scribe3/scribe3_write)的 `model:` 节,返回 `{gateway, provider, default_model}` ×3;密钥不解析不返回;root 配置读取需把 `~/.hermes/config.yaml` 纳入 gateway_files 白名单**只读**路径(不开放写,写仍限两 profile) |

### 2. 前端(设置中心网关分区)

- 分区顶部「Hermes 管理台」卡:状态灯(在线/未运行)+ 未运行时「启动管理台」按钮(ConfirmDialog)+ 在线时快捷深链按钮组:模型与服务商(`/models?profile=…`)、Skills、MCP、Cron、会话——每链对三 profile 用 Dashboard 侧边栏切换器,默认深链 `?profile=scribe3`;深链用 `<a target="_blank">`。
- 三张网关状态卡各加一行「主模型:{provider} · {model}」(来自 /gateway/model-summary,拉取失败静默省略,fail-soft)。

### 3. 防护与测试

- 测试全 mock(subprocess/httpx/sleep),绝不真启 Dashboard、不碰真实 ~/.hermes(tmp HERMES_HOME 夹具);model-summary 白名单扩展有越界测试(root config 只读,PUT 仍 403)。
- 真机验收:启动真 Dashboard 一次 → 状态灯变绿 → 深链打开 Models 页确认 profile 切换器可用 → 网关卡显示主模型 doubao-seed-2.0-pro。

### 4. 明确不做

- 不在 scribe3 内建服务商 CRUD/模型选择器/辅助槽 UI/skill/MCP/cron 管理(Dashboard 原生);后续某领域痛点真实再逐个评估搬入。
- 不自动随 scribe3 拉起 Dashboard;不做 Dashboard 鉴权配置 UI(本机免鉴权;远程暴露场景见官方文档)。

### 5. 风险

| 风险 | 缓解 |
|---|---|
| Dashboard 默认端口非 9119 或本机未装 dashboard 依赖 | 端口做成设置项;start 失败如实报日志路径(官方会提示缺什么依赖) |
| root config.yaml 纳入白名单引入写风险 | 只读专用解析路径,写白名单不变,越界测试钉死 |

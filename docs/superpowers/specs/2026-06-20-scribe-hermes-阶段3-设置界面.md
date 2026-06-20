# 阶段3 · 系统设置界面 Spec(融合 hermes dashboard)

**目标**:一个设置界面,透出所有必要系统配置、可增删改查,**融合新版 hermes 的 web dashboard**(管 config/API key/session)。对应用户最初需求。

## 关键简化(因新版有 dashboard)
新版 `hermes dashboard` 已是 web 配置界面 + `hermes config`(show/set/edit/migrate)是结构化配置 API。所以从"手搓 hermes 配置"简化为**对接**。

## 架构(两块配置,一个界面)
- **scribe 自身配置**(模型路由/成本预算 SCRIBE_COST_BUDGET/审查间隔/嵌入模型):scribe 后端补 `GET/PUT /config` 端点(读写持久化配置,取代硬编码/env);前端设置视图增删改查。
- **hermes 配置**(provider/模型/key/base_url):经 `hermes config` API(或子进程 `hermes config set/show`)读写;或在设置界面**嵌入/链接 hermes dashboard**(iframe/新窗,`hermes dashboard --port`)。
- **统一设置视图**:web-app 新增设置入口,两块分区(scribe 配置 / hermes 配置)。

## 待定(实现前确认)
- hermes dashboard 能否嵌入(iframe/CORS)还是只能链接打开
- `hermes config` 的程序化读写接口(CLI 子进程 vs HTTP)
- 哪些配置该透出 vs 敏感不透出(DB 路径不透;key 透但脱敏)

## 验收
- 设置界面能改 scribe 模型路由/成本/审查 并生效
- 能管 hermes 的 provider/模型/key(经 config API 或嵌入 dashboard)
- 增删改查完整;敏感项保护

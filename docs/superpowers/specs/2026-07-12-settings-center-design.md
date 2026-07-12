# scribe3 统一设置中心(Settings Center)设计文档

日期:2026-07-12
状态:已与作者确认方向,待实施
背景:整个系统没有配置界面。全局约 20 个环境变量、6 个灰度 flags、约 15 个后端阈值常量只能改 env/代码并重启;每书设置与个人偏好有部分 UI 但碎片化散落在 8 处组件里。目标:所有必要的系统设置全部展现、充分管控。

## 已确认的四个关键决策

1. **管控深度:全部可改 + 热生效。** 新建 DB 配置权威源,界面改完立即生效;天然需要重启的项(如 DB 连接)标注"重启后生效"并显示待生效状态。
2. **覆盖边界:Hermes 网关全纳入,含文件编辑。** 三网关地址/状态、profile 的 config.yaml、SOUL.md、.env 都可在界面查看与编辑,提供一键重启网关。
3. **工艺阈值只做全局。** 检测器阈值、记忆检索权重不按书覆盖;题材差异仍由既有题材规则层(genres)处理。
4. **安全兜底选全套。** secrets 掩码不回显;每项显示出厂默认 + 单项/整区一键恢复;修改写审计日志;高危项二次确认;文件编辑自动备份。

## 方案选型

选定 **方案 A:配置注册表 + DB 权威源 + 热生效**。

- 否决方案 B(界面写 .env + 重启生效):不满足热生效,"已改未生效"中间态是长期困惑源。
- 否决方案 C(仅 flags/阈值迁 DB 的混合最小化):"哪些能在线改"的边界靠记忆,不满足"充分管控"。

A 的核心理由:配置获得单一权威源;注册表驱动 UI(界面永不落后于配置项);注册表模式与本仓既有纪律(写路由台账 `KNOWN_REST_WRITE_ROUTES`、门禁测试)同构,可加"未登记配置项即测试红"的门禁,配置从此不再散落。

## 架构

### 1. 后端配置层(`scribe3/settings.py`,新文件)

**配置注册表**:模块级声明式清单,每项字段:

| 字段 | 说明 |
|---|---|
| `key` | 唯一名,沿用现 env 名(如 `SCRIBE3_DAILY_CALL_CAP`)或新造点分名(阈值类,如 `critique.banned_density_per_k`) |
| `category` | 七分区之一(见 UI 节) |
| `type` | int / float / str / bool / secret / enum / list[str] |
| `default` | 出厂默认值(即现代码里的常量/env 默认) |
| `validate` | 校验规则(范围/正则/枚举);写入前强制 |
| `effect` | `hot`(热生效)/ `restart`(重启后生效) |
| `secret` | 是否敏感项(DB 存真值供内部使用;GET/审计对外一律掩码,永不回显明文) |
| `label` / `desc` | 界面显示名与一句话说明(中文) |

**存储**:单文件 SQLite(`~/.scribe2-surreal/scribe3_settings.sqlite3`,env `SCRIBE3_SETTINGS_DB` 可改),表 `setting`(key/value/updated_at)只存被改过的覆盖值,`setting_audit` 存审计(时间、key、旧值→新值;secret 项只记"已变更",绝不落明文)。

> 为什么不用 SurrealDB:①自举悖论——DB 连接参数本身是设置项,却要先连上 DB 才能读到;②设置须跨进程共享(app :3321 与 MCP stdio 进程),仓内 `usage.py` 日帽台账已验证同目录单文件 SQLite 范式,直接沿用;③读侧 fail-soft:SQLite 不可用时告警一次并回落 env/默认值,系统照常工作。

**restart 类项的生效机制**:读点不改(仍读 env);进程启动最早期调用 `settings.apply_restart_overrides()` 把 DB 覆盖值灌进 `os.environ`,随后各模块按原路径读取——DB 是持久层,env 是进程内生效层。`pending_restart` = DB 值 ≠ 当前进程 env 值。

**读取优先级**:`system_setting` 表 → 环境变量 → 注册表 default。env 降级为"初始默认",部署级覆盖仍有效,一旦界面改过则 DB 赢。

**`get_setting(key)`**:带进程内缓存(dict),`PUT` 写入后同进程内立即失效重建;启动时全量预热一次。secrets 读取返回真值(供内部使用),对外序列化一律掩码。

**读点改造**(机械迁移,约 40 处):

- `context_cache.flag_enabled()` → 改读 `get_setting`(6 个灰度 flags 热切换的关键);
- `llm.py`:模型名、timeout、`_MAX_RETRIES`、`_DAILY_CALL_CAP` 常量改为函数内 `get_setting()` 调用;
- `critique.py`:约 15 个阈值常量(`_BANNED_DENSITY_PER_K`、`find_near_duplicate_paragraphs` 的 sim/min_len、副词密度、排比门槛等)改为默认参数从 `get_setting()` 取;
- `memory_retrieval.py`:`CHANNEL_WEIGHTS`、`HALF_LIFE_DAYS`;
- `app.py`:CORS、`SCRIBE3_LIVE_MAX`、`SCRIBE3_API_TOKEN` 等(CORS/token 属 restart 类,读点不动,仅注册表登记以便展现)。
- **不改造**:测试专用 env(`SURREAL_BIN`)、journal 目录类低频项——登记注册表标 restart,读点维持 os.environ。

**门禁测试**:注册表完备性——扫描代码中 `os.environ/getenv` 的白名单比对,新增 env 读取未登记注册表即红(同 `KNOWN_REST_WRITE_ROUTES` 范式)。

### 2. REST 端点(app.py)

| 端点 | 方法 | 语义 |
|---|---|---|
| `/settings` | GET | 全量:每项 value(secret 掩码)+ 来源(db/env/default)+ default + 元数据 + pending_restart 标记 |
| `/settings/{key}` | PUT | 校验 → 写 `system_setting` → 写审计 → 缓存失效;返回新值与生效方式 |
| `/settings/{key}/reset` | POST | 删除 DB 覆盖值(回落 env/default),写审计 |
| `/settings/audit` | GET | 审计日志(倒序分页) |
| `/gateway/status` | GET | 三网关(8642/8643/8644)探活 + profile 名 + 版本 |
| `/gateway/files` | GET | 白名单文件列表与内容:`~/.hermes/profiles/{scribe3,scribe3_write}/{config.yaml,SOUL.md,.env}`(.env 内密钥行掩码) |
| `/gateway/files` | PUT | 写前自动备份 `<file>.bak.<ts>`;路径白名单外一律 403;返回写入 diff 摘要 |
| `/gateway/restart` | POST | nohup 后台拉起 + 轮询探活(铁律:Hermes 起停必须 nohup 后台 + 轮询),返回轮询结果 |

全部写路由登记进 `KNOWN_REST_WRITE_ROUTES` 台账,授权语义注释齐全。`PUT /settings/{key}` 对 secret 项:请求带明文、存储即掩码化(存真值于 DB 但 GET 永不回显,审计不落明文)。

**restart 类项的待生效状态**:GET /settings 对 restart 项同时返回"当前进程生效值"与"DB 已保存值",两者不等即 `pending_restart: true`,前端亮黄标。

### 3. 前端设置中心(web/src/settings/)

**入口**:顶栏(AppRail)齿轮图标 → 横切视图 `sel.mode='view', viewKey:'settings'`(与图谱/时间线/仪表盘同通道,复用 2026-07-12 修复的 I-2 视图旁路补记链路;栏2 隐藏、栏3 全画布)。

**布局**:左侧分区导航 + 右侧表单区。七分区:

| 分区 | 内容 | 生效 |
|---|---|---|
| ① 连接与服务 | DB URL/用户/密码、CORS、API token、SSE 并发配额、journal 目录、默认 work | 多为 restart |
| ② LLM 与用量 | 模型名、超时、重试、**每日调用日帽**、台账路径;内嵌现 `/ai/usage` 用量面板 | 热 |
| ③ 工艺阈值 | critique 约 15 项检测器阈值 + 记忆检索权重/半衰期(全局) | 热 |
| ④ 灰度开关 | 6 个 flags(统一上下文/主编线程/记忆织网/检查器/Spectron 影子/装配器),开关即生效 | 热 |
| ⑤ Hermes 网关 | 三网关状态灯+地址+profile;config.yaml / SOUL.md / .env 在线编辑(带备份与 diff);一键重启 | 重启网关 |
| ⑥ 本书设置 | 现 intent 全字段(reader_feeling/emotional_arc/red_lines/overdue_threshold/total_word_goal/daily_word_goal),走既有 `PUT /intent` | 热 |
| ⑦ 个人偏好 | 主题、四/三栏布局、护栏默认、衬线字体、脉搏静音清单、重排确认重置等 localStorage 碎片集中管理(仍存 localStorage) | 即时 |

**每个设置项的通用控件**:当前值编辑器(按 type 渲染)+ 来源徽章(默认/env/已自定义)+ 出厂默认值提示 + 单项恢复按钮;分区级"全部恢复默认"。表单由 `GET /settings` 的元数据驱动渲染,前端不硬编码配置项清单。

**高危项二次确认**(ConfirmDialog,复用现组件):灰度 flags 开关、日帽修改、网关文件保存、网关重启、整区恢复默认。

**审计页**:分区导航底部"变更历史"入口,渲染 `GET /settings/audit`。

### 4. 数据流与错误处理

- 写入失败(校验不过/DB 挂):表单就地红字报错,不落库不生效;fail-soft 不崩视图。
- 网关重启失败:轮询超时后显式报"重启失败,原进程状态未知",给出日志路径;绝不静默假成功。
- 文件编辑冲突:PUT 带读取时的内容 hash,后端比对失配返回 409(文件已被外部修改),前端提示重新加载。
- `/settings` 拉取失败:设置视图整体降级为错误态+重试按钮,不影响其余系统。

### 5. 测试

- 注册表门禁:未登记 env 读取 → 红(新 test_consistency 用例);
- settings CRUD 单测:优先级(DB>env>默认)、校验拒绝、reset 回落、审计落表、secret 掩码不回显(GET/audit 双路径);
- 热生效:改日帽/阈值后,下一次 `llm 调用/critique 检测`即用新值(patch scribe3.llm 防烧真网关——本仓测试铁律);
- 网关文件:白名单外 403、写前备份存在、hash 失配 409;
- 前端:设置视图渲染(元数据驱动)、二次确认流、pending_restart 黄标、恢复默认;vitest + 既有 harness;
- 真机验收:改一个阈值→立即在 /draft-check 生效;开一个 flag→`/capabilities` 反映;SOUL.md 改一行→重启→新人格生效。

### 6. 明确不做(YAGNI)

- 不做多用户/权限体系(单机单作者);
- 不做配置导出/导入(git + DB 备份已覆盖);
- 不做阈值按书覆盖(决策 3);
- 不做 Hermes skills 目录的 UI 管理(工程资产,进 git);
- 不迁移测试专用 env(`SURREAL_BIN` 等)的读点。

### 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 40 处读点迁移引入回归 | 机械迁移分批提交;全量 1566 后端测试 + 门禁;flags 迁移前后跑金丝雀对比(本仓已有金丝雀书) |
| flags 从 env 改 DB 后,"默认全关=字节等价"承诺 | DB 无覆盖值时读取路径与现状完全一致(env→默认),等价性由现有 flag 回归用例守护 |
| 网关文件在线编辑写坏 config | 自动时间戳备份 + diff 预览 + hash 冲突检测;重启失败可用 .bak 手动回滚 |
| secret 经网络明文提交 | 本系统仅绑 127.0.0.1;界面提示;审计不落明文 |

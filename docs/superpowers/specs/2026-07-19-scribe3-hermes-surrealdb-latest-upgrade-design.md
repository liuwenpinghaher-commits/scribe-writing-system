# Scribe3 Hermes Agent 与 SurrealDB 最新版本安全升级设计

**版本：** 1.0  
**日期：** 2026-07-19  
**状态：** 用户已授权升级，待实施计划  
**关联规格：** `2026-07-19-scribe3-hermes-official-evidence-cache-and-usage-audit-design.md`

## 1. 目标与当前结论

用户要求把 Hermes Agent 和 SurrealDB 升级到最新版本。本规格把“最新”定义为执行开始时从官方来源解析并冻结的目标，而不是在长时间实施过程中不断追逐移动分支。

当前只读取证已经确认：

| 组件 | 本机事实 | 官方最新目标 | 本轮动作 |
|---|---|---|---|
| SurrealDB Server | 运行进程和磁盘二进制均为 `3.2.0 for macos on aarch64` | 最新稳定 release `v3.2.0` | 不重复覆盖；完成3.2.0生产兼容与恢复验收 |
| SurrealDB Python SDK | `2.0.0` | 官方包索引最新 `2.0.0` | 不升级；完成服务端3.2.0兼容回归 |
| Hermes稳定发布 | `v0.18.2 (2026.7.7.2)` | 最新稳定 release仍为`v2026.7.7.2` | 稳定版号已相同 |
| Hermes官方主干 | 本地HEAD `bd740f203...`，官方检查显示落后1034提交 | 执行时冻结的官方`main` SHA | 按官方 updater 升级到固定 main SHA并做全量兼容验收 |

用户要求的 Hermes“最新版本”在当前事实下不能解释为“最新稳定标签”，否则不会发生升级。因此本设计解释为：**升级到执行时冻结的官方 main 最新提交**。这是有意采用主干版本，风险高于稳定发布，必须经过隔离 canary、完整备份和可恢复切换。

## 2. 安全红线

- 不直接修改或删除 `~/.scribe2-surreal/data.db`。该路径虽然名称遗留，但承载当前 Scribe3 生产库。
- 不在没有逻辑导出和恢复演练的情况下停止或替换生产 SurrealDB。
- 不使用 `git reset --hard`、`git clean`、强制推送或手工删除数据目录。
- 不让 `hermes update` 静默覆盖本地 dirty 文件或未跟踪技能。
- 不在 Hermes Dashboard、三个 Gateway 和 MCP watchdog 仍使用旧 venv 时原地改依赖。
- 不使用 `--no-backup`、`--force` 或 `--force-venv`。
- 不打印、缓存、提交或比较 secret 值；只验证引用存在和运行时认证成功。
- 不把升级完成等同于业务完成；升级后必须重新验证真实模型、SSE、审批、记忆、工具和小说业务路径。
- 任何阶段失败立即停止晋级，保留失败现场和旧版本服务，不带病进入生产切换。

## 3. 官方目标冻结

升级执行开始时生成 `upgrade-targets.json`，至少保存：

- SurrealDB 官方最新稳定 tag、release URL、发布时间、资产哈希；
- SurrealDB 当前二进制和运行服务版本；
- Python SDK当前版本和官方最新稳定版本；
- Hermes官方最新 release tag；
- Hermes `origin/main` 解析 SHA；
- Hermes当前HEAD、二进制版本输出和updater检查结果；
- 解析时间和来源URL；
- 对应官方文档快照ID。

目标一旦冻结，本次升级不再因上游新提交而变化。若实施过程中官方 main 继续前进，新提交进入下一轮，而不是中途改变验收对象。

## 4. SurrealDB 工作流

### 4.1 当前运行形态

当前生产实例：

- 本地原生进程；
- 监听 `127.0.0.1:8001`；
- 使用 SurrealKV 持久化目录 `~/.scribe2-surreal/data.db`；
- Scribe3 通过 WebSocket RPC 连接；
- namespace 为 `scribe3`，每部作品一个 database；
- 测试另起内存实例和随机端口，不得复用生产 `:8001`。

HTTP `/health` 响应头已经证明正在运行的服务是 `surrealdb/3.2.0`，因此磁盘二进制版本和进程版本一致，不存在“文件已升级、旧进程仍未重启”的假升级。

### 4.2 为什么仍需验收

仓库中的部分历史文档和实现假设仍写着 SurrealDB 3.1.5。虽然服务已经运行在3.2.0，但没有一份与当前整套代码、全部迁移、查询计划、备份恢复和五万字业务流程绑定的正式升级验收证据。

本轮 SurrealDB 的任务因此是：

1. 把版本事实修正为3.2.0；
2. 证明现有生产数据可被官方逻辑导出和恢复；
3. 证明全部 schema/migration 和关键 SurrealQL 在3.2.0成立；
4. 证明 Python SDK 2.0.0 与服务端3.2.0的真实路径兼容；
5. 重新探测索引、record range、CountScan/IndexCountScan、事务和实时行为；
6. 把3.2.0新增能力作为候选优化审计，而不是无条件启用实验功能。

### 4.3 升级前生产备份

即使当前已是目标版本，也必须生成新的升级基线备份：

- 用官方 `surreal export` 逐数据库导出；
- 导出清单包含 namespace、database、文件字节、SHA-256、开始/结束时间和结果；
- 备份中不得打印认证信息；
- 单本失败则整批状态失败；
- 保留生产数据目录的只读文件系统元数据，不复制正在写入的SurrealKV目录充当一致性备份；
- 备份路径不得位于即将操作的数据目录内。

### 4.4 恢复演练

恢复必须使用隔离目标：

- `mktemp -d` 创建临时持久化目录；
- 使用随机空闲端口；
- 用同版3.2.0二进制启动隔离实例；
- 逐库 `surreal import`；
- 对比数据库集合、迁移集合、关键表行数、正文/章节版本、正典命题、知识边、上下文/记忆和trace数量；
- 对每部重要作品抽样读取正文哈希和关键业务对象；
- 运行只读一致性检查和关键查询；
- 关闭临时实例后验证可再次启动。

临时目录只有在演练结果、日志和校验清单完整保存后才能清理；清理属于单独、可确认的回收动作。

### 4.5 3.2.0兼容回归

至少覆盖：

- 全部 `.surql` migration 在空库从零执行；
- 生产导出副本上的增量 migration；
- 多语句 `query_raw` 逐条错误检查；
- `RecordID`绑定、`RELATE`、UPSERT、事务；
- record range字面量和参数边界；
- count planner与索引ready状态；
- BM25、向量/HNSW、图召回和RRF；
- live query与断线重连；
- export/import；
- `/status`、`/health`、`/ready`三种健康语义；
- 读写超时和慢查询配置；
- Python SDK同步WebSocket连接、认证和命名空间切换；
- 14本或当前全部作品的只读统计与一致性检查。

### 4.6 3.2.0新能力采用边界

`/ready` 可用于修正 Scribe3 readiness，但GQL、Surrealism、文件桶、versioned engine等实验能力不因升级而自动启用。每项新能力仍须通过 Creative Context OS 的上下文贡献合同和生产安全审计。

## 5. Hermes升级工作流

### 5.1 当前安装风险

当前 Hermes：

- 安装目录为 `~/.hermes/hermes-agent`；
- 当前分支为 `main`，HEAD 为 `bd740f203...`；
- 官方 updater 报告落后 `origin/main` 1034提交；
- `package-lock.json` 有本地修改；
- 有9个未跟踪的 `skills/meeting-*.md` 文件；
- Dashboard、default Gateway、scribe3 Gateway、scribe3_write Gateway和MCP watchdog正在使用当前 venv。

这些本地改动和运行进程意味着不能直接执行一次无人值守的 `hermes update -y`。

### 5.2 本地改动保护

升级前必须：

1. 保存 `git status --short`、当前HEAD和分支；
2. 对 tracked diff 生成补丁并计算哈希；
3. 把未跟踪技能复制到独立备份清单，保留相对路径和内容哈希；
4. 检查目标main是否已经包含同名文件；
5. 对相同路径内容冲突做三方比较，不静默选任一方；
6. 把用户文件与上游文件分开保存；
7. 升级后逐项恢复或迁移，验证文件哈希和Hermes技能发现结果。

meeting技能可能已经在最新主干成为上游文件。若如此，必须比较本地版本与上游版本，保留本地内容，不让Git pull因未跟踪文件冲突或自动覆盖而丢失。

### 5.3 升级前快照

至少保存：

- `hermes --version`；
- 当前仓库HEAD、分支、remote和dirty文件清单；
- `hermes update --check`；
- Hermes venv依赖冻结清单；
- 三profile非敏感配置摘要；
- skills、plugins、cron、hooks、fallback和MCP清单；
- 三Gateway capability、toolset和工具数量；
- 当前SOUL、USER、profile配置和cron资产的官方备份；
- 现有安全审计结果；
- 当前Scribe3 Hermes smoke结果；
- 当前Responses和Runs基准样本。

官方 `hermes update --backup` 必须启用，同时保留一份独立于updater的安装与配置恢复锚。任何备份不得包含可提交的secret副本。

### 5.4 隔离canary

生产安装变更前，在临时目录用冻结的main SHA建立隔离canary：

- 独立源码目录和venv；
- 独立 `HERMES_HOME`；
- 使用复制后去敏、端口改写的三个profile；
- 使用随机/预留canary端口，不碰8642/8643/8644；
- 只挂Scribe3隔离测试库和测试work；
- 不读写生产正文和canon；
- 运行upstream自检、doctor、安全审计和CLI帮助；
- 运行Scribe3 provision dry-run；
- 探测Responses、Runs、SSE、Approval、Sessions、Skills、Memory Provider和MCP工具面。

canary必须捕获接口差异，生成 `old_runtime → new_runtime` 合同差异：

- endpoint和请求字段；
- capability名称；
- SSE event名称和载荷；
- approval请求值；
- profile/toolset解析；
- session continuation；
- memory/context plugin生命周期；
- provider/model/usage字段；
- 错误码和重试语义。

### 5.5 兼容修复顺序

若canary发现不兼容：

1. 先在Scribe3写失败测试；
2. 修复兼容适配层，不修改业务权威；
3. 保留旧事件/字段兼容，除非官方明确删除且旧运行时不再支持；
4. 重新运行canary；
5. 通过后才允许生产切换。

重点审查：

- `HermesRuntime` headers和HTTP合同；
- `HermesEventAdapter`事件归一；
- `/ai/runs/{id}/approval` choice映射；
- SSE保持与刷新恢复；
- profile级MCP读写隔离；
- Tool Search是否改变工具名或事件；
- `Scribe3MemoryProvider`基类与生命周期；
- prompt/context compression行为；
- DeepSeek实际供应商证明和fallback；
- trace中的usage、tool output和write effect。

### 5.6 生产切换

只有canary、代码回归和备份恢复全部通过后：

1. 停止接收新的Hermes Runs；
2. 等待或显式终止现有长任务，保存未决审批和run状态；
3. 优雅停止Dashboard和三个Gateway；
4. 确认Hermes venv没有残留持有进程；
5. 再次保存即时备份和dirty文件清单；
6. 使用官方 updater 的备份模式升级到冻结main；
7. 不使用force类参数；
8. 重新应用Scribe3受管profile overlay；
9. 恢复并核对本地技能；
10. 重启default/read/write三个Gateway；
11. Dashboard只在核心网关验证后恢复；
12. 记录新二进制版本、HEAD、依赖和服务进程身份。

升级期间预期有Hermes服务窗口；SurrealDB无需停止，因为本轮没有版本替换。

### 5.7 安全与供应链复验

此前Hermes venv做过定向安全补丁，上游update可能重装依赖并重新引入旧pin。升级后必须：

- 运行 `hermes security audit`；
- 对比升级前后依赖和漏洞；
- 运行 `pip check`；
- 不因主程序可启动就忽略依赖倒退；
- 若出现上游已知脆弱pin，先判断官方兼容修复，再做最小定向补丁；
- 定向补丁后重新运行三个Gateway和全量smoke。

## 6. 联合回归矩阵

### 6.1 基础设施

- SurrealDB `/status`、`/health`、`/ready`；
- 全部数据库可连接；
- Hermes三Gateway health/capabilities；
- default/read/write profile工具面正确；
- 后端 `/health`、`/ready`、`/ai/runtime-status`；
- 前端构建并连接新后端。

### 6.2 数据与上下文

- 正文、章节、设定、事实、知识边和素材读取；
- BM25、向量、图和混合召回；
- `ContextRequest/Manifest/Envelope`兼容路径；
- 会话工作摘要和跨会话召回；
- Memory Provider生命周期；
- 不串work、不泄漏POV、不把Hermes memory当canon。

### 6.3 Hermes业务路径

- 普通补全；
- Responses流式文本；
- MCP只读工具；
- Runs写任务；
- approve与deny双通道；
- stop；
- 断线重连和刷新恢复；
- tool output、usage、trace和write effect；
- provider/model/fallback可见性；
- skills和SOUL身份；
- cron、backup和security smoke。

### 6.4 创作业务

- 主编讨论；
- 章节上下文组装；
- 草稿生成；
- 设定/事实待批写入；
- 质量分析和证据定位；
- 参考作品比较；
- 修订建议与接受/拒绝；
- 至少一个隔离作品的完整章节流程；
- 最终五万字流程在整体系统验收阶段重新执行。

## 7. 验收门

### U0 目标门

新Hermes HEAD必须等于冻结的官方main SHA；SurrealDB运行时必须继续为官方最新稳定3.2.0。

### U1 数据门

所有生产数据库导出成功，恢复演练成功，关键计数和抽样哈希一致。

### U2 兼容门

后端、前端、MCP和关键SurrealQL测试通过；无未解释合同差异。

### U3 运行时门

三个Gateway在新venv上运行；health、capabilities、toolsets和实际调用一致。

### U4 审批门

真实approve写入成功，真实deny零写入，SSE不断线，trace结果可信。

### U5 上下文权威门

升级不得引入第二套canon、记忆或上下文权威；Hermes新增能力默认关闭，直到能力审计批准。

### U6 Provider门

实际provider/model有证据；非官方DeepSeek或fallback不得静默标记为策略符合。

### U7 安全门

零未解决高危供应链漏洞，secret扫描通过，本地技能和配置零丢失。

### U8 回归门

聚焦测试、后端全套、前端测试、构建、smoke和隔离业务E2E全部完成；未运行的测试明确标记未完成。

## 8. 回滚设计

### 8.1 Hermes回滚触发条件

以下任一发生即回滚：

- Gateway无法稳定启动；
- Responses/Runs关键合同无法在兼容层修复；
- approve/deny产生错误写入；
- 工具读写隔离失效；
- provider策略不可验证；
- 本地配置/技能恢复不完整；
- 出现无法接受的高危漏洞或依赖冲突；
- 核心测试或隔离创作E2E失败。

### 8.2 Hermes回滚动作

- 停止新Gateway；
- 保存失败版本日志、HEAD和差异；
- 使用升级前独立恢复锚恢复旧源码、venv和Hermes资产；
- 恢复到旧HEAD `bd740f203...` 只作为本次已知锚，不用破坏性Git命令覆盖现场；
- 恢复本地tracked diff和未跟踪skills；
- 重启旧Gateway；
- 重新运行旧版smoke和approve/deny；
- 保留失败新安装供后续分析，不立即删除。

### 8.3 SurrealDB回滚

本轮不替换SurrealDB，因此正常情况没有数据库版本回滚。若兼容验收发现生产3.2.0已有问题，不做直接降级；保持生产数据不动，在隔离实例上评估官方支持的恢复路径。任何降级或数据格式转换必须另行设计并获得明确授权。

## 9. 交付物

- 两组件目标版本冻结清单；
- SurrealDB 3.2.0生产兼容报告；
- 全库导出Manifest和恢复演练报告；
- Hermes升级前后版本、HEAD、依赖和能力差异；
- 本地dirty文件保护与恢复清单；
- canary结果；
- Scribe3兼容修复及测试；
- 三Gateway升级与运行时证明；
- 安全审计结果；
- 联合E2E与业务质量回归报告；
- 回滚锚和操作记录；
- 对系统架构文档中3.1.5旧口径的修订。

## 10. Git与运行环境边界

- Scribe3代码修改使用当前分支，保留用户未跟踪的SurrealDB缓存。
- `~/.hermes/hermes-agent` 是外部安装目录，其升级不纳入Scribe3 Git提交。
- 兼容代码、测试、规格和审计报告可以提交；外部安装备份、数据导出和secret不能提交。
- 实施完成前不push，除非用户再次明确要求。
- 升级成功后也不自动删除旧安装、备份或canary；待用户确认稳定后再单独回收。

## 11. 完成定义

只有满足以下条件才能称为“已升级到最新并验证完成”：

1. SurrealDB和Python SDK经二进制/包命令证明已是最新稳定版本；
2. 运行中的SurrealDB版本与磁盘二进制一致；
3. 全库备份和隔离恢复演练通过；
4. Hermes已升级到冻结的官方main SHA；
5. 本地dirty文件、skills、profiles和资产零丢失；
6. 三Gateway、MCP、Memory Provider、SSE和Approval真实工作；
7. Scribe3全部关键测试、构建、smoke和隔离业务E2E通过；
8. 安全审计和secret检查通过；
9. 实际provider/model/fallback可追溯；
10. 回滚锚已验证可用；
11. 未把最新Hermes的新能力未经审计直接打开；
12. 所有结论都有当前运行时证据，而非只来自版本号或文档。

升级闭环完成后，才进入 Hermes 全量能力审计的优化实施阶段。这样可以避免针对旧运行时设计优化，也避免把最新主干的新功能未经业务验证直接带入小说创作核心链路。

# A · 运行时急救(R1–R6)

> 枢纽定位:**让"已配置的能力真正在跑"**。本枢纽聚合 Hermes 运行时层的 6 个真问题(R1–R6),它们的共同特征是——配置/代码都对了,但 runtime 处于失败、未加载、未连通或已配未验证的状态,导致"账面上有的能力,事实上没在工作"。
>
> 取证来源:[05-HermesAgent使用深度诊断](../系统架构/05-HermesAgent使用深度诊断.md)(§0 环境基线、§1.3 Runtime 问题清单、§1.5 改进建议)+ 本次起草时对 `~/.hermes/`、`hermes` 二进制、scribe3 源码的二次实测(精确到配置键/`文件:行号`)。
>
> **安全说明**:扫描 `~/.hermes/config.yaml` 时**仅取字段名,未读取/未打印任何 secret 值**;R5 全程只说"移环境变量",不复述 key。
>
> 本文是**方案文档**(设计 + 可验证实施计划),**不真正改配置/代码**。所有命令均为"实施时执行",此刻未执行。

---

## 1. 概述

### 1.1 聚合的问题

| 编号 | 级别 | 一句话 | 类别 |
|---|---|---|---|
| **R1** | 🔴 高 | 体检 cron 持续失败,`Script not found`(profile 脚本目录解析错位) | 运维(失败) |
| **R2** | 🟡 中 | 自进化 skill `scribe-novel-v2` 未确认加载(skills 快照里 0 命中,且早于 SKILL.md 编辑) | 验证(已配未验证) |
| **R3** | 🟡 中 | agentic 端写工具实际写不进(非交互 elicitation fail-closed) | 设计决策(读写边界澄清) |
| **R4** | 🟡 中 | default 网关 :8642 报 `disconnected`(速答/渲染/judge/ingest 全依赖它) | 运维(连通性) |
| **R5** | ⚪ 低 | 明文 ark `api_key` 落盘 2 处 | 运维(凭证外置) |
| **R6** | ⚪ 低 | Hermes 落后上游 434 commits(v0.17.0) | 规划(升级评估) |

### 1.2 目标

**一句话:让"已配"真正在跑。** 具体落点 4 个可度量信号 + 1 个设计决策 + 1 个评估流程:
cron `last_status` 由 `error` 转 `success`;`scribe-novel-v2` 出现在 :8643 会话的 system prompt;:8642 `api_server.state` 由 `disconnected` 转 `connected`(或确认替代路径);两个 `config.yaml` 第 4 行不再有明文 key;R3 给出"agentic 读写边界"明确决策;R6 给出"不盲升"的升级评估流程。

---

## 2. 背景与动机

### 2.1 为何这 6 项同属"运行时健康"

诊断 [05 §1.2](../系统架构/05-HermesAgent使用深度诊断.md) 的判定是:**"Hermes 使用深度 = 核心精准、外围克制,但运行时健康度有缺口"**。scribe3 对 Hermes 的设计选型是对的(MCP + elicitation 写门控是 v0.17 最该用的能力,用对了),问题不在"配错了",而在**配了之后 runtime 没起来 / 没验证 / 没连上**:

- **R1 cron / R4 网关**——平台进程层面的失败与断连(一个脚本路径解析错、一个 api_server 掉线),让"自动护城河告警""速答/渲染/判官"这些已接的能力停摆。
- **R2 skill / R3 写工具**——"已配置但 runtime 未兑现":skill 注册了但快照里没有、写工具挂上了但非交互下 fail-closed 写不进。诊断把它们都标为 **"待验证(runtime)"**(05 §1.1 Skills 行、§1.3 R3)。
- **R5 凭证 / R6 版本**——卫生与规划:不是当下故障,但属于"运行时基线"的健康项,且 R5 一改即清、R6 需提前规划窗口,适合并入急救批次一并处理。

它们**同源于一层**(Hermes runtime),**互不阻塞**(改 cron 不依赖改网关),所以聚成"运行时急救"一个枢纽,而非散到各功能枢纽里。

### 2.2 为何最该立即做

[00-总纲 §4.2](./00-系统改进方案总纲.md) 把 **A 全部** 排在第一阶段(本周 1–3 天),理由:

1. **独立无前置**(总纲依赖图里 A 不依赖 D/B/C),可与关键路径 `D→B→C` 并行,不占用地基工期。
2. **修复成本极低、收益立刻可见**:R1 是"挪一个脚本"、R5 是"移一个环境变量"、R4 是"重连一个网关"——分钟级改动,却直接决定"系统账面能力是否真的在跑"。
3. **是验证其他枢纽的前提**:R2(skill 加载)不修,[05 §1.4](../系统架构/05-HermesAgent使用深度诊断.md) 规划的 5 个工序 skill 全建在沙上;R4(:8642)不确认,后续任何依赖速答/渲染/judge/ingest 的验收都不可信。
4. **R3 是认知错位的纠偏**:当前"配了写工具却写不进"会误导后续 F(安全)/C(账本)对"主编能否写世界"的假设——必须先把边界钉死(见 §6 风险)。

---

## 3. 详细设计

> 每个 R 给"问题精确定位 → 修法 → 验证命令 + 预期输出"。R3 是设计决策,给选项 + 推荐,不写代码。

### R1🔴 体检 cron 路径错位 → 把脚本放到 profile 解析的目录

**精确定位**(本次实测):

- cron 作业 `dc4bd8e87938`(名「scribe3-体检」)归属 **scribe3 profile**(`hermes cron list` 默认 profile 为 `No scheduled jobs`,`hermes -p scribe3 cron list` 才列出它)。
- 作业定义 `~/.hermes/profiles/scribe3/cron/jobs.json`:`"script": "scribe3_qc.sh"`(裸文件名)、`"no_agent": true`、`"last_status": "error"`、`"last_error": "Script not found: /Users/miaoma/.hermes/profiles/scribe3/scripts/scribe3_qc.sh"`。
- **脚本实际在全局目录** `~/.hermes/scripts/scribe3_qc.sh`(存在,可执行,内容 = `cd 仓库根 + scribe3/.venv/bin/python -m scribe3.qc_scan`)。
- **profile 的脚本目录** `~/.hermes/profiles/scribe3/scripts/` **为空**(本次 `ls` 实测 0 文件)。

**根因**:`hermes cron --help` 文档称 `--script` 是 "Path to a script under `~/.hermes/scripts/`"(全局默认);但 **scribe3 profile 下注册的 no-agent 作业,其裸 `script` 名是相对 profile 的 `profiles/scribe3/scripts/` 解析**的——脚本却躺在全局 `~/.hermes/scripts/`,于是 `Script not found`。这是"全局脚本目录 vs profile 脚本目录"的错位,不是脚本本身写错。

**修法(推荐:把脚本放到 profile 解析处)**——脚本极小(282 字节)、复制无副作用,且能让 profile 解析直接命中:

```sh
# 实施时执行(把全局脚本复制进 profile 脚本目录,保持可执行位)
cp -p ~/.hermes/scripts/scribe3_qc.sh ~/.hermes/profiles/scribe3/scripts/scribe3_qc.sh
chmod +x ~/.hermes/profiles/scribe3/scripts/scribe3_qc.sh
```

**备选 B**(用 CLI 重设而非手挪文件,语义更"官方"):`hermes -p scribe3 cron edit dc4bd8e87938 --script scribe3_qc.sh`(重写 script 字段触发路径重解析)。**备选 C**(诊断 §1.5#1 提到的绝对路径思路):若 Hermes 接受 `script` 为绝对路径,可 `--script /Users/miaoma/.hermes/scripts/scribe3_qc.sh`——但 `--help` 明确写"under `~/.hermes/scripts/`",绝对路径是否被接受 **需人工确认**;**故首选 A**(复制到 profile 目录,确定命中)。

**验证命令 + 预期输出**:

```sh
# 1) 先手动跑一次脚本,确认体检逻辑本身能跑通(干净则空输出 = [SILENT] 语义)
~/.hermes/profiles/scribe3/scripts/scribe3_qc.sh; echo "exit=$?"
#   预期:exit=0;stdout 为空(库干净)或一段健康报告 markdown(有伏笔超期/因果缺口时)

# 2) 让 Hermes 在下一个 tick 立刻跑该作业(不必等 12:34)
hermes -p scribe3 cron run dc4bd8e87938
hermes -p scribe3 cron tick           # 触发一次到期作业执行后退出
#   预期:作业被执行,无 "Script not found"

# 3) 复查作业状态
hermes -p scribe3 cron list
#   预期:Last run 行不再有 "error: Script not found",last_status 转 success
```

### R2🟡 自进化 skill 未确认加载 → 验证 system prompt 含 scribe-novel-v2

**精确定位**(本次实测):

- skill 已注册:`~/.hermes/profiles/scribe3/config.yaml:397-398` `skills.external_dirs: ["/Users/miaoma/Downloads/写作 3.0/scribe3/hermes_skills"]`。
- skill 文件存在:`scribe3/hermes_skills/scribe-novel-v2/SKILL.md`(52 行,frontmatter `name: scribe-novel-v2` / `mcp_server: scribe3`),**mtime = 2026-06-23 22:16**。
- **快照里 0 命中**:`~/.hermes/profiles/scribe3/.skills_prompt_snapshot.json`(54 KB)grep `scribe-novel-v2` = **0 次**、grep `scribe-novel`(模糊)= **0 次**;快照 **mtime = 2026-06-22 19:10**,比 SKILL.md 早 **约 27 小时**。

**根因判断**:不是配置错(`external_dirs` 指对了),而是 **skills 快照陈旧**——快照早于 skill 文件创建/最后编辑,网关进程很可能在 skill 落盘前就生成了 prompt 快照并缓存,之后未重载。属"已配未验证 + 需触发重载"。

**修法**:重载 skills / 重启 scribe3 网关让快照重建,再起一个 :8643 会话核验 system prompt 真的含该 skill。

**验证命令 + 预期输出**:

```sh
# 1) 重启 scribe3 profile 网关(--replace 顶掉旧进程,重建 skills 快照)
hermes -p scribe3 gateway run --replace
#   预期:网关重启;.skills_prompt_snapshot.json mtime 更新到当前时间

# 2) 复查快照是否纳入该 skill
grep -c "scribe-novel-v2" ~/.hermes/profiles/scribe3/.skills_prompt_snapshot.json
#   预期:>= 1(由 0 转为命中)

# 3) 起一个 :8643 会话,确认 system prompt 注入了 skill 内容(最终判据)
#    经 /v1/responses 发一句无害问句,要求复述其可用 skill,核查回包/服务端 prompt 含 scribe-novel-v2
#    (需带 API_SERVER_KEY 鉴权;:8643 裸请求返回 401 = 网关在,见 AGENTIC_SETUP.md 步骤5)
hermes -p scribe3 mcp test scribe3
#   预期:✓ 19 工具(确认 MCP 侧在;skill 注入以 system prompt 含 scribe-novel-v2 为最终判据)
```

> 验收最终判据是 [05 §1.5#2](../系统架构/05-HermesAgent使用深度诊断.md) 的原话:**"起一个 :8643 会话,检查 system prompt 是否含 `scribe-novel-v2` 内容"**。快照 grep 命中是中间信号,system prompt 含该 skill 才是闭环。

### R3🟡 agentic 写工具写不进 → 读写边界设计决策(见 §3.R3 决策)

**精确定位**(本次实测):

- 写门控机制:`scribe3/mcp.py:52-58` `_ask()` → `ctx.elicit(...)`,`except Exception: return False`——**非交互上下文 elicitation 抛错即 fail-closed(不写)**。
- 自承文档:`scribe3/AGENTIC_SETUP.md`「已知边界」段原文:"写工具走 elicitation 待批:agentic 流里主编调写工具会触发审批;**非交互上下文 fail-closed(不写)**,只读工具不受影响";`scribe3/app.py:374` 主编 system prompt 原文:"**写操作(加角色/事实/伏笔等)会进入待批,不会立即生效**"。

**这是设计决策,不是 bug**:fail-closed 是正确的安全默认(没有交互批准通道时,宁可不写)。问题是**认知错位**——主编 system prompt(`app.py:370-373`)告诉主编"你能调 s3_ 工具操作 SurrealDB",但写其实落不了库,造成"配了写工具却写不进"的错配。**本 R 的产出是把边界钉死的决策,详见 §3 末「R3 决策」**(此处不写代码)。

### R4🟡 default :8642 disconnected → 健康检查 + 重连

**精确定位**(本次实测):

- 依赖关系:`scribe3/llm.py:12` `HERMES = os.environ.get("HERMES_API", "http://127.0.0.1:8642/v1")`——速答/渲染/纪律判官/ingest 默认全走 :8642。
- 失败证据:`~/.hermes/gateway_state.json` `gateway_state: running` 但 `platforms.api_server.state: "disconnected"`,`updated_at: 2026-06-24T03:53:08Z`(比诊断 §0 记录的 03:13 更新,**仍 disconnected**)。
- 对照:scribe3 profile :8643 `api_server.state: "connected"`(`profiles/scribe3/gateway_state.json`,pid 50534)——故 agentic 路径不受影响,受影响的是 :8642 那条线。

**根因判断**:`gateway_state: running` 但 `api_server` 子状态 `disconnected`——进程在、对外 API 服务面没连上(可能上游 ark 连接掉、可能 api_server 未起监听)。**:8642 是否仍可服务需人工确认**(诊断 §0 ⚠ 与 R4 均如此标注)。

**修法**:先探活,再按结果重连。

**验证命令 + 预期输出**:

```sh
# 1) 探活:是否在监听(401 = 在,需鉴权;拒连/超时 = 真掉)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8642/v1/models
#   预期(健康):401;若 000/拒连 → 确认已掉,进 2)

# 2) 看网关状态机
hermes gateway status   # 或读 ~/.hermes/gateway_state.json 的 api_server.state
#   预期:state 应为 connected;若仍 disconnected,进 3)

# 3) 重连/重启 default 网关
hermes gateway run --replace
#   预期:重启后 api_server.state 转 connected,步骤1 的 curl 返回 401

# 4) 端到端探一句速答(经 :8642 取一段补全,确认真能服务)
#    用 scribe3 后端的 /chat lite 路径或直接打 :8642 /v1/chat/completions(带 API_SERVER_KEY)
#   预期:返回非空补全;失败如实记录(可能上游 ark 凭证/网络问题,另查)
```

> ⚠ **诚实标注**:":8642 是否真可服务"在本方案起草时无法断言(只读状态文件显示 disconnected)。实施时须以步骤 1+4 的真实返回为准,失败不掩盖。

### R5⚪ 明文 api_key 落盘 → 凭证外置(移环境变量)

**精确定位**(本次实测,**未打印任何值**):

- 两处 `config.yaml` 的 **第 4 行** 均为 `model.api_key: <存在明文值>`:`~/.hermes/config.yaml:4` 与 `~/.hermes/profiles/scribe3/config.yaml:4`。
- `base_url`(第 3 行)= `https://ark.cn-beijing.volces.com/api/coding/v3`(火山 ark),`default`(第 5 行)= `doubao-seed-2.0-pro`——确认是 ark 凭证。
- `security.redact_secrets:true` 只管**日志脱敏**,不管**配置文件落盘**(诊断 R5 原文)。

**修法(移环境变量)**:把 key 从两个 `config.yaml` 第 4 行移走,改由环境变量/`.env` 提供。**本方案只说"移环境变量",不复述 key**。

具体路线(实施时按 Hermes 实际支持的注入方式择一,**需人工确认 Hermes 对 `model.api_key` 的 env 解析约定**):

1. **删 config 明文 + 走 `.env`**:从两个 `config.yaml:4` 删除 `api_key` 行,把值写入 Hermes 读取的 `.env`(`~/.hermes/.env` / `profiles/scribe3/.env`,权限 `600`,本就不入 git)。
2. **env 占位引用**(若 Hermes 支持 `${VAR}` 插值):`config.yaml:4` 改为 `api_key: ${ARK_API_KEY}`,值仅存进程环境/`.env`。
3. 任一路线完成后,确认 `config.yaml` 文本里**不再含明文 key**。

**验证命令 + 预期输出**(检"存在性",不打印值):

```sh
# 1) 确认两个 config.yaml 不再含明文 key(只报命中与否,不回显值)
for f in ~/.hermes/config.yaml ~/.hermes/profiles/scribe3/config.yaml; do
  if grep -qE '^\s*api_key:\s*\S' "$f" && ! grep -qE 'api_key:\s*\$\{' "$f"; then
    echo "$f: 仍有明文 api_key —— 未达标"
  else
    echo "$f: 无明文 api_key —— 达标"
  fi
done
#   预期:两行均 "无明文 api_key —— 达标"

# 2) 凭证仍可用(改完后 LLM 仍能取补全;复用 R4 步骤4 的速答探活)
#   预期:速答/agentic 仍正常;若 401/凭证错 → env 注入未生效,回滚或修正注入方式
```

> 🔒 红线:上述脚本只输出"达标/未达标",**绝不 `cat`/`echo` key 值**。

### R6⚪ Hermes 落后上游 434 commits → 升级评估流程(不盲升)

**精确定位**(本次 `hermes --version` 二进制实测):

```
Hermes Agent v0.17.0 (2026.6.19) · upstream 935f2bc4
Update available: 434 commits behind — run 'hermes update'
```

> 注:诊断 §0 记录 upstream 哈希为 `bb7ff7dc`,本次二进制实测为 `935f2bc4`(上游 HEAD 已前移);"落后 434 commits" 与 "v0.17.0" 一致。**以二进制实测为准**(用户全局规则:查版本跑二进制,不读源码快照)。记忆已记**"不盲升"**(`scribe-hermes-surrealdb-facts`:0.17.0 落后 267→现 434,需评估破坏性)。

**修法不是"立即升级",而是给一套评估流程**(本 R 产出流程,不在急救批次内执行升级):

1. **拉变更面**:`hermes update --dry-run`(若支持)或查上游 changelog/release notes,聚焦 **破坏性变更**(config schema 改名、MCP/elicitation 行为变更、cron/skill 解析变更——这些正是 R1/R2/R3 命门所在)。
2. **影响评估清单**:逐项对照 scribe3 的依赖面——`config.yaml` 键名(compression/skills.external_dirs/approvals.mode/api_server.port)、`ctx.elicit` 签名、`/v1/responses` tools 协议、cron `--script` 解析语义。任一项有破坏性变更即标记为"升级需配套改 scribe3"。
3. **隔离演练**:在非生产 profile / 副本上 `hermes update` 后跑回归(R1–R4 的全部验证命令 + scribe3 端到端写一章),通过才升生产。
4. **窗口**:总纲 [§4.2](./00-系统改进方案总纲.md) 把 R6 归"中期";不进第一阶段急救执行,只在本枢纽产出"评估流程"这一交付物。

**验证命令 + 预期输出**(仅评估,不执行升级):

```sh
hermes --version
#   预期:确认当前 v0.17.0 / commits behind 数,作为评估基线(本次=434)
hermes update --dry-run   # 若不支持该 flag 则改查上游 release notes
#   预期:列出将变更内容,人工据破坏性清单决策是否进升级窗口
```

---

### R3 决策:agentic 主编的"读写边界"(本枢纽核心设计产出)

诊断 [05 §1.5#4](../系统架构/05-HermesAgent使用深度诊断.md) 要求"明确 agentic 主编是否应该能写世界"。给两个选项 + 推荐:

| 选项 | 做法 | 优点 | 代价/风险 |
|---|---|---|---|
| **甲:agentic 只读,写一律走 REST 直编** | 文档与 prompt 明确"agentic 主编只读;写世界走前端 REST 待批端点(B3 已落地的待批写)";`app.py:370-374` 主编 prompt 改为"你只读核实,不写;需改世界请走待批写流程" | 与现状一致(零代码改动即生效);单一落库点 `_execute_write` + REST 待批不被绕过;限知/幻觉校验都在 REST 侧已有 | agentic 主编不能"自调写工具进化世界",自进化回路弱一档 |
| **乙:给 agentic 提供交互式批准通道** | 为 :8643 流接一个 elicitation 批准 UI/回调,让主编调写工具时弹批准、人确认后真落库(`mcp.py` 写门控不变,补"交互应答源") | 真正实现"主编自调写工具 + 人批准进化世界";发挥 v0.17 elicitation 设计意图 | 需新增交互批准通道(前端 + 流式 elicitation 桥接),工程量大;与现有 REST 待批写(B3)可能双轨,需防"两个写入口" |

**推荐:甲(短期)**——理由:① 零代码即可消除认知错位,把 `app.py:374` 的措辞从模糊的"会进入待批,不会立即生效"改为明确的"agentic 只读、写走 REST 待批",当下就对齐"配了写工具却写不进"的事实;② B3 已落地 REST 待批写(单一落库点 `_execute_write`),写路径已闭环,不必为 agentic 再开第二写入口;③ 乙作为**中期可选增强**保留(待 F 安全枢纽确立统一写门控后再评估,避免双轨写入口与 F 冲突)。

> **此决策必须先于 F/C 落地**:F(安全)/C(账本)对"主编能否写世界"的假设,要以此决策为准——选甲则 F/C 只需守 REST 写门控一条线,选乙则要把 agentic elicitation 写也纳入门控统一(见 §6)。

---

## 4. 实施计划(可验证、bite-sized)

> 运维类(R1/R4/R5/R2/R6 验证)以"改动 → 验证命令 → 预期输出"表达,每任务可独立验收。R3 是设计决策,产出决策记录,不写代码。任务顺序按"故障优先 → 验证 → 卫生 → 决策/规划"。

### 任务 A1 — 修 R1 cron 路径(🔴 最先)

- **改动**:`cp -p ~/.hermes/scripts/scribe3_qc.sh ~/.hermes/profiles/scribe3/scripts/scribe3_qc.sh` + `chmod +x`(首选 A;若选备选 B 则 `hermes -p scribe3 cron edit dc4bd8e87938 --script scribe3_qc.sh`)。
- **验证**:`~/.hermes/profiles/scribe3/scripts/scribe3_qc.sh; echo exit=$?` → `exit=0`;`hermes -p scribe3 cron run dc4bd8e87938 && hermes -p scribe3 cron tick`;`hermes -p scribe3 cron list`。
- **预期/验收**:cron list 中该作业 **不再有 `error: Script not found`**,`last_status` 转 `success`。

### 任务 A2 — 查 R4 :8642 健康并重连

- **改动**:按 §3.R4 探活结果决定是否 `hermes gateway run --replace`。
- **验证**:`curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8642/v1/models`;`hermes gateway status`;一句速答端到端。
- **预期/验收**:curl 返回 `401`(在,需鉴权)且 `api_server.state` 转 `connected`;速答返回非空。**若实测仍掉,如实记录失败原因(需人工确认上游/网络),不伪绿。**

### 任务 A3 — 验 R2 skill 加载

- **改动**:`hermes -p scribe3 gateway run --replace`(重建 skills 快照)。
- **验证**:`grep -c "scribe-novel-v2" ~/.hermes/profiles/scribe3/.skills_prompt_snapshot.json` → `>=1`;起 :8643 会话核查 system prompt 含 `scribe-novel-v2`;`hermes -p scribe3 mcp test scribe3` → ✓19 工具。
- **预期/验收**:快照 grep 由 **0 转命中**,且 **:8643 会话 system prompt 含 scribe-novel-v2**(最终判据)。

### 任务 A4 — R5 凭证外置

- **改动**:从 `~/.hermes/config.yaml:4` 与 `~/.hermes/profiles/scribe3/config.yaml:4` 移除明文 `api_key`,改 `.env`/env 占位(**不打印值**)。
- **验证**:§3.R5 的"无明文 api_key"检测脚本;复用 A2 速答探活确认凭证仍可用。
- **预期/验收**:两个 config.yaml 均 **"无明文 api_key —— 达标"**;LLM 仍正常。

### 任务 A5 — R3 读写边界决策(设计,不写代码)

- **产出**:在本枢纽/HANDOFF 记录决策 = **甲(agentic 只读、写走 REST 待批)**;把 `app.py:374` 措辞拟改为明确版(此处只定决策与措辞,实际改文案归 G/F 执行批次)。
- **验证**:决策被记录且 F/C 引用一致(对账 §6)。
- **预期/验收**:存在一条明确的"agentic 读写边界"决策,下游枢纽以它为假设基线。

### 任务 A6 — R6 升级评估流程(规划,不执行升级)

- **产出**:§3.R6 的 4 步评估流程 + 破坏性影响清单(config 键/elicit 签名/responses 协议/cron 解析)。
- **验证**:`hermes --version` 锁基线(本次 434 behind);`hermes update --dry-run`(或 release notes)产出变更面。
- **预期/验收**:存在"不盲升"的评估流程文档;**第一阶段不执行 `hermes update`**。

---

## 5. 验收标准(可度量)

| 编号 | 验收信号 | 度量方式 | 达标判据 |
|---|---|---|---|
| **R1** | cron 不再 `Script not found` | `hermes -p scribe3 cron list` | `last_status` = `success`,无 `Script not found` |
| **R2** | skill 进入 prompt | grep 快照 + :8643 会话 system prompt | 快照 grep `scribe-novel-v2` ≥1 **且** system prompt 含该 skill |
| **R3** | 读写边界明确 | 决策记录 | 存在"甲/乙"明确决策(推荐甲),F/C 引用一致 |
| **R4** | :8642 可服务 | `curl .../v1/models` + 速答 | HTTP `401`(在)、`api_server.state` = `connected`、速答返非空;**若不可服务则如实标注** |
| **R5** | 无明文 key | 检测脚本(不回显值) | 两个 config.yaml 均"无明文 api_key",凭证仍可用 |
| **R6** | 升级评估就绪 | 评估流程 + `--version` 基线 | 有"不盲升"流程;第一阶段不执行升级 |

> 总纲 [§4.2](./00-系统改进方案总纲.md) 第一阶段验收线"cron 转绿"由 R1 兑现;R2/R4 的"connected/含 skill"是后续枢纽可信验收的前提。

---

## 6. 风险与依赖

### 6.1 依赖

- **本枢纽独立、无前置**(总纲依赖图:A 不依赖 D/B/C/E/F/G/H),可与关键路径 `D→B→C` 并行。

### 6.2 风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| **R4 :8642 可能确实不可服务** | 起草时只读状态显示 `disconnected`,无法断言重启即恢复(可能上游 ark 连接/凭证/网络问题) | 任务 A2 以真实 curl + 速答返回为准;失败如实记录,不伪绿;必要时另开排查 |
| **R3 决策外溢到 F/C** | F(安全)/C(账本)都对"主编能否写世界"有假设——选甲(只读)则二者只需守 **REST 写门控一条线**;选乙(交互批准)则要把 agentic elicitation 写**纳入 F 的门控统一**,否则出现"两个写入口"绕过单一落库点 `_execute_write` | A5 先定甲;若未来转乙,须与 F 同批改门控,并在 C 的幻觉/幂等校验里覆盖 agentic 写路径 |
| **R5 env 注入方式未证** | Hermes 对 `model.api_key` 的 env/占位解析约定未在本方案核实 | A4 标"需人工确认注入方式";改完用速答探活回归,失败可回滚(`.env` 不入 git,安全) |
| **R1 备选 C(绝对路径)未证** | `--help` 写"under `~/.hermes/scripts/`",绝对路径是否被接受未知 | 首选 A(复制到 profile 目录,确定命中),不赌绝对路径 |
| **R2 重启网关副作用** | `gateway run --replace` 会顶掉在用 :8643 会话 | 选低峰执行;重启后 `mcp test` + 端到端确认 19 工具与 skill 都在 |

---

## 7. 闭环问题清单(对账)

| 编号 | 覆盖 | 落点 |
|---|---|---|
| **R1** | ✓ | §3.R1 复制脚本到 profile 目录 + 验证命令;§4 A1;§5 R1 行 |
| **R2** | ✓ | §3.R2 重建快照 + system prompt 核验;§4 A3;§5 R2 行 |
| **R3** | ✓ | §3「R3 决策」甲/乙 + 推荐甲;§4 A5;§5 R3 行;§6.2 外溢风险 |
| **R4** | ✓ | §3.R4 探活 + 重连 + 端到端;§4 A2;§5 R4 行(标注"需人工确认") |
| **R5** | ✓ | §3.R5 移环境变量(不打印值)+ 存在性检测;§4 A4;§5 R5 行 |
| **R6** | ✓ | §3.R6 不盲升评估流程;§4 A6;§5 R6 行 |

**对账:R1✓ R2✓ R3✓ R4✓ R5✓ R6✓ —— 6/6 全覆盖、闭环。**

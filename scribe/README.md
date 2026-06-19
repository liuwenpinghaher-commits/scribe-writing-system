# Scribe(代号)· 实现仓库

人机协同 · 百万字长篇 · 写小说系统。设计见 [`../设计文档/`](../设计文档/README.md)。

> **当前进度:Batch 0 核心已真实联调通过。** 详见 [开发方案-工单backlog](../设计文档/开发方案-工单backlog.md) 与 [工程0-spike](../设计文档/工程0-前置技术验证spike.md)。

## 已完成并验证

- **领域数据层** `scribe_mcp/db.py` + `schema.sql`(SQLite,对齐 00 §4 子集)。
  - ✅ 自检 `python3 tests/test_db.py`(5 项:CRUD、章节 upsert、想象捕获、**多本书隔离防串味**、**human-lock 手稿保护**)。
- **Hermes Agent v0.16.0** 从 GitHub 源码装入 `vendor/hermes-agent`(uv,Python 3.13)。
  - ✅ **S1 通过**:经火山 Ark(`doubao-seed-2.0-pro`,custom provider)真实应答。
    - 关键坑:custom provider 的 key 必须写 `config.yaml: model.api_key`(进程环境里的旧 `OPENAI_API_KEY` 会串台导致 401)。
- **领域 MCP Server** `scribe_mcp/server.py`:已注册进 Hermes(`mcp_servers.scribe`)。
  - ✅ **S2 + S5 核心通过**:doubao 经 Hermes 真实调用 `create_work`/`capture_imagination`/`list_works`,数据真落 `scribe.db`(已查证)。
  - DB 路径已固定为 `scribe/scribe.db`(绝对路径,不依赖 Hermes 子进程 cwd)。

## Batch 0 决策门 → **GO** ✅

| 项 | 结果 |
|---|---|
| S1 Hermes 起服 + 火山应答 | ✅ Pass(doubao-seed-2.0-pro,custom provider) |
| S2 领域 MCP(SQLite)可被调用 | ✅ Pass(doubao 经 Hermes 调用工具,数据落库已查证) |
| S3 sqlite-vec 语义检索 | ✅ Pass(`tests/test_vec.py` KNN+跨书隔离;fastembed 本地真语义召回:无共同关键词也命中 Top1) |
| S4 Open WebUI 对接口 | ✅ Pass(`:8642/v1` /health + /chat/completions 实测应答;UI 用官方 `setup_open_webui.sh` 指向它) |
| S5 协作回路(建书/想象/写稿/**意见→定向重写/版本父子链**) | ✅ Pass(DB 查证 v1→v2 parent 链,意见"更紧张更短"被真正执行) |
| S6 多本书 Profile 隔离 | ⏳ 待做(数据层隔离已单测通过;Hermes Profile 映射后续) |

> **结论:架构 GO** —— "Hermes 底座 + 火山doubao + 领域MCP/SQLite + sqlite-vec语义检索 + 协作回路 + OpenAI兼容API供现成UI" 全链路已端到端验证。
> 备注:① 火山 coding-plan key 不提供 embeddings(404)→ 用本地 **fastembed(bge-small,384维,ONNX/CPU)+ sqlite-vec**;中文生产换 bge-zh/m3;规模化再迁 pgvector(实现4 接口不变)。② key 必须配 `config.yaml: model.api_key`(避免进程环境旧 `OPENAI_API_KEY` 串台 401)。③ 需 `API_SERVER_ENABLED=true`(已设)启用 :8642 端点。
> 运行态:Hermes gateway 由 launchd 托管常驻(含 :8642 API server + cron)。

## Batch 1(进行中,已验证)

- ✅ **全量 schema**(00 §4):新增 characters/char_states/entity_relations/timeline_events/foreshadows/consistency_flags/memory_entries/option_sets/discussion_threads/proactive_insights/materials/material_refs/style_exemplars/preference_signals/taste_models/agent_memory/agent_skills。
- ✅ **伏笔 F-T-P 状态机** `foreshadow.py`(planted→triggered→paid / abandoned;非法转移拦截;未回收预警;回收率)+ MCP 工具。
- ✅ **跨书品味模型** `taste.py`(owner 级跨书共享 / book 级隔离防串味 / 合并)+ MCP 工具 —— 落地多本书 §2.7。
- ✅ **设定圣经(角色)+ 一致性标记** db 方法 + MCP 工具(含作者裁决回流)。
- ✅ **向量检索** `vec.py`(sqlite-vec + 本地 fastembed)。
- ✅ **15 项单测全绿**(db/vec/foreshadow/taste/bible);server 含 **31 个 MCP 工具**,导入正常。
- ✅ **协作技能** `skills/write-chapter/SKILL.md` 已装入 Hermes(enabled)。
- 复用线索:Hermes 自带 `novel-genesis/outline/simulate/critic-*` 等 writing 技能(autonovel),Batch 2 规划/写作可借鉴。

### 测试
```bash
for t in tests/test_*.py; do .venv/bin/python "$t"; done   # 全部应通过
```

## Batch 2(进行中,已验证)

- ✅ **反平庸规则库** `antislop.py`(内核3):10 条中文 AI 腔规则(顿悟升华/情感直说/不是…而是/套话比喻…)+ 密度指标 + MCP 工具 `check_ai_slop`。`test_antislop.py` 验证 slop 命中、干净文本零误报。
- ✅ **检索接入** `vec.py` 增 `+content` 列;MCP 工具 `index_segment` / `search_book`(语义召回本书片段,防串味)。
- ✅ **17 项单测全绿**(新增 antislop)。
- 复用:Hermes 自带 `novel-genesis/outline/simulate/critic-*`(autonovel)可作规划/写作技能基。

## Batch 3(进行中,已验证)

- ✅ **领域 REST API** `scribe_mcp/api.py`(FastAPI):作品库/北极星/章节/设定/角色/伏笔/一致性 + **越权防护(他人作品 403、无 owner 401)** + `/chat` 代理(转发 :8642,避开浏览器 CORS)。`test_api.py` 4 项验证(含越权 403)。
- ✅ **前端骨架** `web/index.html`(单文件、无需构建):作品库 / 北极星编辑 / 章节 / 设定·伏笔·一致性侧栏 / 主编对话。
- ✅ **全栈端到端实测**:前端 API → :8801 → Hermes :8642 → 火山 doubao,`/chat` 真实应答;`/works` 返回作品库;越权 401/403 生效。
- ⚠️ 前端浏览器 UX 未逐项点测(无头环境);代码调用的每个端点均已 live 验证。这是编辑器的**可用骨架**,工程2b 的 11 面板精修(diff/OptionSet卡/想象浮层/主编札记…)为后续。

## 前端(已按设计重建为 React + TS + Vite + Tiptap)

- **`web-app/`** = 正式前端,**对齐工程1/2b 技术栈**:React + TypeScript + Vite + **Tiptap 富文本编辑器** + lucide SVG 图标。
  - 真·可编辑正文(Tiptap)+ 存为人工定稿(锁定,喂 LoRA)· 版本 diff 三模式 · 作品库/北极星(脏态)/想象捕获/章节 · 主编札记+全文体检 · 设定·伏笔·一致性侧栏(计数)· OptionSet 选项卡 · 主编对话。
  - **修复了 UI 审查的关键问题**:键盘可用(全 `<button>`)、防重复提交(加载态按钮)、错误不再静默(加载/错误/空 + 重试)、表单 `<label>`、`:focus-visible`、响应式三栏(窄屏抽屉)、aria-live、16px 正文、独立 toast、SVG 图标替代 emoji。
  - 跑:`cd web-app && npm install && npm run dev`(默认 :5173,占用则自动让端口,看终端输出)。构建:`npm run build`(tsc+vite 通过)。
  - 待续:超长章节列表虚拟化、URL 深链、diff 词级分组。
- **`web/index.html`** = 早期 vanilla 验证原型,**已废弃**(保留作参考),不再维护。

## 如何运行整套(本地)

```bash
# 0) Hermes gateway(含 :8642 OpenAI 兼容 API)已由 launchd 常驻;如需重启:
cd scribe/vendor/hermes-agent && uv run hermes gateway restart

# 1) 领域 API(给前端面板用)
cd scribe && .venv/bin/uvicorn scribe_mcp.api:app --port 8801

# 2) 打开前端
open scribe/web/index.html   # 面板连 :8801,聊天经 /chat 转发 :8642→火山doubao

# 3) 全部单测(21 项应全绿)
cd scribe && for t in tests/test_*.py; do .venv/bin/python "$t"; done
```

## Batch 4(进行中,已验证)

- ✅ **章节详情 + 版本 diff**:前端点章节 → 显示版本树,**对最后两版做字符级 LCS diff**(删红/增绿)。新端点 `GET /works/{id}/chapters`、`GET .../chapters/{seq}`(附 snapshots)、`POST .../feedback`,均含越权防护,`test_api.py` 验证。
- ✅ **写一章 / 提意见重写** 按钮:经 `/chat`→主编(write-chapter 技能)写正文/定向重写,回填版本 diff。
- ✅ 前端 JS `node --check` 通过;所有调用端点 live 验证;**22 项单测全绿**。
- ⚠️ 浏览器 UX 未逐项点测(无头环境)。

- ✅ **OptionSet 多方案选项卡(选项式核心)**:`propose_options` 工具 + REST `GET /option-sets`、`POST .../choose`;前端右栏渲染"待你定夺的方案"卡(approach/代价 + 选)。**选择即回流品味信号**(option_choice → 跨书底色,内核2)。`test_optionset.py` 验证创建/选择/校验/防重复;REST live 验证列出→选→待决归零→信号入库。
- **24 个用例 / 8 测试文件全绿;前端 JS node --check 通过。**

- ✅ **想象捕获**:`//` 快捷聚焦 + 输入框 → `POST /imaginations`;前端显示最近想象。
- ✅ **主编札记 + 全文体检**:`review.py` 规则版主动引擎(超期伏笔→札记,去重防刷屏)+ REST `proactive-review`/`insights/{id}/ack|dismiss` + MCP `add_insight`/`run_full_review`;前端右栏札记面板(知道了/忽略)。`test_review.py` + live 验证(产出"伏笔已 118 章未回收"札记)。
- **9 测试文件 / ~28 用例全绿;前端 JS node --check 通过。**

## Batch 5(已验证)

- ✅ **门槛后台自动校验** `consistency.py`(规则版,零 LLM):①符号状态矛盾(已遗失/损毁物品再现,SCORE 思路)②叙事风格(high 级 AI 腔)→ `consistency_flag`。写完一章自动跑(前端 writeChapter/feedbackRewrite 后调 `/check`)。`test_consistency.py` + live(断魂剑 destroyed 再现 → flag)。
- ✅ **主动引擎周期自动触发**:API 后台异步循环(`SCRIBE_REVIEW_INTERVAL`,零 LLM)定期 `review_all_works` → 主编札记。`test_review.py` + **live 验证**(后台自动产出"伏笔已 97 章未回收")。比每跑烧 token 的 LLM cron 更省。
- **10 测试文件 / 29 用例全绿。**

## 已建成总览(Batch 0–5,均验证)

后端:Hermes×火山doubao · 领域 MCP/SQLite(全量 schema)· sqlite-vec 语义检索 · 伏笔 F-T-P · 反平庸 · 跨书品味 · 一致性引擎(自动)· 主动引擎(自动)· 设定圣经。
接口:领域 REST API(越权防护)+ /chat 代理 + 后台主动循环。
前端:作品库 / 北极星 / 想象捕获(//)/ 章节 + 版本diff / 写·意见重写 / OptionSet 选项卡 / 设定·伏笔·一致性侧栏 / 主编札记+体检 / 主编对话。
技能:plan-novel · write-chapter(均 enabled)。
**29 单测 + 多处 live 端到端验证;前端 JS 语法通过。**

## 仍待 / 受限(诚实)

- **个性化 LoRA**:已实现 Prompt→**RAG/品味模型**这一档(TasteModel + 偏好信号,推荐的第一档);**LoRA 微调需 GPU + Hermes 开源模型权重,火山 API key 无法做**,属环境受限,未做。
- **多本书 Profile**:数据/接口层隔离已做且验证(work_id 过滤 + 403/401);Hermes per-book Profile 物理隔离为可选增强,未做。
- **工程2b 全面板视觉精修**:diff 双栏对照、聚焦模式、虚拟滚动、想象浮层动画等视觉打磨——功能在,视觉为持续迭代项。
- 这是**能真实运行、核心闭环全通的系统**;离"商业级成品"仍有打磨与上述受限项。

## Batch 6 视觉精修(工程2b,首增量,已验证)

- ✅ 作品库卡片**跨书角标**(📝主编札记数 / ◆待决方案数)。
- ✅ 侧栏 tab **计数角标**(伏笔 / 一致性)。
- ✅ 版本对照**三模式切换**:行内 diff / 双栏对照 / 只看终稿(聚焦阅读)。
- ✅ 写完/重写后**自动切到一致性侧栏 + 刷角标 + 刷札记**(门槛安静呈现)。
- 验证:前端 JS `node --check` 通过;角标 4 端点 live 200;10 测试文件全绿。
- 持续项:diff 词级高亮、虚拟滚动、聚焦写作全屏、动效等(开放迭代)。

## 运行

```bash
# 数据层自检(纯 stdlib,无需安装依赖)
python3 tests/test_db.py

# 安装依赖后跑 MCP Server(需 Hermes 消费)
uv sync                       # 或 pip install -e ".[dev]"
python -m scribe_mcp.server   # stdio MCP server
```

接入 Hermes(`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  scribe:
    command: "python"
    args: ["-m", "scribe_mcp.server"]
```

## 待办(后续 Batch)

按 [开发方案-工单backlog](../设计文档/开发方案-工单backlog.md):Batch 0 余项(B0-3 sqlite-vec 检索、B0-4/5 Hermes 联调、B0-6 决策门)→ Batch 1+(协作回路内核、规划/写作/检索、品味/反平庸、门槛、编辑器面板…)。

## 诚实状态

- 🟢 纯代码/schema/单测:已写并通过自检的部分,真实可用。
- 🟡/🔴 需 Hermes 安装 + LLM API key 才能联调/验收的部分:**尚未端到端验证**,绝不谎称已交付。
- 这不是"完整系统",是 Batch 0 起点。完整验收以 [工程11/11b](../设计文档/README.md) 全部硬门通过为准(含百万字真实跑量,需真实环境与时间)。

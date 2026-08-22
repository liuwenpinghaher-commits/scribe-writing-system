# Hermes / LLM 运行时架构审计（Hermes 角色）

- **仓库**：`/home/admin/projects/scribe-writing-system`
- **范围**：模型怎么被调用、能力面怎么切、记忆怎么隔离。不改 UX、不重画章钟。
- **依据**：`docs/CURRENT_ARCHITECTURE.md` + `scribe3/` 代码。根目录 `交付说明.md` 忽略。
- **北极星**：作者能写出人话、有戏、可续的长篇。主编应是**持工具的编辑**，不是被喂技法的续写机。
- **已知不重复报**（除非升级）：`narrative_contract` 已落库但 `write_assemble_v1` 未 `_push("narrative_contract")`；工程门当产品表面；评分词表把「像冲突」写成完成。
- **分类标签**：已实现 / 设计了未接 / 接了但用错 / 根本不该有。

---

### F-H01 三网关隔离仍合理，但产品主路径已不再走「零工具 default」

- **角度**：Hermes
- **严重度**：P2
- **现状**：git 里仍按三网关设计：`overlay.default.yaml`（`:8642` 零 `platform_toolsets.api_server`）、`overlay.scribe3.yaml`（`:8643` 只激活 `scribe3_read`）、`overlay.scribe3_write.yaml`（`:8644` 激活 read+write）。另有阶段 profile：`scribe3_deduce` `:8645`、`scribe3_deduce_preview` `:8646`、`scribe3_plan` `:8647`、`scribe3_draft` `:8648`（`run_stage_policy._POLICIES` + `hermes_runs_env.hermes_runs_api_base_for_env`）。`provision_hermes._PROFILES` / `_PROFILE_MCP_SERVERS` 把 include 白名单做成物理能力面。U-006 启动守卫仍要求 default 零工具（`hermes_status._summarize_hermes_runtime`）。
- **不合理**：`llm.hermes_complete` / `hermes_complete_stream` **已不再打** `llm.HERMES`（`:8642`）。补全面改走 `DeepSeekClient` 官方 Qwen。default 网关变成健康检查/能力声明（`settings.HERMES_API`、`hermes_status` 仍把 `default_gateway_unavailable` 当 error），不是写作/讨论出口。
- **更合理**：三网关（零工具 / 只读 Responses / 写 Runs）作为**工具隔离拓扑**保留；补全面不必再假装走 Hermes chat completions。健康检查应区分「default 仅运维探针」与「产品 LLM 出口」。阶段 profile 是对「Hermes Runs 无请求级 filter」的正确补丁，应继续。
- **不改的代价**：运维以为 `:8642` 挂了写作就死；实际写作已绕开。能力面文档与运行时分流继续漂移。
- **证据**：`scribe3/llm.py` `HERMES` / `hermes_complete_result` / `hermes_complete_stream`；`scribe3/deploy/hermes/README.md`；`scribe3/api/services/hermes_status.py` `_summarize_hermes_runtime`
- **分类**：隔离拓扑 **已实现**；「速答走 default Hermes」**接了但用错**（名还在、路已切）。

---

### F-H02 `hermes_complete*` 是官方无工具补全，GAP-12 按函数名认 Hermes

- **角度**：Hermes
- **严重度**：P1
- **现状**：`llm.py` 模块头写明「无工具 Chat Completions 统一委托已审查的 Qwen 官方服务；Hermes 只保留 Responses 工具面与 Runs」。`hermes_complete_result` → `DeepSeekClient.complete`。`hermes_responses_events(..., with_tools=False)` 同样绕开 `HermesRuntime`，直连官方流。`llm_path_guard.is_hermes_complete_fn` 只要 `__name__`/`__module__` 含 `"hermes"` 即判通过。`misc_routes.chat_stream` 对 `hermes_complete_stream` 调 `assert_llm_path_ok(..., path="discuss")`，默认 `SCRIBE3_HERMES_ONLY_LLM=1`。
- **不合理**：审计约定「讨论必须经 Hermes」被**名字骗过**。真正的 Hermes 边界是 `HermesRuntime.responses_events` / `create_run`。守卫把官方补全标成合规。
- **更合理**：守卫认 `HermesRuntime` 实例或 `api_base`/`transport=hermes`，认 `with_tools` 与 profile。无工具补全显式登记为 `official_complete`，不要顶 Hermes 名。
- **不改的代价**：以后再切供应商/旁路，GAP-12 继续绿；「主编走 Hermes 可审计」是假账。
- **证据**：`scribe3/llm.py` `hermes_complete_result`、`hermes_responses_events`（`if not with_tools` 分支）；`scribe3/llm_path_guard.py` `is_hermes_complete_fn`；`scribe3/api/routers/misc_routes.py` `chat_stream`
- **分类**：**接了但用错**（守卫）+ 命名 **根本不该有**（把官方补全叫 hermes_complete）。

---

### F-H03 写作主路径是「编译巨 prompt + 关工具 + 官方 complete」，不是主编用 `s3_*` 取世界

- **角度**：Hermes
- **严重度**：P0
- **现状**：`write.chat_write` / `chat_write_post`：`_write_intent = _is_write_intent(msg)`（`write_stream._WRITE_VERB_RE`：写|改|续写|帮我写|…）。动稿时 `_wt = ... and not _write_intent` → **关工具**。`_assemble_write_instructions` → `_assemble_write_instructions_v1` 把 prefix/craft/envelope/codex/outline/brief/pressure/voice/… 一次编进 `instructions`。`_stream_write` → `hermes_responses_events(..., with_tools=_wt)`。动稿时走官方补全。`_write_phase_allows_tools` 对 `final`/`deduce` **再关一层工具**。前端 `ChiefDock.send` / `WriteChat`：散文生成词不走 Runs（`hermesRunIntent.PROSE_GENERATION_WORDS`），走 `api.chatWrite`。
- **不合理**：产品铁律是 Surreal 真相源、主编经 `s3_*` 联查。动稿时物理上**禁止**联查，改把世界+技法灌进 system。主编变成续写机。与北极星「持工具的编辑」相反。
- **更合理**：正文生成仍可用无工具补全（避免工具回合抢输出），但输入应是**本 span 的故事约束 + 限知帧**，由编排层或上一轮只读 `s3_*` 取好；不是把整章 envelope+技法圣经一次性灌进续写。讨论/核对必须挂只读工具。
- **不改的代价**：合同/正典再完善，模型也只见灌进去的技法与碎片；续出来的是「像门禁的句子」，不是戏。
- **证据**：`scribe3/api/routers/write.py` `chat_write` / `chat_write_post`；`scribe3/api/services/write_stream.py` `_write_phase_allows_tools` / `_stream_write`；`scribe3/api/services/write_assemble_v1.py` `_assemble_write_instructions_v1` `_push`
- **分类**：**接了但用错**（assemble 本是编译器，被当成续写燃料管）。
- **相对已知债的升级**：已知「合同没 `_push`」。从 Hermes 看更重：主路径在灌 **craft/anti_slop/phase_role/structure_diversity**（`craft.build_craft_block`、`_anti_slop_floor_block`、`structure_style.structure_diversity_block`），却不让模型用工具去取「这场面必须发生什么」。漏合同是漏杠杆；灌技法是用错调用形状。

---

### F-H04 该持工具的讨论走 complete；真 agentic 被 UI 钉死

- **角度**：Hermes
- **严重度**：P0
- **现状**：`ChiefDock.send` 非章脚手架：`api.chatStream(..., agentic: false)`。`api.js` `chatStream`：`agentic ? '/chat/agentic-stream' : '/chat/stream'`。`chat_stream` 用 `assemble_discussion_system` 灌 envelope（讨论全知）+ `hermes_complete_stream`。`chat_agentic_stream` 才是 `:8643` + `s3_*`（`server_label=SCRIBE3_READ_MCP_LABEL`），且注释写明「ChiefDock 默认 agentic:false」。世界写靠启发式/`orchResolve.use_world_write_run` 才进 `api.runWrite` → `settings_gateway.ai_run_create` → `HermesRuntime.create_run`。
- **不合理**：作者问「这人此刻知道什么 / 伏笔开着几条」——该走 read 网关自己取。现网把设定圣经灌进速答，模型凭印象答。该审批的世界写多数能进 Runs（合理）；该 complete 的闲聊也被灌了整书上下文（过重）；该联查的核对既不联查也不轻量。
- **更合理**：讨论默认 `:8643` 只读工具，envelope 只留身份+本轮焦点+预算内证据。世界写保持 Runs。纯寒暄才可无工具短补全。
- **不改的代价**：主编「像读过书」是因为 prompt 里塞了书，不是因为查过库；一超窗就胡编。
- **证据**：`scribe3/web/src/ChiefDock.jsx` `send`（`agentic: false`）；`scribe3/web/src/api.js` `chatStream`；`scribe3/api/routers/misc_routes.py` `chat_stream` / `chat_agentic_stream`；`scribe3/api/services/write_assemble_discuss.py` `assemble_discussion_system`
- **分类**：agentic 路径 **已实现未接 UI**；讨论主路径 **接了但用错**。

---

### F-H05 工具开着时仍全量 assemble：双重灌上下文

- **角度**：Hermes
- **严重度**：P1
- **现状**：`/chat/write` 在**非**写作动词且 phase 允许时 `_wt=True`：既 `_assemble_write_instructions(..., with_tools=True)`（envelope+codex+`_s3_work_scope_block`+`skills_index_block`），又经 Hermes Responses 挂 `scribe3_read`。`chat_agentic_stream._build_instructions`：`assemble_discussion_system` + 长工具说明书（列出 `s3_project_frame` / `s3_list_promises` / …）。`orchestration.resolve` 的 `context_pack` 注释写「不裁剪 assemble envelope」（H1 PR-5）。
- **不合理**：模型同时被喂「世界已在 instructions 里」和「先调工具核实」。注意力被设定洪水占满，工具变成仪式。与 skill 自称「限知靠投影、不靠把全书塞进 prompt」相反。
- **更合理**：有工具面时 instructions 只留身份、work 钉死、本轮问题、取数优先级；世界状态由 `s3_*` 按需取。assemble 的 Manifest 给检查器，不整包进生成。
- **不改的代价**：双份 token；限知帧和秘密门在「已经写在 prompt 里」时失效或被淹没。
- **证据**：`write.py` `chat_write_post` `_wt`；`write_assemble_v1.py` `with_tools` 分支；`misc_routes.chat_agentic_stream._build_instructions`；`orchestration/resolve.py` `context_pack`
- **分类**：**接了但用错**。

---

### F-H06 SOUL「剧情不得进 Hermes memory」只有提示，没有守门

- **角度**：Hermes
- **严重度**：P1
- **现状**：`SOUL.scribe3.md` / `SOUL.scribe3_write.md` 写死：剧情/秘密/设定/伏笔/章事件不得写入 Hermes memory 或 skill；memory 只许稳定工作偏好。`hermesRunIntent.hermesRunInstructions` 再复述一遍。`provision_hermes`：SOUL **仅在目标不存在时写入、不覆盖调优**。`hermes_runtime.build_hermes_request_body` 的 GAP-7 SOUL 分层是另一套英文 env（`SCRIBE3_HERMES_SYSTEM` / `PERSONALITY`），与 profile SOUL 文件不是同一通道。`scribe3-memory` 插件默认不启用（`hermes_plugins/scribe3-memory/README.md`）。没有拦截 Hermes 原生 `memory_*` / `skill_manage` 的代码。
- **不合理**：纪律停在 markdown。模型 `skill_manage` 或 Hermes 自带 memory 写入时，scribe3 看不见、拦不住。
- **更合理**：写 profile 物理不挂 Hermes memory 写工具；skill 目录只读或禁止 `skill_manage`。压缩摘要只进 Scribe `memory_item`（过程记忆），不进 Hermes SQLite。不要把剧情迁进 Hermes memory（本审计禁止此建议）。
- **不改的代价**：跨书/跨会话的 Hermes 档案会脏；限知与正典分叉。
- **证据**：`scribe3/deploy/hermes/SOUL.scribe3.md`；`SOUL.scribe3_write.md`；`scribe3/scripts/provision_hermes.py` `_PROFILES` SOUL 列；`scribe3/hermes_runtime.py` `soul_layers_enabled` / `build_hermes_request_body`；`scribe3/hermes_skills/scribe-novel-v2/SKILL.md`（教 `skill_manage`）
- **分类**：纪律文案 **已实现**；强制隔离 **设计了未接**。

---

### F-H07 压缩 + `store=True` + session 把剧情写进 Hermes 会话库

- **角度**：Hermes
- **严重度**：P1
- **现状**：三网关 overlay 均 `compression.enabled: true`（default 阈值 0.40，read 0.50，write 0.55）。`_stream_write` / `hermes_responses_events` 默认 `store=True`。`HermesTurnContext` 注释：Responses 服务端 LRU 100，掉链靠 Scribe thread + working summary。`tools/backfill_editorial_chat.py` 从 `~/.hermes/profiles/{profile}/state.db` 回填——证明剧情对话已在 Hermes 库。session key 按 `scribe3_session_key(work, thread_id=...)` 隔离（防串书，**不**防本会话剧情进压缩摘要）。
- **不合理**：SOUL 禁「写入 memory」，但压缩就是把已灌进 prompt 的设定/正文摘要写进 Hermes 侧状态。灌得越多，压缩越像第二真相源。
- **更合理**：产品 Web 主路 `store=false` 或会话只存指针；压缩前 `on_pre_compress` 只 flush 到 Scribe（插件已有钩子，主路未用）。Hermes 侧只留偏好。
- **不改的代价**：限知帧与正典更新后，主编仍「记得」压缩里的旧秘密。
- **证据**：`overlay.default.yaml` / `overlay.scribe3.yaml` / `overlay.scribe3_write.yaml` `compression`；`write_stream._stream_write` `store=True`；`hermes_runtime.scribe3_session_key`；`scribe3/tools/backfill_editorial_chat.py`
- **分类**：**接了但用错**（会话连续做对了，记忆边界没守住）。

---

### F-H08 stage filter + 后验拦截：必要，但写路径关掉；草稿面缺故事联查

- **角度**：Hermes
- **严重度**：P2
- **现状**：Hermes Runs 无请求级 MCP 过滤（`run_stage_policy` 模块文档、`llm.py` 注释）。阶段靠独立 profile 的 `tools.include`。`run_tool_filter.filter_tool_calls` 后验：`discuss/agentic` 用 `_DISCUSS_READ_ALLOW`（只读）。`HermesEventAdapter` 默认 `filter_tools=False`；仅 `chat_agentic_stream` `phase="discuss", filter_tools=True`。写路径与 `ai_run_runtime` **显式关过滤**，怕丢掉 `s3_add_*`。`draft`/`final` policy 允许：章读、`project_frame`、state/promises/relations/rules、`s3_save_chapter`、`s3_patch_chapter_plan`；**无** `s3_semantic_recall` / `s3_hybrid_recall` / `s3_list_motifs` / `s3_get_intent` / `s3_recent_phrases`。`s3_save_chapter` 不在 `WRITE_GATED`（手稿非世界状态，不 elicitation）——合理。`s3_ingest_chapter` 也不在 WRITE_GATED，且不在 draft include。
- **不合理**：后验拦不住 Hermes 进程内已执行的 MCP（只拦 SSE 展示）。真正边界是 profile include。草稿阶段若真走 agent，取「本章该避开的措辞 / 母题 / 北极星」会被物理挡掉。讨论后验若误开在写 Run 上会挡改世界——当前关着是对的。
- **更合理**：继续用 profile include 做硬边界。draft 补最小故事联查（intent/motifs/recent_phrases/recall），仍禁 ingest 与设定写。后验只作审计，不作唯一闸。
- **不改的代价**：要么草稿 agent 写盲文，要么有人把写 Run 打开 discuss 过滤，世界写全被 UI 假拦。
- **证据**：`scribe3/run_stage_policy.py` `DEDUCE_ALLOWED_TOOLS` / `PLAN_*` / draft `allowed_tools`；`scribe3/run_tool_filter.py` `_DISCUSS_READ_ALLOW`；`hermes_runtime.HermesEventAdapter._maybe_block_tool`；`mcp/_common.py` `WRITE_GATED`；`mcp/tools_write.py` `s3_save_chapter`
- **分类**：阶段 profile **已实现**（合理克制）；draft 工具面 **接了但偏窄**；后验 **对写路径正确关闭**。

---

### F-H09 `scribe-novel-v2` skill 闲置且工序是错的；技法走了另一条灌索引的路

- **角度**：Hermes
- **严重度**：P1
- **现状**：`hermes_skills/scribe-novel-v2/SKILL.md` 教：`s3_setting_completeness` → `s3_add_event` → `s3_project_frame` → `s3_render_scene` → `s3_save_chapter` → QC → ingest → `delegate_task` → `skill_manage`。`s3_render_scene` **全仓仅出现在该 SKILL**（mcp include / tools 均无）。`craft_skills.py` 定案：`:8643` Responses **不注入原生 skills**，改 `skills_index_block` + `s3_skill_read`。`hermes_status` skill 未加载只 warning。overlay **不**管 skills（Dashboard 原样保留）。`craft_skills/` 四篇（场景转换/对话潜台词/节奏控制/限知视角）在 `with_tools` 时塞进写 instructions。
- **不合理**：官方 Hermes skill 把主编画成「调一个不存在的渲染工具出整章」。产品主路径又不加载它。真正进模型的是技法索引/全文，强化续写机而不是编辑。
- **更合理**：skill 降为内部工序备忘或删掉 `s3_render_scene`/`skill_manage`。技法按需 `s3_skill_read`，且只在讨论/改稿核对轮，不进整章续写 system。
- **不改的代价**：谁在 Dashboard 打开 skill，主编按过期环路空转；Web 主路则被四篇技法处方推动「像会写」。
- **证据**：`scribe3/hermes_skills/scribe-novel-v2/SKILL.md`；`scribe3/craft_skills.py` `skills_index_block` / `read_skill`；`mcp/tools_read.py` `s3_skill_read`；`hermes_status._profile_has_skill`；`deploy/hermes/README.md` skills 归属 Dashboard
- **分类**：skill **设计了未接** + 文档 **根本不该有**（`s3_render_scene`）；`s3_skill_read` **已实现但灌进续写**（用错）。

---

### F-H10 cron / 模型路由 / 流式 / 多 profile：cron 克制对；路由双栈；profile 膨胀

- **角度**：Hermes
- **严重度**：P2
- **现状**：
  - **cron**：`deploy/hermes/crons.yaml` 三 job 全 `no_agent: true`（摘要/摘报/OSV）。`agent_crons.py` 只管 UI enable 位。**正确克制**。
  - **模型路由**：overlay `fallback_providers`（kimi / MiniMax）给 Hermes agent loop；无工具补全走 `DeepSeekClient`/`llm.model`。两套兜底。本审计不建议换默认供应商。
  - **流式**：写作 SSE 经 `hermes_responses_events`；讨论经 `hermes_complete_stream`。`_stream_with_retry` 首 delta 后不重试。合理。
  - **多 profile**：三网关 + 四阶段。`ai_run_create`：`run_scope` 空/`runs` → 全写 `scribe3_write`；`chapter:N:phase` → 受限 profile。`scaffold_forces_stage_profile` 禁止脚手架掉进全写。`ChiefDock` 世界写清空业务 phase，但脚手架仍强制 `run_scope`。
- **不合理**：产品补全已不经 Hermes fallback；Hermes 挂了官方仍能写，官方挂了 Runs 讨论仍能调工具——韧性是双栈，排障却按「一个 Hermes」。profile 从 3 增到 7，与 README「三网关」叙述不一致，但阶段隔离本身对。
- **更合理**：文档改「补全官方 / 工具 Hermes」双平面。profile 维持阶段切面，不要再为每个 UI 按钮加端口。
- **不改的代价**：demo 上「Hermes 红、写作绿」或相反，值守按错层修。
- **证据**：`crons.yaml`；`agent_crons.py`；`overlay.*.yaml` `fallback_providers`；`llm.py` 双路径；`run_stage_policy.resolve_run_stage_policy`；`settings_gateway.ai_run_create`
- **分类**：cron **已实现且克制**；路由 **接了但文档用错**；多 profile **已实现（必要膨胀）**。

---

### F-H11 整章 assemble 当默认生成上下文；span 只有提示词没有调用面

- **角度**：Hermes
- **严重度**：P0
- **现状**：envelope 预算 V1 1e4 / V2 1.8e4 / novel 2.2e4 token（`context_budget.DEFAULT_ENVELOPE_TOKEN_BUDGET_*`），再加 prefix/craft/codex/outline/…。`_write_revision_block` 要求「改稿默认 span 级定向」。`write_assemble_blocks` 围栏 `scope=chapter|selection|append`。仓内 **无** `revise_span` / `/revise-span` 路由或 MCP（检索为零）。现网默认仍是整章 `instructions` + 一次 complete 出 `⟦PROPOSAL scope=chapter⟧`。
- **不合理**：改一句也对整章世界+技法重新推理。Hermes/官方上下文窗口被当成章级显存。这是对运行时的滥用，不是「充分使用」。
- **更合理**：讨论/联查小上下文 + 工具；落笔只喂本 span 约束与前后各 N 句。整章 regenerate 降为明示「重写整章」。
- **不改的代价**：越长越平、越改越像门禁；算力砸在重复灌设定上。
- **证据**：`scribe3/context_budget.py`；`write_assemble_v1._render_final_input`；`write_assemble_blocks._write_revision_block` / `_write_protocol_block`；无 `revise_span` 符号
- **分类**：span 纪律 **设计了未接**（提示有、调用面无）；整章灌 **接了但用错**。

---

### F-H12 MCP 进程内再打 `hermes_complete`：嵌套无工具 LLM

- **角度**：Hermes
- **严重度**：P2
- **现状**：`s3_ingest_chapter` 在 Hermes MCP 桥内调 `hermes_complete`（90s、禁内部重试）抽知识。`s3_fold_voice_flags` 同样。`mcp/tools_read.py` `s3_dedup_cross` / `s3_discipline_check` 也调 `hermes_complete`。`ingest_bg` / `chapters` / `misc_routes.save` 后置同一套。
- **不合理**：若外层已是写 Run（持工具 agent），内层又开官方补全抽事实——两层模型、两套台账（`usage.py` 跨进程日帽能记笔数，但调用形状是「agent 调工具调 LLM」）。ingest 不经审批是刻意的（客观回写），但把抽取引擎绑在名为 hermes 的官方 complete 上，与外层 Hermes 无关。
- **更合理**：ingest/判官保持无工具短补全（该 complete），但从 MCP 工具实现里拆成明确 `official_extract`；不要让写 Run 的模型自己再调会烧一整章抽取的工具当「写完必做」。
- **不改的代价**：一次存稿叠多次 complete；日帽与超时在 MCP 300s 墙里打架（注释已承认）。
- **证据**：`mcp/tools_write.py` `s3_ingest_chapter` / `s3_fold_voice_flags`；`mcp/tools_read.py` `rewrite_cross_repetitions` / `discipline_truncate`；`usage.py` 日帽说明
- **分类**：抽取用无工具补全 **该 complete**；挂在 Hermes 工具里 **形状别扭**（接了但用错命名/嵌套）。

---

### F-H13 最不合理调用点 ① `chat_write_post` → `_stream_write(with_tools=False)`

- **角度**：Hermes
- **严重度**：P0
- **现状**：作者说「写/续写/把这段…」→ 关 MCP → 整章 compile → 官方流式补全 → `⟦PROPOSAL⟧`。
- **不合理**：这是产品主笔入口。主编在这里不是编辑，是被喂技法的续写机。
- **更合理**：编排层先只读取约束（合同/限知/声口/不可逆），再短补全本 span；或允许模型在写前用只读工具取这四样，取完再闭工具出散文。
- **不改的代价**：北极星落空；后面所有评分/GATE 都在优化一台续写机。
- **证据**：`scribe3/api/routers/write.py` `chat_write_post`；`scribe3/api/services/write_stream.py` `_stream_write`
- **分类**：**接了但用错**。

---

### F-H14 最不合理调用点 ② `chat_stream` + `ChiefDock agentic:false`

- **角度**：Hermes
- **严重度**：P0
- **现状**：右栏默认讨论：灌 discussion envelope，官方 complete，无 `s3_*`。真正的 `chat_agentic_stream` 闲置。
- **不合理**：核对世界是编辑的本职。这里最该用 read 网关，却用了最不该用的「假 Hermes 速答」。
- **更合理**：UI 默认 agentic 只读；短寒暄再降级 complete。
- **不改的代价**：作者以为主编查过库；实际是在背 prompt。
- **证据**：`misc_routes.chat_stream`；`ChiefDock.jsx` `agentic: false`；`llm.hermes_complete_stream`
- **分类**：**已实现未接**（agentic）+ **接了但用错**（stream）。

---

### F-H15 最不合理调用点 ③ `_assemble_write_instructions_v1` 把 craft 引擎当 system

- **角度**：Hermes
- **严重度**：P0
- **现状**：同一编译函数服务 GET/POST `/chat/write` 与 loop。恒注入：身份+围栏+`_anti_slop_floor_block`+`structure_diversity_block`+`build_craft_block`+phase_role+…。有工具时再加技法索引。模型被要求同时演「乱世铜炉语体」「身体先行」「温度曲线」「市井密度」。
- **不合理**：调用点把运行时当成技法播放器。持工具的编辑应查「这场必须发生的事 / 他知不知道 / 这句话像不像这个人」，而不是先背七引擎。
- **更合理**：system 极短；故事约束进红线块（合同接上时也只进约束句，不进工程词）；技法留在 `s3_skill_read` 或事后 critique。
- **不改的代价**：散文越来越像评分词表。这是运行时调用形状问题，不是再加一个 GATE。
- **证据**：`write_assemble_v1._assemble_write_instructions_v1` `_push("craft")` 等；`craft.py` `build_craft_block`；`write_assemble_blocks._anti_slop_floor_block` / `_write_protocol_block`
- **分类**：**接了但用错**。

---

## 七问逐条答

1. **三网关是否仍最合理？有没有该 Runs 却 complete、该 complete 却全量 agent？**  
   作为**能力隔离**仍最合理：零工具 / 只读 Responses / 写 Runs + 阶段子 profile。现网偏差：散文与讨论主路径该轻量或该只读 agent，却走了「假 Hermes complete + 巨 prompt」；世界写启发式命中时走 Runs（对）。脚手架强制受限 profile（对）。全量 `scribe3_write` 仍给书级改设定（对）。**没有**把改世界默认丢进 complete；**有**把该联查的讨论丢进 complete。

2. **写作主路径是灌巨 prompt 还是 Hermes 用 `s3_*` 取世界？有没有双重灌？**  
   **灌巨 prompt**。动稿关工具、官方补全。非动稿且挂工具时 **双重灌**（envelope+工具说明书+MCP）。不是「主编自己取世界」。

3. **SOUL 规定剧情不得进 Hermes memory——代码守住了吗？**  
   **没有。** 只有 SOUL/instructions 文本。压缩、`store=True`、`state.db` 会留下剧情。无拦截 `skill_manage` / 原生 memory。`scribe3-memory` 插件默认关，主路不靠它。不要把剧情迁进 Hermes memory。

4. **stage filter + 后验是否必要？是否挡了改故事该用的工具？**  
   **profile include 必要**（Runs 无请求级 filter）。后验只对闲置的 agentic 讨论有用，写路径正确关闭。draft/final 白名单偏窄，会挡 recall/intent/motifs/recent_phrases——这些是改故事该用的读工具，不是写世界。discuss 白名单挡写工具是对的。

5. **skills / cron / 模型路由 / 流式 / 多 profile：闲置还是正确克制？**  
   cron：正确克制。skills：闲置且工序错误；技法改走灌索引。模型路由：双栈（官方补全 + Hermes fallback），文档仍写三网关同配。流式：形状对。多 profile：阶段隔离必要，不是闲置。

6. **整章 assemble vs span 小上下文——现网是否滥用 Hermes？**  
   **滥用的是「章级上下文编译 + 一次补全」**，多数已不经过 Hermes 工具面。Hermes 被闲置在该用的地方，又在 agentic/Runs 上被双灌。span 只有提示，无调用面。

7. **主编应是持工具的编辑。最不合理的 3 个调用点？**  
   ① `write.chat_write_post` → `_stream_write(with_tools=False)`（主笔续写机）  
   ② `misc_routes.chat_stream` + `ChiefDock` `agentic:false`（讨论不联查）  
   ③ `write_assemble_v1._assemble_write_instructions_v1` 把 craft 引擎灌进 system（编辑变技法播放器）

---

## 不建议（按任务约束）

- 不建议换默认供应商。
- 不建议把剧情迁进 Hermes memory。
- 不建议把 EMERGENCY REST 当默认写通道。
- 不建议为「再用一次」去扫所有 `s3_*`；杠杆在主路径调用形状，不在工具目录完整度。

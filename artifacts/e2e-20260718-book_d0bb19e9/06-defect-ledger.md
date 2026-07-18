# 问题台账

## P1-001｜空作品无法创建第一章或第一卷

- 状态：已修复并真机回归。
- 现象：新建作品后手稿目录没有任何创建入口，普通作者无法开始写作。
- 根因：四栏 `ManuscriptDirectory` 只为既有卷渲染加章动作；`api.createChapter` 在前端无调用方，`BinderLayout.handleAddVolume` 未传至四栏目录。
- 修复：根级“新建未分卷章节/新建卷”动作贯通 `ManuscriptDirectory → DirectoryPane → FourPaneShell → BinderLayout`。
- 验证：新增失败后转绿的组件测试；真实浏览器创建卷和首章；`GET /volumes`、`GET /chapters` 按 work 读回。
- 影响：所有空白作品；原先阻断整条从零写作主流程。

## P1-002｜验收进程陈旧导致主编讨论不留痕

- 状态：运行态已修复并复验；不改源码。
- 现象：首轮主编长回复在页面显示完整，但刷新后消失，线程消息接口返回空数组。
- 根因：验收时实际命中陈旧后端进程；它不具备当前 `chat_stream → _ChatTurnLog → chat_message` 留痕实现。
- 修复：停止陈旧后端并以当前 HEAD 启动 `uvicorn scribe3.app:app`。
- 验证：真实 UI 发送“请只回复‘留痕复现完成’”，再用只读线程接口确认 user/assistant 两条消息均绑定 `ethread:book_d0bb19e9:…`；服务访问日志也确认请求携带正确的 `thread` 与 `work`。
- 影响：若不排除陈旧进程，主编讨论、连续上下文和审计回看都会失真。

## P1-003｜章节元数据不可编辑，非法标签触发 500

- 状态：已修复并真机回归。
- 现象：四栏 UI 不提供 `title`、`label`、`volume` 的编辑入口；补入口的首轮真实保存又发现自由文本标签会使 `PATCH /chapters/{seq}` 返回 500。
- 根因：前端未暴露作者字段；后端请求模型把 `label` 放宽为任意字符串，底层 Surreal schema 却只允许 `draft/revise/done/idea/beat`。
- 修复：新增 `ChapterMetaPane`，在章头提供“章节信息”；标签改为受控选项；`ChapterMetaReq` 新增 Pydantic 枚举校验，使非法输入在写库前返回 422。
- 验证：后端回归测试先复现异常后转绿；组件测试验证三个字段都以 `api.patchChapter` 传递；浏览器实际保存《闸底刻名》/`draft`/第一卷，章头和卷树同步读回。
- 影响：所有需要章节命名、状态标记或组织卷结构的作品；修复前既无法完成字段验收，也会因普通输入暴露服务端错误。

## P1-004｜章节详情漏读归属，保存会静默清卷

- 状态：已修复并真机回归。
- 现象：第 2 章从第一卷创建，首次填写标题后却自动落入“未分卷”。
- 根因：`SurrealStore.get_chapter()` 的 SELECT 没有返回 `label` 与 `volume`；章节信息面板把缺失值当空值，并把 `volume: null` 回写。
- 修复：章节详情查询返回 `label` 和 `meta::id(volume)` 裸 ID，与大纲/卷列表契约一致。
- 验证：新增 endpoint 读回测试先红后绿；浏览器将受影响第 2 章重新归第一卷、再次打开面板确认标签与归属不再丢失。
- 影响：所有编辑已有章节元数据的作者；修复前可能造成无提示的章节归卷丢失。

## P1-005｜卷排序不可编辑，连续新建卷会重复排序

- 状态：已修复并真机回归。
- 现象：卷详情没有排序字段；连续创建多卷时因目录刷新未等待，多个卷会以同一排序值创建。
- 根因：`VolumeDetailPane` 未暴露 `sort_order`，`BinderLayout.doAddVolume` 未等待 `reload()` 完成。
- 修复：卷详情提供受控排序输入；新建卷后等待树刷新再允许下一次创建。
- 验证：组件回归测试先红后绿；浏览器将三卷分别设为 1/2/3，`GET /outline` 与卷树读回一致。
- 影响：多卷作品会出现目录顺序失真，进而干扰阅读顺序和后续批量写作。

## P1-006｜动稿把内部工具调用直接输出给作者

- 状态：已修复，生产接口复验通过；界面提案采纳仍待后续浏览器复验。
- 现象：作者要求“直接写正文”后，右栏显示 `<function_calls>` 文本，既未执行联查也未产出正文。
- 根因：`/chat/write` 为动稿仍挂 MCP 工具；当前 Responses 运行时没有把该格式转换为可执行工具事件，模型调用模板被当作普通文本 delta 流出。
- 修复：动稿意图使用已组装的章节上下文直接生成并禁用 MCP；非动稿讨论仍保留只读工具，真正世界状态变更仍走 Hermes Run 审批链。
- 验证：后端定向回归 5 项通过；真实 `/chat/write` 生产流返回 `proposal_start/proposal_chunk/proposal`，输出约 1.8k 字正文且无内部调用文本。
- 影响：修复前直接阻断全文生成，且暴露系统内部协议给作者。

## P1-007｜“推进人物关系”误路由为世界状态变更 Run

- 状态：已修复并回归通过。
- 现象：正文提示含“推进人物关系”时被送到需要审批的 Hermes Run，完成后只返回“先核实”，没有草稿提案。
- 根因：`shouldUseHermesRun` 仅用“推进 + 人物”词面匹配，没有先排除“正文/草稿/续写/场景”等散文生成意图。
- 修复：散文生成意图优先走写作流；“登记伏笔”等明确世界状态变更保持 Run 路径。
- 验证：`writeChat-run-context.test.jsx` 覆盖该真实语句，3 项通过。
- 影响：作者最常见的写作要求被错误阻断在审批工作流外。

## P1-008｜普通写作流缺失上下文绑定，后端返回 400

- 状态：已修复并前端回归通过；待浏览器通道恢复后再次点击复验。
- 现象：修复 P1-007 后，真实 UI 的 `/chat/write` 返回 HTTP 400。
- 根因：前端仅为 Hermes Run 传递上下文；`chatWrite` 漏传 `context_session_id/context_revision/context_hash`，而开启 ContextSnapshot 门后后端强制三件套。
- 修复：普通写作流与 Run 同源绑定，并额外携带 `context_hash`。
- 验证：组件测试断言正文走 `chatWrite` 且传递完整三件套，修复后通过；后端真实生产流以同一三件套成功返回章节提案。
- 影响：开启上下文校验的生产环境中，所有普通动稿请求都会被拒绝。
# P1-009 · 停止已完成 Hermes Run 误报 500

- 状态：已修复并回归。
- 根因：网关回收完成的 run 后返回 404，后端没有按本地终态做幂等处理。
- 修复：`/ai/runs/{run_id}/stop` 对本地终态的上游 404 返回 `already_finished:true`；其他 HTTP 错误返回 502 并记审计轨迹。
- 验证：`scribe3/tests/test_ai_runs.py::test_stop_completed_run_is_idempotent_when_hermes_has_pruned_it` 通过。

# P2-010 · 待确认人物接受期间可重复点击

- 状态：已修复并经真实 UI 复测。
- 根因：接受人物后会重放本章 ingest，网络请求完成前按钮仍保持可点击，可能重复提交同一条裁决。
- 修复：按条目 ID 维护提交中集合；按钮改为“接受中”并禁用，成功或失败后恢复。
- 验证：新增前端回归测试，双击只会发出一次 `acceptUnverified`；浏览器真实验收时“季棠”条目显示“接受中”且禁用。

# P1-011 · 接受人物同步重放 ingest，造成页面长期无响应

- 状态：已修复并定向回归。
- 根因：`POST /ingest-unverified/{id}/accept` 在请求线程内执行 Hermes 重抽和全章回写；角色已创建后，浏览器仍要等待整次 LLM 调用完成，表面上像按钮卡死。
- 修复：接口先完成可审计的角色确认，再用既有 `BackgroundTasks` 入队章节 replay；响应提供 `replay_queued`，前端告知作者后台回填的章节号。
- 验证：后端测试先断言 `complete_fn is None` 与后台任务入队，修复后通过；前端测试断言后台回填提示文本，修复后通过。真实旧条目因此前重放已完成，无法重复提交，但刷新后已确认的“季棠”作为实际角色存在。

# P1-012 · 事件器物被送入“待确认人物”队列

- 状态：已修复并回归。
- 根因：事件 `SUBJ/OBJ/WITNESS` 复用 `_resolve_char`；该函数对任何未知字符串都登记 pending。LLM 一旦把“半截鱼骨”等器物误填入 `OBJ`，就生成 `event_OBJ` 人物候选。
- 修复：事件参与者仅匹配已确认的 `role:<name>`，未知值仅跳过关联、不再登记人物候选；抽取提示增加“只填具体人物姓名，器物/地点/刻字/自然现象不得填入”的硬约束。真正新角色仍由 `learned/did` 等人物语义字段进入确认链。
- 验证：修改既有事件未知参与者测试，先复现 pending 脏记录再转绿；同时验证已确认角色仍正确写入事件图，提示词测试通过。

# P1-013 · 保存影响声音的角色质变后，声音演变区未即时刷新

- 状态：已修复并真人同页回归。
- 根因：`DynamicTimeline` 成功写入 `/char-states` 后只刷新自身时间线；`CharVoice` 的加载 effect 仅依赖 `characterId`，没有接收到状态保存事件，导致当前页面保留旧的 flags/profile。
- 修复：为 `DynamicTimeline` 增加 `onStateAdded` 回调，贯通至 `CodexDetail` 的 `voiceRefresh`；`CharVoice` 依赖 `refreshKey` 重载声音数据。
- 验证：新增失败后转绿的 Vitest 用例，断言保存质变会通知外层刷新；真实页面先折叠第 4 章标记、再新增第 5 章影响声音质变，立即显示“1 条待折叠 / 一键折叠(1)”。
- 影响：修复前作者必须切换角色或刷新页面才会意识到需要复核声线，容易遗漏人物口吻变化。

# P1-014 · 人工插入素材后没有反向溯源

- 状态：已修复，待浏览器发布→采纳回归。
- 复现：在素材《盐港闸底勘察笔记》中点击“插入到草稿”、发布到第 3 章后，`GET /materials/recall` 能命中该素材，但 `GET /materials/refs-by-chapter?chapter=3` 返回空数组。
- 根因：`MaterialDetail.publishToDraft()` 只发布正文；`stageProposal` 不携带素材 ID。草稿页接受候选后没有任何路径调用已有的 `SurrealStore.add_material_reference()`，仅自动写作召回会创建引用。
- 修复：候选追加 `materialId`；作者点击“填入/追加/替换”时调用新增 `POST /materials/{mid}/refs`，写入 `via=manual_insert`、章节和人工插稿维度。
- 验证：新增 endpoint 回归先红（405）后绿；`test_material_refs_and_paging.py` 4/4 通过。运行态新端点真实返回 `ok:true`，并已为第 3 章先前采纳的素材补写审计引用。

# 阶段2 · 写作走 hermes Spec(续写/改写/质量由主编主笔)

**目标**:把写作生成(续写/改写/扩写/质量/摘取)从 scribe 直连 doubao **迁移到 hermes 主编**(用 scribe 工具+技能)。这是 spec §1 要消除的"绕过 Hermes"根因的正解。

## 架构(依赖阶段1 的 run 驱动管道)
- **写章流程 SKILL.md**(hermes 技能):检索 ContextBundle(search_book/list_settings/相关伏笔)→ 注入品味 → 生成 → 写回 `save_snapshot`/`index_segment`(经 scribe MCP)。
- **品味插件 `scribe-taste`**:Hook `pre_llm_call` 注入 StyleExemplar few-shot + 反例黑名单(内核2)。
- **连贯插件**:Hook 写后自动 `check_chapter`(门槛1)。
- **前端写作操作改 run 驱动**:`actions/continue|rewrite|expand` 从调 scribe_mcp(直连doubao)改成触发 hermes run(写章技能),复用阶段1 的 SSE+审批(存稿走审批 diff)。

## 待实测/待定(实现前对齐)
- hermes SKILL.md 的格式与注册(`hermes skills` 新版)
- hermes 插件 Hook 机制(pre_llm_call/post_tool_call)新版 API
- 主编用哪个 LLM 写中文小说(hermes provider 配 doubao? 还是用 config 的默认?)— 关键质量点,需对比

## 验收
- 续写/改写由主编(经 hermes run+写章技能)产出,scribe 不再直连 doubao
- 品味/反平庸/连贯在生成时生效(非事后)
- 前端写作操作走 run、出 diff、存稿审批

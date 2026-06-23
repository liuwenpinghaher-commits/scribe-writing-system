# scribe3 声音库 + 声音进化 · 设计

> 设计日期:2026-06-23
> 目标:给角色建声音库(4 类独白)+ 渲染注入防 OOC + 半自动声音进化,解决"第20章和第1章一个调"。

## 目标

scribe3 角色当前只有 `name/aliases/backstory`,渲染不注入任何声音样本——角色声音易漂移/OOC,且不随情节演化。本设计:
1. **声音库**:每角色 4 类独白(自由/压力/关系/叙述),store 持久化、可版本化。
2. **渲染注入**:render 注入 focalizer 的最新版声音样本(防 OOC + 自动用进化后的新版)。
3. **半自动进化**:后台 ingest 复用其 LLM 检测"重大事件"→ 标记"声音或需更新"(不自动生成独白,人定内容,避漂移)。

## 设计(approach:半自动 + 复用 ingest LLM)

声音是精心之物,**生成独白的活交给人,系统只做检测提示 + 存储 + 注入最新版**。进化检测复用后台 ingest 已有的 LLM 调用(语义判断"重大"比确定性活跃度准,且不额外加 LLM)。

### A. store `voice_sample` 表(per-character + 版本)

```
voice_sample(SCHEMALESS):{character, kind, text, since_chapter}
  kind ∈ free / pressure / relation / narration
  进化 = 同 character+kind 追加新行(更大 since_chapter),旧版保留
```
迁移 `migrations/009_voice.surql` 建表。store 方法:
- `add_voice_sample(character, kind, text, since_chapter=0)` — 经 `_execute_write` 单点
- `list_voice_samples(character)` — 全部(各 kind 各版本)
- `latest_voice_samples(character, upto_chapter)` → `dict[kind, text]` — **每个 kind 取 `since_chapter ≤ upto` 的最新一条**(时间门:第20章自动用进化后的版本,不剧透未来版本)

### B. render 注入 focalizer 声音样本

`build_render_prompt(world, chapter, focalizer, ..., voice=None)`:在"知识帧事实"之后、craft_block 之前插入(若有声音库):
```
## 你(焦三)的声音(保持一致,别串味)
- 自由独白:…   - 压力独白:…   - 关系独白:…   - 叙述语气:…
```
`render()` 读 `world.latest_voice_samples(focalizer, chapter)` 传入(World 内存版加空实现 `{}` 鸭子兼容)。**不破限知**:声音是 focalizer 自己的,他当然知道自己怎么说话。

### C. 半自动进化检测(复用 ingest LLM + 标记表)

- `migrations/009_voice.surql` 同时建 `voice_evolution_flag(SCHEMALESS):{character, seq, reason, status}`。
- `critique.build_knowledge_extract_prompt` 扩展:抽 learned/did 时**顺带**抽 `voice_shift:[{who, reason}]`("哪些角色这章经历了可能改变其说话方式/声音的重大事件——创伤/背叛/重大转折")。
- `critique.parse_knowledge_delta` 解析新增 `voice_shift` 字段。
- `ingest.apply_delta` 把 `voice_shift` 写入 `voice_evolution_flag`(`status='open'`)。**只标记,不生成独白**。
- store:`add_voice_flag(character, seq, reason)` / `list_voice_flags(status='open')`。
- 提示落地:前端/主编读 open flags → 提示作者"X 这章经历 Y,声音或需更新"。作者加新版 voice_sample(B 的 latest 机制下次渲染自动用上)。

### REST/MCP(作者编辑声音库)

- REST `POST /voice` (add) / `GET /voice?character=` (list) / `GET /voice-flags` (open flags) — 作者像编辑设定库一样维护声音库。
- (MCP 工具可选,本期先 REST;主编 agentic 已能调 s3_ 读工具,写声音库走 REST 作者端即可)

## 组件

| 文件 | 改动 |
|---|---|
| `migrations/009_voice.surql` | 新建 `voice_sample` + `voice_evolution_flag` 两表 |
| `scribe3/store.py` | `add_voice_sample`/`list_voice_samples`/`latest_voice_samples`/`add_voice_flag`/`list_voice_flags` |
| `scribe3/ontology.py` | `World.latest_voice_samples()` 空实现(鸭子兼容) |
| `scribe3/render.py` | `build_render_prompt` 加 voice 注入;`render` 读 latest_voice_samples |
| `scribe3/critique.py` | `build_knowledge_extract_prompt` 加 voice_shift 抽取;`parse_knowledge_delta` 解析 |
| `scribe3/ingest.py` | `apply_delta` 写 voice_evolution_flag |
| `scribe3/app.py` | REST `/voice`(add/list)+ `/voice-flags`(open) |

## 数据流

```
作者填初始声音库 → voice_sample 表
渲染第N章(focalizer=焦三):
  render → latest_voice_samples(焦三, N) → build_render_prompt 注入"你的声音" → 防 OOC
写完存稿 → 后台 ingest:
  LLM 抽 learned/did + voice_shift → apply_delta 写 voice_evolution_flag(标记)
作者看 open flags → "焦三这章经历背叛,声音或需更新" → 加 pressure 独白新版(since_chapter=N)
下次渲染焦三 → latest 自动用新版(N≥触发章)→ 声音演化生效
```

## 测试策略(TDD)

| 测试 | 断言 |
|---|---|
| `test_voice.py::test_add_list_voice_sample`(store fixture) | add 4 类 → list 全在 |
| `test_voice.py::test_latest_voice_time_gate` | 同 character+kind 两版(since 1 / since 10);`latest_voice_samples(c, 5)` 取第1章版、`(c, 10)` 取第10章版 |
| `test_voice.py::test_voice_flag_add_list` | add_voice_flag → list_voice_flags(open) 含它 |
| `test_render.py::test_prompt_injects_voice` | `build_render_prompt(..., voice={...})` 输出含"你的声音"+独白文本 |
| `test_render.py::test_voice_does_not_break_pov`(load-bearing) | 注入声音后,老道视角仍不含焦三私密 |
| `test_critique.py::test_extract_prompt_has_voice_shift` | `build_knowledge_extract_prompt` 含 voice_shift 抽取指令 |
| `test_critique.py::test_parse_voice_shift` | `parse_knowledge_delta` 解析含 voice_shift 的 JSON |
| `test_ingest.py::test_apply_delta_writes_voice_flag`(store) | delta 含 voice_shift → voice_evolution_flag 落库 |
| `test_app.py::test_voice_rest`(可选) | POST /voice → GET /voice 返回 |

## YAGNI(不做)

- **不自动生成独白**(半自动,人定内容;系统只检测标记 + 注入)。
- **不做 OOC 自动判定/声音相似度检测**(靠 render 注入防 OOC,不额外算)。
- **不做进化 flag 的复杂工作流**(就是标记 + 作者看 + 加新版)。
- 声音库编辑先 REST(作者端),不做 MCP 写工具(YAGNI,需要再加)。

## 不变量 / 风险

- 声音注入**不破限知**:focalizer 自己的声音,test_voice_does_not_break_pov 守护。
- `latest_voice_samples` 是**时间门**:`since_chapter ≤ upto` 防剧透未来版本(同 Progressions 原则)。
- `build_knowledge_extract_prompt` 扩展 voice_shift 不能破坏现有 learned/did 抽取(既有 ingest 测试守护)。
- voice 注入增加 render prompt 长度(4 类独白),在窗口内;若过长可只注入 narration + 1-2 类(plan 阶段定上限)。

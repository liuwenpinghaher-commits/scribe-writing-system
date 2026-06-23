# scribe3 craft 资产改进与旧版清理 · 设计

> 设计日期:2026-06-23
> 依据:[两版复盘-Opus交叉决策.md](../refs/两版复盘-Opus交叉决策.md)、[scribe2-retrospective.md](../refs/scribe2-retrospective.md)、[hermes-novel-retrospective.md](../refs/hermes-novel-retrospective.md)

## 目标

把两个旧写作系统的 craft 价值(七大引擎 + 情感词典 + 实战 QC 规则)以**引擎层/题材层分离**的正确架构落地进 scribe3 渲染管线,让渲染端真正具备正面 craft 引导;并删除已无价值的 scribe2、hermes-novel 两个旧系统。

## 背景:scribe3 的 craft 缺口

scribe3 当前状态(一手核实):
- **限知**:靠知识帧投影(`knowledge.project_frame`),物理保证,强。
- **确定性 QC**:`critique.py` 已从 scribe2 移植(`find_repetitions`/`find_purple_prose`/`discipline_check`),强。
- **正面 craft 引导**:几乎为零。`render.py:14-24` 的 `_CONSTRAINT` 仅有"show 不 tell + 禁 3 个词 + 不双高潮",对比 hermes-novel 的七大引擎是巨大缺口。
- **情感词典/温度曲线/身体先行**:完全没有。

## 设计依据:三条必须落地的交叉分析决策

1. **约束注入 vs 信息屏障**(发现 A):负面禁令(禁用词清单)留在后置 critic,不塞渲染 prompt;渲染 prompt 只放正面 craft 引导。scribe3 已部分做对(禁词主力在 `critique.py`),本设计强化之。
2. **题材规则耦合**(发现 B):craft 拆"引擎层(题材无关)/ 题材层(per-work)"两级。判据:换本书还成立吗?成立→引擎层。
3. **craft wiki 是科幻提炼**(勘误):情感词典/温度范例的科幻残留(沈默/姜婉/陆远舟/校准/波形图)迁移前必须清洗。

## 架构(Approach C:混合分层)

```
引擎层(题材无关,所有书共享)          scribe3/craft.py
  · ENGINES   七大引擎结构化文本
  · PALETTE   情感词典 15 种(已清洗)
  · build_craft_block(rules=None) → 注入渲染 prompt

题材层(每本书特化,SurrealDB per-work)  craft_rule 表
  · 升华正则 / 法器写法 / 角色覆盖动作
  · 主编经 elicitation 改,热更新,跨书隔离

浸泡前置(渲染前,开关默认开)           scribe3/soak.py
  · 以 focalizer 写意识流(丢弃)+ CoT
  · 情感曲线/种子词 → 带进正式渲染 prompt

后置 QC(负面禁令兜底,已有)            scribe3/critique.py
  · 确定性扫描 + LLM 纪律闸
```

## 组件清单(文件级)

### 新建 `scribe3/craft.py` — 引擎层
- **职责**:题材无关的 craft 常量 + 组装函数。纯常量/纯函数,无 DB/网络依赖,可离线单测。
- **接口**:
  - `ENGINES: dict[str, str]` — 七大引擎(`body`/`temperature`/`idle`/`subtext`/`metaphor`/`sensory`/`soak`),每条为结构化引导文本。
  - `PALETTE: dict[str, dict]` — 15 种情感,每种 `{body_signals: [...], inner: [...]}`,**不含角色名/科幻物**。
  - `build_craft_block(rules: list[dict] | None = None) -> str` — 组装引擎引导块;`rules` 为题材层 craft_rule,叠加在引擎层之后。
- **依赖**:无。

### 新建 `scribe3/soak.py` — 浸泡前置
- **职责**:渲染前让模型进入 focalizer 状态,产出情感曲线种子词(意识流文本丢弃)。
- **接口**:`soak(world, chapter, focalizer, complete_fn) -> dict` 返回 `{seed_words: list[str], emotion_arc: str, turn: str}`。
- **实现**:用知识帧 + 本章事件构造 soak prompt(以 focalizer 身份写 300 字意识流 + 回答 4 个 CoT 问题:情感起点/终点/转折时刻/种子词),只解析 CoT 结构化产出。
- **依赖**:`knowledge.project_frame`、`render._events_at`。

### 改 `scribe3/render.py`
- `build_render_prompt(world, chapter, focalizer, craft_block="", soak_result=None)`:在“本章事件”之后、`_CONSTRAINT` 之前依次插入 `craft_block` 与 soak 种子词段(顺序同数据流:事件 → craft_block → soak 种子词 → _CONSTRAINT)。
- `render(..., soak: bool = True)`:`soak=True` 时先调 `soak.soak()` 拿种子词,再 `build_render_prompt`。
- **限知不破**:craft_block 与 soak 段都不得引入知识帧外的事实(craft 是写法引导,soak 只用帧内事实)。

### 改 `scribe3/mcp.py`
- `s3_emotion_palette(emotion: str = "") -> dict`(只读):查情感词典,空参返回 15 种名,带参返回该情感的身体信号/内部感觉。
- `s3_craft_rule_list(work) -> list`(只读)。
- `s3_craft_rule_add(work, kind, pattern, note)` / `s3_craft_rule_remove(work, rule_id)`(写,经 elicitation 待批)。

### 改 `scribe3/store.py` + migrations
- 新增 `craft_rule` 表(per-work):`{work, kind, pattern, note}`,`kind ∈ {purple_regex, artifact_craft, cover_action}`。SCHEMALESS,跟随现有 schema 幂等建表模式。

### 改 `scribe3/critique.py`
- 确定性扫描补两条通用 AI 腔正则(从 hermes-novel `hard-checks.md` 提):E1 破折号全章 > 5、E2 `不是.{1,15}——是`。这是题材无关的负面禁令,放后置 critic。

### 改 `hermes_skills/scribe-novel-v2/SKILL.md`
- "写作纪律(craft)"段从 3 句扩展:引用引擎层(身体先行/温度曲线/闲笔/潜台词/认知比喻/感官锚定)+ 浸泡流程(写前 soak)。指向 `craft.py` 为单一真相源,避免 SKILL 与代码再次脱节。

## 数据流:写一章时 craft 如何流动

```
s3_render_scene(focalizer, chapter)
  → project_frame → 知识帧(限知,物理)
  → soak(focalizer, 事件) → seed_words / emotion_arc      [新·浸泡]
  → build_craft_block(craft_rule[本书]) → craft_block      [新·引擎层+题材层]
  → build_render_prompt:
       知识帧事实 + 本章事件 + craft_block + soak种子词 + _CONSTRAINT
  → complete_fn → 正文
  → s3_qc_chapter:确定性扫描(_PURPLE_PATS + E1/E2)+ discipline_check  [已有·负面兜底]
```

## 科幻残留清洗策略

迁移 `写作/.agents/wiki/` 的情感词典/身体先行/温度曲线时,**抽象化**所有科幻具体词:
- 覆盖动作 `沈默:调出数据面板/校准参数` → `压抑理性型:用精确的手上工作覆盖波动`(去角色名 + 去科幻物)。
- 删除 `波形图/探针/数据日志/食堂酸菜鱼` 等具体物,换中性结构描述。
- 引擎层 `PALETTE` = 纯结构,零具体题材词;本书角色的**具体**覆盖动作放题材层 `craft_rule(kind=cover_action)`。
- **验收断言**:`craft.py` 全文不含 `沈默|姜婉|陆远舟|校准|波形图|数据面板|探针`。

## 题材层第一本书种子(乱世铜炉系,实战资产)

写入 `craft_rule` 默认种子(从 scribe2 实战规则移植):
- `purple_regex`:scribe2 `_PURPLE_PATS` 的 8 条(`天地为炉|万物为铜`、`原来…就/早就`、`有些…就再也` 等)。
- `artifact_craft`:法器四件套规则(专名 + 工艺/工序 + 术数 + 义理,至少齐 3 项),范例"灵龙镇煞钉"。

## 迁移 + 删除流程(不可逆操作在最后,逐项报告)

### ① 提取(把价值搬进 scribe3)
- 从 `写作/.agents/wiki/`(craft/03-body、04-temperature、02-idle、05-metaphor、06-subtext、07-sensory-anchor、toolkit/emotion-thesaurus)萃取七大引擎 + 情感词典 → `craft.py`,执行科幻清洗。
- 从 scribe2 `critique.py` `_PURPLE_PATS` + `writing.py` CONSTRAINT_BLOCK 第 7 条 → 题材层种子。

### ② 验证(确认价值已落地、无遗漏)
- `craft.py` / `soak.py` 单测通过。
- 真机渲染一章:断言 prompt 含 `craft_block`、含 soak 段、知识帧外事实仍不出现、`craft.py` 无科幻词。

### ③ 删除(验证通过才执行,逐项确认)
- `git rm -r scribe/`(scribe2 代码,143 追踪文件)。
- `rm -rf 写作/hermes-novel/ 写作/.agents/wiki 写作/.agents/wiki-backup-v3`(hermes-novel 本体)。
- `rm -rf ~/.scribe/data.db`(scribe2 SurrealDB 库数据)。
- **九原渡 32 章书稿(`scribe/out/`)随 `scribe/` 一并删除,不留档**(用户 2026-06-23 决定)。
- 清理 Hermes 全局 `~/.hermes/config.yaml`:删 `skills.external_dirs` 的 scribe2/hermes-novel 两行、删 `mcp_servers.scribe2` 块。
- **保留** `写作/` 其余(开源副本 novel-engine/book-genesis/inkos/NovelForge 等 + 备份 72M)。

## 测试策略(TDD)

| 测试 | 断言 |
|---|---|
| `test_craft.py::test_engines_present` | `build_craft_block()` 含七引擎关键词(身体先行/温度/闲笔/潜台词/比喻/感官) |
| `test_craft.py::test_palette_complete` | `PALETTE` 15 种情感齐,每种有 body_signals |
| `test_craft.py::test_no_scifi_residue` | `craft.py` 源文本不含 `沈默\|姜婉\|陆远舟\|校准\|波形图\|数据面板\|探针` |
| `test_craft.py::test_themed_rules_appended` | `build_craft_block(rules=[...])` 把题材层 rules 拼在引擎层之后 |
| `test_soak.py::test_soak_returns_cot` | 注入 fake complete_fn,返回含 seed_words/emotion_arc/turn |
| `test_render.py::test_prompt_has_craft` | `build_render_prompt(craft_block=X)` 输出含 X |
| `test_render.py::test_soak_seeds_injected` | soak_result 的种子词出现在 prompt |
| `test_render.py::test_limited_pov_unbroken` | 知识帧外私密事实仍不在 prompt(craft 不破限知) |
| `test_craft_rule.py::test_per_work_isolation` | A 书的 craft_rule 不出现在 B 书查询 |

## 不做(YAGNI)

- **不做范文浸泡库**:hermes-novel 的 13000 字范文注入太贵;用 `soak.py` 即兴意识流替代(便宜且贴合 scribe3 知识帧架构)。
- **不做非线性叙事引擎 / 留白配额**:两旧系统都缺,是真空白,但本期不补,单列 future。
- **不大改 web app 主编对话端**:craft 通过 SKILL.md 引用 `craft.py` 即可生效,本期不动 `app.py`/`proposal.py` 结构。

## 影响面 / 风险

- 浸泡前置每章多一次 LLM 调用(token×~1.5),由 `soak` 开关控制,可关。
- 删除为不可逆操作,放在迁移+验证之后,逐项执行并报告;执行阶段(plan)有独立 review gate。
- `craft.py` 注入增加渲染 prompt 长度(~引擎层 1.5-2k 字),在 doubao 上下文窗口内,无溢出风险。

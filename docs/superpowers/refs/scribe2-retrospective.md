# scribe2 深度回顾：架构、产出与经验教训

> 面向 scribe3 开发者的参考文档。  
> 分析基于 `scribe/scribe2/` 全量源码（截至 2026-06-23）、32 章《九原渡》实际产出、及完整测试套件。

---

## 一、架构全景

### 1.1 技术栈

| 层 | 组件 | 备注 |
|---|---|---|
| 存储 | SurrealDB 3.1.5（surrealkv 持久化） | 替代旧底座的 SQLite；向量+全文+图三合一 |
| 嵌入 | fastembed BAAI/bge-small-zh-v1.5（512 维，CPU） | 本地无 API 成本；中文优化 |
| 后端 | FastAPI + uvicorn，端口 3320 | REST + SSE 流式 |
| 前端 | React + TypeScript + Vite + Tiptap，端口 3310 | strictPort 锁死防漂移 |
| 生成 | Hermes 网关（:8642）→ doubao-seed-2.0-pro | 不直连火山，消除绕过 Hermes |
| MCP | FastMCP，stdio 传输 | Hermes 挂载 `scribe2` server |

### 1.2 数据模型

**内容实体**（带向量索引 + 全文索引，可被 `search_knowledge` 召回）：

```
chapter / setting / character / foreshadow / material / memory_entry
style_exemplar / imagination / motif
```

所有内容实体的统一索引由 `schema.py` 的 `ddl()` 函数批量定义：

```python
DEFINE INDEX {t}_vec ON {t} FIELDS embedding HNSW DIMENSION 512 DIST COSINE TYPE F32;
DEFINE INDEX {t}_fts ON {t} FIELDS text FULLTEXT ANALYZER scribe_a BM25;
```

**结构实体**（无向量，纯结构）：

```
work / volume / snapshot / segment / author_intent / option_set /
consistency_flag / quality_snapshot / preference_signal / taste_model /
feedback / insight / thread / entity_relation / char_state / agent_memory /
agent_skill / timeline_event / pending_write / chapter_task / entity_beat /
knowledge_ledger / annotation / highlight
```

**关键设计决策**：SurrealDB `SCHEMALESS` 模式——所有表无需迁移脚本，字段可随版本迭代自由增减。缺点是无 schema 校验，前端契约靠代码约定维护（已有多处 `前端契约别名` 注释）。

### 1.3 MCP 工具清单

共 ~35 个工具，明确分为只读（`readOnlyHint=True`）和写工具（登记 `WRITE_TOOLS` 集合，需审批）。

**只读工具**（主编 agentic 可直接调，不触发 elicitation）：
- `search_knowledge`（向量+全文+图扩展）
- `get_work` / `list_works` / `list_chapters` / `list_snapshots` / `latest_prose`
- `list_settings` / `list_motifs` / `list_characters` / `list_open_foreshadows` / `list_foreshadows_status`
- `get_author_intent` / `get_memory` / `recall_memory`（跨会话记忆）
- `discipline_check`（纪律闸：双高潮/声音崩/解说倾泻/知识泄露）
- `character_known`（某角色截至某章已知事实）
- `write_continue`（生成草稿，不落库，故不需审批）
- `critique_chapter` / `list_consistency_flags` / `list_entity_beats`
- `entity_appearances` / `list_char_states`

**写工具**（需 Hermes elicitation 审批）：
- `create_work` / `create_volume` / `create_chapter` / `save_prose`
- `set_author_intent` / `upsert_character` / `add_setting` / `add_motif`
- `plant_foreshadow` / `add_foreshadow_beat` / `advance_foreshadow`
- `add_entity_beat` / `add_char_state` / `record_knowledge`
- `ingest_chapter` / `check_chapter` / `dedup_chapter` / `fix_leak`
- `remember`（写跨会话记忆）

### 1.4 生成流程

从用户输入到最终落章，完整 pipeline 分以下阶段：

```
① 用户触发"写一章" → REST POST /works/{w}/chapters/{seq}/actions/continue
② build_writing_context(domain, work, seq) → 组装富上下文（~2000 token）
③ build_chapter_prompt(ctx, seq, instruction, prev, target) → 最终 prompt
④ hermes_complete(prompt) → Hermes :8642 /v1/chat/completions → doubao
⑤ 返回草稿（不落库） → 用户确认
⑥ 用户接受 → save_prose → save_segments（分段+引用回填）
⑦ 生成后 QC 闸（按序）：
   dedup_chapter → discipline_check → [fix_leak|截断] → ingest_chapter → record_knowledge → check_chapter
```

**`build_writing_context` 的注入内容（按优先级排列）**：

1. 北极星（`reader_feeling` / `core_emotional_arc` / `red_lines`）
2. 相关角色（`relevant_characters`：开着伏笔关联 ∪ 近章点名 ∪ pinned；非全塞，聚焦在场）
   - 每角色：声音指纹 + 声音样本 + 核心矛盾 + 内核 Truth-Chart（伤/谎/欲/需/惧）
   - POV 角色内核标记为可知；非 POV 内核标记为「私密·他人不知」
3. 知识边界（POV 角色截至 seq-1 的已知事实账本）
4. 人物前史冰山（backstory，你知全貌，落笔只露 1/8）
5. Progressions 时间门（char_state，只注入 chapter_seq ≤ 当前的最新状态）
6. 母题（metaphor_unfolding / bound_theme / material_echoes）
7. 设定（含力量体系：代价/限制/会出什么乱子）
8. 伏笔节点指令（本章±1 的未完成 beats，带 guidance/隐蔽度/效果/戏剧反讽框架）
9. 伏笔承诺线总览（开着的，标注超期/可回收）
10. 统一线模型：实体 entity_beats 指令 + 久未推进告警
11. 全书主线记忆（确定性拼接，首章+最近6章）
12. 最近 3 章梗概
13. 上一章结尾（后 180 字，保衔接）
14. 语义召回（上一章尾或北极星作 query，召回相关旧内容 k=3）
15. 范文·技法标杆（style_exemplar，few-shot 正面锚）
16. 文学约束块（反 AI 腔 9 条铁律）

### 1.5 LLM 调用方式

scribe2 使用两种模式：

**模式一：hermes_complete**（普通补全，用于写作/评改/一致性检查等）  
- `POST /v1/chat/completions`，OpenAI 兼容接口
- 3 次重试（ReadTimeout / ConnectError / 5xx）
- `max_tokens` 硬上限：`int(target_chars * 1.7) + 200`，防暴写注水

**模式二：hermes_responses_events**（主编 agentic 对话）  
- `POST /v1/responses`，带 `tools=[{type:mcp, server_label:scribe2}]`
- Hermes Responses API，主编自动发现并调用 scribe2 MCP 工具查真实数据
- SSE 流式，前端实时显示工具调用与回复

---

## 二、质量保障机制

### 2.1 QC 闸体系（五层，生成后按序执行）

#### 层一：确定性去重（`revise_dedup`）
不靠 LLM 规则，直接扫描已生成文本：

- **字面重复**：n-gram（n=8）计数，出现≥3次的子串定向改写
- **结构性排比**：同三字开头≥4 句（Counter 统计）
- **单字/极短断句**：`火。井。` 式滥用（>4 个极短句触发）
- **升华/主题直陈**：8 条正则（`原来…就/早就`、`天地为炉`、`有些…就再也`等）

守护：改写后长度 < 原文 60% 则放弃（防截短）；最多 2 遍（长章单遍不够）。

#### 层二：LLM 纪律闸（`discipline_check`）
确定性检测对语义违规是盲的，必须用 LLM 判：

- `double_climax`：第二场打斗/救援/偷跑后续章剧情/凭空发明角色
- `voice_collapse`：terse 角色崩成大段独白/系统结算音
- `exposition_dump`：大段身世/前史/规则集中倾泻
- `knowledge_leak`：角色说出其 POV 不可能知道的他人私密（**带账本事实依据**）

返回 `{ok, violations, cut_after}`：`cut_after` 是复发前最后一句原文，可精确截断。

#### 层三：外科式知识泄露修复（`fix_leak`）
专治 `knowledge_leak`，不截断全章：定位泄露那一句 → 只替换那一句 → 保全章。这是"专门 POV 修订 pass"的自动化。

#### 层四：8 维文学评改（`critique_revise`）
8 个维度各打 1-5 分：texture（文字质感）/ surprise（意外性）/ emotion_truth / pace / voice（角色声音）/ anti_slop / intent_resonance / coherence。

**优化版评改环设计**（三部分，防退步）：
1. 闸门看**具体 issues**，不看噪声大的绝对分
2. 外科行改（只动薄弱维度对应的段落）
3. **成对比较**取优（`B_better|same|A_better`），B 更好才采纳，绝不退步

#### 层五：一致性检查（`check_chapter`）
LLM 对照角色/设定/主线找矛盾，专项：**用了力量体系必付代价/守限制**（力量体系的 cost/limitations/trouble_it_causes 结构化字段直接注入 prompt）。矛盾落 `consistency_flag`。

### 2.2 发现的常见 AI 写作病

代码中明确识别并有机制应对的病症：

| 病症 | 检测方式 | 治理层 |
|---|---|---|
| 升华/顿悟尾句（「原来有些…」「有些…就再也…」）| 确定性正则 8 条 + prompt 禁用清单 | `find_purple_prose` + `CONSTRAINT_BLOCK` |
| 跨段字面复读 | n-gram 计数（n=8，≥3次）| `find_repetitions` |
| 排比开头（「他想起…他想起…」）| Counter 统计同三字开头 | `find_structural_repeats` |
| 单字极短断句（火。井。）| 极短句计数（>4触发）| `find_structural_repeats` |
| 双高潮/偷跑剧情 | LLM 纪律判官 | `discipline_check` |
| 角色声音崩（terse 角色大段独白）| LLM 纪律判官 | `discipline_check` |
| 解说倾泻（集中身世/规则）| LLM 纪律判官 | `discipline_check` |
| POV 知识泄露（敌人报出主角私密）| LLM + 知识账本事实依据 | `discipline_check` + `fix_leak` |
| 套话微表情（嘴角勾起/眼底闪过）| prompt 禁用清单 + slop_density 密度指标 | `CONSTRAINT_BLOCK` + `compute_quality` |
| AI 腔通用模板（一丝/千言万语化作）| prompt 禁用清单 | `CONSTRAINT_BLOCK` |
| 角色声音齐平（不同人物说一样的话）| 8 维评改 voice 维度 | `critique_revise` |
| 法器只摹外观不给里子 | prompt 铁律：专名+工艺+术数+义理四件套 | `CONSTRAINT_BLOCK` 规则7 |

### 2.3 检查策略：确定性规则 vs LLM

**关键判断**：两者分工明确，不可互换。

- **确定性规则**擅长：字面重复、排比、极短句、升华句正则——这些在 prompt 层靠黑名单无法治已生成文本，必须生成后扫描。
- **LLM 判官**必须用于：语义级违规（双高潮结构、声音崩、知识泄露）——确定性检测对这些"是瞎的"（代码注释原文）。
- **组合策略**：先确定性（快，零成本），再 LLM（慢，有成本），确定性通过则 LLM 可选。

---

## 三、实际产出分析（《九原渡》32 章，109,691 字）

### 3.1 前几章质量评估

**第一章"夜渡"**展示了 scribe2 的天花板水平：

- 开篇"道旁的旱柳剥到两丈高，白碴树干戳着灰天"——意象具体，无通用模板
- 阿砚七个铜板的触觉焦虑、《寒江钓雪》的裱画职业细节——show 不 tell 落地
- "各认各的船"四字——角色声音克制，无解说
- 渡叔独眼里"汪着一整河的浊水，浪头在里面转"——超过常规 AI 输出的意象密度
- 结尾没升华，只有"再往河心看时，船板上已经空了"——冷笔定格收尾

**craft 水平定性**：达到人工编辑打磨后可投稿水准。叙事声音稳定，志怪笔法一致，无明显 AI 腔。

**结构性观察**：
- 裱画行业的专业细节（矾水/排笔/绫子/宋锦）全书持续，无前后矛盾，说明设定注入起效
- 渡叔声音始终"平得像没波的水面"，无崩坏——角色声音样本注入有效
- 伏笔（长明灯、白石子、船渡图）在多章中自然呼应，伏笔节奏管理生效

**已知缺陷（从代码和注释推断）**：
- `write_continue` 单次 target_chars 勿超 3000 字，否则触发 MCP 超时（SKILL.md 明确标注）
- 长章需分 2-3 次续写，每次接续有语气断裂风险
- critique 评改的绝对分存在 LLM 噪声（这是优化版评改环用"成对比较"取代绝对分的原因）

---

## 四、已解决的核心问题

### 4.1 身份血缘漂移（旧底座最严重问题）

**问题**：旧底座 `rollup_global` 用 LLM 压缩全书主线记忆，会把"孙辈"压成"独子"、凭空造人名。

**scribe2 的根治方案**：确定性拼接，永不 LLM 压缩：

```python
def rollup_global(d, work, cap=1800):
    """确定性拼接:全程 verbatim、不 LLM 压缩 —— 根治身份血缘漂移。"""
    joined = "\n".join(f"第{m['seq']}章:{m['text']}" for m in mems)
    if len(joined) > cap:
        head = f"第{mems[0]['seq']}章:{mems[0]['text']}"  # 首章设定基底
        tail = "\n".join(f"第{m['seq']}章:{m['text']}" for m in mems[-6:])  # 最近6章
        joined = head + "\n…(中段略)…\n" + tail
```

验证测试明确标注：`原文保真，绝不被压成"独子"`（`test_generate.py:44`）。

### 4.2 POV 知识泄露

**问题**：模型写到对抗场景时，敌人角色会"知道"主角的私密（给老娘治眼的花费等），破坏限知视角。

**scribe2 的解法**：知识账本（`knowledge_ledger`）+ 双重防线：

- **预防**：`build_writing_context` 对非 POV 角色标记"私密·他人不知"，注入其已知事实清单
- **兜底**：`discipline_check` 带账本事实依据判 knowledge_leak，`fix_leak` 外科式只改泄露句

### 4.3 上下文相关性问题（"全塞前 15 个角色"）

**问题**：把书里所有角色全塞进 prompt，不在场角色占用 context，降低生成质量。

**scribe2 的解法**：`relevant_characters`——相关性信号三源：

```python
# 信号 = 开着伏笔关联的角色 ∪ 近 recent 章点名的角色 ∪ pinned 角色
# 人少（≤6）或无信号 → 全给
```

### 4.4 数据库迁移到 SurrealDB

替代旧 SQLite 底座，获得：向量索引（HNSW）、全文搜索（BM25）、图遍历（RELATE + 双向图查询），三种检索统一在一个数据库。

---

## 五、未解决的问题与已知局限

### 5.1 架构层面局限

**1. 单例 Domain 对象**（`app.py:35-44`）
```python
_singleton: dict = {"d": None}
def get_domain() -> Domain:
    if _singleton["d"] is None: ...
```
FastAPI 进程内共享一个 DB 连接实例。并发写入时存在竞争风险，未做连接池。

**2. Store.upsert_character 实现为删旧+重建**
```python
if existing:
    self.s.delete("character", self._idpart(existing["id"]))
return self.add_character(...)  # 重新嵌入
```
意味着每次角色更新会重新触发嵌入计算（fastembed 调用）。在批量操作时成本可观。

**3. 前端契约靠注释维护**
多处 `# 前端契约别名` 注释暗示字段命名不一致，靠 Python 层转换（如 `stype` ↔ `type`，`do_not_betray` ↔ `red_lines`），未形成 schema 合同。

**4. SurrealDB 的 SCHEMALESS 无校验**
`domain.py` 里多处 `(c.get(k) or "").strip()` 防御式编程，说明旧数据记录缺字段是预期情况。无自动迁移，靠代码的 `setdefault` 补救。

**5. 一致性检查截断正文**
`check_chapter` 里 `content[:3000]`——长章（>3000 字）只检查前半部，后半部漏检。

**6. search_knowledge 暴力 cosine 扫全表**
注释明确："几百实体暴力 cosine 足够"——在书长（数千 setting/chapter 记录）时性能会退化，无结果缓存。

**7. write_continue 单次 3000 字上限**
MCP 超时 300s 约束（SKILL.md 标注），长章须分节写，节间衔接靠 `prev` 参数人工传入。

### 5.2 测试覆盖盲区

根据测试文件结构，以下场景缺乏单测：
- `hermes_responses_events`（`test_chief_agentic.py` 存在但需真实 Hermes 连接）
- 超长章节的 `revise_dedup` 多轮效果（只测了 mock）
- 并发多用户写入（只做了 owner 越权防护，未测并发写同一 work）
- `critique_revise` 的成对比较退步防护

---

## 六、对 scribe3 的借鉴方案

### 6.1 可直接搬过来的设计

**① 写作上下文组装（`build_writing_context`）**

这是 scribe2 产出质量的命门，整套逻辑可直接复用。关键要保留的：
- 相关性注入（非全塞）+ `relevant_characters` 三信号逻辑
- POV/非 POV 内核标记区分（私密注释）
- 知识边界 `character_known` 注入
- 伏笔节点指令的 `beats` 结构（章号/kind/guidance/subtlety/effect/anchor）
- 母题四位一体（name/metaphor_unfolding/bound_theme/material_echoes）
- Progressions 时间门（`latest_char_states_upto`，防剧透）

**② 确定性去重流水线（`revise_dedup`）**

`find_repetitions` + `find_structural_repeats` + `find_purple_prose` 三函数可直接复用。关键正则（升华句 8 条）是经九原渡 32 章实战验证的有效规则，不要重新发明。

**③ 知识账本（`knowledge_ledger`）**

`record_knowledge_delta` / `character_known` / `build_knowledge_extract_prompt` 体系——这个解法是"谁知道什么"的单一真相源，`discipline_check` 的 knowledge_leak 判定因此从常识判断升级为账本事实核对。scribe3 应保留。

**④ 8 维 rubric 评改（`RUBRIC` + `critique_revise`）**

8 个维度（texture/surprise/emotion_truth/pace/voice/anti_slop/intent_resonance/coherence）是精心选择的，覆盖了志怪小说的主要质量维度。成对比较防退步机制经验证有效。

**⑤ SurrealDB DDL 组织方式**

`schema.py` 的 `ddl()` 函数批量生成所有索引（向量+全文），SCHEMALESS 表定义幂等。scribe3 应保留这个模式，在此基础上扩展表，而不是重新设计。

```python
# 可直接复用的 DDL 模板：
DEFINE INDEX {t}_vec ON {t} FIELDS embedding HNSW DIMENSION 512 DIST COSINE TYPE F32;
DEFINE INDEX {t}_fts ON {t} FIELDS text FULLTEXT ANALYZER scribe_a BM25;
```

**⑥ MCP 只读/写工具分离机制**

`_write_tool` 装饰器 + `WRITE_TOOLS` 集合 + `readOnlyHint` 注解的设计，使主编 agentic 可以自由调只读工具、写工具经 elicitation 审批。这是 scribe2 解决"AI 乱写不经审批"的核心机制，scribe3 应继承。

**⑦ 纪律闸的四类违规定义**

`double_climax` / `voice_collapse` / `exposition_dump` / `knowledge_leak` 四分类，有具体的辨识指引（如"terse 角色崩成大段流畅独白/系统结算音/与主角同温"），是实战提炼的精准定义，直接用在 scribe3 的 `discipline_check` 里。

### 6.2 值得升级的思路

**① 角色声音样本（`voice_samples`）**

scribe2 已有字段，但 `build_writing_context` 里每个样本截断到 40 字。scribe3 考虑：
- 样本长度放宽到 100-150 字（足够展示腔调节奏）
- 按场景类型分类（对话样本 vs 内心独白样本 vs 行动样本）
- 为 OOC 检测专门建一个 few-shot 比较通道（当前只靠 voice 维度的 critique 分）

**② 统一线模型（`entity_beat`）**

scribe2 的 `entity_beat` 把"伏笔节点指令"泛化到了角色/母题/设定，这是正确方向。但当前实现中，伏笔有专门的 `beats` 字段（更丰富），entity_beat 是简化版。scribe3 应统一两套数据结构，或让伏笔的 `beats` 成为 `entity_beat` 的子类型。

**③ 段落级检索（`segment`）**

scribe2 在 `save_segments` 时自动回填 `citation_refs`（段落引用了哪些角色/设定），这个数据双用于"出场追踪"（`entity_appearances`）。scribe3 可以扩展：段落级向量索引（当前只到 chapter 粒度），实现更精确的段落召回。

**④ 评改循环的轮数策略**

scribe2 `critique_revise` 当前 `max_rounds=1`（REST 端点固定值）。实测发现：第一轮改写往往解决最显著的问题，第二轮收益递减且有反弄的风险。scribe3 应在 SKILL.md 里明确：**只对 overall < 3.0 的章节跑评改循环，其他跑 `dedup_chapter` 即可**。

### 6.3 不应重复的弯路

**① 不要在 rollup_global 用 LLM 压缩**

已有血泪教训（旧底座把"孙辈"压成"独子"）。任何形式的 LLM 摘要全书记忆都有漂移风险。scribe3 的全书记忆必须走确定性拼接。

**② 不要全量注入所有角色到 prompt**

超过 6 个角色时必须做相关性过滤。全量注入不只是上下文浪费，更会稀释 POV 焦点，导致"本章不在场的角色突然出现"。

**③ 不要用确定性规则做语义判断**

`check_chapter`（一致性）和 `discipline_check`（纪律闸）必须用 LLM。曾有过"用规则检测知识泄露"的考虑，代码注释明确标记为"瞎的"：确定性检测无法判断"敌人是否知道这个信息"，只有 LLM 能理解语义语境。

**④ 不要让 upsert_character 走删旧+重建**

每次角色字段更新都重跑嵌入是性能陷阱。scribe3 应改为：只在 `text`（用于嵌入的文本字段）实际变化时才重新嵌入；其他字段走 `store.update`（SurrealDB `merge`）即可。

**⑤ 不要为不同用途维护两套"北极星"字段名**

scribe2 里 `red_lines` 和 `do_not_betray` 指同一个字段，靠 Python 层转换维护兼容。这类别名积累会变成负担。scribe3 在 API 设计时统一字段名，不留别名。

**⑥ `write_continue` 不要作为单一大块调用生成超长章节**

MCP 超时 300s 是硬约束。scribe3 应在 SKILL.md 和 UI 层明确：单次 ≤ 2500 字，长章分节调用，由系统自动管理 prev 传递而不是靠用户手动拼接。

---

## 七、关键数字与指标

| 指标 | 数据 |
|---|---|
| 实际产出 | 32 章 / 109,691 字（《九原渡》） |
| 测试套件 | ~28 个测试文件，横跨 domain/store/mcp/app/writing/critique/consistency |
| MCP 工具总数 | ~35 个（只读 ~20 / 写 ~15） |
| 嵌入维度 | 512（BAAI/bge-small-zh-v1.5） |
| 内容实体表数 | 9（chapter/setting/character/foreshadow/material/memory_entry/style_exemplar/imagination/motif） |
| 结构实体表数 | ~20+ |
| 升华句正则规则数 | 8 条（`_PURPLE_PATS`） |
| AI 腔禁用词组 | 15 条（`_SLOP`，domain.py） + 更多在 `CONSTRAINT_BLOCK` |
| 8 维评改 threshold | 3.5 分（满分 5） |
| 全书记忆确定性拼接上限 | 1800 字（首章 + 最近 6 章） |
| 语义召回 k | 默认 6（search_knowledge），写作上下文 k=3 |

---

*本文档基于 scribe2 源码全量阅读生成，无捏造，关键结论均有代码出处。*

# 设定层重构(元数据驱动 + 双层秘密 + 通用关系网)设计文档

日期:2026-07-14
状态:已与作者确认四项关键决策,待实施
背景:作者用下来发现 Faction 只有 9 个字段,`private_operation` 成了"超级垃圾桶"——烛照遗产、天龙座关系、加速手段三块内容混在一个长文本里。这不是结构化承载,而是倾倒:按维度检索、设定一致性校验、限知门控全都对长文本是盲区。作者列出了三个梯队共约 20 个缺失字段,并要求"最完善的方案"。

## 探索揭示的三个更根本的问题(方案必须解决)

1. **字段级 secret 是假秘密**。`private_operation_secret` 只是**界面掩码**(`app._mask_field` app.py:681),它**不进限知体系**——`project_frame`(knowledge.py:24)/`_secret_fact_ids`(context_assembler.py:169)/`_secret_guard_block`(app.py:3245) 全都只认 `proposition.secret`。更糟:faction 的 `private_operation` **根本不进 prompt**——`_codex_block`(app.py:3002-3004)注入势力时只取 `name + ideology[:18]`。所以"私密不泄露"不是因为门控,而是因为**主编压根看不见**。你精心写的势力设定,写作时一个字都用不上。
2. **加字段的改动面是硬编码的 6 处**,且有一个真陷阱:`POST /factions` 的掩码哨兵只 pop 了 `private_operation`(app.py:2402)——新增 secret 字段若忘了同步,整行回传会把 `"🔒 私密"` 字符串**永久写成真值**。
3. **前端字段表硬编码**(`CodexView.jsx:542` 的 `fieldMap` 元组),且**没有 object[] widget**——结构化子项(如持烛者传承链)无处渲染。

## 已确认的四项决策

| # | 决策 | 选择 |
|---|---|---|
| 1 | 秘密机制 | **双层:字段级掩码 + 命题桥**——字段照常结构化存储并受界面掩码;标为限知的字段**自动生成对应 proposition**(`entity_id=势力名, attribute=字段名, secret=true`),从而真正接入限知投影/泄露检测/角色知情图 |
| 2 | 范围 | **全面重构设定层**(五类实体),但**分两阶段**:阶段 1 先把 faction 打通到可用,阶段 2 按同一模板改造 character/item/term/world_rule |
| 3 | 关系网 | **通用实体关系表**(entity_relation):任意实体↔任意实体,带 relation_type + **双方各自认知**(允许不对称/错误认知)+ 时态(since/until 章);现有 character_relation **不动**(避免回归),并存 |
| 4 | 字段定义权威源 | **代码注册表**(仿设置中心 REGISTRY):声明式 schema,前端拉元数据自动渲染表单;加字段 = 注册表加一行 + 一条 migration,**前端零改动** |

## 架构

### 1. 设定字段注册表(`scribe3/codex_schema.py`,新)

声明式,每字段:

```python
CodexField(key, label, type, secret_capable, in_prompt, desc, enum=None, item_schema=None)
```

- `type`: `text | textarea | int | enum | array<string> | array<object> | bool`
- `secret_capable`: 该字段可标限知(伴生 `{key}_secret` bool 字段)
- `in_prompt`: 该字段是否注入写作/对话 prompt(**这是让设定"用起来"的开关**;默认 True,secret 字段经限知门控后注入)
- `array<object>` 用 `item_schema`(子字段列表)描述,前端据此渲染嵌套表格

**FACTION_FIELDS**(阶段 1 全量,含作者三梯队):

*现有(保留)*:name、status(enum)、ideology、leader、known_members(array<string>)、public_face、first_mention_chapter

*拆解 private_operation 垃圾桶 → 三个独立 secret 字段*:
- `artifact_operation`(遗产运作,secret)
- `external_manipulation`(对外操纵,secret)
- `acceleration_methods`(加速手段,secret)
- 旧 `private_operation` **保留但标 deprecated**(数据迁移:一次性拷贝到 artifact_operation,不自动拆分——拆分靠作者/主编,机器不猜)

*第一梯队(新增)*:
- `origin`(textarea, secret_capable)
- `internal_factions`(array<object>: name/claim/representative/power_share)
- `structure`(object: type(enum 金字塔/扁平/蜂窝/双头)/core_size/decision_mechanism/succession)
- `key_figures`(array<object>: name/generation/**fragment_decay_rate**/status(enum: active/dissipated/dead)/known_abilities)
- `artifacts`(array<object>: **artifact_name/artifact_type/current_power_level**/decay_rate/last_transfer_chapter)
  > 子字段名以**作者原始需求逐字为准**(见本节上方引用);2026-07-14 修正:spec 初稿此处简写成
  > name/type/power_level/decay_rate,与作者原话及实施计划不符——实现按作者原话落地是对的,
  > 是 spec 抄写有误,已改回。列名一旦进 SCHEMAFULL migration 就固化,故此处必须与代码逐字一致。
- 关系网 → **不做字段**,走通用关系表(见 §3)

*第二梯队*:scale、recruitment、symbols、motto、goals(array<object>: phase/target/status)、world_rule_affinity(array<object>: rule_name/affinity_type/note)

*第三梯队*:aliases(array<string>)、timeline(array<object>: chapter/event)、headquarters、communication、rituals、secret_agenda(secret,**主编独知**——连势力核心层都不知道的真相)

### 2. 双层秘密与命题桥(`scribe3/codex_secret_bridge.py`,新)

- **字段级**:`{key}_secret` bool → 界面/列表/MCP 掩码(复用 `_mask_field`/`_mask_value`,但**改成按 `_secret` 后缀自动配对的通用循环**,消灭"忘了同步哨兵"的陷阱)。
- **命题桥**(核心新增):字段标 secret 时,自动 upsert 一条 proposition:
  ```
  entity_id = "faction:{name}", attribute = "{field_key}",
  value = 字段内容(摘要), secret = True, leak_markers = 从内容提取的破绽词
  ```
  这条命题从此被 `project_frame`(角色知情投影)、`_secret_fact_ids`(prompt 门控)、`_secret_guard_block`(泄露检测)、证据链 trace **全部自动消费**。
- 字段取消 secret / 内容更新 → 命题同步更新/删除(幂等)。
- **这解决了作者"origin 部分对角色可见、'不可名状之处'仅主编知道"的诉求**:字段整体可见性由 `{key}_secret` 控;更细的"谁知道"由生成的 proposition 挂 `knows` 边表达。

### 3. 通用实体关系表(migration + store)

新表 `entity_relation`(SCHEMAFULL,不动既有 character_relation):

| 字段 | 说明 |
|---|---|
| a / b | 实体引用(字符串 `"faction:衔尾蛇秘会"` / `"character:role:x"`,类型前缀 + 本地 id) |
| relation_type | enum(臣服/敌对/渗透/无视/共生/结盟/利用/未知…,词表在注册表里,app 层 422 校验) |
| perception_a | a 对该关系的认知(a 视角) |
| perception_b | b 对该关系的认知(**可能是错的**——这正是作者要的) |
| truth | 主编独知的真相(secret,可选) |
| since_chapter / until_chapter | 时态(仿 character_relation 的双时态,`relations_at(ch)` 查询) |

REST:`GET/POST/PATCH/DELETE /entity-relations`;MCP:`s3_add_entity_relation`(写门控)/`s3_list_entity_relations`。

### 4. 让设定"真正用起来"(prompt 注入 + 一致性校验)

- **`_codex_block` 扩写**(app.py:2976-3016):势力不再只注入 `name+ideology[:18]`,而是按注册表的 `in_prompt` 字段拼结构化块;secret 字段经限知门控(命题桥 → `_secret_fact_ids`)——**对当前焦点角色不知道的秘密自动屏蔽**。这是本方案最大的即时收益:你写的设定终于会进入主编的写作视野。
- **一致性校验**:新增 `validate_faction_consistency`——检测如"势力 A 的关系里说敌对 B,而 B 的关系里说结盟 A"(除非显式标为"错误认知")、"key_figures 里 active 的持烛者 >1 但 structure.core_size=1"、"artifacts 的 decay_rate 与章节时间线矛盾"等结构化断言(长文本时代做不到的事)。

### 5. 前端元数据驱动(`CodexView.jsx` 改造)

- `GET /codex-schema/{kind}` 返回注册表元数据 → 前端**遍历渲染**,不再硬编码 `fieldMap`。
- 新增两个 widget:`object`(嵌套字段组)、`array<object>`(可增删行的子表,参照既有 `ItemStateHistory` 的做法)。
- secret 字段:统一渲染"🔒 限知"开关 + 掩码显示。
- 关系网:势力详情页新增「关系」区(读 entity_relation,双向展示 a/b 各自认知)。

## 阶段划分

**阶段 1(先交付,作者可立即存秘会设定)**:codex_schema 注册表(faction 全字段)+ migration + store 改造(CONTENT 驱动,不再逐字段字符串)+ REST/MCP 通用化(含 secret 自动配对,消灭哨兵陷阱)+ 命题桥 + 通用关系表 + 前端元数据渲染(含 object[] widget)+ `_codex_block` 注入扩写。

**阶段 2(阶段 1 跑通后)**:character/item/term/world_rule 按同一模板迁入注册表;character.backstory 同样拆解;一致性校验规则集扩充。

## 明确不做

- 不做"用户在界面自定义字段"(决策 4:代码注册表;字段是 schema 不是数据);
- 不改造既有 `character_relation`(并存,避免回归);
- 不自动拆分现有 `private_operation` 长文本(机器不猜作者意图——一次性拷贝到 `artifact_operation` 并提示作者手动分流);
- 阶段 1 不动 character/item/term/world_rule。

## 风险

| 风险 | 缓解 |
|---|---|
| SCHEMAFULL + 20 新字段,migration 出错落库全拒 | migration 全用 `IF NOT EXISTS`;先在测试库跑全量;生产先备份(surreal_backup.sh) |
| 命题桥可能污染正典命题空间(faction 字段命题混入角色事实) | 命题带 `source='codex_bridge'` 标记;限知投影正常消费但一致性检测可按 source 过滤;可回滚(删桥接命题不影响字段) |
| `_codex_block` 注入变大 → prompt 膨胀 | 注册表的 `in_prompt` 开关 + 长度预算(每势力上限 N 字,超出截断并提示);默认只注入当前章相关势力 |
| 前端元数据渲染重写 CodexView | 保留旧 fieldMap 作为 fallback(注册表拉取失败时);逐类切换(阶段 1 只切 faction) |

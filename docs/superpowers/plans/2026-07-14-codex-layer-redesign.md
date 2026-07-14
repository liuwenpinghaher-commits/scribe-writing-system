# 设定层重构 · 阶段1(faction 全链)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** faction 从 9 字段长文本倒垃圾,升级为注册表驱动的 ~25 字段结构化实体;secret 字段经命题桥真正接入限知;通用实体关系表落地;设定终于进 prompt 被主编用起来。

**Architecture:** `codex_schema.py` 声明式注册表 → migration/store/REST/MCP/前端全部由它驱动;`codex_secret_bridge.py` 把 secret 字段同步成 `proposition(secret=true)`;新 `entity_relation` 表承载任意实体间双向关系(含各自认知与主编独知 truth);`_codex_block` 按注册表注入 prompt 并经限知门控。spec:`docs/superpowers/specs/2026-07-14-codex-layer-redesign.md`。

**Tech Stack:** SurrealDB(SCHEMAFULL,migration 必写)+ FastAPI + FastMCP + React。后端测试 `scribe3/.venv/bin/python -m pytest`,前端 `cd scribe3/web && npx vitest run`。

**红线(每个任务都适用):**
- 测试只用 conftest 的临时内存 SurrealDB;**绝不碰生产库**(~/.scribe2-surreal/data.db,含《印迹》15 条世界规则+6 势力、《纸命》等)。
- migration 一律 `IF NOT EXISTS` / `OVERWRITE`,幂等可重放。
- 新写路由必须登记 `test_consistency.KNOWN_REST_WRITE_ROUTES`;新 MCP 写工具必须进 `mcp.WRITE_GATED`。
- 中文 commit + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`;不 push;前台跑测(不用后台+Monitor)。

---

### Task 1:设定字段注册表 `codex_schema.py`

**Files:** Create `scribe3/codex_schema.py`;Test `scribe3/tests/test_codex_schema.py`

- [ ] Step 1 失败测试:

```python
# 断言语义:
# ① FACTION_FIELDS 含 spec 列出的全部字段(name/status/ideology/leader/known_members/public_face/
#    first_mention_chapter/artifact_operation/external_manipulation/acceleration_methods/origin/
#    internal_factions/structure/key_figures/artifacts/scale/recruitment/symbols/motto/goals/
#    world_rule_affinity/aliases/timeline/headquarters/communication/rituals/secret_agenda
#    + deprecated 的 private_operation)
# ② 每个 secret_capable 字段都有伴生 bool 键 f"{key}_secret"(由 secret_flag_key() 派生,不手写)
# ③ schema_for('faction') 返回可 JSON 序列化的元数据(前端要吃):key/label/type/secret_capable/
#    in_prompt/desc/enum/item_schema 齐全
# ④ array<object> 字段(internal_factions/key_figures/artifacts/goals/world_rule_affinity/timeline)
#    的 item_schema 非空且每个子字段有 key/label/type
# ⑤ enum 字段(status/structure.type/key_figures[].status)的 enum 列表非空
# ⑥ deprecated 字段标记为 deprecated=True 且 in_prompt=False(不进 prompt,不进新建表单)
```

- [ ] Step 2 跑红
- [ ] Step 3 实现:`CodexField` dataclass(key/label/type/secret_capable=False/in_prompt=True/desc=''/enum=None/item_schema=None/deprecated=False);`FACTION_FIELDS` 全量(字段清单严格照 spec §1);`secret_flag_key(key) -> f"{key}_secret"`;`schema_for(kind) -> list[dict]`(JSON 化,供 REST 下发);`secret_capable_keys(kind)`;`prompt_keys(kind)`
- [ ] Step 4 跑绿
- [ ] Step 5 Commit `feat: 设定字段注册表(faction 全字段声明式 schema)`

### Task 2:migration + store 改造(CONTENT 驱动)

**Files:** Create `scribe3/migrations/0NN_faction_expand.surql`(NN 取现有最大+1);Modify `scribe3/store.py`;Test `scribe3/tests/test_codex_faction.py`

- [ ] Step 1 失败测试:

```python
# ① add_faction(name="X", origin="...", key_figures=[{...}], structure={...}) → list_factions() 回读一致
# ② 部分更新语义:再 add_faction(name="X", motto="Y") → 其余字段不丢(现状是 DELETE+CREATE 整行覆盖,
#    必须保住"未传字段不动"的既有 PATCH 语义——app 层原来靠 pick() 回填,现在 store 层直接支持 merge)
# ③ secret 伴生字段:add_faction(origin="秘密", origin_secret=True) → 回读 origin_secret is True
# ④ array<object> 字段落库/回读保真(嵌套 dict 不被压平)
# ⑤ 旧数据兼容:只有 9 个老字段的行,list_factions() 不崩、新字段为 None/[]
# ⑥ private_operation 迁移:migration 把老行的 private_operation 拷进 artifact_operation(幂等,只在
#    artifact_operation 为空时拷)
```

- [ ] Step 2 跑红
- [ ] Step 3 实现:
  - migration:逐字段 `DEFINE FIELD IF NOT EXISTS ... ON faction`(类型按注册表:text→string、array<string>→`array<string> DEFAULT []`、array<object>→`option<array>`、object→`option<object>`、bool→`bool DEFAULT false`);enum 字段加 ASSERT;数据迁移 UPDATE 拷 private_operation→artifact_operation(仅当后者为空)
  - `store.add_faction` 重写为 **kwargs/CONTENT 驱动**:按注册表白名单过滤入参 → `UPSERT faction:{name} MERGE $content`(MERGE 保住"未传字段不动");删掉逐字段字符串拼接
  - `list_factions()` 不变(裸 SELECT);新增 `get_faction(name)`
- [ ] Step 4 跑绿 + `pytest scribe3/tests/test_codex_faction.py scribe3/tests/test_batch2.py -q`(既有 faction 测试不回归;grep 找出所有测过 add_faction 的文件一并跑)
- [ ] Step 5 Commit `feat: faction 表扩字段 + store CONTENT 驱动(MERGE 保未传字段)`

### Task 3:REST/MCP 通用化(secret 自动配对,消灭哨兵陷阱)

**Files:** Modify `scribe3/app.py`、`scribe3/mcp.py`、`scribe3/tests/test_consistency.py`;Test `scribe3/tests/test_codex_faction.py`(追加 API 层)

- [ ] Step 1 失败测试:

```python
# ① GET /factions:所有 secret_capable 字段在 {key}_secret=True 时都被掩码为 "🔒 私密"
#    (不只 private_operation;逐字段断言 origin/artifact_operation/external_manipulation/
#     acceleration_methods/secret_agenda)
# ② 【关键·防数据毁灭】POST /factions 整行回传含掩码值 "🔒 私密" 的任意 secret 字段 → 该字段不被覆盖
#    (真值仍在库里);当前实现只防了 private_operation,新字段必然踩坑 → 这条测试先红
# ③ GET /codex-schema/faction → 返回注册表元数据(前端用)
# ④ POST /factions 校验:enum 字段传非法值 → 422
# ⑤ MCP s3_list_factions 同样按 _secret 后缀自动掩码(不硬编码字段名)
# ⑥ s3_add_faction 支持新字段(关键字实参,不是位置实参)
```

- [ ] Step 2 跑红(②必须红——这是现存陷阱的实证)
- [ ] Step 3 实现:
  - `FactionIn` 改为按注册表生成/校验(或手写全字段但字段清单从 codex_schema 取,避免两处漂移)
  - `GET /factions`:`for k in secret_capable_keys('faction'): _mask_field(row, k, secret_flag_key(k), reveal)`——通用循环
  - `POST /factions`:掩码哨兵通用循环 `for k in secret_capable_keys(...): if sent.get(k) == _SECRET_MASK: sent.pop(k)`;enum 校验
  - `GET /codex-schema/{kind}`(只读)
  - `mcp.s3_list_factions` 同款通用掩码;`s3_add_faction` 改关键字实参 + 新字段(仍在 WRITE_GATED)
  - 台账:`POST /factions` 已登记;新增端点若有写路由同步登记
- [ ] Step 4 跑绿 + `pytest scribe3/tests/test_codex_faction.py scribe3/tests/test_consistency.py scribe3/tests/test_mcp.py -q`
- [ ] Step 5 Commit `feat: faction REST/MCP 按注册表通用化(secret 自动配对,堵掩码回写陷阱)`

### Task 4:命题桥(字段级 secret → 真限知)

**Files:** Create `scribe3/codex_secret_bridge.py`;Modify `scribe3/app.py`(POST /factions 后调桥);Test `scribe3/tests/test_codex_secret_bridge.py`

- [ ] Step 1 失败测试:

```python
# ① 写 faction 带 origin_secret=True → 自动 upsert proposition:
#    entity_id 含势力名、attribute='origin'、secret=True、source='codex_bridge'
# ② 该命题被既有限知链消费:context_assembler._secret_fact_ids 能查到它(即真进了限知门控)
# ③ 幂等:重复写同内容 → 命题不重复(同 entity+attribute upsert)
# ④ 内容更新 → 命题 value 同步更新
# ⑤ 取消 secret(origin_secret=False)→ 桥接命题被删除(不再限知)
# ⑥ 字段清空 → 命题删除
# ⑦ 非 secret 字段不生成命题(不污染命题空间)
# ⑧ 桥接命题带 source='codex_bridge' 标记(可与作者手写命题区分/过滤)
```

- [ ] Step 2 跑红
- [ ] Step 3 实现 `sync_faction_secrets(store, name, row)`:遍历 secret_capable 字段 → 有值且 flag=True 则 upsert 命题(entity_id=f"faction:{name}", attribute=key, value=内容摘要, secret=True, source='codex_bridge');否则删除对应桥接命题。POST /factions 落库后调用(fail-soft:桥接失败只告警不阻断写入)
- [ ] Step 4 跑绿 + 限知回归 `pytest scribe3/tests/test_codex_secret_bridge.py scribe3/tests/test_knowledge.py scribe3/tests/test_context_assembler.py -q`(文件名以实际为准)
- [ ] Step 5 Commit `feat: 命题桥——faction secret 字段真正接入限知体系`

### Task 5:通用实体关系表

**Files:** Create migration `0NN_entity_relation.surql`;Modify `scribe3/store.py`、`scribe3/app.py`、`scribe3/mcp.py`、`scribe3/tests/test_consistency.py`;Test `scribe3/tests/test_entity_relation.py`

- [ ] Step 1 失败测试:

```python
# ① add_entity_relation(a="faction:秘会", b="faction:天龙座", relation_type="臣服",
#      perception_a="虚与委蛇,视为台阶", perception_b="视其为地球代理人", truth="秘会实为寄生",
#      since_chapter=1) → 回读一致(双方认知可不对称,truth 独立)
# ② relations_at(chapter) 时态过滤(until_chapter 之后不返回)
# ③ end_relation(a,b,until_chapter) 关边
# ④ 任意实体类型:faction↔character、character↔item 都能存(通用,不锁类型)
# ⑤ relation_type 非法值 → store/app 层拒(422)
# ⑥ truth 字段受 secret 掩码(GET 默认掩,reveal_secret=True 才见)
# ⑦ 既有 character_relation 不受影响(回归)
# ⑧ REST: GET/POST/DELETE /entity-relations;MCP: s3_add_entity_relation(WRITE_GATED)/s3_list_entity_relations
```

- [ ] Step 2 跑红
- [ ] Step 3 实现:migration(SCHEMAFULL:a/b string、relation_type string ASSERT 词表、perception_a/b/truth option<string>、truth_secret bool DEFAULT true、since/until option<int>);store add/list/relations_at/end;REST 三端点 + 台账登记;MCP 两工具(写工具进 WRITE_GATED)
- [ ] Step 4 跑绿 + `pytest scribe3/tests/test_entity_relation.py scribe3/tests/test_consistency.py -q` + character_relation 既有测试回归
- [ ] Step 5 Commit `feat: 通用实体关系表(双向认知+主编独知 truth+时态)`

### Task 6:prompt 注入 + 一致性校验(让设定用起来)

**Files:** Modify `scribe3/app.py`(`_codex_block`);Create 校验函数(store.py 或 critique.py,按仓内归属);Test `scribe3/tests/test_codex_prompt.py`

- [ ] Step 1 失败测试:

```python
# ① _codex_block 注入势力时,按注册表 in_prompt=True 的字段拼结构化块(不再只有 name+ideology[:18])
# ② secret 字段经限知门控:焦点角色不知道的桥接命题对应字段 → 不注入(用 project_frame/_secret_fact_ids)
# ③ 长度预算:单势力注入超上限时截断(不炸 prompt)
# ④ 关系网注入:该势力的 entity_relation 摘要进块(perception_a 视角;truth 永不注入)
# ⑤ 一致性校验 validate_faction_consistency:
#    - A 关系表说敌对 B,B 说结盟 A(且未标为错误认知)→ 报冲突
#    - key_figures 里 status=active 的人数 > structure.core_size → 报冲突
#    - artifacts 的 last_transfer_chapter > 当前最大章 → 报冲突
```

- [ ] Step 2 跑红
- [ ] Step 3 实现(注意:secret 门控必须真走既有限知链,不要另写一套)
- [ ] Step 4 跑绿 + `pytest scribe3/tests/test_codex_prompt.py scribe3/tests/test_prompt_assembly.py -q`
- [ ] Step 5 Commit `feat: 设定进 prompt(注册表驱动+限知门控)+ faction 一致性校验`

### Task 7:前端元数据渲染 + 关系区

**Files:** Modify `scribe3/web/src/api.js`、`scribe3/web/src/views/CodexView.jsx`、`scribe3/web/src/CodexDetail.jsx`;Test `scribe3/web/src/__tests__/codexView-schema.test.jsx`

- [ ] Step 1 失败测试:

```jsx
// ① CodexView 拉 /codex-schema/faction → 按元数据渲染表单(不再读硬编码 fieldMap)
// ② array<object> 字段(key_figures)渲染可增删行的子表,每行按 item_schema 渲染子字段
// ③ object 字段(structure)渲染嵌套字段组
// ④ secret_capable 字段渲染「🔒 限知」开关;开启时值显示掩码
// ⑤ 元数据拉取失败 → fallback 到旧 fieldMap(不白屏)
// ⑥ 势力详情页「关系」区:列出 entity_relation(双方认知并排;truth 不显示除非 reveal)
```

- [ ] Step 2 跑红
- [ ] Step 3 实现(保留旧 fieldMap 作 fallback;只切 faction,其余四类仍走旧路径)
- [ ] Step 4 跑绿 + 全量 `npx vitest run`
- [ ] Step 5 Commit `feat: 设定库元数据驱动渲染(object[]/嵌套 widget)+ 势力关系区`

### Task 8:回归 + 真机验收 + 文档

- [ ] Step 1 后端全量 pytest 绿;前端全量 vitest 绿
- [ ] Step 2 **生产库备份**(`bash scribe3/surreal_backup.sh` 或等价;报告备份路径)→ 重启后端加载新代码 → 确认《印迹》既有 6 势力数据完好(migration 未毁数据,private_operation 已拷进 artifact_operation)
- [ ] Step 3 真机(控制器亲自):在《印迹》里给「衔尾蛇秘会」填入 origin/key_figures/artifacts/internal_factions(经界面 or API)→ 标 origin_secret → 验证:①设定库正常显示嵌套子表 ②GET /factions 掩码 ③桥接命题生成(查 proposition) ④主编写作 prompt 里出现结构化势力块(查 /post-check 或直接看 _codex_block 输出)⑤加一条秘会↔天龙座关系(双方认知不同)→ 关系区正确显示;截图
- [ ] Step 4 更新 `docs/superpowers/2026-07-13-实际使用问题台账.md`(若本次修复涉及)+ 汇报(改了什么/验证结果/阶段2 待办)

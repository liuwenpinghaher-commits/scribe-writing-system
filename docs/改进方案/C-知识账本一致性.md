# C · 知识账本一致性

> 枢纽 C(短期阶段,部分依赖 B 图枢纽)。聚合 **P07 / P18 / P13 / P33 / P04 / P44**。
> 对象:**scribe3** 后台 ingest 管线(定稿正文 → 抽知识 delta → 回写账本)与限知投影。
> 引用诊断:[03-问题诊断与整改方案.md](../系统架构/03-问题诊断与整改方案.md)。所有 `文件:行号` 已在 2026-06-24 只读核对。
> 红线:严格 TDD;所有写经 `_execute_write`;限知 load-bearing 测试不破;既有 `test_ingest` learned/did 测试不回归。本文是**方案文档,不真改代码**。

---

## 1. 概述

### 1.1 本枢纽聚合的问题

| 编号 | 一句话 | 严重度 | 诊断锚点 |
|---|---|---|---|
| **P07** | ingest 重复触发 + fact-id UPSERT 覆盖,KnowledgeEdge 悬挂旧 fid | 🔴 高 | `ingest.py:29,38`、`store.py:151-156`、`gen3.py:72`、`app.py:587` |
| **P18** | `_ensure_char` 对 `seen_by` 任意名凭空建角色 + 发知识边(幻觉污染) | 中 | `ingest.py:13-18,40-42` |
| **P13** | `find_leaks` 异常吞成 `leaks=0`(假绿) | 中 | `app.py:581-586` |
| **P33** | 渲染"事件块"列全部 participants,不经 focalizer 帧过滤 | 中 | `render.py:59-66` |
| **P04** | `knowledge` 是 `@property`,每次访问跑 2 条全表查询(N+1) | 🔴 高 | `store.py:429-441`、消费方 `store.py:411`、`knowledge.py:32` |
| **P44** | learned/did 属性名写死 "新知"/"所为",语义丢失 | 低 | `ingest.py:30,39` |

### 1.2 目标(四个不变量)

1. **ingest 幂等**:同一章被 ingest 任意多次,账本状态收敛到"最后一次抽取结果",不残留孤儿命题、不留悬挂知识边。去掉 `gen3.py` 的第二次触发。
2. **幻觉校验**:LLM 抽出的 `seen_by`/`who` 若指向库中不存在的角色,**不静默建实体发边**;入"待确认"通道,可见、可人工接纳。
3. **去吞错**:泄露检测失败回 `leaks=null` + `error`,把"未检测"与"检测通过=0"在 API 契约上区分开。
4. **投影正确**:事件块参与者按 focalizer 帧过滤(限知不破);`knowledge` 从 `@property` 改显式方法 + 单次投影内缓存,消除每次访问重复全扫。

---

## 2. 背景与动机

### 2.1 账本是限知的命脉

scribe3 的限知范式核心是 `project_frame`(`knowledge.py:24-37`):渲染前按 focalizer 投影出"他截至本章知道的事实集",**只把这个帧喂给生成**——帧外的私密物理上进不了 prompt(`render.py:42-57`,`test_render_feeds_frame_limited_prompt`、`test_app.py:40` 守护)。这套"结构性防泄露"成立的前提是:**`knows` 边(知识账本)如实反映"谁知道什么"**。

账本的唯一自动维护通道是 ingest:定稿正文 → Hermes 抽 `{learned, did, voice_shift}` delta(`critique.py:170-189`)→ `apply_delta` 落 `knows` 边(`ingest.py:21-48`)。闭环是 `render → 存 → ingest → 世界知识态更新 → 下章限知渲染反映新知`(`ingest.py:1-6` docstring)。

**一旦账本漂移,限知就"基于错误的已知"运作**:
- 账本**多**了不该有的边(P18 幻觉角色)→ 投影把不存在的"知道"塞进帧 → 渲染据错误前提写。
- 账本**少/错**了边(P07 覆盖后 KnowledgeEdge 悬挂到被改写的 fid)→ 角色"知道一条已被改写的事实",或边指向不存在的命题 → 帧投影结果与作者意图脱节。

### 2.2 为何这些是一件事:静默漂移、症状滞后难查

这六个问题不是孤立 bug,而是**同一条"账本保真链"上的连续裂口**:

```
抽取(LLM)→ 校验(无)→ 落库(覆盖)→ 投影(N+1/不过滤)→ 检测(吞错)
   P44          P18         P07         P04/P33        P13
```

- **抽取端**(P44)丢语义:所有 learned 砸进 attribute="新知",did 砸进 "所为",`facts_at` 投影回来全是同名属性,主体的知识结构被压平。
- **校验端**(P18)缺失:幻觉角色直接进库,`characters()` 被污染,还会被 `grant_public`(`store.py:182-184`)波及(给"所有角色"发边时把幻觉角色也算上)。
- **落库端**(P07)覆盖:确定性 fact-id `fact:k{seq}-{i}` 把"第 i 条 learned"绑死到序号,二次抽取条目数/顺序一变,旧命题被 UPSERT 改写,而上一轮发出的 `knows` 边仍指向那个 fid → **悬挂/语义漂移**。
- **投影端**(P04 性能、P33 正确性):`knowledge` 每访问全扫两遍(`dramatic_irony` 一次调用触发两遍投影 = 知识边扫 4 次);事件块绕过帧过滤直列 participants,是限知的一个**未触发但敞着的缺口**。
- **检测端**(P13)吞错:最后一道兜底 `find_leaks` 失败时静默回 0,**把"没检测"伪装成"检测通过"**。

**滞后难查**正是危害所在:账本漂移不会立即报错——它在第 N 章悄悄写错一条边,直到第 N+k 章某角色"说出他视角不可能知道的信息"(knowledge_leak),或纪律判官(`critique.py:139`)抓到泄露时才爆发,此时根因已埋在十几章前的某次 ingest 里。诊断 §9 把"ingest 一致性"列为 **ROI 第 2 高**正是此理:"知识账本是限知的命脉,账本漂移会让限知基于错误的已知而失真,且症状滞后难查"。

### 2.3 与既有资产的关系

- 既有 `test_apply_delta_idempotent`(`test_app.py:175-181`)**只**守护"同内容二次回写不抛 AlreadyExists / 只一条命题"——这是 `add_fact` 从 CREATE 改 UPSERT 的产物(observation 3055)。它**不**覆盖 P07 的真问题:**二次抽取条目数/顺序变化时的覆盖与悬挂边**。本枢纽补的正是这个缺口。
- 既有 `test_did_witnesses_know` / `test_non_witness_does_not_know`(`test_ingest.py:15-23`)是 load-bearing 的限知守护,**必须继续绿**。本枢纽对 `seen_by` 的幻觉校验要在"角色已存在"路径上保持这两个测试通过。
- P33 的彻底修复**依赖 B 图枢纽**:`events_at`(`store.py:422-427`)当前不读 participants(P03/B 待补)。在 B 落地前,C 先以"显式断言 + 防御过滤"止血(见 §3.4)。

---

## 3. 详细设计

> 约定:所有写仍只经 `SurrealStore._execute_write`(`store.py:121-123`,不变量1)。下列伪码省略 `from __future__ import annotations` 等样板。surql 标注「需人工确认」者,表示该语法/字段需在真库 `surreal sql` 验证后才落迁移。

### 3.1 P07 · ingest 幂等(章级幂等键 + 去双触发)

**根因**:① 确定性 fact-id 把命题身份绑死到"第几条 + 第几章",二次抽取的条目集与首次不一致时,UPSERT 覆盖旧命题但旧 `knows` 边悬挂。② `/save-chapter` 已 `background.add_task(_bg_ingest)`(`app.py:587`),`gen3.py:72` 又显式 `POST /ingest`,同章 ingest 跑两遍。

**修法 A:章级"先清后写"(选定方案)。** ingest 一章前,先删除该章产出的所有命题与知识边(用稳定的"产出归属"标记定位),再重新落本次抽取结果。这样无论二次抽取条目如何变化,账本始终等于"最后一次抽取",绝无悬挂边。

需要一个**产出归属字段**把"本章 ingest 产出"标出来。给 `proposition` 与 `knows` 各加一个 `ingest_seq`(可空 int,标识"由第几章 ingest 产生";作者直编/种子数据为 NONE,不受清理影响):

```surql
-- 迁移 010_ingest_provenance.surql(需人工确认字段语法在 SurrealDB 3.1.5 通过)
DEFINE FIELD IF NOT EXISTS ingest_seq ON proposition TYPE option<int>;  -- 由第几章 ingest 产出;NONE=非ingest(作者直编/种子)
DEFINE FIELD IF NOT EXISTS ingest_seq ON knows       TYPE option<int>;
-- 清理热路径:按 ingest_seq 反查,补索引(与 E 枢纽协同)
DEFINE INDEX IF NOT EXISTS idx_prop_ingest  ON proposition FIELDS ingest_seq;
DEFINE INDEX IF NOT EXISTS idx_knows_ingest ON knows       FIELDS ingest_seq;
```

`apply_delta` 改为先清后写,并给写入打 `ingest_seq`:

```python
def apply_delta(store, delta: dict, seq: int) -> int:
    """把知识 delta 落到 store。章级幂等:先清本章既有 ingest 产出,再重写。
    返回应用条数。重复调用同章 → 账本收敛到最后一次抽取,无悬挂边。"""
    store.purge_ingest(seq)          # 先清:删 ingest_seq=seq 的命题 + knows 边
    n = 0
    for i, it in enumerate(delta.get("learned") or []):
        who, fact = it.get("who"), it.get("fact")
        if not who or not fact:
            continue
        oid = _resolve_char(store, who)          # P18:不存在则入待确认,返回 None
        if oid is None:
            continue
        fid = f"fact:k{seq}-{i}"
        store.add_fact(Fact(fid, oid, _attr_learned(fact), fact, valid_from=seq), ingest_seq=seq)  # P44 属性名
        store.add_knowledge(KnowledgeEdge(oid, fid, since_chapter=seq, acquired_via="learned"),
                            ingest_seq=seq)
        n += 1
    # did 同理:_resolve_char + ingest_seq=seq;seen_by 见 §3.2
    ...
    return n
```

`SurrealStore` 新增 `purge_ingest`(仍经 `_execute_write`,作为本枢纽唯一新增删路径):

```python
def purge_ingest(self, seq: int) -> None:
    """删除某章 ingest 产出的命题 + knows 边(幂等再 ingest 的前置清理)。
    只清 ingest_seq=seq,作者直编/种子(ingest_seq=NONE)不动。"""
    # 先删指向这些命题的 knows 边,再删命题,避免悬挂(SurrealDB RELATION 不自动级联)
    self._execute_write("DELETE knows WHERE ingest_seq = $seq", {"seq": seq})
    self._execute_write("DELETE proposition WHERE ingest_seq = $seq", {"seq": seq})
```

> **为何选"先清后写"而非"已 ingest 标记跳过":** 跳过方案(第二次直接 return)在"作者改了正文重新定稿"时**不会更新账本**——而正文已变,账本就该跟着重抽。先清后写让账本始终对齐最新正文,语义更正确。代价是每次 ingest 多两条 DELETE(已加索引,O(本章产出数))。

`add_fact` / `add_knowledge` 增加可选 `ingest_seq` 形参(默认 None,**不破坏**既有调用方与 `test_apply_delta_idempotent` 的 CREATE→UPSERT 行为):

```python
def add_fact(self, f: Fact, ingest_seq: int | None = None) -> Fact:
    _, local = _split(f.id)
    self._execute_write(
        "UPSERT type::record('proposition', $local) SET entity=$entity, attribute=$attr, "
        "value=$value, valid_from=$vf, valid_to=$vt, secret=$secret, leak_markers=$lm, "
        "ingest_seq=$iseq",
        {"local": local, "entity": f.entity_id, "attr": f.attribute, "value": f.value,
         "vf": f.valid_from, "vt": f.valid_to, "secret": f.secret, "lm": f.leak_markers,
         "iseq": ingest_seq})
    return f
```

**去双触发**:删 `gen3.py:71-76` 的显式 `POST /ingest`(`save-chapter` 的 `_bg_ingest` 已覆盖),保留 `/ingest` REST 端点本身(`app.py:594-598`,供手动重抽/调试)。`gen3.py` 改为依赖 `save-chapter` 返回的 `ingesting=True` 即可,不再自己调 ingest。

> **可选增强(本枢纽不强制,标记关联 B/G)**:`purge_ingest` + 两条 add 跨多语句,理想上应包 SurrealDB 事务(`BEGIN/COMMIT`)以防中途失败留半套——但事务体系是 G 枢纽 P06 的范围。C 阶段以"先清后写顺序 + 失败结构化日志"止血,事务化留 G。

### 3.2 P18 · 幻觉角色不入库(seen_by 须已存在,否则入待确认)

**根因**:`_ensure_char`(`ingest.py:13-18`)对任意名字"不存在就建"。LLM 把正文里一个路人称呼、或抽错的名字当成 `seen_by`,就会凭空 `add_entity` + 发 `knows` 边,污染 `characters()`,且被 `grant_public` 波及。

**修法**:把"保证存在(建)"改为"解析(不建)"。已存在 → 返回 oid;不存在 → **不建实体、不发边**,改为写入"待确认"队列(`ingest_unverified`),供作者在前端 Codex/质量面板里"接纳为新角色"或"忽略"。

```python
def _resolve_char(store, name: str, seq: int, role: str) -> str | None:
    """解析角色 oid:已存在返回 oid;不存在则登记待确认,返回 None(不建实体、不发边)。
    role: 'learned_who' / 'did_who' / 'seen_by',供待确认条目说明来源。"""
    oid = f"role:{name}"
    if store.entity(oid) is not None:
        return oid
    store.add_unverified_ref(name, seq, role)   # 待确认,不污染 characters()
    return None
```

`learned.who` / `did.who` / `seen_by[*]` 全部走 `_resolve_char`;返回 None 即跳过该条边(`did.who` 解析失败则整条 did 跳过——没有合法行为人就没有命题)。

```python
# did 分支(节选)
actor = _resolve_char(store, who, seq, "did_who")
if actor is None:
    continue
fid = f"fact:d{seq}-{j}"
store.add_fact(Fact(fid, actor, _attr_did(action), action, valid_from=seq), ingest_seq=seq)
for w in [who] + list(it.get("seen_by") or []):
    woid = _resolve_char(store, w, seq, "seen_by")
    if woid is None:
        continue                                 # 幻觉旁观者不发边
    store.add_knowledge(KnowledgeEdge(woid, fid, since_chapter=seq, acquired_via="saw"),
                        ingest_seq=seq)
```

待确认表(SCHEMAFULL,小表):

```surql
-- 迁移 011_ingest_unverified.surql(需人工确认)
DEFINE TABLE IF NOT EXISTS ingest_unverified SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name   ON ingest_unverified TYPE string ASSERT string::len($value) > 0;
DEFINE FIELD IF NOT EXISTS seq    ON ingest_unverified TYPE int;      -- 哪章抽到
DEFINE FIELD IF NOT EXISTS role   ON ingest_unverified TYPE string;   -- learned_who/did_who/seen_by
DEFINE FIELD IF NOT EXISTS status ON ingest_unverified TYPE string DEFAULT 'pending';  -- pending/accepted/ignored
DEFINE FIELD IF NOT EXISTS created ON ingest_unverified TYPE datetime VALUE time::now() READONLY;
```

```python
def add_unverified_ref(self, name: str, seq: int, role: str) -> None:
    self._execute_write(
        "CREATE ingest_unverified SET name=$n, seq=$s, role=$r, status='pending'",
        {"n": name, "s": seq, "r": role})

def list_unverified(self, status: str = "pending") -> list[dict]:
    return self._query("SELECT meta::id(id) AS id, name, seq, role, status "
                       "FROM ingest_unverified WHERE status=$st", {"st": status})
```

可选 REST(供前端面板;非本枢纽必需,标关联 H):`GET /unverified?work=` 列待确认;作者"接纳"时再走既有 `POST /characters` 建角色 + 重 ingest 该章(先清后写会带出新边)。

> **保留 `_ensure_char` 的去向**:`learned`/`did` 的当事人 `who` 在叙事里通常是已立角色;但若严格起见也走 `_resolve_char`,则需保证 scenario 种子(`scenario.py` 的 `luanshi_leak_world`)先建好角色,`test_ingest` 的 `store` fixture 用例里 "焦三/阿萤/老道" 是否已预建——**需人工确认** `test_ingest.py` 各用例是否依赖 `_ensure_char` 自动建"焦三"。若依赖,则这些测试要改为先 `add_entity` 再 `apply_delta`(见 §4 任务 T2 的迁移说明)。

### 3.3 P13 · find_leaks 失败回 null + error(去吞错)

**根因**:`app.py:581-586` 把 `find_leaks` 的任何异常 `except: leaks = 0`,前端/调用方收到 `leaks=0` 无法区分"检测通过"与"检测崩了"。

**修法**:`leaks` 语义改为"检测到的泄露数,**检测失败时为 null**",并在响应里带 `leak_error`。`null` 与 `0` 在 JSON 契约上严格区分。

```python
@app.post("/save-chapter")
def save_chapter(req: SaveChapterReq, background: BackgroundTasks, work: str = "main"):
    st = _store_for(work)
    st.save_chapter(req.seq, req.prose, title=req.title, focalizer=req.focalizer)
    from scribe3.critique import quality_flags
    qf = quality_flags(req.prose)
    leaks, leak_error = None, None
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            leaks = len(find_leaks(req.prose, st, req.focalizer, req.seq))
        except Exception as e:
            import logging
            logging.getLogger("scribe3").exception("find_leaks 失败 work=%s seq=%s", work, req.seq)
            leak_error = str(e)[:160]            # 失败可见,不再伪装成 0
    background.add_task(_bg_ingest, work, req.seq)
    return {"status": "saved", "seq": req.seq,
            "qc": {"repetition": len(qf["repetition"]), "structural": len(qf["structural"]),
                   "purple": len(qf["purple"])},
            "leaks": leaks, "leak_error": leak_error, "ingesting": True}
```

> **契约变更影响**:`leaks` 默认值从 `0` 变 `null`(无 focalizer 时也是 null,因为"无视角"本就无从检测)。`gen3.py:79` 打印 `sc.get('leaks',0)` 与 `test_save_chapter_runs_softcheck`(`test_app.py:169`,只断言 `"leaks" in r`)不破。前端若有 `leaks === 0` 的绿灯判断,需改 `leaks === 0`(真通过)vs `leaks == null`(未检测)——标关联 H。

### 3.4 P33 · 事件块参与者按帧过滤(限知门控补强)

**根因**:`render.py:59-66` 渲染"本章要发生的事件"块时,直列 `ev.participants.values()` 的全部参与者名,**不经 focalizer 帧过滤**。若某事件含视角角色不该知道的隐藏参与者,其名会进 prompt——当前 scenario 未触发,但这是限知的一个敞口。

**修法(分两层,与 B 协同)**:

**C 阶段(立即,不依赖 B):防御性过滤 + 显式断言。** 事件参与者名进 prompt 前,先确认"该参与者对 focalizer 可感知"。可感知判据:participant 是 focalizer 本人,或 focalizer 帧内存在以该 participant 为 entity 的命题(即 focalizer 知道这人在场)。不可感知的参与者从事件块剔除,并打 debug 日志。

```python
def _events_block(world, story_at, focalizer, frame) -> list[str]:
    """事件块:participants 按 focalizer 帧过滤,帧外参与者不进 prompt(限知)。"""
    frame_entities = {f.entity_id for f in frame.facts} | {focalizer}
    lines = []
    for ev in _events_at(world, story_at):
        visible = [v for v in ev.participants.values()
                   if v in frame_entities]               # 仅 focalizer 可感知的参与者
        parts = "、".join((world.entity(v).name if world.entity(v) else v) for v in visible)
        where = ...
        lines.append(f"- [{ev.type}] {parts}" + (f" 于{where}" if where else ""))
    return lines
```

> **注意当前事件块的现实**:`SurrealStore.events_at`(`store.py:422-427`)**当前不返回 participants**(只 etype/valid_from/goal),`Event` 默认 `participants={}`。所以真库路径下事件块此刻就是空参与者——P33 在真库**当前不可触发**,但在内存 `World`(`test_render`)路径可触发,且 B 枢纽给 `events_at` 补 participants 后真库也会触发。因此本过滤是**为 B 落地后预置的强制门控**,同时让内存路径立即正确。**需人工确认**:B 落地时 `events_at` 返回的 participants 结构(dict 槽位)与此处 `.values()` 一致。

**B 落地后(彻底)**:事件块直接吃真库 `see_event` 语义——`witnesses_of`(`knowledge.py:48-50`)已定义"在场者=participants 值集",过滤判据可统一到"focalizer ∈ witnesses 或 focalizer 知道该 witness 在场"。届时把上面的 `frame_entities` 判据收敛到 `knowledge.py` 的单一函数,render 与 ingest 共用。

**load-bearing 守护**:新增断言式测试"事件块不含 focalizer 帧外参与者名"(见 §4 T4),与既有 `test_render_feeds_frame_limited_prompt`(`test_app.py:40`,守"治眼"不进 prompt)互补——后者守事实块,前者守事件块。

### 3.5 P04 · knowledge 改显式方法 + 投影内缓存(去 N+1)

**根因**:`store.knowledge` 是 `@property`(`store.py:429-441`),每次属性访问跑 2 条全表查询(`knows` 全扫 + `reader_knows` 全扫)。消费方:`graph()`(`store.py:411` 遍历 `self.knowledge`)、`project_frame`(`knowledge.py:32` 遍历 `world.knowledge`)。`dramatic_irony`(`knowledge.py:43-45`)调 `project_frame` 两次 = 知识边全扫 **4 遍**。`@property` 的语法把"这是一次昂贵 DB 调用"伪装成廉价字段访问。

**修法**:
1. 新增显式方法 `load_knowledge() -> list[KnowledgeEdge]`(语义同当前 property 主体),**保留** `knowledge` property 作薄封装委托(向后兼容 `graph()` 与既有测试,**不破** `World` 鸭子接口——`World` 仍可有同名 property)。
2. 在**单次投影作用域内缓存**一份知识边快照,避免 `dramatic_irony` 重复全扫。缓存粒度是"一次投影请求",不是进程级(避免与 live 写产生陈旧读)。

```python
def load_knowledge(self) -> list[KnowledgeEdge]:
    """显式拉全部知识边(knows + reader_knows)。昂贵:2 条查询。调用方应在投影作用域内缓存。"""
    rows = self._query("SELECT meta::tb(in) AS itb, ... FROM knows")  # 同现 property 主体
    edges = [...]
    rr = self._query("SELECT proposition, since_chapter FROM reader_knows")
    edges += [...]
    return edges

@property
def knowledge(self) -> list[KnowledgeEdge]:
    """向后兼容薄封装(委托 load_knowledge)。新代码用 load_knowledge + 显式缓存。"""
    return self.load_knowledge()
```

投影侧引入显式缓存。最小侵入做法:`project_frame` 接受可选 `edges` 形参,`dramatic_irony` 拉一次喂两遍:

```python
def project_frame(world, knower_id, chapter, edges=None) -> KnowledgeFrame:
    facts_now = world.facts_at(chapter)
    if knower_id == "world":
        return KnowledgeFrame("world", chapter, list(facts_now))
    if edges is None:
        edges = world.load_knowledge() if hasattr(world, "load_knowledge") else world.knowledge
    known_ids = {k.proposition_id for k in edges
                 if k.knower_id == knower_id and k.polarity
                 and k.since_chapter <= chapter
                 and (k.until_chapter is None or k.until_chapter > chapter)}
    return KnowledgeFrame(knower_id, chapter, [f for f in facts_now if f.id in known_ids])

def dramatic_irony(world, focalizer, chapter):
    edges = world.load_knowledge() if hasattr(world, "load_knowledge") else world.knowledge
    reader = project_frame(world, "reader", chapter, edges=edges)     # 一次拉,两遍用
    foc_ids = {f.id for f in project_frame(world, focalizer, chapter, edges=edges).facts}
    return [f for f in reader.facts if f.id not in foc_ids]
```

> **行为等价性**:`edges=None` 时回退到拉一次(与现状语义等价,只是不再每访问全扫)。`World`(内存)的 `knowledge` 是普通 list,`load_knowledge` 可直接 `return self.knowledge`——鸭子兼容不破。配合 E 枢纽给 `knows FIELDS in, since_chapter` 加索引,单次投影也能走索引而非全扫。**需人工确认**:`World`(`ontology.py`)是否需补 `load_knowledge`,或仅靠 `hasattr` 回退到 `.knowledge` 即可(后者零改动)。

### 3.6 P44 · learned/did 属性名带语义

**根因**:`ingest.py:30,39` 写死 `"新知"`/`"所为"`。`facts_at` 投回来所有 ingest 命题 attribute 全同名,主体知识结构被压平,`_editor_system`(`app.py:323`)按 `attribute:value` 列设定时也全是"新知:…"。

**修法(轻量,不引入分类器)**:从 fact 文本派生一个**更具区分度的短属性名**,而非固定串。保守起步:learned 用 `"获知"`,did 用 `"行动"`(比"新知/所为"更贴 knows 语义且不丢信息);若要进一步带语义,可取 fact 短句的主题词作 attribute(留 D 枢纽词汇表统一后再做,避免在混乱命名上加规则)。

```python
def _attr_learned(fact: str) -> str:
    return "获知"     # P44 起步:稳定但比"新知"更贴语义;主题词提取留 D 枢纽

def _attr_did(action: str) -> str:
    return "行动"
```

> **为何不在 C 阶段做"主题词提取":** attribute 的真正规范化(枚举/词汇表)是 D 枢纽地基。C 阶段在混乱命名上加启发式提取会与 D 返工。C 只做"去塌缩、保稳定"的最小改名,把彻底语义化交给 D。**这是 C 与 D 的边界,需在排期上对齐**(总纲 §4 已列 D 为 C 的上游地基)。

---

## 4. TDD 实施计划

> 每个任务:**先写失败测试 → 跑红 → 实现 → 跑绿 → 全量回归**。回归基线:`scribe3/.venv/bin/python -m pytest scribe3/tests`(当前全绿,observation 3158)。限知 load-bearing 测试(`test_render_feeds_frame_limited_prompt`、`test_non_witness_does_not_know`、`test_frame_excludes_others_secret`)每步都须保持绿。**不 commit**(本文是方案;落地时按红线"当前 main 分支,绝不 `-A`")。

### T0 · 基线锁定(无改动)
- 跑全量 `pytest scribe3/tests`,记录绿基线与 `test_ingest`/`test_app` 用例数。确认 `test_apply_delta_idempotent`、`test_did_witnesses_know`、`test_non_witness_does_not_know` 现状绿。
- **验收**:基线全绿,记录数字。

### T1 · P07 章级幂等(先清后写)
1. **红**:写 `test_ingest_overwrite_no_dangling`——
   ```python
   def test_reingest_changed_extraction_no_dangling(store):
       store.add_entity(Entity("role:甲", "character", "甲"))
       apply_delta(store, {"learned":[{"who":"甲","fact":"A"},{"who":"甲","fact":"B"}],"did":[]}, seq=5)
       # 二次抽取条目变少/换序
       apply_delta(store, {"learned":[{"who":"甲","fact":"C"}],"did":[]}, seq=5)
       facts = [f for f in store.facts_at(5) if f.attribute in ("获知","行动")]
       assert {f.value for f in facts} == {"C"}              # 旧 A/B 已清,无残留
       # 且无 knows 边指向已不存在的 fact:k5-0(旧A)/k5-1(旧B)
       edges = store.load_knowledge()
       live_fids = {f.id for f in store.facts_at(5)}
       assert all(e.proposition_id in live_fids for e in edges if e.since_chapter==5)
   ```
   先跑应红(当前 UPSERT 覆盖 k5-0 但 k5-1 残留,旧边悬挂)。
2. **实现**:加迁移 010(`ingest_seq` 字段 + 索引);`add_fact`/`add_knowledge` 加 `ingest_seq` 形参;新增 `purge_ingest`;`apply_delta` 开头调 `purge_ingest(seq)`。
3. **绿 + 回归**:T1 测试绿;`test_apply_delta_idempotent`、`test_learned_makes_knower_know`、`test_did_witnesses_know`、`test_non_witness_does_not_know` 仍绿。
4. **去双触发**:删 `gen3.py:71-76` 显式 `/ingest` 调用(`gen3` 非测试覆盖,人工核 `save-chapter` 的 `_bg_ingest` 仍触发回写)。

### T2 · P18 幻觉角色不入库
1. **红**:
   ```python
   def test_hallucinated_seen_by_not_persisted(store):
       store.add_entity(Entity("role:焦三", "character", "焦三"))
       apply_delta(store, {"learned":[],"did":[{"who":"焦三","action":"取丹","seen_by":["路人甲"]}]}, seq=2)
       assert not any(e.name=="路人甲" for e in store.characters())   # 幻觉角色未入库
       assert any(u["name"]=="路人甲" and u["role"]=="seen_by" for u in store.list_unverified())  # 入待确认
       assert any("丹" in f.value for f in project_frame(store,"role:焦三",2).facts)  # 当事人仍知道
   ```
2. **实现**:加迁移 011(`ingest_unverified`);`add_unverified_ref`/`list_unverified`;`_ensure_char`→`_resolve_char`(不存在则登记返 None);`apply_delta` 各分支改用 `_resolve_char`。
3. **绿 + 回归**:`test_non_witness_does_not_know`、`test_did_witnesses_know` 仍绿。
   - **需人工确认并修**:若 `test_ingest.py` 用例依赖 `_ensure_char` 自动建"焦三/阿萤/老道"(用例当前直接 `apply_delta` 未先建角色),则这些用例须改为先 `store.add_entity(...)` 再 `apply_delta`——这是**测试迁移**(语义没变:让"已存在"前提显式化),不算回归破坏。先核 `store` fixture(`conftest.py`)是否预置角色。

### T3 · P13 find_leaks 去吞错
1. **红**:
   ```python
   def test_find_leaks_failure_returns_null(store, monkeypatch):
       import scribe3.verify as V
       monkeypatch.setattr(V, "find_leaks", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
       r = _client(store).post("/save-chapter", json={"seq":1,"prose":"x","focalizer":"role:x"}).json()
       assert r["leaks"] is None and r["leak_error"]      # 失败可见,非伪装成 0
   def test_find_leaks_zero_means_clean(store):
       r = _client(store).post("/save-chapter", json={"seq":1,"prose":"干净正文","focalizer":"role:焦三"}).json()
       assert r["leaks"] == 0 and r["leak_error"] is None # 真通过=0,与 null 区分
   ```
2. **实现**:`save_chapter` 端点按 §3.3 改(`leaks=None` 初值 + 捕获回 `leak_error` + `logging.exception`)。
3. **绿 + 回归**:`test_save_chapter_runs_softcheck`(`test_app.py:169`)仍绿(只断言 `"leaks" in r`)。

### T4 · P33 事件块帧过滤
1. **红**(走内存 `World`,因真库 `events_at` 当前无 participants):
   ```python
   def test_event_block_excludes_unperceivable_participant():
       # 构造:事件含 focalizer 帧外的隐藏参与者,断言其名不进 prompt
       w = World(); ...  # 焦三可感知"甲";"隐者乙"是 focalizer 不知道在场的参与者
       prompt = build_render_prompt(w, chapter=1, focalizer="role:焦三")
       assert "隐者乙" not in prompt and "甲" in prompt
   ```
2. **实现**:抽 `_events_block`(§3.4),participants 按 `frame.facts` 的 entity 集 + focalizer 过滤。
3. **绿 + 回归**:`test_render_feeds_frame_limited_prompt`(事实块)仍绿;`test_render` 全套绿。
   - **需人工确认**:B 落地后 `events_at` 返回 participants 时,同测试在真库路径也应绿——T4 测试用内存 World 即可锁住语义,B 落地补真库用例。

### T5 · P04 knowledge 显式方法 + 缓存
1. **红/计数测试**:
   ```python
   def test_dramatic_irony_single_knowledge_load(store, monkeypatch):
       luanshi_leak_world(store)
       calls = {"n": 0}
       orig = store.load_knowledge
       monkeypatch.setattr(store, "load_knowledge", lambda: (calls.__setitem__("n", calls["n"]+1), orig())[1])
       dramatic_irony(store, "role:老道", 1)
       assert calls["n"] == 1     # 一次拉,两遍投影复用(去 N+1)
   ```
2. **实现**:加 `load_knowledge`;`knowledge` property 委托;`project_frame`/`dramatic_irony` 加 `edges` 形参。
3. **绿 + 回归**:`test_graph_endpoint`(`test_app.py:60`)、`test_irony`、`test_frame_excludes_others_secret` 全绿(行为等价)。

### T6 · P44 属性名去塌缩
1. **红**:
   ```python
   def test_learned_attribute_not_collapsed(store):
       store.add_entity(Entity("role:甲","character","甲"))
       apply_delta(store, {"learned":[{"who":"甲","fact":"X真相"}],"did":[]}, seq=1)
       f = next(f for f in store.facts_at(1) if f.value=="X真相")
       assert f.attribute == "获知" and f.attribute != "新知"
   ```
2. **实现**:`_attr_learned`/`_attr_did`;`apply_delta` 用之。
3. **绿 + 回归**:`test_learned_makes_knower_know`(断言 value 含"追索者",不依赖 attribute 名)仍绿。

### T7 · 全枢纽回归 + 限知守护汇总
- 跑全量 `pytest scribe3/tests`,确认 T0 基线用例 + T1-T6 新增用例全绿。
- 专项复跑三条 load-bearing:`test_render_feeds_frame_limited_prompt`、`test_non_witness_does_not_know`、`test_frame_excludes_others_secret`。
- 人工核 `gen3.py` 改后逻辑(无自动化覆盖),确认不再双触发。

---

## 5. 验收标准

| # | 验收项 | 度量方式 | 对应问题 |
|---|---|---|---|
| AC1 | **重复 ingest 不漂移** | 同章二次 ingest(条目变更)后,账本=最后一次抽取;无 `knows` 边指向已删命题 | P07 |
| AC2 | **去双触发** | `gen3.py` 不再显式调 `/ingest`;`save-chapter` 单触发回写 | P07 |
| AC3 | **幻觉角色被拦** | LLM 抽出的库外 `seen_by`/`who` 不入 `characters()`,进 `ingest_unverified(pending)` | P18 |
| AC4 | **泄露失败可见** | `find_leaks` 抛异常时响应 `leaks=null` + `leak_error` 非空;真通过时 `leaks=0` + `leak_error=null` | P13 |
| AC5 | **事件块限知不破** | 事件块不出现 focalizer 帧外参与者名;`test_render_feeds_frame_limited_prompt` 等三条 load-bearing 全绿 | P33 |
| AC6 | **knowledge 不重复全扫** | `dramatic_irony` 一次调用只触发 1 次 `load_knowledge`;`knowledge` property 行为等价不破既有测试 | P04 |
| AC7 | **属性名不塌缩** | learned/did 命题 attribute 不再是固定 "新知"/"所为";既有依赖 value 的测试不破 | P44 |
| AC8 | **既有 ingest 测试不回归** | `test_ingest`(learned/did/voice_flag/end_to_end)+ `test_apply_delta_idempotent` 全绿 | 红线 |

---

## 6. 风险与依赖

### 6.1 依赖

- **B 图枢纽(部分,P33 彻底修复的上游)**:`events_at`(`store.py:422-427`)当前不返回 participants;P33 在真库路径**当前不可触发**。C 阶段先以内存 World 路径锁住过滤语义(T4),B 给 `events_at` 补 participants 后真库才完整生效。**B 落地时需确认 participants 结构与 `_events_block` 的 `.values()` 假设一致。**
- **D 本体规范化(上游地基,P44 彻底语义化的上游)**:attribute 的枚举/词汇表统一在 D。C 只做"去塌缩、保稳定"的最小改名,主题词提取/枚举约束留 D,避免在混乱命名上加规则后返工。排期上 D 应先于或并行 C(总纲 §4 已列)。
- **E 性能与索引(协同)**:`purge_ingest` 的 `DELETE ... WHERE ingest_seq` 与 `project_frame` 的 `knows` 全扫,都依赖索引才不退化为全表扫。C 自带 010 的 `ingest_seq` 索引;`knows FIELDS in, since_chapter` 索引在 E。
- **G 可靠性(协同,非阻塞)**:`purge_ingest` + 两条 add 的事务化(P06)留 G;C 以"先清后写顺序 + 失败结构化日志"止血。

### 6.2 回归风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| **既有 ingest 测试依赖 `_ensure_char` 自动建角色** | `test_ingest.py` 用例可能直接 `apply_delta` 未先建"焦三/阿萤"——改 `_resolve_char` 后这些名字入待确认、当事人边不发,测试转红 | T2 标注:先核 fixture/用例是否预建;若依赖则做**测试迁移**(显式 `add_entity` 前置),语义不变 |
| **`leaks` 契约从 0 变 null** | 前端若有 `leaks===0` 绿灯判断会误判 | §3.3 标关联 H;`gen3.py`/`test_save_chapter_runs_softcheck` 用 `get('leaks',0)`/`in` 不破 |
| **`attribute` 改名影响投影展示** | `_editor_system` 按 `attribute:value` 列设定,改名后显示文案变 | 仅文案变,不影响逻辑;无测试断言固定 "新知" |
| **`knowledge` property 改委托** | `graph()` 与 `World` 鸭子接口依赖该 property | 保留 property 作薄封装,`load_knowledge` 新增不删旧;`hasattr` 回退保 World 兼容 |
| **迁移 010/011 在真库 apply** | `ingest_seq`/`ingest_unverified` 语法须在 SurrealDB 3.1.5 验证 | 标「需人工确认」;`test_migrate` 加这两迁移的 apply 用例 |
| **大量回归面** | ingest 改动牵投影/渲染/save-chapter 多处 | T7 全量回归 + 三条 load-bearing 专项复跑 |

### 6.3 需人工确认清单(本文未能从代码独证)

1. `test_ingest.py` 各用例是否依赖 `_ensure_char` 自动建"焦三/阿萤/老道"(决定 T2 是否需测试迁移)。
2. 迁移 010/011 的字段/表语法在 SurrealDB 3.1.5 真库 apply 通过(`ingest_seq`、`ingest_unverified`、两条索引)。
3. B 落地后 `events_at` 返回的 participants 结构(dict 槽位)与 `_events_block` 的 `.values()` 过滤假设一致。
4. `World`(`ontology.py`)是否需补 `load_knowledge`,或仅靠 `hasattr` 回退到 `.knowledge`(后者零改动,倾向后者)。
5. 前端是否存在 `leaks === 0` 的绿灯判断(决定 H 是否需同步改前端契约)。

---

## 7. 闭环问题清单(对账)

| 问题 | 主归属 | 本枢纽处置 | 设计节 | 测试 | 验收 |
|---|---|---|---|---|---|
| **P04** ✓ | C | knowledge 改 `load_knowledge` 显式方法 + 投影内缓存,去 N+1 | §3.5 | T5 | AC6 |
| **P07** ✓ | C | 章级幂等键(`ingest_seq` + 先清后写)+ 去 `gen3` 双触发 | §3.1 | T1 | AC1/AC2 |
| **P13** ✓ | C | `find_leaks` 失败回 `leaks=null` + `leak_error`,去吞错 | §3.3 | T3 | AC4 |
| **P18** ✓ | C | `seen_by`/`who` 须已存在才发边,否则入 `ingest_unverified` | §3.2 | T2 | AC3 |
| **P33** ✓ | C(B 协同) | 事件块参与者按 focalizer 帧过滤(C 内存止血 + B 真库彻底) | §3.4 | T4 | AC5 |
| **P44** ✓ | C(D 上游) | learned/did 属性名去塌缩("获知"/"行动";彻底语义化留 D) | §3.6 | T6 | AC7 |

**对账**:本枢纽认领的 6 个问题(P04/P07/P13/P18/P33/P44)全部有设计节 + TDD 任务 + 验收项,无遗漏。与总纲 §3 映射表一致。

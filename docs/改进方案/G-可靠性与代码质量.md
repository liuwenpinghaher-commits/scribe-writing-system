# G · 可靠性与代码质量

> 枢纽 G(独立枢纽,无强前置依赖)。聚合 **16 项**:P15 / P16 / P06 / P27 / P31 / P17 / P19 / P20 / P21 / P23 / P34 / P42 / P43 / P39 / P40 / P41。
> 对象:**scribe3**(`<repo-root>`)Python 后端 + React 前端。
> 引用诊断:[03-问题诊断与整改方案.md](../系统架构/03-问题诊断与整改方案.md) §3/§4/§6/§7。所有 `文件:行号` 已在 2026-06-24 只读核对(逐条见 §7 闭环清单)。
> 红线:严格 TDD;所有写经 `_execute_write`;限知 load-bearing 测试不破;全量回归(142 个测试函数)绿。本文是**方案文档,不真改代码**。

---

## 1. 概述

### 1.1 本枢纽聚合的 16 个问题(四组)

这是诊断中**问题最多的枢纽**。按"修法形态"分四组,而非按严重度——因为它们的改动手法、风险面、TDD 策略各自同构。

**A 组 · 可靠性(5 项)**——失败路径无兜底,长篇高强度跑会偶发崩:

| 编号 | 一句话 | 严重度 | 诊断锚点 |
|---|---|---|---|
| **P15** | 流式 LLM(对话/写作/agentic 主路径)无重试,瞬时抖动即整条断 | 中 | `llm.py:57-78`(stream)、`llm.py:81-104`(responses)对比 `llm.py:40-54`(非流式有重试) |
| **P16** | soak 无降级、无独立超时,浸泡一失败整章渲染连带挂 | 中 | `render.py:108-110`、`soak.py:40-42` |
| **P06** | `_execute_write` 无事务,`grant_public`/migrate 等多步写半套即漂移 | 🔴 高 | `store.py:121-123`、多步写 `store.py:182-184`、`migrate.py:110-128` |
| **P27** | `/live` 每请求 9 条 WS 订阅,长连接累积无上限 | 中 | `app.py:611-619`、`live.py`(订阅表数=9) |
| **P31** | `_store_for` 连接缓存永不释放,长跑连接泄漏 | 中 | `app.py:41-46`(`_stores` dict 只增不汰) |

**B 组 · 错误处理(1 项,牵一发)**——保留 fail-open,但去"静默":

| 编号 | 一句话 | 严重度 | 诊断锚点 |
|---|---|---|---|
| **P17** | 多处 `except` 静默吞错,叠加失败时根因被吞、无从察觉 | 中 | `critique.py:151-152`、`critique.py:188-189`、`soak.py:35-37`、`app.py:585-586`、`store.py:108-112`、`migrate.py:127-128` |

**C 组 · 代码质量 / DRY(6 项)**——可维护性税:

| 编号 | 一句话 | 严重度 | 诊断锚点 |
|---|---|---|---|
| **P19** | `build_render_prompt` 59 行、6 段顺序耦合 + 嵌套 entity 解析 | 中 | `render.py:31-89` |
| **P20** | `/chat/write` GET/POST ~90 行近乎整段复制 | 中 | `app.py:414-460`(GET)、`app.py:470-523`(POST) |
| **P21** | `World.facts_at` 与 `SurrealStore.facts_at` 语义已漂移(`tx_to` 条件) | 中 | `ontology.py:114-118` vs `store.py:209-213` |
| **P23** | works 注册表绕过 `_execute_write`,破"单一写点"不变量 | 中 | `store.py:60-95`(`create/delete/rename_work`)、不变量 `store.py:6,121` |
| **P34** | 确定性 QC 误报:排比取 `s[:3]`、破折号阈值不归一化 | 中 | `critique.py:39`、`critique.py:81-82` |
| **P42** | 魔法值:`graph` 的 9999、`_editor_system` 的 99999、模型名散写 | 低 | `store.py:406`、`app.py:321`、`llm.py:31,58` |
| **P43** | 升华正则三处维护、`grant_public` 两处实现 | 低 | `critique.py:49-58` / `store.py:307-311` / `ontology.py:97-102`、`store.py:182-184` |

> P42 与 P43 同属"单一来源"问题,合并为 C 组一个工作项处理(§3.9)。

**D 组 · 死代码(3 项)**——删除,不是重构:

| 编号 | 一句话 | 严重度 | 诊断锚点 | 核对结论 |
|---|---|---|---|---|
| **P39** | `PALETTE`(90 行)——诊断称"全仓无引用" | 低 | `craft.py:55-144` | ⚠ **诊断不准**:`mcp.py:141-144` 实际引用(`s3_emotion_palette` 工具)。**不可删**,详见 §3.10 |
| **P40** | `views/ChatView.jsx` 整文件死代码(未挂载) | 低 | `web/src/views/ChatView.jsx` | ✅ 确认死:`App.jsx:1-44` 未 import,全仓仅自引用 |
| **P41** | `@tanstack/react-table` 已装未用 | 低 | `web/package.json:11` | ✅ 确认未用:`src/` 零 `tanstack`/`react-table` 引用 |

### 1.2 目标(六个验收不变量)

1. **流式有重试**:`hermes_complete_stream` / `hermes_responses_events` 对瞬时错(连接/超时/5xx)重试,与非流式 `hermes_complete` 的重试语义一致(4xx 不重试)。
2. **soak 可降级**:soak 失败时**仍出正文**——回退到"无浸泡渲染",且 soak 有独立(短于主渲染的)超时,不被 600s 主超时拖住。
3. **关键多步写有事务**:`grant_public`、migrate 写入等"多条 surql 才完整"的操作包 SurrealDB 事务,要么全成要么全不落。
4. **失败有结构化日志**:所有 `except` 分支保留 fail-open 行为,但**必须**结构化记录(谁失败、原始返回/异常),失败可观测。
5. **死代码清零(经核对)**:确认死的(ChatView.jsx、react-table)删除并全量回归绿;诊断误报的(PALETTE)保留并修正诊断措辞。
6. **重复代码消除**:`build_render_prompt` 拆分、`_stream_write` 抽公共、升华正则与 `grant_public` 单一来源、`facts_at` 双实现对拍一致——且**所有 load-bearing 限知测试不破**。

### 1.3 为何这 16 项归一枢纽

它们共享同一性质:**都是"非功能性"债务**——不改变 scribe3 能写什么,只改变它"写得有多稳、改得有多痛"。诊断 §9 给系统打 6/10,明言"架构骨相很正",扣分集中在可靠性/一致性/可维护。本枢纽正是把这条扣分线一次性补齐。且其内部有一条逻辑主线(§2):**B 组去静默吞错是 A/C/D 三组的可观测性前提**——先点灯,再修路。

---

## 2. 背景与动机

### 2.1 引诊断:这是"集体缺失"的那条线

诊断 §9 技术债评估把 scribe3 的扣分归为四条线"集体缺失":安全、性能、**一致性(无事务/双实现漂移)**、生产化。本枢纽承接其中"**一致性**"与"**可维护**"两条的代码侧,以及"可靠性"小类(P15/P16)。诊断对本枢纽各项的定性:

- P15/P16(§4 健壮性):"流式 LLM 无重试"、"soak 无降级无独立超时"——**写作鲁棒性 / 渲染鲁棒性**。
- P06(§2 架构):"共享单连接 + `_execute_write` 无事务 + 并发竞态","记忆中'第1章 ingest 因 duplicate record 失败'即此路径"。
- P17(§6 代码质量,标注"牵一发"):"**叠加效应**:LLM 返畸形 JSON 时'纪律放行 + 知识不回写 + 浸泡失效'同时静默发生,根因被吞掉无从察觉"。
- P19/P20/P21/P23/P34/P42/P43(§6/§7):DRY 与可维护性税。
- P39/P40/P41(§6,诊断明确归类):"**这不是'投入',直接删除即可,别当重构任务规划**"。

### 2.2 核心论点:去静默吞错(P17)是可观测性前提,高 ROI

诊断 §9 把"消除静默吞错 + 结构化日志"列为 **ROI 第 3 高**,理由一针见血:"**可观测性是发现其他一切问题的前提。当前多处失败无声,等于'蒙眼开车';点亮它,前两项的效果才可验证**"。

把这条放进本枢纽的语境,它的杠杆更直接——**本枢纽其余 15 项的失败,当前全部会被静默吞错掩盖**:

```
       现状(蒙眼)                          去吞错后(点灯)
─────────────────────────────────   ─────────────────────────────────
P15 流式抖动 → 静默断流,前端只见      → 日志记下"stream 第 k 次重试/最终失败 + 上游状态"
              半截或空白
P16 soak 抛错 → render 整条异常,        → 日志记下"soak 失败,降级无浸泡",正文照出
              用户只见 500
P17 parse_*  → 返空 dict,纪律放行/      → 日志记下"parse_discipline 失败 + 原始 reply 前 N 字"
              知识不回写,无声
P06 事务半套 → duplicate record,只在     → 事务失败显式抛 + 日志,不留半套
              偶发崩溃时才暴露
```

**当前的静默吞错点(逐一,均已核对)**:

| 位置 | 现状 | 危害 |
|---|---|---|
| `critique.py:151-152` `parse_discipline` | `except: return {"ok": True, ...}` | 畸形 JSON → **纪律判官放行**(默认 ok=True),泄露/双高潮漏检 |
| `critique.py:188-189` `parse_knowledge_delta` | `except: return {"learned": [], ...}` | 畸形 JSON → **知识不回写**,账本停止演进(连锁诊断 C 枢纽) |
| `soak.py:35-37` `parse_soak` | `except: pass → 返空` | 浸泡失效,情感设计丢失,无声降级 |
| `app.py:585-586` `find_leaks` | `except: leaks = 0` | **假绿**:把"未检测"伪装成"检测通过=0"(诊断 P13,C 枢纽主修;此处去吞错同步) |
| `store.py:108-112` `close()` | `except: pass` | 连接关闭失败被吞(与 P31 连接泄漏叠加) |
| `migrate.py:127-128` 加知识边 | `except: pass` | 角色实体缺失致边悬空,静默 |
| `app.py:64-67` `works()` 取 stats | `except: {chapter_count:0,...}` | 某书 store 起不来 → 卡片显示 0,不报错 |
| `llm.py:25-26` `_api_key` 读 env 文件 | `except: pass` | key 读取失败 → 回退 "local",鉴权静默错 |

> **设计取舍**:保留 fail-open(诊断 §6 明确"保留 fail-open 行为但**必须**结构化日志")。理由:scribe3 是单用户写作工具,渲染/对话中途因一个解析错误整条 500 比"降级但出活"更伤体验。所以**不是把吞错改成抛错,而是把"无声吞"改成"有声吞"**——失败仍不阻断,但留下可观测的轨迹。

### 2.3 为何可靠性(A 组)对长篇是真问题,不是过度工程

诊断对 scribe3 的定位是"已验证能写长篇的单用户本地工具"。长篇 = **数百章 × 每章多次 LLM 调用**(soak 1 次 + 渲染 1 次 + ingest 1 次 + 可能的纪律/重生)。在这个调用量级下:

- **P15**:Hermes 网关 → doubao 的瞬时抖动(`ReadTimeout`/`RemoteProtocolError`/5xx)是统计必然。非流式路径(`hermes_complete`)早已有 3 次重试(`llm.py:41-54`,docstring 自述"已验证的 600s 超时 + 3 次重试"),但**对话/写作/agentic 这三条用户最高频的主路径走的是流式**,反而裸奔——这是**不对称的可靠性**(observation 3183 已记此为"asymmetric error handling between streaming and non-streaming paths")。
- **P16**:soak 是渲染的**前置增强**,不是主体。它失败时正确行为是"少一道情感设计,但正文照出",而非"整章渲染失败"。当前 `render.py:108-110` 让 soak 异常直接冒泡穿透整个 `render()`。
- **P06**:`grant_public`(`store.py:182-184`)对每个角色发一条边,是**循环多步写**;migrate(`migrate.py:110-128`)是几十条连续写。无事务 + 共享单连接(`app.py:27`),并发 REST + 后台 `_bg_ingest`(`app.py:587`)同时写,半套数据是真实风险(诊断点名"第1章 ingest 因 duplicate record 失败")。

### 2.4 与既有资产的关系(不破什么)

- **限知 load-bearing 测试(render 层)**:`test_craft_does_not_break_limited_pov`(`test_render.py:66`)、`test_voice_does_not_break_pov`(`test_render.py:82`)、`test_flashback_does_not_break_pov`(`test_render.py:134`)、`test_render_prompt_cannot_contain_others_secret`(`test_render.py:10`)。P19 拆 `build_render_prompt` **必须**让这四个继续绿——它们正是守护"拆分后帧外私密仍进不了 prompt"的护栏。
- **限知 load-bearing 测试(ontology 层)**:`test_focalizer_frame_excludes_others_secret`(`test_ontology.py:38`)、`test_world_frame_is_ground_truth`(`test_ontology.py:60`)。P21 改 `facts_at` 双实现一致性**必须**让这两个继续绿。
- **真库范式测试**:`test_persisted_paradigm_holds`(`test_store.py:36`)、`test_fact_roundtrip_and_secret`(`test_store.py:18`)。P06 给 `_execute_write` 包事务、P21 对拍 `facts_at` 不能让这些回归。
- **既有 `_execute_write` 单一写点**:P06 事务化必须**在 `_execute_write` 内部或其上**实现,不得新开绕过它的写路径(否则同时违反 P23 要守护的不变量)。
- **既有"两路写作"模糊性**:observation 3181 记 `/chat/write` GET/POST 是"deterministic but two-path ambiguity"。P20 抽 `_stream_write` 正是消解此模糊——但**不改变对外行为**(GET/POST 端点签名、SSE 事件格式不变)。

---

## 3. 详细设计

> 说明:以下所有代码块是**目标形态示意**,用于界定改动边界与测试锚点;实际实现以 §4 TDD 计划逐步驱动产出。

### 3.1 〔A·P15〕流式 LLM 重试——把非流式的重试语义搬到流式

**现状**:`hermes_complete`(非流式)已有正确的重试骨架(`llm.py:41-54`):

```python
for _ in range(3):
    try:
        r = httpx.post(...); r.raise_for_status()
        return r.json()[...]
    except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError) as e:
        last = e; continue
    except httpx.HTTPStatusError as e:
        last = e
        if e.response is not None and e.response.status_code < 500:
            raise            # 4xx 不重试
        continue
raise last if last else RuntimeError(...)
```

`hermes_complete_stream`(`llm.py:57-78`)和 `hermes_responses_events`(`llm.py:81-104`)**完全没有**这层。

**修法**:流式重试的难点是"已经 yield 出去的 delta 不能重发"。因此重试**只覆盖"建立连接 + 首字节到达前"的失败**——一旦开始正常 yield,中途断流按失败上抛(交由调用方的 SSE error 事件回流)。抽一个公共重试包装器:

```python
# llm.py —— 新增公共重试常量与流式重试包装
_RETRYABLE = (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError)
_MAX_RETRIES = 3   # 与 hermes_complete 对齐(P42:常量化,见 §3.9)

def _stream_with_retry(make_stream, max_retries: int = _MAX_RETRIES):
    """对'打开流 + 取到首个 yield 前'的瞬时错重试;已 yield 后不重试(避免重发 delta)。
    make_stream: () -> 生成器(每次调用新建一条 httpx.stream 并 yield delta)。"""
    import logging
    log = logging.getLogger("scribe3.llm")
    last = None
    for attempt in range(max_retries):
        started = False
        try:
            for piece in make_stream():
                started = True
                yield piece
            return
        except _RETRYABLE as e:
            last = e
            if started:
                log.warning("流式中途断(已输出 %d 次,不重试): %s", attempt, e)
                raise
            log.warning("流式建链瞬时错,重试 %d/%d: %s", attempt + 1, max_retries, e)
            continue
        except httpx.HTTPStatusError as e:
            last = e
            if started or (e.response is not None and e.response.status_code < 500):
                raise            # 已开始 or 4xx：不重试
            log.warning("流式 5xx,重试 %d/%d: %s", attempt + 1, max_retries, e)
            continue
    raise last if last else RuntimeError("stream failed")
```

`hermes_complete_stream` 与 `hermes_responses_events` 各自把"打开 `httpx.stream` 并逐行 yield"的部分包进 `make_stream` 闭包,外面套 `_stream_with_retry`。**对调用方零改动**(仍是 yield delta / yield event 的生成器)。

> 关键 TDD 锚点:用 monkeypatch 让 `make_stream` 前 2 次抛 `ConnectError`、第 3 次正常 yield,断言最终拿到完整输出且重试了 2 次(见 §4 T1)。

### 3.2 〔A·P16〕soak 降级 + 独立超时

**现状**:`render.py:108-110`:

```python
soak_result = None
if soak:
    from scribe3.soak import soak as run_soak
    soak_result = run_soak(world, frame_at, focalizer, complete_fn)   # 抛错则穿透整个 render
```

`soak()`(`soak.py:40-42`)调 `complete_fn` 无独立超时(沿用主渲染的 600s)。

**修法**:soak 是增强非主体,失败降级为"无浸泡渲染";并给它独立的、更短的超时。

```python
# render.py —— soak 降级
soak_result = None
if soak:
    import logging
    from scribe3.soak import soak as run_soak
    try:
        soak_result = run_soak(world, frame_at, focalizer, complete_fn,
                               timeout=_SOAK_TIMEOUT)   # 独立短超时(P42 常量,见 §3.9)
    except Exception as e:
        logging.getLogger("scribe3.render").warning(
            "soak 失败,降级为无浸泡渲染(focalizer=%s @%s): %s", focalizer, frame_at, e)
        soak_result = None   # build_render_prompt 对 None 已正确处理(render.py:76 条件)
```

```python
# soak.py —— soak 接受并透传独立超时
def soak(world, chapter, focalizer, complete_fn, timeout: float | None = None) -> dict:
    kw = {"timeout": timeout} if timeout is not None else {}
    return parse_soak(complete_fn(build_soak_prompt(world, chapter, focalizer), **kw))
```

> 注:`build_render_prompt` 在 `soak_result=None` 时已正确跳过浸泡块(`render.py:76` 的 `if soak_result and (...)`),所以降级路径无需改 prompt 拼装。
> 关键 TDD 锚点:注入一个"soak 调用抛异常、渲染调用正常返回正文"的 `complete_fn`,断言 `render()` 仍返回正文(见 §4 T2)。

### 3.3 〔A·P06〕关键多步写包事务

**现状**:`_execute_write`(`store.py:121-123`)逐条独立提交,无 BEGIN/COMMIT。多步写有:`grant_public`(循环发边,`store.py:182-184`)、migrate 批量写(`migrate.py:110-128`)、`seed_craft_rules`(连发 9 条,`store.py:303-315`)。

**修法**:加一个**事务上下文**方法,把"多条 surql 才完整"的操作包起来。SurrealDB 支持 `BEGIN TRANSACTION; ... COMMIT TRANSACTION;`(或单次 query 内多语句)。**实现仍收敛在 `_execute_write` 之上**,不新开绕过它的写路径(守护 P23 不变量)。

```python
# store.py —— 事务上下文(关键多步写用)
from contextlib import contextmanager

@contextmanager
def transaction(self):
    """关键多步写的事务边界。块内的 _execute_write 在同一事务里,要么全成要么全不落。
    实现取舍见'需人工确认'。"""
    self._execute_write("BEGIN TRANSACTION", {})
    try:
        yield
        self._execute_write("COMMIT TRANSACTION", {})
    except Exception:
        self._execute_write("CANCEL TRANSACTION", {})
        raise
```

```python
# grant_public 用事务包裹循环
def grant_public(self, fact_id: str, chapter: int) -> None:
    with self.transaction():
        for c in self.characters():
            self.add_knowledge(KnowledgeEdge(c.id, fact_id, since_chapter=chapter, acquired_via="given"))
```

> ⚠ **需人工确认**:SurrealDB Python SDK(`surrealdb` 包)的 WS 连接里,`BEGIN/COMMIT` 是否能跨多次独立 `db.query()` 调用维持同一事务上下文,需在真库验证——SurrealDB 的事务语义在不同版本/不同客户端绑定下行为不同(诊断 §2 已将 P06 列为**三阶段、改动"大"**)。若 SDK 不支持跨调用事务,退路是**把多步写拼成单条多语句 surql**(一次 `query("BEGIN; ...; COMMIT")`),代价是 `add_knowledge` 等需提供"返回 surql 字符串而不立即执行"的变体。本方案默认走"单条多语句"退路更稳,T3 测试据此设计(断言:循环中途人为制造失败时,已发的边全部回滚,不留半套)。

### 3.4 〔A·P27/P31〕连接资源治理

**现状**:
- P31:`_store_for`(`app.py:41-46`)把每书的 `SurrealStore` 缓存进 `_stores` dict,**只增不汰**——长跑下连接数随访问过的书数单调增长。
- P27:`/live`(`app.py:611-619`)每请求订阅 `_LIVE_TABLES`(9 张表),`live_stream` 为每表开一条 WS LIVE 查询,客户端反复刷新页面 → 连接累积无上限。

**修法**(诊断列为三阶段,本枢纽给"轻量止血"版,体系化连接池留作后续):

P31——给 `_stores` 加 LRU 上限 + 关闭被汰连接:

```python
# app.py —— store 缓存加上限(轻量,非完整连接池)
from collections import OrderedDict
_STORE_CACHE_MAX = 8   # P42 常量化
_stores: OrderedDict[str, SurrealStore] = OrderedDict()

def _store_for(work: str) -> SurrealStore:
    st = _stores.get(work)
    if st is None:
        st = SurrealStore(ns="scribe3", db=work); st.apply_schema()
        _stores[work] = st
        while len(_stores) > _STORE_CACHE_MAX:
            _, old = _stores.popitem(last=False)
            old.close()   # 汰出即关连接(P17:close 现在有日志,失败可见)
    else:
        _stores.move_to_end(work)
    return st
```

P27——`live_stream` 合并为**单条多表 LIVE 订阅**(SurrealDB LIVE 支持一次订阅,或在 `live.py` 内对同一连接复用),并对单 work 的并发 live 连接设上限。

> ⚠ **需人工确认**:`live.py` 当前实现细节(单连接 9 订阅 vs 9 连接)需对照其源码确认——诊断锚 `live.py:20` 称"每请求 9 条 WS"。合并订阅的可行性取决于 SurrealDB LIVE 是否支持单查询多表。**最小止血**(无论 live.py 形态都成立):给 `/live` 加"每 work 最多 N 个活跃 live 流"的计数闸,超限拒绝新连接。

### 3.5 〔B·P17〕结构化日志替换裸 except——统一兜底范式

**现状**:§2.2 表中 8 处吞错点,日志覆盖不一(`_bg_ingest` 已有 warning,observation 3134;其余多为裸 `pass` 或静默返默认值)。

**修法**:统一一个"有声吞错"范式——保留默认返回值,但记结构化日志(含失败上下文 + 原始输入/异常)。以解析类为例:

```python
# critique.py —— parse_* 去静默
import logging
_log = logging.getLogger("scribe3.critique")

def parse_discipline(reply: str) -> dict:
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        d = json.loads(m.group(0)) if m else {}
        return {"ok": bool(d.get("ok", True)), "violations": list(d.get("violations") or []),
                "cut_after": (d.get("cut_after") or "").strip()}
    except Exception as e:
        _log.warning("parse_discipline 失败,纪律默认放行: %s | reply[:120]=%r", e, (reply or "")[:120])
        return {"ok": True, "violations": [], "cut_after": ""}   # 行为不变,只加日志
```

`parse_knowledge_delta`(`critique.py:188`)、`parse_soak`(`soak.py:35`)、`store.close`(`store.py:111`)、`migrate.py:127`、`app.works` 的 stats(`app.py:66`)、`llm._api_key`(`llm.py:25`)同范式处理。

> **行为契约不变**:这是本枢纽里**唯一一处"明确不改外部行为只加可观测性"**的工作项——所有 parse_* 的返回值、所有 fail-open 的兜底值保持原样。因此它的 TDD 是"**行为回归测试 + 日志断言**"(用 `caplog` 断言失败时确有 WARNING 落下,且默认值仍返回;见 §4 T5)。
> **与 C 枢纽边界**:`find_leaks` 的 `leaks=0` 假绿(`app.py:585`)其**契约修复**(改回 `leaks=null`+error)归 **C 枢纽 P13**;本枢纽只负责"此处 except 也要落日志",不改其返回契约,避免双枢纽冲突。

### 3.6 〔C·P19〕拆 `build_render_prompt`

**现状**:`render.py:31-89`,59 行,顺序拼 6 段(视角头 + 帧事实 + 事件 + 声音 + craft + soak + 渲染纪律),其中"帧事实块"和"事件块"含嵌套 `world.entity()` 解析。

**修法**:抽三个纯私有函数,主函数变成"编排 + 拼接"。**签名与返回的最终字符串逐字不变**(由 `test_render.py` 的多个字面断言守护,如 `test_render_prompt_has_focalizer_and_event:20` 断言 "对峙"/"暴雨" 在 prompt 里)。

```python
# render.py —— 拆分目标
def _facts_block(world, frame, foc_name) -> list[str]:
    lines = ["", f"## {foc_name} 此刻所知(这是你能用的全部事实,帧外之事他不知道):"]
    if frame.facts:
        for f in frame.facts:
            subj = world.entity(f.entity_id)
            nm = subj.name if subj else f.entity_id
            lines.append(f"- {nm}·{f.attribute}:{f.value}")
    else:
        lines.append("-(空:此视角暂无已知事实)")
    return lines

def _events_block(world, story_at) -> list[str]:
    lines = ["", "## 本章要发生的事件(按此渲染):"]
    for ev in _events_at(world, story_at):
        parts = "、".join((world.entity(v).name if world.entity(v) else v)
                          for v in ev.participants.values())
        where = world.entity(ev.location).name if ev.location and world.entity(ev.location) else (ev.location or "")
        lines.append(f"- [{ev.type}] {parts}" + (f" 于{where}" if where else ""))
    return lines

def _voice_block(foc_name, voice) -> list[str]:
    if not voice:
        return []
    _VK = {"free": "自由独白", "pressure": "压力独白", "relation": "关系独白", "narration": "叙述语气"}
    vlines = [f"- {_VK[k]}:{voice[k]}" for k in ("free", "pressure", "relation", "narration") if voice.get(k)]
    return ["", f"## 你({foc_name})的声音(保持一致,别串味)"] + vlines if vlines else []

def build_render_prompt(world, chapter, focalizer, craft_block="", soak_result=None,
                        voice=None, story_at=None, frame_at=None) -> str:
    # ...(头部 story_at/frame_at/frame/foc_name 计算不变)...
    lines = [<视角头两行>]
    if story_at != chapter:
        lines.append(<插叙标注>)
    lines += _facts_block(world, frame, foc_name)
    lines += _events_block(world, story_at)
    lines += _voice_block(foc_name, voice)
    if craft_block: lines += ["", craft_block]
    if soak_result and (...): lines += <soak 块>     # soak 块逻辑保留在主函数(分支多,抽出收益低)
    lines += ["", _CONSTRAINT]
    return "\n".join(lines)
```

> **不破护栏**:`test_craft_does_not_break_limited_pov`/`test_voice_does_not_break_pov`/`test_flashback_does_not_break_pov`/`test_render_prompt_cannot_contain_others_secret` 四个 load-bearing 测试,加上 `test_linear_default_unchanged`(`test_render.py:108`,断言默认参数与显式相等参数逐字相同)——后者是天然的"重构等价性"测试。**先跑一次记录当前 prompt 输出做 golden,拆完比对逐字一致**(见 §4 T6)。
> **P33 边界**:`_events_block` 列全部 participants 不过滤(诊断 P33)——其**限知过滤修复归 C 枢纽**,本枢纽只做"等价拆分",不改事件块逻辑,避免与 C 冲突。

### 3.7 〔C·P20〕抽 `_stream_write` 公共生成器

**现状**:`chat_write`(GET,`app.py:414-460`)与 `chat_write_post`(POST,`app.py:470-523`)各自包含**逐字相同**的 `gen`/`drain` 闭包(ProposalParser feed → drain → SSE),差异只在:(a) 入参来源(query 参数 vs Pydantic body);(b) POST 多了图片附件拼装(`app.py:484-490`);(c) 传给 `fn` 的 message 是 str 还是含图片的 list。

**修法**:抽公共生成器 `_stream_write(message, instructions)`,两个 handler 只做"参数适配 → 拼 instructions → 拼 message → 调公共生成器"。

```python
# app.py —— 公共写作流生成器
def _write_instructions(st, chapter: int, focalizer: str) -> str:
    s = _editor_write_system(st) + f"\n当前第 {chapter} 章。"
    s += (f"作者指定本章跟随焦点者 {focalizer} 的限知视角:贴该角色所知所感写,别写他不知道的私密。"
          if focalizer else "本章未指定限知焦点者 → 作者视角(可全知)。")
    return s

def _stream_write(message, instructions: str):
    """GET/POST 共用的 SSE 写作流。message: str | list(含图片)。"""
    from scribe3.proposal import ProposalParser
    fn = _responses_events or _import_responses_events()
    parser = ProposalParser(); prop = {"scope": None, "prose": []}
    def drain(events):
        for kind, val in events:
            if kind == "delta":
                yield f"data: {json.dumps({'delta': val}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_open":
                prop["scope"] = val
            elif kind == "proposal_delta":
                prop["prose"].append(val)
            elif kind == "proposal_close":
                yield f"data: {json.dumps({'proposal': {'scope': prop['scope'], 'prose': ''.join(prop['prose'])}}, ensure_ascii=False)}\n\n"
                prop["scope"] = None; prop["prose"] = []
    try:
        for ev in fn(message, instructions):
            t = ev.get("type", "")
            if t == "response.output_text.delta":
                yield from drain(parser.feed(ev.get("delta", "")))
            elif t == "response.output_item.added":
                item = ev.get("item", {}) or {}
                if item.get("type") == "function_call":
                    yield f"data: {json.dumps({'tool': item.get('name', '')}, ensure_ascii=False)}\n\n"
        yield from drain(parser.flush())
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
    yield 'data: {"done": true}\n\n'

@app.get("/chat/write")
def chat_write(msg: str, chapter: int = 1, focalizer: str = "", work: str = "main"):
    st = _store_for(work)
    return StreamingResponse(_stream_write(msg, _write_instructions(st, chapter, focalizer)),
                             media_type="text/event-stream")

@app.post("/chat/write")
def chat_write_post(req: ChatWriteReq, work: str = "main"):
    st = _store_for(work)
    message = _build_image_message(req.msg, req.images) if req.images else req.msg
    return StreamingResponse(_stream_write(message, _write_instructions(st, req.chapter, req.focalizer)),
                             media_type="text/event-stream")
```

> **不破护栏**:`_responses_events` 的 monkeypatch 注入点(`app.py:360` `_responses_events = None`)保留,既有 `test_app.py` 里对 `/chat/write` 的测试(用假 events 驱动)继续绿。**对外行为零变**:GET/POST 端点路径、SSE 事件类型(delta/tool/proposal/done/error)逐字不变(见 §4 T7)。

### 3.8 〔C·P21〕`facts_at` 双实现对拍一致

**现状**:`World.facts_at`(`ontology.py:114-118`)有 `and f.tx_to is None` 条件(取当前草稿);`SurrealStore.facts_at`(`store.py:209-213`)**无此条件**(WHERE 只判 valid_from/valid_to)。诊断 P21:"两版语义已不一致,内存测试通过 ≠ 真库行为"。

**核对结论**:切片阶段 `tx_to` 恒为 `None`(`ontology.py:39-40` 注释"草稿版本(切片恒 0)"、"切片暂不用"),所以**当前两版在现有数据上结果相同**——漂移是**潜在的**(一旦真库引入双时态 tx 维度,真库会漏掉 `tx_to` 过滤)。

**修法**:不急于改 surql(真库尚无 tx 列),而是**用对拍测试把"语义必须一致"钉成可执行契约**——同一组 `(facts, knowledge, chapter)` 喂内存 `World` 和真库 `SurrealStore`,断言 `facts_at` 返回的 fact id 集合相等。对拍测试是"漂移警报器":将来任一侧改了语义,对拍立刻红。

```python
# tests/test_consistency.py(新增)—— 内存/真库 facts_at 对拍
def test_facts_at_parity_memory_vs_store(store):
    """同一组事实喂 World 与 SurrealStore,facts_at 各章结果集必须逐章相等。"""
    from scribe3.ontology import World, Entity, Fact
    seed = [Fact("fact:a", "role:x", "attr", "va", valid_from=1),
            Fact("fact:b", "role:x", "attr", "vb", valid_from=2, valid_to=5),
            Fact("fact:c", "role:x", "attr", "vc", valid_from=3)]
    w = World(); w.add_entity(Entity("role:x", "character", "x"))
    store.add_entity(Entity("role:x", "character", "x"))
    for f in seed:
        w.add_fact(f); store.add_fact(f)
    for ch in range(1, 7):
        assert {f.id for f in w.facts_at(ch)} == {f.id for f in store.facts_at(ch)}, f"第{ch}章漂移"
```

> **不破护栏**:`test_focalizer_frame_excludes_others_secret`(`test_ontology.py:38`,内存)与 `test_persisted_paradigm_holds`(`test_store.py:36`,真库)分别守护两侧投影正确;对拍测试守护两侧**彼此一致**。三者合起来才是完整的"双实现一致性"。
> **若选择"统一实现"路线**(更彻底):把 `facts_at` 的时间门逻辑抽成一个共享纯函数(输入 fact 列表 + chapter,输出过滤后列表),`World.facts_at` 直接用,`SurrealStore.facts_at` 先 SELECT 再走同一纯函数——则单一来源,根除漂移。**取舍**:真库侧改成"全取再 Python 过滤"会放大 P05 全表扫问题(诊断 P04/P05 性能线),与性能枢纽冲突。**故本枢纽默认走"对拍测试钉契约",统一实现留作 B 图枢纽索引落地后再议**,此处标"需人工确认走哪条"。

### 3.9 〔C·P23 + P42 + P43〕单一写点收敛 + 魔法值/正则单一来源

**P23 · works 注册表收敛**:`create_work`/`delete_work`/`rename_work`(`store.py:60-95`)直接 `db.query()` 写 `_reg` 库,绕过 `_execute_write`,破坏 `store.py:6,121` 宣称的"改世界状态只经 `_execute_write`"不变量;`delete_work` 含 `REMOVE DATABASE`(`store.py:69`)。

诊断 P23 给两条路,**本枢纽取"精确限定不变量 + 加测试守护"**(成本小、风险低):
- 不变量精确化为:"**世界状态写**(角色/事实/知识边/事件/章节/母题/伏笔/声音等业务表)唯一经 `_execute_write`;**注册表写**(`_reg.work` 的增删改、`REMOVE DATABASE`)是显式除外的元操作"——在 `store.py:6` docstring 和 `_execute_write` docstring 里固化这条边界。
- 加一个**守护测试**:断言"没有新的世界状态写路径绕过 `_execute_write`"(见 §4 T9 的实现思路:对 SurrealStore 的写方法做 spy,确认 add_* 全部经过 `_execute_write`)。

**P42 · 魔法值常量化**(已核对的真实点):

```python
# store.py 顶部
_OPEN_CHAPTER = 9999      # graph()/无界查询的"到当前为止"哨兵
# app.py 顶部
_ALL_CHAPTERS = 99999     # _editor_system 取全部已确立事实
# llm.py 顶部
_DEFAULT_MODEL = "doubao-seed-2.0-pro"   # 两处签名默认值的单一来源(llm.py:31,58)
_MAX_RETRIES = 3
_SOAK_TIMEOUT = 120.0     # soak 独立超时(< 主渲染 600s)
```

> 核对修正:诊断 P42 称"模型名 5 处",scribe3 实际仅 `llm.py:31` 与 `llm.py:58` **两处**("5 处"应为含 scribe2 的跨仓计数)。常量化这两处即可。

**P43 · 升华正则单一来源**:升华正则当前三处维护——
- `critique.py:49-58` `_PURPLE_PATS`(7 条通用)
- `store.py:307-311` `seed_craft_rules` 里硬编码的 8 条(乱世铜炉系,含与 critique 重叠的"原来…就/那一刻起/眼泪/影子/再也/回不去/刀山火海")
- 题材专属经 `craft_rule.purple_regex` 注入(`store.py:299-301` `purple_patterns` → `critique.find_purple_prose(extra_patterns=)`,`critique.py:64`)

**修法**:把"乱世铜炉系种子正则"抽成**一处常量**(如 `craft.py` 里 `LUANSHI_PURPLE_SEEDS`),`store.seed_craft_rules` 与 `critique._PURPLE_PATS` 的重叠部分都引用它,消除"同一条正则改两个文件"的维护陷阱。通用 AI 腔正则(`critique._PURPLE_PATS` 中不属乱世铜炉特化的)留在 critique。

**P43 · `grant_public` 两实现**:`World.grant_public`(`ontology.py:97-102`,遍历 `entities.values()` 筛 character)与 `SurrealStore.grant_public`(`store.py:182-184`,遍历 `characters()`)——两者**算法同构**(对所有 character 发一条 given 边),但因数据源不同无法共用一份代码。**修法**:不强行合并实现(鸭子兼容的代价),而是**用对拍测试**(§3.8 同款手法)钉住"两版对同一组角色产出相同知识边集合",防语义漂移。

### 3.10 〔D·P39/P40/P41〕死代码——核对后差异化处理

诊断 §6/§8 明确:"死代码删除直接删即可,别当重构任务规划"。但**只读核对推翻了 P39 的前提**:

**P39 · PALETTE —— ⚠ 不可删,诊断有误**:
- 诊断 P39 称 `craft.py:55-144` 的 `PALETTE`(90 行)"定义但全仓无引用,死代码"。
- **核对**:`mcp.py:141-144` 实际 `from scribe3.craft import PALETTE`,用于 MCP 工具 `s3_emotion_palette`(空参返 15 种情感名,带参返某情感的身体信号/内部感觉)——这是**主编 agentic 写作时查情感词典的活工具**。
- **处置**:**保留 PALETTE**。本枢纽产出物里同步**修正诊断 §6 P39 措辞**(把"全仓无引用"改为"仅 `mcp.py:141` 经 `s3_emotion_palette` 引用,非死代码")。这是"红线:无法确认标需人工确认 / 不捏造验证结果"的直接体现——**宁可不删,不可误删活工具**。

**P40 · ChatView.jsx —— ✅ 确认死,删**:
- 核对:`App.jsx:1-44` 的 import 与 `body` 路由(`deduce/codex/atlas/insight/write` 五视图)**不含** ChatView;全仓 `grep ChatView` 仅命中其自身 `export function ChatView`(`views/ChatView.jsx:44`)。对话功能由 `WriteChat.jsx`(已挂载于 WriteLayout)承载,ChatView 是被取代的旧实现。
- **处置**:删除 `web/src/views/ChatView.jsx` 整文件。验证:前端 `npm run build` 绿(用 `tsc -b`/build 真检查,非 `tsc --noEmit` 假绿——见用户记忆"前端类型检查")。

**P41 · @tanstack/react-table —— ✅ 确认未用,删**:
- 核对:`package.json:11` 列 `@tanstack/react-table ^8.21.3`;`src/` 下 `grep tanstack/react-table` 零命中(表格由 recharts/原生实现)。
- **处置**:从 `package.json` dependencies 删除该行,`npm install` 重锁,`npm run build` 绿。

> **D 组的 TDD 形态**(诊断认可):死代码删除无"先写测试"——以"**删除 → 全量回归绿**"表达。后端 142 测试(`pytest`)+ 前端 `npm run build` 双绿即验收(见 §4 T10/T11)。

---

## 4. TDD 实施计划(bite-sized)

> 红线:**可靠性 / DRY 项先写测试 → 实现 → 验证;死代码删除项以"删除 → 全量回归绿"表达;限知 load-bearing 测试全程不破**。每个工作项独立可提交,顺序按"先点灯(B 组)后修路"。
> 基线:当前 `scribe3/tests/` 有 **142 个测试函数**;每步结束 `pytest` 必须 ≥ 此数且全绿。

### 阶段 0 · 点灯(B 组优先,后续步骤的可观测性地基)

**T5 · P17 去静默吞错(行为回归 + 日志断言)**
1. **先写测试**(`test_observability.py` 新增):用 `caplog`(pytest 内置)对每个吞错点——
   - 喂畸形 reply 给 `parse_discipline`/`parse_knowledge_delta`/`parse_soak`,断言:(a) 返回值仍是原默认值(行为不变);(b) `caplog` 捕到一条 WARNING(失败可见)。
   - `assert parse_discipline("乱码非json")["ok"] is True`(fail-open 不变)且 `"parse_discipline 失败" in caplog.text`。
2. **实现**:§3.5 范式,逐点加 `logging.getLogger("scribe3.*").warning(...)`,默认返回值一字不改。
3. **验证**:新测试绿 + 既有 `test_critique.py`/`test_soak.py`/`test_discipline.py` 零回归。

### 阶段 1 · 可靠性(A 组,需先有点灯)

**T1 · P15 流式重试**
1. **先写测试**(`test_llm_stream.py` 新增,纯 monkeypatch 不连网):
   - 构造 `make_stream` 工厂,前 2 次抛 `httpx.ConnectError`、第 3 次正常 yield `["a","b"]`;断言 `list(_stream_with_retry(factory)) == ["a","b"]` 且工厂被调 3 次。
   - 构造"第 1 次 yield 一个 'x' 后抛 ReadTimeout":断言**不重试**(已 started),异常上抛。
   - 构造 4xx `HTTPStatusError`:断言**不重试**,立即 raise。
2. **实现**:§3.1 `_stream_with_retry` + `hermes_complete_stream`/`hermes_responses_events` 各包一层 `make_stream`。
3. **验证**:新测试绿;手测 `/chat/stream` 仍正常流(对外行为不变)。

**T2 · P16 soak 降级 + 独立超时**
1. **先写测试**(`test_render.py` 追加):
   - `test_soak_failure_degrades_to_no_soak`:注入 `complete_fn`,当 prompt 含 soak 独有串"写前浸泡一次"时抛 `RuntimeError`,否则返回正文;断言 `render(..., soak=True)` **仍返回正文**(降级成功),且不抛。
   - `test_soak_passes_independent_timeout`:spy `complete_fn` 的 kwargs,断言 soak 调用带 `timeout=_SOAK_TIMEOUT` 而渲染调用带主超时。
2. **实现**:§3.2 try/except 降级 + `soak()` 透传 timeout。
3. **验证**:新测试 + `test_render_runs_soak_then_renders`(`test_render.py:90`)零回归。

**T3 · P06 关键多步写事务**
1. **先写测试**(`test_store.py` 追加,真库 fixture):
   - `test_grant_public_atomic_on_failure`:在 `grant_public` 循环中途人为制造失败(monkeypatch `add_knowledge` 第 2 次抛错),断言**已发的边全部回滚**(事务后 `knowledge` 不含本次任何 given 边),不留半套。
   - `test_transaction_commits_all_or_nothing`:正常路径下事务内多写全部落库。
2. **实现**:§3.3 `transaction()` 上下文(优先"单条多语句"退路,见该节"需人工确认");`grant_public`/`seed_craft_rules`/migrate 关键写包裹。
3. **验证**:新测试绿 + `test_persisted_paradigm_holds`(`test_store.py:36`)零回归(grant_public 是其依赖路径)。

**T4 · P27/P31 连接治理(止血版)**
1. **先写测试**(`test_app.py` 追加):
   - `test_store_cache_evicts_lru`:连续 `_store_for` 访问超过 `_STORE_CACHE_MAX` 本书,断言 `_stores` 大小 ≤ 上限,且被汰 store 的 `close()` 被调(spy)。
   - `test_live_connection_cap`(若 live 计数闸落地):同一 work 超 N 个并发 live 流时拒绝。
2. **实现**:§3.4 LRU + live 计数闸(live 部分标"需人工确认"依 live.py 实际形态)。
3. **验证**:新测试绿 + `test_live.py` 零回归。

### 阶段 2 · DRY(C 组,碰 render/app 核心,限知测试守护)

**T6 · P19 拆 build_render_prompt(等价拆分)**
1. **先固化 golden**:拆分前跑一次,记录 `build_render_prompt` 对 `luanshi_leak_world()` 在若干 (chapter, focalizer, 各参数组合) 下的**逐字输出**作 golden 断言加入 `test_render.py`。
2. **拆分实现**:§3.6 抽 `_facts_block`/`_events_block`/`_voice_block`。
3. **验证**:golden 断言逐字相等 + 四个 load-bearing(`test_craft_does_not_break_limited_pov`/`test_voice_does_not_break_pov`/`test_flashback_does_not_break_pov`/`test_render_prompt_cannot_contain_others_secret`)+ `test_linear_default_unchanged` 全绿。

**T7 · P20 抽 _stream_write(行为等价)**
1. **先写测试**(`test_app.py` 追加,monkeypatch `_responses_events`):
   - `test_chat_write_get_post_same_events`:用同一组假 events 驱动 GET 与 POST(POST 无图片),断言两者产出的 SSE 事件序列(delta/tool/proposal/done)**逐条相同**。
   - `test_chat_write_post_image_message_shape`:断言带图片时 message 拼成 `[{role,content:[input_text, input_image]}]`(`_build_image_message` 行为)。
2. **实现**:§3.7 抽 `_stream_write`/`_write_instructions`/`_build_image_message`,两 handler 瘦身。
3. **验证**:新测试 + 既有 `/chat/write` 相关测试零回归。

**T8 · P21 facts_at 对拍一致**
1. **先写测试**:§3.8 `test_facts_at_parity_memory_vs_store`(新增 `test_consistency.py`),逐章对拍内存/真库 fact id 集合。
2. **实现**:当前两版结果已一致(`tx_to` 恒 None),测试应**直接绿**——它是"漂移警报器"而非"修 bug"。若选"统一纯函数"路线(§3.8 需人工确认),则抽共享时间门函数。
3. **验证**:对拍绿 + `test_focalizer_frame_excludes_others_secret` + `test_persisted_paradigm_holds` 零回归。

**T9 · P23 单一写点 + P42 魔法值 + P43 正则/grant_public**
1. **先写测试**:
   - `test_no_world_write_bypasses_execute_write`(`test_store.py`):spy `_execute_write`,对每个世界状态写方法(add_entity/add_fact/add_knowledge/add_event/save_chapter/plant_promise/add_motif/add_voice_sample…)断言其确实调用了 `_execute_write`(守护不变量)。
   - `test_grant_public_parity_memory_vs_store`(`test_consistency.py`):同组角色下 World 与 Store 的 grant_public 产出相同 knower→fact 边集合。
   - `test_purple_regex_single_source`:断言 `seed_craft_rules` 落库的乱世铜炉正则与 `craft.LUANSHI_PURPLE_SEEDS` 常量一致(无第二份硬编码)。
2. **实现**:§3.9 常量化 9999/99999/模型名;抽 `LUANSHI_PURPLE_SEEDS`;`store.py`/docstring 固化"注册表显式除外"边界。
3. **验证**:三测试绿 + `test_craft_rule.py`/`test_works.py` 零回归。

### 阶段 3 · 死代码(D 组,删除 → 全量回归绿)

**T10 · P40 删 ChatView.jsx**
- 删 `web/src/views/ChatView.jsx`(已核对未挂载)→ `npm run build` 绿(真构建,非 `--noEmit`)。

**T11 · P41 删 react-table**
- `package.json` 删 `@tanstack/react-table` → `npm install` 重锁 → `npm run build` 绿。

**T12 · P39 PALETTE —— 不删,改诊断**
- **不动 craft.py**;修正 `docs/系统架构/03-问题诊断与整改方案.md` §6/§8 中 P39 的"全仓无引用"措辞为"仅 `mcp.py:141` 引用,非死代码"。
- 验证:`pytest`(`test_mcp.py` 中 `s3_emotion_palette` 若有测试)继续绿;无代码改动则后端零回归。

### 全量回归门禁(每阶段末)
- 后端:`pytest`(净化环境跑 SurrealDB fixture,见 conftest)≥ 142 全绿。
- 前端:`npm run build`(`tsc -b` + vite build,真检查)绿。

---

## 5. 验收标准

| # | 标准 | 验证方式 |
|---|---|---|
| 1 | **流式有重试**:`_stream_with_retry` 对建链期瞬时错重试、4xx/已 started 不重试 | T1 三个测试绿 |
| 2 | **soak 可降级**:soak 失败仍出正文 + 独立短超时 | T2 两个测试绿 |
| 3 | **关键写有事务**:grant_public 等多步写原子(中途失败全回滚) | T3 两个测试绿(真库) |
| 4 | **失败有日志**:8 处吞错点保留 fail-open + 落 WARNING | T5 `caplog` 断言绿,默认值不变 |
| 5 | **连接有上限**:store 缓存 LRU 汰出关连接;live 有计数闸 | T4 测试绿 |
| 6 | **死代码清零(经核对)**:ChatView.jsx + react-table 删;PALETTE 保留并修正诊断 | T10/T11 build 绿;T12 诊断已改 |
| 7 | **重复消除**:build_render_prompt 拆三块、_stream_write 抽公共、正则/grant_public 单一来源 | T6/T7/T9 golden + 等价 + 单源测试绿 |
| 8 | **双实现一致**:facts_at / grant_public 内存↔真库对拍相等 | T8/T9 对拍绿 |
| 9 | **不变量守护**:无世界状态写绕过 `_execute_write` | T9 spy 测试绿 |
| 10 | **限知不破**:四个 render 层 + 两个 ontology 层 load-bearing 测试全程绿 | 每阶段末回归 |
| 11 | **全量回归绿**:后端 ≥142 测试 + 前端 build | 阶段门禁 |

---

## 6. 风险与依赖

### 6.1 依赖
- **独立枢纽**:无强前置。可与 A(运行时急救)、B(图)、C(知识账本)、D(本体规范化)并行。
- **软重叠(需协调,不阻塞)**:
  - P17 的 `find_leaks` 吞错点与 **C 枢纽 P13** 重叠——**边界已划清**(§3.5):本枢纽只加日志,C 改返回契约。两枢纽同改 `app.py:585` 时需注意合并顺序。
  - P19 的 `_events_block` 与 **C 枢纽 P33**(事件块限知过滤)重叠——本枢纽只做等价拆分,过滤逻辑归 C。
  - P21 的 `facts_at` 统一实现"全取再过滤"退路会撞 **B/性能枢纽 P05**(全表扫)——故默认走对拍测试而非改 surql。

### 6.2 风险
| 风险 | 等级 | 缓解 |
|---|---|---|
| P19/P20 重构碰 render/app 核心 | 中 | **限知 load-bearing 测试守护**(四 render + 二 ontology)+ golden 等价断言;先固化 golden 再拆 |
| P06 事务:SurrealDB SDK 跨调用事务语义不确定 | 中 | §3.3 标"需人工确认";默认走"单条多语句"退路;T3 真库测试验证回滚 |
| P27 live 合并依赖 live.py 实际形态 | 低 | §3.4 标"需人工确认";最小止血(计数闸)不依赖 live 内部 |
| P21 统一实现走"全取过滤"放大全表扫 | 低 | 默认走对拍测试,不改 surql;统一实现留待索引落地 |
| 死代码删除 | **低** | 诊断认可"直接删";build 双绿即可;**PALETTE 已拦截误删** |
| P17 行为意外改变 | 低 | 唯一"只加日志不改行为"项;`caplog` + 默认值双断言锁死 |

### 6.3 关键"需人工确认"清单
1. **P06 事务**:SurrealDB Python SDK WS 连接是否支持跨多次 `db.query()` 维持同一事务?(决定走"上下文管理器"还是"单条多语句")。
2. **P27 live**:`live.py` 当前是"单连接 9 订阅"还是"9 连接"?合并订阅是否可行?
3. **P21 路线**:走"对拍测试钉契约"(默认,低风险)还是"统一纯函数实现"(彻底但碰性能)?
4. **P39 诊断修正**:确认 `s3_emotion_palette` 是在用工具后,授权修改诊断文档 §6/§8 的 P39 措辞。

---

## 7. 闭环问题清单(16 项逐一对账)

| 编号 | 诊断锚点(已核对) | 本方案处置 | 工作项 | 状态 |
|---|---|---|---|---|
| **P15** | `llm.py:57-78,81-104`(流式无重试)对比 `:40-54`(非流式有) | `_stream_with_retry` 把重试搬到流式,4xx/已 started 不重试 | §3.1 / T1 | ✅ 覆盖 |
| **P16** | `render.py:108-110`、`soak.py:40-42` | soak 失败降级无浸泡 + 独立短超时 | §3.2 / T2 | ✅ 覆盖 |
| **P06** | `store.py:121-123`、`store.py:182-184`、`migrate.py:110-128` | `transaction()` 包关键多步写,原子回滚 | §3.3 / T3 | ✅ 覆盖(SDK 事务语义待人工确认) |
| **P27** | `app.py:611-619`、`live.py` | live 合并订阅 / 计数闸止血 | §3.4 / T4 | ⚠ 部分(依 live.py 形态,需人工确认) |
| **P31** | `app.py:41-46`(`_stores` 只增不汰) | store 缓存 LRU + 汰出关连接 | §3.4 / T4 | ✅ 覆盖 |
| **P17** | `critique.py:151,188`、`soak.py:35`、`app.py:585`、`store.py:111`、`migrate.py:127`(+`app.py:66`,`llm.py:25`) | 8 处吞错保留 fail-open + 结构化 WARNING | §3.5 / T5 | ✅ 覆盖(`find_leaks` 返回契约归 C) |
| **P19** | `render.py:31-89` | 抽 `_facts_block`/`_events_block`/`_voice_block`,golden 等价 | §3.6 / T6 | ✅ 覆盖(事件块过滤归 C) |
| **P20** | `app.py:414-460`(GET)、`:470-523`(POST) | 抽 `_stream_write`/`_write_instructions`,行为等价 | §3.7 / T7 | ✅ 覆盖 |
| **P21** | `ontology.py:114-118` vs `store.py:209-213`(`tx_to` 漂移) | 对拍测试钉"内存↔真库一致"契约 | §3.8 / T8 | ✅ 覆盖(统一实现路线待人工确认) |
| **P23** | `store.py:60-95`、不变量 `store.py:6,121` | 不变量精确化"注册表除外" + spy 守护测试 | §3.9 / T9 | ✅ 覆盖 |
| **P34** | `critique.py:39`(`s[:3]`)、`:81-82`(破折号不归一化) | ⚠ **见下注**:本方案聚合中**未给具体修法**,需补 | — | ⚠ **缺口,见 §7 注** |
| **P42** | `store.py:406`(9999)、`app.py:321`(99999)、`llm.py:31,58`(模型名) | 常量化(诊断"5 处"实为 2 处,已核对修正) | §3.9 / T9 | ✅ 覆盖 |
| **P43** | `critique.py:49-58` / `store.py:307-311` / `ontology.py:97-102` / `store.py:182-184` | 抽 `LUANSHI_PURPLE_SEEDS` 单源 + grant_public 对拍 | §3.9 / T9 | ✅ 覆盖 |
| **P39** | `craft.py:55-144` | ⚠ **诊断有误**:`mcp.py:141` 在用,**保留**;修正诊断措辞 | §3.10 / T12 | ✅ 覆盖(改为"不删 + 改诊断") |
| **P40** | `web/src/views/ChatView.jsx` | ✅ 确认死(`App.jsx` 未挂),删 | §3.10 / T10 | ✅ 覆盖 |
| **P41** | `web/package.json:11` | ✅ 确认未用(`src/` 零引用),删 | §3.10 / T11 | ✅ 覆盖 |

> ⚠ **P34 缺口诚实标注**:本枢纽任务清单(§1.1 C 组)列入了 P34(QC 误报:排比 `s[:3]`、破折号阈值不归一化),但 §3 详细设计中**未展开其具体修法**——为避免捏造"已覆盖"。**补法(建议补入 T9 或独立 T13)**:
> - 排比误报(`critique.py:39` `openers = Counter(s[:3] ...)`):中文取定长前 3 字过粗,"他转身/他抬头/他冷笑" 会误判排比。改为**按词/句法边界**取开头(如取首个标点前的词,或用更长的判别窗 + 词典过滤高频虚词"他/她/那")。
> - 破折号阈值(`critique.py:81-82` `if dash > 5`):全章固定阈值不随章长归一化,长章必误报。改为 `find_ai_tics` 内**按每千字密度**判定(与 `find_oversaturation` 的 `per_k` 同款,`critique.py:95-110` 已有归一化范式可复用)。
> - TDD:先写"长章不误报破折号"、"`他X/他Y` 非排比不误报"两个测试 → 改实现 → 既有 `test_critique.py` 零回归。

---

> 全部 `文件:行号` 经 2026-06-24 只读核对。本文是**方案文档,未改任何代码**。核对中发现并诚实标注:**P39 诊断有误**(PALETTE 在用,不可删)、**P42 计数偏差**(模型名 2 处非 5 处)、**P34 详细设计缺口**(已在 §7 补修法)。

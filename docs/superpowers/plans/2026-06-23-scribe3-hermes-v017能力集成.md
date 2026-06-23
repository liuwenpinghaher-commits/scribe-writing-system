# scribe3 用对 Hermes v0.17 能力 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 scribe3 主编用对 Hermes v0.17 能力——delegate_task(后台体检)/skill_manage(自进化)用在多步自主场景;ingest 后台用 asyncio、动态 context 用 instructions 提醒(各取最优工程)。

**Architecture:** A) save-chapter 落库后用 FastAPI BackgroundTasks 后台跑已有的 `ingest_chapter`(确定性,不阻塞);B/C) SKILL.md 指引主编反思 patch + 后台 delegate 综合体检;D) `_editor_system` 预注入开着伏笔提醒,详情留主编按需查。

**Tech Stack:** Python 3.11、FastAPI(BackgroundTasks)、FastMCP、SurrealDB、pytest。依据:`docs/superpowers/specs/2026-06-23-scribe3-hermes-v017能力集成-design.md`。

**提交约定(用户红线):** 工作区已在 main,还有上次 craft/WriteChat 的无关改动(app.py 部分/web/HANDOFF 等)。commit 须经作者批准,且**精确 add 本次文件**,绝不 `git add -A`。测试命令用 `scribe3/.venv/bin/python -m pytest`。

---

## File Structure

- `scribe3/ingest.py` — **不改**:`ingest_chapter(store, seq, complete_fn)` 已是可复用纯函数(已存在)。
- `scribe3/mcp.py` — A:`s3_ingest_chapter` 移出 `WRITE_GATED` + sync 化复用 `ingest_chapter`。
- `scribe3/app.py` — A:`save-chapter` 加 BackgroundTasks 后台 ingest + `_bg_ingest`;D:`_editor_system` 加开着伏笔提醒。
- `scribe3/hermes_skills/scribe-novel-v2/SKILL.md` — B:章成自检 patch 指引;C:后台 delegate 体检指引。
- 测试:`tests/test_mcp.py`(drift-guard + ingest 不 gated)、`tests/test_app.py`(后台 ingest 触发 + 伏笔提醒)、`tests/test_ingest.py`(ingest_chapter 已有测试,确认不回归)。

---

## Task 1: A — s3_ingest_chapter 移出 WRITE_GATED + 复用 ingest_chapter

**Files:**
- Modify: `scribe3/mcp.py`(WRITE_GATED:30-32;s3_ingest_chapter:221-235)
- Test: `scribe3/tests/test_mcp.py`(追加 + 同步 drift-guard 期望集)

- [ ] **Step 1: 写失败测试(追加 test_mcp.py)**

```python
def test_ingest_not_gated():
    """ingest 是客观回写(反映已定稿正文),不再 elicitation 待批;创作虚构仍 gated。"""
    from scribe3 import mcp as M
    assert "s3_ingest_chapter" not in M.WRITE_GATED
    # 创作虚构仍待批
    assert "s3_add_fact" in M.WRITE_GATED
    assert "s3_add_event" in M.WRITE_GATED


def test_ingest_chapter_sync_reuses_ingest_chapter(store, monkeypatch):
    """s3_ingest_chapter 改 sync,复用 ingest.ingest_chapter,直接落库(无 elicitation)。"""
    from scribe3 import mcp as M
    store.save_chapter(1, "甲把刀给了乙,丙在旁看着。")
    M.set_store(store)
    import scribe3.ingest as ING
    monkeypatch.setattr(ING, "parse_knowledge_delta",
                        lambda r: {"learned": [{"who": "乙", "fact": "得了刀"}], "did": []})
    monkeypatch.setattr("scribe3.llm.hermes_complete", lambda *a, **k: "{}")
    res = M.s3_ingest_chapter(1)
    assert res["applied"] == 1
```

- [ ] **Step 2: 跑确认失败**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -k "ingest_not_gated or ingest_chapter_sync" -v`
Expected: FAIL — `s3_ingest_chapter` 仍在 WRITE_GATED;`s3_ingest_chapter` 仍是 async(直调返回 coroutine,res["applied"] 报错)。

- [ ] **Step 3: 改 mcp.py**

(a) WRITE_GATED(30-32)去掉 `s3_ingest_chapter`:
```python
WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
               "s3_plant_promise", "s3_advance_promise",
               "s3_craft_rule_add", "s3_craft_rule_remove"}
```

(b) s3_ingest_chapter(221-235 整个)换成 sync 复用 ingest_chapter:
```python
@mcp.tool(annotations=_RW)
def s3_ingest_chapter(seq: int) -> dict:
    """章节回写(客观回写,不待批):读定稿抽"谁新知道什么/做了什么"→更新知识账本。
    非创作虚构(add_fact/add_event 那些经 elicitation);ingest 反映已定稿正文,
    后端 save-chapter 也会自动后台跑同一逻辑。"""
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    return ingest_chapter(_store, seq, hermes_complete)
```

(c) 若 test_mcp.py 有 drift-guard(`test_write_gated_set_no_drift` / `EXPECTED_WRITE_GATED`),把 `EXPECTED_WRITE_GATED` 里的 `"s3_ingest_chapter"` 删掉(只删这一项,其余不动)。

- [ ] **Step 4: 跑确认通过(全量防回归)**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py scribe3/tests/test_mcp_elicit.py scribe3/tests/test_ingest.py -v`
Expected: PASS(含新 2 + drift-guard 更新后全绿;ingest 既有测试不回归)。

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/mcp.py scribe3/tests/test_mcp.py
git commit -m "feat(hermes): ingest 移出 WRITE_GATED(客观回写不待批)+ s3_ingest_chapter sync 复用 ingest_chapter"
```

---

## Task 2: A — save-chapter 后台自动 ingest(BackgroundTasks)

**Files:**
- Modify: `scribe3/app.py`(import 区;save_chapter:531-549 附近;新增 `_bg_ingest`)
- Test: `scribe3/tests/test_app.py`(追加)

- [ ] **Step 1: 写失败测试(追加 test_app.py)**

```python
def test_save_chapter_triggers_bg_ingest(monkeypatch):
    """save-chapter 落库后注册后台 ingest 任务,响应含 ingesting=True,不阻塞。"""
    from fastapi.testclient import TestClient
    import scribe3.app as A
    called = {}
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: called.setdefault("args", (work, seq)))
    client = TestClient(A.app)
    r = client.post("/save-chapter?work=main",
                    json={"seq": 7, "prose": "测试正文。", "title": "t", "focalizer": ""})
    assert r.status_code == 200
    assert r.json().get("ingesting") is True
    # TestClient 同步执行 BackgroundTasks:_bg_ingest 应被以 (main, 7) 调过
    assert called.get("args") == ("main", 7)
```

- [ ] **Step 2: 跑确认失败**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -m pytest scribe3/tests/test_app.py -k save_chapter_triggers_bg -v`
Expected: FAIL — 响应无 `ingesting` 字段;`_bg_ingest` 不存在(AttributeError on monkeypatch)。

- [ ] **Step 3: 改 app.py**

(a) 顶部 import 加 `BackgroundTasks`(与现有 fastapi import 合并):
```python
from fastapi import BackgroundTasks
```

(b) 在 save_chapter 端点附近加 `_bg_ingest`(模块级函数,独立 store 连接,异常记日志不外抛):
```python
def _bg_ingest(work: str, seq: int) -> None:
    """后台客观回写:开独立 store 连接跑 ingest_chapter。异常只记日志,不影响存稿。"""
    import logging
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    try:
        st = _store_for(work)
        ingest_chapter(st, seq, hermes_complete)
    except Exception as e:
        logging.getLogger("scribe3").warning("后台 ingest 第%s章失败: %s", seq, e)
```

(c) save_chapter(531)签名加 `background: BackgroundTasks`,落库+软校验后注册后台 ingest、响应加 `ingesting`:
```python
@app.post("/save-chapter")
def save_chapter(req: SaveChapterReq, background: BackgroundTasks, work: str = "main"):
    st = _store_for(work)
    st.save_chapter(req.seq, req.prose, title=req.title, focalizer=req.focalizer)
    # 软校验(确定性、快、不打 LLM):QC + 限知泄露(保留现有逻辑)
    # ... 现有软校验代码不动 ...
    background.add_task(_bg_ingest, work, req.seq)   # 客观回写,后台自动,不阻塞
    # 在现有 return 的 dict 里加 "ingesting": True
```
注:保留现有软校验与返回内容,只新增 `background.add_task(...)` 与返回里的 `"ingesting": True`。读 531-549 看清现有 return 结构后,在其上加字段,别整段替换丢逻辑。

- [ ] **Step 4: 跑确认通过**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -m pytest scribe3/tests/test_app.py -v`
Expected: PASS(新测试 + 原 test_app 全绿)。

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/app.py scribe3/tests/test_app.py
git commit -m "feat(hermes-A): save-chapter 后台自动 ingest(BackgroundTasks,不阻塞存稿)"
```

---

## Task 3: D — _editor_system 预注入开着伏笔提醒

**Files:**
- Modify: `scribe3/app.py`(`_editor_system`:约 290-310)
- Test: `scribe3/tests/test_app.py`(追加)

- [ ] **Step 1: 写失败测试(追加 test_app.py)**

```python
def test_editor_reminds_open_promises(store):
    """_editor_system 预注入"开着的伏笔"强提醒(防主编忘/漏接)。"""
    import scribe3.app as A
    store.plant_promise("井底那只青铜匣", setup_chapter=1)
    sysmsg = A._editor_system(store)
    assert "开着的承诺线" in sysmsg or "勿忘" in sysmsg
    assert "青铜匣" in sysmsg


def test_editor_no_full_motif_dump(store):
    """agentic 主编详情按需查:_editor_system 不全量灌母题(只给提醒,不堆母题清单)。
    无伏笔/数据时也不崩。"""
    import scribe3.app as A
    store.add_motif("铜炉", theme="代价", echoes="炉火", unfolding="X")
    sysmsg = A._editor_system(store)
    # 母题靠主编按需调 s3_list_motifs,不在系统提示里全量展开
    assert "炉火" not in sysmsg
    assert isinstance(sysmsg, str) and len(sysmsg) > 0
```

- [ ] **Step 2: 跑确认失败**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -m pytest scribe3/tests/test_app.py -k "reminds_open_promises or no_full_motif" -v`
Expected: FAIL — `_editor_system` 当前不注入伏笔提醒("青铜匣"不在输出)。

- [ ] **Step 3: 改 app.py `_editor_system`**

在 `_editor_system` 现有 return 之前组装伏笔提醒,拼进返回串。读现有 290-310(它 return 一个多行 f-string),在 return 的串里追加 `rem`:
```python
    # 开着的伏笔:预注入强提醒(易忘项;母题/事件等详情留主编按需调工具查)
    promises = store.open_promises() if hasattr(store, "open_promises") else []
    rem = ""
    if promises:
        items = "；".join(
            f"第{p.get('setup_chapter')}章埋:{(p.get('text') or '')[:30]}" for p in promises[:6])
        rem = f"\n【⚠ 开着的承诺线·勿忘(适时推进/回收,别让它凭空消失)】{items}"
```
然后把 `rem` 接到现有返回串末尾(在"要求:用简体中文…"那段之后 `+ rem`)。注意:函数参数名是 `store` 还是 `st`——按现有签名(读 `def _editor_system(` 那行)用对名字。

- [ ] **Step 4: 跑确认通过**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -m pytest scribe3/tests/test_app.py -v`
Expected: PASS。

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/app.py scribe3/tests/test_app.py
git commit -m "feat(hermes-D): _editor_system 预注入开着伏笔提醒(详情留 agentic 主编按需查)"
```

---

## Task 4: B+C — SKILL.md 加章成自检(patch)+ 后台 delegate 体检指引

**Files:**
- Modify: `scribe3/hermes_skills/scribe-novel-v2/SKILL.md`

- [ ] **Step 1: 改 SKILL.md "写一章的环"**

在"写一章的环"第7步(回写闭环)之后追加两条,并强化"技能自进化"段。把回写第7步改为(ingest 已由后端自动,主编侧改为可选 + 后台体检):
```markdown
7. **回写闭环**:`s3_ingest_chapter`(客观回写,已**不待批**;后端存稿时也会自动后台跑)——读定稿抽"各角色新知道什么/做了什么且谁看见"→更新知识账本。下一章限知渲染据此反映新知。
8. **后台综合体检(delegate)**:存稿后可 `delegate_task(background=true, prompt="对第N章做综合体检:依次 s3_qc_chapter / s3_discipline_check / s3_find_leaks / s3_causal_complete,综合判断哪些是真问题(别堆噪声),写一份精炼体检报告")`——后台 subagent 自主跑,你立刻继续写,不等。报告下次取。
9. **章成自检(自进化)**:本章有没有摸出一条**可复用修法**(某类坑的解/某腔调的立法/某道 QC 序列)?有 → `skill_manage(action="patch")` 把它追加进本 skill 对应段。只沉淀**流程/craft**,不沉淀剧情事实(事实进 SurrealDB)。
```
并在末尾"技能自进化"段强化:写清 patch 往哪个段(anchor)、规矩(小补丁非重写、受 skills_guard 安全扫描、git 可回滚)。

- [ ] **Step 2: 验证 SKILL.md 仍可被 Hermes 加载(无语法破坏)**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && hermes --profile scribe3 skills list 2>&1 | grep scribe-novel-v2`
Expected: 仍列出 `scribe-novel-v2`(frontmatter 未破坏)。

- [ ] **Step 3: 提交(经作者批准)**

```bash
git add "scribe3/hermes_skills/scribe-novel-v2/SKILL.md"
git commit -m "feat(hermes-BC): SKILL.md 加后台 delegate 体检 + 章成自检 skill_manage patch 指引"
```

---

## Task 5: 全量回归 + 真机集成验证

**Files:** 无(集成校验)

- [ ] **Step 1: 全量回归**

Run: `cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -m pytest scribe3/tests/ -q`
Expected: 全绿(含本期新增 + 既有 115)。任何红=回归,先修。

- [ ] **Step 2: 真机验证 A(后台 ingest 跑通)**

Hermes :8642 在跑。存一章后确认后台 ingest 更新了知识账本:
```bash
cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -c "
from scribe3.store import SurrealStore
from scribe3.ingest import ingest_chapter
from scribe3.llm import hermes_complete
s = SurrealStore(ns='scribe3', db='main'); s.apply_schema()
s.save_chapter(98, '胡不为把铜钉收进怀里,老乌头在一旁看着,没说话。')
r = ingest_chapter(s, 98, hermes_complete)
print('ingest applied:', r['applied'], '| delta:', r['delta'])
s.close()
"`
```
Expected: applied ≥ 1,delta 含 learned/did(真机抽取)。**人工确认**抽取合理。

- [ ] **Step 3: 真机验证 C(delegate 后台体检跑通)**

:8643 主编网关在跑。经 scribe3 responses 通路让主编 delegate 一个后台体检,确认 subagent 跑完产出报告(手动:用 `scribe3/llm.py::hermes_responses_events` 发一条"对第1章做后台综合体检"指令,观察是否出现 `delegate_task` 工具调用事件)。若 :8643 未跑或限流,记录并标注待后续真机复验,不阻塞代码合并。

- [ ] **Step 4: 真机验证 B(skill_manage patch 跑通,可选)**

让主编 `skill_manage(action="patch")` 往 scribe-novel-v2 加一条测试修法,确认过 skills_guard 且 git diff 可见;验证后回滚该测试 patch(`git checkout` 该文件)。

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add -p scribe3/   # 只挑本次相关改动,绝不 -A
git commit -m "test(hermes): 四块全量回归绿 + 真机验证 ingest/delegate"
```

---

## Self-Review

**1. Spec coverage:**
- A ingest asyncio 后台 → Task 1(MCP sync 复用)+ Task 2(save-chapter BackgroundTasks)✓
- B skill_manage 自进化 → Task 4(SKILL.md 章成自检)+ Task 5 Step4(集成验证)✓
- C delegate_task 后台体检 → Task 4(SKILL.md delegate 指引)+ Task 5 Step3(集成验证)✓
- D 关键提醒预注入 → Task 3(_editor_system 伏笔提醒 + 不全量灌母题)✓
- ingest 移出 WRITE_GATED → Task 1 ✓;drift-guard 同步 → Task 1 Step3(c)✓

**2. Placeholder scan:** 无 TBD;每步含完整代码/命令。Task 2 Step3 注明"保留现有软校验、只加字段"(防整段替换丢逻辑),非占位。

**3. Type consistency:** `ingest_chapter(store, seq, complete_fn)->{applied,delta}`(已存在,Task1/2/5 一致调用);`_bg_ingest(work, seq)`(Task2 定义、测试 monkeypatch 一致);`_editor_system(store)` 注入串(Task3);`open_promises()->[{setup_chapter,text,...}]`(Task3 用,store.py:327 已有)。`BackgroundTasks` 注入参数与 FastAPI 一致。

> 注:spec 写 `asyncio.create_task`,计划用 FastAPI `BackgroundTasks` —— 对 sync 端点 `save_chapter` 更 idiomatic(自动线程池跑阻塞的 `ingest_chapter`,不需把端点改 async、不阻塞事件循环),是同目标的更优实现。

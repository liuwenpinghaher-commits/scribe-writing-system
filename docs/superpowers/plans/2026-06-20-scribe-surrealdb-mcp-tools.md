# Scribe MCP 工具层(FastMCP + 审批门)Implementation Plan(底座重构 · 第 3 段)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在第 1/2 段(`scribe2/store.py` 知识层 + `scribe2/domain.py` 领域 repo)之上,建**一套干净的 FastMCP 工具** `scribe2/mcp.py`:读/检索工具标只读、写工具登记进审批表并标 `readOnlyHint=False`,把领域动作(`search_knowledge`/`create_chapter`/`save_prose`/`add_setting` 等)暴露给 Hermes run。

**Architecture:** `scribe2/mcp.py` 薄封装 `Domain`(零新业务逻辑)。一个 `FastMCP("scribe")` 实例;模块级 `WRITE_TOOLS: set[str]` 是审批语义的**真相源**(段4 Hermes run 命中写工具 → 暂停 emit 审批事件),`ToolAnnotations(readOnlyHint)` 为协议级标注。`@mcp.tool()` 装饰后返回原函数,故工具可直接函数调用做 TDD,无需 async。Domain 经 `set_domain()` 注入(测试)/惰性 `connect()`(生产),与 `app.py` 单例风格一致。**不碰旧 `scribe_mcp/`**(clean rebuild 末段统一删)。

**Tech Stack:** Python 3.13、`mcp` SDK(`mcp.server.fastmcp.FastMCP` + `mcp.types.ToolAnnotations`)、SurrealDB(经 Store/Domain)、pytest。

参考:[第1段计划](2026-06-20-scribe-surrealdb-knowledge-layer.md)、[第2段计划](2026-06-20-scribe-surrealdb-domain-rest.md)、[改造 spec §5/§6](../specs/2026-06-20-scribe-hermes-surrealdb-rearchitecture-design.md)。

---

### 约定
- 工作目录 `scribe/`;新文件 `scribe2/mcp.py`;测试 `scribe2/tests/test_mcp.py`
- 复用第 1/2 段 `db` 夹具(conftest.py 内存 SurrealDB)+ `scribe2.conn.domain_from(db)` 装配 Domain
- 跑测试:`.venv/bin/python -m pytest scribe2/tests/test_mcp.py -v`
- 命名注意:`scribe2/mcp.py` 内 `from mcp.server.fastmcp import FastMCP` 是**绝对 import**,解析顶层第三方 `mcp` 包,不会自指 `scribe2.mcp`(父包是 `scribe2`)。文件内**不要**写裸 `import mcp`。

### 工具清单(本段范围 = 已有 Domain 方法的封装)
| MCP 工具 | 类型 | 委托 Domain | 审批 |
|---|---|---|---|
| `search_knowledge(work_id, query, k=6)` | 检索 | `search` | 否(只读) |
| `get_work(work_id)` | 读 | `get_work` | 否 |
| `list_works(owner='u1')` | 读 | `list_works` | 否 |
| `list_chapters(work_id)` | 读 | `list_chapters` | 否 |
| `list_snapshots(chapter_id)` | 读 | `list_snapshots` | 否 |
| `latest_prose(chapter_id)` | 读 | `latest_prose` | 否 |
| `list_settings(work_id)` | 读 | `list_settings` | 否 |
| `create_work(title, genre='', owner='u1')` | 写 | `create_work` | **是** |
| `create_volume(work_id, seq, title='')` | 写 | `create_volume` | **是** |
| `create_chapter(work_id, seq, title='', volume_id=None)` | 写 | `add_chapter` | **是** |
| `save_prose(work_id, chapter_id, content, lock=False)` | 写 | `save_prose` | **是** |
| `add_setting(work_id, name, desc='')` | 写 | `add_setting` | **是** |

> 注:`advance_foreshadow`/`run_critique`/`set_intent` 等 spec §5 点名的其余写动作,对应 Domain 方法**段2 尚未实现**,故本段不造空壳工具;待 Domain 扩展后按同模式增量补(见 Self-Review)。

---

### Task 1:依赖探测 + MCP 骨架 + 审批登记表 + 核心两工具

建 `mcp.py` 骨架(FastMCP 实例 / Domain 注入 / `WRITE_TOOLS` 登记机制),先落一读(`search_knowledge`)一写(`create_work`)以验证审批语义与领域贯通。

**Files:**
- Create: `scribe/scribe2/mcp.py`
- Test: `scribe/scribe2/tests/test_mcp.py`

- [ ] **Step 1: 探测 `mcp` 依赖与 annotations 能力**

Run:
```bash
.venv/bin/python -c "from mcp.server.fastmcp import FastMCP; from mcp.types import ToolAnnotations; m=FastMCP('probe'); m.tool(annotations=ToolAnnotations(readOnlyHint=True))(lambda x: x); print('mcp+annotations OK')"
```
Expected: 打印 `mcp+annotations OK`。
- 若 `ModuleNotFoundError: No module named 'mcp'` → 先装:`.venv/bin/pip install mcp` 后重跑本步。
- 若装好后 `TypeError`(该版本 `tool()` 不接受 `annotations=`)→ 走**退化路径**:Step 3 的工具去掉 `annotations=` 参数(仅靠 `WRITE_TOOLS` 登记表),并在 Task 4 把注解断言放宽为 `ro in (True, None)`。`WRITE_TOOLS` 始终是审批真相源,退化不影响审批语义。

- [ ] **Step 2: 写失败测试**

```python
# scribe2/tests/test_mcp.py
import scribe2.mcp as M
from scribe2.conn import domain_from


def test_approval_registry_and_core_tools(db):
    d = domain_from(db); d.s.init_schema()
    M.set_domain(d)
    # 审批语义:写工具需审批,检索工具不需
    assert M.requires_approval("create_work") is True
    assert M.requires_approval("search_knowledge") is False
    # 写工具贯通:建书 → Domain 读得到
    w = M.create_work("雨夜", genre="悬疑")["work_id"]
    assert d.get_work(w)["title"] == "雨夜"
    # 检索工具贯通:喂一条设定(走 Domain,add_setting 工具 Task3 才加)→ 语义召回
    d.add_setting(w, name="断魂剑", desc="会让持有者失忆的古剑")
    hits = M.search_knowledge(w, "失忆的剑", k=3)
    assert any("断魂剑" in (h.get("text") or "") for h in hits)
```

- [ ] **Step 3: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_approval_registry_and_core_tools -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'scribe2.mcp'`)

- [ ] **Step 4: 实现骨架 + 核心两工具**

```python
# scribe2/mcp.py
"""Scribe 领域 MCP 工具(FastMCP)。薄封装 Domain;写工具登记审批表。

段4 Hermes run 挂本 server:命中 WRITE_TOOLS 内的工具 → 暂停并 emit 审批事件。
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .conn import connect, domain_from
from .domain import Domain

mcp = FastMCP("scribe")

# ---- Domain 注入:测试用 set_domain;生产惰性 connect(与 app.py 单例风格一致)----
_state: dict = {"domain": None}


def set_domain(d: Domain) -> None:
    """测试/启动期注入已装配的 Domain。"""
    _state["domain"] = d


def _domain() -> Domain:
    if _state["domain"] is None:
        _state["domain"] = domain_from(connect())
    return _state["domain"]


# ---- 审批登记表:段4 Hermes 审批门据此判定是否暂停 ----
WRITE_TOOLS: set[str] = set()


def requires_approval(tool_name: str) -> bool:
    """该工具是否为需人审批的写操作。"""
    return tool_name in WRITE_TOOLS


READ = ToolAnnotations(readOnlyHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False)


def _write(fn):
    """注册写工具:登记进 WRITE_TOOLS + 标 readOnlyHint=False。返回原函数(可直接调用)。"""
    WRITE_TOOLS.add(fn.__name__)
    return mcp.tool(annotations=WRITE)(fn)


# ---- 检索(核心 · 只读)----
@mcp.tool(annotations=READ)
def search_knowledge(work_id: str, query: str, k: int = 6) -> list[dict]:
    """对全书做 向量+全文 混合检索并沿图扩展,汇聚相关设定/正文/伏笔/记忆。只读。"""
    return _domain().search(work_id, query, k)


# ---- 写(需审批)----
@_write
def create_work(title: str, genre: str = "", owner: str = "u1") -> dict:
    """新建作品。写操作,需审批。"""
    return {"work_id": _domain().create_work(title, genre, owner)}
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_approval_registry_and_core_tools -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add scribe/scribe2/mcp.py scribe/scribe2/tests/test_mcp.py
git commit -m "feat(scribe2): MCP 骨架 + 审批登记表 + search_knowledge/create_work 工具"
```

---

### Task 2:其余读工具(get_work / list_works / list_chapters / list_snapshots / latest_prose / list_settings)

**Files:**
- Modify: `scribe/scribe2/mcp.py`(在 `search_knowledge` 之后、写工具之前追加读工具)
- Test: `scribe/scribe2/tests/test_mcp.py`

- [ ] **Step 1: 写失败测试**

```python
def test_read_tools(db):
    d = domain_from(db); d.s.init_schema()
    M.set_domain(d)
    w = M.create_work("书")["work_id"]
    c = d.add_chapter(w, 1, "一")
    d.save_prose(w, c, "初稿。")
    assert M.get_work(w)["title"] == "书"
    assert [x["title"] for x in M.list_works()] == ["书"]
    assert [x["seq"] for x in M.list_chapters(w)] == [1]
    assert M.latest_prose(c) == "初稿。"
    assert len(M.list_snapshots(c)) == 1
    assert M.list_settings(w) == []
    # 读工具一律不需审批
    for t in ["get_work", "list_works", "list_chapters",
              "list_snapshots", "latest_prose", "list_settings"]:
        assert M.requires_approval(t) is False
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_read_tools -v`
Expected: FAIL(`AttributeError: module 'scribe2.mcp' has no attribute 'get_work'`)

- [ ] **Step 3: 追加读工具**(放在 `search_knowledge` 之后、`create_work` 之前)

```python
@mcp.tool(annotations=READ)
def get_work(work_id: str) -> dict | None:
    """读取作品元数据。"""
    return _domain().get_work(work_id)


@mcp.tool(annotations=READ)
def list_works(owner: str = "u1") -> list[dict]:
    """列出某 owner 的全部作品。"""
    return _domain().list_works(owner)


@mcp.tool(annotations=READ)
def list_chapters(work_id: str) -> list[dict]:
    """按 seq 升序列出作品的章节。"""
    return _domain().list_chapters(work_id)


@mcp.tool(annotations=READ)
def list_snapshots(chapter_id: str) -> list[dict]:
    """按 version 升序列出某章的版本快照。"""
    return _domain().list_snapshots(chapter_id)


@mcp.tool(annotations=READ)
def latest_prose(chapter_id: str) -> str:
    """取某章最新版本的正文文本。"""
    return _domain().latest_prose(chapter_id)


@mcp.tool(annotations=READ)
def list_settings(work_id: str) -> list[dict]:
    """列出作品的设定条目。"""
    return _domain().list_settings(work_id)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_read_tools -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/mcp.py scribe/scribe2/tests/test_mcp.py
git commit -m "feat(scribe2): MCP 读工具(work/章/快照/正文/设定 列表)"
```

---

### Task 3:其余写工具(create_volume / create_chapter / save_prose / add_setting)

**Files:**
- Modify: `scribe/scribe2/mcp.py`(在 `create_work` 之后追加写工具)
- Test: `scribe/scribe2/tests/test_mcp.py`

- [ ] **Step 1: 写失败测试**

```python
def test_write_tools(db):
    d = domain_from(db); d.s.init_schema()
    M.set_domain(d)
    w = M.create_work("书")["work_id"]
    v = M.create_volume(w, seq=1, title="上卷")["volume_id"]
    c = M.create_chapter(w, seq=1, title="一", volume_id=v)["chapter_id"]
    M.save_prose(w, c, "雨夜。", lock=True)
    M.add_setting(w, name="断魂剑", desc="失忆古剑")
    # 贯通:经 Domain 读回写工具落的数据
    assert d.latest_prose(c) == "雨夜。"
    assert [x["seq"] for x in d.list_chapters(w)] == [1]
    assert any("断魂剑" in (h.get("text") or "")
               for h in M.search_knowledge(w, "失忆的剑", k=3))
    # 写工具一律需审批
    for t in ["create_work", "create_volume", "create_chapter",
              "save_prose", "add_setting"]:
        assert M.requires_approval(t) is True
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_write_tools -v`
Expected: FAIL(`AttributeError: module 'scribe2.mcp' has no attribute 'create_volume'`)

- [ ] **Step 3: 追加写工具**(放在 `create_work` 之后)

```python
@_write
def create_volume(work_id: str, seq: int, title: str = "") -> dict:
    """新建卷。写操作,需审批。"""
    return {"volume_id": _domain().create_volume(work_id, seq, title)}


@_write
def create_chapter(work_id: str, seq: int, title: str = "",
                   volume_id: str | None = None) -> dict:
    """在作品下新建章节(可选挂卷)。写操作,需审批。"""
    return {"chapter_id": _domain().add_chapter(work_id, seq, title, volume_id)}


@_write
def save_prose(work_id: str, chapter_id: str, content: str,
               lock: bool = False) -> dict:
    """为某章存一份正文快照(自动递增版本)。写操作,需审批。"""
    return {"snapshot_id": _domain().save_prose(work_id, chapter_id, content, lock)}


@_write
def add_setting(work_id: str, name: str, desc: str = "") -> dict:
    """新增设定条目(自动嵌入,立即可被 search_knowledge 召回)。写操作,需审批。"""
    return {"setting_id": _domain().add_setting(work_id, name, desc)}
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_write_tools -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/mcp.py scribe/scribe2/tests/test_mcp.py
git commit -m "feat(scribe2): MCP 写工具(建卷/建章/存稿/加设定,均登记审批)"
```

---

### Task 4:工具可发现性 + 注解一致性 + stdio 入口 + 全量回归

确认 FastMCP **真的注册**了全部工具(Hermes 才挂得上),且每个工具的 `readOnlyHint` 注解与 `WRITE_TOOLS` 登记一致、描述非空;加 stdio 启动入口供段4 Hermes 挂载。

**Files:**
- Modify: `scribe/scribe2/mcp.py`(文件末尾加 `main()` 入口)
- Test: `scribe/scribe2/tests/test_mcp.py`

- [ ] **Step 1: 写失败测试**

```python
import asyncio


def test_tools_discoverable_and_annotated(db):
    tools = {t.name: t for t in asyncio.run(M.mcp.list_tools())}
    expected = {
        "search_knowledge", "get_work", "list_works", "list_chapters",
        "list_snapshots", "latest_prose", "list_settings",
        "create_work", "create_volume", "create_chapter",
        "save_prose", "add_setting",
    }
    # 全部工具已注册(Hermes 可发现)
    assert expected <= set(tools), f"缺工具: {expected - set(tools)}"
    # 注解 readOnlyHint 与 WRITE_TOOLS 登记一致
    for name in expected:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        assert ro is (name not in M.WRITE_TOOLS), f"{name} 注解/登记不一致"
    # 每个工具有非空描述(供 agent 决策)
    for name in expected:
        assert (tools[name].description or "").strip(), f"{name} 缺描述"
    # 恰好这 5 个写工具需审批,不多不少
    assert M.WRITE_TOOLS == {
        "create_work", "create_volume", "create_chapter",
        "save_prose", "add_setting",
    }
```

> 退化提醒:若 Task 1 Step 1 探测到该 mcp 版本不支持 `annotations=`,把上面 `assert ro is (...)` 改为 `assert ro in (True, None) if name not in M.WRITE_TOOLS else ro in (False, None)`;`WRITE_TOOLS` 断言不变(审批真相源)。

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_tools_discoverable_and_annotated -v`
Expected: FAIL(此前无此测试;若 `main` 未加不影响本测试,主因是先确认 list_tools 断言全绿)

- [ ] **Step 3: 加 stdio 入口**(文件末尾)

```python
def main() -> None:
    """以 stdio 传输启动 MCP server,供 Hermes run / MCP 客户端挂载(段4)。"""
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_mcp.py::test_tools_discoverable_and_annotated -v`
Expected: PASS

- [ ] **Step 5: 全量回归 + 提交**

Run: `.venv/bin/python -m pytest scribe2/tests/ -q`
Expected: 段1+段2+段3 全绿(原 15 测试 + 本段 4 测试 = 19 通过)

```bash
git add scribe/scribe2/mcp.py scribe/scribe2/tests/test_mcp.py
git commit -m "feat(scribe2): MCP 工具可发现性/注解校验 + stdio 入口(供 Hermes 挂载)"
```

---

## Self-Review

- **Spec 覆盖(本段 = spec §5 MCP 工具层 + §6 审批语义)**:一套干净 FastMCP server(T1)、检索工具 `search_knowledge`(T1)、读工具全集(T2)、写工具 `create_chapter`/`save_prose`/`add_setting` 等(T3)、写工具标记 `requires_approval` + 协议注解 + 可发现性(T1/T3/T4)。**未覆盖(后续段)**:① `advance_foreshadow`/`run_critique`/`set_intent` 等动作需先在 Domain 实现(段2 未做),按 T1/T3 同模式增量补;② Hermes run 实际挂载本 server + 审批事件对接(段4);③ SurrealMCP 只读挂载(可选,段4/5)。
- **占位符扫描**:无 TODO/TBD;每步给确切代码与命令;唯一外部不确定点(`mcp` 包是否安装 / `annotations=` 是否被该版本支持)在 T1 Step1 用探测命令 + 明确退化路径就地处理,`WRITE_TOOLS` 恒为审批真相源。
- **类型一致**:工具签名与委托的 Domain 方法逐一对齐——`create_chapter(...volume_id)`→`Domain.add_chapter(...volume)`;`search_knowledge(work_id,query,k)`→`Domain.search(work,query,k)`(Domain 内部加 `work:` 前缀);写工具统一返回 `{"<entity>_id": ...}`(与 `app.py` REST 返回风格一致)。`set_domain`/`_domain`/`requires_approval`/`WRITE_TOOLS`/`_write` 跨任务命名一致。
- **依赖隔离**:`@mcp.tool()` 装饰返回原函数 → 测试直接函数调用,无需 pytest-asyncio;仅 T4 用一次 `asyncio.run(mcp.list_tools())` 验证注册(stdlib,无新依赖)。`set_domain` 注入 `db` 夹具,不连真实 server。
- **风险**:① `mcp` 未装 → T1 Step1 `pip install mcp`;② 该版本 `tool()` 不收 `annotations` → 退化为仅登记表,T4 断言放宽;③ `scribe2.mcp` 与第三方 `mcp` 同名 → 绝对 import 安全(约定已注明,文件内禁裸 `import mcp`)。

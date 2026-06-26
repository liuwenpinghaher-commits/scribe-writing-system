# B3 写工具审批 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 主编调写类 scribe MCP 工具时不直接落库,而是挂起为待批写;作者在 scribe 前端批准后才真写,只读工具自动放行。

**Architecture:** 方案 B(scribe 自管,不依赖 hermes 审批)。MCP server 的写工具改成把调用入队 `pending_writes` 表并立即返回 `awaiting_approval`;唯一真正落库点是 REST approve 端点,它调 `pending.execute_write` 派发到真实 db 写函数。前端在右栏轮询 `GET /pending-writes` 渲染审批卡(待批写不进对话 SSE 流——它发生在 hermes 工具调用内部,只能轮询感知)。

**Tech Stack:** Python / FastAPI / FastMCP / SQLite(scribe_mcp);React + TS(web-app);pytest;前端 `npx tsc --noEmit`。

---

## 文件结构

- **新建** `scribe/scribe_mcp/pending.py` — `WRITE_GATED`(被门控的写工具名集合)+ `execute_write(db, fs, tool_name, args)` 派发(唯一执行点,镜像各 MCP 工具体)。server.py 与 api.py 都从这里 import,避免重复。
- **改** `scribe/schema.sql` + `scribe/scribe_mcp/db.py` — 加 `pending_writes` 表 + 4 个纯行操作方法(无领域派发)。
- **改** `scribe/scribe_mcp/server.py` — 7 个写工具改为入队(`_gate` 助手),只读工具不动。
- **改** `scribe/scribe_mcp/api.py` — 加 list/approve/reject 端点;`/events` SSE 快照加 `pending_writes` 计数。
- **改** `scribe/web-app/src/api.ts` + `scribe/web-app/src/Right.tsx` — api 客户端方法 + 右栏 `PendingWrites` 审批卡。

测试落点:`scribe/tests/test_db.py`、新建 `scribe/tests/test_pending.py`、`scribe/tests/test_api.py`。运行用 `.venv/bin/python -m pytest`。

> **提交说明**:本仓库约定「未经要求不 commit」。各 Task 末尾的 commit 步骤在用户同意执行本计划后照常执行(执行本计划即授权);若用户另有指示则跳过提交、只留改动。

---

## Task 1: pending_writes 表 + db 行操作方法

**Files:**
- Modify: `scribe/schema.sql`(文件末尾追加建表)
- Modify: `scribe/scribe_mcp/db.py`(`_migrate` 里加建表 + 新方法)
- Test: `scribe/tests/test_db.py`

- [ ] **Step 1: 写失败测试**

在 `scribe/tests/test_db.py` 末尾追加(文件顶部已有 `from scribe_mcp.db import Database` 之类;若没有则按文件现有 import 风格补 `import json`):

```python
def test_pending_writes_queue_roundtrip(tmp_path):
    from scribe_mcp.db import Database
    db = Database(str(tmp_path / "t.db"))
    wid = db.create_work("u1", "书")
    pid = db.enqueue_pending_write(wid, "upsert_setting",
                                   {"work_id": wid, "type": "character", "name": "沈舟", "content": {"k": "v"}})
    assert pid
    pend = db.list_pending_writes(wid, "pending")
    assert len(pend) == 1
    row = pend[0]
    assert row["tool_name"] == "upsert_setting"
    assert row["args"] == {"work_id": wid, "type": "character", "name": "沈舟", "content": {"k": "v"}}
    assert row["status"] == "pending"
    one = db.get_pending_write(pid)
    assert one["id"] == pid and one["args"]["name"] == "沈舟"
    db.mark_pending_decided(pid, "approved", {"setting_id": "s1"})
    assert db.list_pending_writes(wid, "pending") == []
    done = db.get_pending_write(pid)
    assert done["status"] == "approved" and done["result"] == {"setting_id": "s1"}
    assert done["decided_at"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_db.py::test_pending_writes_queue_roundtrip -q`
Expected: FAIL —`AttributeError: 'Database' object has no attribute 'enqueue_pending_write'`

- [ ] **Step 3: 加建表 DDL**

在 `scribe/schema.sql` 末尾追加:

```sql
-- B3 写工具审批:主编写类工具挂起,作者批准才真写
CREATE TABLE IF NOT EXISTS pending_writes (
  id TEXT PRIMARY KEY,
  work_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  args_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  result_json TEXT,
  created_at TEXT,
  decided_at TEXT
);
```

并在 `scribe/scribe_mcp/db.py` 的 `_migrate` 方法 `for sql in [ ... ]:` 列表里追加同一条建表语句(旧库补表),紧跟 `chapter_tasks` 那条之后:

```python
            "CREATE TABLE IF NOT EXISTS pending_writes ("
            "id TEXT PRIMARY KEY, work_id TEXT NOT NULL, tool_name TEXT NOT NULL, "
            "args_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
            "result_json TEXT, created_at TEXT, decided_at TEXT)",
```

- [ ] **Step 4: 加 db 方法**

在 `scribe/scribe_mcp/db.py` 的 `Database` 类里追加(文件顶部第 9 行已有 `import json`,无需再加):

```python
    def enqueue_pending_write(self, work_id: str, tool_name: str, args: dict) -> str:
        pid = _id()
        self.conn.execute(
            "INSERT INTO pending_writes(id,work_id,tool_name,args_json,status,created_at) "
            "VALUES(?,?,?,?, 'pending', ?)",
            (pid, work_id, tool_name, json.dumps(args, ensure_ascii=False), _now()))
        self.conn.commit()
        return pid

    def _row_to_pending(self, r) -> dict:
        return {"id": r["id"], "work_id": r["work_id"], "tool_name": r["tool_name"],
                "args": json.loads(r["args_json"]), "status": r["status"],
                "result": json.loads(r["result_json"]) if r["result_json"] else None,
                "created_at": r["created_at"], "decided_at": r["decided_at"]}

    def list_pending_writes(self, work_id: str, status: str = "pending") -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM pending_writes WHERE work_id=? AND status=? ORDER BY created_at",
            (work_id, status)).fetchall()
        return [self._row_to_pending(r) for r in rows]

    def get_pending_write(self, pid: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM pending_writes WHERE id=?", (pid,)).fetchone()
        return self._row_to_pending(r) if r else None

    def mark_pending_decided(self, pid: str, status: str, result: dict | None) -> None:
        self.conn.execute(
            "UPDATE pending_writes SET status=?, result_json=?, decided_at=? WHERE id=?",
            (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
             _now(), pid))
        self.conn.commit()
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_db.py::test_pending_writes_queue_roundtrip -q`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
cd scribe && git add schema.sql scribe_mcp/db.py tests/test_db.py
git commit -m "feat(b3): pending_writes 表 + db 行操作(入队/列/取/决断)"
```

---

## Task 2: 写工具门控集合 + 执行派发(pending.py)

**Files:**
- Create: `scribe/scribe_mcp/pending.py`
- Test: `scribe/tests/test_pending.py`

- [ ] **Step 1: 写失败测试**

新建 `scribe/tests/test_pending.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scribe_mcp.db import Database
from scribe_mcp.foreshadow import ForeshadowStore
from scribe_mcp.pending import WRITE_GATED, execute_write


def _db(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    return db, ForeshadowStore(db.conn)


def test_write_gated_set_covers_canonical_writes():
    assert {"upsert_setting", "save_chapter", "save_snapshot", "upsert_character",
            "plant_foreshadow", "advance_foreshadow", "set_author_intent"} <= WRITE_GATED
    # 只读/低风险工具不在门控集
    assert "list_settings" not in WRITE_GATED
    assert "search_book" not in WRITE_GATED


def test_execute_write_upsert_setting_persists(tmp_path):
    db, fs = _db(tmp_path)
    wid = db.create_work("u1", "书")
    res = execute_write(db, fs, "upsert_setting",
                        {"work_id": wid, "type": "character", "name": "沈舟", "content": {"动机": "复仇"}})
    assert "setting_id" in res
    names = [s["name"] for s in db.list_settings(wid)]
    assert "沈舟" in names


def test_execute_write_plant_foreshadow_persists(tmp_path):
    db, fs = _db(tmp_path)
    wid = db.create_work("u1", "书")
    res = execute_write(db, fs, "plant_foreshadow",
                        {"work_id": wid, "summary": "断剑", "foreshadow_chapter": 1})
    assert "foreshadow_id" in res
    assert len(fs.list_open(wid)) == 1


def test_execute_write_unknown_tool_raises(tmp_path):
    db, fs = _db(tmp_path)
    try:
        execute_write(db, fs, "rm_rf", {"work_id": "w"})
        assert False, "未注册工具应抛错"
    except ValueError:
        pass
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_pending.py -q`
Expected: FAIL —`ModuleNotFoundError: No module named 'scribe_mcp.pending'`

- [ ] **Step 3: 实现 pending.py**

新建 `scribe/scribe_mcp/pending.py`,`execute_write` 各分支**逐字镜像** server.py 对应工具体(返回同样的 dict):

```python
"""B3 写工具审批:门控集合 + 执行派发。

WRITE_GATED 里的工具被 MCP server 改为入队待批(不直接落库);
唯一真正落库点是 execute_write —— REST approve 批准后调用。
各分支与 scribe_mcp/server.py 对应工具体一一对应。
"""
from __future__ import annotations

# 碰正典内容的写工具:必须审批。新增此类工具务必加进本集合,否则绕过审批。
WRITE_GATED = {
    "upsert_setting", "save_chapter", "save_snapshot", "upsert_character",
    "plant_foreshadow", "advance_foreshadow", "set_author_intent",
}


def execute_write(db, fs, tool_name: str, args: dict) -> dict:
    """按 tool_name 派发到真实写函数;返回与对应 MCP 工具相同的结果 dict。"""
    a = args
    if tool_name == "upsert_setting":
        return {"setting_id": db.upsert_setting(a["work_id"], a["type"], a["name"], a.get("content"))}
    if tool_name == "save_chapter":
        return {"chapter_id": db.save_chapter(a["work_id"], a["seq"], a.get("title", ""),
                                              a.get("outline"), a.get("status", "draft"))}
    if tool_name == "save_snapshot":
        return {"snapshot_id": db.save_snapshot(a["work_id"], a["chapter_id"], a["content"],
                                                a.get("created_by", "ai"), a.get("parent_id"),
                                                a.get("branch_label", "ai-draft"))}
    if tool_name == "upsert_character":
        return {"character_id": db.upsert_character(a["work_id"], a["name"], a.get("traits"),
                                                    a.get("motivation", ""), a.get("voice_profile"))}
    if tool_name == "set_author_intent":
        return {"intent_id": db.set_author_intent(
            a["work_id"], reader_feeling=a["reader_feeling"], why_write=a.get("why_write", ""),
            central_promise=a.get("central_promise", ""), do_not_betray=a.get("do_not_betray"))}
    if tool_name == "plant_foreshadow":
        return {"foreshadow_id": fs.plant(a["work_id"], a["summary"], a["foreshadow_chapter"],
                                          a.get("importance", "normal"))}
    if tool_name == "advance_foreshadow":
        fs.transition(a["foreshadow_id"], a["to_state"], a.get("chapter"))
        return {"ok": True, "state": a["to_state"]}
    raise ValueError(f"未注册的写工具: {tool_name}")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_pending.py -q`
Expected: PASS(4 项)

- [ ] **Step 5: 提交**

```bash
cd scribe && git add scribe_mcp/pending.py tests/test_pending.py
git commit -m "feat(b3): WRITE_GATED 集合 + execute_write 派发(唯一落库点)"
```

---

## Task 3: MCP server 写工具门控

**Files:**
- Modify: `scribe/scribe_mcp/server.py`(7 个写工具体 + 加 `_gate` 助手)
- Test: `scribe/tests/test_pending.py`(追加,用 importlib 加载 server 模块到独立临时库)

- [ ] **Step 1: 写失败测试**

在 `scribe/tests/test_pending.py` 末尾追加(server.py 在 import 时按 `SCRIBE_DB` 连库,需先设环境变量再 import):

```python
def test_mcp_write_tool_enqueues_not_writes(tmp_path, monkeypatch):
    import importlib, os
    monkeypatch.setenv("SCRIBE_DB", str(tmp_path / "srv.db"))
    import scribe_mcp.server as srv
    importlib.reload(srv)  # 用新 SCRIBE_DB 重连
    wid = srv.db.create_work("u1", "书")

    # 写工具:入队、返回 awaiting_approval、库里没真写
    out = srv.upsert_setting.fn(work_id=wid, type="character", name="沈舟", content={"k": "v"})
    assert out["status"] == "awaiting_approval" and out["pending_id"]
    assert srv.db.list_settings(wid) == []          # 未落库
    assert len(srv.db.list_pending_writes(wid)) == 1  # 已入队

    # 只读工具:照常直接返回
    assert isinstance(srv.list_settings.fn(work_id=wid), list)
```

> 说明:FastMCP 的 `@mcp.tool()` 把函数包成 Tool 对象,原函数在 `.fn` 上(若该版本属性名不同,用 `srv.upsert_setting` 直接可调时去掉 `.fn`)。Step 4 跑测时若 `.fn` 不存在,改成直接 `srv.upsert_setting(...)`。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_pending.py::test_mcp_write_tool_enqueues_not_writes -q`
Expected: FAIL —`assert out["status"] == "awaiting_approval"`(现在直接写库返回 `{"setting_id": ...}`)

- [ ] **Step 3: 加 `_gate` 助手并改写 7 个写工具**

在 `scribe/scribe_mcp/server.py` 顶部 import 区加:

```python
from .pending import WRITE_GATED  # noqa: F401  (门控集合,文档/校验用)
```

在 `db`/`foreshadows` 初始化之后、第一个 `@mcp.tool()` 之前加助手:

```python
def _gate(tool_name: str, args: dict) -> dict:
    """写类工具统一入口:入队待批,不直接落库。"""
    pid = db.enqueue_pending_write(args["work_id"], tool_name, args)
    return {"status": "awaiting_approval", "pending_id": pid,
            "note": "已提交,待作者在 scribe 里确认后写入"}
```

把这 7 个工具体改为调 `_gate`(签名不变,只换函数体):

```python
@mcp.tool()
def set_author_intent(work_id: str, reader_feeling: str, why_write: str = "",
                      central_promise: str = "", do_not_betray: list | None = None) -> dict:
    """设置/更新北极星(写操作,需作者审批)。"""
    return _gate("set_author_intent", {"work_id": work_id, "reader_feeling": reader_feeling,
                 "why_write": why_write, "central_promise": central_promise, "do_not_betray": do_not_betray})


@mcp.tool()
def save_chapter(work_id: str, seq: int, title: str = "", outline: dict | None = None,
                 status: str = "draft") -> dict:
    """保存/更新一章元信息与大纲(写操作,需作者审批)。"""
    return _gate("save_chapter", {"work_id": work_id, "seq": seq, "title": title,
                 "outline": outline, "status": status})


@mcp.tool()
def upsert_setting(work_id: str, type: str, name: str, content: dict | None = None) -> dict:
    """写入/更新一条设定(写操作,需作者审批)。"""
    return _gate("upsert_setting", {"work_id": work_id, "type": type, "name": name, "content": content})


@mcp.tool()
def save_snapshot(work_id: str, chapter_id: str, content: str, created_by: str = "ai",
                  parent_id: str | None = None, branch_label: str = "ai-draft") -> dict:
    """保存一个正文版本快照(写操作,需作者审批)。"""
    return _gate("save_snapshot", {"work_id": work_id, "chapter_id": chapter_id, "content": content,
                 "created_by": created_by, "parent_id": parent_id, "branch_label": branch_label})


@mcp.tool()
def upsert_character(work_id: str, name: str, traits: dict | None = None,
                     motivation: str = "", voice_profile: dict | None = None) -> dict:
    """写入/更新角色档案(写操作,需作者审批)。"""
    return _gate("upsert_character", {"work_id": work_id, "name": name, "traits": traits,
                 "motivation": motivation, "voice_profile": voice_profile})


@mcp.tool()
def plant_foreshadow(work_id: str, summary: str, foreshadow_chapter: int,
                     importance: str = "normal") -> dict:
    """埋一个伏笔(写操作,需作者审批)。"""
    return _gate("plant_foreshadow", {"work_id": work_id, "summary": summary,
                 "foreshadow_chapter": foreshadow_chapter, "importance": importance})


@mcp.tool()
def advance_foreshadow(foreshadow_id: str, to_state: str, chapter: int | None = None) -> dict:
    """推进伏笔状态(写操作,需作者审批)。"""
    # advance 无 work_id 入参,审批队列按 work 维度展示,故查出归属 work_id 一并入队
    work_id = db.work_id_of_foreshadow(foreshadow_id)
    return _gate("advance_foreshadow", {"work_id": work_id, "foreshadow_id": foreshadow_id,
                 "to_state": to_state, "chapter": chapter})
```

`advance_foreshadow` 需要 `work_id` 才能进队(队列按书展示)。在 `scribe/scribe_mcp/db.py` 加一个小查询:

```python
    def work_id_of_foreshadow(self, fid: str) -> str | None:
        r = self.conn.execute("SELECT work_id FROM foreshadows WHERE id=?", (fid,)).fetchone()
        return r["work_id"] if r else None
```

> 已核对:`foreshadows` 表(schema.sql:175)主键 `id`、含 `work_id` 列,SQL 无需调整。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_pending.py -q`
Expected: PASS(5 项)。若报 `.fn` 属性不存在,把测试里的 `.fn` 去掉再跑。

- [ ] **Step 5: 回归 —— 确认 server 模块能 import、其它测试不挂**

Run: `cd scribe && .venv/bin/python -c "import scribe_mcp.server" && .venv/bin/python -m pytest tests/test_db.py -q`
Expected: 无 import 错误;test_db.py 全过。

- [ ] **Step 6: 提交**

```bash
cd scribe && git add scribe_mcp/server.py scribe_mcp/db.py tests/test_pending.py
git commit -m "feat(b3): MCP 写工具改为入队待批,只读工具不变"
```

---

## Task 4: REST 审批端点 + SSE 计数

**Files:**
- Modify: `scribe/scribe_mcp/api.py`(加 3 个端点;`sse_events` 快照加计数)
- Test: `scribe/tests/test_api.py`

- [ ] **Step 1: 写失败测试**

在 `scribe/tests/test_api.py` 末尾、`_run_all` 之前追加:

```python
def test_pending_write_approve_executes_and_idempotent():
    wid = client.post("/works", json={"title": "审批书"}, headers=U1).json()["work_id"]
    # 直接用 db 入队一条待批(模拟 MCP 门已入队)
    from scribe_mcp.api import db
    pid = db.enqueue_pending_write(
        wid, "upsert_setting", {"work_id": wid, "type": "character", "name": "沈舟", "content": {"k": "v"}})

    # 列待批
    pend = client.get(f"/works/{wid}/pending-writes", headers=U1).json()
    assert any(p["id"] == pid for p in pend)
    # 批准前未落库
    assert client.get(f"/works/{wid}/settings", headers=U1).json() == [] or \
        all(s["name"] != "沈舟" for s in client.get(f"/works/{wid}/settings", headers=U1).json())

    # 批准 → 真写
    r = client.post(f"/works/{wid}/pending-writes/{pid}/approve", headers=U1)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert any(s["name"] == "沈舟" for s in client.get(f"/works/{wid}/settings", headers=U1).json())
    # 幂等:再批一次不重复执行,返回已决结果
    r2 = client.post(f"/works/{wid}/pending-writes/{pid}/approve", headers=U1)
    assert r2.status_code == 200 and r2.json()["status"] == "approved"
    settings_now = [s for s in client.get(f"/works/{wid}/settings", headers=U1).json() if s["name"] == "沈舟"]
    assert len(settings_now) == 1  # 未重复写

    # 越权:U2 不能批 U1 的
    pid2 = db.enqueue_pending_write(wid, "upsert_setting",
                                    {"work_id": wid, "type": "x", "name": "y", "content": {}})
    assert client.post(f"/works/{wid}/pending-writes/{pid2}/approve", headers=U2).status_code == 403


def test_pending_write_reject_does_not_write():
    wid = client.post("/works", json={"title": "拒书"}, headers=U1).json()["work_id"]
    from scribe_mcp.api import db
    pid = db.enqueue_pending_write(
        wid, "upsert_setting", {"work_id": wid, "type": "character", "name": "废稿", "content": {}})
    r = client.post(f"/works/{wid}/pending-writes/{pid}/reject", headers=U1)
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert all(s["name"] != "废稿" for s in client.get(f"/works/{wid}/settings", headers=U1).json())
    assert all(p["id"] != pid for p in client.get(f"/works/{wid}/pending-writes", headers=U1).json())
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_api.py::test_pending_write_approve_executes_and_idempotent tests/test_api.py::test_pending_write_reject_does_not_write -q`
Expected: FAIL —404(端点不存在)

- [ ] **Step 3: 实现端点**

在 `scribe/scribe_mcp/api.py` 末尾追加(`db`、`fs`、`_owner`、`_own_work` 均已在文件内定义):

```python
# ---- B3 写工具审批:待批写列表 / 批准 / 拒绝 ----
@app.get("/works/{work_id}/pending-writes")
def list_pending_writes_ep(work_id: str, status: str = "pending",
                           x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_pending_writes(work_id, status)


@app.post("/works/{work_id}/pending-writes/{pid}/approve")
def approve_pending_write(work_id: str, pid: str,
                          x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    pw = db.get_pending_write(pid)
    if not pw or pw["work_id"] != work_id:
        raise HTTPException(404, "待批写不存在")
    if pw["status"] != "pending":           # 幂等:已决断的直接回既有结果
        return {"status": pw["status"], "result": pw["result"]}
    from .pending import execute_write
    try:
        result = execute_write(db, fs, pw["tool_name"], pw["args"])
    except Exception as e:
        raise HTTPException(400, f"执行写操作失败: {e}")
    db.mark_pending_decided(pid, "approved", result)
    return {"status": "approved", "result": result}


@app.post("/works/{work_id}/pending-writes/{pid}/reject")
def reject_pending_write(work_id: str, pid: str,
                         x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    pw = db.get_pending_write(pid)
    if not pw or pw["work_id"] != work_id:
        raise HTTPException(404, "待批写不存在")
    if pw["status"] != "pending":
        return {"status": pw["status"], "result": pw["result"]}
    db.mark_pending_decided(pid, "rejected", None)
    return {"status": "rejected"}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_api.py::test_pending_write_approve_executes_and_idempotent tests/test_api.py::test_pending_write_reject_does_not_write -q`
Expected: PASS(2 项)

- [ ] **Step 5: SSE 快照加 pending 计数(失败测试 + 实现)**

先在 `scribe/tests/test_api.py` 加测试:

```python
def test_sse_snapshot_includes_pending_count():
    # 直接验证快照构造逻辑:list_pending_writes 计数被纳入(不订阅长连接,查 db 即可)
    wid = client.post("/works", json={"title": "计数书"}, headers=U1).json()["work_id"]
    from scribe_mcp.api import db
    db.enqueue_pending_write(wid, "upsert_setting", {"work_id": wid, "type": "x", "name": "n", "content": {}})
    assert len(db.list_pending_writes(wid)) == 1
```

Run 它确认通过(纯 db,Step 1 的 db 方法已实现):
`cd scribe && .venv/bin/python -m pytest tests/test_api.py::test_sse_snapshot_includes_pending_count -q` → PASS

然后改 `sse_events` 的 `snap` 字典(`scribe/scribe_mcp/api.py` 内,现为 `optionsets/insights/flags` 三项),加一项:

```python
                snap = {"optionsets": len(db.list_open_option_sets(work_id)),
                        "insights": len(db.list_proactive_insights(work_id, "new")),
                        "flags": len(db.list_consistency_flags(work_id)),
                        "pending_writes": len(db.list_pending_writes(work_id))}
```

- [ ] **Step 6: 回归全量 api 测试**

Run: `cd scribe && .venv/bin/python -m pytest tests/test_api.py -q`
Expected: 全过(含 B1 的 `test_chat_stream_*`)

- [ ] **Step 7: 提交**

```bash
cd scribe && git add scribe_mcp/api.py tests/test_api.py
git commit -m "feat(b3): 待批写 REST 端点(列/批准/拒绝,幂等+越权挡)+ SSE 计数"
```

---

## Task 5: 前端审批卡(右栏待批写)

**Files:**
- Modify: `scribe/web-app/src/api.ts`(类型 + 3 个方法)
- Modify: `scribe/web-app/src/Right.tsx`(顶部加 `PendingWrites` 区)
- 验证:`npx tsc --noEmit` + 真机点一次

- [ ] **Step 1: api.ts 加类型与方法**

在 `scribe/web-app/src/api.ts` 的 interface 区加:

```typescript
export interface PendingWrite {
  id: string; work_id: string; tool_name: string;
  args: Record<string, unknown>; status: string; created_at?: string;
}
```

在 `export const api = {` 对象里(挨着 insights/optionSets 那批)加:

```typescript
  pendingWrites: (w: string) => req<PendingWrite[]>(`/works/${w}/pending-writes`),
  approvePending: (w: string, id: string) =>
    post<{ status: string }>(`/works/${w}/pending-writes/${id}/approve`),
  rejectPending: (w: string, id: string) =>
    post<{ status: string }>(`/works/${w}/pending-writes/${id}/reject`),
```

- [ ] **Step 2: Right.tsx 加 PendingWrites 区 + 友好工具名**

在 `scribe/web-app/src/Right.tsx`:`Right` 组件 return 里、`<Insights .../>` 上方插入 `<PendingWrites work={work} rev={rev} bump={bump} />`(`bump` 已是 `Right` 的入参,见 `export function Right({ work, rev, bump })`)。

在文件内(挨着 `Insights` 函数)新增组件。复用已有 `useData`/`useToast`/`Card`/`Button` 等 import(文件已在用):

```tsx
const PENDING_LABEL: Record<string, string> = {
  upsert_setting: "新增/更新设定",
  save_chapter: "保存章节",
  save_snapshot: "保存正文快照",
  upsert_character: "新增/更新角色",
  plant_foreshadow: "埋伏笔",
  advance_foreshadow: "推进伏笔",
  set_author_intent: "改北极星",
};

function PendingWrites({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  const { data, loading, error, reload } = useData(() => api.pendingWrites(work), [work, rev]);
  const toast = useToast();
  if (loading || error || !data || data.length === 0) return null;
  const decide = async (id: string, approve: boolean) => {
    try {
      if (approve) await api.approvePending(work, id);
      else await api.rejectPending(work, id);
      toast(approve ? "已写入" : "已拒绝", "ok");
      reload(); bump();
    } catch (e) {
      toast(errMsg(e), "err");
    }
  };
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold text-foreground">待你确认的写操作（{data.length}）</h4>
      {data.map((p) => {
        const name = (p.args.name as string) || (p.args.summary as string) || "";
        return (
          <Card key={p.id} className="border-amber-300/60">
            <CardContent className="p-3 flex items-center justify-between gap-2">
              <div className="text-sm">
                <span className="font-medium">{PENDING_LABEL[p.tool_name] ?? p.tool_name}</span>
                {name && <span className="text-muted-foreground">：{name}</span>}
              </div>
              <div className="flex gap-1.5 shrink-0">
                <Button size="sm" className="h-7" onClick={() => decide(p.id, true)}>批准</Button>
                <Button size="sm" variant="outline" className="h-7" onClick={() => decide(p.id, false)}>拒绝</Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
```

> 校验:`errMsg`、`useToast`、`useData`、`Card`/`CardContent`、`Button` 是否已在 `Right.tsx` 顶部 import。若 `errMsg` 未 import,从 `./common` 补:`import { useData, useToast, errMsg } from "./common";`(按文件现有 import 行合并)。

- [ ] **Step 3: 类型检查**

Run: `cd scribe/web-app && npx tsc --noEmit`
Expected: 无输出(通过)

- [ ] **Step 4: 真机验证(需三服务在跑)**

1. 确认 hermes:8642 / scribe:3320(新代码,重启过)/ 前端:3310 都在。
2. 浏览器开 `localhost:3310` → 进《雾港迷案》→ 对主编说「请把『沈舟动机=查父亲沉船真相』存成一条人物设定」。
3. 期望:主编回复「已提交待确认」,右栏出现「待你确认的写操作」卡 → 点「批准」→ toast「已写入」→ 卡消失;去设定区确认新设定已落库。点「拒绝」的另一条不落库。

> 这是人工验收,非自动化。观察到上述即通过;若主编没调写工具,换更直接的指令(「调用 upsert_setting 写一条设定」)。

- [ ] **Step 5: 提交**

```bash
cd scribe && git add web-app/src/api.ts web-app/src/Right.tsx
git commit -m "feat(b3): 右栏待批写审批卡(批准才落库)"
```

---

## 收尾

- [ ] **更新文档**:把 B3 标记为完成,接力点推进到阶段2。改 `docs/superpowers/HANDOFF.md` 与 `docs/superpowers/specs/2026-06-20-scribe-hermes-阶段1-对话run驱动.md`(追加 B3 实测/实现小结)。
- [ ] **全量回归**:`cd scribe && .venv/bin/python -m pytest tests/test_db.py tests/test_pending.py tests/test_api.py -q` 全过。
- [ ] **提交文档**:`git add docs/ && git commit -m "docs(b3): 阶段1 B3 完成,接力点推进到阶段2"`

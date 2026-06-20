# Scribe 领域层 + REST(SurrealDB)Implementation Plan(底座重构 · 第 2 段)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在第 1 段 `scribe2/store.py`(SurrealDB 知识层)之上,建领域 repo(work/卷/章 + 版本 snapshot + 内容实体)与一个跑在 SurrealDB 上的 FastAPI(`scribe2/app.py`),把核心写作 REST 路径迁到新底座并端到端可运行。

**Architecture:** `scribe2/conn.py`(按 env 连真实 SurrealDB,默认 `~/.scribe/`ASCII 路径避中文坑)→ `scribe2/domain.py`(领域 repo,薄封装 Store)→ `scribe2/app.py`(FastAPI,owner 头鉴权边界,核心端点)。旧 `scribe_mcp/` 不动(clean rebuild 最后一段统一删)。

**Tech Stack:** Python 3.13、SurrealDB(surrealdb SDK + surreal 二进制)、FastAPI + TestClient、pytest。

参考:[第1段计划](2026-06-20-scribe-surrealdb-knowledge-layer.md)、[改造 spec](../specs/2026-06-20-scribe-hermes-surrealdb-rearchitecture-design.md)。

---

### 约定
- 工作目录 `scribe/`;新文件在 `scribe2/`;测试 `scribe2/tests/`
- 复用第1段 `db` 夹具(conftest.py 内存 SurrealDB)
- 跑测试:`.venv/bin/python -m pytest scribe2/tests/<f> -v`

---

### Task 1:领域 repo — 卷/章结构 + 列表排序

**Files:**
- Create: `scribe/scribe2/domain.py`
- Test: `scribe/scribe2/tests/test_domain.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe2/tests/test_domain.py
from scribe2.store import Store
from scribe2.domain import Domain

def test_work_volume_chapter(db):
    d = Domain(Store(db)); d.s.init_schema()
    w = d.create_work("雨夜", genre="悬疑")
    v = d.create_volume(w, seq=1, title="上卷")
    c2 = d.add_chapter(w, seq=2, title="二", volume=v)
    c1 = d.add_chapter(w, seq=1, title="一", volume=v)
    chs = d.list_chapters(w)
    assert [c["seq"] for c in chs] == [1, 2]  # 按 seq 升序
    assert d.get_work(w)["title"] == "雨夜"
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_domain.py::test_work_volume_chapter -v`
Expected: FAIL(`scribe2.domain` 不存在)

- [ ] **Step 3: 实现 Domain(work/volume/chapter)**

```python
# scribe2/domain.py
from __future__ import annotations
from .store import Store

class Domain:
    """领域 repo:在 Store 之上的小说语义。结构实体走 store.create;内容实体走 put_content。"""
    def __init__(self, store: Store):
        self.s = store

    # ---- work ----
    def create_work(self, title: str, genre: str = "", owner: str = "u1") -> str:
        return self.s.create("work", {"title": title, "genre": genre, "owner": owner})

    def get_work(self, wid: str) -> dict | None:
        return self.s.get("work", wid)

    def list_works(self, owner: str = "u1") -> list[dict]:
        return self.s.list("work", "owner = $o", {"o": owner})

    # ---- volume / chapter ----
    def create_volume(self, work: str, seq: int, title: str = "") -> str:
        return self.s.create("volume", {"work": f"work:{work}", "seq": seq, "title": title})

    def add_chapter(self, work: str, seq: int, title: str = "", volume: str | None = None) -> str:
        return self.s.create("chapter", {
            "work": f"work:{work}", "seq": seq, "title": title,
            "volume": (f"volume:{volume}" if volume else None), "status": "draft"})

    def list_chapters(self, work: str) -> list[dict]:
        return self.s.list("chapter", "work = $w ORDER BY seq ASC", {"w": f"work:{work}"})
```

> 注:`work = $w` 用字符串 `"work:⟨id⟩"` 过滤;若 SurrealDB 要 record 类型比较,改存 `RecordID`。先按字符串(第1段 put_content 也用字符串 work),实测对齐。

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_domain.py::test_work_volume_chapter -v`
Expected: PASS(若 `work = $w` 比较因类型不符返回空,改 `WHERE string::concat('work:', meta::id(work)) = $w` 或把 work 存成纯 id 串)

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/domain.py scribe/scribe2/tests/test_domain.py
git commit -m "feat(scribe2): Domain repo(work/volume/chapter + seq 排序)"
```

---

### Task 2:版本 snapshot(存稿 → 版本树)

**Files:**
- Modify: `scribe/scribe2/domain.py`(加 snapshot 方法)
- Test: `scribe/scribe2/tests/test_domain.py`

- [ ] **Step 1: 写失败测试**

```python
def test_snapshots_versioning(db):
    from scribe2.store import Store
    from scribe2.domain import Domain
    d = Domain(Store(db)); d.s.init_schema()
    w = d.create_work("书"); c = d.add_chapter(w, 1, "一")
    s1 = d.save_prose(w, c, "初稿。", locked=False)
    s2 = d.save_prose(w, c, "改稿。", locked=True)
    snaps = d.list_snapshots(c)
    assert len(snaps) == 2
    assert [s["version"] for s in snaps] == [1, 2]   # 版本递增
    assert d.latest_prose(c) == "改稿。"
    assert snaps[1]["locked"] is True
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_domain.py::test_snapshots_versioning -v`
Expected: FAIL(`save_prose` 不存在)

- [ ] **Step 3: 实现 snapshot(版本号 = 该章现有快照数 + 1)**

```python
    def save_prose(self, work: str, chapter: str, content: str, locked: bool = False) -> str:
        existing = self.s.list("snapshot", "chapter = $c", {"c": f"chapter:{chapter}"})
        ver = len(existing) + 1
        return self.s.create("snapshot", {
            "work": f"work:{work}", "chapter": f"chapter:{chapter}",
            "version": ver, "content": content, "locked": bool(locked)})

    def list_snapshots(self, chapter: str) -> list[dict]:
        return self.s.list("snapshot", "chapter = $c ORDER BY version ASC",
                           {"c": f"chapter:{chapter}"})

    def latest_prose(self, chapter: str) -> str:
        snaps = self.list_snapshots(chapter)
        return snaps[-1]["content"] if snaps else ""
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_domain.py::test_snapshots_versioning -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/domain.py scribe/scribe2/tests/test_domain.py
git commit -m "feat(scribe2): snapshot 版本树(save_prose/list_snapshots/latest_prose)"
```

---

### Task 3:内容实体(设定)+ 检索贯通

**Files:**
- Modify: `scribe/scribe2/domain.py`(加 add_setting / search)
- Test: `scribe/scribe2/tests/test_domain.py`

- [ ] **Step 1: 写失败测试**

```python
def test_setting_and_search(db):
    from scribe2.store import Store
    from scribe2.domain import Domain
    d = Domain(Store(db)); d.s.init_schema()
    w = d.create_work("书")
    d.add_setting(w, name="断魂剑", desc="会让持有者失忆的古剑")
    d.add_setting(w, name="码头", desc="雨夜常起雾")
    hits = d.search(w, "失忆的剑", k=2)
    assert hits and "断魂剑" in (hits[0].get("text") or "")
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_domain.py::test_setting_and_search -v`
Expected: FAIL(`add_setting` 不存在)

- [ ] **Step 3: 实现(内容实体走 put_content 自动嵌入)**

```python
    def add_setting(self, work: str, name: str, desc: str = "", type_: str = "设定") -> str:
        text = f"{name}:{desc}" if desc else name
        return self.s.put_content("setting", work=f"work:{work}", text=text,
                                  name=name, stype=type_)

    def list_settings(self, work: str) -> list[dict]:
        return self.s.list("setting", "work = $w", {"w": f"work:{work}"})

    def search(self, work: str, query: str, k: int = 6) -> list[dict]:
        return self.s.search_knowledge(f"work:{work}", query, k=k)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_domain.py::test_setting_and_search -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/domain.py scribe/scribe2/tests/test_domain.py
git commit -m "feat(scribe2): 设定内容实体(自动嵌入)+ domain.search 贯通知识层"
```

---

### Task 4:连接模块(按 env 连真实 SurrealDB)

**Files:**
- Create: `scribe/scribe2/conn.py`
- Test: `scribe/scribe2/tests/test_conn.py`

- [ ] **Step 1: 写失败测试**(用夹具的连接验证 Domain 装配)

```python
# scribe2/tests/test_conn.py
from scribe2.conn import domain_from
def test_domain_from_conn(db):
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("接线书")
    assert d.get_work(w)["title"] == "接线书"
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_conn.py -v`
Expected: FAIL(`scribe2.conn` 不存在)

- [ ] **Step 3: 实现 conn(env 驱动 + 测试可注入)**

```python
# scribe2/conn.py
import os
from surrealdb import Surreal
from .store import Store
from .domain import Domain

# 默认连本地 surreal(ASCII 路径避中文坑);生产经 env 覆盖
SURREAL_URL = os.environ.get("SURREAL_URL", "ws://127.0.0.1:8000/rpc")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")
SURREAL_NS = os.environ.get("SURREAL_NS", "scribe")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")

def connect() -> Surreal:
    d = Surreal(SURREAL_URL)
    d.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
    d.use(SURREAL_NS, SURREAL_DB)
    return d

def domain_from(db) -> Domain:
    return Domain(Store(db))
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_conn.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/conn.py scribe/scribe2/tests/test_conn.py
git commit -m "feat(scribe2): conn 连接模块(env 驱动 + domain_from 注入)"
```

---

### Task 5:FastAPI 核心端点(works/章/正文/设定/search)

**Files:**
- Create: `scribe/scribe2/app.py`
- Test: `scribe/scribe2/tests/test_app.py`

- [ ] **Step 1: 写失败测试**(TestClient + 依赖注入夹具 db)

```python
# scribe2/tests/test_app.py
from fastapi.testclient import TestClient
from scribe2.app import app, get_domain
from scribe2.conn import domain_from

def test_core_rest_flow(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    c = TestClient(app); H = {"X-Owner-Id": "u1"}
    w = c.post("/works", json={"title": "雨夜"}, headers=H).json()["work_id"]
    assert c.get("/works", headers=H).json()[0]["title"] == "雨夜"
    ch = c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=H).json()["chapter_id"]
    c.post(f"/works/{w}/chapters/{ch}/prose", json={"content": "雨夜。", "lock": True}, headers=H)
    c.post(f"/works/{w}/settings", json={"name": "断魂剑", "desc": "失忆古剑"}, headers=H)
    hits = c.post(f"/works/{w}/search", json={"query": "失忆的剑", "k": 3}, headers=H).json()
    assert any("断魂剑" in (h.get("text") or "") for h in hits)
    app.dependency_overrides.clear()
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_app.py -v`
Expected: FAIL(`scribe2.app` 不存在)

- [ ] **Step 3: 实现 FastAPI app**

```python
# scribe2/app.py
from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from .conn import connect, domain_from
from .domain import Domain

app = FastAPI(title="Scribe (SurrealDB)")

_singleton = {"d": None}
def get_domain() -> Domain:
    if _singleton["d"] is None:
        _singleton["d"] = domain_from(connect())
    return _singleton["d"]

def owner(x_owner_id: str | None) -> str:
    if not x_owner_id:
        raise HTTPException(401, "缺少 X-Owner-Id")
    return x_owner_id

class WorkIn(BaseModel):
    title: str
    genre: str = ""
class ChapterIn(BaseModel):
    seq: int
    title: str = ""
class ProseIn(BaseModel):
    content: str
    lock: bool = False
class SettingIn(BaseModel):
    name: str
    desc: str = ""
class SearchIn(BaseModel):
    query: str
    k: int = 6

@app.post("/works")
def create_work(b: WorkIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    return {"work_id": d.create_work(b.title, b.genre, owner(x_owner_id))}

@app.get("/works")
def list_works(x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    return d.list_works(owner(x_owner_id))

@app.put("/works/{w}/chapters")
def add_chapter(w: str, b: ChapterIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"chapter_id": d.add_chapter(w, b.seq, b.title)}

@app.get("/works/{w}/chapters")
def list_chapters(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return d.list_chapters(w)

@app.post("/works/{w}/chapters/{c}/prose")
def save_prose(w: str, c: str, b: ProseIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"snapshot_id": d.save_prose(w, c, b.content, b.lock)}

@app.post("/works/{w}/settings")
def add_setting(w: str, b: SettingIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"setting_id": d.add_setting(w, b.name, b.desc)}

@app.post("/works/{w}/search")
def search(w: str, b: SearchIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return d.search(w, b.query, b.k)

@app.get("/health")
def health():
    return {"ok": True}
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_app.py -v`
Expected: PASS

- [ ] **Step 5: 全量回归 + 提交**

Run: `.venv/bin/python -m pytest scribe2/tests/ -q`(第1段 + 第2段全绿)

```bash
git add scribe/scribe2/app.py scribe/scribe2/tests/test_app.py
git commit -m "feat(scribe2): FastAPI 核心端点(works/章/正文/设定/search)跑在 SurrealDB"
```

---

## Self-Review

- **Spec 覆盖(本段=领域 repo + REST 竖切)**:work/卷/章(T1)、版本 snapshot(T2)、内容实体+检索(T3)、连接(T4)、FastAPI 核心端点(T5)。**未覆盖(后续增量)**:其余 ~60 端点、角色/伏笔/一致性/素材/option_set/北极星等全实体、越权 403、cursor 分页——按 T1/T3/T5 已建的模式逐步补。
- **类型一致**:`Domain` 方法 create_work/get_work/list_works/create_volume/add_chapter/list_chapters/save_prose/list_snapshots/latest_prose/add_setting/list_settings/search 跨任务一致;`domain_from`/`get_domain` 注入一致。
- **无占位符**:每步给确切代码/命令。已知不确定点(`work = $w` 字符串 vs record 比较)在 T1 Step4 给了退化写法。
- **风险**:SurrealDB record-link 字段比较语义需 T1 实测对齐;FastAPI 依赖注入用 `dependency_overrides` 在测试注入夹具 db(避免连真实 server)。

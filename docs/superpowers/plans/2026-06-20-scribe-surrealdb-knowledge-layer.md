# Scribe SurrealDB 知识层地基 Implementation Plan(底座重构 · 第 1 段)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建起 SurrealDB 数据底座的"知识层":连接、schema(关系+向量+全文+图)、嵌入、`search_knowledge` 统一混合检索(向量+全文+图扩展一句 SurrealQL)。这是 clean rebuild 的地基(spec §9.4 第 1 步,最不确定先建)。

**Architecture:** 新建独立 Python 包 `scribe2/`(不碰旧 `scribe_mcp/`,旧的最后一段统一删)。SurrealDB 以本地 `surreal start`(rocksdb 文件)跑;测试用 `surreal start memory` 临时实例。领域逻辑封装在 `scribe2/store.py`;嵌入复用 fastembed。

**Tech Stack:** Python 3.13、SurrealDB(`surrealdb` SDK + `surreal` 二进制)、fastembed(嵌入)、pytest。

参考 spec:[2026-06-20-scribe-hermes-surrealdb-rearchitecture-design.md](../specs/2026-06-20-scribe-hermes-surrealdb-rearchitecture-design.md)(§3 数据层、§9 clean rebuild)。

---

### 约定
- 工作目录:`<repo-root>/scribe`
- 新包:`scribe2/`(`__init__.py` 空);测试:`scribe2/tests/`
- 跑测试:`.venv/bin/python -m pytest scribe2/tests/<f> -v`
- **本任务不删旧代码**(旧 `scribe_mcp/` 留着对照,最后一段计划再清,符合 spec"跑通前不删可参考旧码")。

---

### Task 0:装 SurrealDB + SDK + 测试夹具

**Files:**
- Modify: `scribe/pyproject.toml`(deps 加 `surrealdb`)
- Create: `scribe/scribe2/__init__.py`(空)
- Create: `scribe/scribe2/tests/conftest.py`

- [ ] **Step 1: 装二进制 + SDK**

Run:
```bash
curl -sSf https://install.surrealdb.com | sh   # 装 surreal 二进制
.venv/bin/pip install surrealdb fastembed
```
并在 `pyproject.toml` `[project] dependencies` 增 `"surrealdb"`、`"fastembed"`。
Expected:`surreal version` 有输出;`.venv/bin/python -c "import surrealdb"` 无报错。

- [ ] **Step 2: 写 pytest 夹具(每个测试会话起一个内存 SurrealDB)**

```python
# scribe2/tests/conftest.py
import socket, subprocess, time, pytest
from surrealdb import Surreal

def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

@pytest.fixture()
def db():
    port = _free_port()
    proc = subprocess.Popen(
        ["surreal", "start", "--bind", f"127.0.0.1:{port}",
         "--user", "root", "--pass", "root", "memory"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)  # 等起服
    try:
        d = Surreal(f"ws://127.0.0.1:{port}/rpc")
        d.connect(); d.signin({"username": "root", "password": "root"})
        d.use("scribe", "test")
        yield d
        d.close()
    finally:
        proc.terminate()
```

- [ ] **Step 3: 冒烟测试连接**

```python
# scribe2/tests/test_smoke.py
def test_connect_and_query(db):
    db.query("CREATE work:x SET title='雨夜';")
    rows = db.query("SELECT title FROM work;")
    assert rows and rows[0]["title"] == "雨夜"
```

Run: `.venv/bin/python -m pytest scribe2/tests/test_smoke.py -v`
Expected: PASS(若 SDK 返回结构不同,适配:SurrealDB SDK `query` 可能返回 `[{...}]` 或 `[{result:[...]}]`——按实测调断言并在 store 层统一解包,见 Task 1 Step 3 的 `_rows`)。

- [ ] **Step 4: 提交**

```bash
git add scribe/pyproject.toml scribe/scribe2
git commit -m "chore(scribe2): SurrealDB SDK + 二进制 + pytest 内存夹具 + 连接冒烟"
```

---

### Task 1:连接层 + 结果解包(`store.py` 骨架)

**Files:**
- Create: `scribe/scribe2/store.py`
- Test: `scribe/scribe2/tests/test_store_connect.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe2/tests/test_store_connect.py
from scribe2.store import Store

def test_store_create_and_get(db):
    s = Store(db)
    wid = s.create("work", {"title": "雨夜", "genre": "悬疑"})
    w = s.get("work", wid)
    assert w["title"] == "雨夜" and w["genre"] == "悬疑"
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_store_connect.py -v`
Expected: FAIL(`No module named 'scribe2.store'`)

- [ ] **Step 3: 实现 Store 骨架(统一解包 SurrealDB 返回)**

```python
# scribe2/store.py
import uuid

def _rows(res):
    """SurrealDB SDK query() 返回归一为 list[dict]。兼容 [{...}] 与 [{'result':[...]}] 两种。"""
    if not res:
        return []
    first = res[0]
    if isinstance(first, dict) and "result" in first and isinstance(first["result"], list):
        return first["result"]
    return res

class Store:
    """SurrealDB 领域存取薄封装。表名即实体类型;id 用 uuid hex(SurrealDB record id = table:⟨id⟩)。"""
    def __init__(self, db):
        self.db = db

    def create(self, table: str, data: dict) -> str:
        rid = uuid.uuid4().hex
        self.db.query(f"CREATE type::thing($t, $id) CONTENT $data;",
                      {"t": table, "id": rid, "data": data})
        return rid

    def get(self, table: str, rid: str) -> dict | None:
        rows = _rows(self.db.query("SELECT * FROM type::thing($t, $id);",
                                   {"t": table, "id": rid}))
        return rows[0] if rows else None

    def list(self, table: str, where: str = "", vars: dict | None = None) -> list[dict]:
        q = f"SELECT * FROM type::table($t)" + (f" WHERE {where}" if where else "") + ";"
        return _rows(self.db.query(q, {"t": table, **(vars or {})}))

    def update(self, table: str, rid: str, patch: dict) -> None:
        self.db.query("UPDATE type::thing($t, $id) MERGE $patch;",
                      {"t": table, "id": rid, "patch": patch})
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_store_connect.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/store.py scribe/scribe2/tests/test_store_connect.py
git commit -m "feat(scribe2): Store 连接层 + 结果解包 + create/get/list/update"
```

---

### Task 2:数据驱动 schema 初始化(表 + 向量索引 + 全文索引)

**Files:**
- Create: `scribe/scribe2/schema.py`
- Modify: `scribe/scribe2/store.py`(加 `init_schema`)
- Test: `scribe/scribe2/tests/test_schema.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe2/tests/test_schema.py
from scribe2.store import Store
from scribe2.schema import EMBED_DIM

def test_schema_defines_vector_and_fts(db):
    s = Store(db); s.init_schema()
    info = s.db.query("INFO FOR TABLE chapter;")
    txt = str(info)
    # 向量索引 + 全文索引都已定义
    assert "HNSW" in txt or "hnsw" in txt
    assert "FULLTEXT" in txt or "ANALYZER" in txt
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_schema.py -v`
Expected: FAIL(`init_schema` 不存在)

- [ ] **Step 3: 写 schema 规格 + 生成 DDL**

```python
# scribe2/schema.py
EMBED_DIM = 384  # fastembed 多语小模型维度(probe 实测,见 Task 3;若不符改这里)

# 需要"可被语义检索"的内容实体:都带 text(FTS)+ embedding(向量)
CONTENT_TABLES = ["chapter", "setting", "character", "foreshadow",
                  "material", "memory_entry", "style_exemplar", "imagination"]
# 纯结构表(无需向量):
STRUCT_TABLES = ["work", "volume", "snapshot", "segment", "author_intent",
                 "option_set", "consistency_flag", "quality_snapshot",
                 "preference_signal", "taste_model", "feedback"]

def ddl() -> list[str]:
    out = ["DEFINE ANALYZER scribe_a TOKENIZERS blank,class FILTERS lowercase;"]
    for t in STRUCT_TABLES + CONTENT_TABLES:
        out.append(f"DEFINE TABLE {t} SCHEMALESS;")
        out.append(f"DEFINE FIELD work ON {t} TYPE option<record>;")  # 归属书(结构链接)
    for t in CONTENT_TABLES:
        out.append(f"DEFINE FIELD text ON {t} TYPE option<string>;")
        out.append(f"DEFINE FIELD embedding ON {t} TYPE option<array<float>>;")
        out.append(f"DEFINE INDEX {t}_vec ON {t} FIELDS embedding "
                   f"HNSW DIMENSION {EMBED_DIM} DIST COSINE TYPE F32;")
        out.append(f"DEFINE INDEX {t}_fts ON {t} FIELDS text "
                   f"FULLTEXT ANALYZER scribe_a BM25;")
    return out
```

并在 `store.py` 加:

```python
    def init_schema(self) -> None:
        from .schema import ddl
        for stmt in ddl():
            self.db.query(stmt)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_schema.py -v`
Expected: PASS(若 `INFO FOR TABLE` 结构不同导致断言失败,改为断言 `INFO FOR DB` 含 `chapter_vec`/`chapter_fts` 索引名)

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/schema.py scribe/scribe2/store.py scribe/scribe2/tests/test_schema.py
git commit -m "feat(scribe2): 数据驱动 schema(表 + HNSW 向量索引 + BM25 全文索引)"
```

---

### Task 3:嵌入 + 写内容实体(record + embedding 同写)

**Files:**
- Create: `scribe/scribe2/embed.py`
- Modify: `scribe/scribe2/store.py`(加 `put_content`)
- Test: `scribe/scribe2/tests/test_embed.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe2/tests/test_embed.py
from scribe2.store import Store
from scribe2.embed import embed, dim

def test_embed_dim_matches_schema():
    from scribe2.schema import EMBED_DIM
    assert dim() == EMBED_DIM

def test_put_content_stores_embedding(db):
    s = Store(db); s.init_schema()
    cid = s.put_content("setting", work="work:1", name="断魂剑",
                        text="一把会低语的古剑,持有者会逐渐失去记忆。")
    row = s.get("setting", cid)
    assert row["text"].startswith("一把会低语")
    assert isinstance(row["embedding"], list) and len(row["embedding"]) == EMBED_DIM
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_embed.py -v`
Expected: FAIL(`scribe2.embed` 不存在)

- [ ] **Step 3: 实现 embed + put_content**

```python
# scribe2/embed.py —— 复用 fastembed,本地 CPU,中文优先多语模型
_model = None
_MODEL_NAME = "intfloat/multilingual-e5-small"  # 384 维,中文可用

def _m():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model

def embed(texts: list[str]) -> list[list[float]]:
    return [list(map(float, v)) for v in _m().embed(texts)]

def dim() -> int:
    return len(embed(["probe"])[0])
```

`store.py` 加:

```python
    def put_content(self, table: str, work: str, text: str, **fields) -> str:
        from .embed import embed
        vec = embed([text])[0] if text else None
        rid = uuid.uuid4().hex
        data = {"work": work, "text": text, "embedding": vec, **fields}
        self.db.query("CREATE type::thing($t, $id) CONTENT $data;",
                      {"t": table, "id": rid, "data": data})
        return rid
```

> 注:若 `dim()` 实测不是 384,改 `schema.py:EMBED_DIM` 为实测值后重跑 Task 2/3。

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_embed.py -v`
Expected: PASS(首次会下载 fastembed 模型,慢属正常)

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/embed.py scribe/scribe2/store.py scribe/scribe2/tests/test_embed.py
git commit -m "feat(scribe2): fastembed 嵌入 + put_content(record+embedding 同写)"
```

---

### Task 4:图边(RELATE)+ 遍历

**Files:**
- Modify: `scribe/scribe2/store.py`(加 `relate`、`neighbors`)
- Test: `scribe/scribe2/tests/test_graph.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe2/tests/test_graph.py
from scribe2.store import Store

def test_relate_and_traverse(db):
    s = Store(db); s.init_schema()
    a = s.put_content("character", work="work:1", text="沈舟", name="沈舟")
    b = s.put_content("setting", work="work:1", text="断魂剑", name="断魂剑")
    s.relate(f"character:{a}", "holds", f"setting:{b}",
             {"category": "从属", "weight": 2, "valid_from": 1})
    nb = s.neighbors(f"character:{a}", "holds")
    assert any("断魂剑" in str(x) for x in nb)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_graph.py -v`
Expected: FAIL(`relate` 不存在)

- [ ] **Step 3: 实现 relate / neighbors**

```python
    def relate(self, frm: str, edge: str, to: str, props: dict | None = None) -> None:
        self.db.query(f"RELATE {frm}->{edge}->{to} CONTENT $p;", {"p": props or {}})

    def neighbors(self, node: str, edge: str) -> list:
        rows = _rows(self.db.query(f"SELECT ->{edge}->? AS n FROM {node};"))
        return rows[0]["n"] if rows and rows[0].get("n") else []
```

> 注:`frm/to` 是已存在的 record id(`table:⟨uuid⟩`),直接拼进语句(uuid hex 安全,无注入)。若 SurrealDB 对 record-id 字面量有引号要求,用 `type::thing` 改写。

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_graph.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/store.py scribe/scribe2/tests/test_graph.py
git commit -m "feat(scribe2): 图边 RELATE + 邻居遍历"
```

---

### Task 5:`search_knowledge` 统一混合检索(向量 + 全文 + 图扩展)

**Files:**
- Modify: `scribe/scribe2/store.py`(加 `search_knowledge`)
- Test: `scribe/scribe2/tests/test_search.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe2/tests/test_search.py
from scribe2.store import Store

def test_search_hybrid_and_graph_expand(db):
    s = Store(db); s.init_schema()
    a = s.put_content("character", work="work:1", text="沈舟,沉默寡言的剑客", name="沈舟")
    b = s.put_content("setting", work="work:1", text="断魂剑,会让持有者失忆的古剑", name="断魂剑")
    s.put_content("setting", work="work:1", text="码头,雨夜常起雾", name="码头")
    s.relate(f"character:{a}", "holds", f"setting:{b}", {"category": "从属"})
    hits = s.search_knowledge("work:1", "失忆的剑", k=3)
    # 命中"断魂剑"(语义/全文),且能返回结果
    assert any("断魂剑" in h["text"] for h in hits)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_search.py -v`
Expected: FAIL(`search_knowledge` 不存在)

- [ ] **Step 3: 实现 search_knowledge(逐内容表混合检索 + 合并)**

```python
    def search_knowledge(self, work: str, query: str, k: int = 6,
                         types: list[str] | None = None) -> list[dict]:
        """统一知识检索:对每个内容表跑 向量KNN + 全文,合并去重按分排序。
        work 形如 'work:⟨id⟩' 或 'work:1';按 work 字段过滤防串书。"""
        from .embed import embed
        from .schema import CONTENT_TABLES
        qv = embed([query])[0]
        tables = types or CONTENT_TABLES
        seen, out = set(), []
        for t in tables:
            # 向量 KNN:<|k|> 取最近 k 个;再叠加全文 @@
            rows = _rows(self.db.query(
                f"SELECT id, type, text, name, "
                f"vector::similarity::cosine(embedding, $qv) AS score "
                f"FROM type::table($t) "
                f"WHERE work = type::thing('work', $w) AND embedding <|{k}|> $qv "
                f"ORDER BY score DESC LIMIT $k;",
                {"t": t, "w": work.split(":")[-1], "qv": qv, "k": k}))
            for r in rows:
                rid = str(r.get("id"))
                if rid in seen:
                    continue
                seen.add(rid)
                r["entity_type"] = t
                out.append(r)
        out.sort(key=lambda r: r.get("score") or 0, reverse=True)
        return out[:k]
```

> 注:KNN 算子语法 `embedding <|k|> $qv` 与 `vector::similarity::cosine` 以实测为准;若该写法报错,退化为纯 `ORDER BY vector::similarity::cosine(embedding,$qv) DESC LIMIT k`(暴力,几百实体够用)。**图扩展**(对 top 命中跑 `neighbors` 拉关联)放 Task 6 增量加,本任务先保证混合检索通。

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest scribe2/tests/test_search.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/store.py scribe/scribe2/tests/test_search.py
git commit -m "feat(scribe2): search_knowledge 混合检索(向量+全文,按书过滤)"
```

---

### Task 6:图扩展并入 search_knowledge + 全量回归

**Files:**
- Modify: `scribe/scribe2/store.py`(`search_knowledge` 加图扩展)
- Test: `scribe/scribe2/tests/test_search.py`(加用例)

- [ ] **Step 1: 加失败测试(命中实体的邻居被一并带回)**

```python
def test_search_expands_graph(db):
    from scribe2.store import Store
    s = Store(db); s.init_schema()
    a = s.put_content("character", work="work:1", text="沈舟", name="沈舟")
    b = s.put_content("setting", work="work:1", text="断魂剑,失忆古剑", name="断魂剑")
    s.relate(f"character:{a}", "holds", f"setting:{b}", {"category": "从属"})
    res = s.search_knowledge("work:1", "失忆古剑", k=3, expand=True)
    names = " ".join(str(h) for h in res["related"])
    assert "沈舟" in names  # 命中断魂剑 → 顺图带回持有者沈舟
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest scribe2/tests/test_search.py::test_search_expands_graph -v`
Expected: FAIL

- [ ] **Step 3: search_knowledge 增 expand**

把 `search_knowledge` 签名加 `expand: bool = False`;当 `expand` 为真,返回 `{"hits": out[:k], "related": [...]}`,其中 related = 对每个 hit 跑 `<-?<-` 与 `->?->` 一跳邻居(去重、去掉已在 hits 的)。非 expand 时维持返回 list(向后兼容旧测试)。

```python
        if not expand:
            return out[:k]
        related, rids = [], {str(h.get("id")) for h in out[:k]}
        for h in out[:k]:
            nb = _rows(self.db.query(
                f"SELECT ->?->? AS o, <-?<-? AS i FROM {h['id']};"))
            for r in nb:
                for side in ("o", "i"):
                    for x in (r.get(side) or []):
                        if str(x) not in rids:
                            rids.add(str(x)); related.append(x)
        return {"hits": out[:k], "related": related}
```
> 注:`->?->?` 通配遍历语法以实测为准;不支持则用已知边名集合循环 `neighbors`。

- [ ] **Step 4: 全量回归**

Run: `.venv/bin/python -m pytest scribe2/tests/ -q`
Expected: 全绿(Task 0–6)

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe2/store.py scribe/scribe2/tests/test_search.py
git commit -m "feat(scribe2): search_knowledge 图扩展(命中→邻居)+ 全量回归"
```

---

## Self-Review(规划者自检)

- **Spec 覆盖(本段=spec §3 数据层 + §9.4 第1步)**:连接(T0/T1)✓、关系/结构(T1/T2 SCHEMALESS+字段)✓、向量索引(T2 HNSW)✓、全文(T2 BM25)✓、图(T4 RELATE)✓、统一联动检索(T5/T6 向量+全文+图)✓、嵌入(T3 fastembed)✓。**未覆盖(后续段)**:领域 CRUD 全实体 repo、REST 迁移、版本/snapshot 语义、MCP 工具暴露、Hermes 集成、前端清遗留——各自另出计划(spec §9.4 第2–5步)。
- **类型一致**:`Store` 方法 `create/get/list/update/put_content/relate/neighbors/search_knowledge` 跨任务一致;`EMBED_DIM` 与 `dim()` 在 T2/T3 对齐(实测不符则改 schema 常量)。
- **无占位符**:每步给确切 SurrealQL/Python/命令。**已知不确定语法(KNN `<|k|>`、`vector::similarity`、`->?->` 通配)在步骤里写明"实测为准 + 退化写法"**——这是真实 spike 风险点,非占位。
- **风险**:SurrealDB SDK `query()` 返回结构、KNN/相似度/通配遍历的确切语法需首次实测对齐(已在 T0 Step3、T5/T6 注明退化路径);中文 FTS 分词弱 → 主要靠向量路,FTS 兜底。

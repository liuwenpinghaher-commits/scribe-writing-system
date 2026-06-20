# Scribe 后端数据支撑增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给关系图谱与质量趋势补足后端数据:关系丰富化(类型/类别/权重/方向)、质量时序表、中文质量指标、批量分析全书入口。全部 additive,不破现有 72 接口契约。

**Architecture:** 复用现有 FastAPI + SQLite + 直连 Hermes 的 `ingest`/`metrics` 模式。schema 增列与建表 + db 幂等迁移;`memory.py` 抽取升级为 typed schema;`metrics.py` 加 `jieba` 中文指标;`api.py` 新增 2 端点。不引入重型 KG 库/图数据库/MCP。

**Tech Stack:** Python 3.13、FastAPI、SQLite(stdlib sqlite3)、jieba(新增)、pytest + FastAPI TestClient。

---

### 约定

- 工作目录:`/Users/miaoma/Downloads/写作 3.0/scribe`
- 跑测试:`.venv/bin/python -m pytest tests/<file>::<test> -v`
- 全量回归:`.venv/bin/python -m pytest tests/ -q`
- 测试用 `Database(":memory:")`(每用例独立)或 `TestClient(app)` + `{"X-Owner-Id": "u1"}`。

---

### Task 1:schema 增列/建表 + 幂等迁移

**Files:**
- Modify: `scribe/schema.sql`(entity_relations 增列;新增 quality_snapshots)
- Modify: `scribe/scribe_mcp/db.py`(`_init_schema` 末尾增幂等 ALTER)
- Test: `scribe/tests/test_data_enhance.py`(新建)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_data_enhance.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def _cols(db, table):
    return {r["name"] for r in db.conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_schema_relation_columns_and_quality_table():
    db = Database(":memory:")
    cols = _cols(db, "entity_relations")
    assert {"src_type", "dst_type", "relation_category", "weight", "directed"} <= cols
    # quality_snapshots 表存在且有关键列
    qcols = _cols(db, "quality_snapshots")
    assert {"work_id", "scope", "chapter_seq", "slop_density", "created_at"} <= qcols
```

- [ ] **Step 2: 运行,确认失败**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_schema_relation_columns_and_quality_table -v`
Expected: FAIL(`src_type` 不在列中 / `quality_snapshots` 无此表)

- [ ] **Step 3: 改 schema.sql**

在 `entity_relations` 定义里、`valid_to_chapter` 行后补 5 列(注意末尾逗号),并在其后新增表:

```sql
-- entity_relations 内,valid_to_chapter 之后新增:
    src_type    TEXT,                -- 角色/地点/阵营/物品/组织/概念
    dst_type    TEXT,
    relation_category TEXT,          -- 亲属/敌对/盟友/师徒/爱慕/从属/因果/其它
    weight      REAL DEFAULT 1.0,    -- 关系强度(出现次数/LLM 估)
    directed    INTEGER DEFAULT 1    -- 是否有向

-- 文件中 entity_relations 块之后新增:
CREATE TABLE IF NOT EXISTS quality_snapshots (
    id          TEXT PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id),
    scope       TEXT NOT NULL,        -- 'global' | 'chapter'
    chapter_seq INTEGER,              -- scope=chapter 时
    words       INTEGER,
    slop_density REAL,
    consistency_score REAL,
    foreshadow_payoff REAL,
    vocab_richness REAL,
    repetition_rate REAL,
    cost_usd    REAL,
    created_at  TEXT NOT NULL
);
```

- [ ] **Step 4: 加幂等迁移(db.py)**

在 `_init_schema` 方法末尾(现有 `ALTER TABLE segments ...` 同款 try/except 之后)追加。已存在的库靠 ALTER 补列;新库 schema.sql 已含,ALTER 会报错被吞:

```python
        for col, ddl in [
            ("src_type", "ALTER TABLE entity_relations ADD COLUMN src_type TEXT"),
            ("dst_type", "ALTER TABLE entity_relations ADD COLUMN dst_type TEXT"),
            ("relation_category", "ALTER TABLE entity_relations ADD COLUMN relation_category TEXT"),
            ("weight", "ALTER TABLE entity_relations ADD COLUMN weight REAL DEFAULT 1.0"),
            ("directed", "ALTER TABLE entity_relations ADD COLUMN directed INTEGER DEFAULT 1"),
        ]:
            try:
                self.conn.execute(ddl)
            except Exception:
                pass  # 列已存在
        self.conn.commit()
```

- [ ] **Step 5: 运行,确认通过**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_schema_relation_columns_and_quality_table -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add scribe/schema.sql scribe/scribe_mcp/db.py scribe/tests/test_data_enhance.py
git commit -m "feat(db): entity_relations 增列 + quality_snapshots 表 + 幂等迁移"
```

---

### Task 2:add_relation 增字段 + 去重累加

**Files:**
- Modify: `scribe/scribe_mcp/db.py:518-525`(`add_relation`)
- Test: `scribe/tests/test_data_enhance.py`

- [ ] **Step 1: 写失败测试**

```python
def test_add_relation_typed_and_dedup():
    db = Database(":memory:")
    w = db.create_work("u", "书")
    db.add_relation(w, "沈舟", "断魂剑", "持有", valid_from=1,
                    src_type="角色", dst_type="物品", category="从属", weight=1.0)
    # 同 (src,dst,relation) 再来一次 → 累加 weight,不新增行
    db.add_relation(w, "沈舟", "断魂剑", "持有", valid_from=2,
                    src_type="角色", dst_type="物品", category="从属")
    rels = db.list_relations(w)
    assert len(rels) == 1
    r = rels[0]
    assert r["src_type"] == "角色" and r["dst_type"] == "物品"
    assert r["relation_category"] == "从属"
    assert r["weight"] == 2.0
```

- [ ] **Step 2: 运行,确认失败**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_add_relation_typed_and_dedup -v`
Expected: FAIL(`add_relation()` 不接受 `src_type` 等关键字 / weight 非 2.0)

- [ ] **Step 3: 替换 add_relation 实现**

```python
    def add_relation(self, work_id: str, src: str, dst: str, relation: str,
                     valid_from: int | None = None, src_type: str | None = None,
                     dst_type: str | None = None, category: str | None = None,
                     weight: float = 1.0, directed: int = 1) -> str:
        existing = self.conn.execute(
            "SELECT id, weight FROM entity_relations WHERE work_id=? AND src_entity=? "
            "AND dst_entity=? AND relation=?", (work_id, src, dst, relation)).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE entity_relations SET weight=?, valid_from_chapter=COALESCE(valid_from_chapter, ?) "
                "WHERE id=?", ((existing["weight"] or 1.0) + 1.0, valid_from, existing["id"]))
            self.conn.commit()
            return existing["id"]
        rid = _id()
        self.conn.execute(
            "INSERT INTO entity_relations(id,work_id,src_entity,dst_entity,relation,"
            "valid_from_chapter,src_type,dst_type,relation_category,weight,directed) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (rid, work_id, src, dst, relation, valid_from, src_type, dst_type, category, weight, directed))
        self.conn.commit()
        return rid
```

- [ ] **Step 4: 运行,确认通过**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_add_relation_typed_and_dedup -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe_mcp/db.py scribe/tests/test_data_enhance.py
git commit -m "feat(db): add_relation 支持类型/类别/权重/方向 + 去重累加"
```

---

### Task 3:ingest 抽取 typed 关系

**Files:**
- Modify: `scribe/scribe_mcp/memory.py`(`build_ingest_prompt` 关系段、`parse_ingest`、`ingest_chapter` 的 add_relation 调用)
- Test: `scribe/tests/test_data_enhance.py`

- [ ] **Step 1: 写失败测试**

```python
from scribe_mcp.memory import parse_ingest  # 顶部 import 区


def test_parse_ingest_typed_relations_with_defaults():
    # 含新字段
    full = '{"summary":"s","relations":[{"src":"沈舟","dst":"断魂剑","relation":"持有",' \
           '"src_type":"角色","dst_type":"物品","category":"从属","directed":1}]}'
    r = parse_ingest(full)["relations"][0]
    assert r["src_type"] == "角色" and r["category"] == "从属"
    # 缺新字段 → 补默认,不丢条
    bare = '{"relations":[{"src":"A","dst":"B","relation":"敌对"}]}'
    r2 = parse_ingest(bare)["relations"][0]
    assert r2["src_type"] == "未知" and r2["category"] == "其它" and r2["directed"] == 1
```

- [ ] **Step 2: 运行,确认失败**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_parse_ingest_typed_relations_with_defaults -v`
Expected: FAIL(`KeyError: 'src_type'`)

- [ ] **Step 3: 改 memory.py**

(a) `build_ingest_prompt` 里关系示例那行改成带类型:

```python
        '"relations":[{"src":"实体A","dst":"实体B","relation":"关系(如 师徒/敌对/结盟)",'
        '"src_type":"角色/地点/阵营/物品/组织/概念","dst_type":"同前","category":"亲属/敌对/盟友/师徒/爱慕/从属/因果/其它","directed":1}]}。\n'
```

(b) `parse_ingest` 的 relations 循环替换为(补默认值):

```python
    for r in d.get("relations") or []:
        if isinstance(r, dict) and r.get("src") and r.get("dst") and r.get("relation"):
            out["relations"].append({
                "src": str(r["src"]), "dst": str(r["dst"]), "relation": str(r["relation"])[:40],
                "src_type": str(r.get("src_type") or "未知")[:10],
                "dst_type": str(r.get("dst_type") or "未知")[:10],
                "category": str(r.get("category") or "其它")[:10],
                "directed": 1 if r.get("directed", 1) else 0,
            })
```

(c) `ingest_chapter` 里 add_relation 调用传新字段:

```python
    for r in data["relations"]:
        db.add_relation(work_id, r["src"], r["dst"], r["relation"], valid_from=seq,
                        src_type=r["src_type"], dst_type=r["dst_type"], category=r["category"],
                        directed=r["directed"])
        cnt["relations"] += 1
```

- [ ] **Step 4: 运行,确认通过**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_parse_ingest_typed_relations_with_defaults -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe_mcp/memory.py scribe/tests/test_data_enhance.py
git commit -m "feat(ingest): 关系抽取升级为 typed schema(类型/类别/方向 + 默认值)"
```

---

### Task 4:jieba 中文质量指标

**Files:**
- Modify: `scribe/pyproject.toml`(deps 加 `jieba`)
- Modify: `scribe/scribe_mcp/metrics.py`(新增 `vocab_richness`、`repetition_rate`;并入 `chapter_quality`)
- Test: `scribe/tests/test_data_enhance.py`

- [ ] **Step 1: 装依赖**

Run: `.venv/bin/pip install jieba` 并在 `pyproject.toml` 的 `[project] dependencies` 增 `"jieba"`。
Expected: 安装成功;`.venv/bin/python -c "import jieba"` 无报错。

- [ ] **Step 2: 写失败测试**

```python
def test_chinese_quality_metrics():
    from scribe_mcp.metrics import vocab_richness, repetition_rate
    # 全不同词 → 丰富度高、重复低
    rich = "晨光 落在 窗台 猫咪 伸懒腰 茶香 漫开"
    assert vocab_richness(rich) > 0.8
    # 大量重复 → 丰富度低、重复率高
    rep = "走 走 走 走 走 走 走 走"
    assert vocab_richness(rep) < 0.3
    assert repetition_rate(rep) > 0.5
```

- [ ] **Step 3: 运行,确认失败**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_chinese_quality_metrics -v`
Expected: FAIL(`cannot import name 'vocab_richness'`)

- [ ] **Step 4: 实现 metrics.py 中文指标**

```python
import jieba  # 文件顶部

def _tokens(text: str) -> list[str]:
    return [t for t in jieba.lcut(text or "") if t.strip()]

def vocab_richness(text: str) -> float:
    """词汇丰富度(type-token ratio):去重词数 / 总词数。越高越不啰嗦。"""
    toks = _tokens(text)
    return round(len(set(toks)) / len(toks), 3) if toks else 0.0

def repetition_rate(text: str) -> float:
    """重复率:重复 bigram 占比(AI 腔强信号)。"""
    toks = _tokens(text)
    if len(toks) < 2:
        return 0.0
    bigrams = list(zip(toks, toks[1:]))
    from collections import Counter
    c = Counter(bigrams)
    repeated = sum(n for n in c.values() if n > 1)
    return round(repeated / len(bigrams), 3)
```

并入 `chapter_quality` 的返回 dict(在现有字段后追加):

```python
    text = snaps[-1]["content"] if snaps else ""
    # ...现有 return 改为增两字段:
    return {"seq": seq, "words": len(text), "slop_density": round(slop_density(text), 2),
            "open_flags": len(flags),
            "vocab_richness": vocab_richness(text), "repetition_rate": repetition_rate(text)}
```

- [ ] **Step 5: 运行,确认通过**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_chinese_quality_metrics -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add scribe/pyproject.toml scribe/scribe_mcp/metrics.py scribe/tests/test_data_enhance.py
git commit -m "feat(metrics): jieba 中文质量指标(词汇丰富度/重复率)"
```

---

### Task 5:quality_snapshots db 方法

**Files:**
- Modify: `scribe/scribe_mcp/db.py`(新增 `add_quality_snapshot`、`list_quality_snapshots`)
- Test: `scribe/tests/test_data_enhance.py`

- [ ] **Step 1: 写失败测试**

```python
def test_quality_snapshot_add_list():
    db = Database(":memory:")
    w = db.create_work("u", "书")
    db.add_quality_snapshot(w, "global", None, {"words": 1200, "slop_density": 0.8,
        "consistency_score": 0.9, "foreshadow_payoff": 0.5, "vocab_richness": 0.7,
        "repetition_rate": 0.1, "cost_usd": 0.02})
    db.add_quality_snapshot(w, "chapter", 1, {"words": 600, "slop_density": 1.2})
    g = db.list_quality_snapshots(w, "global")
    assert len(g) == 1 and g[0]["words"] == 1200
    c = db.list_quality_snapshots(w, "chapter")
    assert len(c) == 1 and c[0]["chapter_seq"] == 1
```

- [ ] **Step 2: 运行,确认失败**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_quality_snapshot_add_list -v`
Expected: FAIL(`'Database' object has no attribute 'add_quality_snapshot'`)

- [ ] **Step 3: 实现 db 方法**

```python
    def add_quality_snapshot(self, work_id: str, scope: str, chapter_seq: int | None,
                             metrics: dict) -> str:
        sid = _id()
        self.conn.execute(
            "INSERT INTO quality_snapshots(id,work_id,scope,chapter_seq,words,slop_density,"
            "consistency_score,foreshadow_payoff,vocab_richness,repetition_rate,cost_usd,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (sid, work_id, scope, chapter_seq, metrics.get("words"), metrics.get("slop_density"),
             metrics.get("consistency_score"), metrics.get("foreshadow_payoff"),
             metrics.get("vocab_richness"), metrics.get("repetition_rate"),
             metrics.get("cost_usd"), _now()))
        self.conn.commit()
        return sid

    def list_quality_snapshots(self, work_id: str, scope: str | None = None) -> list[dict]:
        q = "SELECT * FROM quality_snapshots WHERE work_id=?"
        p: list = [work_id]
        if scope:
            q += " AND scope=?"; p.append(scope)
        q += " ORDER BY created_at ASC"
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]
```

- [ ] **Step 4: 运行,确认通过**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_quality_snapshot_add_list -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe_mcp/db.py scribe/tests/test_data_enhance.py
git commit -m "feat(db): quality_snapshots 增删查方法"
```

---

### Task 6:落快照 + GET /quality/history

**Files:**
- Modify: `scribe/scribe_mcp/api.py`(在 ingest 端点后写 global 快照;新增 `GET /works/{id}/quality/history`)
- Test: `scribe/tests/test_data_enhance.py`

- [ ] **Step 1: 写失败测试**(TestClient + monkeypatch 避免真连 Hermes)

```python
def test_quality_history_endpoint(monkeypatch):
    import scribe_mcp.api as api
    from fastapi.testclient import TestClient
    client = TestClient(api.app); U = {"X-Owner-Id": "u1"}
    w = client.post("/works", json={"title": "趋势书"}, headers=U).json()["work_id"]
    # 直接落两笔 global 快照(模拟多次修订)
    api.db.add_quality_snapshot(w, "global", None, {"words": 500, "slop_density": 1.5})
    api.db.add_quality_snapshot(w, "global", None, {"words": 1200, "slop_density": 0.9})
    hist = client.get(f"/works/{w}/quality/history?scope=global", headers=U).json()
    assert len(hist) == 2 and hist[0]["words"] == 500 and hist[1]["words"] == 1200
```

- [ ] **Step 2: 运行,确认失败**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_quality_history_endpoint -v`
Expected: FAIL(404,history 端点不存在)

- [ ] **Step 3: 加端点(api.py,放在 `quality_report` 函数之后)**

```python
@app.get("/works/{work_id}/quality/history")
def quality_history(work_id: str, scope: str = "global",
                    x_owner_id: str | None = Header(default=None)):
    """C6-2 质量时序:随修订/时间累积的快照,供前端趋势图。"""
    _own_work(work_id, _owner(x_owner_id))
    return db.list_quality_snapshots(work_id, scope)
```

并在 ingest 端点(`ingest_chapter_ep`,api.py:827 一带)落一笔 global 快照——把 return 改为:

```python
    from .metrics import work_quality_report
    res = ingest_chapter(db, _volc_complete, work_id, seq)
    rep = work_quality_report(db, work_id)
    db.add_quality_snapshot(work_id, "global", None, {
        "words": rep["words"], "slop_density": rep["avg_slop_density"],
        "consistency_score": rep["consistency"]["score"],
        "foreshadow_payoff": rep["foreshadow"]["payoff_rate"],
        "cost_usd": _LEDGER.total_cost(work_id)["cost_usd"]})
    return res
```

- [ ] **Step 4: 运行,确认通过**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_quality_history_endpoint -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scribe/scribe_mcp/api.py scribe/tests/test_data_enhance.py
git commit -m "feat(api): GET /quality/history + ingest 落质量快照"
```

---

### Task 7:POST /analyze 批量分析(幂等)

**Files:**
- Modify: `scribe/scribe_mcp/db.py`(新增 `clear_chapter_extractions`)
- Modify: `scribe/scribe_mcp/api.py`(新增 `POST /works/{id}/analyze`)
- Test: `scribe/tests/test_data_enhance.py`

- [ ] **Step 1: 写失败测试**(monkeypatch `_volc_complete` 返回固定 JSON)

```python
def test_analyze_idempotent(monkeypatch):
    import scribe_mcp.api as api
    from fastapi.testclient import TestClient
    client = TestClient(api.app); U = {"X-Owner-Id": "u1"}
    w = client.post("/works", json={"title": "分析书"}, headers=U).json()["work_id"]
    client.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=U)
    client.post(f"/works/{w}/chapters/1/prose", json={"content": "沈舟握紧断魂剑。", "lock": True}, headers=U)
    fake = '{"summary":"沈舟登场","relations":[{"src":"沈舟","dst":"断魂剑","relation":"持有",' \
           '"src_type":"角色","dst_type":"物品","category":"从属"}],"timeline":[],"char_states":[]}'
    monkeypatch.setattr(api, "_volc_complete", lambda *a, **k: fake)
    r1 = client.post(f"/works/{w}/analyze", headers=U).json()
    assert r1["analyzed"] >= 1
    r2 = client.post(f"/works/{w}/analyze", headers=U).json()  # 重跑
    # 幂等:关系不翻倍(去重累加 weight,行数仍 1)
    rels = client.get(f"/works/{w}/relations", headers=U).json()
    assert len(rels) == 1
```

- [ ] **Step 2: 运行,确认失败**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_analyze_idempotent -v`
Expected: FAIL(404,analyze 端点不存在)

- [ ] **Step 3: db.clear_chapter_extractions**

```python
    def clear_chapter_extractions(self, work_id: str, seq: int) -> None:
        """重跑前清理该章既有时间线/角色状态/关系,避免重复堆积(关系按 valid_from 清)。"""
        self.conn.execute("DELETE FROM timeline_events WHERE work_id=? AND chapter_seq=?", (work_id, seq))
        self.conn.execute(
            "DELETE FROM char_states WHERE chapter_seq=? AND character_id IN "
            "(SELECT id FROM characters WHERE work_id=?)", (seq, work_id))
        self.conn.execute("DELETE FROM entity_relations WHERE work_id=? AND valid_from_chapter=?", (work_id, seq))
        self.conn.commit()
```

- [ ] **Step 4: api.py 端点**

```python
@app.post("/works/{work_id}/analyze")
def analyze_work(work_id: str, x_owner_id: str | None = Header(default=None)):
    """批量分析全书:逐章清理→ingest(摘要/关系/时间线/状态)→落质量快照。幂等。"""
    from .memory import ingest_chapter
    from .metrics import work_quality_report
    _own_work(work_id, _owner(x_owner_id))
    chs = db.list_chapters(work_id)
    cnt = {"analyzed": 0, "relations": 0, "events": 0, "states": 0}
    for c in chs:
        db.clear_chapter_extractions(work_id, c["seq"])
        res = ingest_chapter(db, _volc_complete, work_id, c["seq"])
        if res.get("ok"):
            cnt["analyzed"] += 1
            cnt["relations"] += res.get("relations", 0)
            cnt["events"] += res.get("timeline", 0)
            cnt["states"] += res.get("char_states", 0)
    rep = work_quality_report(db, work_id)
    db.add_quality_snapshot(work_id, "global", None, {
        "words": rep["words"], "slop_density": rep["avg_slop_density"],
        "consistency_score": rep["consistency"]["score"],
        "foreshadow_payoff": rep["foreshadow"]["payoff_rate"],
        "cost_usd": _LEDGER.total_cost(work_id)["cost_usd"]})
    return cnt
```

- [ ] **Step 5: 运行,确认通过**

Run: `.venv/bin/python -m pytest tests/test_data_enhance.py::test_analyze_idempotent -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add scribe/scribe_mcp/db.py scribe/scribe_mcp/api.py scribe/tests/test_data_enhance.py
git commit -m "feat(api): POST /analyze 批量分析全书(幂等)+ clear_chapter_extractions"
```

---

### Task 8:全量回归 + __main__ runner

**Files:**
- Modify: `scribe/tests/test_data_enhance.py`(底部加 runner,与 test_agent_tables 同款)

- [ ] **Step 1: 加 runner**

```python
if __name__ == "__main__":
    test_schema_relation_columns_and_quality_table()
    test_add_relation_typed_and_dedup()
    test_parse_ingest_typed_relations_with_defaults()
    test_quality_snapshot_add_list()
    print("  ✓ data-enhance(纯 db/解析)通过")
```

- [ ] **Step 2: 全量回归**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: 全绿(含既有 test_api / test_metrics / test_orchestrator / test_agent_tables)。

- [ ] **Step 3: 提交**

```bash
git add scribe/tests/test_data_enhance.py
git commit -m "test: data-enhance runner + 全量回归通过"
```

---

## Self-Review(规划者自检)

- **Spec 覆盖**:关系丰富化(T1-T3)✓、质量时序(T1/T5/T6)✓、中文质量指标(T4)✓、批量分析(T7)✓、幂等(T7)✓、additive 不破契约(全程只增列/增端点)✓。
- **类型一致**:`add_relation(... src_type,dst_type,category,weight,directed)` 在 T2 定义,T3/T7 同名调用 ✓;`add_quality_snapshot(work_id,scope,chapter_seq,metrics)` 在 T5 定义,T6/T7 同签名 ✓;`vocab_richness/repetition_rate` 在 T4 定义并被 metrics 复用 ✓。
- **无占位符**:每步均含可运行代码与命令 ✓。
- **风险**:`_volc_complete` 真连 Hermes → 测试一律 monkeypatch;`/analyze` 真实调用成本由"显式动作"承担(spec §4 已注明,可后续改后台任务)。

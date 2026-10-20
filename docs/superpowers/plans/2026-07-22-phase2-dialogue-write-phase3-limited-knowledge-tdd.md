# Phase 2 对话写工具面 + Phase 3 限知结构闭环 · TDD 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让「对话 → 审批 → 结构落库」在 MCP 上可走通（无表单也能养书骨架），并让限知账本在真库上由事件结构自动派生（`effects` + `see_event`），同时堵住 hybrid 时间门与 WRITE_GATED 漏登。

**Architecture:** Store 层已有 `add_volume` / `create_chapter` / `update_chapter_meta` / `set_intent` / `set_char_anchors`；本计划只把它们接到 MCP 的 `commit_if_approved` + Hermes write include，并改 ingest/`add_event` 接线。前端只读与 WriteProposal 卡放在 Phase 2 后半，**工具先于 UI**。Phase 3 不换库、不引入 GBrain。

**Tech Stack:** Python 3 + pytest（`scribe3/.venv`）、SurrealDB memory fixture（`conftest`）、FastMCP `scribe3/mcp.py`、`store/chapters|events|recall|facts_knowledge`、可选 vitest 前端 flag。

**上游审查:** `docs/superpowers/plans/2026-07-22-surrealdb-memory-boundary-audit-and-remediation.md`  
**产品铁律:** `设计文档/2026-07-22-对话驱动写入-禁表单直填-决策与改造方案.md`

**明确不在本计划:** 换库、GBrain、全量灭 Codex 表单（仅 flag + 结构 CTA 最小集）、Hermes 大版本升级、批量 WriteProposal 服务端原子事务（可 defer 为「尽最大努力顺序写 + 失败列表」）。

---

## 文件地图

| 路径 | 职责 |
|------|------|
| `scribe3/mcp.py` | 新写工具、WRITE_GATED、author_pref 入闸、fold 统一门控 |
| `scribe3/tests/test_mcp.py` | EXPECTED_WRITE_GATED、结构写工具契约测 |
| `scribe3/tests/test_structure_write_mcp.py` | **新建**：volume/chapter/plan 批准/拒绝/读回 |
| `scribe3/tests/test_gate_invariants.py` | **新建**：commit 名 ⊆ WRITE_GATED AST 不变量 |
| `scribe3/tests/test_hybrid_time_gate.py` | **新建**：hybrid/semantic 时间门 |
| `scribe3/tests/test_see_event_production.py` | **新建**：生产路径 see_event / ingest effects |
| `scribe3/store/recall.py` | hybrid 时间门 |
| `scribe3/store/events.py` | add_event 事务；可选 auto_see_event |
| `scribe3/knowledge.py` | see_event（保持）；可加 `propagate_event_knowledge` 别名 |
| `scribe3/ingest.py` | did→effects；apply 后 see_event |
| `scribe3/deploy/hermes/mcp_servers.yaml` | write include 新工具 |
| `scribe3/tests/test_provision_hermes.py` | 交叉校验自动覆盖新 WRITE_GATED |
| `scribe3/web/src/...` | Phase 2 后半：author_write_via_chief flag（最小） |
| `scribe3/api/app_impl.py` | emergency REST 开关（Phase 2 末） |

**执行顺序总览**

```text
Task 0  基线绿
Task 1  门控不变量 + author_pref 入闸          } 可半天
Task 2  hybrid 时间门                          } 可半天（属 Phase3 但优先）
Task 3  s3_add_volume / s3_patch_volume
Task 4  s3_add_chapter / s3_patch_chapter_meta
Task 5  s3_patch_chapter_plan
Task 6  s3_set_char_anchors
Task 7  hermes yaml + provision 测
Task 8  add_event 事务 + auto see_event
Task 9  ingest effects + 生产 see_event
Task 10 multi-WITNESS 读模型（可独立 PR）
Task 11 graph until_chapter
Task 12 前端只读 flag 最小 + CTA 种子（2B）
Task 13 emergency REST 开关（2D）
```

---

### Task 0: 基线确认（不改功能）

**Files:** 无

- [ ] **Step 1: 跑 MCP 与相关单测，记录基线**

```bash
cd "<repo-root>"
scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q --tb=no
```

Expected: 全绿（或记下既有红项，禁止本计划「顺手修无关」）。

- [ ] **Step 2: 确认 store API 已存在（只读）**

```bash
scribe3/.venv/bin/python -c "
from scribe3.store import SurrealStore
assert hasattr(SurrealStore, 'add_volume')
assert hasattr(SurrealStore, 'update_volume')
assert hasattr(SurrealStore, 'create_chapter')
assert hasattr(SurrealStore, 'update_chapter_meta')
assert hasattr(SurrealStore, 'set_char_anchors')
print('ok')
"
```

Expected: `ok`

---

### Task 1: 门控不变量 + `s3_author_pref_add` 入闸

**Files:**
- Modify: `scribe3/mcp.py`（WRITE_GATED；author_pref；fold 可选）
- Modify: `scribe3/tests/test_mcp.py`（EXPECTED_WRITE_GATED）
- Create: `scribe3/tests/test_gate_invariants.py`
- Modify: `scribe3/tests/test_author_prefs.py`（若存在拒绝测）

- [ ] **Step 1: 写失败测试 — commit 名必须 ⊆ WRITE_GATED**

创建 `scribe3/tests/test_gate_invariants.py`:

```python
"""凡调用 commit_if_approved(name, ...) 的 name 必须 ∈ WRITE_GATED。"""
from __future__ import annotations

import ast
from pathlib import Path

import scribe3.mcp as M

MCP_PATH = Path(M.__file__).resolve()


def _commit_names_from_source() -> set[str]:
    tree = ast.parse(MCP_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "commit_if_approved":
            pass
        elif isinstance(fn, ast.Attribute) and fn.attr == "commit_if_approved":
            pass
        else:
            continue
        if not node.args:
            continue
        arg0 = node.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            names.add(arg0.value)
    return names


def test_all_commit_if_approved_names_are_write_gated():
    used = _commit_names_from_source()
    assert used, "应至少解析到一个 commit_if_approved 调用"
    missing = used - M.WRITE_GATED
    assert not missing, (
        f"commit_if_approved 使用了未入 WRITE_GATED 的工具名: {sorted(missing)}"
    )


def test_author_pref_add_requires_approval():
    assert "s3_author_pref_add" in M.WRITE_GATED
    assert M.requires_approval("s3_author_pref_add") is True
```

- [ ] **Step 2: 跑测确认失败**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_gate_invariants.py -q
```

Expected: FAIL，`s3_author_pref_add` 在 missing 集合（或类似断言）。

- [ ] **Step 3: 最小实现**

在 `scribe3/mcp.py` 的 `WRITE_GATED` 集合中加入 `"s3_author_pref_add"`。

在 `scribe3/tests/test_mcp.py` 的 `EXPECTED_WRITE_GATED` 同步加入。

（可选同 PR）将 `s3_fold_voice_flags` 改为 `return commit_if_approved("s3_fold_voice_flags", ok, lambda: ...)`，删除手写 declined 分支。

- [ ] **Step 4: 补拒绝行为测（author_pref）**

若 `test_author_prefs.py` 无拒绝测，追加：

```python
def test_author_pref_decline_does_not_write(tmp_path, monkeypatch):
    import scribe3.mcp as M
    import scribe3.author_prefs as AP
    pref = tmp_path / "USER.md"
    monkeypatch.setattr(AP, "USER_MD", pref)  # 按实际模块常量名调整
    # 若路径函数不同，monkeypatch append_pref 为记录列表
    calls = []
    out = M.commit_if_approved(
        "s3_author_pref_add", False,
        lambda: calls.append("wrote") or True)
    assert out["status"] == "declined"
    assert calls == []
```

（实现时按 `author_prefs.py` 真实 API 改 monkeypatch 点；原则：`accepted=False` 时 `do_write` 零调用。）

- [ ] **Step 5: 跑测确认通过**

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_gate_invariants.py \
  scribe3/tests/test_mcp.py::test_write_gated_set_no_drift \
  scribe3/tests/test_author_prefs.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scribe3/mcp.py scribe3/tests/test_gate_invariants.py scribe3/tests/test_mcp.py scribe3/tests/test_author_prefs.py
git commit -m "fix(mcp): gate s3_author_pref_add and enforce commit name ⊆ WRITE_GATED"
```

---

### Task 2: `hybrid_recall` 时间门（Phase 3 优先项）

**Files:**
- Modify: `scribe3/store/recall.py`
- Create: `scribe3/tests/test_hybrid_time_gate.py`

- [ ] **Step 1: 写失败测试**

```python
"""hybrid/semantic 不得把 valid_from 晚于 chapter 的命题召回为「当前可用事实」。"""
from __future__ import annotations

from scribe3.ontology import Entity, Fact


def test_hybrid_recall_excludes_future_facts(store, monkeypatch):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:past", "role:甲", "身份", "学徒", valid_from=1))
    store.add_fact(Fact("fact:future", "role:甲", "身份", "掌门", valid_from=100))

    # 避免依赖真实 embed 质量：强制 semantic 返回两命题（若语义索引失败也注入）
    past = store.fact("fact:past")
    future = store.fact("fact:future")
    assert past and future

    def fake_semantic(self, query: str, k: int = 5):
        return [past, future]

    monkeypatch.setattr(type(store), "semantic_recall", fake_semantic, raising=True)

    hits = store.hybrid_recall("身份", chapter=5, k=10)
    ids = {f.id for f in hits}
    assert "fact:past" in ids
    assert "fact:future" not in ids, f"chapter=5 不应含 valid_from=100: {ids}"


def test_semantic_recall_optional_chapter_filter(store, monkeypatch):
    """若实现选择给 semantic_recall 增加 chapter 参数，则同样过滤；
    若保持 API 不变，本测可改为只测 hybrid（删本测）。
    推荐：semantic_recall(query, k=5, chapter=None) — chapter 非空时过滤。
    """
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:p2", "role:乙", "能力", "旧", valid_from=1))
    store.add_fact(Fact("fact:f2", "role:乙", "能力", "新", valid_from=50))
    p2, f2 = store.fact("fact:p2"), store.fact("fact:f2")

    def fake_sem(self, query: str, k: int = 5, chapter=None):
        rows = [p2, f2]
        if chapter is not None:
            rows = [f for f in rows
                    if f.valid_from <= chapter
                    and (f.valid_to is None or f.valid_to > chapter)]
        return rows[:k]

    monkeypatch.setattr(type(store), "semantic_recall", fake_sem, raising=True)
    hits = store.semantic_recall("能力", k=10, chapter=10)
    assert {f.id for f in hits} == {"fact:p2"}
```

- [ ] **Step 2: 跑测确认失败**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_hybrid_time_gate.py::test_hybrid_recall_excludes_future_facts -q
```

Expected: FAIL（future 仍在结果中）。

- [ ] **Step 3: 实现**

改 `scribe3/store/recall.py` 中 `hybrid_recall`：

```python
def hybrid_recall(self, query: str, chapter: int, k: int = 5) -> list[Fact]:
    vector_results = self.semantic_recall(query, k=min(k * 3, 20), chapter=chapter)
    keyword_results = _keyword_search_propositions(self, query, chapter, top_k=k * 2)
    # ... 既有 RRF ...
```

改 `semantic_recall` 签名为 `chapter: int | None = None`，在映射 `Fact` 之前或之后过滤：

```python
if chapter is not None:
    rows = [r for r in rows
            if r.get("valid_from", 0) <= chapter
            and (r.get("valid_to") is None or r.get("valid_to") > chapter)]
```

或在 SurrealQL `WHERE` 增加条件（注意：与 HNSW 组合用后过滤，与底座对表一致——**禁止**依赖 pre-filtered HNSW 正确性）。

`graph_recall` 已有 `valid_from <= $ch`，保持；可选补 `valid_to`。

MCP `s3_hybrid_recall` / `s3_semantic_recall` 透传 chapter（hybrid 已有；semantic 若加参则 MCP 可选）。

- [ ] **Step 4: 跑测**

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_hybrid_time_gate.py \
  scribe3/tests/test_mcp.py::test_mcp_hybrid_recall_masks_secret_by_default \
  scribe3/tests/test_reveal_isolation.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "fix(recall): enforce chapter time gate on hybrid/semantic recall"
```

---

### Task 3: `s3_add_volume` / `s3_patch_volume`

**Files:**
- Modify: `scribe3/mcp.py`
- Create: `scribe3/tests/test_structure_write_mcp.py`（本 Task 起建，后续 Task 追加）
- Modify: `scribe3/tests/test_mcp.py`（EXPECTED_WRITE_GATED）

- [ ] **Step 1: 写失败测试**

`scribe3/tests/test_structure_write_mcp.py`:

```python
from __future__ import annotations

import asyncio
import inspect

import scribe3.mcp as M


def test_volume_tools_in_write_gated():
    assert "s3_add_volume" in M.WRITE_GATED
    assert "s3_patch_volume" in M.WRITE_GATED


def test_s3_add_volume_signatures():
    sig = inspect.signature(M.s3_add_volume)
    for p in ("title", "sort_order", "intro", "work"):
        assert p in sig.parameters


def test_s3_add_volume_decline_blocks(store):
    M.set_store(store)
    before = store.list_volumes()
    out = M.commit_if_approved(
        "s3_add_volume", False,
        lambda: store.add_volume("卷一·不该出现", sort_order=1))
    assert out["status"] == "declined"
    assert store.list_volumes() == before


def test_s3_add_volume_accept_persists(store):
    M.set_store(store)
    out = M.commit_if_approved(
        "s3_add_volume", True,
        lambda: store.add_volume("卷一·潮生", sort_order=0, intro="入世"))
    assert out["status"] == "written"
    vols = store.list_volumes()
    assert any(v.get("title") == "卷一·潮生" for v in vols)


def test_s3_patch_volume_accept_and_missing(store):
    M.set_store(store)
    vid = store.add_volume("旧题", sort_order=0)

    def _patch_ok():
        ok = store.update_volume(vid, {"title": "新题", "intro": "改写"})
        return ok if ok else False

    out = M.commit_if_approved("s3_patch_volume", True, _patch_ok)
    assert out["status"] == "written"
    row = next(v for v in store.list_volumes() if v["id"] == vid)
    assert row["title"] == "新题"

    out2 = M.commit_if_approved(
        "s3_patch_volume", True,
        lambda: store.update_volume("no_such_vol", {"title": "x"}) or False)
    # commit_if_approved: False → status=error
    assert out2["status"] == "error"
```

- [ ] **Step 2: 跑测 FAIL**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_structure_write_mcp.py -q
```

Expected: FAIL（工具不存在 / 未入闸）。

- [ ] **Step 3: 实现 MCP 工具**

在 `mcp.py` 的 WRITE_GATED 加入 `"s3_add_volume", "s3_patch_volume"`。

```python
@mcp.tool(annotations=_RW)
async def s3_add_volume(ctx: Context, title: str, sort_order: int = 0,
                        intro: str | None = None, color: str | None = None,
                        work: str | None = None) -> dict:
    """新建卷(写,待批)。返回 volume 裸 id。"""
    ok = await _ask(ctx, f"新建卷《{title}》sort={sort_order}")
    def _write():
        vid = _store_for(work).add_volume(title, sort_order=sort_order,
                                          intro=intro, color=color)
        return {"volume_id": vid, "title": title}
    return commit_if_approved("s3_add_volume", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_patch_volume(ctx: Context, volume_id: str,
                          title: str | None = None,
                          sort_order: int | None = None,
                          intro: str | None = None,
                          color: str | None = None,
                          work: str | None = None) -> dict:
    """改卷元数据(写,待批)。仅提交非 None 字段。"""
    fields = {k: v for k, v in {
        "title": title, "sort_order": sort_order,
        "intro": intro, "color": color,
    }.items() if v is not None}
    if not fields:
        return {"status": "noop", "tool": "s3_patch_volume", "reason": "no fields"}
    ok = await _ask(ctx, f"改卷 {volume_id}: {list(fields)}")
    def _write():
        st = _store_for(work)
        if not st.update_volume(volume_id, fields):
            return False
        return {"volume_id": volume_id, "fields": list(fields)}
    return commit_if_approved("s3_patch_volume", ok, _write)
```

同步 `EXPECTED_WRITE_GATED`。

- [ ] **Step 4: 跑测 PASS + Commit**

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_structure_write_mcp.py \
  scribe3/tests/test_mcp.py::test_write_gated_set_no_drift \
  scribe3/tests/test_gate_invariants.py -q
```

```bash
git commit -am "feat(mcp): s3_add_volume / s3_patch_volume with approval gate"
```

---

### Task 4: `s3_add_chapter` / `s3_patch_chapter_meta`

**Files:**
- Modify: `scribe3/mcp.py`, `test_mcp.py`, `test_structure_write_mcp.py`

- [ ] **Step 1: 写失败测试（追加到 test_structure_write_mcp.py）**

```python
def test_chapter_tools_in_write_gated():
    assert "s3_add_chapter" in M.WRITE_GATED
    assert "s3_patch_chapter_meta" in M.WRITE_GATED


def test_s3_add_chapter_accept(store):
    M.set_store(store)
    vid = store.add_volume("卷一", sort_order=0)

    def _write():
        return store.create_chapter(title="开篇", volume_id=vid)

    out = M.commit_if_approved("s3_add_chapter", True, _write)
    assert out["status"] == "written"
    chs = store.list_chapters()
    assert any(c.get("title") == "开篇" for c in chs)


def test_s3_add_chapter_decline(store):
    M.set_store(store)
    n0 = len(store.list_chapters())
    out = M.commit_if_approved(
        "s3_add_chapter", False,
        lambda: store.create_chapter(title="幽灵章"))
    assert out["status"] == "declined"
    assert len(store.list_chapters()) == n0


def test_s3_patch_chapter_meta_missing_returns_error(store):
    M.set_store(store)
    out = M.commit_if_approved(
        "s3_patch_chapter_meta", True,
        lambda: store.update_chapter_meta(99999, {"title": "无"}) or False)
    assert out["status"] == "error"


def test_s3_patch_chapter_meta_title_and_label(store):
    M.set_store(store)
    store.save_chapter(1, "正文", title="旧")
    out = M.commit_if_approved(
        "s3_patch_chapter_meta", True,
        lambda: (store.update_chapter_meta(1, {"title": "新题", "label": "主线"}) or False))
    assert out["status"] == "written"
    ch = store.get_chapter(1)
    assert ch["title"] == "新题"
    assert ch.get("label") == "主线"
```

- [ ] **Step 2: FAIL → 实现**

```python
@mcp.tool(annotations=_RW)
async def s3_add_chapter(ctx: Context, title: str = "",
                         volume_id: str | None = None,
                         work: str | None = None) -> dict:
    ok = await _ask(ctx, f"新建章《{title or '未命名'}》vol={volume_id}")
    def _write():
        return _store_for(work).create_chapter(title=title, volume_id=volume_id)
    return commit_if_approved("s3_add_chapter", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_patch_chapter_meta(
    ctx: Context, seq: int,
    title: str | None = None,
    label: str | None = None,
    volume_id: str | None = None,   # 注意: 清空卷需显式协议,见下
    clear_volume: bool = False,
    work: str | None = None,
) -> dict:
    """改章身份元数据(非 plan 内容)。synopsis/beats 走 s3_patch_chapter_plan。"""
    fields = {}
    if title is not None:
        fields["title"] = title
    if label is not None:
        fields["label"] = label
    if clear_volume:
        fields["volume"] = None
    elif volume_id is not None:
        fields["volume"] = volume_id
    if not fields:
        return {"status": "noop", "tool": "s3_patch_chapter_meta", "reason": "no fields"}
    ok = await _ask(ctx, f"改第{seq}章 meta {list(fields)}")
    def _write():
        st = _store_for(work)
        if not st.update_chapter_meta(seq, fields):
            return False
        return {"seq": seq, "fields": list(fields)}
    return commit_if_approved("s3_patch_chapter_meta", ok, _write)
```

写入 `WRITE_GATED` + `EXPECTED_WRITE_GATED`。

- [ ] **Step 3: PASS + Commit**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_structure_write_mcp.py scribe3/tests/test_gate_invariants.py -q
git commit -am "feat(mcp): s3_add_chapter / s3_patch_chapter_meta gated writes"
```

---

### Task 5: `s3_patch_chapter_plan`（synopsis / beats / scene_truth / deductions）

**Files:**
- Modify: `scribe3/mcp.py`, tests

- [ ] **Step 1: 写失败测试**

```python
def test_patch_chapter_plan_in_write_gated():
    assert "s3_patch_chapter_plan" in M.WRITE_GATED


def test_patch_chapter_plan_synopsis_beats(store):
    M.set_store(store)
    store.save_chapter(1, "", title="一")
    beats = [{"text": "沈砚入城"}, {"text": "季棠试探"}]

    def _write():
        ok = store.update_chapter_meta(1, {
            "synopsis": "开篇立人物与潮信",
            "beats": beats,
            "scene_truth": "城门盘查在即",
            "deductions": [{"claim": "潮信与失踪有关"}],
        })
        return ok if ok else False

    out = M.commit_if_approved("s3_patch_chapter_plan", True, _write)
    assert out["status"] == "written"
    ch = store.get_chapter(1)
    assert "潮信" in (ch.get("synopsis") or "")
    assert isinstance(ch.get("beats"), list) and len(ch["beats"]) == 2
    assert "盘查" in (ch.get("scene_truth") or "")


def test_patch_chapter_plan_decline(store):
    M.set_store(store)
    store.save_chapter(1, "", title="一")
    store.update_chapter_meta(1, {"synopsis": "原大纲"})
    out = M.commit_if_approved(
        "s3_patch_chapter_plan", False,
        lambda: store.update_chapter_meta(1, {"synopsis": "不该写入"}) or False)
    assert out["status"] == "declined"
    assert store.get_chapter(1).get("synopsis") == "原大纲"
```

- [ ] **Step 2: 实现**

```python
@mcp.tool(annotations=_RW)
async def s3_patch_chapter_plan(
    ctx: Context, seq: int,
    synopsis: str | None = None,
    beats: list | None = None,
    scene_truth: str | None = None,
    deductions: list | None = None,
    involved_characters: list | None = None,
    work: str | None = None,
) -> dict:
    """改章阶段内容:大纲/节拍/场景真相/演绎(写,待批)。不改 prose。"""
    fields = {}
    if synopsis is not None:
        fields["synopsis"] = synopsis
    if beats is not None:
        fields["beats"] = beats
    if scene_truth is not None:
        fields["scene_truth"] = scene_truth
    if deductions is not None:
        fields["deductions"] = deductions
    if involved_characters is not None:
        fields["involved_characters"] = involved_characters
    if not fields:
        return {"status": "noop", "tool": "s3_patch_chapter_plan", "reason": "no fields"}
    ok = await _ask(ctx, f"改第{seq}章 plan {list(fields.keys())}")
    def _write():
        if not _store_for(work).update_chapter_meta(seq, fields):
            return False
        return {"seq": seq, "fields": list(fields.keys())}
    return commit_if_approved("s3_patch_chapter_plan", ok, _write)
```

- [ ] **Step 3: PASS + Commit**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_structure_write_mcp.py -q
git commit -am "feat(mcp): s3_patch_chapter_plan for synopsis/beats/scene_truth"
```

---

### Task 6: `s3_set_char_anchors`

**Files:**
- Modify: `scribe3/mcp.py`, tests

- [ ] **Step 1: 测试**

```python
def test_set_char_anchors_gated_and_persists(store):
    from scribe3.ontology import Entity
    M.set_store(store)
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    assert "s3_set_char_anchors" in M.WRITE_GATED

    def _write():
        store.set_char_anchors("role:沈砚", {
            "want": "查明潮信",
            "lie": "潮信只是气象",
            "arc_type": "disillusionment",
        })
        return {"character_id": "role:沈砚"}

    out = M.commit_if_approved("s3_set_char_anchors", True, _write)
    assert out["status"] == "written"
    a = store.char_anchors("role:沈砚")
    assert a.get("want") == "查明潮信"
    assert "气象" in (a.get("lie") or "")
```

- [ ] **Step 2: 实现**（参数与 `set_char_anchors` 白名单字段对齐，见 `characters.py`）

```python
@mcp.tool(annotations=_RW)
async def s3_set_char_anchors(
    ctx: Context, character_id: str,
    want: str | None = None, need: str | None = None,
    lie: str | None = None, ghost: str | None = None,
    arc_type: str | None = None,
    # 其余以 store 白名单为准，实现时对照 set_char_anchors
    work: str | None = None,
) -> dict:
    anchors = {k: v for k, v in {
        "want": want, "need": need, "lie": lie,
        "ghost": ghost, "arc_type": arc_type,
    }.items() if v is not None}
    if not anchors:
        return {"status": "noop", "tool": "s3_set_char_anchors", "reason": "no fields"}
    ok = await _ask(ctx, f"设弧光锚 {character_id}: {list(anchors)}")
    def _write():
        _store_for(work).set_char_anchors(character_id, anchors)
        return {"character_id": character_id, "keys": list(anchors)}
    return commit_if_approved("s3_set_char_anchors", ok, _write)
```

- [ ] **Step 3: PASS + Commit**

```bash
git commit -am "feat(mcp): s3_set_char_anchors gated write"
```

---

### Task 7: Hermes write include + provision 交叉

**Files:**
- Modify: `scribe3/deploy/hermes/mcp_servers.yaml`
- 依赖: `test_provision_hermes.py`（已有 `WRITE_GATED <= write_inc`）

- [ ] **Step 1: 跑 provision 测（预期 FAIL 缺新工具）**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_provision_hermes.py -q
```

Expected: FAIL，缺 `s3_add_volume` 等。

- [ ] **Step 2: 把 Task 3–6 全部新写工具名加入 `scribe3_write.tools.include`**

至少：

```yaml
      - s3_add_volume
      - s3_patch_volume
      - s3_add_chapter
      - s3_patch_chapter_meta
      - s3_patch_chapter_plan
      - s3_set_char_anchors
      - s3_author_pref_add   # 若尚未在列表
```

（完整列表以当时 `WRITE_GATED` 为准；`test_provision_hermes` 要求 **WRITE_GATED ⊆ include**。）

- [ ] **Step 3: PASS**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_provision_hermes.py -q
git commit -am "chore(hermes): expose structure write tools on scribe3_write"
```

---

### Task 8: `add_event` 事务 + 可选自动 `see_event`

**Files:**
- Modify: `scribe3/store/events.py`
- Create: `scribe3/tests/test_see_event_production.py`（本 Task 起）

- [ ] **Step 1: 写测试 — 带 effects 的 add_event 后目击者有知识边**

```python
from scribe3.ontology import Entity, Event, Fact
from scribe3.knowledge import project_frame


def test_add_event_with_effects_grants_witness_knowledge(store):
    """生产路径: add_event 写入 causes 后应自动(或显式 propagate)让在场者知道 effects。
    本测禁止手调 see_event——只调 store API。
    """
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:secret_act", "role:甲", "行动", "偷了铜钥", valid_from=2))
    store.add_event(Event(
        "ev:e1", "theft",
        participants={"SUBJ": "role:甲", "WITNESS": "role:乙"},
        effects=["fact:secret_act"],
        story_time=2,
    ))
    # 实现约定: add_event(..., propagate_knowledge=True) 默认 True
    # 或 add_event 末尾总是 propagate
    frame_b = project_frame(store, "role:乙", 2)
    assert frame_b.knows("fact:secret_act"), "目击者乙应知道 effect"
    frame_a = project_frame(store, "role:甲", 2)
    assert frame_a.knows("fact:secret_act"), "当事人甲应知道 effect"


def test_add_event_no_effects_no_spurious_edges(store):
    store.add_entity(Entity("role:丙", "character", "丙"))
    store.add_event(Event(
        "ev:e2", "travel",
        participants={"SUBJ": "role:丙"},
        effects=[],
        story_time=1,
    ))
    edges = [e for e in store.load_knowledge() if e.knower_id == "role:丙"]
    assert edges == []
```

- [ ] **Step 2: FAIL → 实现**

在 `events.py` `add_event` 末尾（写完边之后）:

```python
        # 结构限知:看见即知道
        if getattr(ev, "effects", None):
            from scribe3.knowledge import see_event
            see_event(self, ev)  # SurrealStore 鸭子兼容 add_knowledge
```

并用 `transaction()` 包裹 event + edges + knowledge 写入（若 `see_event` 多次 `add_knowledge`，应在同一 transaction 上下文内调用 `add_event` 的写，或：

```python
with self.transaction():
    # 原 CREATE event + RELATE loops 改为走 _execute_write 收集
    ...
    if ev.effects:
        see_event(self, ev)
```

注意：`transaction()` 只拦截 `_execute_write`；`see_event`→`add_knowledge` 已走 `_execute_write`，可一并收集。

**半失败测（可选加强）:** mock 第二次 RELATE 抛错，断言 event 行不存在（需事务支持）。

- [ ] **Step 3: 既有 MCP `s3_add_event` 集成**

若 MCP 已传 effects，批准后应自动有 knows：

```python
def test_s3_add_event_effects_propagate_via_store(store):
    # 直接 store 路径已在上测；此处保证 MCP 写路径同样走 add_event
    from scribe3.ontology import Entity, Fact
    M.set_store(store)
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:x", "role:甲", "物", "铜钥", valid_from=1))
    # 用 commit 包装 store.add_event 模拟批准
    from scribe3.ontology import Event
    out = M.commit_if_approved(
        "s3_add_event", True,
        lambda: store.add_event(Event(
            "ev:mcp1", "reveal",
            participants={"SUBJ": "role:甲", "WITNESS": "role:乙"},
            effects=["fact:x"], story_time=1)))
    assert out["status"] == "written"
    assert project_frame(store, "role:乙", 1).knows("fact:x")
```

- [ ] **Step 4: PASS + Commit**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_see_event_production.py scribe3/tests/test_ontology.py -q
git commit -am "feat(events): transactional add_event auto-propagates see_event knowledge"
```

---

### Task 9: ingest 写 `effects` + 生产 `see_event`（禁手调）

**Files:**
- Modify: `scribe3/ingest.py`
- Modify: `scribe3/tests/test_see_event_production.py`
- 可能: `scribe3/tests/test_ingest.py` 回归

- [ ] **Step 1: 写失败测试**

```python
def test_apply_delta_did_sets_effects_and_witness_knows(store):
    """ingest apply_delta: did 产生的 fact 应进事件 effects；seen_by/participants 目击者应有 knows。
    不调用 see_event()。
    """
    from scribe3.ontology import Entity
    from scribe3.ingest import apply_delta  # 确认实际导出符号
    from scribe3.knowledge import project_frame

    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    # 按 apply_delta 真实 schema 构造最小 delta
    # 常见形态（实现时对照 ingest.apply_delta / parse_knowledge_delta）:
    delta = {
        "learned": [],
        "did": [{
            "who": "甲",
            "action": "偷走铜钥",
            "fact": "甲偷了铜钥",  # 若字段名不同，按源码改
            "seen_by": ["乙"],
        }],
        "events": [{
            "type": "theft",
            "participants": {"SUBJ": "甲", "WITNESS": "乙"},
            "goal": "得钥",
            "caused_by": [],
        }],
        "voice_shift": [],
    }
    # 若 events 与 did 分轨：实现必须把 did 生成的 fact id 链到同章 event.effects
    apply_delta(store, seq=3, delta=delta)  # 签名以源码为准

    facts = store.facts_at(3)
    assert any("铜钥" in f.value for f in facts), "did 应落命题"
    # 目击者帧
    assert any(
        project_frame(store, "role:乙", 3).knows(f.id)
        for f in facts if "铜钥" in f.value
    ), "乙应通过结构路径知道 did 事实"

    evs = store.events_at(3)
    assert evs, "应有事件"
    assert any(ev.effects for ev in evs), "事件应挂 effects→causes"
```

**实现前必读：** `ingest.py` 中 `apply_delta` 的真实字段名（`did`/`events` 键）。上表是契约意图；写测时用一次 `rg -n "def apply_delta" -A 80 scribe3/ingest.py` 对齐字段，**禁止臆造键名进生产代码**。

- [ ] **Step 2: 实现策略（契约）**

1. 对每条 `did`：创建 proposition（若尚未有）得到 `fact_id`。  
2. 对本章对应 `events[k]`：`effects.append(fact_id)`，再 `add_event`（现已 auto see_event）。  
3. 若仅有 `did` 无 events：合成最小 event（type=`action`，participants 从 who/seen_by 建）**或** 对 `seen_by` 直接 `add_knowledge(..., acquired_via="saw")` 并测保证帧正确。  
4. 与 LLM `seen_by` / `learned` 去重：同一 (knower, prop) 已存在则不再 RELATE。  
5. 保持 `purge_ingest` 幂等：effects/knows 带 `ingest_seq`。

- [ ] **Step 3: 跑 ingest 相关测**

```bash
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_see_event_production.py \
  scribe3/tests/test_ingest.py \
  scribe3/tests/test_ingest_idempotency.py -q
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(ingest): wire did/effects into events and structural see_event"
```

---

### Task 10: 多目击者 participants（可选独立 PR）

**Files:**
- Modify: `scribe3/ontology.py`（Event.participants 类型）
- Modify: `scribe3/store/events.py`（读回）
- Modify: `scribe3/knowledge.py`（`witnesses_of`）
- Tests: `test_see_event_production.py`

- [ ] **Step 1: 测试**

```python
def test_multiple_witnesses_same_slot(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_entity(Entity("role:丙", "character", "丙"))
    store.add_fact(Fact("fact:y", "role:甲", "言", "密谈", valid_from=1))
    # 写入两条 WITNESS involves（实现后 add_event 接受 list 或重复 slot）
    store.add_event(Event(
        "ev:mw", "talk",
        participants=[("SUBJ", "role:甲"), ("WITNESS", "role:乙"), ("WITNESS", "role:丙")],
        effects=["fact:y"],
        story_time=1,
    ))
    assert project_frame(store, "role:乙", 1).knows("fact:y")
    assert project_frame(store, "role:丙", 1).knows("fact:y")
```

- [ ] **Step 2: 实现要点**

- `Event.participants` 改为 `list[tuple[str, str]]` **或** 保留 dict 并新增 `witness_ids: list[str]`。  
- 推荐兼容期：dict 仍可用；若 value 为 list 则展开。  
- `events_at` 禁止 `participants = {role: oid}` 覆盖；改为 list 聚合。  
- `witnesses_of` 读所有参与者 oid。

- [ ] **Step 3: 全量相关测 + Commit**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_event_graph.py scribe3/tests/test_see_event_production.py -q
```

---

### Task 11: `graph()` 尊重 `until_chapter`

**Files:**
- Modify: `scribe3/store/structure.py`
- Test: 新建或并入 `test_store.py`

- [ ] **Step 1: 测试**

```python
def test_graph_hides_forgotten_knowledge(store):
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:z", "role:甲", "密", "旧事", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:z", since_chapter=1, until_chapter=5))
    g3 = store.graph(chapter=3)
    edges3 = {(e["src"], e["dst"]) for e in g3.get("edges", []) if e.get("rel") == "knows"}
    assert ("role:甲", "fact:z") in edges3 or any(
        e.get("src") == "role:甲" and "z" in str(e.get("dst")) for e in g3.get("edges", []))
    g6 = store.graph(chapter=6)
    assert not any(
        e.get("rel") == "knows" and e.get("src") == "role:甲" and "z" in str(e.get("dst"))
        for e in g6.get("edges", [])
    ), "until_chapter=5 后章6不应显示 knows"
```

（按 `graph()` 实际 edge 字段微调断言。）

- [ ] **Step 2: 实现** — 与 `project_frame` 同谓词：`since <= ch and (until is None or until > ch)`。

- [ ] **Step 3: Commit**

```bash
git commit -am "fix(graph): honor knows.until_chapter at chapter snapshot"
```

---

### Task 12: 前端只读 flag 最小集（Phase 2B）

**Files（按现网入口裁剪，实现前 `rg` 确认）:**
- `scribe3/web/src/api.js` 或 settings：读 `author_write_via_chief`（可用 `import.meta.env` 或 `/capabilities`）
- `scribe3/web/src/CodexNew.jsx` / `CodexDetail.jsx` / `NorthStarBar.jsx` / 章 meta 相关
- `scribe3/web/src/__tests__/author_write_via_chief.test.jsx`（新建）

**范围（本计划最小，不做全灭 F-01～F-15）:**

1. flag **默认 true**（产品铁律）。  
2. true 时：隐藏 CodexNew 提交；CodexDetail 字段只读 + 按钮「让主编改这项」→ `s3-chief-seed` 事件（已有 ChiefDock 监听）。  
3. NorthStar 已只读则只保证 CTA 种子含 `s3_set_intent` 意图话术。  
4. false 时旧行为（dev/e2e 逃生）。

- [ ] **Step 1: 前端测（概念）**

```js
// author_write_via_chief.test.jsx
import { render, screen } from '@testing-library/react'
// mock api + flag true
// expect(screen.queryByRole('button', { name: /保存|新建角色/ })).toBeNull()
// expect(screen.getByText(/让主编/)).toBeInTheDocument()
```

- [ ] **Step 2: 实现 CTA 种子模板**

```text
请为角色「{name}」补全/修改「{field}」为…，并提交写入提案供我批准（使用 s3_patch_character 等工具）。
```

- [ ] **Step 3: 前端测**

```bash
cd scribe3/web && npm test -- --run author_write_via_chief
```

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(web): author_write_via_chief default readonly + chief seed CTA"
```

---

### Task 13: REST 紧急写开关（Phase 2D）

**Files:**
- `scribe3/settings.py`：`SCRIBE3_EMERGENCY_REST_WRITE` 默认 `false`
- `scribe3/api/app_impl.py`：世界状态 POST/PATCH/PUT/DELETE 入口检查
- `scribe3/tests/test_emergency_rest_write.py`
- conftest / 依赖 REST 的测试：fixture 设 env true

- [ ] **Step 1: 测试**

```python
def test_rest_post_character_blocked_by_default(store, client, monkeypatch):
    monkeypatch.delenv("SCRIBE3_EMERGENCY_REST_WRITE", raising=False)
    # 或 monkeypatch.setenv(..., "0")
    r = client.post("/characters?work=main", json={"name": "不该进"})
    assert r.status_code in (403, 404, 405)


def test_rest_post_character_allowed_when_emergency(store, client, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "1")
    # 可能需 reload settings
    r = client.post("/characters?work=main", json={"oid": "role:测", "name": "测"})
    assert r.status_code < 400
```

（`client` fixture 以 `test_app.py` 为准；世界写路由列表从设计文档 F 清单收敛，**至少** `/characters` `/facts` `/intent` `/volumes` `/chapters` meta。）

- [ ] **Step 2: 实现** — 中间件或依赖函数：

```python
def _require_emergency_rest_write():
    if not _flag_enabled("SCRIBE3_EMERGENCY_REST_WRITE"):
        raise HTTPException(403, "REST world write disabled; use dialogue + MCP approval")
```

测试 conftest 默认 `SCRIBE3_EMERGENCY_REST_WRITE=1` 以免炸现有 `test_app.py`。

- [ ] **Step 3: 全量 app 相关测**

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/test_app.py scribe3/tests/test_emergency_rest_write.py -q --tb=line
```

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(api): gate REST world writes behind SCRIBE3_EMERGENCY_REST_WRITE"
```

---

## 总验收（Phase 2+3 完成定义）

```bash
# 门控 + 结构写 + 限知
scribe3/.venv/bin/python -m pytest \
  scribe3/tests/test_gate_invariants.py \
  scribe3/tests/test_structure_write_mcp.py \
  scribe3/tests/test_hybrid_time_gate.py \
  scribe3/tests/test_see_event_production.py \
  scribe3/tests/test_mcp.py \
  scribe3/tests/test_provision_hermes.py \
  scribe3/tests/test_ingest_idempotency.py \
  -q

# PR 基线
scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q
cd scribe3/web && npm test -- --run
```

**手工场景（可选但推荐）**

1. 写网关对话：「建卷一，第一章大纲…，登记角色沈砚弧光锚…」→ 审批 → `list_volumes` / `get_chapter` / `char_anchors` 只读可见。  
2. 入库带 effects 的事件后，不手调，`project_frame(目击者)` 含 effect。  
3. `hybrid_recall(..., chapter=5)` 不含 valid_from=100。  
4. flag 开：UI 无法失焦保存外貌。  
5. emergency 关：curl POST /characters → 403。

---

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| ingest delta schema 与测试草稿不一致 | Task 9 Step1 先读源码再写最终断言 |
| `transaction()` 与 embed 副作用 | see_event 不触发 embed；fact 已在 did 路径建索引 |
| test_app 依赖 REST 写 | conftest 测试默认 emergency=1 |
| multi-WITNESS 改 ontology 面过大 | Task 10 独立 PR，可 defer |
| WriteProposal 批量卡未做 | 本计划用 per-tool elicit；UX 另开计划 |
| provision 未重跑导致网关无新工具 | Task 7 强制 + 文档提醒 `provision` |

---

## Self-review（计划对照）

| 审查要求 | 对应 Task |
|----------|-----------|
| Phase 2 结构 MCP 缺口 | 3–6 |
| WRITE_GATED / author_pref | 1 |
| Hermes include | 7 |
| UI 只读最小 | 12 |
| REST 后门 | 13 |
| see_event 生产接线 | 8–9 |
| hybrid 时间门 | 2 |
| multi-WITNESS | 10 |
| graph until | 11 |
| 批量 WriteProposal | **defer**（注明） |
| GBrain / 换库 | **不做** |

---

## 执行交接

**Plan complete and saved to**  
`docs/superpowers/plans/2026-07-22-phase2-dialogue-write-phase3-limited-knowledge-tdd.md`

**Two execution options:**

1. **Subagent-Driven（推荐）** — 每 Task 一个子代理，Task 间人工/主代理复核  
2. **Inline Execution** — 本会话按 Task 0→13 顺序 TDD  

**Which approach?** 回复 `1` 或 `2` 即可开干。建议先跑 **Task 0→1→2**（门控 + 时间门，半日内可合），再 **3→7**（对话写工具面），再 **8→9**（限知命根）。

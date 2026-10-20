# Scribe3 Record Range、COUNT 索引与单书数据收敛 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. This task must run inline because the user did not authorize subagents. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将章节顺序读取改为 SurrealDB record range，让两种章节计数真正命中 COUNT 索引，并将现网历史数据收敛为只保留《纸命》。

**Architecture:** 保留现有数值型 chapter record id，用一个严格校验边界的内部辅助函数统一构造 record range target。新增 `075` migration 定义全章与未归档章 COUNT 索引；未归档计数命中 `IndexCountScan`，无条件计数在 SurrealDB 3.1.5 中保留更直接的内建 `CountScan` 快路。数据清理采用“纸命单库导出→迁移验证→显式白名单删除→前后指纹对账”。

**Tech Stack:** Python 3.12, pytest, SurrealDB 3.1.5, surrealdb-py, SurrealQL migrations.

## Global Constraints

- 只保留 NS=`scribe3` 中 `_reg` 和 DB=`book_c256380e`；`_reg.work` 只保留《纸命》。
- 删除所有其他数据库、旧混合备份和非《纸命》 loop journals。
- 先生成并验证《纸命》单库导出，再执行任何删除。
- 不修改 chapter record id；现存 `chapter:1..=6` 必须保持。
- 不改 HNSW 向量查询和单 record 点查形状。
- 不覆盖工作树现有修改；只精确修改本计划列出的代码块。
- 不 commit、不 push、不建分支、不创建 worktree。
- 实施顺序必须遵守 TDD RED→GREEN→REFACTOR，未看到预期失败不得写生产代码。

---

### Task 1: 建立《纸命》清理前基线和单库备份

**Files:**
- Runtime artifact: `/tmp/scribe3-paper-20260710/book_c256380e.surql`
- Preserve: `~/.scribe3-backups` until the temporary export is verified

**Interfaces:**
- Consumes: NS=`scribe3`, DB=`book_c256380e`, running SurrealDB at `127.0.0.1:8001`
- Produces: non-empty paper-only SurrealQL export and a printed table-count/chapter-hash baseline

- [ ] **Step 1: Capture the paper-only baseline**

Run from the repository root; this read-only probe prints sorted table counts, chapter `(id, seq)` pairs, and SHA-256 over sorted `(seq, title, prose)` JSON without printing credentials:

```bash
PYTHONPATH=scribe3 scribe3/.venv/bin/python - <<'PY'
import hashlib
import json
import os
from surrealdb import Surreal

db = Surreal(os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc"))
db.signin({
    "username": os.environ.get("SCRIBE3_SURREAL_USER", "root"),
    "password": os.environ.get("SCRIBE3_SURREAL_PASS", "root"),
})
db.use("scribe3", "book_c256380e")
info = db.query("INFO FOR DB") or {}
tables = sorted((info.get("tables") or {}).keys())
counts = {}
for table in tables:
    rows = db.query(f"SELECT count() AS n FROM `{table}` GROUP ALL") or []
    counts[table] = int((rows[0].get("n") if rows else 0) or 0)
chapters = db.query(
    "SELECT id, meta::id(id) AS local_id, seq, title, prose FROM chapter:.. ORDER BY seq"
) or []
payload = [[r.get("seq"), r.get("title"), r.get("prose")] for r in chapters]
print(json.dumps({
    "counts": counts,
    "chapters": [[str(r.get("id")), r.get("local_id"), r.get("seq")] for r in chapters],
    "prose_sha256": hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest(),
}, ensure_ascii=False, sort_keys=True))
db.close()
PY
```

Expected: six chapter pairs `chapter:1` through `chapter:6`, every local id equals `seq`, and one deterministic SHA-256 string.

- [ ] **Step 2: Export only `book_c256380e` outside the old backup directory**

Run the active binary with credentials passed through environment variables, without echoing their values:

```bash
mkdir -p /tmp/scribe3-paper-20260710
SURREAL_USER="${SCRIBE3_SURREAL_USER:-root}" \
SURREAL_PASS="${SCRIBE3_SURREAL_PASS:-root}" \
~/.surrealdb/surreal export \
  --endpoint http://127.0.0.1:8001 \
  --namespace scribe3 \
  --database book_c256380e \
  /tmp/scribe3-paper-20260710/book_c256380e.surql
```

Expected: exit 0 and a non-empty `/tmp/scribe3-paper-20260710/book_c256380e.surql`.

- [ ] **Step 3: Verify export scope**

Run:

```bash
test -s /tmp/scribe3-paper-20260710/book_c256380e.surql
find /tmp/scribe3-paper-20260710 -maxdepth 1 -type f -print
```

Expected: one file named `book_c256380e.surql`; no other database export.

### Task 2: RED — 定义 Record Range 与 COUNT 索引的可观测行为

**Files:**
- Modify: `scribe3/tests/test_store.py`
- Modify: `scribe3/tests/test_indexes.py`

**Interfaces:**
- Consumes: existing `store` fixture and future `_chapter_range_target`, `chapter_seqs_in_range`
- Produces: failing tests that describe exact range, ordering, archive, and index-plan behavior

- [ ] **Step 1: Add failing range target validation tests**

Add these exact tests, importing `pytest` and `_chapter_range_target` at the top of `tests/test_store.py`:

```python
@pytest.mark.parametrize("bad", [True, 0, -1, 1.5, "1"])
def test_chapter_range_target_rejects_non_positive_ints(bad):
    with pytest.raises((TypeError, ValueError)):
        _chapter_range_target(start=bad, end=3)

def test_chapter_range_target_shapes():
    assert _chapter_range_target() == "chapter:.."
    assert _chapter_range_target(end=5, end_inclusive=False) == "chapter:..5"
    assert _chapter_range_target(start=1, end=10) == "chapter:1..=10"
    with pytest.raises(ValueError):
        _chapter_range_target(start=10, end=1)
```

- [ ] **Step 2: Add failing range semantics tests**

Create chapters 1, 2, 4 and archive chapter 2. Assert `chapter_seqs_in_range(1, 4)` returns `[1, 2, 4]` because it is an existence primitive, while `list_chapters()` excludes 2. Assert `recent_proses(4, k=3)` excludes archived 2 and chapter 4 itself, returning only chapter 1.

- [ ] **Step 3: Add failing execution-plan tests**

After schema application, assert:

```python
assert "RecordIdScan" in store._raw_query(
    "EXPLAIN SELECT seq FROM chapter:1..=4 ORDER BY seq"
)
info = store._raw_query("INFO FOR INDEX idx_chapter_count ON chapter")
assert info["building"]["status"] == "ready"
full_plan = str(store._raw_query(
    "EXPLAIN SELECT count() FROM chapter GROUP ALL"
))
assert "CountScan" in full_plan and "TableScan" not in full_plan
assert "IndexCountScan" in store._raw_query(
    "EXPLAIN SELECT count() FROM chapter "
    "WHERE archived = NONE OR archived != true GROUP ALL"
)
```

Normalize `_raw_query` output to `str(...)` in the assertions because the SDK returns planner text directly.

- [ ] **Step 4: Run RED tests**

Run:

```bash
cd scribe3
.venv/bin/pytest -q tests/test_store.py -k 'chapter_range or recent_proses_range'
.venv/bin/pytest -q tests/test_indexes.py -k 'record_id_scan or count_index'
```

Expected: failures caused by missing `_chapter_range_target`, missing `chapter_seqs_in_range`, and missing COUNT indexes; no syntax/import setup errors.

### Task 3: GREEN — 实现 Record Range 查询与 COUNT 迁移

**Files:**
- Modify: `scribe3/store.py`
- Create: `scribe3/migrations/075_chapter_record_range_count.surql`

**Interfaces:**
- Produces: `_chapter_range_target(start=None, end=None, end_inclusive=True) -> str`
- Produces: `SurrealStore.chapter_seqs_in_range(start_seq: int, end_seq: int) -> list[int]`
- Preserves: `get_chapter(seq)` direct record lookup and vector-search table target

- [ ] **Step 1: Implement the validated range target helper**

Add near the store constants:

```python
def _chapter_range_target(start: int | None = None, end: int | None = None,
                          *, end_inclusive: bool = True) -> str:
    for name, value in (("start", start), ("end", end)):
        if value is not None and type(value) is not int:
            raise TypeError(f"{name} must be an int")
        if value is not None and value < 1:
            raise ValueError(f"{name} must be >= 1")
    if start is not None and end is not None and start > end:
        raise ValueError("start must be <= end")
    if start is None and end is None:
        return "chapter:.."
    if start is None:
        return f"chapter:..{'=' if end_inclusive else ''}{end}"
    if end is None:
        return f"chapter:{start}.."
    return f"chapter:{start}..{'=' if end_inclusive else ''}{end}"
```

- [ ] **Step 2: Implement the inclusive existence-range method**

```python
def chapter_seqs_in_range(self, start_seq: int, end_seq: int) -> list[int]:
    target = _chapter_range_target(start_seq, end_seq)
    rows = self._query(f"SELECT seq FROM {target} ORDER BY seq")
    return [int(row["seq"]) for row in rows if row.get("seq") is not None]
```

Do not filter archived rows in this primitive; pilot previously treated an archived record as existing.

- [ ] **Step 3: Migrate safe chapter scans**

Replace chapter table targets with `chapter:..` in:

- `backfill_scalability_caches`
- `list_chapters`
- `chapters_lite`
- `causal_debt_total`
- `max_chapter`
- `_validate_cross_chapter_impl`
- `create_chapter` volume-membership lookup
- `list_archived_chapters`
- `outline`

Change `recent_proses()` to build `chapter:..{before_seq}` through `_chapter_range_target(end=before_seq, end_inclusive=False)` and remove the redundant `seq < $s` predicate.

Leave aggregate queries and the HNSW query unchanged in this step.

- [ ] **Step 4: Split count queries from sums**

In `stats()`, use one exact active count query and one active `sum(qc_word_count)` query. In `validate_cross_chapter_consistency()`, use one full count query and one full sum query. Preserve return shapes and zero defaults.

- [ ] **Step 5: Add migration 075**

Create:

```surql
-- scribe3 · 075_chapter_record_range_count.surql · 章节计数快路
DEFINE INDEX IF NOT EXISTS idx_chapter_count ON chapter COUNT;
DEFINE INDEX IF NOT EXISTS idx_chapter_active_count ON chapter COUNT
    WHERE archived = NONE OR archived != true;
```

- [ ] **Step 6: Run GREEN tests**

Run the same focused commands from Task 2.

Expected: all focused range and index tests pass.

### Task 4: RED/GREEN — pilot 连写使用一次区间预取

**Files:**
- Modify: `scribe3/tests/test_pilot.py`
- Modify: `scribe3/app.py`

**Interfaces:**
- Consumes: `SurrealStore.chapter_seqs_in_range(start_seq, end_seq)`
- Preserves: missing chapters are created; existing and archived records are not recreated

- [ ] **Step 1: Add a failing pilot prefetch test**

Spy on `store.chapter_seqs_in_range`, run `_pilot_run_bg` for a short range with a parked stub step, and assert the method is called exactly once with the requested inclusive bounds. Assert an absent starting chapter is still created.

- [ ] **Step 2: Run the pilot RED test**

```bash
cd scribe3
.venv/bin/pytest -q tests/test_pilot.py -k 'prefetches_chapter_range_once'
```

Expected: failure because `_pilot_run_bg` still calls `get_chapter()` for each sequence.

- [ ] **Step 3: Implement pilot prefetch**

Immediately after obtaining `st` in `_pilot_run_bg`:

```python
existing_seqs = set(st.chapter_seqs_in_range(start, until))
```

Inside the loop, replace `if not st.get_chapter(seq)` with membership against `existing_seqs`; after creating a missing chapter, add it to the set.

- [ ] **Step 4: Migrate app-level full chapter scans**

Change the two inbox pilot queries from `FROM chapter` to `FROM chapter:..`, preserving predicates and ordering.

- [ ] **Step 5: Run pilot focused tests**

```bash
cd scribe3
.venv/bin/pytest -q tests/test_pilot.py -k 'run_until or run_parks or prefetches_chapter_range_once'
```

Expected: focused pilot tests pass.

### Task 5: 代码回归和查询形状审计

**Files:**
- Verify only: `scribe3/store.py`
- Verify only: `scribe3/app.py`
- Verify only: `scribe3/migrations/075_chapter_record_range_count.surql`

**Interfaces:**
- Produces: evidence that no eligible production `FROM chapter` table scan remains

- [ ] **Step 1: Audit remaining chapter targets**

Run `rg -n "FROM chapter" scribe3/store.py scribe3/app.py` and classify every remaining hit. Allowed hits are:

- `chapter_version` and `chapter_scorecard` tables
- chapter aggregate queries used for `count()` / `sum()`
- chapter HNSW query
- direct `type::record` point reads

Any other full or bounded chapter-row read must use a record range.

- [ ] **Step 2: Run store/index/pilot suites**

```bash
cd scribe3
.venv/bin/pytest -q tests/test_store.py tests/test_indexes.py tests/test_pilot.py tests/test_manuscript.py tests/test_batch2.py
```

Expected: zero failures.

- [ ] **Step 3: Run full Python regression before production migration**

```bash
cd scribe3
.venv/bin/pytest -q
```

Expected: exit 0. If unrelated pre-existing failures occur, capture exact failures and stop before production migration unless they are proven unrelated and the user authorizes continuing.

### Task 6: 应用《纸命》生产迁移并验证执行计划

**Files:**
- Runtime DB: NS=`scribe3`, DB=`book_c256380e`

**Interfaces:**
- Consumes: passing tests and verified paper-only export
- Produces: migration `_migration:075_chapter_record_range_count`, ready COUNT indexes, unchanged paper data

- [ ] **Step 1: Re-run the paper baseline immediately before migration**

Expected: matches Task 1 counts, id/seq pairs, and prose hash.

- [ ] **Step 2: Apply schema only to paper**

Instantiate `SurrealStore(db="book_c256380e")`, call `apply_schema()`, close the connection.

Expected: migration 075 applies without modifying chapter records.

- [ ] **Step 3: Verify indexes and planners**

Run `INFO FOR INDEX idx_chapter_count ON chapter`, `INFO FOR INDEX idx_chapter_active_count ON chapter`, and four `EXPLAIN` probes.

Expected: record-range probes contain `RecordIdScan`; the unconditional COUNT index is `ready` and the planner uses `CountScan` without `TableScan`; the active-count probe contains `IndexCountScan`.

- [ ] **Step 4: Re-run paper baseline**

Expected: all table counts except `_migration`/schema metadata remain unchanged; chapter pairs and prose hash are byte-for-byte identical.

### Task 7: 删除其他历史数据并收敛备份

**Files:**
- Delete DBs: explicit nine-name allowlist from the approved design
- Delete registry rows: every `_reg.work` row except `book_c256380e`
- Delete: existing `~/.scribe3-backups/*`
- Delete: `~/.scribe3-loop-journals/main`, `~/.scribe3-loop-journals/loop-qa`
- Create: `~/.scribe3-backups/20260710-paper-only/book_c256380e.surql`

**Interfaces:**
- Consumes: verified migration and `/tmp` paper-only export
- Produces: namespace with only `_reg` and `book_c256380e`, paper-only backup tree

- [ ] **Step 1: Re-read live namespace and assert the deletion allowlist**

The deletion set must equal:

```text
__codex_probe_20260709__
book_5ce0a5c4
book_bfd18b78
book_x
codex_hermes_e2e_20260710
loop-qa
main
material_inject_test
tmp_advproof_img
```

Abort if `book_c256380e` or `_reg` appears in the deletion set.

- [ ] **Step 2: Remove the nine databases explicitly**

Run this exact Python command. It validates the immutable allowlist before issuing one quoted `REMOVE DATABASE IF EXISTS` statement per database and stops on the first exception:

```bash
PYTHONPATH=scribe3 scribe3/.venv/bin/python - <<'PY'
import os
from surrealdb import Surreal

to_delete = [
    "__codex_probe_20260709__",
    "book_5ce0a5c4",
    "book_bfd18b78",
    "book_x",
    "codex_hermes_e2e_20260710",
    "loop-qa",
    "main",
    "material_inject_test",
    "tmp_advproof_img",
]
assert "book_c256380e" not in to_delete and "_reg" not in to_delete
db = Surreal(os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc"))
db.signin({
    "username": os.environ.get("SCRIBE3_SURREAL_USER", "root"),
    "password": os.environ.get("SCRIBE3_SURREAL_PASS", "root"),
})
db.use("scribe3", "_reg")
done = []
for name in to_delete:
    escaped = name.replace("`", "``")
    db.query(f"REMOVE DATABASE IF EXISTS `{escaped}`")
    done.append(name)
print({"deleted": done})
db.close()
PY
```

- [ ] **Step 3: Prune the registry**

Run against `_reg` through the authenticated Python client:

```surql
DELETE work WHERE slug != 'book_c256380e';
SELECT slug, title FROM work ORDER BY slug;
```

Expected: exactly one row with title `纸命`.

- [ ] **Step 4: Delete old backup and journal trees**

Run only after the new temporary export has passed `test -s`:

```bash
rm -rf "$HOME/.scribe3-backups/20260710-112012"
rm -rf "$HOME/.scribe3-backups/20260710-112110"
rm -rf "$HOME/.scribe3-loop-journals/main"
rm -rf "$HOME/.scribe3-loop-journals/loop-qa"
```

These are the exact paths approved by the user; do not touch any other home-directory data.

Expected: old timestamp backup directories, `main`, and `loop-qa` journal directories no longer exist.

- [ ] **Step 5: Install the paper-only backup**

Run:

```bash
mkdir -p "$HOME/.scribe3-backups/20260710-paper-only"
mv /tmp/scribe3-paper-20260710/book_c256380e.surql \
  "$HOME/.scribe3-backups/20260710-paper-only/book_c256380e.surql"
test -s "$HOME/.scribe3-backups/20260710-paper-only/book_c256380e.surql"
```

Expected: the new backup tree contains exactly one non-empty export file.

### Task 8: 最终验证与交付对账

**Files:**
- Verify: production SurrealDB namespace and paper DB
- Verify: `~/.scribe3-backups`
- Verify: `~/.scribe3-loop-journals`
- Verify: git diff/status for scoped source changes

**Interfaces:**
- Produces: fresh evidence for every completion claim

- [ ] **Step 1: Verify final namespace and registry**

Expected: `INFO FOR NS` database names equal `['_reg', 'book_c256380e']`; registry contains only paper.

- [ ] **Step 2: Verify paper data and backup**

Expected: chapter ids remain 1–6, id equals seq, prose hash matches Task 1, business table counts match pre-cleanup baseline, and backup contains exactly one non-empty file.

- [ ] **Step 3: Verify removed paths**

Expected: old mixed backups and `main`/`loop-qa` journals are absent.

- [ ] **Step 4: Re-run focused regression after live cleanup**

```bash
cd scribe3
.venv/bin/pytest -q tests/test_store.py tests/test_indexes.py tests/test_pilot.py tests/test_manuscript.py tests/test_batch2.py
```

Expected: zero failures.

- [ ] **Step 5: Run fresh full regression**

```bash
cd scribe3
.venv/bin/pytest -q
```

Expected: exit 0; record exact pass/skip counts.

- [ ] **Step 6: Inspect scoped diff and unrelated dirty files**

Run `git diff -- scribe3/store.py scribe3/app.py scribe3/tests/test_store.py scribe3/tests/test_indexes.py scribe3/tests/test_pilot.py scribe3/migrations/075_chapter_record_range_count.surql` plus `git status --short`.

Expected: scoped changes implement only this plan; all unrelated pre-existing modifications remain untouched. Do not stage or commit.

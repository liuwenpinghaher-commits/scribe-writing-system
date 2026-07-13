# 作品生命周期(废弃箱 + 重名硬拦)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删书变成软删+可恢复的废弃箱(永久删除需两道门),建书/改名重名硬拦 409。

**Architecture:** store 注册表层加 archived 字段与四个函数(archive/restore/archived_works/purge 语义收窄);REST 加三端点并变更 DELETE /works/{slug} 语义;前端 Library 加废弃箱区。spec:`docs/superpowers/specs/2026-07-13-work-lifecycle-design.md`。

**Tech Stack:** SurrealDB + FastAPI + React;后端测试 `scribe3/.venv/bin/python -m pytest`,前端 `cd scribe3/web && npx vitest run`。纪律同前(TDD/写路由台账/中文 commit/Co-Authored-By/不 push/前台跑测)。

**红线:** 测试只用测试 DB;**绝不碰生产作品**(book_c256380e《纸命》、book_a55a4111 等);purge 真删只在测试库验证。

---

### Task 1:store 层(archived 字段 + 五函数 + 重名校验)

**Files:** Modify `scribe3/store.py`;Test `scribe3/tests/test_work_lifecycle.py`(新)

- [ ] Step 1 失败测试(参考仓内既有 store 测试的 fixture 惯例——grep test_ 文件里怎么起测试 SurrealDB/建临时 work):

```python
# 断言语义(fixture 按仓内惯例写):
# ① archive_work(slug) → list_works() 不含它;archived_works() 含它(带 archived_at)
# ② restore_work(slug) → list_works() 复现;archived_works() 不含
# ③ archive_work('main') → 抛错(主书不可废弃)
# ④ delete_work(未废弃的 slug) → 抛错(必须先废弃)
# ⑤ archive 后 delete_work(slug) → 注册表与 DB 均消失(用测试库真删验证)
# ⑥ create_work('同名') → 抛 ValueError('已有同名作品')(strip 后比对)
# ⑦ 废弃的书不占名:archive《X》后 create_work('X') 成功
# ⑧ rename_work 改成已有活跃同名 → 抛错;改成自己原名 → 允许
# ⑨ restore_work 时已有同名活跃作品 → 抛错(提示先改名)
```

- [ ] Step 2 跑红
- [ ] Step 3 实现(store.py):
  - `list_works()` 加过滤 `WHERE archived = NONE OR archived != true`(注意现有"空则自动登记 main"逻辑保持);
  - `archived_works()` 新增(返回 slug/title/archived_at,archived_at 倒序);
  - `archive_work(slug)`(main 保护 + slug 合法性沿用 delete_work 现有校验);
  - `restore_work(slug)`(恢复前查活跃同名);
  - `delete_work(slug)` 语义收窄:先查该 slug 必须 `archived=true`,否则抛 `ValueError("请先移入废弃箱再永久删除")`;其余(REMOVE DATABASE)不变;
  - `create_work` / `rename_work` 加活跃作品重名校验(strip 比对,rename 排除自己)。
- [ ] Step 4 跑绿 + `scribe3/.venv/bin/python -m pytest scribe3/tests/test_work_lifecycle.py scribe3/tests/test_app.py -q`(test_app 含 works CRUD 既有测试,必须不回归——若既有测试假设"删就物理删",按新语义修它并在报告说明)
- [ ] Step 5 Commit `feat: 作品软删(废弃箱)+ 重名硬拦(store 层)`

### Task 2:REST 三端点 + DELETE 语义变更 + 台账

**Files:** Modify `scribe3/app.py`、`scribe3/tests/test_consistency.py`;Test `scribe3/tests/test_work_lifecycle.py`(追加 API 层)

- [ ] Step 1 失败测试(TestClient):
  - `DELETE /works/{slug}` → 200 且书进废弃箱(GET /works 不见、GET /works/archived 可见);
  - `POST /works/{slug}/restore` → 200 复现;同名冲突 → 409;
  - `DELETE /works/{slug}/purge` body `{confirm_title: "错名"}` → 422;正确书名且已废弃 → 200 真删;未废弃 → 409;
  - `POST /works` 重名 → 409;`PATCH /works/{slug}` 重名 → 409。
- [ ] Step 2 跑红
- [ ] Step 3 实现:
  - `DELETE /works/{slug}`:改调 `archive_work`,返回 `{ok: True, archived: True}`(`_stores.pop(slug, None)` 保留——废弃后不该继续持连接);
  - `GET /works/archived`;
  - `POST /works/{slug}/restore`(ValueError → 409);
  - `DELETE /works/{slug}/purge`(pydantic body `WorkPurgeReq{confirm_title: str}`;title 不符 → 422;未废弃 → 409;成功后 `_stores.pop`);
  - `POST /works` / `PATCH /works/{slug}` 的 ValueError → 409。
  - 台账登记:`("POST","/works/{slug}/restore")`、`("DELETE","/works/{slug}/purge")`(注释:purge 是唯一真删,两道门=必须已废弃 + confirm_title 匹配)。
- [ ] Step 4 跑绿 + `pytest scribe3/tests/test_work_lifecycle.py scribe3/tests/test_consistency.py scribe3/tests/test_app.py -q`
- [ ] Step 5 Commit `feat: 作品废弃箱 REST(restore/purge)+ 重名 409 + 台账登记`

### Task 3:前端 Library 废弃箱

**Files:** Modify `scribe3/web/src/api.js`(三方法:archivedWorks/restoreWork/purgeWork)、`scribe3/web/src/Library.jsx`;Test `scribe3/web/src/__tests__/library-trash.test.jsx`(新)

- [ ] Step 1 失败测试:
  - 删除按钮确认文案含「移入废弃箱」(可恢复);
  - 废弃箱区渲染已废弃作品(名 + 废弃时间);点「恢复」→ 调 restoreWork 并重拉;恢复 409 → 红字「已有同名作品」;
  - 点「永久删除」→ ConfirmDialog 需输入书名才启用确认;输对 → 调 purgeWork(slug, title);
  - 新建重名 409 → 就地红字「已有同名作品」且输入不清空。
- [ ] Step 2 跑红
- [ ] Step 3 实现(api.js 三方法用现有封装;Library 加废弃箱折叠区,样式沿仓内 token;输入书名确认的 Dialog——看 ui/Dialog.jsx 有无带输入的变体,无则在 Library 内本地实现受控输入 + 禁用确认按钮)
- [ ] Step 4 跑绿 + 全量 `npx vitest run`
- [ ] Step 5 Commit `feat: 作品库废弃箱(恢复/永久删除需输入书名)+ 重名就地提示`

### Task 4:回归 + 真机验收

- [ ] Step 1 后端全量 pytest 绿;前端全量 vitest 绿
- [ ] Step 2 真机(控制器亲自):**只用一次性测试书**——建《测试书A》→ 再建同名被 409 拦 → 删除进废弃箱(作品库列表消失、废弃箱可见)→ 恢复 → 再废弃 → 永久删除(输错名不放行、输对才删)→ 确认 DB 真消失;全程**不碰任何真实作品**;截图
- [ ] Step 3 Commit(如有修复)+ 汇报

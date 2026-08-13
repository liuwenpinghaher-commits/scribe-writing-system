# ctx-audit-fix · 自动修到诚实满分（循环任务）

| 项 | 值 |
|----|----|
| **短名** | **`ctx-audit-fix`** |
| **启动** | 新会话或 `/goal` 粘贴文末「GOAL 正文」 |
| **进度 SSOT** | [`MATRIX.md`](./MATRIX.md) 五维分 + [`CEILINGS.md`](./CEILINGS.md) |
| **停机** | MATRIX 每一行：五维皆 5，**或** 该单元在 CEILINGS 且已达标天花板 |
| **现网硬顶** | 代码常量 `NOVEL_PROMPT_HARD=48000`；demo 可以 env 升 96k。禁止为刷分再加大常量 |

---

## GOAL 正文（复制到 `/goal` 或新会话第一条）

```
执行 docs/audits/ctx-audit-20260813/FIX-LOOP.md
短名 ctx-audit-fix。
自动循环：每次取队列第一个未达标单元（P0-1 三燃料允许同 PR），改 shipped 代码 + 真实入口单测 + 重评 MATRIX + commit push origin/main。
直到 MATRIX 全员诚实五维=5 或已登记天花板。不要问我「要不要下一个」，自己继续。
先读 AGENTS.md、docs/SESSION.md、本 FIX-LOOP、MATRIX.md、RECOMMEND.md。
禁止 npm ci / 全量 pytest / 本机 Surreal；验证优先 demo 已部署栈冒烟。
禁止改评分口径凑 5、禁止加 PROMPT_HARD、禁止把段无故焊进 L0。
```

---

## 诚实 5（刷分无效）

| 维 | 5 分必须同时成立 |
|----|------------------|
| P_flow | 生产→注入→裁剪→观测闭环；空/失败可区分；无死登记 |
| Q_craft | 对写好一章有不可替代贡献；无邻段复读；≥1 条自动探针已绿 |
| R_safety | 限知/秘密不因本段变差；误用有测或明确 fail-closed |
| B_product | 作者能理解，或标明「仅引擎」且不与产品文案打架 |
| Observability | 独立段名或等价 trace；skip/fail 原因可查 |

禁止：加大 48k、灌 provenance 进模、无测改 Markdown 分数、一次 PR 扫多个无关单元。

---

## 天花板（允许永久 <5，写入 CEILINGS.md 后视为「该单元完成」）

| 单元 | 允许不满 | 必须仍达到 | 理由 |
|------|----------|------------|------|
| provenance | Q、B | P=5 R=5 O=5，额度保持 0 | 审计清单不准当生成燃料 |
| request_position | Q | 其余 ≥4，正文只有「当前第 N 章」 | 一行章号不是小说质量源 |
| story_move | — | 无已批计划 **零字节** 即为该段满分纪律 | 禁止无计划灌卡刷 Q |

新增天花板必须：改 CEILINGS.md + MATRIX 改造句写「天花板：…」+ 提交。不得把死段/bug 标成天花板。

---

## 队列（每次只取队首未完成项）

完成定义：MATRIX 该行五维=5，**或** 在 CEILINGS 且天花板维已满足。

1. **P0-1** `story_ember`+`story_recall`+`story_causal`（**唯一允许的多单元 PR**）
2. **P0-2** `narrative_contract`
3. **P0-3** `deduction_final`
4. **P1 按序**：`secret_guard` → `focalizer` → `event_drive`/`event_drive_hook`（可同 PR）→ `outline` → `codex` → `final_reminder` → `drama_contract`
5. **其余**：MATRIX 中仍未完成的单元，按五维均分升序；均分相同按单元名字母序
6. 跳过已完成与已登记天花板

---

## 单轮循环（禁止停下来问「要不要下一个」）

```
while 存在未完成单元:
  NAME = 队首
  读 seg-NAME.md + 源码锚点（行号过期先改卷宗）
  列出 <5 的维与可证伪缺口
  只做卷宗主方案（过时则先改主方案再改代码）
  改 shipped 代码
  补打真实入口测试（禁止 mock 被测函数、禁止测试内重实现）
  过滤单测绿；写路径改动则 deploy_demo 热更 + curl 已部署 /health
  按同一把尺重评 → 改 seg-NAME.md + MATRIX.md 该行
  commit + push origin HEAD:main
  更新本文件「进度」一节日期与队首
  立刻进入下一 NAME
```

单单元最多 **3** 轮仍不能诚实 5：停在该单元，把缺口写成 `seg-NAME.md` 的「阻塞」节并 **fail-loud 结束 goal**（不要假装全绿）。三燃料合计也算 3 轮。

---

## 验收（整个 goal 完成时）

1. 解析 MATRIX 全部数据行：每行要么五维=5，要么名字在 CEILINGS 且符合天花板。  
2. `git log` 能对应到各 P0 的实现提交（不只文档）。  
3. 相关过滤单测命令与输出保存在该次 goal 的 scratch。  
4. `scribe3/context_budget.py` 的 `NOVEL_PROMPT_HARD` 仍为 48000。

---

## 进度（执行者维护）

| 项 | 值 |
|----|----|
| 上次更新 | 2026-08-13 |
| 下一 NAME | （队列空） |
| 已完成单元 | story_ember, story_recall, story_causal, narrative_contract, deduction_final, secret_guard, focalizer, event_drive, event_drive_hook, outline, codex, final_reminder, drama_contract, anti_slop, sincerity, prefix, continue_snapshot, structure_diversity, tool_scope, craft_skills_index, author_prefs, brief_must, material_recall, pressure_drive, purpose, recent, reference_craft, storyline_polish, craft, discourse_soft, drama_vacuum, identity, procedural, revision, write_protocol, avoid, focus, phase_role, revelation_discipline, seed_words, uncertainty, volume_intro, global, reference, scene_truth_proj, voice_anchor, envelope, request_constraint, canonical |
| 天花板已登记 | provenance / request_position / story_move |

---

## 给编排/goal 的验收标准（可粘到 plan）

```
1. MATRIX 每一库存行：P=Q=R=B=O=5，或 CEILINGS.md 允许的维 <5 且其余达标。
2. P0 三条均有 shipped 代码 + 真实入口测试，不是只改 Markdown。
3. NOVEL_PROMPT_HARD 仍为 48000；无把故事燃料焊进 L0_NEVER_CUT。
4. 未在 Grok 机跑全量 npm/pytest/本机 Surreal；demo 热更仅在写路径变更时。
```

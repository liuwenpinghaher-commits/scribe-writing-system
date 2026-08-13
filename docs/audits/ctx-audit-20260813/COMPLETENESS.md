# ctx-audit × context-optimal 完成度审查

| 项 | 值 |
|----|----|
| 日期 | 2026-08-13 |
| 对照 HEAD | `a06b69b`（96k 分档） |
| 库存 | `MATRIX.md` 52 行 |
| 性质 | 分析；**不改分数、不加天花板、不改 48k 常量** |

诚实五维尺（FIX-LOOP）：P 闭环（空/失败可分）、Q 无邻段复读、R 限知不因本段变差、B 人话或标明仅引擎、O skip/fail 可查。

---

## 1. 总判

| 桶 | 行数 | 含义 |
|----|------|------|
| **complete-5** | 49 | MATRIX 五维=5，且抽查到的 shipped 入口与主方案同向 |
| **ceiling-ok** | 3 | `provenance` / `request_position` / `story_move` 满足 `CEILINGS.md`「仍须达到」 |
| **overclaimed** | **0** | 未发现「表格写 5 而写路径入口缺失」 |
| **incomplete** | **0** | 无未登记天花板且未满 5 的行 |

**FIX-LOOP 停机条件在表格层已满足。** 真实余量是：**卷宗评分表大量未重评（doc-lag）**、**context 方案 PR3 运维浸泡未做完人审冻结**、**PR1.1 / 掉链重建 / UI 画 96k 按方案本就不在本轮。**

---

## 2. 逐行判定

完整机读表见审查 scratch `matrix-parse.txt`。此处按波汇总。

### 2.1 五维皆 5（49）

W1：`deduction_final` `drama_contract` `drama_vacuum` `event_drive` `final_reminder` `focalizer` `narrative_contract` `outline` `scene_truth_proj` `secret_guard`

W2：`canonical` `focus` `global` `procedural` `recent` `reference` `uncertainty`

W3：`brief_must` `codex` `event_drive_hook` `pressure_drive` `story_causal` `story_ember` `story_recall`

W4：`anti_slop` `author_prefs` `avoid` `continue_snapshot` `craft` `craft_skills_index` `discourse_soft` `envelope` `identity` `material_recall` `phase_role` `prefix` `purpose` `reference_craft` `request_constraint` `revelation_discipline` `revision` `seed_words` `sincerity` `storyline_polish` `structure_diversity` `tool_scope` `voice_anchor` `volume_intro` `write_protocol`

### 2.2 天花板（3）

| 单元 | MATRIX | CEILINGS 仍须达到 | 判定 |
|------|--------|-------------------|------|
| provenance | 5/2/5/2/5 | P=5 R=5 O=5；额度 0 | **ceiling-ok**。`BLOCK_BUDGETS_NOVEL["provenance"]=0` |
| request_position | 5/2/5/3/2 | P≥4 R≥4 B≥3 O≥2；仅「当前第 N 章」 | **ceiling-ok**。prefix 里一行章号 |
| story_move | 4/4/4/4/4 | 无已批计划零字节 | **ceiling-ok**。旗默认关则 `render_story_move_segment` 空串；无 `approved` 也空。meta 有 `enabled/fed/applied`，**没有**字面 `plan_missing` 键 |

FIX-LOOP 表写 request_position「其余≥4」与 CEILINGS.md「B≥3 O≥2」不一致；**以 CEILINGS.md 为准**（本审查不改文档）。

---

## 3. 过宣称 / 缺口（不是改分，是诚实对照）

**入口缺失类过宣称：0。** 抽查的「已落地」都能在 `write_assemble_v1` / store / `context_budget` 找到对应符号。

### 3.1 卷宗滞后（doc-lag）— 表格 5、卷宗评分表仍 2–4

下列 `seg-*.md` **§5 分数未跟 MATRIX 对齐**，正文甚至还写旧主方案未做：

| 单元 | 卷宗表 | 代码实际 |
|------|--------|----------|
| identity | 4/3/4/3/2，「并入 prefix」 | 独立 `_push("identity")` |
| author_prefs | 全 3，「与 procedural 去重」 | 已对 envelope 整行差集 + `empty_author_prefs` |
| continue_snapshot | 全 3，「并入 prefix」 | 独立 `_push`；skip 走 soft_fail |
| tool_scope / craft_skills_index | 4/3/…，「并入 prefix」 | `with_tools` 才独立 `_push` |
| structure_diversity | 4/3/3/3/3，「拼进 prefix」 | 独立 `_push` |
| drama_vacuum | 3/3/4/3/3 | `should_inject_drama_vacuum`（仅无 goal∧conflict）；已剔出 `DRAMA_CORE_NAMES` |

这是 **文档债**，不是「代码没做却标 5」。若要以卷宗为唯一诚实源，应回头把评分表改到与 MATRIX 一致。

### 3.2 文案过时（非断链）

- **prefix**：MATRIX 一句仍写「只留身份+协议+anti_slop+章号」。现网 `prefix = anti_slop + 当前第 N 章`；身份/协议已独立段。五维仍成立，**描述落后一刀**。
- **purpose**：MATRIX 写「global 有北极星」。global 产品文案已改「作品意图」；差集函数同时认二者。

### 3.3 观测余量（不推翻 5，但未做到卷宗字面）

- `continue_snapshot`：有 `continue_snapshot_skip` soft_fail，**无** `budget_report.continue_snapshot_skip_reason`。
- `story_move`：零字节纪律成立，缺显式 `plan_missing` 字段。
- `story_fuel_skip` 是整包燃料异常；单段空是 `empty_story_*`。

---

## 4. 抽查（≥8，对照 shipped 入口）

详见 `spotcheck.txt`。结论摘要：

| # | 单元 | 主方案 | shipped 锚点 | 五维抽查 |
|---|------|--------|--------------|----------|
| 1 | narrative_contract | store 同构 + 场面头 | `CHAPTER_META_ALLOWED`；`format_story_contract_head`；`_push` + injected/skip | P/O 可分空与失败 |
| 2–4 | story_* | 独立 supplemental | `collect_story_fuel_segments` → `_push`；∉ L0 | 空记 `empty_*`；限知召回掩码 |
| 5 | brief_must | 相对大纲/合同差集 | `_filter_brief_must_against_cover` | Q 去复读 |
| 6 | craft / prefs / procedural | compact/整行差集 | `subtract_codex_canonical_echoes`；`_dedup_procedural_against_craft` | Q |
| 7 | revision | 非修订不注入 | `is_revision_request` | 空不 push |
| 8 | drama_vacuum | 仅无 goal∧conflict | `should_inject_drama_vacuum` | 有测 `test_drama_vacuum_honest` |
| 9 | identity / write_protocol | 独立 L0 | `_push("identity"|"write_protocol")` | NEVER 按名 |
| 10 | join work= | 分档共用顶 | `join_generation_segments(..., work=work)` | 见 §5 |

未发现「MATRIX=5 但入口不存在」。

---

## 5. context-optimal（96k 分档）完成度

方案 SSOT：`docs/plans/2026-08-13-budget-context-optimal.md`。

| 目标 | 状态 | 证据 |
|------|------|------|
| 默认硬顶仍 48k | **已完成** | `NOVEL_PROMPT_HARD=48000`；无旗 `get_prompt_hard()==48000` |
| 显式 wide 时 L2 与全域顶同 96k | **代码已完成** | `resolve_write_caps` → join 把同一组 int 给 L2 与 O1；`test_novel_wide_profile` |
| supplemental 随档 28/36k | **已完成** | `WIDE_SUPPLEMENTAL_*` |
| 信封仍 22k、codex 4500 | **已完成** | `NOVEL_ENVELOPE_TOKEN_BUDGET`；`DEFAULT_CODEX_INJECT_CAP` |
| 三燃料不进 L0 | **已完成** | ∉ `L0_NEVER_CUT`；档 `T1_fuel` |
| 讨论近窗不涨 | **已完成** | 12/600/2400/8000；agentic 无 `conversation_history=` |
| 缺窗/非法数值 fail-loud | **已完成** | 不得吞成 42k |
| 白名单外 / 未传 work 窄档 | **已完成** | `work_unspecified_narrow` |

### PR 切分

| PR | 内容 | 完成度 |
|----|------|--------|
| PR1 | 机械分档，默认 48k | **shipped** `a06b69b` |
| PR2 | flags + probe/report | **shipped** 同提交 |
| PR3 | demo recreate + 白名单浸泡 | **运维已开一刀**：`.env` `WIDE=1` `WORKS=wide_soak` `WINDOW=1000000`；**未**采 N=10 `drama_core_share` 基线；**未**记 with_tools usage；活书 `main` 仍 48k |
| PR1.1 | wide 燃料帽 | **未做**（方案可选 / 本审查非目标） |
| PR4 | 近窗钉测 | **shipped** `test_discuss_window_pin.py` |
| PR5 | 文档常驻 + 人审后 env | **文档已写**（DEPLOY / FIX-LOOP 头注）；**未**把 demo 改成全站常驻 96k |

### 还缺什么才算「方案做完」

1. **人审 OQ1**：连续写 + 人工看章后，才决定 demo 是否常驻 96k（或清旗回 48k）。
2. **PR3 余量**：开旗前 N=10 密度基线；一笔 `with_tools` 的 `prompt_tokens`。
3. **卷宗还债**：至少把 §3.1 七份 `seg-*` 评分表改到与 MATRIX 一致，prefix/purpose 一句改准。
4. **明确不做**（方案 Non-Goals）：燃料帽、掉链重建、作者 UI 画满 96k、改 38 条常量钉。

---

## 6. 结论（给编排）

- **52 行库存：FIX-LOOP 意义上已停机**（49×诚实 5 + 3×合法天花板）。没有 incomplete 行。
- **「已落地」在写路径上大体诚实**；过宣称是 **卷宗/MATRIX 一句没跟上后拆的 prefix**，不是空表刷分。
- **96k 目标：代码分档 100% 按 rev.3 落地**；终态「生产默认 96k」**故意没做**（默认钉 48k）。demo 仅 `wide_soak` 白名单浸泡。
- 下一厘米若还要做：先还卷宗债，再做人审后的 PR3/PR5 运维冻结，不要重开 FIX-LOOP 改分。

---

## 7. 证据索引

- 机读逐行：审查 scratch `matrix-parse.txt`
- 预算符号：`context-complete.txt`
- 抽查：`spotcheck.txt`
- 提交摘录：`commits.txt`（本仓库 `a06b69b` / `62d90f2` / `a14e0d2` / `7857a3b` 等）

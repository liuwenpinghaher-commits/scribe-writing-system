# 工艺优先验证方案 · v3

> **地位**：取代 `book_b4e72480` 一类「字数 + form_fill=0 + 入口扫尾」假 PASS。  
> **与既有文档关系**：
> - 继承 `真人作者全功能验收测试方案-v2.md` 的作者心智、禁表单、缺口即改；
> - 继承 `融合执行规程-真人验收×对话驱动改造.md` 的对话+Playwright 决策；
> - **推翻** `hq_wordcount_push` / 融合结案里以字数为主门控的逻辑；
> - 对齐代码真源：`brief.assemble_*`、`/post-check`、`find_leaks`、`_grounding_review`、章阶段 Tab。
>
> 更新：2026-07-22  
> **专家团修订**：Product / Architect / Tester 三方 **Approve with changes** 已并入下文（R1–R5）。  
> **机判实现**：`scribe3/verify_craft_compliance.py` · 单测 `tests/test_craft_compliance_gates.py` · CLI `python -m scribe3.tools.craft_gate_cli`

---

## 0. 一句话

**先写满可审计的辅助信息，再分阶段写章；正文必须可证明「参考并遵守了」这些信息；违规则停笔、定根因、修链路、同路径回归。**

正文不是目标本身，是辅助信息在限知约束下的投影。

### 0.1 门闩作用域（专家团 · 产品）

| 场景 | GATE |
|------|------|
| 试写 / sandbox 草稿 | **不**强制 GATE-A/B；**不得**标章完成、不得计旅程 PASS |
| 接受为章正文并进入完成/连写 | **必须** GATE-A（书级一次）+ 本章 GATE-B + C-Det |

### 0.2 专家团硬修订（R1–R5）

| ID | 修订 |
|----|------|
| **R1** | 默认 PASS 只绑 **C-Det（硬项）**；C-Align LLM 为报告轨 / nightly，不阻塞默认 CI |
| **R2** | 母题注入真源是 editor `_motif_block`，不在 `assemble_chapter_brief`；A7 勿误判 fallback |
| **R3** | B7 无库内时间戳时 **skip**，仅 e2e journal 可 hard；禁止假装 PipelineJournal 已覆盖阶段序 |
| **R4** | C2 直调 `causal_complete`（非 post-check）；无事件 → skip 不阻断 |
| **R5** | B6 grounding **verbatim-first**；LLM grounding 另轨 |

### 0.3 默认 PASS 公式（**双轨**；闸绿 ≠ 质量过）

```text
卫生 PASS ⇔ GATE-A ∧ ∀seq (GATE-B ∧ C-Det_hard ∧ GATE-D_min)

质量 PASS ⇔ 卫生 PASS
           ∧ ContentQuality(seq)   # verify_content_quality
           ∧ 人工/专家内容评审无阻断项

旅程总 PASS ⇔ 质量 PASS ∧ 无未关闭 P0/P1
```

| 轨 | 模块 | 回答的问题 |
|----|------|------------|
| 卫生 | `verify_craft_compliance` | 辅信/脚手架齐吗？限知漏了吗？ |
| 质量 | `verify_content_quality` + 专家评审 | **写得像章吗？辅信用进戏了吗？高不高？** |

**明确禁止**：仅因 craft gates 绿就写「验证通过 / 高质量完成」。  
**不进任一公式**：`form_fill_count`、入口触达；全书字数不得单独替代质量轨。

---

## 1. 旧方案错在哪（必须写进记忆）

| 旧做法 | 问题 |
|--------|------|
| `form_fill_count=0` 当主 KPI | 鼓励不碰结构化工艺 |
| `word_count≥5万` 当 PASS | 鼓励空脚手架瞎扩 |
| 伏笔/母题「点到入口」 | 触达 ≠ 使用 ≠ 约束正文 |
| 十维/文学分掩盖空台账 | 分数与世界状态脱钩 |
| 接受正文后不对照辅助信息 | 违纲、漏伏笔、OOC 无人拦 |

`book_b4e72480` 实测：promises=`[]`、motifs=`[]`、全书 deductions≈0，却仍可结案 PASS → **作废该 PASS**，仅作反面对照。

---

## 2. 验证金字塔（四层，全部必过）

```text
L0  单元/API 契约（确定性）     改领域逻辑时必跑
L1  书级辅助信息齐套门闩        未齐 → 禁止写任何正文
L2  章级脚手架齐套门闩          未齐 → 禁止接受本章正文
L3  正文×辅助信息合规审计       未过 → 禁止标章完成 / 禁止连写下一章
L4  根因闭环（缺口即改）        失败必须分类到 RC-* 并修
```

字数、十维、人工读感 **只在 L1–L3 全绿之后** 才作为质量附加指标（L3+）。

---

## 3. 依赖方向（硬序）

```text
┌─────────────────────────────────────────────┐
│  Phase A · 书级辅助信息（对话+审批写入）      │
│  北极星/intent · 设定库 · 母题 · 伏笔 · 关系  │
│  事件/命题按卷需要                           │
└────────────────────┬────────────────────────┘
                     │ GATE-A 全绿
                     ▼
┌─────────────────────────────────────────────┐
│  Phase B · 章级脚手架（每章强制）             │
│  大纲 → 节拍 → 演绎(真相+全涉及角色投影)     │
│  （可选：草稿）                               │
└────────────────────┬────────────────────────┘
                     │ GATE-B 全绿
                     ▼
┌─────────────────────────────────────────────┐
│  Phase C · 正文生成（注入 brief/envelope）   │
│  提案 → Playwright 接受 → 落库 prose         │
└────────────────────┬────────────────────────┘
                     │ GATE-C 合规审计全绿
                     ▼
┌─────────────────────────────────────────────┐
│  Phase D · 反哺 + 看板                       │
│  ingest/知识 · 伏笔 touch · 母题 instance    │
│  章前看板再进下一章                           │
└─────────────────────────────────────────────┘
```

**禁止**：跳过 A/B 直接 C；C 后不跑 GATE-C；用 API 静默灌 prose 冒充旅程通过。

---

## 4. GATE 定义（可机判）

### 4.1 GATE-A · 书级辅助信息齐套

在**第一次** `draft-accept` / `save-chapter` 接受正文前执行。

| ID | 检查 | 数据源 | 最低阈值（默认） |
|----|------|--------|------------------|
| A1 | 北极星/intent 结构化 | `GET /intent` | 读者感受/情感弧/红线类字段非空（以当前 intent schema 为准） |
| A2 | 主线角色 | `GET /entities` 或 characters | ≥2；每人至少：appearance 或 personality 之一 + 动机/欲望类字段之一 |
| A3 | 命题或世界规则（按书型） | facts / world-rules | ≥1 条支撑冲突的事实或规则 |
| A4 | 角色关系 | character-relations / entity-relations | ≥1 条主线关系 |
| A5 | 母题 | `GET /motifs` | ≥1，且 `name` 非空 |
| A6 | 伏笔 | `GET /promises` | ≥1 open；`setup_chapter` 有值；文本非空 |
| A7 | 注入可观测 | 对 ch1 调 `GET /chapter-brief?seq=1`（或等价组装） | brief 中 promises/motifs/设定相关段非「空跳过」 |

**全部通过 → `GATE_A=PASS`，记入 `artifacts/.../gates/gate-a.json`。**  
任一失败 → **停止**，不得写正文；缺陷记 `G-AUX-*`。

> 阈值可按卷规模上调（长篇角色≥5、伏笔≥3 等），但 **不得下调到 0**。

### 4.2 GATE-B · 章级脚手架齐套

每一章，在接受正文前执行。

| ID | 检查 | 条件 |
|----|------|------|
| B1 | 大纲 | `synopsis` strip 后长度 ≥ 80 |
| B2 | 节拍 | `beats` 有效条数 ≥ 3 |
| B3 | 场景真相 | `scene_truth` strip 后长度 ≥ 80 |
| B4 | 涉及角色 | `involved_characters` 非空；且 ⊆ 书中已有角色 |
| B5 | 限知投影完备 | 每个 involved 角色都有一条 `deductions[]` 且 prose 非空 |
| B6 | 演绎接地 | 对每条 deduction 调 `POST .../deductions/grounding`（或批内 `_grounding_review`） | `ok=true`；失败则停 |
| B7 | 阶段顺序证据 | journal 中有 大纲→节拍→演绎 的填入/接受时间戳，且早于正文接受 |

**全部通过 → `GATE_B=PASS`（按章）。**

### 4.3 GATE-C · 正文×辅助信息合规审计

正文接受落库后、标记「本章完成」前执行。  
分 **确定性** 与 **对照性（LLM 辅助但证据必须落在正文）** 两轨。

#### C-Det · 确定性（必须 0 阻断）

| ID | 检查 | 实现锚点 |
|----|------|----------|
| C1 | 限知泄露 | `find_leaks(prose, store, focalizer, seq)` → 空 |
| C2 | 因果断裂 | `causal_complete` 本章违规 → 按产品档位；e2e 默认 0 blocking |
| C3 | 综合体检 | `POST /post-check` → 无 S1/blocking（沿用 loop 三分流） |
| C4 | 草稿轻检 | 可选：`POST /draft-check` 与 post-check 一致 |
| C5 | 伏笔继承项 | post-check 的 inherited open / fulfillment：到期窗口内无进展 → **fail**（除非章 brief 显式声明「本章不推进」并落库标记） |
| C6 | 母题触及（弱确定） | 若母题登记了可检索 echo 词：正文或 `motif_instance` 至少命中 1；若只有抽象母题名 → 走 C-LLM |

#### C-Align · 对照辅助信息（必须出报告）

对每个维度产出：`{ dimension, expected_refs[], prose_hits[], miss[], verdict, root_cause_hint }`

| ID | 维度 | 期望 | 命中判定 |
|----|------|------|----------|
| C10 | 大纲 | synopsis 中的情节点 | 关键实体/动作是否在 prose 出现（关键词+LLM 双判；LLM 证据须可在 prose 定位） |
| C11 | 节拍 | 每条 beat | 覆盖率 ≥ 2/3 条有可定位痕迹；否则 fail |
| C12 | 场景真相 | scene_truth 中的隐藏机制/客观事实 | 限知允许「暗示」；**禁止** POV 直说 secret（与 C1 交叉） |
| C13 | 限知投影 | 焦点角色 deduction | 正文所知边界 ⊆ 投影；多知 = fail（C1 或 grounding） |
| C14 | 角色设定 | 外貌/称谓/能力/弱点 | 与 codex 冲突 = fail（OOC） |
| C15 | 关系 | 当前有效关系 | 正文关系态度不得无依据反转 |
| C16 | 伏笔 | open promises | setup 章应埋线索；payoff 窗口应收；超期未 touch = fail |
| C17 | 母题 | motifs | 声响/意象/主题句至少一处可辩护的回声 |
| C18 | 北极星 | intent 红线/情感弧 | 正文不得踩红线；情感方向明显逆意图 = fail |
| C19 | 注入清单 | 写前 brief/assemble_injection 实际注入列表 | 审计：注入了但正文 0 痕迹的条目计入 miss（可 warn→二轮升 error） |

**实现策略（务实）：**

1. **优先复用**：`/post-check`、`find_leaks`、scorecard、`promise` lifecycle、grounding。  
2. **新增机判模块**（建议路径）：`scribe3/verify_craft_compliance.py`  
   - `audit_chapter(st, seq) -> ComplianceReport`  
   - 确定性先跑；对照性调用 LLM 时 **强制 evidence quote ⊆ prose**（与 QualityEvaluator 同构）。  
3. **e2e 调用**：`node e2e/craft_compliance_gate.mjs --work=... --seq=N` 或 pytest 包装同一函数，**禁止只靠人工读感**。

**GATE-C = C-Det 全绿 ∧ C-Align 无 error。**  
warn 可记台账但本章仍可「有条件通过」仅当产品明确分级；**e2e 默认 warn≥阈值也 fail**（防假绿）。

### 4.4 GATE-D · 反哺

| ID | 检查 |
|----|------|
| D1 | 本章若推进伏笔 → promise 状态/clue/last_refresh 有变更 |
| D2 | 母题有 instance 或下章 brief 能读到 heat |
| D3 | 新事实若出现 → 命题/知识边有路径写入或明确记入「待主编落库」工单（不得静默丢失） |

---

## 5. 根因分类（合规失败必归类）

每次 GATE-C fail **必须**打一个主因（可多标签）：

| 码 | 根因 | 典型修法 |
|----|------|----------|
| **RC-EMPTY-AUX** | 辅助信息根本没写入 | 回到 Phase A；修对话→工具→审批链路 |
| **RC-SKIP-STAGE** | 跳过大纲/节拍/演绎 | 禁接受正文；e2e/产品硬门闩 GATE-B |
| **RC-NO-INJECT** | 信息在库但未进 prompt/envelope | 修 `assemble_chapter_brief` / editor system / memory fabric |
| **RC-INJECT-IGNORED** | 注入了模型未遵守 | 收紧指令+重写；或 grounding 阻断接受；补 few-shot/校验环 |
| **RC-TOOL-FAIL** | 工具/审批失败导致半写入 | 修 MCP `commit_if_approved`、审批 UI、幂等 |
| **RC-SCHEMA-WEAK** | 字段太虚无法机判 | 补具体 echo 词、leak_markers、relation 词表 |
| **RC-DETECTOR-BUG** | 检测误报/漏报 | 标定后修 verify/critique；不得改正文糊弄 |
| **RC-PRODUCT-HOLE** | 无路径表达该约束 | 记 G 工单，按 v2 §1 缺口即改 |

**流程：**

```text
GATE fail
  → 写 05-gap 条目：现象 / 证据 / 疑似 RC
  → 最小复现（同 work、同 seq、只读 API 导出辅助信息快照+prose）
  → 定 RC → FIX（链路或检测器，禁止只改阈值放水）
  → 同路径回归：同一章从 GATE-B 或重写正文再跑 GATE-C
  → 绿了才允许下一章
```

禁止：「先写完 17 章再修合规」。

---

## 6. e2e / 脚本改造清单

### 6.1 废弃或降级

| 资产 | 处置 |
|------|------|
| `hq_wordcount_push.mjs` 作为主 PASS | **降级**：仅允许在 GATE-A/B/C 绿后的「加厚」；不得对空脚手架章写正文 |
| `01-feature-value-matrix`「触达=1 分」 | 改为 **有写作后果** 才计分（落库+约束正文） |
| `form_fill_count=0` 作主门控 | 降为约束；**主门控改为 GATE-A/B/C** |
| `book_b4e72480` 结案 PASS | **作废**；目录保留为反面教材 |

### 6.2 新增（建议文件）

| 文件 | 职责 |
|------|------|
| `scribe3/verify_craft_compliance.py` | `gate_a` / `gate_b` / `audit_chapter` 纯逻辑 |
| `scribe3/tests/test_craft_compliance_gates.py` | 齐套/跳阶段/空伏笔/泄露 等确定性用例 |
| `scribe3/web/e2e/craft_first_journey.mjs` | 新主旅程：A→B→C→D 循环 |
| `scribe3/web/e2e/craft_compliance_gate.mjs` | 调 API/本地脚本跑 GATE，写 `gates/*.json` |
| `artifacts/e2e-YYYYMMDD-<slug>/gates/` | gate-a/b/c 每章报告 + RC 台账 |

### 6.3 新主旅程伪代码

```text
create_isolated_book()
dialog_fill_intent()           # 审批落库
dialog_fill_codex_min()        # 角色/关系/关键命题
dialog_fill_motifs()
dialog_fill_promises()
assert GATE_A()

for seq in 1..N:
  board_ritual()               # 图谱/时间线/仪表盘
  stage_outline_fill(seq)
  stage_beats_fill(seq)
  stage_deduce_fill(seq)       # truth + 全角色投影 + grounding
  assert GATE_B(seq)
  write_prose_accept(seq)      # 仅此时允许
  report = GATE_C(seq)
  if report.fail:
    classify_RC(); fix(); rewrite_or_patch(); re-GATE_C()
  assert GATE_D(seq)
  journal + scorecard

assert never_skipped_stages
assert promises/motifs still non-empty and progressed where required
```

### 6.4 证据树（新标准）

```text
artifacts/e2e-YYYYMMDD-<slug>/
  00-runtime-baseline.md
  01-aux-inventory.json          # 书级辅助信息快照
  gates/
    gate-a.json
    ch01-gate-b.json
    ch01-gate-c.json             # 含 C10–C19 miss 列表
    ...
  02-step-journal.md
  05-gap-research-log.md         # 按 RC 分类
  manuscript/chXX.txt
  09-author-verdict.md           # 仅当全部 GATE 绿才可写 PASS
```

**PASS 公式：**

```text
PASS ⇔ GATE-A
     ∧ ∀seq GATE-B(seq) ∧ GATE-C(seq) ∧ GATE-D(seq)
     ∧ 无未关闭 P0/P1
     ∧ form 约束（若仍禁表单）满足
```

字数、十维 **不进入** PASS 公式；可写在 verdict 附录。

---

## 7. 产品硬门闩（与测试一致，防再假绿）

建议分两期：

| 期 | 行为 |
|----|------|
| **P0 测试** | 仅 e2e/脚本门闩；产品可先警告 |
| **P1 产品** | `accept draft` / pilot 进正文：服务端校验 GATE-B 子集；失败 409 + 缺项列表 |
| **P2 产品** | 接受后自动跑 C-Det；blocking → 章标记 `compliance=failed`，仪表盘可见 |

测试方案 **不依赖** 产品 P1 才成立：e2e 必须自带 GATE，即使 UI 仍能点接受。

---

## 8. 与禁表单的兼容

- 辅助信息 **必须** 通过：对话 → 工具提案 → Playwright 批准 → 落库。  
- 大纲/节拍/演绎 **必须** 通过：阶段对话 → 填入/追加（阶段决策，非 Codex 失焦表单）。  
- 若对话写不进库 → **RC-TOOL-FAIL / 产品洞**，修链路，禁止改用手填灌库充数（融合规程 M2）。  
- 唯一例外：结构命名（卷名）等已记录的 structure 输入；不得扩展到设定语义字段。

---

## 9. 验收章节规模建议

| 轮次 | 章数 | 目的 |
|------|------|------|
| 烟测 | 1 章 | GATE-A/B/C 全链路通 |
| 主验收 | 3 章 | 跨章伏笔/母题/关系演变 |
| 加压 | 10 章 | 长程合规与反哺 |

**禁止** 用 17 章空脚手架正文冒充加压通过。

---

## 10. 落地顺序（工程）

1. **本文入仓**（本文件）— 契约 ✅  
2. **`verify_craft_compliance` + 单测** — 机判真源 ✅（`test_craft_compliance_gates.py`）  
3. **gate CLI** — `python -m scribe3.tools.craft_gate_cli --work=...` ✅  
4. **`craft_first_journey.mjs`** — 替掉 wordcount 主路径（Playwright+Hermes，后续）  
5. **废止旧 PASS** — `book_b4e72480` 结案作废；CLI `--expect-fail` 反面对照  
6. **产品 409 门闩（可选）** — 与 gate_b 同判据  
7. **新隔离书重跑** — 仅新公式可 PASS  

### 10.1 验证命令

```bash
# P0 机判（不依赖 Hermes）
scribe3/.venv/bin/python -m pytest scribe3/tests/test_craft_compliance_gates.py -q

# 对运行中的书跑门闩（需 Surreal + 该书 db）
scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work book_b4e72480 --expect-fail
scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work <slug> --seq 1

# HTTP 同源
curl -s "http://127.0.0.1:3321/craft-gates?work=book_b4e72480"
curl -s "http://127.0.0.1:3321/craft-gates?work=<slug>&seq=1"

# 真机工艺优先旅程（需前后端+Hermes）
cd scribe3/web && node e2e/craft_first_journey.mjs
```

### 10.2 产品硬门闩（已落地）

| 项 | 行为 |
|----|------|
| `POST /save-chapter` | `SCRIBE3_CRAFT_GATE` 默认 **1**：实质 prose(≥80 字)须过 GATE-B；全书尚无实质正文时另须 GATE-A。失败 **409** `{code, blocking, root_causes, reports}` |
| 逃生 | body `skip_craft_gate=true` 或环境 `SCRIBE3_CRAFT_GATE=0` |
| 单测 | `conftest` 默认钉 `SCRIBE3_CRAFT_GATE=0`，防存量用例无脚手架 |

### 10.3 e2e 脚本 exit

| 脚本 | 变更 |
|------|------|
| `craft_gates.mjs` | 共用 `GET /craft-gates` |
| `fused_author_journey*.mjs` | OK 前 assert craft gates |
| `hq_wordcount_push.mjs` / `hq_close_gaps.mjs` | 字数后仍须 craft gates（空辅信书 exit 10/11） |
| `craft_first_journey.mjs` | 新主旅程 A→B→C→gates |
---

## 11. 反模式清单（CI / 人工审查时直接打回）

- [ ] 以 word_count 或 form_fill 宣布旅程成功  
- [ ] promises/motifs 为空仍继续写正文  
- [ ] 无 scene_truth / deductions 接受正文  
- [ ] GATE-C 失败仍连写下一章  
- [ ] 只点「伏笔」导航算工艺验收  
- [ ] API 静默 saveChapter 代替 UI 接受  
- [ ] 调低检测阈值使红变绿而不修根因  
- [ ] 用文学十维高分覆盖合规 fail  

---

## 12. 成功标准（方案本身）

本方案落地成功，当且仅当：

1. 新 e2e 在辅助信息为空时 **必然 FAIL**；  
2. 跳过演绎写正文 **必然 FAIL**；  
3. 正文违背设定/限知/到期伏笔 **必然 FAIL 并打出 RC**；  
4. 修 RC 后同路径可绿；  
5. 旧 `book_b4e72480` 用新公式重跑 **必须 FAIL**（回归对照）。

---

## 13. 附录 · 与代码锚点对照

| 能力 | 代码位置 |
|------|----------|
| 章前简报/伏笔指令 | `scribe3/brief.py` `assemble_chapter_brief` / `promise_directives` |
| 设定注入 | `assemble_injection` / editor envelope（`runtime.py`） |
| 限知泄露 | `scribe3/verify.py` `find_leaks` |
| 因果 | `causal_complete` |
| 存稿后体检 | `POST /post-check` |
| 演绎接地 | `_grounding_review` / `POST .../deductions/grounding` |
| 章阶段 UI | `ChapterStudio.jsx` outline→beats→deduce→draft→final |
| 旧错误旅程 | `web/e2e/hq_wordcount_push.mjs`、`fused_author_journey*.mjs` |

---

**维护**：改 GATE 阈值或 RC 枚举时同步改本文件 + `test_craft_compliance_gates.py`，禁止只改脚本魔法数。

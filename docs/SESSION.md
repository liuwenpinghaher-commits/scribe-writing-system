# SESSION.md · 跨会话交接（滚动状态）

> **用途**：本仓库唯一跨会话记忆。新会话先读 [`AGENTS.md`](../AGENTS.md) + **本文件**，再动手。

---

## 主验收协议（现行）

| 项 | 值 |
|----|-----|
| **总 PASS 协议** | **v6.3.4 rev.13.4.3** · [`e2e-director-journey-v634-true-chat-full-capability.md`](./e2e-director-journey-v634-true-chat-full-capability.md)（写章内核 play-contract 五层 + playbook.3.2.2 上游引导接线 + Wave C） |
| **WCG SSOT** | `scripts/v4_world_complete_gate.py`（exit 0 / `pass=true`） |
| **体验路径** | SPA 对话驱动 + 点批/工作台裁决；**禁止**脚本灌章 / EMERGENCY / fabric-off 刷绿冒充总 PASS |
| **工程对照** | `scripts/v632_true_chat_journey.py` · v6.3.2 记忆子集 · v6.3.3 变更复验 → **≠** 体验总 PASS |
| **证据清单** | `scripts/v634_evidence_checklist.py` |
| **证据模板** | `docs/evidence/v634-true-chat-TEMPLATE/` |
| **公式** | 总 PASS ⇔ Wave A ∧ Wave B；仅 Wave A 或 `author_human=false` → 最高 **PARTIAL** |
| **写章内核** | play-contract 五层 duty→design→deduce→draft→final。playbook.3.2.2。Fate/水面词闸已删。旧验收 slug **不 overlay**（含 `book_20bab124` / `book_8777aad8` / `book_0786fff6`）。 |

---

## 新会话开场（复制粘贴）

```
继续 https://github.com/liuwenpinghaher-commits/scribe-writing-system
先读 AGENTS.md 和 docs/SESSION.md，再继续。
主验收协议 = v6.3.4（docs/e2e-director-journey-v634-true-chat-full-capability.md）。
```

### 50k 验收硬化（短入口）

```
继续 50k-e2e
先读 docs/plans/50k-e2e.md 与 docs/SESSION.md。
实现暂缓；按 PR Plan 开工再说。
```

### craft-loop · 真人视角块门改进闭环（短入口）

```
继续 craft-loop
先读 docs/plans/craft-loop.md 与 docs/SESSION.md。
性质：第一性块门 + 运营 + 改系统复验；≠ 50k-e2e；≠ v6.3.4 总 PASS。
```

### ctx-audit-fix · 52 单元修到诚实满分（自动循环）

```
执行 docs/audits/ctx-audit-20260813/FIX-LOOP.md
自动循环直到 MATRIX 全员诚实五维=5 或已登记天花板。不要问下一个。
```

### 拆文倒逼翻主（短入口）

已结案。**现行 SSOT 换成 v4 指标坍缩修正**：[`2026-08-27-craft-v4.md`](./plans/2026-08-27-craft-v4.md)（短名 `craft4`）。v1 尺子/铁律、v2 先出样章/接诡秘/砍 token、v3 母题分层/黑名单/外部处境 仍有效，执行顺序以 v4 为准。

```
执行 docs/plans/2026-08-27-craft-v4.md
短名 craft4。先读 AGENTS.md 与 docs/SESSION.md。
复制该文件「Warp 执行入口」整段即跑。单次 goal，不挂 tick。
```

### 故事招式库 · 命名绕法卡片（短入口）

```
继续 招式库
先读 docs/plans/2026-08-13-move-library-design.md 与 docs/SESSION.md。
性质：L_move 构造层（本意×绕法，规范例三角信息法）；≠ 完成/宣称；≠ craft-loop；≠ v6.3.4 总 PASS。
实现按 PR Plan 0→6；v1 只种子三角；旗 SCRIBE3_MOVE_LIBRARY 默认关。
```

---

## 当前状态

### 默认模型切 DeepSeek V4 Flash（2026-08-26）

作者授意全部换成 Flash。代码默认 `llm.model` / `DEFAULT_MODEL` = **`deepseek-v4-flash-0731`**。本机 Hermes 五写作网关 `default:` 同此。TokenPlan 别名 `deepseek-v4-flash` 同钥 **HTTP 403**；快照 `deepseek-v4-flash-0731` 同钥可通。供应商仍 `qwen`，口仍 TokenPlan。兜底 kimi/MiniMax 未动。**demo 未部署，不宣称现网已切。** 运行中 Hermes 需重启才吃新 default。

### 技法标尺（2026-08-25）

合同：左轨「技法标尺」= 参考作品 / 质量审阅 / 质量合同。不是仪表盘、不是文学总分。`craft_ruler.py` 只是情绪曲线 advisory。
**已改：** 创建评价不再手填合同 ID，绑定本书 `quality-contract:{work}` 已批准修订；没有批准合同则禁用创建。合同页已批准标尺加载失败要响。栏2 标题与空态改成「技法标尺」。
**测：** QualityReview + QualityContractEditor + 入口/弱章跳转 31 passed。
**已合入并热更：** `f64f5323`。frontend `FRONTEND_DEPLOY_OK`，首页 `index-j3oc4sue.js`。宿主机与 nginx `index.html` 哈希一致。nginx unlink busy 非致命。强制刷新后再开技法标尺。未改评价算法、指纹生成、十维权重。

### 素材库 P3（2026-08-25）

整洁：拆 `Materials.jsx`（665→16 行 barrel；form/new/detail/list 独立）。`sessionClip.js` 只留剪藏/引用，`@` 目录进 `atCatalog.js`。`relates` 用 `166_material_relates.surql` 锁成 material→material SCHEMAFULL。删几乎无调用的 `emotion_target_from_materials`。作者直管 `/materials` 合同未改。
**测：** 前端焦点 42 passed；迁移护栏 10 passed。
**已合入并热更：** `e80edbf0`。hot `HEALTH_OK` + v634 27/27。frontend `FRONTEND_DEPLOY_OK`，首页 `index-BBh1o_zc.js`。宿主机与 nginx `index.html` 哈希一致。nginx unlink busy 非致命。强制刷新后再开素材库。旧口径「P3 不拆 Materials.jsx」作废。
**现网 166：** 注册表 3 本书均已标记 `166_material_relates`；`relates` 为 material→material SCHEMAFULL。《腕账》热更后首次开库才补上，已补。审计清单 P0–P3 闭合。手建 `/materials` 近重、写路径排除 `emotion_module` 仍按合同不改。

### 素材库 P2（2026-08-25）

不改合同。插入按钮写「填入后才记引用」。去掉恒空的「历史主编记录」。健康度失败要响。空库探测 `materials_exist` 只探一条。简单视图列表走 SQL `LIMIT/START`。情绪卡标签不再装成笔记。`@` 有查询时把 `q` 交给服务端，素材请求失败不装空目录。`/objects/material` 删/归档走作者直管闸外。
**测：** 前端 46 passed；后端 P2 焦点 12 passed。
**已合入并热更：** `29b62a65`。hot `HEALTH_OK` + v634 27/27。frontend `FRONTEND_DEPLOY_OK`，首页 `index-CgbrcZ3v.js`。宿主机与 nginx `index.html` 哈希一致。nginx unlink busy 非致命。强制刷新后再验素材库来源筛、插入按钮、健康度。
**余项已合入并热更：** `8dad78c6`。健康度走 SQL COUNT，不扫全表。全图节点 `LIMIT`，边只查 keep 集合。hot `HEALTH_OK` + v634 27/27。前端未改，首页仍 `index-CgbrcZ3v.js`。P3 见上节（已拆）。
**近重挡入库已合入并热更：** `ec70e979`。导入 commit 近重进 `failed`，不落库；同批其余条照常。扫描失败仍 warning 放行。hot `HEALTH_OK` + v634 27/27。前端未改，首页仍 `index-CgbrcZ3v.js`。
**SSRF 二次校验已合入并热更：** `643c5b4e`。导入 URL 解析 IP 后再检私网。hot `HEALTH_OK` + v634 27/27。前端未改，首页仍 `index-CgbrcZ3v.js`。

### 素材库 P0+P1（2026-08-25）

作者直管仍走 `/materials`。主编不能经 `s3_delete_codex` 改素材。导入 URL 每跳再检私网。commit 必须对应未过期 preview job。写路径自动注入不再记「作者已用」。章内引用失败要响，草稿页也能看账。转正典走待批 `s3_promote_material`（`fact.source=material:<id>`），不改素材行。
**测：** 后端焦点 26 passed；前端 workbench+sessionClip 25 passed。
**已合入并热更：** `107be8b0`。hot `HEALTH_OK` + v634 27/27。frontend `FRONTEND_DEPLOY_OK`，首页 `index-BHO-D5bG.js`。宿主机与 nginx `index.html` 哈希一致。nginx unlink busy 非致命。强制刷新后再验素材库/导入/章内引用。

### 主编可读面（2026-08-25）

输入框上方状态条写现在谈什么、只讨论/会改库、种子来自哪页；空会话不再假绿。审批和分流不改。
**讨论栏：** `56a07761`。空会话「空会话可以问」。
**写作槽：** `WriteChat` 复用 `ChiefStatusStrip`；空态走 `chiefEmptyCopy(write_ask)`。写库 run 故意 `phase=''`，测试已跟生产。相关 vitest 29 passed。
**现网已验：** frontend `FRONTEND_DEPLOY_OK`，首页 `index-Dtz9Tn4M.js`。腕账第 3 章「正文」写作槽过；空书《手术室》点「让主编写入」发出 `【总纲】` 种子，状态条「来自总纲 / 这句会改库，要你批」。收件箱空态改为「这页没有等你的事项。没查到的别处不算干净。」，不再说「一切有账」。强制刷新后再看。nginx unlink busy 非致命。

### 仪表盘先可读再助写（2026-08-25）

仪表盘合同仍是「机器体检」。第一屏改成弱章+未收账；码字图/各章图仍在，只是挪到名单下面。空书说「还没有章」，不再谎称「质检干净」。`DetailPane` 透传 `chapter={qualitySeq}`：当前章若也弱则钉顶；呼吸默认跟写作章。弱章/开口账多一粒「针对这条体检写下一笔」（只讨论）。弱章仍进 `quality_review`，不回退。
**已改并热更：** `90ae4032`。frontend `FRONTEND_DEPLOY_OK`，首页 `index-CX6-iORL.js`，懒加载 `InsightView-BGApNdVF.js` 含「针对这条体检写下一笔」/「还没有章」。强制刷新后再开仪表盘。nginx unlink busy 非致命。测绿 ≠ 视觉过。

### 拆文倒逼翻主（2026-08-25）· 已结案

旧过夜 SSOT [`docs/plans/2026-08-25-tonglu-force-rebuild-loop.md`](./plans/2026-08-25-tonglu-force-rebuild-loop.md) **禁止续跑**。能力 0–21 与《井台灯》场A–M 作为旧证据留档，不复用为过闸书。后继：`craft-eval`。

### craft5 · 第三次修正：量化闸整个降级为监控（2026-08-27 深夜 · 现行）

作者质疑「量化的闸根本不能带来正向效果」。**成立，铁证在上一轮我自己的代码里**：`prose_check._PHATIC`（「无信息回合」通过白名单）写着 `你吃了|吃了没`，而「你吃了没。」正是 D1/D2/D3 三篇共用、被作者判为「一个味道」的套利句——**上一轮的套利产物成了下一轮的及格线**。

机制上必然如此：明喻密度这类是**事后的表面统计**，模型逐 token 采样时没有对应内部状态，写进提示只能粗暴映射到极端；闸跑在生成之后**不产生梯度**；规则可枚举而文本高维，Goodhart 不是意外。效力排序：微调 > 拒绝采样+人类偏好 > 长示范 > 规则约束（≈0 且为负）。前四轮都在最底层。

**四处改动**：① `prose_check` 报告**去掉过/红与总分**，只给本稿值 vs 两本实测值（铜炉/诡秘：明喻 0.83/1.07、句长 SD 41.7/41.9、无信息回合 20%/13%；旧 SD 参照 32.8/35.5 亦是错的）；② 新建偏好数据集 [`docs/craft-prefs/`](./craft-prefs/README.md) + `scribe3/eval/prefs.py`，作者判断落成 (chosen, rejected, notes)，含糊批注被拒；③ 示范池扩到 9 段，加铜炉「决裂」（对峙逼问）与诡秘「黑蛇」（多人同场+内心盘算）；④ `generate_candidates` 同一处境独立写 N 篇交作者挑。

**回归钉**：`test_monitor_report_has_no_pass_fail`、`test_monitor_numbers_never_leak_into_prompt`（REF 数值不得进提示，`build_prompt_v4` 签名只准两参）、`test_prefs_reject_vague_notes_and_self_pairs`。craft 27 passed。详见 [`craft-v4.md`](./plans/2026-08-27-craft-v4.md#第三次修正--闸整个降级为监控)。

**下一件**：跑 `generate_candidates` 出 3 篇候选交作者挑，落第一条 pref。人写稿 `V4-3b` 按作者要求暂不动。

### craft4 · 第二次修正：尺子方向翻正（2026-08-27 深夜）

作者读人写对照稿 [`V4-3b-乡土-人写.md`](./craft-samples/V4-3b-乡土-人写.md) 后确认「方向对了」，据此重做 B 步的闸。详见 [`craft-v4.md`](./plans/2026-08-27-craft-v4.md#第二次修正--尺子方向是反的)。
**明喻阈值的依据算错了**：旧统计正则吞掉「如果/如此/如今」，把铜炉算成 2.69。精确重算 **铜炉 0.80 / 诡秘 1.07**——旧下限 1.0 比铜炉还严，而机器稿 2.02/2.27/2.48 是原文两三倍却判过。区间改 **0.4–1.5**。
**两条指标反向，已退役**：「内心活动占比」数标记词（三次给出与作者相反信号，正是「她心中一沉」的成因）；「26 字以上占比」奖励信息倾泻式长台词。
**参数标签会被直接执行**：`speech_len: 惜字` → 每句不超五字；`catchphrase: 有文件。` → 原样贴进第一句。**素材写成参数就还是答案**。改为 `speech_habit`（写行为）+ 新增 `tic`（无关执念，须复现≥2 次）+ `props`（物件须再承担行动），`catchphrase` 反转为「禁止原样搬运」。
**新闸 13 项**，新增：无信息回合 ≥12%、不接话茬 ≥1 处、执念复现、物件复现、卡片原句 =0。
**方向验证**：机器稿 9/10 → **7/13（6 红）**；人写稿 7/10 → **13/13**。红项与作者三轮批评逐条对应。回归钉 `test_retired_gates_are_gone`、`test_gate_agrees_with_author_verdict`。craft 相关测试 20 passed；`-k craft` 全集 15 failed 全为产品侧预存失败（stash 验证过，与 `scribe3/eval/*` 无依赖）。
**下一件**：D 用新闸重跑三篇。

### craft4 · 指标坍缩修正（2026-08-27）

SSOT：[`docs/plans/2026-08-27-craft-v4.md`](./plans/2026-08-27-craft-v4.md)。Warp 单次 goal。
**为什么换**：craft3 交付 D1–D3 三篇，`prose_check` **各 6/6 全绿**，作者仍判全废——「分不清谁在说」「不像这个角色该说的话」「有故事性没趣味性」。
**查明的机制**：`sample_scene.py:84` 的写作提示是 `prose_check` 六项的**逐条复述**。v3 立了「检查表不当提纲」的原则，我却把检查表原样抄进了提示 → 6/6 全绿是照着答案写的。铁证：三篇不同题材出现**完全相同的对白**——「你听我说——」「等一下。」「你吃了没。」「没有。」「嗯。」各出现在三篇里。
**量化对照**：句长标准差 铜炉 32.8 / 诡秘 35.5 vs 样章 **3.1 / 2.8 / 3.3**（十倍差）；26 字以上对白占比 33.6% / 18.9% vs **0% / 0% / 0%**；最长一句 399 / 400 字 vs 17 / 15 / 23；明喻密度 2.69 / 1.97 vs 0 / 0.6 / 0——**v3 的线 ≤1.0 比两本原文都严**，系统直接打到 0。
**方法论结论**：v3 只说对一半。**只要指标被系统看见，它就会变成提纲**。v4 两条硬规矩——① 提示与检查表物理隔离（有反套利测试钉）；② 给素材不给答案（角色语域卡、信息不对称属于写前的人物设定，不是检查项）。
**改了**：A 角色语域卡 + 信息不对称 + 两本对白示范（零 LLM）→ B `prose_check` 单边闸改**区间闸**，阈值一律由原文统计反推，新增句长 SD ≥12 / 26 字占比 ≥15% / 最长句 ≥60 字 / 角色句长分档 / 职业词命中 / 内心活动 ≥8% / **跨篇重复对白 =0** → C 重写提示，删掉第 84 行检查表复述 → D 三篇互不知情重写 → E 才回到拉分。
**没改**：三条铁律、留出集 hash、`stop.json`、母题黑名单、诡秘探针、快速集。
**现状**：A–C 已完（语域卡 + 区间闸 + 提示隔离；craft4 4 + craft3 6 = **10 passed**）。D 三篇已交作者：[`docs/craft-samples/V4-1-工厂.md`](./craft-samples/V4-1-工厂.md) / [`V4-2-体育.md`](./craft-samples/V4-2-体育.md) / [`V4-3-乡土.md`](./craft-samples/V4-3-乡土.md)。抽签 `seed=20260827` exclude p04/p07/p11 → p10 工厂 / p08 体育 / p01 乡土。跨篇 5/5 过，`shared=[]`；明喻 2.02 / 2.27 / 2.48。单篇各 9/10（内心或话说一半），全绿不作停机。E 未开：`bill_holder` 仍在；等人评再退闸、拉 R1/R2。R1 0.5463 / R2 0.2256 未过线。

### craft3 · 母题坍缩修正（2026-08-26，已被 v4 取代执行顺序）

SSOT：[`docs/plans/2026-08-26-craft-v3.md`](./plans/2026-08-26-craft-v3.md)。在 Warp 上按单次 goal 执行。
**为什么换**：craft2 的 A 样章《夜班差三百》被作者判不合格——「和已删掉的旧样本一个味道，又是对账」。
**查明的机制**：铜炉 214 张卡里 135 张含「账」（**63%**），诡秘 1394 张里只有 197 张（**14%**）。「账」是铜炉的**题材母题**，不是写法通则。而 `structural.py` 把 `bill_holder` 设成必填（`duty_holder_empty`），逼系统写任何题材都先造一笔账。样章已绕开闸仍然对账 → **病根在语料母题未分层，不在闸**。
**被推翻的假设**：不是「会拆就会写」。**尺子本身会变成模板**。新原则：拆解产物只能当写完后的**检查表**，不能当写之前的**填空提纲**。
**改了**：A 母题分层（纯脚本零 LLM，「账」须落进单本母题档 + 建黑名单）→ B 反转生成顺序（处境由 `premises.json` 外部随机给，必须是事件不是流程；提示里不给 21 段清单）→ C `prose_check.py` 文风机械闸（明喻密度/对话冗余/答非所问/开篇事件/结尾总结句/母题黑名单，先拿旧样章验证应六项全红）→ D 一次三篇不同题材交作者读 → E 才回到拉分。
**没改**：三条铁律、留出集 hash、已冻尺子 `stop.json`、诡秘探针、快速集。
**新增红线**：母题黑名单命中 = 本篇作废重写，不许辩解「这题材天然要算账」。
**token**：A/C 零调用，B+D ≤6 次，前四步总预算 ≤ 旧方案已耗量的 2%。
**现状（craft3 本轮）**：A 分层已落盘，「账」在单本母题。B `premises.json` 12 条，抽签 p04/p07/p11。C 《夜班差三百》prose_check 六红。D 三篇已交：`docs/craft-samples/D1-当代家庭.md`、`D2-海运.md`、`D3-幼儿园.md`（各 6/6，coding 3 次）。E 未开。`bill_holder` 仍在，退役最前。R1 0.5463 / R2 0.2256 未过线。

### craft2 · 两本参照（2026-08-26，已被 v3 取代执行顺序）

SSOT：[`docs/plans/2026-08-26-craft-two-books.md`](./plans/2026-08-26-craft-two-books.md)。在 Warp 上按单次 goal 执行。
**为什么换**：旧路烧了约 300+ 次长调用（粗估 500–600 万 tonglu token），作者至今没读到系统写的任何一段小说；且单本无法区分「学会写法」和「背熟铜炉」。
**改了**：A 先产人能评审的样章（≤3 次调用）→ B 接《诡秘之主》做跨书探针（先解决「节/章」字段名不一致）→ C 快速集+换通道砍 token → D 两本一起拉分，每轮必跑跨书探针。
**没改**：三条铁律、留出集 hash、已冻尺子 `stop.json`（R1 线 0.70 / R2 线 0.775）。
**现状（craft2 本轮）**：A 样章已交 `docs/craft-samples/A1-当代职场.md`（作者评；1 次 coding，非 hermes）。B 节/章归一 + `chapters_lotm.json` + 探针冻 `85674429…da10a`；金卡对金卡 n=20 mean=1.0。铜炉 r1_before pred 重打仍 0.439。C 快速集 8+4 已冻；`--provider` 默认 coding。C.3 R2 瘦身未开（单独轮）。D 未跑模型拉分。R1 0.5463 / R2 0.2256 未过线。

### craft-eval · 会拆才会写（2026-08-26，v1 归档）

现行循环 SSOT：[`docs/plans/2026-08-26-craft-ruler-loop.md`](./plans/2026-08-26-craft-ruler-loop.md)（`craft-eval`）。先拆后写。P1 不写小说。
**P0 齐：** 留出冻结 hash `fb460682…da4649`。母本 30812 行 gitignored。现网三本书已 purge（手术室 / 井台灯 / 腕账），`/works` 空。
**P1.1–P1.5：** 拆卡 / R1 / 负样本 / R2 / 停机线已接线并冻结。tag `craft-eval-ruler-v1`。`stop.json`：R1 0.70 / R2 0.775。冻结 ≠ 过线。
**R1 before（冻结）：** 留出 41 章均分 **0.439**（打开书 0.0976 / 回不去 0.2927 / 热怎么变冷 0.3415 最矮；翻了 0.9024）。
**R2 before（齐）：** n=164 score=**0.2256**（clean 0.9024 / cut=pump=lecture=0）。`--jobs 6` resume，无 `R2_MISSING`。这是 before，不是事故。
**盲评：** `blind_r1_before.json` 机械 0.439 / 盲评 0.8098 / 一致率 0.4927。人抽查清单 `human_spotcheck.json` seqs 14/148/160/194，不空等作者。
**并行：** 12 分钟 tick 已停，单次 goal。`pool.py` + `--jobs`（`test_craft_eval_jobs.py` 绿）。
**打开书 after（齐且涨）：** 探针解除 429 后 `--jobs 1` resume。`r1_after_openbook.json` n=41 mean=**0.5463**（before 0.439）。打开书 **0.3415**（before 0.0976）。未覆盖 `r1_before.json`。仍 < stop 0.70。
**goal：** 下一件 = 仍在 P1，打「回不去」。after 新 label、`--jobs 1`。未进 P2。

### 时间线列表+抽屉（2026-08-25）

时间线合同仍是「事在何时」。列表点选只开抽屉，不离开时间线；跳章只走抽屉「跳到第N章」或双击。vis 轴默认可见（没有「看图」开关，不重蹈图谱藏图）。有当前写作章时首屏拉 N-5…N+5，不再默认书末 50 章。空态分「还没有事件」/「这窗里是空的」。抽屉多一粒「围绕这件事写下一笔」（只讨论，不写库）。
**已改并热更：** `954ed164`。frontend `FRONTEND_DEPLOY_OK`，首页 `index-LUaF09u3.js`，懒加载 `TimelineView-COj0K3DN.js` 含「围绕这件事写下一笔」/「还没有事件」/「这窗里是空的」。强制刷新后再开时间线。nginx unlink busy 非致命。测绿 ≠ 视觉过。

### 图谱先可读再助写（2026-08-25）

知情图不再默认甩力导向网。列表+抽屉是主阅读面；画布「看图」才展开。默认章切片跟 `qualitySeq`（刚写过的章）；全书要显式选。空图说清缺知情边/角色。抽屉多一粒「用这个信息差写下一笔」（只讨论）。
**已改并热更：** `63bd3603`。frontend `FRONTEND_DEPLOY_OK`，首页 `index-CjfTCmM2.js`，懒加载 `AtlasView-CFhaZ5wE.js` 含「谁知道什么」/下一笔。强制刷新后再开图谱。

### 顶栏搜索压住「仪表盘」（2026-08-25）

横切视图 nav 默认可收缩，子按钮 `shrink-0` 溢出去，后绘制的搜索盖住最后一项「仪表盘」。
**已改并热更：** `698d63d2`。品牌/作品/视图/搜索收进不可压缩主群；进度胶囊自己 `flex-1 min-w-0` 让位。相关 vitest 6 passed。1100px 包围盒间隙 14px、无重叠。frontend `FRONTEND_DEPLOY_OK`，首页 `index-D1A__Skd.js` 含 `topbar-primary`。强制刷新后再看顶栏。

### 弱章跳转回弹（2026-08-24）

现网点弱章先到技法标尺质量审阅，随后弹回总纲。根因：`quality_review` 不在上下文 `FocusType` 白名单，`focusForNode` 把它记成 `view`；快照一确认，投影就把栏3当横切视图，再叠门厅空选就回总纲。换书时 `hallTick` 若因回调换身份再 bump，也会冲门厅。
**已改并热更：** 后端/前端白名单加 `quality_review`；旧 `view:quality:N` 快照投影回质量审阅；换书门厅只 bump 一次。`a7447770`。hot `HEALTH_OK` + v634 26/26；frontend `FRONTEND_DEPLOY_OK`，首页 `index-BYdTmhBE.js`。强制刷新后再点弱章。

### 仪表盘审计修复（2026-08-24）

**已改：** `InsightView.jsx` + `targetNavigation.js`。
- 质量汇总失败不再卸掉整页：码字进度、伏笔台账仍在；横幅「质量汇总加载失败」；图表/弱章隐藏。
- 弱章点进左轨 **技法标尺** 的 `quality_review`（`quality:N`），不再伪造无证据区间的 `review_issue`。
- 已删埋章是不可点文案（`insight-setup-missing`），不跳章。
- 码字文案改成「码字进度（工程配额）/码字配额」，摘要写明不是总纲「写到/立到」。
- 正文呼吸默认最后一章 `lastSeq`，改书后同步。
**测：** 相关 vitest 6 文件 23 passed。
**现网（admin · `book_e4a6e353`《腕账》）：** 仪表盘副标题「质量 · 伏笔 · 码字」；「码字进度（工程配额）」/「码字配额」6,318 / 1,000,000；摘要写明不是总纲进度。质量汇总这次加载成功（质检问题 -8）。弱章「第3章 · 灯罩里的母亲」点进左轨技法标尺、中区「质量审阅 第 3 章」、主编上下文 `quality_review`。无「全局规划」。未登录 `GET /api/works` 仍是 401。

### 作者面去重叠（2026-08-24）

职责清单：[`docs/plans/2026-08-24-surface-ownership.md`](./plans/2026-08-24-surface-ownership.md)。总纲读这本书，旅程管下一步，跨章弧（参考）挂在旅程底部折叠，仪表盘只做质量/伏笔/码字。旧 `storyline`/`planning`/`arcs` 进旅程，不再进仪表盘。禁止「全局规划」顶栏。
**现网点过：** 旅程有「下一步」；底部折叠「跨章弧（参考）」展开后是可选登记，不替代总纲/大纲/伏笔。仪表盘无规划区。相关 vitest 15 passed。

### 本机同步（2026-08-24）

- 本机 `main` 已含弱章回弹修复并推 origin。demo 已 hot+frontend（`index-BYdTmhBE.js`）。frontend 打包去掉 AppleDouble；hot 解包后清 `._*` 并 `chmod a+rX`，否则 `docker cp` 会 unexpected EOF。
- 部署机 SSH：`ssh scribe3-demo`（`82.157.130.140`，密钥 `~/.ssh/id_tencent_lh`，绑 `en0` 绕开 VPN）。直连不绑网卡会卡在 banner。
- 「同步云端」= 代码 + SSH，不是把云端书库导回本机。

### 拆文薄切片已写并核过（2026-08-24）

[`worlds/乱世铜炉-拆文/对照.md`](./worlds/乱世铜炉-拆文/对照.md) 50 行：距离、假破真、办事不剖心；有「不要学」。参照本 §二十七有指针。八条书证都能在拆文包里对上（本机无全文，未回原文）。`缺口.md` 第一层「可以停」未改。现网点验《腕账》不改拆文包。不要再扩 214 份。

下一本翻：〇 → 二十二 → 章法 → 七场批注 → `因文.md` → `对照.md`。

### Qoder 深度拆书方案已归档（2026-08-24）

[`docs/plans/2026-08-24-tonglu-qoder-deep-analyze.md`](./plans/2026-08-24-tonglu-qoder-deep-analyze.md) **不是**执行方案。审查：范围错（43 章/25.7 万字是节选，全书 214 节）、配额填表、与已落地拆文冲突。拆书真源仍是 [`worlds/乱世铜炉-拆文/`](./worlds/乱世铜炉-拆文/) + mentor-extract / mentor-craft 两份设计。不要按 Qoder 文开拆，不要把铜炉情节灌进 Surreal。

### 质量仪表盘加载失败（2026-08-24）

修好了。后台读质量汇总时少带了一个函数，页面就会说加载失败。现网 `book_e4a6e353` 能读到 12 章。

### 总纲改成书的肖像（2026-08-24）

设计稿：[`docs/plans/2026-08-24-synopsis-as-book-portrait.md`](./plans/2026-08-24-synopsis-as-book-portrait.md)。总纲是读书（书的肖像），旅程是动手（向导）。

**已落地 PR-1～4：** 打开书 / 从章点「总纲」落到空选门厅（hub 先退再 `hallTick`）；中间是肖像：书名、`north_star`、卷章进度（写到/立到）、人、规矩、母题、未收的账。点「让主编写入」派 `s3-right-tab=chief`。首屏只拉 outline + intent + entities + world-rules + motifs + promises/ledger；评分卡要点开才算，reconnect 不拉 snapshot/quality。写作台 `NorthStarBar` 未改。PR-5 `who_pays` / PR-6 `GET /book-portrait` 另案。

**现网已验（2026-08-24）：** `https://tonglu.qing.blue` 已热更。`book_e4a6e353`《腕账》打开即门厅（目录还在）：书名、北极星、写到第 3 章、人/规矩/母题、还没收回 3 笔。从第 3 章点「总纲」回到门厅，不卡写作台。空书《手术室》空态 +「让主编写入」会把 `s3_set_intent` 种子送进右侧主编。系统中心点「总纲」先退 hub 再落门厅。总纲首屏有 outline/intent/entities/world-rules/motifs/ledger；无 quality / north-star/book。顶栏「继续」仍会打 `workflow/snapshot`（不是总纲自己）。
**交互补刀（现网点过）：** `book_e4a6e353` 总纲门厅「把这本书当一本书来读」。点卷名「讨账」只展开该卷，仍停在总纲；「看这卷」进 `volume-detail-pane`（讨账）。人名单 4 人，没有「去设定库」（未过 12 人阈值）；块里仍有 `synopsis-open-codex` 路。空书《手术室》总纲写「还没有人。」，没有 `synopsis-cast` / 「去设定库」（`hidden>0` 才出，空书验不了这条链）。强制刷新后再验。

### 铜炉最优化改造（2026-08-23）

规格与编号台账已落仓：`docs/plans/2026-08-23-tonglu-optimization-spec.md`、`docs/plans/2026-08-23-tonglu-opt-ledger.md`。

止血已做：目标字数为 0 不再除零；归档角色不再进写作名单；设定补丁按登记表保存；章锁挡住同章双写；超期伏笔满 3 条会拦住开写；危险管理操作要二次确认。

正典批过之后会把摘要、秘密桥、检索一起跟上。删设定会清关联。提案刷新后还能按编号找回。

未做完、台账里写成「产品决定/推迟」的：自动生成数据库表结构脚本、时间线因果弧线、旅程完成仪式等远期项。

### 统一度收口（2026-08-22 第九轮）

已做：判定只认新出口；「学到了几条」改走中性字段，错误字段只留一轮兼容。对话对不上时名片还在，不变薄。

未做：GitHub 分支保护要你自己去勾（第五次）。前端请强制刷新。

### 戏为唯一主人 · play-contract（2026-08-19）

章设计改成：责任卡 → 写戏 → 抄契约 → 演绎 → 排演 → 正文。旧大纲/节拍生成返回 410。戏过审冻结后 force 改不掉。demo 已热更；`book_b0beed49` 第 1 章能读到冻结戏，duty 层 force 后戏的 sha 没变。

### 章设计接得上这本书 · design-book-continuity（2026-08-17）

> **设计** [`docs/plans/2026-08-17-design-book-continuity.md`](./plans/2026-08-17-design-book-continuity.md)

- 短名 `design-book-continuity`。细旗 `SCRIBE3_DESIGN_BOOK` 默认 **on**（`CHAPTER_DESIGN` 关则本旗也关；typo→off）。
- 过检从「表格填满」扩成「这一章接得上这本书」：人/地/咬/线/左右镜像。仍一道 `evaluate_chapter_design`。不传 book 时旧格式金样仍绿。
- 写之前发本书硬卡（人名/线 id+正文/上章钩与地）。简介在带章纲落库时用章纲覆盖。不自动建人、不自动种线。
- 有 store 不传 book → 422 `design_book_missing`。验收用**新书**，不 overlay `book_44eb8789` 及名单旧书。
- **现网冒烟书** `book_21f2dca9`：ch1 主编一次过；ch2/3 点批过检后落库。负例「对手周青臣」→ `cast_invented`；第2章标题箱锁却挂指针态线 → `line_wrong_bind`。不 force 再写 → 跳过。
- **2026-08-17 按 6.3.4 重写前三章+设定：** 现网只留 **`book_7042c28c`《万界概率战争》**（已改成这个书名）。先种设定（沈拾灯人物卡、金縢之箱/场核碎片/令牌、术语、华山北峰/伪真空口、守火人、世界规则、三条母题、两条线）。三章《华山成核》《金縢箱锁》《双锚伪真空》设计已过检落库。第2章主编一次过；第1、3章点批过同一套检查。历史验收书已从书库永久删掉。系统书《乱世铜炉·设定参照》也已从现网摘掉。本轮仍只写到章设计，未写演绎/正文。

### 大纲/节拍融合 · outline-beats-merge（2026-08-17）

> **设计** [`docs/plans/2026-08-17-outline-beats-merge.md`](./plans/2026-08-17-outline-beats-merge.md)

- 短名 `outline-beats-merge`。旗 `SCRIBE3_CHAPTER_DESIGN` 默认 **on**。
- 规范阶段 `design`：一次 LLM、一次 persist、一道 `evaluate_chapter_design`。落库仍是 `chapter_spine` + `beats[]` + `beats_meta.schema_design=chapter_design.v1`。
- 验收须**新 slug** 第 1 章融合节点。`book_718fe88f` 只作双节点病灶考古，**不 overlay**。
- 合法写：主编 / 点批整份 / generate-stage=design / `/chat/write`。创建半稿 → 422 `design_half`。旧脚本单独 beats → 422 `stage_merged`。
- 协议 **v6.3.4 rev.11**：只改 OpSeq 叙述与 KD-25；总 PASS 公式 / GATE-B / WCG / SPA **不改**。
- **2026-08-17 优化 6.3.4 + 新书三章设计：** 协议加 **rev.11 本轮只写设计节点**。ASK 改为格式先于洪水（`## 拍1/2/3`、短 A vs B、线 id 置顶）。新书 **`book_44eb8789`**《万界概率战争·v6.3.4rev11·三章设计·20260817c》：intent 已设；promise `7mlc0hskmmndl0cmyxkg` / `9g8pq9n16fbt1o9ungh3`；storyline `sl_20ff834e8b`；三章壳《华山成核》《金縢箱锁》《双锚伪真空》。ch1 `stage=design persist=true` 多轮均 **422 llm_thin**（`spine_density` / `beat_gcd` / `beat_leak`），**未落库**——闸按方案拒半稿。不 overlay 旧书。不写演绎/正文。

### 小说家第二刀 · 命运变贵（2026-08-16）

> **设计** [`docs/plans/2026-08-16-fate-dearer-novelist-reform.md`](./plans/2026-08-16-fate-dearer-novelist-reform.md)（scratch 同源 `/tmp/grok-1000/grok-design-doc-c58fdafc.md`）

- 病灶：一场好戏 ≠ 一部小说（同门同纸、钟停在当夜、矿当氛围、种子无户口）。
- 方案 **rev.8**：场景坐标 = 命运 × 钟 × **地点**。`setting` 启发式退役硬闸。
- **用户终裁：** 字数不作手段；炉灰记 / `book_e415dfeb` 不 overlay；钟/地都不是唯一主轴，也都不是装饰。
- **现行已落地：** `FATE_DEARER=on` + `FATE_WAVE=2` + `PIPELINE_RECORDER=1` + **`WORLD_SURFACE=on`**。WAVE-1 含 `cast_role_frozen` / `world_fact_*` / `goal_off_world`，以及水面孪生 `surface_claim_unpaid` / `claim_paid_by_paraphrase` / `gesture_echo`。extra 后置【世界合同】；命令语气走 `extra_authors`。F3b/c 分批硬闸是历史切片，勿再当部署清单。
- 协议 **v6.3.4 rev.10**。本轮验收书 **`book_718fe88f`**（`万界概率战争·v6.3.4rev10·三章水面·20260817`）。ch1–3 已有定稿；质量审查 [`docs/audits/2026-08-17-book718fe88f-ch1-3-quality.md`](./audits/2026-08-17-book718fe88f-ch1-3-quality.md)：**未完全按方案**（ch2/3 大纲节拍点批；水面只付组内一词）。`book_83584141` 只作上一轮 ch1 样本，**不 overlay**。旧书 `book_61a7935e` / `book_e415dfeb` ch8/9 **不 overlay / 不重写**。
- 本书户口：promise `fo0rzii5phykb4gm0ojr` 十八个月深渊碰撞 / `22bx5lg7mn4e2y64r00a` 肉体三年碳化 / `o47d4lnrtvzmha2omh4a` 金縢因果封印；storyline `sl_3887096383` 金縢未开。
- **ch1《华山成核》OpSeq 已跑完**（outline→beats→deduce→draft→final，均 `persist=true`）。钩：`成核点开始复制他的指针态`。**现网终态已付清**：卡 `wc.ch1.nucleation-pointer`，定稿含成核点+指针态+大遮蔽。初稿曾把成核点写成黑针（符合度 P0 / 热更前只读红），`force=1` 重跑 final 后已不是现网终态。
- 符合度审查：[`docs/audits/2026-08-16-book83584141-ch1-reform-gap.md`](./audits/2026-08-16-book83584141-ch1-reform-gap.md) 记录的是付清前切片（闸绿、水面丢词）。
- **打破补丁循环设计（已审定并落地）：** [`docs/plans/2026-08-16-world-surface-break-the-loop.md`](./plans/2026-08-16-world-surface-break-the-loop.md)。短名 `world-surface`。设置页可拨 `SCRIBE3_WORLD_SURFACE` on/off。

### v6.3.4 rev.6 · 万界换锚（2026-08-15）

> **协议** [`docs/e2e-director-journey-v634-true-chat-full-capability.md`](./e2e-director-journey-v634-true-chat-full-capability.md) **rev.6**  
> **宇宙 SSOT** [`docs/worlds/wanjie-probability-war-v7.md`](./worlds/wanjie-probability-war-v7.md)

- 默认验收宇宙 = 《万界概率战争》V7.0（柳岸青 / 沈烛 / 赫斯 / 兰因；三卷囚笼·泄露·第三条路）。
- 炉灰记与 `book_bdfdcdc4` **退役**，不得续写冒充本版总 PASS；必须新建 slug。
- 产品闸不改：13 槽、密度、OpSeq、SPA、WCG、宣称。
- 章纲闭环工程审查（假铜复演 / `role:以为` / `st` 未传）仍有效，金样改为万界原子。

### 章纲闭环 + 三章验收审查（2026-08-15 · 考古）

> 当时验收书 `book_bdfdcdc4`（炉灰记合同）。**rev.6 起不再当总 PASS 书。**

### 冰山完整方案（2026-08-14）

> **短名：`iceberg`** · **SSOT** [`docs/plans/2026-08-14-iceberg-complete.md`](./plans/2026-08-14-iceberg-complete.md)  
> 合并：闸 / 生成链（必须 LLM）/ 注入对齐。旧三文降为考古。  
> 未并入：142 飞行记录仪、book79 N1–N5（另案）。

- **回答**：原先**没有**独立 outline/beats/deduce/draft skill。SPA 只是同一 `/chat/write` 换 phase；唯一较独立的是 pilot `expand_beats`，还带切句充数。
- **已落地 G1–G5**：`scribe3/stage_generate.py` StageSpec；`thicken_*` 必须 `llm_fn`；薄稿不 skip；禁大纲切句 / 摘录占位 / 空白五栏；`POST /generate-stage`；`s3_generate_stage` + `s3_save_chapter_draft`；分阶 `max_tokens`；`stage_ready` 409。
- **注入**：final **也吃满**演绎/排演（用户裁断）。`clip_for` 刚过闸不裁；拍不再 200；draft_full 登记并 L2 保护。
- **未做**：提交 / 部署 / G6 空章真链。未 push。
- **轻测**：stage_generate + iceberg + inject + outline L2 + deduction_final **41 passed**。

### 故事招式库 + 38 融合（2026-08-13）

> **短名：`move-library` / `38 融合`** · 设计 [`docs/plans/2026-08-13-oh-story-38-fusion.md`](./plans/2026-08-13-oh-story-38-fusion.md) · [`docs/plans/2026-08-13-move-library-design.md`](./plans/2026-08-13-move-library-design.md)

- **状态**：已上 demo（`402a46d` + 本轮写环）
- **入口**：系统中心 → 技法与招式（三栏：技法 4 / 招式 5 / 编目 37）
- **卡全集**：triangle_info / bond_tear / one_word_crush / speech_wither / withhold_escalate
- **写环**：章信息「登记这一圈」REST；系统中心可提案新卡（假破真并三角）；`POST /story-moves` + `/review`
- **注入**：旗 `SCRIBE3_MOVE_LIBRARY` 默认 0；无已批计划零字节
- **女频**：编目隐藏

### 工程健康度结案（2026-08-12）

- **状态**：Accepted · main `9656d33`（代码锁 `cb64141`）
- **结案**：`docs/plans/2026-08-12-engineering-health-closure.md`
- **分层**：业务层私有 store 调用 = 0；钉 `test_next_layer_adapters_no_private_store`
- **冒烟**：`./scripts/smoke_eh.sh` → `DEMO_EH_OK`
- **包 B**：`scribe3/soft_fail.py` + 热路径 warning；组装可选 DEBUG  
- **包 C**：`write_assemble_v1` / `write_assemble_discuss`；`critique/rules/*` 可 import（无 exec）  
- **契约**：`test_eh_residual` 34 passed；`./scripts/smoke_eh.sh`

### v6.3.4 验收脚手架（2026-08-12）

- **协议**：`docs/e2e-director-journey-v634-true-chat-full-capability.md`（rev.2）为唯一体验总 PASS  
- **指针**：2w-memory / 5w / v633 文首 PR-Doc-2 五行李  
- **清单脚本**：`scripts/v634_evidence_checklist.py` + pure tests  
- **本轮执行**：工程脚手架 + demo runtime baseline；**无真人 SPA → 不得总 PASS**（见 evidence 包结案 PARTIAL）

### ctx-audit · 96k/48k 写路径块段审计（2026-08-13）

> **短名：`ctx-audit`** · `docs/audits/ctx-audit-20260813/`（W0–W5 齐：库存 + 52 卷宗 + `MATRIX.md` / `RECOMMEND.md`）
> 现网 `NOVEL_PROMPT_HARD=48000`。P0：接线 story_* 燃料；合同 store；deduction 硬帽。
> **自动修分循环**：`ctx-audit-fix` · [`FIX-LOOP.md`](./audits/ctx-audit-20260813/FIX-LOOP.md)（`/goal` 贴文内 GOAL 正文，跑到 MATRIX 诚实满分或天花板）

### craft-loop · 真人视角块门 + 改进闭环（2026-08-12）

> **短名：`craft-loop`** · `继续 craft-loop` 或读 [`docs/plans/craft-loop.md`](./plans/craft-loop.md)

- **状态**：Accepted Draft **0.3.1**（design 循环共识；**实现暂缓**）
- **证据模板**：`docs/evidence/craft-loop-TEMPLATE/`
- **性质**：CL-B0…B6 第一性 hard + 运营 + P/C/T/M/A/K 根因 + 改系统 + `deploy_demo` 同场景复验；**≠** 50k-e2e；**≠** v6.3.4 总 PASS
- **用户已决**：CL-B1 **全绿**才进 B2（无 partial）；先只看设计
- **下一步**：用户再要求时再开 PR-1 CLI / demo 试点

### 50k-e2e · 5 万字 CLI+Playwright 验收（2026-08-12）

> **短名：`50k-e2e`** · 新会话直接说「继续 50k-e2e」或「读 docs/plans/50k-e2e.md」

- **硬化设计（Accepted 0.3）**：[`docs/plans/50k-e2e.md`](./plans/50k-e2e.md)（PR-0…7；实现暂缓）
- **旧长文件名指针**：`docs/plans/2026-08-12-50k-acceptance-hardening-v2-design.md` → 同上
- **方案 v1 脚手架**：`docs/plans/2026-08-12-50k-cli-playwright-acceptance.md`（B- 基线）
- **入口脚本**：`./scripts/run_50k_acceptance.sh`
- **实现目录**：`scribe3/web/e2e/acceptance_50k/*`
- **性质**：已部署栈长程自动化；**≠** v6.3.4 体验总 PASS；**≠** craft-loop
- **要点**：三级判定；WCG；checkpoint 迁移；分章 re-launch

### 控制面活地图（2026-08-10）

- **P0a**：`mcp_catalog_build` 扫描 async def；gate 分档 world_write=48 / manuscript / ingest / read  
- **P0b–P3**：SystemHub 默认「总览地图」；六模块说明；任务旋钮精确 keys；中文能力注册表（无执行按钮）  
- **设计**：`设计文档/2026-08-10-控制面活地图-模块说明与任务旋钮.md`


### 系统中心 System Hub（2026-08-10）

- **App 全页** `SystemHub`（`viewKey=system`）；无书可开；DetailPane 设置已迁出  
- **RBAC**：`Setting.audience` 默认 admin；connection/flags/gateway 全 admin；craft + 3 llm 键 author；`assert_setting_writable` + gateway 写/重启 403  
- **API**：`/craft-skills` · `/mcp/catalog` · `/data/health` · `/admin/data/tables|rows`  
- **三平面**：写作 / 运行时·数据 / 运维·危险  
- **设计**：`设计文档/2026-08-10-系统中心-管理设置与Hermes-Surreal统一改造.md`



| 项 | 值 |
|----|----|
| **更新于** | 2026-08-10（**系统中心 System Hub** PR-0…5） |
| **旧更新** | 2026-08-10（**卷/章信息架构改造 PR-1…5** 实现 + demo 冒烟） |
| **产品名（UI）** | 铜炉 / tonglu（仅品牌文案+logo，色板未改） |
| **默认分支** | `main` |
| **刚完成** | 卷/章 IA：章前契约页、outline write 注入、volume_intro、final soft banner、focus 去重 |
| **设计** | [`设计文档/2026-08-10-卷章信息架构改造.md`](../设计文档/2026-08-10-卷章信息架构改造.md)（r2 Accepted · 实现中/已实现） |
| **进行中目标** | demo 部署验收；记忆质量 / 人盲 |
| **主验收书** | **`book_aa57f17e`** / **`book_7b918ca0`** |
| **活跃分支** | `main` |

### 卷/章信息架构改造（2026-08-10）

- **热修**：`568dede` rebind-safe `_VOLUME_INTRO_BUDGET`；demo 真库 assemble 两次一致（book_aa57f17e ch3）

- **UI**：`ChapterMetaPane` 章前契约合成页 + `lib/chapterContractGate.js`（B1/B2/B3 soft）  
- **写栈**：`_outline_block(mode=write|plan)` 挂 draft/final；focus 指针 + `source_id=chapter:N:focus`；`_volume_intro_block` ~400  
- **soft**：`ChapterStudio` final 亦拉 meta；`ContractSoftBanner` + 切 final toast（不拦 chat-write）  
- **卷页**：intro 注入说明 + 缺大纲角标  
- **测**：`chapterContractGate` node pure 6 pass；pytest outline/focus/volume_intro 已改写（demo 跑）  
- **部署**：`./scripts/deploy_demo.sh`（hot + frontend）

### 图谱节点抽屉 · 戏剧操作台（2026-08-10 PR-A）

- **纯函数**：`web/src/lib/atlasNodeDetail.js`（neighbors / knowledgeDiff / hop-boost / secret）· `atlasChiefSeed.js`（discuss）  
- **UI**：`views/atlas/NodeDetail.jsx` 三层；`AtlasView` hop 保留 picked（KD-19）；列表 pick+设定  
- **修**：faction/item 打开设定不再误标 proposition  
- **测**：`run-atlas-unit` ALL_PASS；demo SPA 标记双跑 + `book_aa57f17e` graph×helpers  
- **证据**：goal scratch `atlas-drawer-unit.log` · `demo-atlas-drawer-smoke.md` · `demo-drawer-sim.json`

### 角色弧光完善（2026-08-09）

- **模块**：`scribe3/arc_signals.py`（纯函数）；接线 `pulse._arc_dim` / `brief.assemble_chapter_brief` / `arc_directive` focus 驱动  
- **假绿**：无 eligible → info「未启用可忽略」；主档缺 lie → decision；**禁止**「未见跳变」当健康；配置态 **不** `degraded`  
- **节拍**：`arc_beat_focus` 每角一条；`miss_belief` 有向；brief ⚠ 与 pulse decision 同文案源（工具名可执行）  
- **工具**：MCP `s3_add_arc_beat` / `s3_delete_arc_beat`；`s3_add_char_state` + REST `POST /char-states` 透传 `lie_belief`  
- **UI**：`CodexDetail` 消费 `alignment`、冷启动条、质变历史折叠  
- **测**：`scribe3/tests/test_arc_signals.py` **14 passed**  
- **demo**：hot+frontend；HTTP pulse/brief **写前/写后** 捕获；MCP `commit_if_approved` 自动批写入 belief=88 + beat add/delete；URL 编码 GET anchors.alignment  
- **证据**（goal scratch）：`demo-chapter-pulse-before/after.json`、`demo-char-anchors.json`、`demo-char-states.json`、`demo-arc-smoke.md`、`demo-arc-write.log`  
- **注**：世界 REST 写默认关；章节验证写路径走 **MCP 工具**（与产品口径一致）

### 章节流水线闭环（2026-08-09）

- **模块**：`scribe3/ingest_lease.py` · `scribe3/ingest_policy.py` · migration **112**
- **单入口**：`schedule_ingest` / `run_or_enqueue` 覆盖 save / checkpoint / loop / restore / 终选 / dedup·polish·semantic_repair / POST `/ingest` / import / accept_unverified / MCP `s3_ingest_chapter` / `_bg_ingest` 占锁
- **KD18**：advisory hold 后 `checkpoint(final)` 同 prose_fp → `active_hold_supersedes`，**不 enqueue**
- **MCP**：`s3_save_chapter` 对齐 `evaluate_save_craft_gate`；blocking 不落库
- **API**：`POST /ingest/confirm`；`GET /ingest/status` 扩 held/lease；capabilities 报 `ingest_lease`/`ingest_policy`/`mcp_craft_gate`
- **测**：`scribe3/tests/test_ingest_pipeline_policy.py` **15 passed**；证据 `/tmp/grok-goal-c24de3662f01/implementer/`
- lease CAS：migration **113** `ingest_lease` 表 + `TableLeaseBackend`；purge 前 assert owner  
- residual：SPA hold 确认条、token 哈希化（见 residuals.md）

### 上下文检查器 B∪C（2026-08-09）

- **根因**：检查器只读空 `memory_trace`；讨论不编译；写路径合成 snapshot 与 UI 脱节；六块假 0。  
- **读模型**：`context_turn_view.py` · `GET .../trace/{rev}` 聚合 TurnBind（优先）+ memory_trace 明细。  
- **写模型**：migration **111** `context_turn_bind`；每次成功 compile 且带 session+revision 即落库。  
- **讨论**：`discussion.v1` Policy + `assemble_discussion_system`；禁写作围栏协议。  
- **UI**：八块预算；`not_compiled_yet` 不画假 0；ChiefDock 凡 snapshot 即绑定。  
- **测**：`scribe3/tests/test_context_turn_view.py`（8 passed）。  
- **demo**：`./scripts/deploy_demo.sh hot` 后容器内 `DEMO_SMOKE_PASS`（discuss+write bind + handler）。  

### 旅程 5 万字 / 2 万字记忆

- 方案 v6.2 / v6.3.2 见既有进度文档；A/B D7 硬门槛未达见 `设计文档/2026-08-08-旅程2万字-记忆验收-进度.md`。  

### 下一步

1. SPA hold 确认 UX（PR-4 residual）+ 可选 token 哈希  
2. 前端 `deploy_demo.sh frontend`（若需公网 SPA 立刻见八块 UI）  
3. 待确认设定收件箱完善；记忆人盲仍须真人  
4. `git push` 后若需镜像重建再走 GHA / deploy 脚本（当前 demo 已 docker cp 热部署）  

### 已知坑

- Grok 机禁重活、**禁止本机起 Surreal**；验收只打 **已部署 demo**  
- **Surreal 唯一 3.x（demo 3.2.4）**：无 2.x 回退；`_migration` 仅 `type::record`；conftest 遇 2.x 直接 fail  
- 启发式 extract 可能过召回 → 人批拒  
- full_check AI 味 soft-pass ≠ 质量线自动绿  
- **Demo 40G 盘**：`compose --build` 会堆悬空镜像；见 [`docs/ops/demo-disk-hygiene.md`](./ops/demo-disk-hygiene.md)  

# 拆文倒逼系统翻主（loop SSOT）

短名：`tonglu-force-rebuild`。本稿 = 已批准方案 07c153be。进度只写这里。

旧过夜 `tonglu-chengse-overnight` **已结案，禁止续跑**。指针：[`2026-08-24-tonglu-chengse-loop.md`](./2026-08-24-tonglu-chengse-loop.md)。

---

## 真意

用 `docs/worlds/乱世铜炉-拆文/` 倒逼**整个写作系统**重构。不被现成 play-contract / 写协议 / `draft_len` / QC 限死。

代码与真源冲突时，**改代码**（含删层、关闸、换唯一写入口）。不能改拆文就口。

真源优先级：`对照.md` → `因文.md` → 七场批注 → 章法 → 参照本〇 / 二十二。

翻序给人开下一本：参照本 〇 → 二十二 → 章法 → 七场批注 → `因文.md` → `对照.md`。不要按 Qoder 提纲重拆，不要给 214 节写因文，不要把情节灌进 Surreal。

---

## 禁止

问选择题。重抽 214。铜炉情节灌 Surreal。通读全文。本机 Surreal。全量 pytest。npm ci。古白话当成色。QC / 十维 / 字数冒充成色。黄金三章 / 三次失败 / 开篇强钩子。先注水凑 10 万。只加提示词。overlay 《腕账》或名单旧书。把对照.md 当旁路提示而不接真源。

---

## 一轮一能力（锁死顺序）

每轮只拿拆文一条骨头。场不过 = 本能力未闭合。禁止写下一场、禁止加厚清账。

| # | 能力 | 拆文骨头 |
| --- | --- | --- |
| 0 | 反着教必死 | 写协议不得教古白话词表（本切片） |
| 1 | 日子 | 先立还在过的日子，奇事从日子里来 |
| 2 | 办事 | 看见谁办了哪一件、日子怎么变 |
| 3 | 假破真 | 先反面再破功 |
| 4 | 远近 | 共情把眼睛交给当场那个人 |
| 5 | 切 | 热过再冷，切在能听见看见的那一下 |
| 6 | 因文 | 一行本事说不完；删了那一截场会塌 |
| 7 | 热闹像翻了、处境没翻 | 热闹当场面也能过 = 系统还没这条 |

一轮必做：

1. 打开拆文对应节 + 现网 / 管线证据，写清「现系统为什么写不出这一条」（指到文件 / 闸 / 层）。
2. 若隐着的是架构（五层必走、`draft_len`、章末钩子闸、古白话写协议、QC 当完成）→ **翻主**：删层、关闸、换唯一写入口。台账写谁让改 / 为何更好 / 旧路差哪 / 怎么退。模板：[`2026-08-22-round8-ledger.md`](./2026-08-22-round8-ledger.md)。
3. 用**新书一场**作证据（可继《井台灯》`book_46cff31a`，不 overlay 腕账）。场不过不准写下一场。
4. 落盘 + commit 只含本能力。

三轮同能力仍是贴提示 / 改阈值 = `FAIL_LOUD`。

---

## 停机

先系统后字数。可停仅当同时成立：

- 七条能力（1–7）各至少有一场现网证据 + 翻主台账；且
- 写路径不再教古白话；且
- `对照.md` 已接进生成 / 审判真源（不是旁路提示）。

10 万是系统闭合之**后**的样例门，不得单独开跑。

三类真阻塞仍停：破坏性、设施死、计划坏到只能猜。

---

## 与旧物

- `SCRIBE3_CHENGSE_CRAFT` / `chengse.py` 可留作词表过滤，**不得**再当翻主本体。关旗 = 过滤与成色块停，**不**回古白话教学。回退这条能力 = revert，不是关旗。
- 《井台灯》`book_46cff31a` 可当证据书，不重开世界，不 overlay 《腕账》`book_e4a6e353`。
- play-contract 五层不再神圣；挡日子 / 办事就按翻主纪律拆。
- 过夜 goal 正文必须指向**本文件**。禁止再贴 `chengse-overnight`。

---

## 过夜 goal 正文（复制即跑）

```
执行 docs/plans/2026-08-25-tonglu-force-rebuild-loop.md
短名 tonglu-force-rebuild。先读 AGENTS.md 与 docs/SESSION.md。
一轮一能力，按文件锁死顺序。场不过不准写下一场。
禁止续跑 2026-08-24-tonglu-chengse-loop.md。禁止 10 万单独开跑。
禁止重拆 214、灌铜炉情节、本机 Surreal、全量 pytest。
对照.md 是真源；代码冲突改代码。
```

---

## 进度

- 阶段：对照.md 已接进生成/审判真源。七条骨头代码闭合。现网第2章责任卡/戏已冻。糙稿曾被 `draft_len` 2000 卡死，已翻主。
- 现网样例 slug：`book_46cff31a`《井台灯》
- 累计汉字：第1章 2305（3.2.6 过夜遗留，不算七闸证据）；第2章戏 837 / 责任卡已冻 / 定稿未落
- 能力闭合：0–7 代码闭合 / 现网场证据未齐（第2章糙稿在翻主前被字数闸拦下）
- 对照.md 进生成/审判真源：是（读原文，不是成色复述；热更已打进容器）
- 可停：否（缺现网场证据）
- 阻塞：无

### 能力 0 · 反着教必死

现系统为什么写不出（施工前）：关 `SCRIBE3_CHENGSE_CRAFT` 时 `_write_protocol_block` → `protocol_style_block` 回 `PROTOCOL_STYLE_LEGACY`，明文「多用端的、岂料、怎禁得」，并灌 `_LUANSHI_EXEMPLAR`（含「岂料」）。旗文案写「关=回旧文案」。这是教学路径，不是禁令。

已做：删 `PROTOCOL_STYLE_LEGACY` 与 `_LUANSHI_EXEMPLAR`。写协议无论旗开关都不教词表。关旗只停过滤 / 成色生成审判块。回退 = revert 本能力 commit。

证据：`scribe3/tests/test_chengse.py` 主路径 + 关旗都不含「多用'端的、岂料」；源码钉无 `PROTOCOL_STYLE_LEGACY` / `_LUANSHI_EXEMPLAR`。本切片不写《井台灯》下一场。

### 能力 1 · 日子

现系统为什么写不出（施工前）：`check_duty_struct` 只问 `must_happen` 非空。开篇报身份、扔钩子、先宣布法会也能过。`narrative_drive.openers_plan.first_beat_must` 催开篇外力，和对照.md「先立还在过的日子」反着。

已做：责任卡必有 `day`。报身份 / 扔钩子 / 先宣布法会 → `duty_day_announce`。糙稿/定稿开篇叙述同拒。开篇闸改成先立日子。升 `playbook.3.2.7`。回退 = revert。

证据：`test_duty_day_blocks_identity_announce`。本切片不写《井台灯》下一场。

### 能力 2 · 办事

现系统为什么写不出（施工前）：duty/play 只验「有对手拍」「一件可演的动作」。鉴定式人设、杯子余温、剖心、嘴上要的等于真正缺的，也能过。对照.md 三要「用办事说」。

已做：责任卡必有 `said` / `needed`，两栏必须打架。鉴定/剖心 → `duty_work_appraisal`。升 `playbook.3.2.8`。回退 = revert。

证据：`test_duty_work_blocks_appraisal_and_same_want`。本切片不写《井台灯》下一场。

### 能力 3 · 假破真

现系统为什么写不出（施工前）：戏把两难当心脏（`IDENTITY_PLAY` / play 生成第 4 条 / 法官 Q5–6）。责任卡没有假破真栏。上来掏底牌、先把真意说穿，也能过。对照.md 二要「先给反面，再破功」。

已做：责任卡必有 `mask` / `crack` / `real`，三句必须转向。掏底牌 / 反面里已经说穿真意 → `duty_mask_dump`。戏改问先反面再破功。升 `playbook.3.2.9`。回退 = revert。

证据：`test_duty_mask_blocks_dump_and_same_sentence`。本切片不写《井台灯》下一场。

### 能力 4 · 远近

现系统为什么写不出（施工前）：限知/人称闸只问泄密和「我/他」。责任卡没有眼睛交给谁。开篇报「北宋，雍熙三年」、人还在办事时铺戒律上课，也能过。对照.md 一要「共情就把眼睛交给当场那个人」。

已做：责任卡必有 `eye` / `dist`。近时报年号/上课/把眼睛交给说书旁白不过。开篇叙述同拒。升 `playbook.3.2.10`。回退 = revert。

证据：`test_duty_dist_blocks_lecture_and_empty_eye`。本切片不写《井台灯》下一场。

### 能力 5 · 切

现系统为什么写不出（施工前）：成色块只把「切」写进 C6 问卷。责任卡没有切点。切在叹气、夜色深了、他决定了也能过。参照本十七要「切在手上那一下，不切在一段叹气上」。

已做：责任卡必有 `cut`。叹气/夜色深了/`他决定了` → `duty_cut_sigh`。没有能听见看见的那一下 → `duty_cut_not_sensed`。升 `playbook.3.2.11`。回退 = revert。

证据：`test_duty_cut_blocks_sigh_and_empty`。本切片不写《井台灯》下一场。

### 能力 6 · 因文

现系统为什么写不出（施工前）：成色块只把「因文」写进 C5 问卷。责任卡没有一行本事 / 删了会塌。整场能一行本事说完也能过。因文.md 要「一行本事说不完；删了那一截场会塌」。

已做：责任卡必有 `one_line` / `keep`。两句不能同一句。过场即可 / 说明书 → `duty_yin_one_line`。升 `playbook.3.2.12`。回退 = revert。

证据：`test_duty_yin_blocks_one_line_and_same`。本切片不写《井台灯》下一场。

### 能力 7 · 热闹像翻了、处境没翻

现系统为什么写不出（施工前）：成色块只把「热闹像翻了、处境没翻」写进 C1。责任卡没有热闹/处境两栏。热闹当场面也能过。参照本十七：热闹不算翻。怪墓村人信了，墓还在。

已做：责任卡必有 `heat` / `stay`。两句不能同一句。热闹就是翻 / 场面过了就算翻 → `duty_flip_heat`。升 `playbook.3.2.13`。回退 = revert。

证据：`test_duty_flip_blocks_heat_as_turn`。本切片不写《井台灯》下一场。

### 对照.md 进生成/审判真源

现系统为什么写不出（施工前）：`craft_generate_block` / `craft_judge_block` 吐成色复述（C1–C7）。对照.md 文件从未被读。关旗连复述也撤。这是旁路提示。

已做：生成/审判读 `docs/worlds/乱世铜炉-拆文/对照.md` 原文。找不到或空 = `DuizhaoMissing`。不跟成色旗走。升 `playbook.3.2.14`。回退 = revert。

证据：`test_duizhao_is_generate_ssot_not_paraphrase`。热更漏 `docs/` 时现网 `DuizhaoMissing`；已改 hot/镜像把对照.md 打到 `/app/docs/`。

### 字数不作完成 · `draft_len`
现系统为什么写不出（施工前）：`check_draft_struct` 硬拦去空白不足 2000。第2章戏已立住（井台还在排队、灯还在横担、油罐没掏），糙稿 1729 字被 `draft_len` 毙，场不过。这是字数冒充成色。
已做：`draft_len` 只拦没立住一场（不足 400 字）。生成提示改成场面立住就停。升 `playbook.3.2.15`。回退 = revert。
证据：`test_draft_len_does_not_kill_lived_scene`。第1章过夜遗留不算七闸证据。

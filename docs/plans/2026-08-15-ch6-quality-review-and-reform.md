# 第六章《炉冷之前》飞行记录仪 + 内容质量审查与改造方案

| 项 | 值 |
|----|-----|
| **文档标题** | book_c14585d8 第 6 章：卷宗审查 → 问题清单 → 最优改造 |
| **作者** | Grok Review |
| **日期** | 2026-08-15 |
| **状态** | Draft · 审查结论（本轮只出方案，不改代码、不重跑章） |
| **书 / 章** | `book_c14585d8`《炉灰记》seq=6《第六章 · 炉冷之前》 |
| **验收环境** | 仅已部署 demo `https://tonglu.example.com` |
| **协议** | `docs/e2e-director-journey-v634-true-chat-full-capability.md` **rev.4**（OpSeq / Ice7 / KD-25） |
| **证据根** | `/tmp/grok-goal-9f6336fb1f07/implementer/ch6-review/`（章 JSON + 10 条链原文） |
| **禁止** | 改宣称 / GATE-B / `GATE_SAVE_MODE`；本机 `npm ci` / Surreal / 第二套库；把 contrast red 或 HTTP 200 当质量 PASS |

> **一句话结论：** 定稿水面是本章最好的一层（10488 字，避开了锁眼、接上了「账勾了 / 门没开 / 门内咳」）。质量债主要不在「没写够字」，而在 **生成当时喂进去的四仪/戏剧槽是脏的、水下冰山泄漏锁眼、因果段后半截退化成 `event:i5-*`、记录仪 headline 撒谎、超窗伏笔没人点**。最优路径是 **修产品提取 + 记录仪诚实 + 只改冰山脏层**，不要整章重写定稿。

---

## 1. 卷宗地图

`GET /api/debug/pipeline-traces?work=book_c14585d8&chapter=6` 共 **10** 条。单链均能 `include=events,artifacts` 打开正文。防洪水 **dropped=[]**（帽 36k，未砍段）。

| 时间 UTC | phase | trace_id 前 8 | outcome | usage 字 | headline 摘要 | 工件要点 |
|----------|-------|---------------|---------|----------|---------------|----------|
| 03:53:55 | outline | `d1ef2a47` | succeeded | 2424 | 定稿门跳过 · empty_drama_contract · 点名设定 injected | ember 吃到第 5 章钩；causal 章台账可读；drama 真空（尚无节拍，合理） |
| 03:54:34 | beats | `02aa3fe0` | **failed** | **0** | 同上 + empty_drama_contract | 第一次 LLM 流失败；四仪已注入且为脏稿 |
| 03:56:31 | beats | `4fcccb23` | succeeded | 1681 | 同上 | 落库成功；drama 仍 empty（提取未跟上） |
| 03:57:08 | beats | `c2a70d2a` | succeeded | — | 同上 | 再跑/加厚 |
| 03:58:41 | deduce | `926f187d` | succeeded | 10257 | 场面真相 **deduce_truth_not_yet** | drama 已有但截断；`scene_truth_proj` empty（鸡生蛋）；truth 事后才 1666 |
| 04:01:25 | draft | `29752412` | succeeded | 3865 | 定稿门跳过 · 点名设定 | extra「已有 3811，还差 6189」续写加厚 |
| 04:02:04 | draft | `9ee9ffb3` | succeeded | 3794 | 同上 | 第二次加厚 |
| 04:03:36 | draft | `8f6d6221` | succeeded | 2604 | 同上 | 第三次加厚到地板；**causal 已变成 `event:i5-*`** |
| 04:05:52 | final | `6f2b3d47` | succeeded | 定稿 10488 | 点名设定 · 设定名片 · **未登记·draft_full** | `draft_full` 10139 字真注入；contrast 标 unexpected |
| 04:08:23 | save | `fc02462e` | ok | — | 步骤完成 | craft C 过；leaks=0；`ingest_enqueued=false` |

**现库地板（审查时）：**

| 层 | 去空白 | 地板 | 判定 |
|----|--------|------|------|
| 大纲 | 2375 | ≥500 | 过。槽齐，但「因→果」标题泄漏「为什么非发生不可」 |
| 节拍 | 3 拍 / 1359+1291+1411 | ≥3 / 每拍≥500 / 合计≥2000 | 过。槽全。水下含 **锁眼** |
| 演绎 | 投影 2999+2790+2538，truth 1666 | ≥5000 | 过。五层齐全。truth/投影含 **锁眼** |
| 草稿 | 10091，`latest-draft` source=`chapter_version` | ≥10000 | 过。**锁眼 ×9**。开头接近场面真相 |
| 定稿 | 10488 | ≥5000 | 过。**无锁眼**。与草稿不同开头 |
| hook | 「比往常早…他蹲着，没有张嘴。」 | 非空 | Ice7 过。与第 5 章「天亮以前，不能张嘴」同型 |
| focalizer | `role:qin_huiqi` | 必有 | 现库过 |

**注入燃料（以 final 链为准）：**

| 段 | 有无 | 质量 |
|----|------|------|
| story_ember | 有，53 字 | 真吃到第 5 章官方钩 |
| story_recall | 有 | 三条开着的承诺 + 第 5 章余波；缺第 4 章铜钱压锅 |
| story_causal | 有，但 **75 字全是 `event:i5-0` 等 id** | 早期链是章标题台账，后半截退化 |
| narrative_contract | 有 | **生成当时**欲望空、挡=呼吸段、付被截断。现库已点批修好，**当时没喂到模型** |
| drama_contract | 有，338 字 | `拍1：：` 双冒号，句中截断，像槽正则又咬坏了 |
| focalizer | 有 | `qin_huiqi`，诚实 |
| purpose / deltas | 空合同 | 「空合同也可写」 |
| brief_must | 有 | 伏笔「父名点名」**超窗阻塞级**，作者未三选一 |
| secret_guard | 有 | 破绽词已打码；**定稿守住了，冰山没守住** |
| draft_full | 有 | 排演全文进定稿，headline 标「未登记」= 矩阵滞后 |
| usage | 非 0 | outline 2424 / beats 失败 0 / deduce 10257 / draft 三段约 1 万 / final 成稿 10488 |

---

## 2. 质量问题清单

### S1 本章内容（人读主轴）

| ID | 问题 | 证据 | 根因 |
|----|------|------|------|
| C1 | **水下冰山泄漏锁眼** | 节拍 2 水下「没有把锁眼那片新铜完全盖住」；场面真相「锁眼外沿那片被刮掉的新铜」；草稿 9 处写匙齿探锁眼。定稿 0 处（改写成「门缝/缝口」） | 生成 extra / 模型把工艺步骤写进了非定稿层；secret_guard 只在 final 挡存 |
| C2 | **生成链四仪是脏的** | beats/deduce/draft/final 的 `chapter_story_io`：`desire="为什么非发生不可"` 或空；挡=呼吸段；付=「翻过面，擦完，搁到」截断。大纲三级标题就是「因 → 果：为什么非发生不可」 | 槽名泄漏进提取。2026-08-15 点批已把现库四仪改成作者短句，**改晚了，模型已经按脏合同写完** |
| C3 | **章任务漂移** | extra/点批四仪要「炉冷前把焦黑还回去」。大纲 1 次「焦黑」，定稿/草稿 **0 次**。正文主线变成：交三斤半炉灰 + 纸角塞门缝 + 假铜片拨开 | 脏四仪没有「还焦黑」；大纲「必须发生」已改成拨假铜 |
| C4 | **钩回声** | 第 5 章钩「天亮以前，不能张嘴」；第 6 章钩「他蹲着，没有张嘴」 | ember 被吃进去后，章末又用同一动作收束 |
| C5 | **草稿三次续写加厚** | extra「已有 3811，还差 6189」→ 再差 2463。定稿另写，避开了复读开头，但草稿本身前半=场面真相扩写，后半为凑地板 | 10000 地板逼出续摊，不是一气呵成的排演 |
| C6 | **超窗伏笔未裁决** | `brief_must`：「炉册夜审要点名，名里有个字像灰七爹」阻塞级三选一。正文用「爹的口气咳了一声」擦边，没有兑现也没有延期 | 作者路径没点 `s3_advance_promise` / 改窗 / 作废 |
| C7 | **比喻偏密、空锅磕复读** | 定稿「像」65 次（约 6.2/千字）；「空锅」7 次。结构段已要求「像字勿过密」 | 纪律在 prefix，模型仍用物象堆烟/锅 |
| C8 | **水下越知** | 节拍 3 水下：「他永远不知道那扇侧门在他身后开了一道缝」——叙述者替读者看了灰七没回头看见的门缝 | 演绎/节拍水下写成全知剧透，定稿收敛成「门板里面一声闷响」较好 |

### S2 产品 / 记录仪

| ID | 问题 | 证据 | 根因 |
|----|------|------|------|
| P1 | **headline「定稿门跳过」出现在 outline/beats/deduce** | 10 条链里写阶段全部带这句 | 段标题/跳过句绑错 phase，不是真的跳了定稿门 |
| P2 | **empty_drama_contract / 截断戏剧槽** | outline 真空合理；beats 已落后仍 empty；其后 drama 正文 `拍1：：` 双冒号、句中切断 | 槽提取仍吃冒号/粗体；有节拍也不回填 |
| P3 | **causal 后半截变 id** | outline/deduce：章标题链；draft3/final：`event:i5-0`… | ingest 出事件后回退格式改成内部 id，没走章台账可读句 |
| P4 | **deduce_truth_not_yet 半真** | deduce 当时库里确实还没有 truth（鸡生蛋）；生成后 truth=1666。headline 事后看起来像撒谎 | 应用「本阶段将要写真相」而不是「真相缺失当缺陷」 |
| P5 | **contrast 常红** | 缺 `event_drive(_hook)` / `phase_role` / `purpose`；意外出现 `codex_named`、`draft_full` | 期望矩阵与 rev.4 实跑脱节。**红 ≠ 内容失败** |
| P6 | **draft_full 标未登记** | final 真注入了 10139 字排演（该有），headline 当 unexpected | 定稿期望表没把排演全文列为应注入 |
| P7 | **purpose 空、phase_role 空** | 各链 purpose=「空合同也可写」；phase_role missing | 本章没登记 delta；phase_role 段没产出 |
| P8 | **beats 第一次 503 / usage=0** | `02aa3fe0` outcome=failed，output_chars=0，链 status 仍 ok | 失败链标绿；半截燃料未标红 |

### S3 文案 / 矩阵

| ID | 问题 | 说明 |
|----|------|------|
| L1 | 「点名设定（injected）」 | 名片有字（灰狸/冷锅婆），不是空壳；但亡父几乎只在 final 的 `codex_cards` 47 字出现 |
| L2 | 事件 kind 无 `code` 字段 | 分析脚本若只扫 `event.code` 会以为「没有 read/drop」。真信息在 `kind`+`payload` |
| L3 | save 链无 events/artifacts | 只有 6 个 span 名，回放存稿细节弱 |

---

## 3. 改进方向全集（先穷尽，再裁）

1. 产品：四仪提取拒槽名 / 拒空欲望（**代码已于 2026-08-15 热更**，须在 **新开层** 上验证，本章生成链用的仍是旧提取）。
2. 产品：drama 槽正则与「有节拍必须回填」；禁止 `：：` 残片进模型。
3. 产品：causal 有 event 图时仍输出「章标题 + 人话短句」，禁止 `event:i5-0` 进 prompt。
4. 产品：headline 按 phase 选句；outline 不得写「定稿门跳过」。
5. 产品：`draft_full` 列入 final 期望；contrast 的 purpose/phase_role 降为 Should，避免假红。
6. 产品：secret_guard 扩到 persist 节拍/演绎/草稿（或至少打码「锁眼」），不要只挡 `/save-chapter`。
7. 产品：deduce 阶段不把「尚无 truth」标成缺陷。
8. 产品：失败链 `outcome=failed` 必须反映到链 status / headline。
9. 协议：OpSeq 增加「大纲后验四仪，脏则先修再节拍」（rev.4 已写，**脚本当时没拦**）。
10. 本书：点批超窗伏笔（推进 / 改窗 / 作废）。
11. 本书：改大纲「因→果」标题，去掉「为什么非发生不可」。
12. 本书：重跑节拍水下 + 场面真相，去掉锁眼（已厚层不可 persist=false 充数）。
13. 本书：可选改第 6 章末两句，避免「张嘴」回声，保留咳/空锅信息增量。
14. 本书：不整章重写定稿（定稿已是最干净一层）。
15. 生成 extra：新章写死「禁锁眼/匙孔；焦黑必须作为可见物还回去；钩禁止复用上章动词」。
16. 不做：把 contrast red 当 Wave 失败；重开书；为凑 10000 再续第四次草稿。

---

## 4. 最优改造方案（现在该做的）

原则：**定稿不动；先修会污染下一章的产品；再补本章冰山泄漏；伏笔单独点批。**

### 立刻改产品（P0，热更 backend，不碰宣称）

| # | 改什么 | 冒烟 |
|---|--------|------|
| A1 | headline / SEG 按 `phase` 选句：thicken 阶段禁止「定稿门跳过」 | 新开一章 outline 链，headline 不含「定稿门」 |
| A2 | causal 回退：有 event 也输出人话；`event:` id 不得进 artifact.body | 第 7 章 draft 链 `story_causal` 正文无 `event:i` |
| A3 | drama 提取：有 beats 必回填；去掉双冒号残片 | 第 7 章 beats 后 drama 槽完整 |
| A4 | persist 节拍/演绎/草稿扫破绽词（至少锁眼/匙孔），422 或自动改写提示 | 再跑节拍含「锁眼」→ 不得静默落库 |

A1–A3 改动面小、风险低。A4 要小心误伤「门缝」合法写法，词表保持与 `secret_guard` 一致。

### 立刻改本书（P1，合法写，一层一层）

| # | 动作 | 说明 |
|---|------|------|
| B1 | 点批 `s3_advance_promise` 或改窗 | 处理「父名点名」阻塞。建议：**延期到炉冷之后**（与「不得念亡者真名」一致），不要在第 6 章补念名 |
| B2 | 点批改大纲三级标题 | 「因 → 果：为什么非发生不可」→ 人话标题（拨开假铜 / 账勾门没开） |
| B3 | `generate-stage` beats+deduce `persist=true` | **只为去掉锁眼**。extra 写死禁锁眼、保留拨铜/账勾/咳。已厚字数够，重点是去泄漏不是加长 |
| B4 | （可选）`/chat/write` 只换章末 2–3 句 | 去掉「没有张嘴」，留下空锅早磕或咳的余音。禁止整章重写 |

**不要**重跑第 6 章 outline（会冲掉已经不错的日子/必须发生）。**不要**重跑 draft/final。

### 放入协议（P2，不另开总 PASS）

- Ice7 附录：生成当时四仪以 **该链 artifact** 为准，不以事后点批为准。
- Rec2：分析必须打开 `story_causal` / `narrative_contract` / `drama_contract` 正文。
- 失败链 usage=0 记 S2，不得用「链 status=ok」抹掉。

### 明确不做

- 不改宣称、GATE-B、`GATE_SAVE_MODE`。
- 不把 C3 / `event:i5-*` 当事实图去「补全事件引擎」。
- 不因 contrast red 重开书或重跑 Wave A。
- 不把第 6 章定稿当失败稿推翻（它已经完成秘密守卫，人读合格）。

---

## 5. 建议下一轮执行顺序

严格一层完再进下一层，禁止并行两层。

```text
1. 热更 A1 headline + A2 causal 人话 + A3 drama 回填
   → demo 新章或第 7 章壳上冒烟（不要动第 6 章定稿）
2. 点批 B1 超窗伏笔（延期）
3. 点批 B2 改第 6 章大纲标题
4. generate-stage seq=6 stage=beats persist=true（去锁眼）
   → GET chapter 验水下无锁眼、每拍仍 ≥500
5. generate-stage seq=6 stage=deduce persist=true（去锁眼）
   → 验 truth / 投影无锁眼、合计仍 ≥5000
6. （可选）只改第 6 章末钩
   → GET narrative_drive.end_hook 与第 5 章钩动词不重复
7. 打开第 6 章最新 deduce/beats 链：headline 不再「定稿门跳过」；
   causal 不再是 event:id
```

A4（persist 扫锁眼）放在 4–5 之前或同时，避免 B3 再写下锁眼。

---

## 6. 验收口径（本章改造完成的定义）

**绿（本章）：**

- 节拍 / 场面真相 / 草稿正文不含「锁眼」「匙孔」「门芯」
- 大纲标题无「为什么非发生不可」
- 现库四仪保持作者短句（要还焦黑 / 假铜会暴露 / 账勾门没开 / 门内咳声）
- 定稿字数仍 ≥5000，钩非空，无锁眼
- 父名伏笔状态不再是「超窗未裁决」

**绿（产品，可用第 7 章证）：**

- thicken 链 headline 无「定稿门跳过」
- `story_causal` 无人话以外的 `event:` id
- 有节拍则 drama 非 empty、无 `：：` 残片

**不纳入本章绿：** contrast 全绿、purpose 必填、事件图完备、人盲分。

---

## 7. 附录：人读定稿（为什么不重写）

定稿开头用各家烟性子进场，布包里藏纸角，拨开灰狸铜片，「账勾了。」「门没开。」门板里「用他爹的口气咳了一声」，把纸角又朝门里推回一分。限知大体守住（灰狸不知匙；名未出口）。这是全书目前最稳的一章水面。

它没完成 extra 里的「把焦黑还回去」，钩又弱回「张嘴」。那是 **S1 可补丁**，不是推倒重来的理由。推倒会丢掉已经过 QC、无泄漏的 10488 字。

---

*完。执行前先确认：本方案默认「定稿锁定 + 冰山去泄漏 + 产品三刀」。若你要改成「整章按焦黑任务重写」，需要另开一轮，从大纲重跑 OpSeq。*

# book_79c0d45e 问题全表

严重度：P0 挡读者或假绿宣称 · P1 挡质量闭环 · P2 体验/观测债。  
「挡读者」= 人打开章页会直接读到机器垃圾、复读墙、或设定被剧透到无法当小说读。

---

## A. 系统运行

| ID | 问题 | 证据 | 严重度 | 挡读者 | 根因（机制） |
|----|------|------|--------|--------|--------------|
| S1 | 存稿把 SSE 兜底 `proposal` 字典整段拼进 `chapter.prose` | 第 1/2/3/4 章文末 `{'scope': 'chapter', 'prose': …, 'fallback': True}`；`write_stream.py` 模型忘围栏时 `yield proposal fallback=True` | P0 | 是 | extract/save 把流里的提案帧当正文追加，没有「只取 `prose` 字段」的围栏 |
| S2 | 第 3 章整章双份（dup_n=116） | `post-check-ch3` `duplicate_lines` 几乎每句 count=2；库 `chars=9534` vs 机判 visible 8031 | P0 | 是 | 兜底提案的 `prose` 再次拼到已写入正文后；save 无「后缀=前缀拷贝」拒绝 |
| S3 | `skip_finalize_gate` 落库后链 headline 仍可「对照齐全」 | `00-author-path.md` 明文 skip；save 失败链 `fd08fe10…` headline=「定稿门（blocked）」；后继 save ok 不写 skip 戳 | P0 | 否（挡宣称） | 定稿门被绕过不进 span；`headline_from_spans` 无红则「对照齐全」 |
| S4 | 能落库 ≠ 过质控，但脚手架灯全绿 | 五章 `may_claim_scaffold=true` 且 `may_claim_readable=false`；GATE-B 只验 synopsis/beats/scene_truth 长度 | P0 | 否（挡宣称） | 开写门与可读门未在 save 成功态上强制对齐 |
| S5 | 戏剧合同步恒空（`empty_drama_contract`） | 写链 `071e3439…` span `assemble.seg.drama_contract` actual=empty；beats 仅 `{text}` | P1 | 间接 | `_drama_block` → `format_drama_block` **无 GCD/钩子就返回空串**；MCP 点批只写了三句 slogan |
| S6 | 大纲步恒空（`empty_outline`），尽管章上有 synopsis+beats | 同链 `assemble.seg.outline` chars=0，`expected_reason=has_outline_src` | P1 | 间接 | 期望层看见大纲源，装段函数仍吐空（rebind/章视图/fail-soft）。写模型只好自己拟提纲 → 第 2 章「开写前先理一条线」 |
| S7 | 装段对照与 span 对同一段结论打架 | 同链 span：`codex` injected 702 字；`contrast_summary.rows` 里 `codex` empty。headline 报「工艺误注 / 目的误注」 | P1 | 否 | 对照卡与 span 不是同一时刻/同一套 actual；分析员无法信任何一侧 |
| S8 | 失败写链无 exception | `73946e1a…` status=failed，149ms，停在 `voice_anchor`，`outcome_status=null`，无 error class | P1 | 否 | rebind `NameError FOCAL_DEDUCTION_PROSE_CAP` 已修，但失败路径没把异常摘要写入 chain |
| S9 | 无逐步分析账 `pipeline_log` | `GET /api/debug/pipeline-logs` → 404；现网只有瘦 chain/span | P1 | 否 | 141 设计未落地。本分析只能读结果对照，不能还原步内决策 |
| S10 | `anti_meta` 漏掉提纲腔与 JSON 尾 | 五章 `anti_meta.hits=[]`，第 2 章「开写前先理一条线 / 正文如下」公然在库 | P0 | 是 | 禁元词表不覆盖导演备忘录和 Python dict 尾巴；所以 QC 不挡这类脏稿 |
| S11 | `scene_cover` 对口号节拍恒 0 | 五章 `valid=0/total=3`；beats 如「霍三刀下令封炉一夜。」 | P1 | 否（挡可读宣称） | `_keyword_ranges` 要正文吃进整句口号；GATE-B 不验 GCD 字段 |
| S12 | 工艺/目的/声口「不该注却注了」 | contrast `unexpected_present`: brief_must / voice_anchor / storyline_polish / discourse_soft | P2 | 间接 | 期望谓词与真实装段白名单不一致；声口锚只有 30 字空壳 |
| S13 | injection-trace 只留 last-one | `GET /api/debug/injection-trace` | P2 | 否 | 内存语义，重启即丢 |
| S14 | `from_span_id` / 消费边为空 | 全链 `links` 几乎只有 manifest/outcome id | P2 | 否 | 140 合同没写 produce/consume |
| S15 | 第 3/4 章标题未生成 | `title=第3章` / `第4章` | P2 | 弱 | 结构点批只保证壳，不保证章名 |
| S16 | post-check 设定噪声把「炉火」「拾灯」当未登记专名 | `post-check-ch3.setting` 25+ 条 unknown_name | P2 | 否 | 分词把角色名切开；不能当设定债 |
| S17 | 写路径曾被 rebind NameError 打断 16 次 | 42 链里 write failed=16，2–5 章各 4 | P1 | 否（已热更） | `_rebind_services` 漏 `FOCAL_DEDUCTION_PROSE_CAP`（已修，须防再发） |
| S18 | 字数口径含污染 | `wordcount.json` 31614 含 JSON 尾与第 3 章双份 | P2 | 间接 | `_degen_visible_length` / 去空白未剥提案帧 |

---

## B. 文本 / 设定

| ID | 问题 | 证据 | 严重度 | 挡读者 | 根因（机制） |
|----|------|------|--------|--------|--------------|
| T1 | 第 1 章从半句中途开场 | `prose-ch1.md` L1 以「这个断续不该由我来说破」+ 闭括号起 | P0 | 是 | 续写快照/流截断 + 无「章必须成篇」的 persist 闸 |
| T2 | 第 2 章开篇导演提纲 | 「开写前先理一条线…正文如下：## 第二章 夜税」 | P0 | 是 | S6 大纲空注 → 模型把大纲写进正文；S10 不拦 |
| T3 | 第 1 章契约场面缺席 | 节拍要缺页面交 + 巷口敲鞘；正文是炉房闲话 + 远处牵驴 | P1 | 弱 | S5 戏剧合同空；beats 未变成「必须发生」硬约束 |
| T4 | 第 3 章阿绣全知开挂 | 「你当年在军里，欠了一条人命」；沈拾灯内心「她怎么会知道」 | P1 | 是（戏假） | 限知守卫 `guard.epistemic` span ok 但不管「人物怎知」；无 secret 绑定 |
| T5 | 刀鞘归属三真 | ch2 霍留下；ch3 爹的东西；ch5 河堤霍不知谁拾 | P1 | 是（连续性） | 物件 A2 无单真锁；模型每章重编来历 |
| T6 | 第 4 章侧门开法泄密（A7/M5） | 铜签、拨两下、门轴浸油 | P0 | 是（设定） | `secret_guard` 本链 actual=empty；揭示纪律只注入 87 字条幅，不挡操作步骤 |
| T7 | 第 5 章揭破炉契规则 | 「头一个被念到的名字，便得拿自个儿去填炉底」 | P1 | 是 | 第 1 章 synopsis 禁令未进入写提示（outline 空） |
| T8 | 「郭家三刀」笔误 | `prose-ch5.md` 「郭家三刀的鞘」 | P2 | 弱 | 专名表未在生成出口做强制别名检查 |
| T9 | 第 1 章灯芯讲义 | 老桂解释念想/铜臭/锈/甜 | P1 | 弱 | 正典/工艺段把规则当对白材料灌进 |
| T10 | 声口不稳 | ch1 讲义、ch2 市井、ch3 翻译腔、ch5 半文言 | P2 | 弱 | `voice_anchor` 30 字且 contrast 判 unexpected |
| T11 | 第 5 章契约「揭册不是胜利」只做到一半 | 揭开「庄正经」后停住，火未灭——这点好；但开篇先把炉契惩罚讲透，张力被泄 | P2 | 弱 | 同 T7 |
| T12 | 节拍/场面不对齐导致可读灯永红 | 见 quality-findings 末表 | P1 | 否 | S11 + 点批 beats 是计划句不是场面句 |

---

## 归因图（一句话）

```
点批只写了 slogan beats
        ↓
戏剧合同/大纲装段常空（S5/S6）
        ↓
模型自己写提纲、自己发明刀鞘来历、自己揭炉契
        ↓
流忘围栏 → fallback proposal 字典
        ↓
save 把字典+复读拼进 prose（S1/S2）
        ↓
anti_meta 看不见（S10）→ finalize 只看见 AI heavy
        ↓
工程 skip_finalize 入库（S3）→ 读者看见脏稿
        ↓
分析员只有瘦 span，「对照齐全」或 404（S9）
```

本表 **不是** 已实现清单。改造见 `remediation-plan.md` / `docs/plans/2026-08-14-book79-quality-remediation.md`。

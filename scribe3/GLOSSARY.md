# scribe3 词汇表(GLOSSARY)· D枢纽单一事实源

## 组一:章时间
| 中文名 | 规范代码名 | 定义 |
|---|---|---|
| 事件发生章 | `story_chapter` | 事件占用的故事时刻(单点) |
| 事实生效起点 | `valid_from` | 事实有效区间起章 |
| 事实失效点 | `valid_to` | 事实有效区间终章;None=持续 |
| 获知起章 | `since_chapter` | 知识边时态:从第几章起知道 |
| 获知止章 | `until_chapter` | 知道到第几章为止 |
| 伏笔埋设章 | `setup_chapter` | promise 被开启的章 |
| 伏笔回收章 | `payoff_chapter` | promise 被闭合的章 |
| 章序号 | `seq` | chapter 表主键序号 |

## 组二:标识符
| 中文名 | 规范代码名 | 定义 |
|---|---|---|
| 本体标识符 | `<entity>_id` | 带前缀 oid(role:焦三) |
| 局部名 | `local` | oid 去前缀后部分 |

## 组三:角色
| 中文名 | 规范代码名 | 定义 |
|---|---|---|
| 角色(实体) | `character` / `character_id` | kind=character 的 Entity |
| 视角角色 | `focalizer` | 当前渲染章 POV 角色 |
| 知识持有者 | `knower` / `knower_id` | 知识边主体(含 reader/world) |

## 组四:文本
| 中文名 | 规范代码名 | 定义 |
|---|---|---|
| 章节正文 | `prose` | 章的长正文 |
| 短文本字段 | `text` | promise/voice 的短文本 |
| 事实取值 | `value` | Fact 的 attribute 取值 |
| 注记 | `note` | craft_rule 的可选说明 |

## 组五:kind(一名多义拆分)
| 中文名 | 规范代码名 | 枚举 |
|---|---|---|
| 实体本体类别 | `entity_kind` | character/item/place/faction |
| 题材规则类型 | `craft_rule_kind` | purple_regex/artifact_craft/allow_pattern/allow_word |
| 声音语域 | `voice_kind` | free/pressure/relation/narration |
| 伏笔性质 | `promise_kind` | promise/red_herring |

## 组六:写作产物字段(章表)
| 中文名 | 规范代码名 | 定义 |
|---|---|---|
| 章大纲/梗概 | `synopsis` | 章级种子;大纲阶段真源 |
| 节拍列表 | `beats` | 拍级 GCD/text;戏剧合同主杠杆 |
| 场景真相 | `scene_truth` | 演绎认知层;≠世界命题真相 |
| 草稿 | `draft` | 执行稿;与 prose 分列 |
| 正文 | `prose` | 落库长散文 |
| 章末钩元 | `beats_meta.chapter_hook` | 钩子 SSOT 优先层(见 `chapter_hooks.resolve_chapter_hook`) |
| 事件驱动 | `narrative_drive` | 章级导航/引导;end_hook 由钩子链种子;MetaPane「本章事件驱动」只读三行 |
| 力学合同 | `pressure_drive` | 写路径压力真源;≠经验复盘 UI |
| 执行合同 soft | `soft_fulfill` / `soft_fulfill_drive` | 写后对白/长度组合 advisory;同源 GET `/chapter/execution-soft-status`;永不 blocking |
| 执行戳/漂移 | `execution_stamp` / `drive_prose_drift` | drive 与 prose 对齐指纹;drift 建议强制重写,不自动清稿 |
| 章执行软状态 | `chapter_execution_soft_status` | UI SSOT 聚合:drive 三行+stakes+soft_fulfill+drift |

## 组七:写路径注入 domain(节选)
| 中文名/槽 | 规范 domain / 代码 | 定义 |
|---|---|---|
| 戏剧合同 | `drama_contract` / `_drama_block` | 唯一 GCD 执行摘要 |
| 大纲块 | `outline` | 仅 synopsis + beat.text(无 GCD 字段当大纲) |
| 简报必达 | `brief_must` | 操作段;已 pop purpose/drama_contract/injection |
| must-link 钉 | envelope pin · `reason=must_link_priority` | 权威全文;brief 在 `SCRIBE3_INJECT_DEDUP=1` 时短路 |
| 目的 | `purpose` | 世界验收 delta;非文案 |
| 续写快照 | `continue_snapshot` | 可注入;≠ pressure_drive |

## 组八:产品面命名(IA 人决 · 消歧)
| 产品中文名 | 规范代码/入口 | 旧称/勿混 | 注入/数据源 |
|---|---|---|---|
| 作品意图 | 顶栏 `NorthStarBar` · `intent:main` | 旧 UI「北极星」条 | s3_get/set_intent |
| 评分卡 | 辅助 tab · `NorthStarPanel` | 旧「北极星」面板;≠作品意图 | chapter/book scorecard |
| 经验复盘 | 辅助 tab · `ExperiencePressurePanel` | 旧「压力」面板;≠力学合同 | 六格/问诊/续写;不写 beats |
| 力学合同 | `pressure_drive` 写路径块 | 勿称「压力面板」 | PDC 真源 |
| 章节信息 | `ChapterMetaPane` | 章前契约+事件驱动+执行 soft | `evaluateChapterContract` + execution-soft-status |
| 契约 soft banner | `ContractSoftBanner` | 正文顶栏合一黄条 | 契约缺口 + 执行 soft;不阻断生成 |
| 信息密度 | `localStorage s3.ia.density` | 禁止 USER.md / author_prefs | essential(默认)/standard/full |
| 设计锚 · IA | `docs/plans/2026-08-10-chapter-writing-ia-optimal.md` | — | Accepted rev.3.1+ |
| 设计锚 · EC | `docs/plans/2026-08-10-narrative-rootcause-optimal-execution.md` | 执行合同 | rev.1.1+ |
| 设计锚 · 卷 IA | `docs/plans/2026-08-10-volume-outline-ia-optimal.md` | 卷信息/卷纲 | Accepted rev.2.1+ |
| 设计锚 · 主编能力 H1 | `docs/plans/2026-08-11-chief-module-generation-skill-vs-mcp.md` | skill≠模块生成器 | 单脑+软路由+种子 |

## 组十:主编能力分层(H1 · 软门控 vs 硬门控)

| 中文名 | 规范代码/入口 | 定义 | 勿混 |
|---|---|---|---|
| 主编 | `ChiefDock` / Hermes Run | 作者右栏对话写入口 | 非多 skill 人格 |
| 能力目录软路由 | `orchestration/catalog.py` · `resolve` | domain / write_tools **评价与提案** | **不是** Hermes MCP include 过滤器 |
| 硬门控 profile | `run_stage_policy` · `scribe3_deduce*` | 运行时 tools.include 真子集 | 现网仅演绎;大纲/节拍为全写+软合同 |
| 种子合同 | `chiefSeed.js` · `volumeSeed.js` | 点名 `s3_*` + 禁脚手架 save | 非「进 Hermes」门槛本身 |
| 域指令后缀 | resolve `instruction_suffix` | world_write 清空 phase 时仍注入域纪律 | 不靠 run phase 恢复 |
| 技法 skill | `craft_skills/*.md` · `s3_skill_read` | 渐进披露写作技法 | **不是**大纲/节拍生成器 |
| 派生只读面 | 简报/评分卡/关联 | 后端组装;LLM 不写 SSOT | 评分卡≠作品意图;经验复盘≠`pressure_drive` |

## 组九:卷层(卷信息 / 卷纲 · 按需后建)
| 中文名 | 规范代码名 | 定义 |
|---|---|---|
| 卷 | `volume` 表 / `chapter.volume` | Binder 容器;可空=**未分卷**(一等合法态) |
| 未分卷 | `volume is null` / Binder 未分卷组 | **按需后建卷**默认路径;非错误;永不作 GATE-B 硬拦 |
| 卷信息 | `title` / `sort_order` / `color` | 卷元数据;≠卷纲 |
| 卷纲 | `volume.intro`（UI 称「卷纲」） | 卷级冲突/弧/应付的账备忘;SSOT 单字段;≠章 synopsis/beats |
| 写路径注入 | domain `volume_intro` / `_volume_intro_block` | 有归属且 intro 非空且 flag 开 → ≤400 字;空 intro/无卷 → 空串 |
| 卷信号复盘 | `GET /volume/review` · KR4 | 伏笔超期/母题等只读; **≠ GATE-B** 工艺门 |
| 改卷工具 | `s3_patch_volume` | WRITE_GATED;正式卷「让主编写入」种子必须点名 `volume_id` |
| 建卷工具 | `s3_add_volume` | WRITE_GATED;从「未分卷」创建正式卷 |
| 策略 | 按需后建卷（opt-in） | 默认后建;先建卷=作者主动;禁止开书强制先建卷 |

## 组十一：API 键名与产品文案映射

| API 键/路径 | 产品文案（作者可见） | 说明 |
|---|---|---|
| `GET /chapter-pulse` → `checks` | "本章脉搏" | PulseBar 组件渲染的维度列表 |
| `checks[].dimension` | 维度 ID（promise/arc/relation/tension/causal/quality/scene） | 不对作者显示原始 ID |
| `checks[].severity` | info→灰/nudge→黄/decision→红 | 三级信号灯 |
| `checks[].items[].message` | "脉搏详情"面板正文 | 人话描述，直接展示 |
| `GET /quality` → `gate.hits` | "质量判定" | ChiefDock 质量面板 |
| `gate.vcode` | pass→"通过"/needs_human→"待人审"/fail→"未通过" | 质量判定结果 |
| `GET /inbox` → `items` | "决策收件箱" | PilotInbox 组件 |

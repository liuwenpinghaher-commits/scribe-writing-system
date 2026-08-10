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
| 事件驱动 | `narrative_drive` | 章级导航/引导;end_hook 由钩子链种子 |
| 力学合同 | `pressure_drive` | 写路径压力真源;≠经验复盘 UI |

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
| 评分卡 | 辅助 tab · `NorthStarPanel` | 旧「北极星」面板 | chapter/book scorecard |
| 经验复盘 | 辅助 tab · `ExperiencePressurePanel` | 旧「压力」面板 | 六格/问诊/续写;不写 beats |
| 力学合同 | `pressure_drive` 写路径块 | 勿称「压力面板」 | PDC 真源 |
| 信息密度 | `localStorage s3.ia.density` | 禁止 USER.md / author_prefs | essential(默认)/standard/full |
| 设计锚 | `docs/plans/2026-08-10-chapter-writing-ia-optimal.md` | — | Accepted rev.3.1+ |

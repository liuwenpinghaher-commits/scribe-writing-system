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

# playbook.3.1

共用版本号：`PLAYBOOK_VERSION = "playbook.3.1"`。

相对 playbook.3：章末态补叙事人称，糙稿拦住翻人称和过低对白，清洗器不再把「不像是」洗成病句。改任何 prompt / rubric / schema 必须再升版本，并另写本文对应副本。已有产物按其落库时的版本验收，不追溯重考。老书（含 `book_be4343e4`）不回修人称，封存对照。

## 相对 3 的增量

- 章末态字段 `narrative_pov`：`first` / `third` / 空。第 1 章冻糙稿时按叙述层「我」测定；第 2 章起沿用上章。
- 机器闸 `pov_consistency`：剥对白后数「我」，和第 1 章钉下的人称比对。判定不进法官。
- 机器闸 `dialogue_floor`：糙稿引号行字数比 ≥15%。场景豁免只走人工留痕，闸本身不猜「这一章该不该少说话」。
- 清洗器：否定式（不像/不像是/并不像）先改成「不似」，再洗肯定式；洗出残渣的句子退回原句。
- 读接口：`GET /chapters/{seq}/state`、`GET /chapters/{seq}/duty`。
- 嘱咐：duty / play / draft 三处生成提示在上章末态旁加人称一行。

## 沿用 3

- 抽取：`state_extract`（场记，T=0.2）
- 表：`chapter_state`（照 146 信封，JSON 文档加字段不用 migration）
- 机器闸：`gender_pronoun` / `state_quote` / 明喻密度
- 法官：play / draft / final 对照上章末态三问；duty 加意象域一问
- 旧产物法官：`playbook.2` 走 `*_judge_v2`；`playbook.3` 产物仍按 3 的尺子验收

## 边界

`chapter_state` 只管「这章写完时世界变成了什么样」，不管下一章必须发生什么。人称只许第 1 章确立，后面不许自己改口。

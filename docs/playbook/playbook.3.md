# playbook.3

共用版本号：`PLAYBOOK_VERSION = "playbook.3"`。

相对 playbook.2：加上章末世界快照 `chapter_state`。改任何 prompt / rubric / schema 必须再升版本，并另写本文对应副本。已有产物按其落库时的版本验收，不追溯重考。

## 新增

- 抽取：`scribe3/playbook/prompts.py` `state_extract`（场记，T=0.2）
- 表：`chapter_state`（照 146 信封）
- 机器闸：`gender_pronoun` / `state_quote`
- 法官：play / draft / final 对照上章末态三问；duty 加意象域一问
- 旧产物法官：`playbook.2` 走 `duty_judge_v2` / `play_judge_v2` / `final_judge_v2`

## 边界

`chapter_state` 只管「这章写完时世界变成了什么样」，不管下一章必须发生什么。

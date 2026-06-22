# scribe3 — 故事本体 v2 内核(greenfield)

彻底重构的 greenfield 项目。落地《故事本体 v2》+《写作台 v2》两份规划文档:
- [`docs/superpowers/plans/2026-06-22-scribe-故事本体v2-全局重构方案.md`](../docs/superpowers/plans/2026-06-22-scribe-故事本体v2-全局重构方案.md)
- [`docs/superpowers/plans/2026-06-22-scribe-写作台v2-重构规划.md`](../docs/superpowers/plans/2026-06-22-scribe-写作台v2-重构规划.md)

## 现状:端到端纵切片(已验证)
先用一条最薄的端到端路径证明**范式级断言**——再全建。

**断言:限知渲染靠【渲染前的知识帧投影】,不靠【事后判官】。角色不知道的事,物理上进不了他的 prompt。**

证明(`demo.py` 真机 A/B,复刻用户最初揪出的「老道说出焦三私密」泄露):

| | 旧法(全知扁平注入,= scribe2 之前) | 新法(按 focalizer 投影知识帧) |
|---|---|---|
| 老道视角 prompt 含焦三私密「治眼」? | **True** ← 泄露曾从这发生 | **False** ← 物理上写不出 |

→ POV 泄露从「事后判官救」变成「渲染前结构上不会犯」;判官降为第二道兜底。

## 模块(4 类一等公民,持续体/发生体分明)
- `ontology.py` — `Entity`(持续体)/ `Event`(发生体)/ `Fact`(状态@时间,双时态骨架)/ `KnowledgeEdge`(belief base,显式·可错·非闭包)+ `World`(fabula 唯一事实源,唯一改状态入口)
- `knowledge.py` — `project_frame`(三帧投影:world 真相 / 角色 / reader)+ `see_event`(看见即知道:在场目击者获知)
- `render.py` — `build_render_prompt`(**fabula ∩ 知识帧** → 限知 prompt,帧外私密绝不出现)+ `render`(→ Hermes)
- `verify.py` — `find_leaks`(兜底 POV 修订 pass)+ `causal_complete`(连贯性=可跑查询:每事件须因果入边+目标)
- `llm.py` — 移植 scribe2 已验证的 Hermes 客户端(600s+3 重试)
- `scenario.py` — canonical 泄露场景(焦三/老道),demo 与测试共用

## 跑
```bash
scribe/.venv/bin/python -m pytest scribe3/ -q          # 12 passed(结构证明全绿,不碰网/不碰 SurrealDB)
scribe/.venv/bin/python -u -m scribe3.demo             # 端到端 A/B(Hermes :8642 在线则真机渲染)
```

## 运维(S4):体检 cron + 分章并行
- **体检 cron**(已注册,隔离在 scribe3 profile):`hermes --profile scribe3 cron list` 见 `scribe3-体检`(每 6h,`--no-agent` watchdog)。脚本 `qc_scan.py`(经 `~/.hermes/scripts/scribe3_qc.sh`)连 NS=scribe3 跑 `health_report`(跨章 `causal_complete`),干净=空 stdout=静默,有问题才交付报告。纯机械检查不耗 LLM。
  - ⚠ **自动定时触发需起 scribe3 gateway**(default 的 gateway 在 :8642,scribe3 profile 的没跑);脚本本身已真库验证。手动触发:`hermes --profile scribe3 cron run scribe3-体检`。
  - 可扩展:`health.py` 现只聚合连贯性,后续加伏笔超期/跨章泄露/声音一致性。
- **分章并行**:用 Hermes 原生 **kanban**(`auto_decompose`),别自建调度。scribe3 profile 已带 description 供 kanban decomposer 路由。模式:把"写第 N..M 章"丢给 kanban → 分解成多个章任务 → 各 dispatch 给 scribe3 主编(继承 s3_ 工具)并行写。(需 gateway 运行;交互流,未在此跑通。)

## 下一步(未建)
纵切片证明范式后,按规划文档扩建:双时态 SurrealDB 持久层 → 三帧并存 + 戏剧反讽查询 → 写作台 v2 双表面(W1 散文面+回链 → W6 掌控契约)。移植 scribe2 已验证资产(16 处 QC 纯函数 / craft 知识 / 乱世铜炉+拾骨记数据迁移 / B3 写审批)。

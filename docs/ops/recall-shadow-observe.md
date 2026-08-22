# 召回对照（追认观察期）

写章设定槽已于 **2026-08-22 17:27** 翻主（`5e7def28`）。对照从 **2026-08-22** 翻主日起算，按追认记账，不是「再等 7 天才能用」。

放行门槛（核销违规账，不是创作质量判据）：

- 按路径（playbook / discuss）过关率 ≥ 95%
- 秘密泄漏累计 = 0
- 人评至少 10 章没有变差

查询：`GET /debug/recall-shadow`（含窗口注记）；`GET /debug/pipeline-events?tag=recall_shadow`。

7 天追认账从对照事件能写入 observe 的本轮落库日起算，不压缩。越线就把 `SCRIBE3_RECALL_PLAYBOOK` 关掉回旧链。

进程刚退出时，最后一次写章的向量对照可能还没记完，观察期读数缺末笔是预期，不是事故。

要退回旧路：把 `SCRIBE3_RECALL_PLAYBOOK` 关掉。

-- scribe3 · 064_purpose_contract.surql · 章节目的合同(北极星方案任务6,蓝图 §3-④ 第四块拼图)
-- purpose_text=与主编探讨敲定的一句话目的;deltas=本章承诺改变的世界状态清单(JSON 串,
-- scene_meta/beats 先例:绕 SCHEMAFULL 嵌套校验,读时还原)。挂章表不另建表——与
-- scene_truth/deductions"写前登记、逐字段消费"同模式(蓝图明示);纯增字段,不触已有数据。
DEFINE FIELD IF NOT EXISTS purpose_text ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS deltas ON chapter TYPE option<string>;

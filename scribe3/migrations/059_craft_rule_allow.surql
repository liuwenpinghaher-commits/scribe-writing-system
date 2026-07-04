-- scribe3 · 059_craft_rule_allow.surql · 题材豁免 allow_pattern/allow_word 新路径(方案B任务14)
-- 对应 Python scribe3/enums.py CraftRuleKind:新增 allow_pattern/allow_word(前置 skip
-- 判定,减法),删除全程无消费者的空格 cover_action(勘误篇裁定,见 010_enums.surql/
-- 019_schemafull.surql 的旧域)。两层防护——Python 进程内 + DB 落库层——须保持同步,
-- 否则新 kind 值在 DB ASSERT 层被硬拒(SurrealDB 3.x DEFINE FIELD OVERWRITE 幂等重放)。
DEFINE FIELD OVERWRITE kind ON craft_rule TYPE string
  ASSERT $value IN ['purple_regex', 'artifact_craft', 'allow_pattern', 'allow_word'];

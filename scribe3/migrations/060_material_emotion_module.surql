-- scribe3 · 060_material_emotion_module.surql · EM/RH/TR 情绪模式库新 kind(方案B任务15)
-- 对应 Python scribe3/store.py MATERIAL_KINDS:新增 emotion_module(EM-001情绪模块卡/
-- RH-001爽点循环/TR-001触动点三张互引 schema 统一挂此 kind,卡内 id 前缀自行区分)。
-- 两层防护——Python 进程内 + DB 落库层——须保持同步,否则新 kind 值在 DB ASSERT 层
-- 被硬拒(SurrealDB 3.x DEFINE FIELD OVERWRITE 幂等重放,先例见 059_craft_rule_allow.surql)。
DEFINE FIELD OVERWRITE kind ON material TYPE string DEFAULT 'note'
  ASSERT $value IN ['research', 'reference', 'snippet', 'inspiration', 'note', 'emotion_module'];

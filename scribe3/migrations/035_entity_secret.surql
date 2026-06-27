-- scribe3 · 035_entity_secret.surql · 实体层私密标志
-- 与 proposition.secret 对等:character.backstory_secret / faction.private_operation_secret
-- 默认 false(非私密),由作者/编辑显式设置后通过 reveal_secret=true 解锁查看

-- 角色冰山私密前史标志
DEFINE FIELD IF NOT EXISTS backstory_secret ON character TYPE bool DEFAULT false;

-- 势力隐秘运作标志
DEFINE FIELD IF NOT EXISTS private_operation_secret ON faction TYPE bool DEFAULT false;

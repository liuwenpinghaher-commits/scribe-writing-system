-- 对象 lifecycle:角色/命题支持归档标记。
-- material 已在 070_material_memory.surql 定义 archived,这里补齐正典对象。
DEFINE FIELD IF NOT EXISTS archived ON character TYPE bool DEFAULT false;
DEFINE FIELD IF NOT EXISTS archived ON proposition TYPE bool DEFAULT false;

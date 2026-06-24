-- scribe3 · 013_event_graph.surql · 事件图边(B枢纽 P03)
-- 补回 store.add_event 蒸发的 participants/effects/causal_in/前置条件。
-- 全部 IF NOT EXISTS:与现有迁移一致,启动可重复 apply 幂等。

-- ① event 表补字段
DEFINE FIELD IF NOT EXISTS location      ON event TYPE option<record<place>>;
DEFINE FIELD IF NOT EXISTS preconditions ON event TYPE array<string> DEFAULT [];

-- ② 参与者:多对多 event->character + 角色槽位(SUBJ/OBJ/WITNESS)
DEFINE TABLE IF NOT EXISTS involves TYPE RELATION FROM event TO character SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS role ON involves TYPE string
    ASSERT $value IN ['SUBJ', 'OBJ', 'WITNESS'];
DEFINE INDEX IF NOT EXISTS idx_involves_role ON involves FIELDS role;

-- ③ 效果:事件初始化的命题(支撑 see_event「看见即知道」)
DEFINE TABLE IF NOT EXISTS causes TYPE RELATION FROM event TO proposition SCHEMAFULL;

-- ④ 因果链:event->event(对齐内存 causal_in,verify.causal_complete 据此查)
DEFINE TABLE IF NOT EXISTS causal TYPE RELATION FROM event TO event SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS ctype ON causal TYPE string;

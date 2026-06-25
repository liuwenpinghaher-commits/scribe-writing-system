-- scribe3 · 031_character_profile.surql · 角色深描(对齐门槛2-设定圣经 §3.1.1)
-- 设计文档要求 Character.traits{appearance/personality_tags/personality_detail/backstory_summary/abilities/weaknesses/importance}
-- + motivation{surface_goal/deep_need/internal_conflict/fear}
-- 全部用扁平字段(SCHEMAFULL 兼容)

-- 外貌
DEFINE FIELD IF NOT EXISTS appearance         ON character TYPE option<string>;
-- 性格深描
DEFINE FIELD IF NOT EXISTS personality_detail  ON character TYPE option<string>;
-- 能力列表(JSON 字符串,存 [{name,level,description,acquired_chapter}] )
DEFINE FIELD IF NOT EXISTS abilities          ON character TYPE option<string>;
-- 弱点
DEFINE FIELD IF NOT EXISTS weaknesses         ON character TYPE option<array>;
-- 首次出场章
DEFINE FIELD IF NOT EXISTS first_appearance   ON character TYPE option<int>;
-- 动机(surface_goal/deep_need/internal_conflict/fear)
DEFINE FIELD IF NOT EXISTS surface_goal       ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS deep_need          ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS internal_conflict  ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS fear               ON character TYPE option<string>;

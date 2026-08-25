-- 166_material_relates.surql · 素材联想边 schema 锁
-- 此前 RELATE …->relates->… 靠隐式表；正典知情边 knows 在 001 已 TYPE RELATION。
-- 只锁 material→material，不进知识图谱 / 不与 knows 混用。
-- OVERWRITE：已有隐式 SCHEMALESS relates 必须收成 RELATION，IF NOT EXISTS 对旧库是空操作。
DEFINE TABLE OVERWRITE relates TYPE RELATION FROM material TO material SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS weight ON relates TYPE option<float>;
DEFINE FIELD IF NOT EXISTS reason ON relates TYPE option<string>;

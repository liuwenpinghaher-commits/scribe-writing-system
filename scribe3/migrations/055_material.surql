-- scribe3 · 055_material.surql · 素材库(Materials Library):非正典写作材料
-- 收集研究资料/参考片段/灵感剪藏/待用桥段/笔记,与设定库(codex=故事正典)严格分开:
-- 素材不进知识图谱、不被 ingest、不参与限知/伏笔/QC/时间线。每书独立(一书一 DB 天然隔离)。
DEFINE TABLE IF NOT EXISTS material SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS title      ON material TYPE string;
DEFINE FIELD IF NOT EXISTS body       ON material TYPE option<string>;    -- markdown 正文
DEFINE FIELD IF NOT EXISTS kind       ON material TYPE string DEFAULT 'note'
    ASSERT $value IN ['research', 'reference', 'snippet', 'inspiration', 'note'];
DEFINE FIELD IF NOT EXISTS tags       ON material TYPE array<string> DEFAULT [];  -- 与 001 aliases 等既有惯例一致:扁平字符串数组用原生 array
DEFINE FIELD IF NOT EXISTS source     ON material TYPE option<string>;    -- 来源(出处/链接/备注)
DEFINE FIELD IF NOT EXISTS created_at ON material TYPE datetime VALUE time::now() READONLY;
DEFINE FIELD IF NOT EXISTS updated_at ON material TYPE datetime VALUE time::now();

-- scribe3 · 章节正文(manuscript / sjuzhet 落库)。
-- 章是叙述层(discourse)对象:seq + 标题 + focalizer(视角)+ 渲染出的 prose。
DEFINE TABLE IF NOT EXISTS chapter SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq       ON chapter TYPE int;
DEFINE FIELD IF NOT EXISTS title     ON chapter TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS focalizer ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS prose     ON chapter TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS updated   ON chapter TYPE datetime VALUE time::now();

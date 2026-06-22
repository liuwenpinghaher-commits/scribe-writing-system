-- scribe3 故事本体 v2 · NS=scribe3 schema(S0 子集,后续段扩)
-- 核心表 SCHEMAFULL 强约束(防 LLM 写脏);可变元数据后续用 FLEXIBLE。
-- 持续体/发生体分明:character/place=持续体;event=发生体;proposition=quality(状态@章)。

-- ===== 持续体节点 =====
DEFINE TABLE character SCHEMAFULL;
DEFINE FIELD name      ON character TYPE string ASSERT string::len($value) > 0;
DEFINE FIELD aliases   ON character TYPE array<string> DEFAULT [];
DEFINE FIELD backstory ON character TYPE option<string>;          -- 冰山·私密前史
DEFINE FIELD created   ON character TYPE datetime VALUE time::now() READONLY;

DEFINE TABLE place SCHEMAFULL;
DEFINE FIELD name      ON place TYPE string ASSERT string::len($value) > 0;

-- ===== 命题/事实(知识帧载体;状态@章,双时态 valid 自建)=====
DEFINE TABLE proposition SCHEMAFULL;
DEFINE FIELD entity       ON proposition TYPE string;             -- 主体 oid(如 role:焦三 / place:乱岗)
DEFINE FIELD attribute    ON proposition TYPE string;
DEFINE FIELD value        ON proposition TYPE string;
DEFINE FIELD valid_from   ON proposition TYPE int;                -- 故事内生效起点(章)
DEFINE FIELD valid_to     ON proposition TYPE option<int>;        -- null=惯性持续
DEFINE FIELD secret       ON proposition TYPE bool DEFAULT false; -- 私密(泄露=穿帮)
DEFINE FIELD leak_markers ON proposition TYPE array<string> DEFAULT [];
DEFINE FIELD created      ON proposition TYPE datetime VALUE time::now() READONLY;

-- ===== 发生体节点(事件本体)=====
DEFINE TABLE event SCHEMAFULL;
DEFINE FIELD etype             ON event TYPE string;
DEFINE FIELD valid_from        ON event TYPE int;                 -- 章
DEFINE FIELD motivated_by_goal ON event TYPE option<string>;      -- IPOCL 硬约束
DEFINE FIELD draft_version     ON event TYPE int DEFAULT 1;       -- transaction_time(自建)
DEFINE FIELD tx_at             ON event TYPE datetime VALUE time::now();

-- ===== 知识边(RELATE,belief base;边上挂 since/polarity/来源)=====
DEFINE TABLE knows TYPE RELATION FROM character TO proposition SCHEMAFULL;
DEFINE FIELD since_chapter ON knows TYPE int;
DEFINE FIELD until_chapter ON knows TYPE option<int>;
DEFINE FIELD polarity      ON knows TYPE bool DEFAULT true;       -- false=误信
DEFINE FIELD acquired_via  ON knows TYPE string DEFAULT 'given';  -- saw/told/inferred/given

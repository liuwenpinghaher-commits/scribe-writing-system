-- scribe3 · 受控枚举 ASSERT(落库层硬拒脏值;对应 Python scribe3/enums.py)
-- 幂等策略:DEFINE FIELD OVERWRITE 重定义已有字段(SurrealDB 3.x 支持)。
-- 不动 _execute_write 单写点;仅在 schema 层加约束。

-- 知识边 acquired_via:补 learned 入域(此前 ingest.py:31 越界无校验)
DEFINE FIELD OVERWRITE acquired_via ON knows TYPE string
  ASSERT $value IN ['saw', 'told', 'inferred', 'given', 'learned'] DEFAULT 'given';

-- 伏笔 promise.kind / status
DEFINE FIELD OVERWRITE kind ON promise TYPE string
  ASSERT $value IN ['promise', 'red_herring'] DEFAULT 'promise';
DEFINE FIELD OVERWRITE status ON promise TYPE string
  ASSERT $value IN ['open', 'closed'] DEFAULT 'open';

-- 声音语域 voice_sample.kind
DEFINE FIELD OVERWRITE kind ON voice_sample TYPE string
  ASSERT $value IN ['free', 'pressure', 'relation', 'narration'];

-- 声音进化标记 status
DEFINE FIELD OVERWRITE status ON voice_evolution_flag TYPE string
  ASSERT $value IN ['open', 'done'] DEFAULT 'open';

-- 题材规则 craft_rule.kind
DEFINE FIELD OVERWRITE kind ON craft_rule TYPE string
  ASSERT $value IN ['purple_regex', 'artifact_craft', 'cover_action'];

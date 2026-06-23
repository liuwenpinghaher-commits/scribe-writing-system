-- 题材层 craft 规则(per-work):升华正则/法器写法/角色覆盖动作。
-- 引擎层(craft.py)题材无关、所有书共享;题材特化规则在此,主编经 elicitation 可改。
DEFINE TABLE IF NOT EXISTS craft_rule SCHEMALESS;
DEFINE FIELD IF NOT EXISTS kind ON craft_rule TYPE string;     -- purple_regex|artifact_craft|cover_action
DEFINE FIELD IF NOT EXISTS pattern ON craft_rule TYPE string;
DEFINE FIELD IF NOT EXISTS note ON craft_rule TYPE option<string>;

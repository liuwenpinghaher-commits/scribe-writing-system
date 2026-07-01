-- scribe3 · 049_deduction_fields.surql · 演绎工作流章字段(scene_truth/involved_characters/deductions)
-- chapter SCHEMAFULL,新字段须显式 DEFINE 方能落库(否则被严格校验丢弃/报错)。

-- scene_truth:场景客观真相(str)。
DEFINE FIELD IF NOT EXISTS scene_truth ON chapter TYPE option<string>;

-- involved_characters:涉及角色 id 列表的 JSON 串(同 beats,绕 SCHEMAFULL 嵌套校验;读时 json.loads 还原)。
DEFINE FIELD IF NOT EXISTS involved_characters ON chapter TYPE option<string>;

-- deductions:每角色限知投影列表的 JSON 串(同上)。
DEFINE FIELD IF NOT EXISTS deductions ON chapter TYPE option<string>;

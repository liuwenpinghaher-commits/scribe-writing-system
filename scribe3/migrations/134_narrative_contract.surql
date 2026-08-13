-- narrative-mainline：章级叙事合同 JSON 串（desire/obstacle/turn/cost）
-- 镜像 narrative_drive：option<string> JSON；读端 json.loads
-- 设计：docs/plans/2026-08-13-narrative-mainline.md KD14
DEFINE FIELD IF NOT EXISTS narrative_contract ON chapter TYPE option<string>;

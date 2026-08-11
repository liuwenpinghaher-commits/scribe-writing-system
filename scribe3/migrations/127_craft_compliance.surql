-- P2 产品门闩：存正文后 C-Det 结果落章（JSON 串；SCHEMAFULL 不嵌套 object）
DEFINE FIELD IF NOT EXISTS craft_compliance ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS craft_compliance_at ON chapter TYPE option<datetime>;

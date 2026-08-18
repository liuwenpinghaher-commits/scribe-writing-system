-- play-contract：戏/契约/责任卡/演绎/排演新表；旧设计字段作废。
-- 过审 play 迁入 chapter_play 标 legacy；无过审 play 的设计数据丢弃，prose 保留。

DEFINE TABLE IF NOT EXISTS duty_card SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON duty_card TYPE int;
DEFINE FIELD IF NOT EXISTS version ON duty_card TYPE int;
DEFINE FIELD IF NOT EXISTS status ON duty_card TYPE string;
DEFINE FIELD IF NOT EXISTS sha ON duty_card TYPE string;
DEFINE FIELD IF NOT EXISTS playbook_version ON duty_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_sha ON duty_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS schema_name ON duty_card TYPE option<string>;
DEFINE FIELD IF NOT EXISTS body ON duty_card TYPE string;
DEFINE INDEX IF NOT EXISTS duty_card_seq_ver ON duty_card FIELDS seq, version UNIQUE;

DEFINE TABLE IF NOT EXISTS chapter_play SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON chapter_play TYPE int;
DEFINE FIELD IF NOT EXISTS version ON chapter_play TYPE int;
DEFINE FIELD IF NOT EXISTS status ON chapter_play TYPE string;
DEFINE FIELD IF NOT EXISTS sha ON chapter_play TYPE string;
DEFINE FIELD IF NOT EXISTS playbook_version ON chapter_play TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_sha ON chapter_play TYPE option<string>;
DEFINE FIELD IF NOT EXISTS schema_name ON chapter_play TYPE option<string>;
DEFINE FIELD IF NOT EXISTS body ON chapter_play TYPE string;
DEFINE INDEX IF NOT EXISTS chapter_play_seq_ver ON chapter_play FIELDS seq, version UNIQUE;

DEFINE TABLE IF NOT EXISTS chapter_contract SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON chapter_contract TYPE int;
DEFINE FIELD IF NOT EXISTS version ON chapter_contract TYPE int;
DEFINE FIELD IF NOT EXISTS status ON chapter_contract TYPE string;
DEFINE FIELD IF NOT EXISTS sha ON chapter_contract TYPE string;
DEFINE FIELD IF NOT EXISTS playbook_version ON chapter_contract TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_sha ON chapter_contract TYPE option<string>;
DEFINE FIELD IF NOT EXISTS schema_name ON chapter_contract TYPE option<string>;
DEFINE FIELD IF NOT EXISTS body ON chapter_contract TYPE string;
DEFINE INDEX IF NOT EXISTS chapter_contract_seq_ver ON chapter_contract FIELDS seq, version UNIQUE;

DEFINE TABLE IF NOT EXISTS chapter_deduce SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON chapter_deduce TYPE int;
DEFINE FIELD IF NOT EXISTS version ON chapter_deduce TYPE int;
DEFINE FIELD IF NOT EXISTS status ON chapter_deduce TYPE string;
DEFINE FIELD IF NOT EXISTS sha ON chapter_deduce TYPE string;
DEFINE FIELD IF NOT EXISTS playbook_version ON chapter_deduce TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_sha ON chapter_deduce TYPE option<string>;
DEFINE FIELD IF NOT EXISTS schema_name ON chapter_deduce TYPE option<string>;
DEFINE FIELD IF NOT EXISTS body ON chapter_deduce TYPE string;
DEFINE INDEX IF NOT EXISTS chapter_deduce_seq_ver ON chapter_deduce FIELDS seq, version UNIQUE;

DEFINE TABLE IF NOT EXISTS chapter_draft SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS seq ON chapter_draft TYPE int;
DEFINE FIELD IF NOT EXISTS version ON chapter_draft TYPE int;
DEFINE FIELD IF NOT EXISTS status ON chapter_draft TYPE string;
DEFINE FIELD IF NOT EXISTS sha ON chapter_draft TYPE string;
DEFINE FIELD IF NOT EXISTS playbook_version ON chapter_draft TYPE option<string>;
DEFINE FIELD IF NOT EXISTS source_sha ON chapter_draft TYPE option<string>;
DEFINE FIELD IF NOT EXISTS schema_name ON chapter_draft TYPE option<string>;
DEFINE FIELD IF NOT EXISTS body ON chapter_draft TYPE string;
DEFINE INDEX IF NOT EXISTS chapter_draft_seq_ver ON chapter_draft FIELDS seq, version UNIQUE;

DEFINE FIELD IF NOT EXISTS play_sha ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS contract_sha ON chapter TYPE option<string>;
DEFINE FIELD IF NOT EXISTS playbook_version ON chapter TYPE option<string>;

-- 旧字段在 147 删除：须先跑 python migrate_legacy_plays，把过审戏抄进 chapter_play。

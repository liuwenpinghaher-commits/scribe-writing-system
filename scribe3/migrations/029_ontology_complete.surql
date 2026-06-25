-- scribe3 · 029_ontology_complete.surql · 本体论合规补全
-- 补齐设计文档门槛2-设定圣经.md 要求的全部实体

-- ===== VoiceProfile 9节结构(声音指纹) =====
-- 设计文档 §3.1.2: style_summary/catchphrases/sentence_patterns/vocabulary_profile/
--   tone_rules/internal_monologue_style/ooc_signals/reference_lines/version
-- voice_sample 已有 character/kind/text/since_chapter, 补 voice_profile 表存 9 节
DEFINE TABLE IF NOT EXISTS voice_profile SCHEMALESS;
DEFINE FIELD IF NOT EXISTS character_id           ON voice_profile TYPE string;
DEFINE FIELD IF NOT EXISTS style_summary           ON voice_profile TYPE option<string>;
DEFINE FIELD IF NOT EXISTS catchphrases            ON voice_profile TYPE option<array>;
DEFINE FIELD IF NOT EXISTS sentence_patterns       ON voice_profile TYPE option<object>;
DEFINE FIELD IF NOT EXISTS vocabulary_profile      ON voice_profile TYPE option<object>;
DEFINE FIELD IF NOT EXISTS tone_rules             ON voice_profile TYPE option<array>;
DEFINE FIELD IF NOT EXISTS internal_monologue_style ON voice_profile TYPE option<string>;
DEFINE FIELD IF NOT EXISTS ooc_signals             ON voice_profile TYPE option<array>;
DEFINE FIELD IF NOT EXISTS reference_lines         ON voice_profile TYPE option<object>;
DEFINE FIELD IF NOT EXISTS version                 ON voice_profile TYPE option<int>;
DEFINE FIELD IF NOT EXISTS last_updated_chapter    ON voice_profile TYPE option<int>;
DEFINE INDEX IF NOT EXISTS idx_vp_char ON voice_profile FIELDS character_id;

-- ===== item 表(物品/道具,设计文档 §3.1.4) =====
DEFINE TABLE IF NOT EXISTS item SCHEMALESS;
DEFINE FIELD IF NOT EXISTS name             ON item TYPE string;
DEFINE FIELD IF NOT EXISTS category         ON item TYPE option<string>;
DEFINE FIELD IF NOT EXISTS description      ON item TYPE option<string>;
DEFINE FIELD IF NOT EXISTS current_owner    ON item TYPE option<string>;
DEFINE FIELD IF NOT EXISTS symbolic_state   ON item TYPE string DEFAULT 'active'
    ASSERT $value IN ['active','lost','destroyed','unknown'];
DEFINE FIELD IF NOT EXISTS state_history    ON item TYPE option<array>;
DEFINE FIELD IF NOT EXISTS special_properties ON item TYPE option<array>;
DEFINE FIELD IF NOT EXISTS first_chapter    ON item TYPE option<int>;
DEFINE INDEX IF NOT EXISTS idx_item_state ON item FIELDS symbolic_state;

-- ===== term 表(专有名词/术语,设计文档 §3.1.4) =====
DEFINE TABLE IF NOT EXISTS term SCHEMALESS;
DEFINE FIELD IF NOT EXISTS name             ON term TYPE string;
DEFINE FIELD IF NOT EXISTS category         ON term TYPE option<string>;
DEFINE FIELD IF NOT EXISTS definition       ON term TYPE option<string>;
DEFINE FIELD IF NOT EXISTS aliases          ON term TYPE option<array>;
DEFINE FIELD IF NOT EXISTS first_mention_chapter ON term TYPE option<int>;
DEFINE INDEX IF NOT EXISTS idx_term_name ON term FIELDS name;

-- ===== character_relation 词表扩展(设计文档 §3.1.5: 15+词) =====
-- 旧: ally/enemy/kin/master_disciple/lover
-- 新: 扩展为设计文档受控词表 + custom
DEFINE FIELD OVERWRITE relation ON character_relation TYPE string
    ASSERT $value IN [
        '父子','母子','兄弟','姐妹','夫妻','师徒','养父子',
        '知己','战友','盟友','同门','恩人',
        '同行','熟人','上下级','雇主雇员',
        '仇敌','宿敌','竞争者','利益对立',
        '爱恨交织','前恋人','背叛者',
        'ally','enemy','kin','master_disciple','lover',
        'custom'
    ];

-- ===== character aliases 字段(精确名/别名匹配用) =====
DEFINE FIELD IF NOT EXISTS aliases ON character TYPE option<array> DEFAULT [];

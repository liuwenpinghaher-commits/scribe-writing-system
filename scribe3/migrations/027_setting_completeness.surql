-- scribe3 · 027_setting_completeness.surql · 设定完整性框架(层1)
-- 参考:门槛2-设定圣经.md §3.1 的完整角色/世界/势力/地点结构

-- ===== 角色深描:traits + motivation =====
DEFINE FIELD IF NOT EXISTS traits ON character TYPE option<object>;
DEFINE FIELD IF NOT EXISTS motivation ON character TYPE option<object>;
DEFINE FIELD IF NOT EXISTS importance ON character TYPE option<string>
    ASSERT $value IN ['protagonist','major','minor','background'] OR $value IS NONE;

-- ===== 世界规则表(Sanderson 式:源头/能力/代价/限制/例外) =====
DEFINE TABLE IF NOT EXISTS world_rule SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name        ON world_rule TYPE string;
DEFINE FIELD IF NOT EXISTS category    ON world_rule TYPE string
    ASSERT $value IN ['magic','technology','social','physical','economic','political'];
DEFINE FIELD IF NOT EXISTS source      ON world_rule TYPE option<string>;
DEFINE FIELD IF NOT EXISTS capabilities ON world_rule TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS cost        ON world_rule TYPE option<string>;
DEFINE FIELD IF NOT EXISTS limitations ON world_rule TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS exceptions  ON world_rule TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS scope       ON world_rule TYPE string DEFAULT 'global'
    ASSERT $value IN ['global','regional','faction_specific'];
DEFINE FIELD IF NOT EXISTS established_chapter ON world_rule TYPE option<int>;
DEFINE FIELD IF NOT EXISTS note        ON world_rule TYPE option<string>;
DEFINE INDEX IF NOT EXISTS idx_worldrule_category ON world_rule FIELDS category;

-- ===== 势力/组织表 =====
DEFINE TABLE IF NOT EXISTS faction SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name      ON faction TYPE string;
DEFINE FIELD IF NOT EXISTS ideology  ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS status    ON faction TYPE string DEFAULT 'active'
    ASSERT $value IN ['active','dissolved','dormant','reformed'];
DEFINE FIELD IF NOT EXISTS leader     ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS known_members ON faction TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS public_face ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS private_operation ON faction TYPE option<string>;
DEFINE FIELD IF NOT EXISTS first_mention_chapter ON faction TYPE option<int>;
DEFINE INDEX IF NOT EXISTS idx_faction_status ON faction FIELDS status;

-- ===== 地点扩展:geography + notable_events =====
DEFINE FIELD IF NOT EXISTS geography ON place TYPE option<object>;
DEFINE FIELD IF NOT EXISTS notable_events ON place TYPE array<string> DEFAULT [];
DEFINE FIELD IF NOT EXISTS first_visit_chapter ON place TYPE option<int>;
DEFINE FIELD IF NOT EXISTS political_affiliation ON place TYPE option<string>;

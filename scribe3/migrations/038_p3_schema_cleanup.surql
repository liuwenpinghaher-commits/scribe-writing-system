-- scribe3 · 038_p3_schema_cleanup.surql · P3-c schema 清债
-- 审计 C4/G/H:删除死列、加约束、建 UNIQUE 索引

-- ===== 1) chapter 死列删除 =====
-- qc_issues/qc_causal/qc_at: 死缓存列,/quality 在运行时计算同名 key,从未有意义地写入/读取。
-- qc_word_count 是 LIVE 字段(save_chapter 写入,stats() 读取),保留。
REMOVE FIELD IF EXISTS qc_issues ON chapter;
REMOVE FIELD IF EXISTS qc_causal ON chapter;
REMOVE FIELD IF EXISTS qc_at ON chapter;

-- ===== 2) chapter_version.kind 加枚举约束 =====
-- 旧定义(032)无 ASSERT,任意字符串可写入;OVERWRITE 补上枚举校验,同时保留 DEFAULT "checkpoint"。
DEFINE FIELD OVERWRITE kind ON chapter_version TYPE string DEFAULT "checkpoint" ASSERT $value IN ['checkpoint', 'final'];

-- ===== 3) 设定表 name UNIQUE 索引 =====
-- 各 add_* 方法均为 DELETE-before-CREATE 幂等,现有数据唯一,UNIQUE 只会加固。
DEFINE INDEX IF NOT EXISTS uniq_faction_name ON faction FIELDS name UNIQUE;
DEFINE INDEX IF NOT EXISTS uniq_item_name ON item FIELDS name UNIQUE;
DEFINE INDEX IF NOT EXISTS uniq_term_name ON term FIELDS name UNIQUE;
DEFINE INDEX IF NOT EXISTS uniq_world_rule_name ON world_rule FIELDS name UNIQUE;

-- ===== 4) place 027 扩展死字段删除 =====
-- geography/first_visit_chapter/political_affiliation/notable_events:
-- 均为 027_setting_completeness 引入的孤儿列,无 MCP 工具/API/UI 读取。
-- notable_events 虽由 tools/extract_settings.py 写入,但该写入为初始化脚本的孤立操作,
-- 且无任何消费端(无读路径),同时从工具侧删除该写入,一并清除。
REMOVE FIELD IF EXISTS geography ON place;
REMOVE FIELD IF EXISTS first_visit_chapter ON place;
REMOVE FIELD IF EXISTS political_affiliation ON place;
REMOVE FIELD IF EXISTS notable_events ON place;

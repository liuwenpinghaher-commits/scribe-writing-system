-- scribe3 · 085_entity_relation.surql · 通用实体关系表(CX-Task 5:双向认知 + 主编独知 truth + 时态)
-- 背景(spec `docs/superpowers/specs/2026-07-14-codex-layer-redesign.md` §3):既有
-- 020_character_relation.surql 是 character→character 的 `TYPE RELATION` 边表,RELATE
-- 语义要求两端必须是真实存在的 character 记录——锁死了实体类型,也没有"双方认知可以
-- 不对称、甚至任一方是错的"这层语义。作者的核心诉求是"秘会看天龙座(虚与委蛇/视为
-- 台阶)vs 天龙座看秘会(视其为地球代理人),而且对方的认知可能是错的",还需要一层
-- 唯主编知道的客观真相(truth)——单向碎片不是关系网。
--
-- 故新建独立 SCHEMAFULL 普通表(不是 TYPE RELATION):a/b 是自由字符串实体引用
-- (前缀+本地 id,如 "faction:衔尾蛇秘会"/"role:焦三",与 codex_secret_bridge.py 已确认
-- 的 proposition.entity_id 惯例一致),不做记录存在性校验、不锁实体类型
-- (faction↔character、character↔item……任意组合皆可存)。
--
-- 020_character_relation.surql 本迁移零改动,两表并存、互不影响。
--
-- ⚠️ truth_secret 刻意用 `option<bool>`(不是 `bool DEFAULT true`)——见
-- 083_faction_expand.surql 头部记录的 P0 教训:`DEFAULT` 只在 CREATE 时生效,不回填
-- 已存在的老行;若老行该字段实为 NONE,SurrealDB 写入时校验整条记录,此后对该行的任何
-- 写操作(含 MERGE)都会永久 500。entity_relation 是本迁移新建的表,当下没有"老行"这个
-- 具体触发条件,但为了不给"下一个抄这份 migration 当模板的人"埋雷,统一按"bool 一律
-- option<bool>,默认值交给应用层"的安全习惯办:store.add_entity_relation 在 Python 侧
-- 对新建行注入默认 True(未显式指定时"宁可误锁不可误放"),读取侧(app.py/mcp.py 的
-- 掩码逻辑)一律 `bool(x)` 处理 None。

DEFINE TABLE IF NOT EXISTS entity_relation SCHEMAFULL;

DEFINE FIELD IF NOT EXISTS a ON entity_relation TYPE string;
DEFINE FIELD IF NOT EXISTS b ON entity_relation TYPE string;

-- relation_type 合法词表与 scribe3/codex_schema.py 的 ENTITY_RELATION_TYPES 同源
-- (单一权威源在 Python 侧;DB 侧 ASSERT 是必然的手写镜像,SurrealDB migration 无法
-- import Python 常量——若改动词表,两处必须一并更新,与 faction.status 的既有先例一致)。
DEFINE FIELD IF NOT EXISTS relation_type ON entity_relation TYPE string
    ASSERT $value IN ['臣服','敌对','渗透','无视','共生','结盟','利用','未知'];

DEFINE FIELD IF NOT EXISTS perception_a ON entity_relation TYPE option<string>;
DEFINE FIELD IF NOT EXISTS perception_b ON entity_relation TYPE option<string>;
DEFINE FIELD IF NOT EXISTS truth        ON entity_relation TYPE option<string>;
DEFINE FIELD IF NOT EXISTS truth_secret ON entity_relation TYPE option<bool>;

DEFINE FIELD IF NOT EXISTS since_chapter ON entity_relation TYPE option<int>;
DEFINE FIELD IF NOT EXISTS until_chapter ON entity_relation TYPE option<int>;

-- 非唯一复合索引(任务描述原话:防重「或按需」)。刻意不设 UNIQUE:关系可能"结束后
-- 重修"——同一 (a,b,relation_type,since_chapter) 在关闭(until_chapter 非空)之后
-- 允许再开一条新的当前生效行,UNIQUE 会拒绝这种合法场景。真正的"防重"落在
-- store.add_entity_relation 的自然键 upsert(先查后写:命中仍开着的同键行则 MERGE,
-- 否则才 CREATE),不落在 DB 约束上;此索引只负责加速该 upsert 查询与按 a/b 的常规检索。
DEFINE INDEX IF NOT EXISTS idx_entrel_abtype ON entity_relation
    FIELDS a, b, relation_type, since_chapter;

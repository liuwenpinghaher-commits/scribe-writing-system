-- scribe3 · 047_scalability_cache.surql · 千万字可扩展基座(Phase0-BE1)
-- 头号病灶:outline()/project_tree() 把全书正文拉进内存仅为切场景数;
-- quality() 每章全量重算。补章级缓存列,聚合端点改读缓存,不再全表拉 prose / 全量重算。

-- scene_count:章内场景段数(_split_scenes 切分),save_chapter 写入,outline() 读。
DEFINE FIELD IF NOT EXISTS scene_count ON chapter TYPE option<int>;

-- scene_meta:场景轻量详情 [{title, char_count}, ...] 的 JSON 串,供 project_tree 建场景子节点,
-- 免得为画树重新拉全书正文。save_chapter 写入。
-- 存 JSON 串(option<string>)而非 array<object>:chapter 表 SCHEMAFULL,严格校验嵌套对象
-- 子字段;序列化为串可彻底绕开嵌套 schema,读时 json.loads 还原(数据轻、读写对称)。
DEFINE FIELD IF NOT EXISTS scene_meta  ON chapter TYPE option<string>;

-- qc_issues / qc_causal:章级 QC 缓存(038 曾删的死列,此处复活并真正写入)。
-- save_chapter 落库时算好存列;quality() 直接聚合,不再每章全文重算 + 逐章查图。
DEFINE FIELD IF NOT EXISTS qc_issues   ON chapter TYPE option<int>;
DEFINE FIELD IF NOT EXISTS qc_causal   ON chapter TYPE option<int>;

-- qc_breakdown:五类 QC 计数 {repetition,structural,purple,ai_tics,oversaturation} 的 JSON 串。
-- /quality 返回 qc_breakdown 字段不变;缓存避免每章重跑 quality_flags(同 scene_meta 用串绕嵌套 schema)。
DEFINE FIELD IF NOT EXISTS qc_breakdown ON chapter TYPE option<string>;

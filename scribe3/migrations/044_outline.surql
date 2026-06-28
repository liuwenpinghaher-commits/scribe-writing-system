-- scribe3 · 044_outline.surql · 作者工具:大纲/卷章树(手稿支数据层)
-- 新建 volume 表(卷:一等结构对象);chapter 加 synopsis/volume/sort_order/label。
-- 一书一 DB,不含 work 字段(与 chapter 同例,每书独立 db 隔离)。

-- ===== 卷(volume):一等结构对象 =====
-- 一卷含多章(chapter.volume 反向链接)。独立建表以承载卷自身属性。
DEFINE TABLE IF NOT EXISTS volume SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS title     ON volume TYPE string DEFAULT '';
DEFINE FIELD IF NOT EXISTS sort_order ON volume TYPE int DEFAULT 0;   -- 卷展示序
DEFINE FIELD IF NOT EXISTS intro     ON volume TYPE option<string>;   -- 卷简介(可选)
DEFINE FIELD IF NOT EXISTS color     ON volume TYPE option<string>;   -- 卷色带(可选)
DEFINE FIELD IF NOT EXISTS updated   ON volume TYPE datetime VALUE time::now();
DEFINE INDEX IF NOT EXISTS idx_volume_sort ON volume FIELDS sort_order;

-- ===== chapter 增列:梗概 / 卷链接 / 排序权重 / 色彩标签 =====
-- synopsis:每章梗概(大纲用,不碰 prose)
DEFINE FIELD IF NOT EXISTS synopsis   ON chapter TYPE option<string>;
-- volume:chapter → volume 的 record link(可选;NONE = 未分卷)
-- 选 record<volume> 而非 string:与现有 chapter 表的 focalizer(option<string>) 保持类型纪律,
-- 同时利用 SurrealDB record link 语义(meta::id(volume) 提取裸 id,删卷可 UPDATE 置 NONE 无孤儿)。
DEFINE FIELD IF NOT EXISTS volume     ON chapter TYPE option<record<volume>>;
-- sort_order:展示排序权重(独立于 seq;seq 是主键/故事时间轴,不能因重排而改动)
DEFINE FIELD IF NOT EXISTS sort_order ON chapter TYPE option<int>;
-- label:色彩编码枚举(可选)
DEFINE FIELD IF NOT EXISTS label      ON chapter TYPE option<string>
  ASSERT $value = NONE OR $value IN ['draft', 'revise', 'done', 'idea', 'beat'];

-- ===== 回填:已有章 sort_order 初始化为 seq =====
-- 保证旧数据有稳定展示序;WHERE sort_order = NONE 保证幂等重跑安全。
UPDATE chapter SET sort_order = seq WHERE sort_order = NONE;

-- scribe3 · 048_four_stage.surql · 四阶段写作数据模型(Phase0-BE2)
-- 章四阶段:大纲(synopsis,已有)/ 节拍(beats,本迁移)/ 草稿(draft,本迁移)/ 正文(prose,已有)。
-- chapter / chapter_version 均 SCHEMAFULL,新字段须显式 DEFINE 方能落库(否则被严格校验丢弃)。

-- beats:节拍列表的 JSON 串。每节拍 {text, done?}。
-- 存 JSON 串(option<string>)而非 array<object>:同 047 的 scene_meta,绕开 SCHEMAFULL 嵌套校验,
-- 读时 json.loads 还原。
DEFINE FIELD IF NOT EXISTS beats ON chapter TYPE option<string>;

-- draft:草稿正文,与定稿 prose 分离。草稿是"写手期"产出,采用后留版、刷新恢复最新。
DEFINE FIELD IF NOT EXISTS draft ON chapter TYPE option<string>;

-- chapter_version 扩字段(032 已建表,此处补列):
-- stage:'draft'(草稿版)| 'final'(正文版)。旧版本无此字段时读端降级为 'final'。
DEFINE FIELD IF NOT EXISTS stage   ON chapter_version TYPE string DEFAULT "final";
-- summary:作者/系统给该版本的一句话摘要。
DEFINE FIELD IF NOT EXISTS summary ON chapter_version TYPE string DEFAULT "";
-- stats:{words, avg_sentence, dialog_count} 的 JSON 串(同 beats,绕嵌套校验)。
DEFINE FIELD IF NOT EXISTS stats   ON chapter_version TYPE option<string>;

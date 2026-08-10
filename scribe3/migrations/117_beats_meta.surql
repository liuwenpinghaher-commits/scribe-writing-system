-- scribe3 · beats_meta：节拍 v2 元数据 JSON 串（schema/chapter_hook/beats_source/drama_validation/…）
-- chapter SCHEMAFULL：新字段须显式 DEFINE，否则静默丢弃/报错（同 048/049/114）。
-- 存 option<string> JSON，绕嵌套 object 校验；读端 json.loads（镜像 pressure_drive）。
DEFINE FIELD IF NOT EXISTS beats_meta ON chapter TYPE option<string>;

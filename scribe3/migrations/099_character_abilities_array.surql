-- Codex 注册表把 abilities 定义为 array<string>；031 曾误设为 option<string>，
-- 导致动态表单提交数组时被 SCHEMAFULL 拒绝。先重定义，再把历史单字符串保留为单元素数组。
-- SurrealDB 2.1.x 用 type::is::string()（type::is_string 会 Parse error，导致整书 500）。
DEFINE FIELD OVERWRITE abilities ON character TYPE option<array<string>>;
UPDATE character SET abilities = [abilities] WHERE type::is::string(abilities);

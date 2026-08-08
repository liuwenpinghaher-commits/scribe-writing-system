-- Codex 注册表把 abilities 定义为 array<string>；031 曾误设为 option<string>，
-- 导致动态表单提交数组时被 SCHEMAFULL 拒绝。先重定义，再把历史单字符串保留为单元素数组。
-- SurrealDB 3.x: type::is_string()（2.x 旧式 type::is::string 已移除）。
DEFINE FIELD OVERWRITE abilities ON character TYPE option<array<string>>;
UPDATE character SET abilities = [abilities] WHERE type::is_string(abilities);

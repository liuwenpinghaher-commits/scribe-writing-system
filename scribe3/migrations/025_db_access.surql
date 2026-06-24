-- scribe3 · 025_db_access.surql · F枢纽 DB权限(暴露场景)
-- 本地单用户不需要;暴露/多用户时 apply 此迁移。
-- 建 NS 级非 root 应用账户(EDITOR 权限,不能改 schema/删库)
DEFINE USER IF NOT EXISTS scribe3_app ON NAMESPACE PASSWORD 'changeme' ROLES EDITOR;

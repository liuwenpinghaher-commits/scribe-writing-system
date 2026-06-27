-- P3-e1 Fix 4: 删除 voice_sample 冗余死表
-- voice_sample 有 ZERO 生产写入者;voice_profile.reference_lines 承担同职责。
-- 移除 voice_sample 表及其全部数据(若有)。
REMOVE TABLE IF EXISTS voice_sample;

-- P3-e1 Fix 1: intent 表新增 overdue_threshold 可选字段(per-work overdue 阈值覆盖)
-- SCHEMAFULL → 须显式 DEFINE FIELD;int | null 允许空=使用全局 OVERDUE_SLACK 常量。
DEFINE FIELD IF NOT EXISTS overdue_threshold ON intent TYPE option<int>;

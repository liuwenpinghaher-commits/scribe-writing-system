-- scribe3 · 067_distill_marker.surql · 蒸馏幂等标记(P1门对抗审查 P1-1)
-- 每次 /save-chapter 都排后台 ingest → 同章对话被反复蒸馏:importance 被同章重跑
-- 虚增到升格阈(真机复现 3 次→4)+每次白烧一发长 prompt。标记=章的(消息数+最新 turn),
-- 对话无新增即跳过蒸馏。
DEFINE TABLE IF NOT EXISTS distill_marker SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS chapter ON distill_marker TYPE int;
DEFINE FIELD IF NOT EXISTS msg_count ON distill_marker TYPE int;
DEFINE FIELD IF NOT EXISTS last_turn ON distill_marker TYPE string;
DEFINE FIELD IF NOT EXISTS ts ON distill_marker TYPE datetime;

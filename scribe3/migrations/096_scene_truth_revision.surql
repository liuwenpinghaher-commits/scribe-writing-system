-- scribe3 · 096_scene_truth_revision.surql
-- 场景真相单调 revision：投影 based_on_truth_rev 对齐此字段以判定 stale。
-- 缺省 NONE/0 = 未 bump；首次改写真相后递增。不自动重写历史投影。

DEFINE FIELD IF NOT EXISTS scene_truth_revision ON chapter TYPE option<int>;

-- 限知帧规模化：122 的实现在长篇上是二次复杂度，千万字量级实测 32.7 秒。
--
-- 旧实现末段 `WHERE meta::id(id) IN $known.prop_local`，$known.prop_local 是 idiom
-- 投影，会在 proposition 每一行上重算一次（主角 8355 条已知 × 3 万行命题）。
-- 实测（3000 章 / 3 万命题 / 15 万边，主角独占 8000 条边，查第 3000 章）：
--   主角  32765 ms → 244 ms
--   配角   1767 ms → 4.8 ms
-- 结果集与旧实现逐条一致（覆盖 polarity=false / until_chapter 过期 / valid_to 失效
--   / archived / role: 前缀 / 不存在的角色 / 一命题多条边去重）。
--
-- 前半段 `meta::id(in) = $klocal` 用函数包住了字段，索引用不上；改成按 record 直接比，
-- 配合下面的 idx_knows_in 才生效。只加索引不改写法无效（实测仍 32.5 秒）。

DEFINE INDEX IF NOT EXISTS idx_knows_in ON knows FIELDS in;

-- 旧实现留档：出问题可直接对拍 fn::knowledge_frame_v1，确认是新写法的锅还是数据的锅。
DEFINE FUNCTION OVERWRITE fn::knowledge_frame_v1($knower: string, $chapter: int) {
    LET $klocal = string::replace($knower, 'role:', '');
    LET $edges = (
        SELECT meta::id(out) AS prop_local, since_chapter, until_chapter, polarity
        FROM knows
        WHERE meta::id(in) = $klocal
           OR string::concat('role:', meta::id(in)) = $knower
    );
    LET $known = (
        SELECT prop_local FROM $edges
        WHERE (polarity = true OR polarity = NONE)
          AND since_chapter <= $chapter
          AND (until_chapter = NONE OR until_chapter > $chapter)
    );
    RETURN (
        SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, secret, leak_markers
        FROM proposition
        WHERE meta::id(id) IN $known.prop_local
          AND valid_from <= $chapter
          AND (valid_to = NONE OR valid_to > $chapter)
          AND (archived = NONE OR archived != true)
    );
};

-- array::distinct 不能省：同一命题被多条 knows 边指向（重复获知 / 重复 ingest）时，
-- 旧实现在命题表上匹配天然去重，展开边则会重复计数。
DEFINE FUNCTION OVERWRITE fn::knowledge_frame($knower: string, $chapter: int) {
    LET $klocal = string::replace($knower, 'role:', '');
    LET $c = type::record('character', $klocal);
    RETURN (
        SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, secret, leak_markers
        FROM array::distinct((
            SELECT VALUE out FROM knows
            WHERE in = $c
              AND (polarity = true OR polarity = NONE)
              AND since_chapter <= $chapter
              AND (until_chapter = NONE OR until_chapter > $chapter)
        ))
        WHERE valid_from <= $chapter
          AND (valid_to = NONE OR valid_to > $chapter)
          AND (archived = NONE OR archived != true)
    );
};

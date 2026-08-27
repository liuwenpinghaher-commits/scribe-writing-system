-- scribe3 · 169_reader_frame_fn.surql · 限知帧支持读者
--
-- fn::knowledge_frame 一直只查 knows 表，而读者帧存在**另一张表** reader_knows
-- （002 建的，只有 proposition + since_chapter，没有 knower——读者只有一个）。
-- 于是 knower='reader' 查 `knows WHERE in = character:reader` 必然空集，
-- dramatic_irony 拿不到读者帧，静默回退 Python 全表扫（千万字规模 2.3 秒）。
--
-- 这里在函数里分支。reader 路径用和主路径一样的 record link 写法，
-- 别重蹈 122 那个 `IN $idiom投影` 的覆辙——读者知道的比任何角色都多，
-- 千万字规模下那个写法会是最慢的一条。
--
-- reader_knows.proposition 存的是字符串，历史上有 'fact:local' 和裸 'local' 两种写法
-- （见 recall.py:373 的兼容注释），两种都要认。

DEFINE FUNCTION OVERWRITE fn::knowledge_frame($knower: string, $chapter: int) {
    LET $klocal = string::replace($knower, 'role:', '');

    IF $klocal = 'reader' {
        LET $recs = (
            SELECT VALUE type::record('proposition', string::replace(proposition, 'fact:', ''))
            FROM reader_knows
            WHERE since_chapter <= $chapter
        );
        RETURN (
            SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, secret, leak_markers
            FROM array::distinct($recs)
            WHERE valid_from <= $chapter
              AND (valid_to = NONE OR valid_to > $chapter)
              AND (archived = NONE OR archived != true)
        );
    };

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

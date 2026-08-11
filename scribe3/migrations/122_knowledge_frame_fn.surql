-- S-5: 知识帧投影下沉（DEFINE FUNCTION）
-- 返回 knower 在 chapter 已知的 proposition 行（id/local 等）
DEFINE FUNCTION IF NOT EXISTS fn::knowledge_frame($knower: string, $chapter: int) {
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

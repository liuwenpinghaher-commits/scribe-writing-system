"""验证 tokenize_for_fts + SurrealDB FULLTEXT BM25 中文可行性（3.x）。"""
from scribe3.text_tokens import tokenize_for_fts


def test_jieba_bm25_chinese_ranking(store):
    store._execute_write("DEFINE ANALYZER probe_zh TOKENIZERS blank FILTERS lowercase", {})
    store._execute_write(
        "DEFINE INDEX probe_fts ON probe FIELDS tokens FULLTEXT ANALYZER probe_zh BM25", {})
    docs = [("血玉铜炉在密室中散发寒气", "d1"),
            ("江湖上流传的传说故事", "d2"),
            ("密室里的机关暗器", "d3")]
    for text, did in docs:
        toks = tokenize_for_fts(text)
        store._execute_write("CREATE type::record('probe',$id) SET tokens=$t",
                             {"id": did, "t": toks})
    q = tokenize_for_fts("密室")
    rows = store._query(
        "SELECT meta::id(id) AS id, search::score(1) AS s FROM probe "
        "WHERE tokens @1@ $q ORDER BY s DESC", {"q": q})
    ids = [r["id"] for r in rows]
    assert "d1" in ids, f"含'密室'的 d1 应命中,实得 {ids}"
    assert "d3" in ids, f"含'密室'的 d3 应命中,实得 {ids}"
    assert "d2" not in ids, f"不含'密室'的 d2 不应命中,实得 {ids}"
    # 嵌套「铜炉」vs 查询整词
    q2 = tokenize_for_fts("铜炉")
    rows2 = store._query(
        "SELECT meta::id(id) AS id FROM probe WHERE tokens @1@ $q", {"q": q2})
    assert "d1" in [r["id"] for r in rows2], f"铜炉应命中 d1, tokens_q={q2}"

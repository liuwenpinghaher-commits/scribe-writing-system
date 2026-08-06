"""Phase0 Task0.1 预研:验证 jieba 分词 + SurrealDB BM25 search::score 中文可行性。

SurrealDB 原生 tokenizer 无 CJK 分词(中文整句变一个 token)。方案:jieba 切词写
tokens 字段,SurrealDB 用 blank tokenizer 对已分词文本做 BM25 + search::score 排序。
本探针验证该组合在真机(内存 SurrealDB)上的实际行为;通过则 Phase2 全文通道走此路径,
不通则降级纯 jieba+Python BM25 计分。
"""
import jieba


def test_jieba_bm25_chinese_ranking(store):
    # 先定义 analyzer + BM25 索引,再插数据(插入时自动索引)
    store._execute_write("DEFINE ANALYZER probe_zh TOKENIZERS blank FILTERS lowercase", {})
    # SurrealDB 2.1.x: SEARCH ANALYZER；3.x 才是 FULLTEXT（demo/prod 为 2.1.4）
    store._execute_write(
        "DEFINE INDEX probe_fts ON probe FIELDS tokens SEARCH ANALYZER probe_zh BM25", {})
    docs = [("血玉铜炉在密室中散发寒气", "d1"),
            ("江湖上流传的传说故事", "d2"),
            ("密室里的机关暗器", "d3")]
    for text, did in docs:
        toks = " ".join(w for w in jieba.cut(text) if w.strip())
        store._execute_write("CREATE type::thing('probe',$id) SET tokens=$t",
                             {"id": did, "t": toks})
    # 查询"密室"(jieba 切),BM25 打分排序
    q = " ".join(jieba.cut("密室"))
    rows = store._query(
        "SELECT meta::id(id) AS id, search::score(1) AS s FROM probe "
        "WHERE tokens @1@ $q ORDER BY s DESC", {"q": q})
    ids = [r["id"] for r in rows]
    assert "d1" in ids, f"含'密室'的 d1 应命中,实得 {ids}"
    assert "d3" in ids, f"含'密室'的 d3 应命中,实得 {ids}"
    assert "d2" not in ids, f"不含'密室'的 d2 不应命中,实得 {ids}"

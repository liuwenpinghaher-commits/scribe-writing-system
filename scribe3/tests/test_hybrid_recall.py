"""Test RRF fusion + hybrid recall (B+E RAG融合 分析报告优化#2).

RRF (Reciprocal Rank Fusion): 融合多路排序列表(向量+关键词+图),k=60。
"""
import pytest

from scribe3.enums import AcquiredVia
from scribe3.ontology import Entity, Fact, KnowledgeEdge


class TestReciprocalRankFusion:
    """RRF 纯函数:融合多路排序列表"""

    def test_fusion_combines_ranks(self):
        from scribe3.store import _reciprocal_rank_fusion

        result = _reciprocal_rank_fusion(
            ["a", "b", "c"],       # 路1: a最好
            ["c", "a", "b"],       # 路2: c最好
            k=60,
        )
        # a在路1排第1(得分1/61)+路2排第2(得分1/62)
        # c在路1排第3(得分1/63)+路2排第1(得分1/61)
        ids = [r[0] for r in result]
        assert ids[0] in ("a", "c")  # a或c排第一取决于rank
        assert len(result) == 3

    def test_item_in_all_lists_ranks_higher(self):
        from scribe3.store import _reciprocal_rank_fusion

        result = _reciprocal_rank_fusion(
            ["a", "b", "x"],       # x在路1排第3
            ["c", "a", "x"],       # x在路2排第3
            ["d", "a", "x"],       # x在路3排第3
            k=60,
        )
        ids = [r[0] for r in result]
        assert ids[0] == "a"  # a在所有3路中都排前,综合分最高

    def test_single_list_noop(self):
        from scribe3.store import _reciprocal_rank_fusion

        result = _reciprocal_rank_fusion(["x", "y", "z"], k=60)
        assert [r[0] for r in result] == ["x", "y", "z"]

    def test_empty_lists_handled(self):
        from scribe3.store import _reciprocal_rank_fusion

        result = _reciprocal_rank_fusion([], ["a"], [], k=60)
        assert len(result) == 1
        assert result[0][0] == "a"


class TestKeywordRecall:
    """jieba 中文分词 + 命题 value 关键词匹配"""

    def test_chinese_tokenization(self):
        import jieba

        words = list(jieba.cut("焦三在乱岗取出尸丹"))
        assert "焦三" in words or "尸丹" in words

    def test_keyword_search_finds_proposition(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:k1", "role:甲", "获知", "焦三在乱岗取出尸丹", valid_from=1))
        store.semantic_index("fact:k1", "焦三在乱岗取出尸丹")

        from scribe3.store import _keyword_search_propositions
        results = _keyword_search_propositions(store, "焦三 尸丹", chapter=5, top_k=5)
        ids = {r.id for r in results}
        assert "fact:k1" in ids

    def test_keyword_no_match_returns_empty(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:k2", "role:甲", "获知", "下雨了", valid_from=1))

        from scribe3.store import _keyword_search_propositions
        results = _keyword_search_propositions(store, "尸丹", chapter=5, top_k=5)
        ids = {r.id for r in results}
        assert "fact:k2" not in ids

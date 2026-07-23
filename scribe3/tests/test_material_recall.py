"""Phase2 召回引擎:聚焦query/强度加权/门控/三通道RRF/LLM重排理由/block渲染。

纯函数测试不需 DB;三通道测试用 store fixture(真机)。LLM 用 mock(不烧网关)。
"""
from scribe3.material_recall import (extract_focus_query, apply_strength, gate,
                                     render_material_block, rerank_materials)


def test_focus_query():
    """长上下文提取短聚焦 query(关键实体+动作核心),截断防稀释。"""
    ctx = {"beats": ["沈砚在密室刑讯囚犯，寒气逼人" + "无关铺垫" * 20],
           "mentioned": ["沈砚"]}
    q = extract_focus_query(ctx, max_len=60)
    assert "沈砚" in q
    assert len(q) <= 60


def test_strength_weight():
    """pinned 优先;recall_count 温和加权(防马太)。"""
    cands = [{"material_id": "a", "score": 1.0, "pinned": True, "recall_count": 0},
             {"material_id": "b", "score": 1.0, "pinned": False, "recall_count": 20}]
    ranked = apply_strength(cands)
    assert ranked[0]["material_id"] == "a"


def test_gate_empty():
    """空候选门控:返回空,不触发下游 LLM。"""
    assert gate([]) == []


def test_gate_budget_keeps_top_score():
    """有预算时按强度裁剪,保留高分。"""
    cands = [
        {"material_id": "a", "score": 1.0, "title": "A", "summary": "x" * 80},
        {"material_id": "b", "score": 0.2, "title": "B", "summary": "y" * 80},
        {"material_id": "c", "score": 0.1, "title": "C", "summary": "z" * 80},
    ]
    out = gate(cands, budget_chars=100)
    assert out[0]["material_id"] == "a"
    assert len(out) <= 2


def test_render_block():
    """渲染:反照搬头 + reason + 维度化借鉴指令 + 预算裁剪;优先 summary。"""
    cands = [{"material_id": "a", "title": "密室白描", "body": "不应优先的正文",
              "summary": "冷硬的文字",
              "ref_tags": ["手法"], "reason": "冷硬白描适合刑讯"}]
    block = render_material_block(cands, budget_chars=800)
    assert "借鉴" in block and "照搬" in block
    assert "冷硬白描适合刑讯" in block
    assert "技法" in block  # 手法维度的差异化指令
    assert "冷硬的文字" in block
    assert "不应优先的正文" not in block


def test_rerank_mock_llm():
    """LLM 重排:mock 返回重排+理由。"""
    cands = [{"material_id": "a", "title": "t1", "body": "b1", "ref_tags": []},
             {"material_id": "b", "title": "t2", "body": "b2", "ref_tags": []}]
    def fake_llm(prompt, **kw):
        return '[{"id":"b","reason":"更相关"},{"id":"a","reason":"次之"}]'
    out = rerank_materials(cands, "query", fake_llm, k=2)
    assert out[0]["material_id"] == "b"
    assert out[0]["reason"] == "更相关"


def test_rerank_llm_failure_degrades():
    """LLM 失败降级 RRF 顺序 + 机械 reason,不抛。"""
    cands = [{"material_id": "a", "title": "t1", "body": "b1", "ref_tags": []}]
    def bad_llm(prompt, **kw):
        raise RuntimeError("网关炸")
    out = rerank_materials(cands, "q", bad_llm, k=5)
    assert out[0]["material_id"] == "a" and out[0].get("reason")


def test_material_recall_three_channel(store):
    """三通道召回真机:相关命中 + archived 排除。"""
    m1 = store.add_material("密室寒气", "血玉铜炉散发寒气", "snippet")
    m2 = store.add_material("无关内容", "江湖传说故事", "note")
    store.add_material("密室机关", "暗器埋伏的密室", "snippet")
    store.update_material(m2, {"archived": True})
    res = store.material_recall("密室", chapter=5, k=5)
    ids = [r["material_id"] for r in res]
    assert m1 in ids, f"相关素材 m1 应命中,实得 {ids}"
    assert m2 not in ids, f"archived 的 m2 应排除,实得 {ids}"

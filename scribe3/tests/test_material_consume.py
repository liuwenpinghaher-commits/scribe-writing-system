"""Phase3 消费接线:写作总闸素材注入 + 门控 + 溯源反哺。

用 store fixture(真机素材+召回);mock get_chapter 避免建章节复杂;fake llm 不烧网关。
"""
import scribe3.app as appmod


def test_material_recall_block_injects_and_provenance(store, monkeypatch):
    """有相关素材 → 注入参考段(带 reason);进 prompt 不等于作者已用。"""
    mid = store.add_material("密室白描", "冷硬的密室描写，寒气逼人", "snippet", ref_tags=["手法"])
    monkeypatch.setattr(store, "get_chapter", lambda seq: {"synopsis": "沈砚在密室审讯囚犯", "beats": []})
    fake_llm = lambda p, **k: f'[{{"id":"{mid}","reason":"冷硬白描适合刑讯"}}]'
    block = appmod._material_recall_block(store, chapter=1, phase="draft", llm=fake_llm)
    assert "参考记忆" in block and "冷硬白描适合刑讯" in block
    assert store.material_refs_by_chapter(1) == []
    assert (store.get_material(mid).get("recall_count") or 0) == 0


def test_material_recall_uses_current_author_request_when_chapter_brief_is_empty(store, monkeypatch):
    """临时写作要求也必须能唤起素材，不能只依赖已落库的章节草料。"""
    mid = store.add_material(
        "码头救援的潮汐节奏", "潮水先缓后急，暗溜把人拖向桥墩缝里。",
        "snippet", ref_tags=["场景技法"],
    )
    monkeypatch.setattr(store, "get_chapter", lambda seq: {"synopsis": "", "beats": []})

    block = appmod._material_recall_block(
        store, chapter=1, phase="draft",
        request_text="请写码头救援，利用潮汐暗溜制造节奏。",
    )

    assert "码头救援的潮汐节奏" in block
    assert not any(ref["material_id"] == mid for ref in store.material_refs_by_chapter(1))
    assert (store.get_material(mid).get("recall_count") or 0) == 0


def test_material_block_empty_gated(store, monkeypatch):
    """空库 → 门控返回空,不注入、不调 LLM(零开销)。"""
    monkeypatch.setattr(store, "get_chapter", lambda seq: {"synopsis": "无关内容", "beats": []})
    called = []
    block = appmod._material_recall_block(
        store, chapter=1, phase="draft", llm=lambda p, **k: called.append(1) or "[]")
    assert block == ""
    assert not called, "门控应在调 LLM 前拦截空库"


def test_editor_system_material_hint(store, monkeypatch):
    """Task3.2:素材库非空 → 主编系统提示带能力提示(引导 s3_material_recall)。"""
    store.add_material("武侠打斗资料", "冷兵器格斗的节奏", "research")
    listed = []
    orig = store.list_materials

    def wrap(*a, **k):
        listed.append(1)
        return orig(*a, **k)

    monkeypatch.setattr(store, "list_materials", wrap)
    sys_prompt = appmod._editor_system(store)
    assert "素材" in sys_prompt and "s3_material_recall" in sys_prompt
    assert listed == [], "空库探测不得扫全表 list_materials"


def test_editor_system_no_hint_when_empty(store):
    """空库不给提示(不干扰主编)。"""
    assert "s3_material_recall" not in appmod._editor_system(store)


def test_emotion_module_recallable(store):
    """Task3.4:emotion_module 素材(休眠链)现可被统一 material_recall 召回激活。"""
    import json
    card = json.dumps({"id": "EM-001", "emotion": "憋屈", "trigger": "被冤枉下狱"},
                      ensure_ascii=False)
    mid = store.add_material("憋屈反杀桥段", card, "emotion_module", ref_tags=["情绪"])
    res = store.material_recall("憋屈", chapter=5, k=5)
    assert mid in [r["material_id"] for r in res]


def _rest_client(store):
    from fastapi.testclient import TestClient
    import scribe3.app as A
    A.set_store(store)
    A.set_complete_fn(lambda p, **k: "x")
    return TestClient(A.app)


def test_material_rest_recall_and_provenance(store):
    """Task5:REST 搜索 + 双向溯源端点。"""
    mid = store.add_material("密室白描", "冷硬密室寒气逼人", "snippet", ref_tags=["手法"])
    store.add_material_reference(mid, 3, "手法", "适合刑讯", "brief")
    c = _rest_client(store)
    assert mid in [r["material_id"] for r in c.get("/materials/recall?q=密室").json()]
    refs = c.get(f"/materials/{mid}/refs").json()
    assert len(refs) == 1 and refs[0]["chapter"] == 3
    assert mid in [r["material_id"] for r in c.get("/materials/refs-by-chapter?chapter=3").json()]


def test_project_tree_includes_emotion_module(store):
    """Task5.1:项目树素材支补齐 emotion_module(前后端一致)。"""
    c = _rest_client(store)
    assert "情绪卡" in str(c.get("/project-tree").json()), "项目树素材支应含 emotion_module"


def test_material_graph_endpoint(store):
    """记忆网络端点:节点 + relates 联想边(sigma 可视化用)。"""
    m1 = store.add_material("密室A", "寒气逼人的密室机关", "snippet", ref_tags=["手法"])
    store.add_material("密室B", "寒气逼人的密室暗器", "snippet")
    store.build_material_edges(m1, top_k=3, threshold=-1.0)  # 建 relates 边
    c = _rest_client(store)
    g = c.get("/materials/graph").json()
    assert len(g["nodes"]) == 2 and any(n["title"] == "密室A" for n in g["nodes"])
    assert isinstance(g["edges"], list)   # 有 relates 边(m1 的语义近邻)

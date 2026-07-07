"""Phase3 消费接线:写作总闸素材注入 + 门控 + 溯源反哺。

用 store fixture(真机素材+召回);mock get_chapter 避免建章节复杂;fake llm 不烧网关。
"""
import scribe3.app as appmod


def test_material_recall_block_injects_and_provenance(store, monkeypatch):
    """有相关素材 → 注入参考段(带 reason),并写溯源(reason/via)。"""
    mid = store.add_material("密室白描", "冷硬的密室描写，寒气逼人", "snippet", ref_tags=["手法"])
    monkeypatch.setattr(store, "get_chapter", lambda seq: {"synopsis": "沈砚在密室审讯囚犯", "beats": []})
    fake_llm = lambda p, **k: f'[{{"id":"{mid}","reason":"冷硬白描适合刑讯"}}]'
    block = appmod._material_recall_block(store, chapter=1, phase="draft", llm=fake_llm)
    assert "参考记忆" in block and "冷硬白描适合刑讯" in block
    refs = store.material_refs_by_chapter(1)
    assert len(refs) >= 1 and refs[0]["material_id"] == mid


def test_material_block_empty_gated(store, monkeypatch):
    """空库 → 门控返回空,不注入、不调 LLM(零开销)。"""
    monkeypatch.setattr(store, "get_chapter", lambda seq: {"synopsis": "无关内容", "beats": []})
    called = []
    block = appmod._material_recall_block(
        store, chapter=1, phase="draft", llm=lambda p, **k: called.append(1) or "[]")
    assert block == ""
    assert not called, "门控应在调 LLM 前拦截空库"


def test_editor_system_material_hint(store):
    """Task3.2:素材库非空 → 主编系统提示带能力提示(引导 s3_material_recall)。"""
    store.add_material("武侠打斗资料", "冷兵器格斗的节奏", "research")
    sys_prompt = appmod._editor_system(store)
    assert "素材" in sys_prompt and "s3_material_recall" in sys_prompt


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

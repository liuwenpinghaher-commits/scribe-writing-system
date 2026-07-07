"""Phase4 导入流水线:切分打标摘要 + fail-soft(不需 DB/网关,纯逻辑 + mock LLM)。"""
from scribe3.material_import import split_and_tag


def test_split_and_tag():
    """AI 切分成多条,每条 title/kind/ref_tags/summary + source 透传。"""
    def fake_llm(p, **k):
        return ('[{"title":"冷硬白描","kind":"snippet","ref_tags":["手法"],'
                '"body":"密室寒气逼人","summary":"以物写情"},'
                '{"title":"江湖设定","kind":"reference","ref_tags":["世界观"],'
                '"body":"门派格局","summary":"势力构建"}]')
    items = split_and_tag("长资料……", fake_llm, source="某武侠")
    assert len(items) == 2
    assert items[0]["title"] == "冷硬白描" and items[0]["kind"] == "snippet"
    assert items[0]["summary"] == "以物写情" and items[0]["source"] == "某武侠"


def test_split_invalid_kind_and_no_title():
    """非法 kind 降级 note;无 title 条跳过(fail-soft)。"""
    def fake_llm(p, **k):
        return '[{"title":"有效","kind":"乱填","ref_tags":[]},{"kind":"note","body":"无标题"}]'
    items = split_and_tag("资料", fake_llm)
    assert len(items) == 1
    assert items[0]["kind"] == "note"


def test_split_llm_failure_degrades_to_single():
    """LLM 失败 → 整篇降级为一条(不丢数据)。"""
    def bad_llm(p, **k):
        raise RuntimeError("网关炸")
    items = split_and_tag("整篇内容", bad_llm)
    assert len(items) == 1 and items[0]["body"] == "整篇内容"


def test_split_empty():
    """空输入 → 空列表。"""
    assert split_and_tag("", lambda p, **k: "[]") == []


def test_import_endpoint_flow(store, monkeypatch):
    """端点闭环:POST import(text)→ 预览 → commit 落库(BackgroundTasks 同步完成)。"""
    from fastapi.testclient import TestClient
    import scribe3.app as A
    monkeypatch.setattr(
        "scribe3.llm.hermes_complete",
        lambda p, **k: '[{"title":"素材A","kind":"note","body":"内容要点",'
                       '"ref_tags":["手法"],"summary":"以物写情"}]')
    A.set_store(store)
    A.set_complete_fn(lambda prompt, **kw: "散文。")
    c = TestClient(A.app)
    r = c.post("/materials/import", data={"text": "一段长资料内容"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    prev = c.get(f"/materials/import/{job_id}/preview").json()
    assert prev["done"] and len(prev["items"]) == 1
    assert prev["items"][0]["title"] == "素材A"
    commit = c.post(f"/materials/import/{job_id}/commit", json={"items": prev["items"]})
    assert commit.json()["created"] == 1
    assert len(store.list_materials()) == 1

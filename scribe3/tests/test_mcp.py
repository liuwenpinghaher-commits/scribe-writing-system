"""S2 · scribe3 MCP server TDD(standalone,不碰 Hermes config)。

读工具放行;写工具经 elicitation 待批,批准后才走 store 单点落库。
工具名带 s3_ 前缀(与 scribe2 隔离,防同挂撞名)。
elicitation 本身是生产侧(ctx.elicit);可测核心 = commit_if_approved 门控逻辑。
"""
import asyncio

import scribe3.mcp as M
from scribe3.scenario import luanshi_leak_world

EXPECTED_WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
                        "s3_plant_promise", "s3_advance_promise",
                        "s3_craft_rule_add", "s3_craft_rule_remove"}
EXPECTED_WRITE_UNGATED = {"s3_save_chapter"}   # manuscript 草稿,非世界状态,不待批
EXPECTED_WRITE_UNGATED_WORLD = {"s3_ingest_chapter"}  # 世界知识态客观回写(读定稿抽),不待批
EXPECTED_READ = {"s3_project_frame", "s3_render_scene", "s3_find_leaks", "s3_causal_complete",
                 "s3_dramatic_irony", "s3_semantic_recall", "s3_get_chapter", "s3_qc_chapter",
                 "s3_list_promises", "s3_discipline_check", "s3_list_motifs",
                 "s3_emotion_palette", "s3_craft_rule_list"}


def test_write_gated_set_no_drift():
    assert M.WRITE_GATED == EXPECTED_WRITE_GATED


def test_requires_approval():
    for w in EXPECTED_WRITE_GATED:
        assert M.requires_approval(w) is True, f"{w} 应需批准"
    for r in EXPECTED_READ | EXPECTED_WRITE_UNGATED | EXPECTED_WRITE_UNGATED_WORLD:
        assert M.requires_approval(r) is False, f"{r} 应放行(读/草稿/客观回写)"


def test_commit_if_approved_accept_writes():
    calls = []
    out = M.commit_if_approved("s3_add_fact", True, lambda: calls.append("did"))
    assert calls == ["did"], "批准→执行写"
    assert out["status"] == "written"


def test_commit_if_approved_decline_blocks():
    calls = []
    out = M.commit_if_approved("s3_add_fact", False, lambda: calls.append("did"))
    assert calls == [], "拒绝→不写(fail-closed)"
    assert out["status"] == "declined"


def test_read_tool_project_frame_excludes_secret(store):
    luanshi_leak_world(store)
    M.set_store(store)
    laodao = M.s3_project_frame("role:老道", 1)
    vals = " ".join(x["value"] for x in laodao)
    assert "治眼" not in vals, "老道帧不含焦三私密"
    jiaosan = M.s3_project_frame("role:焦三", 1)
    assert any("治眼" in x["value"] for x in jiaosan), "焦三知道自己的动机"


def test_read_tool_find_leaks(store):
    luanshi_leak_world(store)
    M.set_store(store)
    leaks = M.s3_find_leaks("皂衣道士冷笑:够你给老娘治眼了。", "role:老道", 1)
    assert any(l["fact_id"] == "fact:治眼" for l in leaks)


def test_emotion_palette_list_and_query():
    names = M.s3_emotion_palette("")
    assert isinstance(names, list) and "压抑的悲伤" in names
    one = M.s3_emotion_palette("压抑的悲伤")
    assert one["body"] and one["inner"]


def test_craft_rule_gated_in_write_set():
    assert "s3_craft_rule_add" in M.WRITE_GATED
    assert "s3_craft_rule_remove" in M.WRITE_GATED
    assert "s3_craft_rule_list" not in M.WRITE_GATED
    assert "s3_emotion_palette" not in M.WRITE_GATED


def test_qc_chapter_uses_themed_purple(store):
    """s3_qc_chapter 把本书 craft_rule 的题材升华正则喂给 find_purple_prose。"""
    store.seed_craft_rules()
    store.save_chapter(1, "炉火映脸,天地为炉,万物为铜。")
    M.set_store(store)
    flags = M.s3_qc_chapter(1)
    assert flags["purple"], "题材升华句(天地为炉)应被本书正则抓到"


def test_ingest_not_gated():
    """ingest 是客观回写(反映已定稿正文),不再 elicitation 待批;创作虚构仍 gated。"""
    assert "s3_ingest_chapter" not in M.WRITE_GATED
    assert "s3_add_fact" in M.WRITE_GATED
    assert "s3_add_event" in M.WRITE_GATED


def test_ingest_chapter_sync_reuses_ingest_chapter(store, monkeypatch):
    """s3_ingest_chapter 改 sync,复用 ingest.ingest_chapter,直接落库(无 elicitation)。"""
    store.save_chapter(1, "甲把刀给了乙,丙在旁看着。")
    M.set_store(store)
    import scribe3.ingest as ING
    monkeypatch.setattr(ING, "parse_knowledge_delta",
                        lambda r: {"learned": [{"who": "乙", "fact": "得了刀"}], "did": []})
    monkeypatch.setattr("scribe3.llm.hermes_complete", lambda *a, **k: "{}")
    res = M.s3_ingest_chapter(1)
    assert res["applied"] == 1


def test_tools_discoverable_and_annotated():
    tools = {t.name: t for t in asyncio.run(M.mcp.list_tools())}
    want = EXPECTED_WRITE_GATED | EXPECTED_WRITE_UNGATED | EXPECTED_WRITE_UNGATED_WORLD | EXPECTED_READ
    assert want <= set(tools), f"缺工具: {want - set(tools)}"
    for name in EXPECTED_READ:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is True, f"{name} 应注 readOnlyHint=True"
    for name in EXPECTED_WRITE_GATED | EXPECTED_WRITE_UNGATED | EXPECTED_WRITE_UNGATED_WORLD:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is not True, f"{name} 不应注 readOnlyHint=True"

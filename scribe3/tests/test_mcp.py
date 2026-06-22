"""S2 · scribe3 MCP server TDD(standalone,不碰 Hermes config)。

读工具放行;写工具经 elicitation 待批,批准后才走 store 单点落库。
工具名带 s3_ 前缀(与 scribe2 隔离,防同挂撞名)。
elicitation 本身是生产侧(ctx.elicit);可测核心 = commit_if_approved 门控逻辑。
"""
import asyncio

import scribe3.mcp as M
from scribe3.scenario import luanshi_leak_world

EXPECTED_WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
                        "s3_plant_promise", "s3_advance_promise"}
EXPECTED_WRITE_UNGATED = {"s3_save_chapter"}   # manuscript 草稿,非世界状态,不待批
EXPECTED_READ = {"s3_project_frame", "s3_render_scene", "s3_find_leaks", "s3_causal_complete",
                 "s3_dramatic_irony", "s3_semantic_recall", "s3_get_chapter", "s3_qc_chapter",
                 "s3_list_promises"}


def test_write_gated_set_no_drift():
    assert M.WRITE_GATED == EXPECTED_WRITE_GATED


def test_requires_approval():
    for w in EXPECTED_WRITE_GATED:
        assert M.requires_approval(w) is True, f"{w} 应需批准"
    for r in EXPECTED_READ | EXPECTED_WRITE_UNGATED:
        assert M.requires_approval(r) is False, f"{r} 应放行(读或草稿)"


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


def test_tools_discoverable_and_annotated():
    tools = {t.name: t for t in asyncio.run(M.mcp.list_tools())}
    want = EXPECTED_WRITE_GATED | EXPECTED_WRITE_UNGATED | EXPECTED_READ
    assert want <= set(tools), f"缺工具: {want - set(tools)}"
    for name in EXPECTED_READ:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is True, f"{name} 应注 readOnlyHint=True"
    for name in EXPECTED_WRITE_GATED | EXPECTED_WRITE_UNGATED:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is not True, f"{name} 不应注 readOnlyHint=True"

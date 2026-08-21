"""P1 定案B:通用写作技法渐进披露——索引进带工具 instructions + s3_skill_read 取全文。
零降级:未知 slug 抛错带清单;无工具路径绝不注入索引(说了工具却调不到=对模型说谎)。"""
import pytest

from scribe3.craft_skills import list_skills, read_skill, skills_index_block


def test_list_skills_has_four_with_desc():
    rows = list_skills()
    slugs = {r["slug"] for r in rows}
    assert {"限知视角", "对话潜台词", "场景转换", "节奏控制"} <= slugs
    assert all(r["desc"] for r in rows), "每篇技法必须有一句话描述(索引行)"


def test_read_skill_roundtrip_and_unknown_raises():
    body = read_skill("限知视角")
    assert "焦点角色" in body and len(body) > 300
    with pytest.raises(ValueError) as e:
        read_skill("不存在的技法")
    assert "可用" in str(e.value)
    for bad in ("../etc/passwd", "a/b", ""):
        with pytest.raises(ValueError):
            read_skill(bad)


def test_index_block_lists_all_and_mentions_tool():
    blk = skills_index_block()
    assert "s3_skill_read" in blk
    for r in list_skills():
        assert r["slug"] in blk


def test_mcp_tool_reads_skill():
    from scribe3.mcp import s3_skill_read
    fn = getattr(s3_skill_read, "fn", s3_skill_read)   # FastMCP 包装兼容
    out = fn(slug="对话潜台词") if callable(fn) else None
    assert out and "潜台词" in out


def test_agentic_instructions_do_not_carry_skills_index(store, monkeypatch):
    """讨论查阅不教 s3_skill_read（闭集外）。写作路径仍可带索引。"""
    import scribe3.app as A
    from .test_app import _client
    captured = {}
    def fake(message, instructions, **kw):
        captured["ins"] = instructions
        yield {"type": "response.completed", "response": {"id": "r"}}
    monkeypatch.setattr(A, "_responses_events", fake)
    r = _client(store).get("/chat/agentic-stream", params={"msg": "hi", "work": "main"})
    b"".join(r.iter_bytes())
    assert "s3_skill_read" not in (captured.get("ins") or "")
    assert "写作技法库" not in (captured.get("ins") or "")


def test_write_instructions_index_only_with_tools(store):
    """写作组装:with_tools=True 含索引;False 绝不含(无工具不说谎)。"""
    import scribe3.app as A
    A.set_store(store)
    ins_t = A._assemble_write_instructions(store, chapter=1, focalizer="", phase="",
                                           seed_words=[], short_mode=False,
                                           with_tools=True, work="main")
    ins_f = A._assemble_write_instructions(store, chapter=1, focalizer="", phase="",
                                           seed_words=[], short_mode=False,
                                           with_tools=False, work="main")
    assert "写作技法库" in ins_t
    assert "写作技法库" not in ins_f and "s3_skill_read" not in ins_f

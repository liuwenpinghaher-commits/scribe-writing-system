"""P3:跨书作者偏好(USER.md)——注入唯一路径 + 待批写 + 红线(偏好≠正典)。"""
import pytest

from scribe3.author_prefs import append_pref, author_prefs_block


@pytest.fixture()
def hermes_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    return tmp_path


def test_block_empty_when_file_missing(hermes_home):
    """文件不存在=合法初始态(空块),不是静默失败。"""
    assert author_prefs_block() == ""


def test_append_and_inject_roundtrip(hermes_home):
    append_pref("偏短句,少用逗号堆叠")
    append_pref("不煽情:情绪进动作与器物,不直说")
    blk = author_prefs_block()
    assert "偏短句" in blk and "不煽情" in blk
    assert "偏好≠正典" in blk   # 冲突时本书设定优先的声明必须随块注入
    content = (hermes_home / "USER.md").read_text(encoding="utf-8")
    assert "scribe3 写作偏好" in content and content.count("- ") == 2


def test_append_guards(hermes_home):
    with pytest.raises(ValueError):
        append_pref("   ")
    with pytest.raises(ValueError):
        append_pref("长" * 201)


def test_block_caps_and_editor_system_injection(hermes_home, store):
    """注入单点:_editor_system(讨论/agentic/写作全路径复用)携带偏好块。"""
    import scribe3.app as A
    A.set_store(store)
    append_pref("叙事距离偏远,少贴脸描写")
    sysmsg = A._editor_system(store)
    assert "作者跨书偏好" in sysmsg and "叙事距离偏远" in sysmsg


def test_mcp_pref_tool_is_write_gated():
    """s3_author_pref_add 必须是写注解(readOnlyHint=False)——待批门的前提。"""
    from scribe3 import mcp as M
    tool = M.s3_author_pref_add
    ann = getattr(tool, "annotations", None)
    if ann is None and hasattr(tool, "_tool"):
        ann = tool._tool.annotations
    # FastMCP 包装差异兜底:至少函数在 write server 白名单里(provision 交叉校验兜真)
    if ann is not None:
        assert ann.readOnlyHint is False
    assert "s3_author_pref_add" in M.WRITE_GATED
    assert M.requires_approval("s3_author_pref_add") is True


def test_s3_author_pref_add_decline_blocks_write():
    """accepted=False 时 do_write 零调用(fail-closed,不落 USER.md)。"""
    from scribe3 import mcp as M
    calls: list[str] = []
    out = M.commit_if_approved(
        "s3_author_pref_add", False, lambda: calls.append("did") or "x")
    assert calls == [], "拒绝→不执行 do_write"
    assert out["status"] == "declined"
    assert out.get("tool") == "s3_author_pref_add"

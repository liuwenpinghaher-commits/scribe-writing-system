"""限知门覆盖：MCP reveal 路径 + chief/author 视角 + 空 focalizer。"""
import inspect

from scribe3.epistemic import visible_to


class _FakeStore:
    def facts_at(self, chapter):
        return [
            {"id": "f1", "secret": False, "value": "公开"},
            {"id": "f2", "secret": True, "value": "密事"},
        ]


def test_chief_author_never_sees_secret():
    st = _FakeStore()
    for viewer in ("chief", "author", "主编", "", None):
        ids = visible_to(st, "book", 5, viewer)
        assert "f1" in ids
        assert "f2" not in ids, f"viewer={viewer!r} 不应看到 secret"


def test_role_viewer_delegates_to_frame():
    """角色视角走 knowledge.project_frame——此处 mock 确认委托链。"""
    called = {}

    def fake_frame(store, who, n):
        called["who"] = who
        return ["f1"]

    import scribe3.knowledge
    orig = getattr(scribe3.knowledge, "project_frame", None)
    scribe3.knowledge.project_frame = fake_frame
    try:
        ids = visible_to(_FakeStore(), "book", 5, "role:灰狸")
        assert ids == ["f1"]
        assert called["who"] == "role:灰狸"
    finally:
        if orig:
            scribe3.knowledge.project_frame = orig


def test_mcp_recall_default_masks_secret():
    """s3_hybrid_recall 默认打码，明文只走孪生 _reveal 工具。"""
    from scribe3.mcp import tools as M
    src = inspect.getsource(M.s3_hybrid_recall)
    assert "reveal_secret" not in src or "False" in src, \
        "s3_hybrid_recall 必须默认 reveal_secret=False"
    reveal_src = inspect.getsource(M.s3_hybrid_recall_reveal)
    assert "True" in reveal_src

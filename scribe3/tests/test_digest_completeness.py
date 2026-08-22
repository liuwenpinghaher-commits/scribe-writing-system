"""摘要生成：codex_digest 全种类覆盖 + post_analysis 非空守卫。"""
from scribe3.codex_digest import _KIND_GROUPS, _KEY_FIELDS, digest_payloads, DIGEST_ATTRIBUTE

_ALL_KINDS = {"character", "faction", "place", "item"}


def test_kind_groups_covers_all_entity_kinds():
    assert set(_KIND_GROUPS.keys()) == _ALL_KINDS


def test_key_fields_covers_all_entity_kinds():
    assert set(_KEY_FIELDS.keys()) == _ALL_KINDS


def test_make_digest_never_empty_for_valid_entity():
    for kind in _ALL_KINDS:
        row = {"name": f"测试{kind}"}
        out = digest_payloads(kind, f"test:{kind}", row)
        assert out, f"{kind} 有 name 时 digest 不应为空"
        assert all(p["attribute"] == DIGEST_ATTRIBUTE for p in out)


def test_post_analysis_summary_not_corrupt():
    """章后分析摘要对空章返回 present=False 而非异常。"""
    from scribe3.store.chapters import ChaptersMixin

    class _Dummy:
        def _query(self, *a, **k):
            return []

    result = ChaptersMixin.post_analysis_summary(_Dummy(), 999)
    assert result is None or result.get("present") is False

"""CAS 走唯一写点 + 缓存失效 + NONE 章报库态。不启 Surreal。"""
from __future__ import annotations

from scribe3.store.chapters import ChaptersMixin
from scribe3.store.connection import ConnectionMixin


class _CasStore(ChaptersMixin):
    db_name = "book_cas"

    def __init__(self, write_rows=None, chapter=None):
        self.write_rows = list(write_rows or [])
        self.writes = []
        self.chapter = chapter
        self.invalidations = []

    def _execute_write(self, sql, vars):
        self.writes.append(sql)
        return list(self.write_rows)

    def _rows_from_write(self, raw):
        return ConnectionMixin._rows_from_write(raw)

    def get_chapter(self, seq):
        if self.chapter is None:
            return None
        return dict(self.chapter)


def test_cas_refreeze_chapter_uses_execute_write_and_invalidates(monkeypatch):
    from scribe3.store import chapters as chmod

    hits = []

    def _emit(table, work, store=None):
        hits.append((table, work))

    monkeypatch.setattr(chmod, "_emit_cache_invalidation", _emit)
    st = _CasStore(
        write_rows=[{"seq": 1, "outline_status": "frozen", "outline_rev": 2}],
        chapter={"seq": 1, "outline_status": "stale", "outline_rev": 1},
    )
    out = st.cas_refreeze_chapter(1)
    assert out["ok"] is True
    assert out["idempotent"] is False
    assert out["outline_rev"] == 2
    assert st.writes and "UPDATE" in st.writes[0]
    assert "WHERE outline_status" in st.writes[0]
    assert hits == [("chapter", "book_cas")]


def test_cas_refreeze_chapter_missing():
    st = _CasStore(write_rows=[], chapter=None)
    out = st.cas_refreeze_chapter(9)
    assert out["ok"] is False
    assert out["code"] == "chapter_missing"


def test_cas_refreeze_none_status_absent():
    st = _CasStore(write_rows=[], chapter={"seq": 1, "outline_status": None, "outline_rev": 0})
    out = st.cas_refreeze_chapter(1)
    assert out["ok"] is True
    assert out["status_absent"] is True
    assert out["idempotent"] is True


def test_cas_refreeze_volume_invalidates(monkeypatch):
    from scribe3.store import chapters as chmod

    hits = []
    monkeypatch.setattr(chmod, "_emit_cache_invalidation", lambda *a, **k: hits.append(a))
    st = _CasStore(write_rows=[
        {"seq": 1, "outline_status": "frozen", "outline_rev": 1},
        {"seq": 2, "outline_status": "frozen", "outline_rev": 3},
    ])
    out = st.cas_refreeze_volume("vol-1")
    assert out["n"] == 2
    assert out["seqs"] == [1, 2]
    assert hits
    assert all("UPDATE" in w for w in st.writes)


def test_cas_source_has_no_query_write():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "store" / "chapters.py").read_text(encoding="utf-8")
    start = src.index("def cas_refreeze_chapter")
    end = src.index("def delete_volume")
    block = src[start:end]
    assert "self._execute_write(" in block
    assert "self._query(" not in block
    assert "_emit_cache_invalidation" in block


def test_update_volume_single_write_returns_before(monkeypatch):
    marks = []
    monkeypatch.setattr(
        "scribe3.outline_status.mark_volume_intro_changed",
        lambda st, vid: marks.append(vid),
    )
    monkeypatch.setattr("scribe3.outline_status.intro_text_changed", lambda a, b: a != b)

    class _VolStore(_CasStore):
        def _query(self, sql, vars=None):
            return [{"id": "volume:v1"}]

    st = _VolStore(write_rows=[{"intro": "旧纲"}])
    ok = st.update_volume("v1", {"intro": "新纲"})
    assert ok is True
    assert any("RETURN BEFORE intro" in w for w in st.writes)
    assert marks == ["v1"]

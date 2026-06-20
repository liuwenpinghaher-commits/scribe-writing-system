from scribe2.store import Store
from scribe2.schema import EMBED_DIM

def test_schema_defines_vector_and_fts(db):
    s = Store(db); s.init_schema()
    info = str(s.db.query("INFO FOR TABLE chapter;"))
    assert "HNSW" in info.upper()
    assert ("SEARCH" in info.upper()) or ("ANALYZER" in info.upper()) or ("FULLTEXT" in info.upper())

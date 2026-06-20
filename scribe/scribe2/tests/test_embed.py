from scribe2.store import Store
from scribe2.embed import dim
from scribe2.schema import EMBED_DIM

def test_embed_dim_matches_schema():
    assert dim() == EMBED_DIM

def test_put_content_stores_embedding(db):
    s = Store(db); s.init_schema()
    cid = s.put_content("setting", work="work:1", name="断魂剑",
                        text="一把会低语的古剑,持有者会逐渐失去记忆。")
    row = s.get("setting", cid)
    assert row["text"].startswith("一把会低语")
    assert isinstance(row["embedding"], list) and len(row["embedding"]) == EMBED_DIM

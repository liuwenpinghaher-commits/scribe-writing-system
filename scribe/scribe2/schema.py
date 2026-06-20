EMBED_DIM = 384  # fastembed multilingual-e5-small 维度(Task 3 probe 实测;不符改这里)

# 需"可被语义检索"的内容实体:都带 text(FTS)+ embedding(向量)
CONTENT_TABLES = ["chapter", "setting", "character", "foreshadow",
                  "material", "memory_entry", "style_exemplar", "imagination"]
# 纯结构表(无需向量)
STRUCT_TABLES = ["work", "volume", "snapshot", "segment", "author_intent",
                 "option_set", "consistency_flag", "quality_snapshot",
                 "preference_signal", "taste_model", "feedback"]


def ddl() -> list[str]:
    out = ["DEFINE ANALYZER scribe_a TOKENIZERS blank,class FILTERS lowercase;"]
    for t in STRUCT_TABLES + CONTENT_TABLES:
        out.append(f"DEFINE TABLE {t} SCHEMALESS;")
    for t in CONTENT_TABLES:
        out.append(
            f"DEFINE INDEX {t}_vec ON {t} FIELDS embedding "
            f"HNSW DIMENSION {EMBED_DIM} DIST COSINE TYPE F32;")
        out.append(
            f"DEFINE INDEX {t}_fts ON {t} FIELDS text "
            f"FULLTEXT ANALYZER scribe_a BM25;")
    return out

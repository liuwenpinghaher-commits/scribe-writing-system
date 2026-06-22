EMBED_DIM = 512  # BAAI/bge-small-zh-v1.5 维度(中文优化)

# 需"可被语义检索"的内容实体:都带 text(FTS)+ embedding(向量)
CONTENT_TABLES = ["chapter", "setting", "character", "foreshadow",
                  "material", "memory_entry", "style_exemplar", "imagination",
                  "motif"]  # Codex 2.0:核心意象/母题(隐喻网,可语义检索)
# 纯结构表(无需向量)
STRUCT_TABLES = ["work", "volume", "snapshot", "segment", "author_intent",
                 "option_set", "consistency_flag", "quality_snapshot",
                 "preference_signal", "taste_model", "feedback",
                 # 写作面完整化新增
                 "insight", "thread", "entity_relation", "char_state",
                 "agent_memory", "agent_skill", "timeline_event", "pending_write",
                 "chapter_task", "entity_beat",  # 统一线模型:通用实体逐章节点
                 "knowledge_ledger",  # 知识边界:每章各角色新知/所为 delta(单一真相源)
                 # 划词交互:批注/旁注 + 高亮标记(锚在选中文字 quote 上)
                 "annotation", "highlight"]


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

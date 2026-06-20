"""Task 1-3: 关系丰富化链 数据增强测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.memory import parse_ingest  # noqa: E402


def _cols(db, table):
    return {r["name"] for r in db.conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_schema_relation_columns_and_quality_table():
    db = Database(":memory:")
    cols = _cols(db, "entity_relations")
    assert {"src_type", "dst_type", "relation_category", "weight", "directed"} <= cols
    # quality_snapshots 表存在且有关键列
    qcols = _cols(db, "quality_snapshots")
    assert {"work_id", "scope", "chapter_seq", "slop_density", "created_at"} <= qcols


def test_add_relation_typed_and_dedup():
    db = Database(":memory:")
    w = db.create_work("u", "书")
    db.add_relation(w, "沈舟", "断魂剑", "持有", valid_from=1,
                    src_type="角色", dst_type="物品", category="从属", weight=1.0)
    # 同 (src,dst,relation) 再来一次 → 累加 weight,不新增行
    db.add_relation(w, "沈舟", "断魂剑", "持有", valid_from=2,
                    src_type="角色", dst_type="物品", category="从属")
    rels = db.list_relations(w)
    assert len(rels) == 1
    r = rels[0]
    assert r["src_type"] == "角色" and r["dst_type"] == "物品"
    assert r["relation_category"] == "从属"
    assert r["weight"] == 2.0


def test_parse_ingest_typed_relations_with_defaults():
    # 含新字段
    full = '{"summary":"s","relations":[{"src":"沈舟","dst":"断魂剑","relation":"持有",' \
           '"src_type":"角色","dst_type":"物品","category":"从属","directed":1}]}'
    r = parse_ingest(full)["relations"][0]
    assert r["src_type"] == "角色" and r["category"] == "从属"
    # 缺新字段 → 补默认,不丢条
    bare = '{"relations":[{"src":"A","dst":"B","relation":"敌对"}]}'
    r2 = parse_ingest(bare)["relations"][0]
    assert r2["src_type"] == "未知" and r2["category"] == "其它" and r2["directed"] == 1


if __name__ == "__main__":
    test_schema_relation_columns_and_quality_table()
    test_add_relation_typed_and_dedup()
    test_parse_ingest_typed_relations_with_defaults()
    print("  ✓ data-enhance(纯 db/解析)通过")

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


def test_chinese_quality_metrics():
    from scribe_mcp.metrics import vocab_richness, repetition_rate
    # 全不同词 → 丰富度高、重复低
    rich = "晨光 落在 窗台 猫咪 伸懒腰 茶香 漫开"
    assert vocab_richness(rich) > 0.8
    # 大量重复 → 丰富度低、重复率高
    rep = "走 走 走 走 走 走 走 走"
    assert vocab_richness(rep) < 0.3
    assert repetition_rate(rep) > 0.5


def test_quality_snapshot_add_list():
    db = Database(":memory:")
    w = db.create_work("u", "书")
    db.add_quality_snapshot(w, "global", None, {"words": 1200, "slop_density": 0.8,
        "consistency_score": 0.9, "foreshadow_payoff": 0.5, "vocab_richness": 0.7,
        "repetition_rate": 0.1, "cost_usd": 0.02})
    db.add_quality_snapshot(w, "chapter", 1, {"words": 600, "slop_density": 1.2})
    g = db.list_quality_snapshots(w, "global")
    assert len(g) == 1 and g[0]["words"] == 1200
    c = db.list_quality_snapshots(w, "chapter")
    assert len(c) == 1 and c[0]["chapter_seq"] == 1


# ---- Task 6: GET /quality/history + ingest 落快照 ----

def test_quality_history_endpoint(monkeypatch):
    import scribe_mcp.api as api
    from fastapi.testclient import TestClient
    client = TestClient(api.app); U = {"X-Owner-Id": "u1"}
    w = client.post("/works", json={"title": "趋势书"}, headers=U).json()["work_id"]
    # 直接落两笔 global 快照(模拟多次修订)
    api.db.add_quality_snapshot(w, "global", None, {"words": 500, "slop_density": 1.5})
    api.db.add_quality_snapshot(w, "global", None, {"words": 1200, "slop_density": 0.9})
    hist = client.get(f"/works/{w}/quality/history?scope=global", headers=U).json()
    assert len(hist) == 2 and hist[0]["words"] == 500 and hist[1]["words"] == 1200


# ---- Task 7: POST /analyze 批量分析(幂等) ----

def test_analyze_idempotent(monkeypatch):
    import scribe_mcp.api as api
    from fastapi.testclient import TestClient
    client = TestClient(api.app); U = {"X-Owner-Id": "u1"}
    w = client.post("/works", json={"title": "分析书"}, headers=U).json()["work_id"]
    client.put(f"/works/{w}/chapters", json={"seq": 1, "title": "一"}, headers=U)
    client.post(f"/works/{w}/chapters/1/prose", json={"content": "沈舟握紧断魂剑。", "lock": True}, headers=U)
    fake = '{"summary":"沈舟登场","relations":[{"src":"沈舟","dst":"断魂剑","relation":"持有",' \
           '"src_type":"角色","dst_type":"物品","category":"从属"}],"timeline":[],"char_states":[]}'
    monkeypatch.setattr(api, "_volc_complete", lambda *a, **k: fake)
    r1 = client.post(f"/works/{w}/analyze", headers=U).json()
    assert r1["analyzed"] >= 1
    r2 = client.post(f"/works/{w}/analyze", headers=U).json()  # 重跑
    # 幂等:关系不翻倍(去重累加 weight,行数仍 1)
    rels = client.get(f"/works/{w}/relations", headers=U).json()
    assert len(rels) == 1


if __name__ == "__main__":
    test_schema_relation_columns_and_quality_table()
    test_add_relation_typed_and_dedup()
    test_parse_ingest_typed_relations_with_defaults()
    test_chinese_quality_metrics()
    test_quality_snapshot_add_list()
    print("  ✓ data-enhance(纯 db/解析)通过")

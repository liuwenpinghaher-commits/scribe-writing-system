"""Phase1 存储层:material 记忆化(三模态字段/索引/溯源/联想边/强度/backfill)。

用 store fixture(真机内存 SurrealDB)。embedding 走本地 fastembed(非 LLM 网关,不烧钱)。
"""


def test_migration_fields_and_indexes(store):
    """migration 070:新字段存在 + material_reference 表可用。"""
    mid = store.add_material("标题", "正文", "note")
    row = store.get_material(mid)
    for f in ("ref_tags", "pinned", "archived", "recall_count", "tokens"):
        assert f in row, f"缺字段 {f}"
    assert row["pinned"] is False and row["recall_count"] == 0


def test_crud_writes_tokens_and_embedding(store):
    """add_material 写入时 jieba 切 tokens + 生成 embedding + ref_tags。"""
    mid = store.add_material("血玉铜炉", "散发寒气的密室", "snippet",
                             tags=["恐怖"], ref_tags=["风格"])
    row = store.get_material(mid)
    assert row["tokens"] and "密室" in row["tokens"]
    assert row["ref_tags"] == ["风格"]
    emb = store._material_embedding(mid)
    assert emb and len(emb) == 512


def test_reference_and_strength(store):
    """溯源双向查 + recall_count 递增 + last_recalled_at。"""
    mid = store.add_material("t", "b", "note")
    store.add_material_reference(mid, 3, "手法", "冷硬白描适合刑讯", "brief")
    assert store.get_material(mid)["recall_count"] == 1
    assert [r["chapter"] for r in store.material_refs_by_material(mid)] == [3]
    assert [r["material_id"] for r in store.material_refs_by_chapter(3)] == [mid]


def test_relates_topk_and_about(store):
    """联想边:relates top-k 上限(建 8 条相似素材,只保 top-3)。"""
    ids = [store.add_material(f"密室机关{i}", "寒气逼人的暗器", "snippet") for i in range(8)]
    store.build_material_edges(ids[0], top_k=3, threshold=-1.0)  # 低阈值确保建边
    edges = store.material_relates(ids[0])
    assert len(edges) <= 3, f"top-k 上限应 ≤3,实得 {len(edges)}"


def test_backfill_idempotent(store):
    """backfill:旧素材(无 tokens/embedding)补齐,重跑幂等。"""
    store._execute_write("CREATE material CONTENT $c",
                         {"c": {"title": "旧素材", "body": "密室寒气", "kind": "note",
                                "tags": [], "source": None}})
    from scribe3.store import backfill_material_memory
    n1 = backfill_material_memory(store)
    assert n1 >= 1, "应补齐至少 1 条旧素材"
    n2 = backfill_material_memory(store)
    assert n2 == 0, "已补齐,重跑应幂等(0 条)"

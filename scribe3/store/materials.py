"""SurrealStore mixin: materials."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class MaterialsMixin:

    def add_material(self, title: str, body: str | None = None, kind: str = "note",
                     tags: list[str] | None = None, source: str | None = None,
                     ref_tags: list[str] | None = None) -> str:
        """新建素材(记忆化:jieba 切 tokens + 生成 embedding),返回裸 id。"""
        if kind not in MATERIAL_KINDS:
            raise ValueError(f"非法素材分类 kind='{kind}'(合法: {list(MATERIAL_KINDS)})")
        toks, vec = self._material_index_fields(title, body)
        rows = self._query(
            "CREATE material CONTENT $c",
            {"c": {"title": title, "body": body, "kind": kind,
                   "tags": list(tags or []), "source": source,
                   "ref_tags": list(ref_tags or []), "tokens": toks, "embedding": vec}})
        rid = (rows[0] if rows else {}).get("id")
        if rid is None:
            raise RuntimeError("add_material: CREATE 未返回 id")
        return str(rid).split(":")[-1] if ":" in str(rid) else str(rid)

    def list_materials(self, kind: str | None = None, archived: bool | None = False) -> list[dict]:
        """素材列表(可选 kind 过滤),按 updated_at DESC。"""
        filters = []
        vars = {}
        if kind is not None:
            filters.append("kind=$k")
            vars["k"] = kind
        if archived is True:
            filters.append("archived = true")
        elif archived is False:
            filters.append("(archived = NONE OR archived != true)")
        where = f" WHERE {' AND '.join(filters)}" if filters else ""
        return self._query(
            f"SELECT {self._MATERIAL_COLS} FROM material{where} ORDER BY updated_at DESC",
            vars)

    def get_material(self, material_id: str) -> dict | None:
        rows = self._query(
            f"SELECT {self._MATERIAL_COLS} FROM type::record('material',$m) LIMIT 1",
            {"m": material_id})
        return rows[0] if rows else None

    def _material_exists(self, material_id: str) -> bool:
        # 不走 exists()(其 _split 只认 ONT2TBL 本体前缀),直接按表查
        rows = self._query("SELECT id FROM type::record('material',$m) LIMIT 1",
                           {"m": material_id})
        return bool(rows)

    def update_material(self, material_id: str, fields: dict) -> bool:
        """局部更新;title/body 变则重算 tokens+embedding。返回是否存在。"""
        if fields.get("kind") is not None and fields["kind"] not in MATERIAL_KINDS:
            raise ValueError(f"非法素材分类 kind='{fields['kind']}'(合法: {list(MATERIAL_KINDS)})")
        if not self._material_exists(material_id):
            return False
        if "title" in fields or "body" in fields:
            cur = self.get_material(material_id) or {}
            toks, vec = self._material_index_fields(
                fields.get("title", cur.get("title")), fields.get("body", cur.get("body")))
            fields = {**fields, "tokens": toks, "embedding": vec}
        self._update_by("material", material_id, fields)
        # Task 16-B:素材 archive/pin(及正文改动)发表级失效,清检索缓存里的素材召回。
        if "archived" in fields or "pinned" in fields or "title" in fields or "body" in fields:
            _emit_cache_invalidation("material", self.db_name)
        return True

    def material_lifecycle_impact(self, material_id: str) -> dict | None:
        row = self.get_material(material_id)
        if not row:
            return None
        counts = {
            "material_reference": len(self.material_refs_by_material(material_id)),
        }
        try:
            rid = RecordID("material", material_id)
            counts["graph"] = len(self._query(
                "SELECT id FROM relates WHERE in=$rid OR out=$rid", {"rid": rid}))
        except Exception:
            counts["graph"] = 0
        if row.get("embedding"):
            counts["semantic_index"] = 1
        if row.get("about_entities"):
            counts["about_entities"] = len(row.get("about_entities") or [])
        return {"object": {"id": material_id, "label": row.get("title") or material_id}, "counts": counts}

    def _cleanup_material_refs(self, material_id: str) -> None:
        rid = RecordID("material", material_id)
        self._execute_write("DELETE material_reference WHERE material_id=$m", {"m": material_id})
        try:
            self._execute_write("DELETE relates WHERE in=$rid OR out=$rid", {"rid": rid})
        except Exception:
            pass

    def delete_material(self, material_id: str, cleanup_refs: bool = False) -> bool:
        """删除素材;返回 True 若存在并删除,False 若不存在。"""
        if not self._material_exists(material_id):
            return False
        if cleanup_refs:
            self._cleanup_material_refs(material_id)
        self._delete_by("material", material_id)
        return True

    @staticmethod
    def _material_index_fields(title, body):
        """jieba 切词 + embedding(add/update/backfill 共用,DRY)。"""
        import jieba
        from scribe3.embed import embed
        text = f"{title or ''}\n{body or ''}"
        toks = " ".join(w for w in jieba.cut(text) if w.strip())
        return toks, embed([text])[0]

    def _material_embedding(self, material_id: str):
        rows = self._query(
            "SELECT embedding FROM type::record('material',$m) LIMIT 1", {"m": material_id})
        return (rows[0].get("embedding") if rows else None)

    def add_material_reference(self, material_id, chapter, dimension=None,
                               reason=None, via="manual") -> None:
        """记一次参考(溯源)+ 强化(recall_count++/last_recalled_at)。"""
        self._execute_write(
            "CREATE material_reference SET material_id=$m, chapter=$c, "
            "dimension=$d, reason=$r, via=$v",
            {"m": material_id, "c": int(chapter), "d": dimension, "r": reason, "v": via})
        self._execute_write(
            "UPDATE type::record('material',$m) SET recall_count += 1, "
            "last_recalled_at = time::now()", {"m": material_id})

    def material_refs_by_material(self, material_id) -> list[dict]:
        return self._query(
            "SELECT material_id, chapter, dimension, reason, via FROM material_reference "
            "WHERE material_id=$m ORDER BY chapter", {"m": material_id})

    def build_material_edges(self, material_id, top_k: int = 5, threshold: float = 0.3) -> None:
        """建联想边:relates(语义近邻 top-k,图 RELATE)+ about_entities(提及实体,数组)。
        threshold=相似度下限(1-距离),低于则不建 relates 边。防爆炸:只保 top-k。"""
        emb = self._material_embedding(material_id)
        if not emb:
            return
        rows = self._query(
            f"SELECT meta::id(id) AS id, vector::distance::knn() AS dist FROM material "
            f"WHERE embedding <|{top_k + 1},{max(40, top_k + 1)}|> $qv "
            f"AND meta::id(id) != $self ORDER BY dist LIMIT {top_k}",
            {"qv": emb, "self": material_id})
        for r in rows:
            sim = 1.0 - float(r.get("dist") or 0.0)
            if sim < threshold:
                continue
            self._execute_write(
                "RELATE (type::record('material',$a))->relates->(type::record('material',$b)) "
                "SET weight=$w, reason=$reason",
                {"a": material_id, "b": r["id"], "w": sim, "reason": "语义近邻"})
        try:  # about_entities:素材提及的实体 id(图召回按实体关联),富集失败不阻塞
            from scribe3.brief import detect_mentions
            ents = [{"id": e.id, "name": e.name,
                     "aliases": (getattr(e, "traits", None) or {}).get("aliases") or []}
                    for e in self.all_entities()]
            row = self.get_material(material_id) or {}
            mentioned = list(detect_mentions(f"{row.get('title', '')} {row.get('body') or ''}", ents))
            if mentioned:
                self._execute_write("UPDATE type::record('material',$m) SET about_entities=$e",
                                    {"m": material_id, "e": mentioned})
        except Exception:
            pass

    def material_relates(self, material_id) -> list[dict]:
        """查素材的 relates 联想邻居(表未建/无边→空,首次召回空库时鲁棒)。"""
        try:
            return self._query(
                "SELECT meta::id(out) AS id, weight, reason FROM relates "
                "WHERE in = type::record('material',$m)", {"m": material_id})
        except Exception:
            return []

    def material_graph(self, focus: str | None = None, limit: int = 200, hop: int = 1) -> dict:
        """素材记忆网络:节点(素材)+ relates 联想边,供前端 sigma 可视化。"""
        all_nodes = [{"id": m["id"], "title": m.get("title"), "kind": m.get("kind"),
                  "recall_count": m.get("recall_count") or 0, "pinned": bool(m.get("pinned")),
                  "ref_tags": m.get("ref_tags") or []}
                 for m in self.list_materials()]
        truncated = len(all_nodes) > limit
        nodes = all_nodes[:limit]
        keep = {n["id"] for n in nodes}
        edges = []
        degraded_sources = []
        try:
            rows = self._query(
                "SELECT meta::id(in) AS src, meta::id(out) AS dst, weight FROM relates")
            edges = [{"src": r["src"], "dst": r["dst"], "weight": r.get("weight") or 1.0}
                     for r in (rows or []) if r.get("src") in keep and r.get("dst") in keep]
        except Exception as e:
            edges = []
            degraded_sources.append({"source": "relates", "reason": str(e)})
        return {
            "nodes": nodes,
            "edges": edges,
            "edges_degraded": bool(degraded_sources),
            "degraded_sources": degraded_sources,
            "truncated": truncated,
        }

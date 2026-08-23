"""SurrealStore mixin: materials."""
from __future__ import annotations

import logging
import time
from typing import Any

from scribe3.store.core_preamble import *  # noqa: F403

_log = logging.getLogger("scribe3")


def rank_materials_hybrid(
    query: str,
    items: list[dict],
    vec_scores: dict[str, float] | None = None,
) -> list[dict]:
    """字面命中 + 向量分加权。vec_scores 为 id→相似度(0~1)。"""
    q = (query or "").strip().lower()
    vec_scores = vec_scores or {}
    if not items:
        return []
    scored = []
    for m in items:
        title = str(m.get("title") or "").lower()
        blob = "\n".join([
            title, str(m.get("body") or ""), str(m.get("summary") or ""),
        ]).lower()
        score = blob.count(q) if q else 0
        if q and q in title:
            score += 3
        mid = str(m.get("id") or "")
        vs = float(vec_scores.get(mid) or 0.0)
        score += vs * 5.0
        scored.append((score, vs, m))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [m for _, _, m in scored]

# 导入 job 默认 TTL(秒):24h
_IMPORT_JOB_TTL_SEC = 24 * 3600


class MaterialsMixin:

    def add_material(self, title: str, body: str | None = None, kind: str = "note",
                     tags: list[str] | None = None, source: str | None = None,
                     ref_tags: list[str] | None = None, summary: str | None = None,
                     pinned: bool = False, origin: str = "manual") -> str:
        """新建素材(记忆化:jieba 切 tokens + 生成 embedding),返回裸 id。

        origin 仅创建时写入(manual/import/session_clip/chief);后续 update 不得改写。
        """
        if kind not in MATERIAL_KINDS:
            raise ValueError(f"非法素材分类 kind='{kind}'(合法: {list(MATERIAL_KINDS)})")
        org = (origin or "manual").strip() or "manual"
        if org not in MATERIAL_ORIGINS:
            org = "manual"
        toks, vec = self._material_index_fields(title, body)
        rows = self._query(
            "CREATE material CONTENT $c",
            {"c": {"title": title, "body": body, "kind": kind,
                   "tags": list(tags or []), "source": source,
                   "ref_tags": list(ref_tags or []),
                   "summary": (summary or "").strip() or None,
                   "pinned": bool(pinned),
                   "origin": org,
                   "tokens": toks, "embedding": vec}})
        rid = (rows[0] if rows else {}).get("id")
        if rid is None:
            raise RuntimeError("add_material: CREATE 未返回 id")
        mid = str(rid).split(":")[-1] if ":" in str(rid) else str(rid)
        if org in ("manual", "session_clip"):
            try:
                self.build_material_edges(mid)
            except Exception as e:
                logging.getLogger("scribe3").warning("build_material_edges fail %s: %s", mid, e)
        return mid

    def list_materials(self, kind: str | None = None, archived: bool | None = False) -> list[dict]:
        """素材列表(可选 kind 过滤),按 updated_at DESC。"""
        filters = []
        vars: dict[str, Any] = {}
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

    def list_materials_page(
        self,
        kind: str | None = None,
        view: str = "all",
        q: str = "",
        limit: int | None = None,
        cursor: int = 0,
        origin: str | None = None,
        mode: str = "bm25",
    ) -> dict:
        """服务端视图过滤 + 偏移分页;返回 {items, next_cursor, total}。

        view: all|pinned|referenced|untagged|archived|recent
        recent 按 created_at DESC;其余默认 updated_at DESC(recent 同 created)。
        """
        view = (view or "all").strip() or "all"
        archived_flag: bool | None
        if view == "archived":
            archived_flag = True
        else:
            archived_flag = False

        filters = []
        vars: dict[str, Any] = {}
        if kind is not None:
            filters.append("kind=$k")
            vars["k"] = kind
        if archived_flag is True:
            filters.append("archived = true")
        elif archived_flag is False:
            filters.append("(archived = NONE OR archived != true)")
        if view == "pinned":
            filters.append("pinned = true")
        if origin:
            filters.append("origin = $origin")
            vars["origin"] = origin

        where = f" WHERE {' AND '.join(filters)}" if filters else ""
        order = "ORDER BY created_at DESC" if view == "recent" else "ORDER BY updated_at DESC"
        rows = self._query(
            f"SELECT {self._MATERIAL_COLS} FROM material{where} {order}",
            vars) or []

        # 需后过滤的视图(Surreal 表达式对空数组/NONE 不统一时用 Python 保真)
        if view == "referenced":
            rows = [m for m in rows if (m.get("recall_count") or 0) > 0]
        elif view == "untagged":
            rows = [m for m in rows if not (m.get("tags") or m.get("ref_tags"))]

        needle = (q or "").strip().lower()
        if needle:
            def _blob(m):
                return "\n".join([
                    str(m.get("title") or ""), str(m.get("body") or ""),
                    str(m.get("summary") or ""),
                    " ".join(m.get("tags") or []), " ".join(m.get("ref_tags") or []),
                ]).lower()
            kw = [m for m in rows if needle in _blob(m)]
            hybrid = str(mode or "").strip().lower() == "hybrid"
            vec_scores: dict[str, float] = {}
            extra: list[dict] = []
            if hybrid:
                try:
                    vec_scores = self._material_knn_scores(q, k=max(20, len(kw) or 8))
                    by_id = {str(m.get("id") or ""): m for m in rows}
                    seen = {str(m.get("id") or "") for m in kw}
                    for mid, sim in vec_scores.items():
                        if sim >= 0.3 and mid in by_id and mid not in seen:
                            extra.append(by_id[mid])
                            seen.add(mid)
                except Exception:
                    vec_scores = {}
            merged = kw + extra
            rows = rank_materials_hybrid(q, merged, vec_scores=vec_scores) if hybrid else kw

        total = len(rows)
        if limit is None:
            return {"items": rows, "next_cursor": None, "total": total}
        start = max(0, int(cursor or 0))
        lim = int(limit)
        items = rows[start:start + lim]
        next_cursor = start + lim if start + lim < total else None
        return {"items": items, "next_cursor": next_cursor, "total": total}

    def material_health_counts(self) -> dict:
        """健康度计数:从未召回 / 无 summary / 无标签(活跃库,排除 archived)。"""
        rows = self.list_materials(archived=False) or []
        never = sum(1 for m in rows if not (m.get("recall_count") or 0))
        no_sum = sum(1 for m in rows if not (m.get("summary") or "").strip())
        untagged = sum(1 for m in rows if not (m.get("tags") or m.get("ref_tags")))
        return {
            "total": len(rows),
            "never_recalled": never,
            "no_summary": no_sum,
            "untagged": untagged,
        }

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
        """局部更新;title/body 变则重算 tokens+embedding。返回是否存在。

        origin 禁止更新(创建时固定)。summary/ref_tags/pinned/archived 可改。
        """
        if fields.get("kind") is not None and fields["kind"] not in MATERIAL_KINDS:
            raise ValueError(f"非法素材分类 kind='{fields['kind']}'(合法: {list(MATERIAL_KINDS)})")
        # 创建来源不可变
        fields = {k: v for k, v in fields.items() if k != "origin"}
        if not self._material_exists(material_id):
            return False
        if "title" in fields or "body" in fields:
            cur = self.get_material(material_id) or {}
            toks, vec = self._material_index_fields(
                fields.get("title", cur.get("title")), fields.get("body", cur.get("body")))
            fields = {**fields, "tokens": toks, "embedding": vec}
        self._update_by("material", material_id, fields)
        # Task 16-B:素材 archive/pin(及正文改动)发表级失效,清检索缓存里的素材召回。
        if "archived" in fields or "pinned" in fields or "title" in fields or "body" in fields or "summary" in fields:
            _emit_cache_invalidation("material", self.db_name, store=self)
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
        _emit_cache_invalidation("material", getattr(self, "db_name", None), store=self)
        return True

    @staticmethod
    def _material_index_fields(title, body):
        """FTS 分词 + embedding(add/update/backfill 共用,DRY)。"""
        from scribe3.embed import embed
        from scribe3.text_tokens import tokenize_for_fts
        text = f"{title or ''}\n{body or ''}"
        toks = tokenize_for_fts(text)
        return toks, embed([text])[0]

    def _material_knn_scores(self, query: str, k: int = 20) -> dict[str, float]:
        """素材向量近邻：id → 1-距离。失败返回空，调用方降级字面层。"""
        t0 = time.perf_counter()
        q = (query or "").strip()
        if not q:
            return {}
        from scribe3.embed import embed
        knn_k = max(5, int(k))
        qv = embed([q])[0]
        rows = self._query(
            f"SELECT meta::id(id) AS id, vector::distance::knn() AS dist FROM material "
            f"WHERE embedding <|{knn_k},{max(40, knn_k)}|> $qv "
            f"AND (archived = NONE OR archived != true) ORDER BY dist",
            {"qv": qv},
        ) or []
        out: dict[str, float] = {}
        for r in rows:
            mid = str(r.get("id") or "")
            if not mid:
                continue
            dist = float(r.get("dist") or 0.0)
            out[mid] = max(0.0, min(1.0, 1.0 - dist))
        elapsed = time.perf_counter() - t0
        if elapsed > 0.5:
            _log.warning("knn search slow: %.1fs", elapsed)
        return out

    def _material_embedding(self, material_id: str):
        rows = self._query(
            "SELECT embedding FROM type::record('material',$m) LIMIT 1", {"m": material_id})
        return (rows[0].get("embedding") if rows else None)

    def add_material_reference(self, material_id, chapter, dimension=None,
                               reason=None, via="manual", ref_kind: str | None = None) -> None:
        """记一次参考(溯源)+ 强化(recall_count++/last_recalled_at)。

        ref_kind: injection=正文吃进去；inspiration=只借鉴。缺省按 via 推断。
        """
        kind = (ref_kind or "").strip().lower()
        if kind not in ("injection", "inspiration"):
            kind = "injection" if str(via or "") in ("write", "brief") else "inspiration"
        try:
            self._execute_write(
                "CREATE material_reference SET material_id=$m, chapter=$c, "
                "dimension=$d, reason=$r, via=$v, ref_kind=$rk",
                {"m": material_id, "c": int(chapter), "d": dimension, "r": reason, "v": via, "rk": kind})
        except Exception:
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

    def find_near_duplicate_materials(
        self, title: str, body: str | None = None, threshold: float = 0.88, limit: int = 5,
    ) -> list[dict]:
        """近重候选:同标题优先,再 embedding 相似度。返回 [{id,title,sim,reason}]。"""
        title = (title or "").strip()
        out: list[dict] = []
        seen: set[str] = set()
        if title:
            try:
                rows = self._query(
                    f"SELECT {self._MATERIAL_COLS} FROM material "
                    "WHERE title = $t AND (archived = NONE OR archived != true) LIMIT $lim",
                    {"t": title, "lim": limit}) or []
                for r in rows:
                    mid = str(r.get("id") or "")
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    out.append({"id": mid, "title": r.get("title"), "sim": 1.0,
                                "reason": "同标题"})
            except Exception:
                _log.debug("near-dup title scan failed", exc_info=True)
        if len(out) >= limit:
            return out[:limit]
        try:
            text = f"{title or ''}\n{body or ''}".strip()
            if not text:
                return out
            from scribe3.embed import embed
            emb = embed([text])[0]
            k = max(limit * 2, 5)
            rows = self._query(
                f"SELECT meta::id(id) AS id, title, vector::distance::knn() AS dist FROM material "
                f"WHERE embedding <|{k},{max(40, k)}|> $qv "
                f"AND (archived = NONE OR archived != true) ORDER BY dist LIMIT $lim",
                {"qv": emb, "lim": k}) or []
            for r in rows:
                mid = str(r.get("id") or "")
                if not mid or mid in seen:
                    continue
                sim = 1.0 - float(r.get("dist") or 0.0)
                if sim < threshold:
                    continue
                seen.add(mid)
                out.append({"id": mid, "title": r.get("title"), "sim": round(sim, 4),
                            "reason": "语义近邻"})
                if len(out) >= limit:
                    break
        except Exception:
            _log.debug("near-dup embedding scan failed", exc_info=True)
        return out[:limit]

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
        """查素材的 relates 联想邻居(出边;表未建/无边→空)。"""
        try:
            return self._query(
                "SELECT meta::id(out) AS id, weight, reason FROM relates "
                "WHERE in = type::record('material',$m)", {"m": material_id}) or []
        except Exception:
            return []

    def material_relates_bidirectional(self, material_id) -> list[dict]:
        """双向邻居:出边 out + 入边 in。"""
        out = []
        try:
            rid = f"type::record('material',$m)"
            rows = self._query(
                "SELECT meta::id(out) AS id, weight, reason, 'out' AS dir FROM relates "
                "WHERE in = type::record('material',$m) "
                "UNION "
                "SELECT meta::id(in) AS id, weight, reason, 'in' AS dir FROM relates "
                "WHERE out = type::record('material',$m)",
                {"m": material_id})
            if rows:
                return rows
        except Exception:
            pass
        # UNION 失败时拆两次查
        try:
            for r in self._query(
                "SELECT meta::id(out) AS id, weight, reason FROM relates "
                "WHERE in = type::record('material',$m)", {"m": material_id}) or []:
                out.append({**r, "dir": "out"})
            for r in self._query(
                "SELECT meta::id(in) AS id, weight, reason FROM relates "
                "WHERE out = type::record('material',$m)", {"m": material_id}) or []:
                out.append({**r, "dir": "in"})
        except Exception:
            return out
        return out

    def material_graph(self, focus: str | None = None, limit: int = 200, hop: int = 1) -> dict:
        """素材记忆网络:节点 + relates 边。

        focus 非空时做 ego-neighborhood:从 focus 沿 relates 双向 BFS hop 跳;
        否则全库列表截断到 limit。truncated=是否有更多节点未纳入。
        """
        focus = (focus or "").strip() or None
        hop = max(1, min(int(hop or 1), 3))
        limit = max(1, int(limit or 200))
        degraded_sources: list[dict] = []

        if focus:
            keep: list[str] = [focus]
            seen = {focus}
            frontier = [focus]
            try:
                for _ in range(hop):
                    nxt: list[str] = []
                    for nid in frontier:
                        for e in self.material_relates_bidirectional(nid):
                            oid = str(e.get("id") or "")
                            if not oid or oid in seen:
                                continue
                            seen.add(oid)
                            nxt.append(oid)
                            keep.append(oid)
                            if len(keep) >= limit:
                                break
                        if len(keep) >= limit:
                            break
                    frontier = nxt
                    if not frontier or len(keep) >= limit:
                        break
            except Exception as e:
                degraded_sources.append({"source": "relates", "reason": str(e)})
            nodes = []
            for mid in keep[:limit]:
                m = self.get_material(mid)
                if not m:
                    if mid == focus:
                        # focus 不存在也返回空图而非 500
                        continue
                    continue
                if m.get("archived"):
                    continue
                nodes.append({
                    "id": m["id"], "title": m.get("title"), "kind": m.get("kind"),
                    "recall_count": m.get("recall_count") or 0, "pinned": bool(m.get("pinned")),
                    "ref_tags": m.get("ref_tags") or [], "origin": m.get("origin") or "manual",
                    "summary": m.get("summary"),
                })
            # 若 focus 本身 archived/缺失,nodes 可能为空
            keep_ids = {n["id"] for n in nodes}
            # truncated: 还有未纳入的邻居
            truncated = len(seen) > len(nodes)
            edges = []
            try:
                rows = self._query(
                    "SELECT meta::id(in) AS src, meta::id(out) AS dst, weight FROM relates") or []
                edges = [{"src": r["src"], "dst": r["dst"], "weight": r.get("weight") or 1.0}
                         for r in rows
                         if r.get("src") in keep_ids and r.get("dst") in keep_ids]
            except Exception as e:
                edges = []
                degraded_sources.append({"source": "relates", "reason": str(e)})
            return {
                "nodes": nodes,
                "edges": edges,
                "edges_degraded": bool(degraded_sources),
                "degraded_sources": degraded_sources,
                "truncated": truncated,
                "focus": focus,
                "hop": hop,
            }

        # 全图:列表截断
        all_nodes = [{"id": m["id"], "title": m.get("title"), "kind": m.get("kind"),
                      "recall_count": m.get("recall_count") or 0, "pinned": bool(m.get("pinned")),
                      "ref_tags": m.get("ref_tags") or [], "origin": m.get("origin") or "manual",
                      "summary": m.get("summary")}
                     for m in self.list_materials()]
        truncated = len(all_nodes) > limit
        nodes = all_nodes[:limit]
        keep = {n["id"] for n in nodes}
        edges = []
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
            "focus": None,
            "hop": hop,
        }

    # ── 导入 job 持久化(一书一 DB,bound to work) ──

    def save_import_job(self, job_id: str, data: dict) -> None:
        """UPSERT 导入 job;data 含 stage/done/total/items/error/source/work。"""
        fields = {
            "job_id": job_id,
            "work": data.get("work") or self.db_name,
            "stage": data.get("stage") or "",
            "done": bool(data.get("done")),
            "total": int(data.get("total") or 0),
            "items": list(data.get("items") or []),
            "error": data.get("error") or "",
            "source": data.get("source"),
        }
        try:
            existing = self._query(
                "SELECT meta::id(id) AS id FROM material_import_job WHERE job_id=$j LIMIT 1",
                {"j": job_id}) or []
            if existing:
                self._execute_write(
                    "UPDATE type::record('material_import_job',$id) SET "
                    "stage=$stage, done=$done, total=$total, items=$items, "
                    "error=$error, source=$source, work=$work, updated_at=time::now()",
                    {"id": existing[0]["id"], **{k: fields[k] for k in
                     ("stage", "done", "total", "items", "error", "source", "work")}})
            else:
                # 不用 CONTENT 塞字符串时间戳;让 VALUE time::now() 字段定义生效
                self._execute_write(
                    "CREATE material_import_job SET "
                    "job_id=$job_id, work=$work, stage=$stage, done=$done, total=$total, "
                    "items=$items, error=$error, source=$source",
                    fields)
        except Exception:
            try:
                self._execute_write(
                    "DELETE material_import_job WHERE job_id=$j", {"j": job_id})
                self._execute_write(
                    "CREATE material_import_job SET "
                    "job_id=$job_id, work=$work, stage=$stage, done=$done, total=$total, "
                    "items=$items, error=$error, source=$source",
                    fields)
            except Exception:
                _log.error("save_import_job failed job=%s", job_id, exc_info=True)
                raise

    def get_import_job(self, job_id: str) -> dict | None:
        try:
            rows = self._query(
                "SELECT job_id, work, stage, done, total, items, error, source, "
                "created_at, updated_at FROM material_import_job WHERE job_id=$j LIMIT 1",
                {"j": job_id}) or []
            return rows[0] if rows else None
        except Exception:
            return None

    def delete_import_job(self, job_id: str) -> None:
        try:
            self._execute_write("DELETE material_import_job WHERE job_id=$j", {"j": job_id})
        except Exception:
            pass

    def purge_expired_import_jobs(self, ttl_sec: int = _IMPORT_JOB_TTL_SEC) -> int:
        """清理过期 job;返回删除数(尽力)。"""
        try:
            # Surreal 时间比较:用 updated_at 字符串比较不稳,扫 Python 侧
            rows = self._query(
                "SELECT meta::id(id) AS id, job_id, updated_at, created_at "
                "FROM material_import_job") or []
            now = time.time()
            n = 0
            for r in rows:
                ts = r.get("updated_at") or r.get("created_at")
                age = None
                if hasattr(ts, "timestamp"):
                    age = now - ts.timestamp()
                elif isinstance(ts, str):
                    try:
                        from datetime import datetime
                        age = now - datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        age = None
                if age is not None and age > ttl_sec:
                    self._execute_write(
                        "DELETE type::record('material_import_job',$id)",
                        {"id": r["id"]})
                    n += 1
            return n
        except Exception:
            return 0

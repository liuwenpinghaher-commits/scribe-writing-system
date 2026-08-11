"""SurrealStore mixin: recall."""
from __future__ import annotations

from scribe3.store.core_preamble import *  # noqa: F403

class RecallMixin:

    def semantic_index(self, oid: str, text: str) -> None:
        """给某命题写入 embedding(语义召回用;经 execute_write 单点)。

        反哺会并发写命题与向量字段；SurrealDB 的事务冲突是可重试的瞬态失败。向量
        已在循环外生成，重试只重放幂等 UPDATE，避免一条已落库命题永久不可语义召回。
        """
        from scribe3.embed import embed
        import time
        _, local = _split(oid)
        vector = embed([text])[0]
        # S-1: 同步写 tokens（jieba 空格串）供 BM25 / 混合检索
        tokens = ""
        try:
            import jieba
            tokens = " ".join(w for w in jieba.cut(text or "") if len(w.strip()) >= 1)[:2000]
        except Exception:
            tokens = (text or "")[:2000]
        for attempt in range(3):
            try:
                self._execute_write(
                    "UPDATE type::record('proposition',$local) SET embedding=$v, tokens=$tok",
                    {"local": local, "v": vector, "tok": tokens},
                )
                return
            except Exception as e:
                # tokens 字段未迁移时降级只写 embedding
                if "tokens" in str(e).lower() or "field" in str(e).lower():
                    try:
                        self._execute_write(
                            "UPDATE type::record('proposition',$local) SET embedding=$v",
                            {"local": local, "v": vector},
                        )
                        return
                    except Exception:
                        pass
                transient = "transaction" in str(e).lower() and "conflict" in str(e).lower()
                if not transient or attempt == 2:
                    raise
                logging.getLogger("scribe3.store").warning(
                    "semantic_index 事务冲突，重试 %s/2 命题 %s: %s", attempt + 1, oid, str(e)[:120])
                time.sleep(0.05 * (attempt + 1))

    def semantic_recall(self, query: str, k: int = 5, chapter: int | None = None) -> list[Fact]:
        """语义召回最相关命题(HNSW <|K,EF|>,按距离升序)。
        D-022:<|K,COSINE|> 显式距离形式经 EXPLAIN 实锤为 KnnTopK+TableScan 暴力扫描,
        <|K,EF数字|> 才走 HNSW 索引(KnnScan);EF=max(40,K) 召回富余,14 组对拍一致。

        chapter 非空时做限知时间门:保留 valid_from <= chapter 且
        (valid_to 为空或 valid_to > chapter) 的命题。后过滤,避免 KNN×WHERE 组合坑。
        """
        from scribe3.embed import embed
        # chapter 门后过滤可能裁掉若干条,多取一些 HNSW 候选再截到 k
        knn_k = int(k) if chapter is None else min(max(int(k) * 3, int(k)), 40)
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, "
            f"secret, leak_markers, vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{knn_k},{max(40, knn_k)}|> $qv "
            f"AND (archived = NONE OR archived != true) ORDER BY dist",
            {"qv": qv})
        facts = [Fact(f"fact:{r['local']}", r.get("entity_id") or "",
                      r["attribute"], r["value"], r["valid_from"],
                      r.get("valid_to"), r.get("secret", False), r.get("leak_markers", []))
                 for r in rows]
        if chapter is not None:
            ch = int(chapter)
            facts = [f for f in facts
                     if f.valid_from <= ch
                     and (f.valid_to is None or f.valid_to > ch)]
        return facts[:k]

    def hybrid_recall(self, query: str, chapter: int, k: int = 5) -> list[Fact]:
        """混合召回:向量路 + 关键词路 → RRF 融合排名。

        S-1: SCRIBE3_HYBRID_SEARCH_NATIVE=1 时走**单程** SurQL（双通道一次往返 + 融合）；
        失败/flag 关回退 legacy 双查询 + Python RRF。
        限知时间门(chapter)过滤未来事实。
        """
        try:
            from scribe3.surreal_flags import hybrid_search_native
            if hybrid_search_native():
                out = self._hybrid_recall_native(query, chapter, k=k)
                if out is not None:
                    return out
        except Exception:
            logging.getLogger("scribe3.store").debug(
                "hybrid_recall native fail→legacy", exc_info=True)
        return self._hybrid_recall_legacy(query, chapter, k=k)

    def _hybrid_recall_legacy(self, query: str, chapter: int, k: int = 5) -> list[Fact]:
        """Legacy: 两次 DB 往返 + Python RRF。"""
        vector_results = self.semantic_recall(query, k=min(k * 3, 20), chapter=chapter)
        keyword_results = _keyword_search_propositions(self, query, chapter, top_k=k * 2)

        vec_ids = [f.id for f in vector_results]
        kw_ids = [f.id for f in keyword_results]

        fused = _reciprocal_rank_fusion(vec_ids, kw_ids, k=60)
        top_ids = [item_id for item_id, _ in fused[:k]]

        all_facts = {f.id: f for f in vector_results + keyword_results}
        ch = int(chapter)
        out = []
        for fid in top_ids:
            f = all_facts.get(fid)
            if f is None:
                continue
            if f.valid_from > ch:
                continue
            if f.valid_to is not None and f.valid_to <= ch:
                continue
            out.append(f)
        return out

    def _hybrid_recall_native(self, query: str, chapter: int, k: int = 5) -> list[Fact] | None:
        """单程混合：一次 _query 取向量候选 + 关键词候选，再 RRF（或 search::rrf）。

        返回 None 表示应回退 legacy。
        """
        from scribe3.embed import embed
        import jieba

        ch = int(chapter)
        kk = min(max(int(k) * 3, int(k)), 20)
        ef = max(40, kk)
        qv = embed([query or ""])[0]
        kws = [w for w in jieba.cut(query or "") if len(w.strip()) >= 2]
        kw0 = kws[0] if kws else (query or "")[:8]
        # 单脚本：向量 HNSW + 全文(优先 tokens BM25，失败侧 CONTAINS 由 Python 不负责)
        # 融合：优先 search::rrf；否则 Python RRF
        bundle = self._query(
            "LET $vs = ("
            "  SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, "
            "  secret, leak_markers, vector::distance::knn() AS dist "
            f"  FROM proposition WHERE embedding <|{kk},{ef}|> $qv "
            "  AND (archived = NONE OR archived != true) ORDER BY dist"
            "); "
            "LET $ft = ("
            "  SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, "
            "  secret, leak_markers FROM proposition "
            "  WHERE valid_from <= $ch AND (valid_to = NONE OR valid_to > $ch) "
            "  AND (archived = NONE OR archived != true) "
            "  AND ("
            "    (tokens IS NOT NONE AND tokens @@ $qtok)"
            "    OR string::lowercase(value) CONTAINS string::lowercase($kw)"
            "  ) "
            "  LIMIT $tk"
            "); "
            "RETURN { vs: $vs, ft: $ft };",
            {
                "qv": qv, "ch": ch, "kw": kw0, "tk": int(k) * 2,
                "qtok": " ".join(kws) if kws else kw0,
            },
        )
        if not bundle:
            return None
        row0 = bundle[0] if isinstance(bundle, list) else bundle
        if not isinstance(row0, dict):
            return None
        # 部分驱动把 RETURN 包一层
        if "vs" not in row0 and isinstance(row0.get("result"), dict):
            row0 = row0["result"]
        vs_rows = row0.get("vs") or []
        ft_rows = row0.get("ft") or []
        if not isinstance(vs_rows, list):
            vs_rows = []
        if not isinstance(ft_rows, list):
            ft_rows = []

        def _fact(r):
            return Fact(
                f"fact:{r['local']}", r.get("entity_id") or "",
                r["attribute"], r["value"], r["valid_from"],
                r.get("valid_to"), r.get("secret", False), r.get("leak_markers", []),
            )

        vector_results = []
        for r in vs_rows:
            if not isinstance(r, dict) or not r.get("local"):
                continue
            f = _fact(r)
            if f.valid_from <= ch and (f.valid_to is None or f.valid_to > ch):
                vector_results.append(f)
        keyword_results = [_fact(r) for r in ft_rows if isinstance(r, dict) and r.get("local")]

        vec_ids = [f.id for f in vector_results]
        kw_ids = [f.id for f in keyword_results]
        # 优先 DB search::rrf：Surreal 3.2 要求「对象列表」[{id},…] 而非纯字符串
        # （纯字符串会静默返回 []）。失败则 Python RRF。
        fused_ids: list[str] = []
        try:
            a_objs = [{"id": i} for i in vec_ids]
            b_objs = [{"id": i} for i in kw_ids]
            rrf = self._query(
                "RETURN search::rrf([$a, $b], $lim, 60);",
                {"a": a_objs, "b": b_objs, "lim": int(k)},
            )
            # Surreal 驱动常见两种形态：
            #   1) 扁平 [{id, rrf_score}, …]（_query 解包后）
            #   2) 包一层 [[…]] / {result: […]}
            items: list = []
            if isinstance(rrf, list) and rrf:
                if isinstance(rrf[0], dict) and ("id" in rrf[0] or "rrf_score" in rrf[0]):
                    items = rrf
                elif isinstance(rrf[0], list):
                    items = rrf[0]
            elif isinstance(rrf, dict):
                inner = rrf.get("result") or rrf.get("vs")
                if isinstance(inner, list):
                    items = inner
            for x in items:
                if isinstance(x, dict) and x.get("id") is not None:
                    fused_ids.append(str(x["id"]))
                elif x is not None and not isinstance(x, dict):
                    fused_ids.append(str(x))
            fused_ids = fused_ids[:k]
        except Exception:
            fused_ids = []
        if not fused_ids:
            fused = _reciprocal_rank_fusion(vec_ids, kw_ids, k=60)
            fused_ids = [item_id for item_id, _ in fused[:k]]

        all_facts = {f.id: f for f in vector_results + keyword_results}
        out = []
        for fid in fused_ids:
            f = all_facts.get(fid)
            if f is None:
                continue
            if f.valid_from > ch:
                continue
            if f.valid_to is not None and f.valid_to <= ch:
                continue
            out.append(f)
        return out

    def causal_chain(
        self,
        event_id: str,
        *,
        direction: str = "forward",
        max_depth: int = 10,
    ) -> list[dict]:
        """S-4: 递归因果链。direction=forward|backward；深度封顶。

        返回 [{id, title, seq}, ...] 链节点（含起点时依赖查询形态）。
        """
        eid = (event_id or "").strip()
        if eid.startswith("event:"):
            eid = eid.split(":", 1)[-1]
        if not eid:
            return []
        depth = max(1, min(int(max_depth), 20))
        if (direction or "forward").lower().startswith("back"):
            arrow = f"<-causal(..{depth})<-event"
        else:
            arrow = f"->causal(..{depth})->event"
        try:
            rows = self._query(
                f"SELECT meta::id(id) AS local, title, seq, "
                f"{arrow}.{{id, title, seq}} AS chain "
                f"FROM type::record('event', $eid);",
                {"eid": eid},
            ) or []
        except Exception:
            # 兼容无递归语法时的 1 跳
            try:
                rows = self._query(
                    "SELECT meta::id(id) AS local, title, seq, "
                    "->causal->event.{id, title, seq} AS chain "
                    "FROM type::record('event', $eid);",
                    {"eid": eid},
                ) or []
            except Exception:
                return []
        if not rows:
            return []
        r0 = rows[0] if isinstance(rows, list) else rows
        if not isinstance(r0, dict):
            return []
        chain = r0.get("chain") or []
        if not isinstance(chain, list):
            chain = [chain] if chain else []
        out: list[dict] = []
        # 起点
        out.append({
            "id": f"event:{r0.get('local') or eid}",
            "title": r0.get("title"),
            "seq": r0.get("seq"),
        })
        for node in chain:
            if isinstance(node, dict):
                nid = node.get("id") or node.get("local")
                out.append({
                    "id": str(nid) if nid else None,
                    "title": node.get("title"),
                    "seq": node.get("seq"),
                })
            else:
                out.append({"id": str(node), "title": None, "seq": None})
        return out

    def list_knowers_for_proposition(self, prop_local: str, chapter: int) -> list[dict]:
        """命题在 chapter 的知情角色富字段列表（PR-4 · 「谁知道」真源）。

        与 project_frame / graph() 同谓词: since_chapter<=ch 且 (until is None 或 until>ch)。
        返回 [{id, name, since_chapter, until_chapter, acquired_via}, ...]。
        **不**返回 proposition value（secret 安全）。
        """
        ch = int(chapter)
        plocal = (prop_local or "").strip()
        if plocal.startswith("fact:"):
            plocal = plocal.split(":", 1)[-1]
        if not plocal:
            return []
        knower_rows = self._query(
            "SELECT meta::id(in) AS knower_local, meta::tb(in) AS knower_tb, "
            "in.name AS name, since_chapter, until_chapter, acquired_via "
            "FROM knows "
            "WHERE out = type::record('proposition', $p)",
            {"p": plocal})
        knowers: list[dict] = []
        for kr in knower_rows or []:
            sc = kr.get("since_chapter")
            if sc is None:
                sc = 0
            try:
                sc_i = int(sc)
            except (TypeError, ValueError):
                sc_i = 0
            if sc_i > ch:
                continue
            uc = kr.get("until_chapter")
            uc_i = None
            if uc is not None:
                try:
                    uc_i = int(uc)
                except (TypeError, ValueError):
                    uc_i = None
                if uc_i is not None and uc_i <= ch:
                    continue
            kloc = kr.get("knower_local")
            ktb = (kr.get("knower_tb") or "character").strip() or "character"
            # 角色对外 oid 统一 role: 前缀（与 Entity 一致）
            if ktb in ("character", "role"):
                kid = f"role:{kloc}" if kloc else None
            else:
                kid = f"{ktb}:{kloc}" if kloc else None
            knowers.append({
                "id": kid,
                "name": kr.get("name") or (str(kloc) if kloc else ""),
                "since_chapter": sc_i,
                "until_chapter": uc_i,
                "acquired_via": kr.get("acquired_via") or "given",
            })
        return knowers

    def reader_knows_at_chapter(self, prop_local: str, chapter: int) -> bool:
        """读者帧是否已知该命题（reader_knows 表 · 章门 since<=ch）。"""
        ch = int(chapter)
        plocal = (prop_local or "").strip()
        if plocal.startswith("fact:"):
            plocal = plocal.split(":", 1)[-1]
        if not plocal:
            return False
        # reader_knows.proposition 写入多为 fact:local 字符串；兼容裸 local / record
        candidates = [f"fact:{plocal}", plocal]
        for p in candidates:
            rows = self._query(
                "SELECT since_chapter FROM reader_knows WHERE proposition = $p",
                {"p": p}) or []
            for r in rows:
                sc = r.get("since_chapter")
                try:
                    sc_i = 0 if sc is None else int(sc)
                except (TypeError, ValueError):
                    sc_i = 0
                if sc_i <= ch:
                    return True
        return False

    def knowers_at_chapter(self, prop_local: str, chapter: int) -> list[str]:
        """命题在 chapter 的知情角色名列表（兼容薄封装 → list_knowers_for_proposition）。
        与 project_frame / graph() 同谓词: since_chapter<=ch 且 (until is None 或 until>ch)。
        纯库查询,不依赖 KNN——单测可确定性断言。"""
        return [
            k["name"] for k in self.list_knowers_for_proposition(prop_local, chapter)
            if k.get("name")
        ]

    def attach_knowers_to_fact_items(
        self,
        items: list[dict],
        chapter: int,
        *,
        fill_closed: bool = False,
    ) -> list[dict]:
        """为 _fact_item 结果批量附 knowers / reader_knows（同请求内批处理，禁 graph ego）。

        规格：with_knowers=1 时至少为 **仍 open** 的行填 knowers；closed 默认 [] 省成本。
        """
        ch = int(chapter)

        def _open_at(vf, vt) -> bool:
            try:
                vf_i = int(vf) if vf is not None else 0
            except (TypeError, ValueError):
                vf_i = 0
            if vf_i > ch:
                return False
            if vt is None:
                return True
            try:
                return int(vt) > ch
            except (TypeError, ValueError):
                return True

        for it in items:
            fid = str(it.get("id") or "")
            local = fid.split(":", 1)[-1] if fid else ""
            if not _open_at(it.get("valid_from"), it.get("valid_to")) and not fill_closed:
                it["knowers"] = []
                it["reader_knows"] = False
                continue
            it["knowers"] = self.list_knowers_for_proposition(local, ch)
            it["reader_knows"] = self.reader_knows_at_chapter(local, ch)
        return items

    def graph_recall(self, query: str, chapter: int, k: int = 5) -> list[dict]:
        """Graph RAG:向量召回种子命题 + 沿图边拼知识子图(B枢纽)。
        返回每条种子事实 + {主体, 知情角色, 来源事件, 同场角色}。
        限知时间门(chapter)过滤未来事实与已失效命题(valid_to)。
        knowers 经 knowers_at_chapter 过滤(不依赖图边 SQL 无时间门的默认 FETCH)。"""
        from scribe3.embed import embed
        qv = embed([query])[0]
        rows = self._query(
            # entity_link:疑似死(P2-15)——migration 026 定义字段+索引但"数据迁移后切换"从未落地,
            #   全仓无写入方,此处 entity_link.name 恒 null,subject 回退 entity_id(下方 or 兜底)。
            #   保留待确认(移除牵动 live 召回查询+idx_prop_entity_link 索引)。
            f"SELECT meta::id(id) AS local, entity_id, attribute, value, valid_from, valid_to, secret, "
            f"  entity_link.name AS subject, "
            f"  <-knows<-character.name AS knowers, "
            f"  <-causes<-event.event_type AS source_events, "
            f"  <-causes<-event->involves->character.name AS co_present, "
            f"  vector::distance::knn() AS dist "
            f"FROM proposition WHERE embedding <|{int(k)},{max(40, int(k))}|> $qv "
            f"  AND valid_from <= $ch AND (archived = NONE OR archived != true) "
            f"ORDER BY dist", {"qv": qv, "ch": chapter})
        out = []
        ch = int(chapter)
        for r in rows:
            vt = r.get("valid_to")
            # SQL 侧暂只滤 valid_from(KNN×复杂 WHERE 历史坑);valid_to 在 Python 后滤
            if vt is not None and vt <= ch:
                continue
            out.append({
                "id": f"fact:{r['local']}",
                "value": r["value"],
                "attribute": r.get("attribute", ""),
                "valid_from": r.get("valid_from", 0),
                "secret": bool(r.get("secret", False)),
                "subject": r.get("subject") or r.get("entity_id") or "",
                "knowers": self.knowers_at_chapter(r["local"], ch),
                "source_events": r.get("source_events") or [],
                "co_present": r.get("co_present") or [],
                "distance": r.get("dist", 0),
            })
            if len(out) >= k:
                break
        return out

    def recall_lessons(self, query: str, k: int = 3, min_sim: float | None = None) -> list[dict]:
        """HNSW 语义召回 lesson,相似度下限过滤(宁缺勿滥:相关但不适用比无关更毒),
        命中即 uses+1(质量闭环);invalid 条目 Python 侧过滤(避开 KNN×WHERE 组合坑,Q4)。"""
        if not (query or "").strip():
            return []
        from scribe3.embed import embed
        if min_sim is None:
            from scribe3.lesson import RECALL_MIN_SIM as min_sim   # 真机标定值(D-017)
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT meta::id(id) AS id, chapter, kind, text, condition, importance, uses, "
            f"invalid_at, vector::distance::knn() AS dist "
            f"FROM lesson WHERE embedding <|{int(max(k * 3, 6))},{max(40, int(k * 3))}|> $qv "
            f"ORDER BY dist", {"qv": qv})
        out: list[dict] = []
        for r in rows:
            if r.get("invalid_at"):
                continue
            sim = 1 - r["dist"] if r.get("dist") is not None else 0.0
            if sim < min_sim:
                continue
            r["sim"] = round(sim, 4)
            r.pop("dist", None)
            r.pop("invalid_at", None)
            out.append(r)
            if len(out) >= k:
                break
        for r in out:
            self._execute_write("UPDATE type::record('lesson',$i) SET uses += 1",
                                {"i": r["id"]})
        return out

    def material_recall(self, query: str, chapter: int | None = None, k: int = 5,
                        mentioned_entities=None, degraded_out: list | None = None) -> list[dict]:
        """素材三通道召回(语义 HNSW + 全文 BM25 + 图 relates/about)→ RRF 融合 → 强度加权。
        archived 排除。返回按强度排序的 top-k 素材行(含 material_id/score)。

        degraded_out: 可选 list,通道失败时 append {source, reason}(不改返回值形状,兼容旧调用)。
        """
        import jieba
        from scribe3.embed import embed
        from scribe3.material_recall import apply_strength
        if not (query or "").strip():
            return []
        k3, ef = k * 3, max(40, k * 3)
        # 语义路(HNSW,archived 排除)
        try:
            vec_ids = [r["id"] for r in self._query(
                f"SELECT meta::id(id) AS id, vector::distance::knn() AS dist FROM material "
                f"WHERE embedding <|{k3},{ef}|> $qv "
                f"AND (archived = NONE OR archived != true) ORDER BY dist",
                {"qv": embed([query])[0]})]
        except Exception as e:
            logging.getLogger("scribe3").error("material_recall 语义路失败(该路清零)", exc_info=True)   # U-011
            vec_ids = []
            if degraded_out is not None:
                degraded_out.append({"source": "semantic", "reason": str(e)[:200]})
        # 全文路(tokenize_for_fts → BM25 search::score)
        from scribe3.text_tokens import tokenize_for_fts
        q_toks = tokenize_for_fts(query)
        fts_ids = []
        if q_toks:
            try:
                fts_ids = [r["id"] for r in self._query(
                    "SELECT meta::id(id) AS id, search::score(1) AS s FROM material "
                    "WHERE tokens @1@ $q AND (archived = NONE OR archived != true) "
                    "ORDER BY s DESC LIMIT $lim",
                    {"q": q_toks, "lim": k * 2})]
            except Exception as e:
                logging.getLogger("scribe3").error("material_recall 全文路失败(该路清零)", exc_info=True)   # U-011
                fts_ids = []
                if degraded_out is not None:
                    degraded_out.append({"source": "fts", "reason": str(e)[:200]})
        # 图路:语义种子沿 relates 扩展 + about_entities 匹配本章提及实体
        graph_ids: list[str] = []
        graph_fail = False
        for sid in vec_ids[:2]:
            try:
                graph_ids.extend(e["id"] for e in self.material_relates(sid))
            except Exception as e:
                graph_fail = True
                if degraded_out is not None:
                    degraded_out.append({"source": "graph", "reason": str(e)[:200]})
                break
        if mentioned_entities:
            try:
                graph_ids.extend(r["id"] for r in self._query(
                    "SELECT meta::id(id) AS id FROM material "
                    "WHERE about_entities CONTAINSANY $ents "
                    "AND (archived = NONE OR archived != true)",
                    {"ents": list(mentioned_entities)}))
            except Exception as e:
                if not graph_fail and degraded_out is not None:
                    degraded_out.append({"source": "graph_about", "reason": str(e)[:200]})
        # RRF 融合三路 → 位次转分 → 强度加权
        fused = _reciprocal_rank_fusion(vec_ids, fts_ids, graph_ids, k=60)
        top_ids = [i for i, _ in fused[:k * 2]]
        if not top_ids:
            return []
        cands = []
        for i, mid in enumerate(top_ids):
            row = self.get_material(mid)
            if not row or row.get("archived"):
                continue   # 图路邻居可能含 archived,Python 层再兜一次
            row["material_id"] = mid
            row["score"] = 1.0 / (i + 1)
            cands.append(row)
        return apply_strength(cands)[:k]


    def save_memory_trace(self, trace: dict) -> str:
        """落一条记忆溯源 trace,返回 trace_id。

        服务端权威屏蔽:selected/rejected 里携私密的证据,value/text 在【落库前】就抹掉
        (mask_memory_trace),DB 永不持有私密明文——不靠前端不显(Task 7 教训)。
        同 trace_id 重放:先删后建(幂等 upsert 语义,单语句各自 _execute_write,
        不触多语句 query() 吞错铁律)。"""
        if not isinstance(trace, dict) or not trace.get("trace_id"):
            raise ValueError("save_memory_trace: 需要 trace['trace_id']")
        # C1 权威兜底(at-rest 不变量):落库前叠加 store 权威 secret 集,凡候选 source_id
        # ∈ 权威 secret 即屏蔽——不信 retriever 自报的 provenance.secret(漏标即秘密明文入 DB)。
        # U-011(作者要 fail-loud):删"失败退空集"——这正是 docstring 自称"at-rest 保证"的
        # 权威兜底本尊,它自己失败退空=秘密明文入 DB(fail-open)。失败直接【抛】,拒绝落库。
        from scribe3.context_assembler import _secret_fact_ids
        secret_ids = _secret_fact_ids(self)
        t = mask_memory_trace(trace, secret_ids=secret_ids)
        tid = str(t["trace_id"])
        doc = {
            "trace_id": tid,
            "work": str(t.get("work") or ""),
            "thread_id": str(t.get("thread_id") or ""),
            "context_session_id": str(t.get("context_session_id") or ""),
            "snapshot_revision": int(t.get("snapshot_revision") or 0),
            "snapshot_hash": str(t.get("snapshot_hash") or ""),
            "envelope_hash": str(t.get("envelope_hash") or ""),
            "query": str(t.get("query") or ""),
            "channels": t.get("channels") or {},
            "selected": t.get("selected") or [],
            "rejected": t.get("rejected") or [],
            "block_tokens": t.get("block_tokens") or {},
            "latency_ms": t.get("latency_ms") or {},
            "response_id": t.get("response_id"),
            "run_id": t.get("run_id"),
        }
        self._execute_write("DELETE memory_trace WHERE trace_id=$tid", {"tid": tid})
        self._execute_write(
            "CREATE memory_trace SET trace_id=$trace_id, work=$work, thread_id=$thread_id, "
            "context_session_id=$context_session_id, snapshot_revision=$snapshot_revision, "
            "snapshot_hash=$snapshot_hash, envelope_hash=$envelope_hash, query=$query, "
            "channels=$channels, selected=$selected, rejected=$rejected, "
            "block_tokens=$block_tokens, latency_ms=$latency_ms, "
            "response_id=$response_id, run_id=$run_id",
            doc)
        return tid

    def get_memory_trace(self, trace_id: str) -> dict | None:
        """按 trace_id 取溯源。出参再过一遍 mask(防御性:任何私密明文绝不出服务端)。"""
        rows = self._query(
            f"SELECT {self._MEMORY_TRACE_COLS} FROM memory_trace WHERE trace_id=$tid LIMIT 1",
            {"tid": trace_id})
        return mask_memory_trace(rows[0]) if rows else None

    def get_memory_trace_for_snapshot(self, session_id: str, revision: int) -> dict | None:
        """按 (会话, 快照版本) 取该版本最近一次溯源(GET trace API 的自然键)。"""
        rows = self._query(
            f"SELECT {self._MEMORY_TRACE_COLS} FROM memory_trace "
            "WHERE context_session_id=$sid AND snapshot_revision=$rev "
            "ORDER BY created_at DESC LIMIT 1",
            {"sid": session_id, "rev": int(revision)})
        return mask_memory_trace(rows[0]) if rows else None

    def save_context_turn_bind(self, view: dict) -> str:
        """B∪C：按 (session, revision) 幂等落检查器 TurnBind（不含 prompt 正文）。

        selected/rejected 落库前 mask；同键先删后建。返回 bind_id。
        """
        from scribe3.store import mask_memory_trace
        if not isinstance(view, dict):
            raise ValueError("save_context_turn_bind: view 须为 dict")
        sid = str(view.get("context_session_id") or view.get("session_id") or "")
        if not sid:
            raise ValueError("save_context_turn_bind: 需要 context_session_id")
        rev = int(view.get("snapshot_revision") if view.get("snapshot_revision") is not None else 0)
        # 复用 memory_trace 的 mask 形状（selected/rejected 字段同名）
        masked = mask_memory_trace({
            "selected": view.get("selected") or [],
            "rejected": view.get("rejected") or [],
        })
        bind_id = f"ctb:{sid}:{rev}"
        doc = {
            "bind_id": bind_id,
            "work": str(view.get("work") or ""),
            "context_session_id": sid,
            "snapshot_revision": rev,
            "task_kind": str(view.get("task_kind") or "draft"),
            "path": str(view.get("path") or "write"),
            "availability": str(view.get("availability") or "ready"),
            "manifest_id": view.get("manifest_id"),
            "request_id": view.get("request_id"),
            "actual_input_hash": view.get("actual_input_hash"),
            "policy_version": view.get("policy_version"),
            "envelope_hash": str(view.get("envelope_hash") or ""),
            "query": str(view.get("query") or ""),
            "synthetic_snapshot": bool(view.get("synthetic_snapshot")),
            "block_tokens": view.get("block_tokens") or {},
            "blocks": view.get("blocks") or [],
            "selected": masked.get("selected") or [],
            "rejected": masked.get("rejected") or [],
            "usage_digest": view.get("usage_digest") or {},
        }
        self._execute_write(
            "DELETE context_turn_bind WHERE context_session_id=$sid AND snapshot_revision=$rev",
            {"sid": sid, "rev": rev},
        )
        self._execute_write(
            "CREATE context_turn_bind SET bind_id=$bind_id, work=$work, "
            "context_session_id=$context_session_id, snapshot_revision=$snapshot_revision, "
            "task_kind=$task_kind, path=$path, availability=$availability, "
            "manifest_id=$manifest_id, request_id=$request_id, "
            "actual_input_hash=$actual_input_hash, policy_version=$policy_version, "
            "envelope_hash=$envelope_hash, query=$query, "
            "synthetic_snapshot=$synthetic_snapshot, block_tokens=$block_tokens, "
            "blocks=$blocks, selected=$selected, rejected=$rejected, "
            "usage_digest=$usage_digest",
            doc,
        )
        return bind_id

    def get_context_turn_bind(self, session_id: str, revision: int) -> dict | None:
        """按 (会话, revision) 取最新 TurnBind；出参 mask selected/rejected。"""
        from scribe3.store import mask_memory_trace
        rows = self._query(
            "SELECT bind_id, work, context_session_id, snapshot_revision, task_kind, path, "
            "availability, manifest_id, request_id, actual_input_hash, policy_version, "
            "envelope_hash, query, synthetic_snapshot, block_tokens, blocks, selected, "
            "rejected, usage_digest, "
            "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at "
            "FROM context_turn_bind "
            "WHERE context_session_id=$sid AND snapshot_revision=$rev "
            "ORDER BY created_at DESC LIMIT 1",
            {"sid": session_id, "rev": int(revision)},
        )
        if not rows:
            return None
        row = dict(rows[0])
        masked = mask_memory_trace({
            "selected": row.get("selected") or [],
            "rejected": row.get("rejected") or [],
        })
        row["selected"] = masked.get("selected") or []
        row["rejected"] = masked.get("rejected") or []
        return row

    def add_memory_item(self, work: str, kind: str, text: str, *,
                        scope_type: str = "work", scope_id: str | None = None,
                        source_type: str = "", source_id: str = "",
                        summary: str = "", condition: str | None = None,
                        status: str = "active", confidence: float = 1.0,
                        importance: int = 2, pinned: bool = False,
                        observed_at=None, valid_from: int | None = None,
                        valid_to: int | None = None, known_from: int | None = None,
                        known_to: int | None = None, source_revision: str | None = None,
                        provenance: list[dict] | None = None,
                        linked_ids: list[str] | None = None,
                        entity: str | None = None, attribute: str | None = None) -> str:
        """写一条经验记忆(jieba 切 tokens + 生成 embedding),返回裸 id。

        observed_at 用 type::datetime($iso) 显式转型(不依赖 SDK datetime 序列化);
        缺省取当下墙钟。created_at 由 schema time::now() READONLY 自动落。

        Task 9 活化回填:provenance(array<object>,每项可含 entity/attribute)+ linked_ids
        (提及实体 id)是 Task 8 已就绪但静默失效的两处机制的判据——
          · 正典压制(_suppress_by_canonical)读 provenance 的 (entity,attribute);
          · focus 加权(final_score.focus_bonus)读 linked_ids。
        便捷参数 entity/attribute:显式给出时自动折进 provenance(若未另传 provenance)
        并把 entity 计入 linked_ids,免调用方手搓 provenance。"""
        if kind not in MEMORY_KINDS:
            raise ValueError(f"非法记忆类型 kind='{kind}'(合法: {list(MEMORY_KINDS)})")
        # P1 幂等根治:效果幂等——按确定性键 (work, source_type, source_id) 预查去重
        # (source_id 非空时)。捕获管线崩溃窗口后重放/重复 drain 天然 no-op:add 成功但
        # mark_complete 失败 → consolidate 认领 failed 再 add,此处预查命中即返回旧 id,不新增。
        # 与 enqueue 预查同款(单进程同步模型下 TOCTOU 不可达);source_id 空的经验记忆不去重。
        if source_id:
            _dup = self._query(
                "SELECT meta::id(id) AS id FROM memory_item "
                "WHERE work=$w AND source_type=$st AND source_id=$sid LIMIT 1",
                {"w": work, "st": source_type or "", "sid": source_id})
            if _dup:
                return _dup[0]["id"]
        from datetime import datetime as _dt, timezone as _tz
        from scribe3.embed import embed
        from scribe3.text_tokens import tokenize_for_fts
        toks = tokenize_for_fts(text or "")
        vec = embed([text or ""])[0]
        obs = observed_at
        if obs is None:
            obs = _dt.now(_tz.utc)
        obs_iso = obs.isoformat() if hasattr(obs, "isoformat") else str(obs)
        # 活化回填:entity/attribute 折进 provenance;entity 计入 linked_ids(去重保序)。
        prov = list(provenance) if provenance else []
        if (entity or attribute) and not any(
                p.get("entity") == entity and p.get("attribute") == attribute for p in prov):
            prov.append({"entity": entity or "", "attribute": attribute or ""})
        links: list[str] = []
        for lid in list(linked_ids or []) + ([entity] if entity else []):
            if lid and lid not in links:
                links.append(lid)
        rows = self._query(
            "CREATE memory_item SET "
            "work=$work, scope_type=$scope_type, scope_id=$scope_id, kind=$kind, "
            "text=$text, summary=$summary, condition=$condition, "
            "source_type=$source_type, source_id=$source_id, source_revision=$source_revision, "
            "status=$status, confidence=$confidence, importance=$importance, pinned=$pinned, "
            "observed_at=type::datetime($observed_at), "
            "valid_from=$valid_from, valid_to=$valid_to, known_from=$known_from, known_to=$known_to, "
            "provenance=$provenance, linked_ids=$linked_ids, "
            "tokens=$tokens, embedding=$embedding, updated_at=time::now()",
            {"work": work, "scope_type": scope_type, "scope_id": scope_id or work,
             "kind": kind, "text": text or "", "summary": summary or "", "condition": condition,
             "source_type": source_type or "", "source_id": source_id or "",
             "source_revision": source_revision, "status": status,
             "confidence": float(confidence), "importance": int(importance), "pinned": bool(pinned),
             "observed_at": obs_iso, "valid_from": valid_from, "valid_to": valid_to,
             "known_from": known_from, "known_to": known_to,
             "provenance": prov, "linked_ids": links, "tokens": toks, "embedding": vec})
        rid = (rows[0] if rows else {}).get("id")
        if rid is None:
            raise RuntimeError("add_memory_item: CREATE 未返回 id")
        s = str(rid)
        # M2(Task 16-C):新记忆写入发表级失效,与 supersede/invalidate 对称——清 RETRIEVAL_CACHE
        #   里同 work 的旧检索结果,消除新记忆 ≤30s TTL 的可见延迟(fail-safe 漏新不泄旧,对称更干净)。
        #   仅落在真新增路径:上方 (work,source_type,source_id) 幂等预查命中的重放 early-return 不发
        #   (无写入=无需失效)。best-effort,绝不阻断写主链路。
        _emit_cache_invalidation("memory_item", work, store=self)
        return s.split(":")[-1] if ":" in s else s

    def add_memory_relation(self, in_id: str, out_id: str, relation: str,
                            weight: float = 1.0, provenance: dict | None = None) -> None:
        """记一条记忆间联想边(graph 通道遍历用)。"""
        if relation not in MEMORY_RELATIONS:
            raise ValueError(f"非法记忆关系 relation='{relation}'(合法: {list(MEMORY_RELATIONS)})")
        self._execute_write(
            "RELATE $a->memory_relation->$b SET relation=$rel, weight=$w, provenance=$prov "
            "RETURN NONE",
            {"a": RecordID("memory_item", in_id), "b": RecordID("memory_item", out_id),
             "rel": relation, "w": float(weight), "prov": provenance or {}})

    def get_memory_items(self, ids: list[str], *, status: str | None = None) -> list[dict]:
        """按裸 id 批量取经验记忆行(检索候选水合用)。observed_at 以 <string> 回传 ISO。

        M-2 契约:本方法【不】按状态过滤(默认 status=None),会照返 superseded/invalid 行——
        调用方须保证只喂【已过滤】的 id(现有唯一调用方 memory_retrieval._hydrate_experiential 与
        memory_graph 只传各通道已按 status='active' 筛过的 id,故无泄漏)。需要状态门时显式传
        status='active' 作防御性收窄(如未来新增未经通道过滤的调用路径)。"""
        if not ids:
            return []
        recs = [RecordID("memory_item", i) for i in ids]
        where = ["id IN $recs"]
        vars: dict = {"recs": recs}
        if status:
            where.append("status=$st")
            vars["st"] = status
        return self._query(
            f"SELECT {self._MEMORY_COLS} FROM memory_item WHERE {' AND '.join(where)}", vars)

    def memory_bm25(self, work: str, query: str, k: int = 10, chapter: int | None = None) -> list[str]:
        """BM25 全文通道:tokenize_for_fts(query) → tokens @1@ 匹配,按 search::score 降序。返回裸 id。
        限知门在 SQL 侧(bm25 无 KNN,AND known_from/to 组合安全)。"""
        from scribe3.text_tokens import tokenize_for_fts
        q = tokenize_for_fts(query or "")
        if not q:
            return []
        where = ["work=$w", "status='active'", "tokens @1@ $q"]
        vars: dict = {"w": work, "q": q, "lim": int(k)}
        if chapter is not None:
            where.append("(known_from = NONE OR known_from <= $ch)")
            where.append("(known_to = NONE OR known_to > $ch)")
            vars["ch"] = int(chapter)
        rows = self._query(
            f"SELECT meta::id(id) AS id, search::score(1) AS s FROM memory_item "
            f"WHERE {' AND '.join(where)} ORDER BY s DESC LIMIT $lim", vars)
        return [r["id"] for r in rows]

    def memory_vector(self, work: str, query: str, k: int = 10, chapter: int | None = None) -> list[str]:
        """HNSW 语义通道:<|K,EF|> 数字形式走 KnnScan(D-022);同 work + active 过滤。返回裸 id。
        限知门在 Python 侧(post-KNN)——避开本仓已知的 KNN×WHERE 组合坑(lesson.recall 同款规避),
        红线不赌 KNN 与额外 WHERE 的交互。"""
        from scribe3.embed import embed
        if not (query or "").strip():
            return []
        qv = embed([query])[0]
        kk = max(int(k), 1)
        ef = max(40, kk)
        rows = self._query(
            f"SELECT meta::id(id) AS id, known_from, known_to, vector::distance::knn() AS dist "
            f"FROM memory_item WHERE embedding <|{kk},{ef}|> $qv AND work=$w AND status='active' "
            f"ORDER BY dist", {"qv": qv, "w": work})
        out: list[str] = []
        for r in rows:
            if chapter is not None and not _memory_known_at(r.get("known_from"), r.get("known_to"), chapter):
                continue
            out.append(r["id"])
        return out

    def memory_graph(self, work: str, seed_ids: list[str], k: int = 10,
                     chapter: int | None = None) -> list[str]:
        """联想边通道:从种子 memory_item 沿 memory_relation 一跳,返回邻居裸 id。
        Task 10:只回 active 邻居——superseded / invalid 记忆被生命周期排除,绝不经 graph
        绕过 bm25/vector 的 status 门倒灌回检索(supersede/invalidate 的审计留库但不召回)。
        status 与限知门都在 Python 侧(取邻居行再筛)——避开 RELATION 跨链 WHERE 的不确定性。"""
        if not seed_ids:
            return []
        seeds = [RecordID("memory_item", s) for s in seed_ids]
        rows = self._query(
            "SELECT meta::id(out) AS id FROM memory_relation WHERE in IN $seeds LIMIT $lim",
            {"seeds": seeds, "lim": int(k)})
        ids = [r["id"] for r in rows if r.get("id")]
        if not ids:
            return []
        items = {m["id"]: m for m in self.get_memory_items(ids)}
        kept: list[str] = []
        for i in ids:   # 保原遍历顺序
            m = items.get(i)
            if m is None or m.get("status") != "active":
                continue
            if chapter is not None and not _memory_known_at(
                    m.get("known_from"), m.get("known_to"), chapter):
                continue
            kept.append(i)
        return kept

    def count_memory_by_source(self, source_type: str, source_id: str,
                               work: str | None = None) -> int:
        """按 (source_type, source_id) 计 memory_item 条数(捕获幂等的验收口径)。"""
        where = ["source_type=$st", "source_id=$sid"]
        vars: dict = {"st": source_type, "sid": source_id}
        if work:
            where.append("work=$w")
            vars["w"] = work
        rows = self._query(
            f"SELECT count() AS n FROM memory_item WHERE {' AND '.join(where)} GROUP ALL", vars)
        return int(rows[0]["n"]) if rows else 0

    def get_memory(self, memory_id: str) -> dict | None:
        """按裸 id 取单条经验记忆,含审计字段(status / supersedes / invalid_at / 时间戳)。
        supersedes 以裸 id 回传(None = 非更正产物)。查无返回 None。"""
        rows = self._query(
            f"SELECT {self._MEMORY_COLS}, supersedes, "
            "(IF created_at IS NONE THEN NONE ELSE <string>created_at END) AS created_at, (IF updated_at IS NONE THEN NONE ELSE <string>updated_at END) AS updated_at, "
            "(IF invalid_at IS NONE THEN NONE ELSE <string>invalid_at END) AS invalid_at "
            "FROM type::record('memory_item', $id)", {"id": memory_id})
        if not rows:
            return None
        row = rows[0]
        sup = row.get("supersedes")
        if sup:
            s = str(sup)
            row["supersedes"] = s.split(":")[-1] if ":" in s else s
        else:
            row["supersedes"] = None
        return row

    def add_memory(self, text: str, *, work: str = "main", kind: str = "episodic",
                   **kw) -> dict:
        """便捷入口:写一条经验记忆并返回完整行(生命周期各操作的对称返回口径)。
        底层复用 add_memory_item(jieba tokens + embedding + 幂等预查),仅换成 dict 返回。"""
        mid = self.add_memory_item(work, kind, text, **kw)
        return self.get_memory(mid)

    def invalidate_memory(self, memory_id: str) -> dict:
        """作废一条经验记忆:status='invalid' + 记 invalid_at(system_time)。
        审计留库,检索与 resolve_temporal_view 都靠 status 门自动排除。
        正典/领域数据不受此管辖。"""
        _row = self.get_memory(memory_id)
        if _row is None:
            raise ValueError(f"invalidate_memory: memory_item '{memory_id}' 不存在")
        # M-3 记账:重复作废会覆写 invalid_at 为最新墙钟(system_time"最后一次失效"语义,可接受)——
        #   作废是幂等终态(status 不变),invalid_at 略微前移无害,不额外加 CAS 守卫。
        self._execute_write(
            "UPDATE type::record('memory_item', $id) SET status='invalid', "
            "invalid_at=time::now(), updated_at=time::now() RETURN NONE", {"id": memory_id})
        # M1(Task 16-C):作废发表级失效,与 supersede 对称——否则已作废记忆在 RETRIEVAL_CACHE
        #   最长 30s 仍被命中(检索层 status='active' 门只在 miss 重算时生效,缓存命中会漏 status 变更,
        #   构成"已作废记忆倒灌进写作 prompt"的短窗)。
        _emit_cache_invalidation("memory_item", _row.get("work"), store=self)
        return self.get_memory(memory_id)

    def get_memory_event(self, event_id: str) -> dict | None:
        rows = self._query(
            f"SELECT {self._MEMORY_EVENT_FIELDS} FROM memory_event WHERE event_id=$e LIMIT 1",
            {"e": event_id})
        return rows[0] if rows else None

    def enqueue_memory_event(self, event_id: str, work: str, event_type: str,
                             payload: dict, thread_id: str | None = None) -> bool:
        """幂等入队。返回 True=新建、False=已存在(不覆盖已入队事件的 payload/状态)。
        幂等靠 event_id UNIQUE:预查存在即返回;并发/竞态下 CREATE 撞唯一索引也当幂等成功。"""
        if self.get_memory_event(event_id):
            return False
        try:
            self._execute_write(
                "CREATE memory_event SET event_id=$e, work=$w, thread_id=$tid, "
                "event_type=$et, payload=$p, status='pending', attempts=0 RETURN NONE",
                {"e": event_id, "w": work, "tid": thread_id, "et": event_type,
                 "p": payload or {}})
        except Exception as ex:
            msg = str(ex).lower()
            # 唯一索引冲突 → 幂等成功;乐观事务读写冲突(多 worker 并发入队)→ 视为已入队。
            if any(s in msg for s in (
                    "index", "already", "exists",
                    "write conflict", "transaction conflict", "retry the transaction",
                    "read or write conflict")):
                return False
            raise
        return True

    def list_memory_events(self, work: str | None = None, thread_id: str | None = None,
                           event_type: str | None = None, status: str | None = None,
                           limit: int = 500) -> list[dict]:
        where: list[str] = []
        vars: dict = {"lim": int(limit)}
        if work:
            where.append("work=$w")
            vars["w"] = work
        if thread_id:
            where.append("thread_id=$tid")
            vars["tid"] = thread_id
        if event_type:
            where.append("event_type=$et")
            vars["et"] = event_type
        if status:
            where.append("status=$st")
            vars["st"] = status
        w = ("WHERE " + " AND ".join(where) + " ") if where else ""
        return self._query(
            f"SELECT {self._MEMORY_EVENT_FIELDS} FROM memory_event {w}"
            "ORDER BY created_at ASC LIMIT $lim", vars)

    def count_memory_events(self, work: str | None = None, thread_id: str | None = None,
                            event_type: str | None = None, status: str | None = None) -> int:
        """轻量计数(不载 payload):_maybe_consolidate 算每 8 轮水位用,长篇不拉全量行。"""
        where: list[str] = []
        vars: dict = {}
        if work:
            where.append("work=$w")
            vars["w"] = work
        if thread_id:
            where.append("thread_id=$tid")
            vars["tid"] = thread_id
        if event_type:
            where.append("event_type=$et")
            vars["et"] = event_type
        if status:
            where.append("status=$st")
            vars["st"] = status
        w = ("WHERE " + " AND ".join(where) + " ") if where else ""
        rows = self._query(
            f"SELECT count() AS n FROM memory_event {w}GROUP ALL", vars)
        return int(rows[0]["n"]) if rows else 0

    def count_failed_memory_events(self, work: str | None = None) -> int:
        """runtime-status 告警口径:仍处 failed 的捕获事件数(工作者失败不阻断对话,但可见)。"""
        where = ["status='failed'"]
        vars: dict = {}
        if work:
            where.append("work=$w")
            vars["w"] = work
        rows = self._query(
            f"SELECT count() AS n FROM memory_event WHERE {' AND '.join(where)} GROUP ALL", vars)
        return int(rows[0]["n"]) if rows else 0

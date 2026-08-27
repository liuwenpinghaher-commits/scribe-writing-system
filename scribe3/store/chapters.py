"""SurrealStore mixin: chapters."""
from __future__ import annotations

import logging

from scribe3.store.core_preamble import *  # noqa: F403

_log = logging.getLogger(__name__)
from scribe3.chapter_meta_codec import (  # noqa: F401
    CHAPTER_JSON_LIST_META_KEYS,
    CHAPTER_JSON_META_KEYS,
    CHAPTER_META_ALLOWED,
    coerce_chapter_json_dict,
    coerce_chapter_json_list,
    dump_chapter_json_meta,
)


def _deduce_for_ui(deduce: dict) -> tuple[list[dict], list[dict]]:
    mapped: list[dict] = []
    chars: list[dict] = []
    for c in deduce.get("characters") or []:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "").strip()
        if not cid:
            continue
        prose = "\n".join([
            f"看到/听到：{c.get('perceived') or ''}",
            f"知道：{c.get('known') or ''}",
            f"以为：{c.get('believed') or ''}",
            f"做了/说了：{c.get('acted') or ''}",
            f"没察觉：{c.get('blind') or ''}",
        ])
        mapped.append({"character_id": cid, "character_name": cid, "prose": prose})
        chars.append({"id": cid, "name": cid})
    return mapped, chars


class ChaptersMixin:

    def purge_ingest(self, seq: int, *, _qstats: dict | None = None) -> None:
        """删除某章 ingest 产出的命题 + knows 边 + reader_knows 边 + char_state(幂等再 ingest 的前置清理)。
        只清 ingest_seq=seq,作者直编/种子(ingest_seq=NONE)不动。

        learned 跨章复用保护:删命题前检查是否有【他章】的 knows/reader_knows 边仍引用该命题
        (ingest_seq != seq)。有则保留命题本身,只删本章的边——防止 B 章复用 A 章命题,
        重 ingest A 时把命题删掉导致 B 的 knows 边悬空。

        EH-03 / PR-EH-1：命题路径集合化（对 N 斜率 0），禁止 per-prop existence/count。
        ``_qstats`` 可选：``{"prop_path": 0, "total": 0}`` 供单测统计 round-trip。
        """
        def _q(sql, vars=None):
            if _qstats is not None:
                _qstats["total"] = int(_qstats.get("total") or 0) + 1
            return self._query(sql, vars or {})

        def _w(sql, vars=None):
            if _qstats is not None:
                _qstats["total"] = int(_qstats.get("total") or 0) + 1
            self._execute_write(sql, vars or {})

        # 1. 先删本章的 knows / reader_knows 边(无论命题是否保留)
        _w("DELETE knows WHERE ingest_seq = $seq", {"seq": seq})
        _w("DELETE reader_knows WHERE ingest_seq = $seq", {"seq": seq})

        # 2. 命题路径（集合化，O(1) 次查询 vs N）
        # 2a. 本章全部命题 id
        if _qstats is not None:
            _qstats["prop_path"] = int(_qstats.get("prop_path") or 0) + 1
        own_props = _q(
            "SELECT meta::id(id) AS local FROM proposition WHERE ingest_seq = $seq",
            {"seq": seq})
        own: set[str] = {
            str(r["local"]) for r in (own_props or []) if r.get("local") is not None
        }
        if own:
            # 2b. 他章 knows 引用的命题 local（一次扫）
            if _qstats is not None:
                _qstats["prop_path"] = int(_qstats.get("prop_path") or 0) + 1
            kept_knows_rows = _q(
                "SELECT meta::id(out) AS local FROM knows WHERE ingest_seq != $seq",
                {"seq": seq})
            kept: set[str] = {
                str(r["local"]) for r in (kept_knows_rows or [])
                if r.get("local") is not None and str(r["local"]) in own
            }
            # 2c. 他章 reader_knows 引用（一次扫 + fact: 剥前缀）
            if _qstats is not None:
                _qstats["prop_path"] = int(_qstats.get("prop_path") or 0) + 1
            kept_rk_rows = _q(
                "SELECT proposition FROM reader_knows WHERE ingest_seq != $seq",
                {"seq": seq})
            for r in kept_rk_rows or []:
                pref = r.get("proposition")
                if pref is None:
                    continue
                ps = str(pref)
                pl = ps.split(":", 1)[-1] if ":" in ps else ps
                if pl in own:
                    kept.add(pl)
            # 2d. 批量删无他章引用的本章命题
            to_del = sorted(own - kept)
            if to_del:
                if _qstats is not None:
                    _qstats["prop_path"] = int(_qstats.get("prop_path") or 0) + 1
                # Surreal：按 local id 列表删（单条，非 per-prop 循环 count）
                _w(
                    "DELETE proposition WHERE ingest_seq = $seq AND "
                    "meta::id(id) IN $locals",
                    {"seq": seq, "locals": to_del},
                )

        # 3. char_state 无跨章复用问题,直接清
        _w("DELETE char_state WHERE ingest_seq = $seq", {"seq": seq})
        # 4. P2-a Fix5: 清本章 ingest_unverified 记录——重 ingest 时防止累积重复 pending。
        # 审计 C-3:只清 pending——accepted/ignored 是人的决策,re-ingest 不得抹掉
        _w("DELETE ingest_unverified WHERE seq = $seq AND status = 'pending'",
           {"seq": seq})
        # 审计 C-2:ingest 路径产的 voice_evolution_flag 同步幂等清除(re-ingest 防累积);
        _w("DELETE voice_evolution_flag WHERE ingest_seq = $seq", {"seq": seq})
        # 5. 母题章实例:随本章 ingest 幂等清除
        _w("DELETE motif_instance WHERE ingest_seq = $seq", {"seq": seq})
        # 6. 伏笔章触及:随本章 ingest 幂等清除(手动登记 ingest_seq=NONE 不受影响)
        _w("DELETE promise_touch WHERE ingest_seq = $seq", {"seq": seq})
        # 6b. 关系触碰按 chapter 清除
        _w("DELETE relation_touch WHERE chapter = $seq", {"seq": seq})
        # 7. 事件图:先取 ids 再删边+本体
        ev_ids = _q("SELECT VALUE id FROM event WHERE ingest_seq = $seq", {"seq": seq})
        if ev_ids:
            _w("DELETE involves WHERE in IN $ids", {"ids": ev_ids})
            _w("DELETE causes WHERE in IN $ids", {"ids": ev_ids})
            _w("DELETE causal WHERE in IN $ids OR out IN $ids", {"ids": ev_ids})
            _w("DELETE event WHERE ingest_seq = $seq", {"seq": seq})
            self._invalidate_chapter_quality_cache(seq)

    def chapter_recall(self, query: str, k: int = 5) -> list[dict]:
        """章节语义召回:按标题+正文首段向量匹配相似章。"""
        from scribe3.embed import embed
        qv = embed([query])[0]
        rows = self._query(
            f"SELECT seq, title, vector::distance::knn() AS dist "
            f"FROM chapter WHERE embedding <|{int(k)},{max(40, int(k))}|> $qv ORDER BY dist",
            {"qv": qv})   # D-022:EF 形式走 HNSW,显式 COSINE 是暴力扫描
        return [{"seq": r["seq"], "title": r.get("title", ""), "distance": r["dist"]} for r in rows]

    def _invalidate_chapter_quality_cache(self, seq: int | None) -> None:
        """事件图变动后令对应章节的派生质量缓存失效；正文与正典数据不受影响。"""
        if seq is None:
            return
        self._execute_write(
            "UPDATE type::record('chapter',$seq) SET qc_cache_revision=NONE",
            {"seq": int(seq)})

    def material_refs_by_chapter(self, chapter) -> list[dict]:
        return self._query(
            "SELECT material_id, chapter, dimension, reason, via FROM material_reference "
            "WHERE chapter=$c", {"c": int(chapter)})

    def _compute_chapter_caches(self, seq: int, prose: str) -> dict:
        """算章级缓存,返回 {scene_count, scene_meta, qc_issues, qc_causal, qc_breakdown}。
        供 save_chapter 落库 + backfill 回填复用。纯计算,不写库。
        - 场景:_split_scenes(prose) → scene_count + [{title, char_count}, ...](序列化为 JSON 串)。
        - QC问题:critique.quality_flags(prose) → PRODUCT_QC_LIST_KEYS 计数之和
          （纯文本；含 god_view/degeneration/filler/rule_of_three）；拆分存 qc_breakdown JSON。
        - 因果违规:verify.causal_complete(self, seq) 违规条数(查该章事件图,O(本章事件))。
          事件图变更后由 refresh_chapter_cache() 重算；质量面板用版本戳标识未刷新缓存。
        """
        import json
        scenes = _split_scenes(prose)
        scene_meta = json.dumps(
            [{"title": s["title"], "char_count": s["chars"]} for s in scenes],
            ensure_ascii=False)
        from scribe3.critique import quality_flags
        from scribe3.qc_product_keys import product_qc_breakdown_from_flags, product_qc_total
        qf = quality_flags(prose)
        breakdown = product_qc_breakdown_from_flags(qf)
        qc_n = product_qc_total(breakdown)
        try:
            from scribe3.verify import causal_complete
            # 批D P1-5 假绿止血:本章无落库事件时写 -1 哨兵(无事件数据),
            # 区分'因果完整=0'与'根本没有事件可校验'——防空事件图恒返 0 被读作真绿。
            if not self.events_at(seq):
                qc_causal_n = -1
            else:
                qc_causal_n = len(causal_complete(self, seq))
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "qc_causal 计算失败(降级为 0): %s", _e)
            qc_causal_n = 0
        return {"scene_count": len(scenes), "scene_meta": scene_meta,
                "qc_issues": qc_n, "qc_causal": qc_causal_n,
                "qc_breakdown": json.dumps(breakdown, ensure_ascii=False),
                # 内存透传(不落章表):scorecard 复用同一份 quality_flags,免重算(北极星任务3)
                "_quality_flags": qf}

    def refresh_chapter_cache(self, seq: int) -> bool:
        """只刷新一章的派生缓存，不改正文、版本或任何正典/事件数据。"""
        rows = self._query(
            "SELECT prose FROM type::record('chapter', $seq)", {"seq": seq})
        prose = (rows[0].get("prose") if rows else "") or ""
        if not prose.strip():
            return False
        cache = self._compute_chapter_caches(seq, prose)
        self._execute_write(
            "UPDATE type::record('chapter', $seq) SET "
            "scene_count=$scn, scene_meta=$scm, qc_issues=$qc, qc_causal=$qcc, "
            "qc_breakdown=$qcb, qc_cache_revision=$qcr RETURN NONE",
            {"seq": seq, "scn": cache["scene_count"], "scm": cache["scene_meta"],
             "qc": cache["qc_issues"], "qcc": cache["qc_causal"],
             "qcb": cache["qc_breakdown"], "qcr": QUALITY_CACHE_REVISION})
        return True

    def get_chapter_scorecard(self, seq: int) -> dict | None:
        """读章 scorecard;缓存行缺失(旧库章)→ 现算回填(lazy backfill)。
        章不存在或无正文 → None(端点侧 404)。"""
        import json
        rows = self._query(
            "SELECT seq, constraints, advisory, fulfillment, degraded, "
            "(IF computed_at IS NONE THEN NONE ELSE <string>computed_at END) AS computed_at "
            "FROM type::record('chapter_scorecard',$s)", {"s": seq})
        if rows:
            r = rows[0]
            return {"seq": seq,
                    "constraints": json.loads(r.get("constraints") or "{}"),
                    "advisory_scores": json.loads(r.get("advisory") or "{}"),
                    "fulfillment": json.loads(r.get("fulfillment") or "{}"),
                    "degraded": json.loads(r.get("degraded") or "[]"),
                    "computed_at": r.get("computed_at")}
        ch = self.get_chapter(seq)
        if not ch or not (ch.get("prose") or "").strip():
            return None
        sc = self._compute_scorecard(seq, ch["prose"], ch.get("focalizer"))
        try:
            self._upsert_scorecard(sc)
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "scorecard lazy 回填落库失败(返回现算结果): %s", _e)
        return sc

    def save_chapter(self, seq: int, prose: str, title: str = "", focalizer: str | None = None,
                     _today: str | None = None, expected_version: int | None = None) -> None:
        """落/覆盖某章正文(UPSERT)。附带章向量 + QC缓存(字数,不再全拉正文统计)。
        _today:测试时注入固定日期字符串(YYYY-MM-DD),生产不传。
        expected_version: MAN-02 乐观锁，不匹配则 ValueError(chapter_conflict)。
        带 expected_version 时用 UPDATE … WHERE rev=$expected 原子递增，避免双读竞态。"""
        # 审计 E-1:embedding 是召回辅助不是正文,故障绝不拖死存稿(命门 fail-soft)。
        try:
            from scribe3.prose_sanitize import sanitize_for_persist, fill_placeholder_title, visible_length
            _san = sanitize_for_persist(prose or "")
            prose = _san.get("prose") or prose
            existing: dict = {}
            try:
                existing = self.get_chapter(seq) or {}
            except Exception:
                existing = {}
            _syn = str(existing.get("synopsis") or "")
            title = fill_placeholder_title(title or "", _syn, seq)
            if not str(title or "").strip():
                title = str(existing.get("title") or "")
            wc = visible_length(prose)
        except Exception:
            wc = len("".join((prose or "").split()))
        text_for_embed = f"{title} {prose[:200]}".strip()
        try:
            from scribe3.embed import embed
            vec = embed([text_for_embed])[0]
            # HNSW DIMENSION 512:错误维度会让后续 UPDATE 整段炸(Surreal InternalError)
            if not isinstance(vec, (list, tuple)) or len(vec) != 512:
                logging.getLogger("scribe3.store").warning(
                    "save_chapter embedding 维度异常 len=%s,跳过向量",
                    len(vec) if hasattr(vec, "__len__") else type(vec))
                vec = None
        except Exception as _ee:
            logging.getLogger("scribe3.store").warning(
                "save_chapter embedding 失败(正文照存,该章暂无语义召回向量): %s", _ee)
            vec = None
        # 千万字缓存(Phase0-BE1):落库时算好场景切分 + QC 计数,聚合端点不再全表拉正文/重算。
        cache = self._compute_chapter_caches(seq, prose)
        payload = {
            "seq": seq, "title": title, "foc": focalizer, "prose": prose, "v": vec, "wc": wc,
            "scn": cache["scene_count"], "scm": cache["scene_meta"], "qc": cache["qc_issues"],
            "qcc": cache["qc_causal"], "qcb": cache["qc_breakdown"],
            "qcr": QUALITY_CACHE_REVISION,
        }
        sets = (
            "seq=$seq, title=$title, focalizer=$foc, prose=$prose, embedding=$v, "
            "qc_word_count=$wc, scene_count=$scn, scene_meta=$scm, qc_issues=$qc, "
            "qc_causal=$qcc, qc_breakdown=$qcb, qc_cache_revision=$qcr, "
            "post_analysis_cache=NONE, post_analysis_fp=NONE, post_analysis_at=NONE, "
            "ingest_prose_fp=NONE, archived=false, archived_at=NONE, archive_reason=NONE"
        )
        # B-02：单条 UPDATE … WHERE rev=$expected 原子递增，消灭双读 TOCTOU。
        if expected_version is not None:
            payload["expected"] = int(expected_version)
            rows = self._query(
                f"UPDATE chapter SET {sets}, rev=rev+1, updated=time::now() "
                f"WHERE seq=$seq AND rev=$expected RETURN AFTER",
                payload,
            ) or []
            if not rows:
                if int(expected_version) == 0 and not (self.get_chapter(seq) or {}):
                    self._execute_write(
                        f"UPSERT type::record('chapter',$seq) SET {sets}, rev=1 RETURN NONE",
                        payload,
                    )
                else:
                    raise ValueError("chapter_conflict")
        else:
            rows = self._query(
                f"UPDATE type::record('chapter',$seq) SET {sets}, "
                f"rev=(rev OR 0)+1, updated=time::now() RETURN AFTER",
                payload,
            ) or []
            if not rows:
                self._execute_write(
                    f"UPSERT type::record('chapter',$seq) SET {sets}, rev=1 RETURN NONE",
                    payload,
                )
        try:
            from scribe3.quality.cache import invalidate_quality_cache
            invalidate_quality_cache(getattr(self, "db_name", None))
        except Exception:
            pass
        # 北极星任务3:章级 scorecard 存稿即算(独立缓存表,D-008)——fail-soft,
        # scorecard 是面板不是命门,失败只告警绝不阻断存稿。
        try:
            self._upsert_scorecard(self._compute_scorecard(
                seq, prose, focalizer, precomputed_flags=cache.get("_quality_flags")))
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "chapter_scorecard 计算/落库失败(存稿不受影响): %s", _e)
        # 北极星任务9:QD 文体档案存稿即算(纯确定性,fail-soft)。
        try:
            from scribe3.qd import chapter_style_profile
            self._upsert_style_profile(seq, chapter_style_profile(prose, focalizer))
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "style_profile 计算/落库失败(存稿不受影响): %s", _e)
        # S-2：章正文写 → 真表 CDC + cache_watch 双写（LIVE/缓存）
        _emit_cache_invalidation("chapter", getattr(self, "db_name", None), store=self)
        # fail-soft:记账失败绝不阻断存稿(统计是锦上添花,存稿是命门)
        try:
            self._record_daily_progress(seq, today=_today)
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "_record_daily_progress 失败(记账跳过,存稿不受影响): %s", _e)
        # 余烬：正文尾巴写入 narrative_drive.end_hook，下章 story_ember 必吃。
        try:
            from scribe3.narrative_drive import extract_end_hook_from_prose, merge_end_hook
            cur0 = self.get_chapter(seq) or {}
            spine = cur0.get("chapter_spine") if isinstance(cur0.get("chapter_spine"), dict) else {}
            hook = str((spine or {}).get("hook") or "").strip() or extract_end_hook_from_prose(prose)
            if hook:
                cur = self.get_chapter(seq) or {}
                drive = cur.get("narrative_drive") if isinstance(cur.get("narrative_drive"), dict) else {}
                nxt = merge_end_hook(drive, hook)
                if (nxt.get("end_hook") or "") != (drive.get("end_hook") or ""):
                    self.update_chapter_meta(seq, {"narrative_drive": nxt})
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "end_hook 回填失败(存稿不受影响): %s", _e)
    def add_chapter_version(self, seq: int, prose: str, label: str = "",
                            kind: str = "checkpoint", qc: dict | None = None,
                            stage: str = "final", summary: str = "",
                            stats: dict | None = None) -> str:
        """记一个存档点。返回新版本的裸 id。
        Phase0-BE2:扩 stage('draft'|'final')/ summary / stats(JSON 串绕嵌套 schema)。
        向后兼容:旧调用不传 stage → 默认 'final';stats 不传 → 不写(列为 NONE)。
        """
        import json
        stats_str = json.dumps(stats, ensure_ascii=False) if stats is not None else None
        rows = self._query(
            "CREATE chapter_version SET seq=$seq, prose=$prose, label=$label, "
            "kind=$kind, qc=$qc, stage=$stage, summary=$summary, stats=$stats, "
            "created_at=time::now()",
            {"seq": seq, "prose": prose, "label": label, "kind": kind, "qc": qc or {},
             "stage": stage, "summary": summary, "stats": stats_str})
        # CREATE 返回新记录(含 id,形如 'chapter_version:xxxx');取裸 id 部分。
        rid = rows[0]["id"] if rows else None
        vid = str(rid).split(":")[-1] if rid else ""
        try:
            self.prune_chapter_versions(seq)
        except Exception as _e:
            logging.getLogger("scribe3.store").warning(
                "chapter_version 保留策略失败(新版本已写入): %s", _e)
        return vid

    def list_chapter_versions(self, seq: int, *, limit: int | None = 100,
                              offset: int = 0) -> list[dict]:
        """某章存档点列表(不含 prose 全文),最新在前。
        stage 缺失(旧版本)降级为 'final'(向后兼容)。MAN-01：默认分页。"""
        q = (
            "SELECT meta::id(id) AS id, seq, label, kind, qc, "
            "stage, summary, stats, created_at "
            "FROM chapter_version WHERE seq=$seq ORDER BY created_at DESC"
        )
        params: dict = {"seq": seq}
        if limit is not None:
            q += " LIMIT $limit START $offset"
            params["limit"] = max(1, int(limit))
            params["offset"] = max(0, int(offset))
        rows = self._query(q, params) or []
        for r in rows:
            if not r.get("stage"):
                r["stage"] = "final"
            r.setdefault("summary", "")
        return rows

    def prune_chapter_versions(self, seq: int, *, keep_recent: int = 20) -> dict:
        """MAN-01：保留最近 N 条 + 里程碑/引用，删掉其余。"""
        from scribe3.chapter_versions import select_versions_to_drop
        rows = self.list_chapter_versions(seq, limit=10000, offset=0)
        drop = select_versions_to_drop(rows, keep_recent=keep_recent)
        if not drop:
            return {"dropped": 0, "kept": len(rows)}
        drop_ids = {str(r.get("id") or "") for r in drop}
        keep_ids = [str(r.get("id") or "") for r in rows if str(r.get("id") or "") not in drop_ids]
        self._execute_write(
            "DELETE chapter_version WHERE seq=$seq AND meta::id(id) NOT IN $keep_ids",
            {"seq": seq, "keep_ids": keep_ids},
        )
        return {"dropped": len(drop), "kept": len(rows) - len(drop)}

    def get_chapter_version(self, vid: str) -> dict | None:
        """单个存档点全文(回看用)。"""
        rows = self._query(
            "SELECT meta::id(id) AS id, seq, prose, label, kind, qc, "
            "stage, summary, stats, created_at "
            "FROM type::record('chapter_version', $vid)", {"vid": vid})
        if not rows:
            return None
        r = rows[0]
        if not r.get("stage"):
            r["stage"] = "final"
        r.setdefault("summary", "")
        return r

    def save_chapter_draft(self, seq: int, draft: str) -> None:
        """落/覆盖某章草稿(与定稿 prose 分离;UPSERT 不碰 prose/embedding/qc)。
        刷新恢复读 chapter.draft(最新草稿);留版另走 add_chapter_version(stage='draft')。
        147 已删 chapter.draft：失败时改走 chapter_version，不挡排演冻结。"""
        try:
            self._execute_write(
                "UPSERT type::record('chapter',$seq) SET seq=$seq, draft=$draft RETURN NONE",
                {"seq": seq, "draft": draft})
        except Exception:
            self.add_chapter_version(
                seq, draft, label="chapter-draft",
                kind="checkpoint", stage="draft",
                summary="chapter.draft 字段已删，改留版",
            )

    def set_craft_compliance(self, seq: int, report: dict | None) -> None:
        """P2：落 C-Det / 工艺合规摘要（JSON 串；fail-soft 由调用方捕获）。"""
        import json
        payload = report if isinstance(report, dict) else {}
        try:
            raw = json.dumps(payload, ensure_ascii=False)
        except Exception:
            raw = "{}"
        self._execute_write(
            "UPDATE type::record('chapter', $seq) SET "
            "craft_compliance=$c, craft_compliance_at=time::now() RETURN NONE",
            {"seq": int(seq), "c": raw},
        )

    def get_chapter(self, seq: int) -> dict | None:
        """单章身份 + 四阶段内容(synopsis/beats/draft/prose)。
        beats 存为 JSON 串,读时解析为 list;缺失降级为 []。"""
        # SurrealDB 2.1: bare ``<string> optional_field`` InternalError when field is NONE;
        # cast only when present. type::record (not type::record) for two-arg record ids.
        sql_full = (
            "SELECT seq,title,label,(IF volume THEN meta::id(volume) ELSE NONE END) AS volume,"
            "focalizer,prose,synopsis,"
            "outline_status,outline_rev,confidence,settled_note,"
            "scene_truth_revision,involved_characters,purpose_text,deltas,"
            "pressure_drive,narrative_drive,narrative_contract,"
            "prose_lock,play_sha,contract_sha,playbook_version,"
            "reveal_secret_ids,"
            "archived,"
            "(IF archived_at IS NONE THEN NONE ELSE <string>archived_at END) AS archived_at,"
            "archive_reason,"
            "ingest_status,ingest_message,ingest_prose_fp "
            "FROM type::record('chapter',$seq)"
        )
        rows = self._query(sql_full, {"seq": seq})
        if not rows:
            return None
        r = rows[0]
        if "ingest_message" not in r or not r["ingest_message"]:
            _log.debug("get_chapter seq=%s: ingest_message missing, defaulting to empty", seq)
            r["ingest_message"] = ""
        r["beats"] = []
        r["draft"] = ""
        r["chapter_spine"] = {}
        r["beats_meta"] = {}
        r["deductions"] = []
        r["scene_truth"] = ""
        for _k in ("involved_characters", "deltas"):
            raw = r.get(_k)
            try:
                r[_k] = json.loads(raw) if raw else []
            except (ValueError, TypeError):
                r[_k] = []
        # pressure_drive 保持 str 或 None；dict 已是解析结果则原样
        pd = r.get("pressure_drive")
        if pd is not None and not isinstance(pd, (str, dict)):
            r["pressure_drive"] = str(pd)
        r["narrative_drive"] = coerce_chapter_json_dict(r.get("narrative_drive"))
        r["narrative_contract"] = coerce_chapter_json_dict(r.get("narrative_contract"))
        r["prose_lock"] = bool(r.get("prose_lock"))
        r["reveal_secret_ids"] = coerce_chapter_json_list(r.get("reveal_secret_ids"))
        try:
            r["scene_truth_revision"] = max(0, int(r.get("scene_truth_revision") or 0))
        except (TypeError, ValueError):
            r["scene_truth_revision"] = 0
        r["archived"] = bool(r.get("archived"))
        r["archive_reason"] = r.get("archive_reason") or ""
        # 章后统一分析摘要（不回传大 JSON）
        try:
            r["post_analysis"] = self.post_analysis_summary(int(seq), r.get("prose") or "")
        except Exception:
            r["post_analysis"] = None
        if hasattr(self, "get_frozen"):
            try:
                play = self.get_frozen("chapter_play", int(seq))
            except Exception:
                play = None
            if play:
                r["play_sha"] = play.get("sha") or r.get("play_sha")
                r["play"] = play.get("text") or ""
            try:
                contract = self.get_frozen("chapter_contract", int(seq))
            except Exception:
                contract = None
            if contract:
                r["contract_sha"] = contract.get("sha") or r.get("contract_sha")
                r["contract"] = contract
            try:
                deduce = self.get_frozen("chapter_deduce", int(seq))
            except Exception:
                deduce = None
            if deduce:
                r["deduce"] = deduce
                r["scene_truth"] = deduce.get("scene_truth") or ""
                mapped, chars = _deduce_for_ui(deduce)
                r["deductions"] = mapped
                r["chars"] = chars
        return r

    def list_chapters(self) -> list[dict]:
        return self._query(
            "SELECT seq,title FROM chapter:.. "
            "WHERE archived = NONE OR archived != true ORDER BY seq")

    def chapter_seqs_in_range(self, start_seq: int, end_seq: int) -> list[int]:
        """闭区间读取已存章节号;不过滤归档章,供 pilot 判定 record 是否存在。"""
        target = _chapter_range_target(start_seq, end_seq)
        rows = self._query(f"SELECT seq FROM {target} ORDER BY seq")
        return [int(row["seq"]) for row in rows if row.get("seq") is not None]

    def chapters_lite(self) -> list[dict]:
        """遗留处置 2-D(#5):书级面板窄查询——一次拉草料/目的字段,不拉 prose/embedding
        (north_star_book 原逐章 get_chapter 全行,几百章时既慢又占内存)。缺失字段补 None,
        调用方不必区分"无键"与"空值"。"""
        sql = (
            "SELECT seq, title, synopsis, deltas, "
            "(IF volume THEN meta::id(volume) ELSE NONE END) AS volume, focalizer "
            "FROM chapter:.. "
            "WHERE archived = NONE OR archived != true ORDER BY seq"
        )
        sql_flags = (
            "SELECT seq, title, synopsis, deltas, "
            "(IF volume THEN meta::id(volume) ELSE NONE END) AS volume, focalizer, "
            "(IF prose IS NONE OR prose = '' THEN false ELSE true END) AS has_prose "
            "FROM chapter:.. "
            "WHERE archived = NONE OR archived != true ORDER BY seq"
        )
        try:
            rows = self._query(sql_flags)
        except Exception:
            try:
                rows = self._query(sql)
            except Exception:
                rows = self._query(
                    "SELECT seq, title, synopsis, deltas FROM chapter:.. "
                    "WHERE archived = NONE OR archived != true ORDER BY seq"
                )
        for r in rows:
            for k in ("title", "synopsis", "deltas", "volume", "focalizer"):
                r.setdefault(k, None)
            r.setdefault("beats", None)
            r.setdefault("scene_truth", None)
            if "has_prose" in r:
                r["has_prose"] = bool(r.get("has_prose"))
            r["has_draft"] = False
        return rows

    def recent_proses(self, before_seq: int, k: int = 5) -> list[dict]:
        """before_seq 之前最近 k 章的 {seq, prose}(按 seq 升序)。
        供跨章复读检测与"前文已用措辞→生成时避免"清单复用。"""
        target = _chapter_range_target(end=before_seq, end_inclusive=False)
        rows = self._query(
            f"SELECT seq, prose FROM {target} "
            "WHERE archived = NONE OR archived != true "
            "ORDER BY seq DESC LIMIT $k", {"k": k})
        return list(reversed(rows))

    def chapter_count(self) -> int:
        """已有章节条数（含未归档）。开写门槛用来判断是不是旧书。"""
        try:
            rows = self._query(
                "SELECT count() AS n FROM chapter "
                "WHERE archived = NONE OR archived != true GROUP ALL"
            ) or []
            if rows and rows[0].get("n") is not None:
                return int(rows[0]["n"])
        except Exception:
            pass
        try:
            return int(self.max_chapter() or 0)
        except Exception:
            return 0

    def max_chapter(self) -> int:
        """书的最大章号:以 chapter 表实际章节为准(真实范围),并入 event 的 story_chapter 兜底。
        旧实现只数 event 表 → 仅有伏笔/章节而无事件时返回 0,使时间线/体检整体短路为空(真bug)。"""
        ch_rows = self._query("SELECT seq FROM chapter:..")
        seqs = [r["seq"] for r in (ch_rows or []) if r.get("seq") is not None]
        ev_rows = self._query("SELECT story_chapter AS ch FROM event")
        evs = [r["ch"] for r in (ev_rows or []) if r.get("ch") is not None]
        allv = seqs + evs
        return int(max(allv)) if allv else 0

    def _ev_chapter_map(self) -> dict[str, int]:
        """批量查所有事件的 id→story_chapter 映射,供 timeline() 用于 causal_in 章号补全。
        一次 SQL 全表扫,O(N) 内存,避免逐 causal_in 单独查库。"""
        rows = self._query("SELECT meta::id(id) AS local, story_chapter FROM event")
        return {f"ev:{r['local']}": r["story_chapter"] for r in rows if r.get("story_chapter") is not None}

    def latest_version_prose(self, seq: int, kind: str) -> str | None:
        """某章某 kind 最新版本的正文(审计 P2-1:final 版同稿去重的比对源)。"""
        rows = self._query(
            "SELECT prose, created_at FROM chapter_version WHERE seq=$s AND kind=$k "
            "ORDER BY created_at DESC LIMIT 1", {"s": seq, "k": kind})
        return rows[0].get("prose") if rows else None

    def validate_cross_chapter_consistency(self) -> list[dict]:
        """跨章一致性检测(带指纹缓存壳)。审计 P2-13:每次 /post-check 全书扫太贵,
        以 (章数, Σqc_word_count) 为指纹——正文未变直接回缓存;指纹是弱哈希
        (同字数改动漏检),一致性 hint 是 advisory 级,可接受,存稿即失效重扫。"""
        count_rows = self._query("SELECT count() AS n FROM chapter GROUP ALL")
        word_rows = self._query(
            "SELECT math::sum(qc_word_count) AS w FROM chapter GROUP ALL")
        fp = (((count_rows[0].get("n") if count_rows else 0) or 0),
              ((word_rows[0].get("w") if word_rows else 0) or 0))
        cached = getattr(self, "_cc_cache", None)
        if cached and cached[0] == fp:
            return cached[1]
        hints = self._validate_cross_chapter_impl()
        self._cc_cache = (fp, hints)
        return hints

    def _validate_cross_chapter_impl(self) -> list[dict]:
        """跨章一致性检测(全书扫描)。

        返回 hint 列表(与 validate_setting 同结构),包含:
          (a) numeric_inconsistency —— 同一专名实体在不同章绑定不同数字(如「潭家二十七口」vs「潭家三百一十七口」)
          (b) unregistered_name     —— 高频疑似专名(≥3次)但未在 characters/terms/factions/items 中登记

        不修改任何状态,可安全重复调用。向后兼容:不影响原 validate_setting 签名。
        """
        import re

        hints: list[dict] = []

        # ── 收集全书章正文 ──────────────────────────────────────────────────
        chapters = self._query("SELECT seq, prose FROM chapter:.. ORDER BY seq")
        chapters = [c for c in chapters if c.get("prose")]
        if not chapters:
            return hints

        # ── 构建已登记专名集合(同 validate_setting §4 段) ─────────────────
        known_names: set[str] = set()
        for c in self.characters():
            known_names.add(c.name)
            known_names.update(c.traits.get("aliases") or [])
        for term in self.list_terms():
            known_names.add(term["name"])
            known_names.update(term.get("aliases") or [])
        for it in self.list_items():
            known_names.add(it["name"])
        for pl in self._query("SELECT name FROM place"):
            known_names.add(pl.get("name", ""))
        for fc in self.list_factions():
            known_names.add(fc["name"])
            # faction.aliases:疑似死(P2-15)——faction 无 aliases schema/写入路径(add_faction 不写),
            #   此 get 恒空,为前瞻性防御读;isinstance 守卫使其无害,保留守卫待确认。
            known_names.update(fc.get("aliases") or [] if isinstance(fc.get("aliases"), list) else [])
        known_names.discard("")

        # ── (a) 数字声明矛盾检测 ────────────────────────────────────────────
        # 策略:抽取「<专名>…<数字><量词单位>」三元组,
        #       只有【同一专名 + 同一量词单位 + 不同数字】才报 numeric_inconsistency。
        # 量词单位取数字紧跟的1-2字(须在已定义单位集内);否则单位为空串""。
        # 这样 "三十出头"(单位"") 与 "二十年前"(单位"年") 单位不同,不报矛盾。
        _HANZI_DIGITS = "零一二三四五六七八九十百千万亿两"
        _NUM_PAT = rf"[{_HANZI_DIGITS}]+|\d+"
        # 标准量词集合:实物计量单位
        _UNITS: set[str] = {
            "口", "枚", "颗", "人", "名", "位", "座", "条", "件", "个",
            "匹", "张", "把", "支", "根", "块", "面", "载", "年", "日",
            "月", "天", "两", "石", "斤", "尺", "丈", "里", "里",
        }
        # 2字复合量词(精确匹配优先于1字)
        _UNITS2: set[str] = {"年前", "年后", "天前", "天后", "日前", "日后"}

        def _extract_unit(text_after_num: str) -> str:
            """从数字后面的文本提取量词单位(1-2字);不在单位集内则返回空串。"""
            if not text_after_num:
                return ""
            # 优先尝试2字复合量词
            two = text_after_num[:2] if len(text_after_num) >= 2 else ""
            if two in _UNITS2:
                return two
            # 再尝试1字
            one = text_after_num[0] if text_after_num else ""
            if one in _UNITS:
                return one
            return ""

        # entity_nums: {entity_name: [(chapter_seq, number_str, unit_str, snippet), ...]}
        entity_nums: dict[str, list[tuple[int, str, str, str]]] = {}

        for ch in chapters:
            seq = ch["seq"]
            prose = ch["prose"]
            for name in known_names:
                if not name or name not in prose:
                    continue
                for m in re.finditer(re.escape(name), prose):
                    # 取专名右侧30字内的数字
                    window = prose[m.end(): m.end() + 30]
                    num_m = re.search(_NUM_PAT, window)
                    if num_m:
                        num_str = num_m.group()
                        # 过滤纯单字汉字数字「一」「二」等噪声(需≥2字或为阿拉伯数字)
                        if len(num_str) < 2 and not num_str.isdigit():
                            continue
                        # 提取数字后面的量词单位
                        after_num = window[num_m.end():]
                        unit = _extract_unit(after_num)
                        snippet = prose[max(0, m.start() - 2): m.end() + num_m.end() + 4]
                        entity_nums.setdefault(name, []).append((seq, num_str, unit, snippet))

        for name, occurrences in entity_nums.items():
            if len(occurrences) < 2:
                continue
            # 按(量词单位, 数字)聚合:只对同一单位下的不同数字报矛盾
            # unit_seen: {unit_str: {num_str: [(seq, snippet), ...]}}
            unit_seen: dict[str, dict[str, list[tuple[int, str]]]] = {}
            for seq, num_str, unit, snippet in occurrences:
                unit_seen.setdefault(unit, {}).setdefault(num_str, []).append((seq, snippet))

            for unit, num_map in unit_seen.items():
                if len(num_map) < 2:
                    continue  # 同单位下数字都一样,无矛盾
                # 找出现次数最多的两个数字(最典型矛盾对)
                sorted_nums = sorted(num_map.items(), key=lambda x: -len(x[1]))
                num_a, locs_a = sorted_nums[0]
                num_b, locs_b = sorted_nums[1]
                ch_a = locs_a[0][0]
                ch_b = locs_b[0][0]
                snip_a = locs_a[0][1]
                snip_b = locs_b[0][1]
                unit_label = f"(量词:{unit})" if unit else ""
                hints.append({
                    "type": "numeric_inconsistency",
                    "severity": "high",
                    "entity": name,
                    "description": (
                        f"「{name}」数字前后矛盾{unit_label}:"
                        f"第{ch_a}章「{num_a}」vs 第{ch_b}章「{num_b}」"
                    ),
                    "evidence": {
                        f"第{ch_a}章": snip_a,
                        f"第{ch_b}章": snip_b,
                    },
                })

        # ── (b) 未登记高频疑似专名检测(收紧版) ─────────────────────────────
        # 只报【出现≥5次】且【与已知专名共享≥2个连续汉字(含子串)】的词——
        # 疑似命名漂移/别名(如"潭家"已登记但出现"潭家府")。
        # 纯独立新词、常用词、已知专名的纯前/后缀词一律不报。
        # 选择选项A:精准收紧,宁可漏报也不滥报。
        all_prose = "".join(c["prose"] for c in chapters)

        # 提取所有2-4字汉字词组(滑动窗口,排除标点/空格)
        hanzi_only = re.sub(r"[^一-鿿]", " ", all_prose)
        candidate_counts: dict[str, int] = {}
        for length in (2, 3, 4):
            tokens = re.findall(rf"[一-鿿]{{{length}}}", hanzi_only)
            for tok in tokens:
                candidate_counts[tok] = candidate_counts.get(tok, 0) + 1

        # 常见虚词/停用词/助词排除
        _STOPWORDS = {
            "这个", "那个", "什么", "如何", "为何", "因为", "所以", "虽然", "但是",
            "他们", "我们", "你们", "她们", "已经", "可以", "没有", "一个", "一些",
            "这样", "那样", "只是", "还是", "就是", "于是", "不是", "都是", "的是",
            "时候", "地方", "事情", "东西", "问题", "方面", "情况", "之后", "之前",
            "之中", "之间", "之上", "之下", "以上", "以下", "以前", "以后", "一直",
            "一边", "一起", "一般", "一样", "一切", "一定", "一旦", "如此", "这里",
            "那里", "这时", "那时", "其中", "其他", "其实", "不过", "不知", "不得",
            "只有", "只能", "只好", "不禁", "不由", "不觉", "不得不", "不由得",
            "看见", "走过", "想起", "回头", "逃散", "走来", "说道", "点头", "摇头",
            "百姓", "街道", "门楼", "石板", "月光", "夜色", "空院", "往日", "五味",
        }

        reported: set[str] = set()
        for tok, cnt in candidate_counts.items():
            if tok in known_names or tok in _STOPWORDS:
                continue
            if tok in reported:
                continue

            if not known_names:
                # 无已登记专名时:退回原始行为,高频(≥3次)词即报
                if cnt >= 3:
                    hints.append({
                        "type": "unregistered_name",
                        "severity": "low",
                        "entity": tok,
                        "description": (
                            f"「{tok}」全书出现 {cnt} 次但未登记为角色/术语/地点/阵营/物品"
                        ),
                        "evidence": tok,
                    })
                    reported.add(tok)
                continue

            # ── 有已登记专名时:大幅收紧,只报疑似命名漂移 ──────────────────
            # 门槛提高到≥5次
            if cnt < 5:
                continue
            # 排除:tok 是已知专名的直接超集(专名+助词/动词,如"潭家的"、"柳三更走")
            if any(kn in tok for kn in known_names if len(kn) >= 2):
                continue
            # 排除:tok 是已知专名的严格子串(截断词,如"柳三"是"柳三更"的前缀)
            if any(tok in kn for kn in known_names if len(kn) > len(tok)):
                continue
            # 疑似命名漂移:tok 与某已知专名共享≥2个连续汉字但互不包含
            # (如"潭家"已登记,"潭府"出现 → 疑似别名)
            is_derived = any(
                len(kn) >= 2 and any(
                    kn[i:i+2] in tok
                    for i in range(len(kn) - 1)
                )
                for kn in known_names
            )
            if is_derived:
                hints.append({
                    "type": "unregistered_name",
                    "severity": "low",
                    "entity": tok,
                    "description": (
                        f"「{tok}」全书出现 {cnt} 次但未登记为角色/术语/地点/阵营/物品"
                        "(疑似已登记专名的别名/命名漂移)"
                    ),
                    "evidence": tok,
                })
                reported.add(tok)

        return hints

    def add_volume(self, title: str, sort_order: int = 0,
                   intro: str | None = None, color: str | None = None) -> str:
        """新建卷,返回裸 id(SurrealDB 自动生成)。"""
        vid = self._query(
            "CREATE volume CONTENT $c",
            {"c": {"title": title, "sort_order": sort_order,
                   "intro": intro, "color": color}}
        )
        # CREATE 返回 [{"id": RecordID(...), ...}]
        row = vid[0] if vid else {}
        rid = row.get("id")
        if rid is None:
            raise RuntimeError("add_volume: CREATE 未返回 id")
        # RecordID → 裸 id 字符串
        return str(rid).split(":")[-1] if ":" in str(rid) else str(rid)

    def list_volumes(self) -> list[dict]:
        """按 sort_order 升序列所有卷。"""
        try:
            return self._query(
                "SELECT meta::id(id) AS id, title, sort_order, intro, color, charter "
                "FROM volume ORDER BY sort_order")
        except Exception:
            # 旧库没有 168 的 charter 字段
            return self._query(
                "SELECT meta::id(id) AS id, title, sort_order, intro, color "
                "FROM volume ORDER BY sort_order")

    def update_volume(self, vid: str, fields: dict) -> bool:
        """更新卷字段(title/sort_order/intro/color/charter 白名单)。返回 True 若存在,False 若不存在。

        charter 是 168 的卷契约(object)：这一卷引入哪些新实体、收哪几条旧线、
        卷末主角该知道什么。结构与核对见 `scribe3/charter.py`。
        """
        rows = self._query("SELECT id FROM type::record('volume',$vid) LIMIT 1", {"vid": vid})
        if not rows:
            return False
        allowed = {"title", "sort_order", "intro", "color", "charter"}
        payload = {k: v for k, v in fields.items() if k in allowed}
        if not payload:
            return True
        sets = ", ".join(f"{k}=$p_{k}" for k in payload)
        params = {f"p_{k}": v for k, v in payload.items()}
        intro_changed = False
        old_intro = None
        try:
            raw = self._execute_write(
                f"UPDATE type::record('volume', $vid) SET {sets} RETURN BEFORE",
                {"vid": vid, **params},
            )
            before = self._rows_from_write(raw)
            if "intro" in payload:
                try:
                    from scribe3.outline_status import intro_text_changed
                    if before:
                        old_intro = (before[0].get("intro") if isinstance(before[0], dict) else "") or ""
                        intro_changed = intro_text_changed(old_intro, payload.get("intro"))
                    else:
                        intro_changed = True
                except Exception:
                    intro_changed = True
        except Exception:
            self._execute_write(
                f"UPDATE type::record('volume', $vid) SET {sets}",
                {"vid": vid, **params})
            if "intro" in payload:
                intro_changed = True
        if intro_changed:
            try:
                from scribe3.outline_status import mark_volume_intro_changed
                mark_volume_intro_changed(self, vid)
            except Exception:
                pass
        return True

    def cas_refreeze_chapter(self, seq: int) -> dict:
        """只有待核对才冻住并版本+1。已冻着的再调一次不改版本。"""
        n = int(seq)
        raw = self._execute_write(
            "UPDATE type::record('chapter', $seq) SET "
            "outline_status = 'frozen', "
            "outline_rev = (IF outline_rev IS NONE THEN 0 ELSE outline_rev END) + 1 "
            "WHERE outline_status INSIDE ['stale', 'review'] "
            "RETURN seq, outline_status, outline_rev",
            {"seq": n},
        )
        rows = self._rows_from_write(raw)
        if rows:
            _emit_cache_invalidation("chapter", getattr(self, "db_name", None), store=self)
            row = rows[0] if isinstance(rows[0], dict) else {}
            return {
                "ok": True,
                "seq": n,
                "outline_status": str(row.get("outline_status") or "frozen"),
                "outline_rev": int(row.get("outline_rev") or 0),
                "idempotent": False,
            }
        cur = self.get_chapter(n) or {}
        if not cur:
            return {"ok": False, "code": "chapter_missing", "seq": n}
        raw_status = cur.get("outline_status")
        absent = (
            raw_status is None
            or str(raw_status).strip() == ""
            or str(raw_status).strip().upper() == "NONE"
        )
        out = {
            "ok": True,
            "seq": n,
            "outline_status": "" if absent else str(raw_status or "frozen"),
            "outline_rev": int(cur.get("outline_rev") or 0),
            "idempotent": True,
        }
        if absent:
            out["status_absent"] = True
        return out

    def cas_refreeze_volume(self, volume_id: str) -> dict:
        vid = str(volume_id or "").strip()
        raw = self._execute_write(
            "UPDATE chapter SET "
            "outline_status = 'frozen', "
            "outline_rev = (IF outline_rev IS NONE THEN 0 ELSE outline_rev END) + 1 "
            "WHERE volume = type::record('volume', $vid) "
            "AND outline_status INSIDE ['stale', 'review'] "
            "AND (archived = NONE OR archived != true) "
            "RETURN seq, outline_status, outline_rev",
            {"vid": vid},
        )
        rows = self._rows_from_write(raw)
        seqs = []
        results = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            try:
                s = int(r.get("seq") or 0)
            except (TypeError, ValueError):
                continue
            if s <= 0:
                continue
            seqs.append(s)
            results.append({
                "ok": True,
                "seq": s,
                "outline_status": str(r.get("outline_status") or "frozen"),
                "outline_rev": int(r.get("outline_rev") or 0),
                "idempotent": False,
            })
        if seqs:
            _emit_cache_invalidation("chapter", getattr(self, "db_name", None), store=self)
        return {
            "ok": True,
            "volume_id": vid,
            "seqs": seqs,
            "results": results,
            "n": len(results),
        }

    def delete_volume(self, vid: str) -> bool:
        """删卷:先把该卷下所有章的 volume 置 NONE(不删章),再删卷记录。返回 True 若存在并删除,False 若不存在。"""
        rows = self._query("SELECT id FROM type::record('volume',$vid) LIMIT 1", {"vid": vid})
        if not rows:
            return False
        self._execute_write(
            "UPDATE chapter SET volume = NONE WHERE volume = type::record('volume', $vid)",
            {"vid": vid})
        self._execute_write(
            "DELETE type::record('volume', $vid)",
            {"vid": vid})
        return True

    def create_chapter(self, title: str = "", volume_id: str | None = None) -> dict:
        """创建一个空章节。

        seq 是故事时间轴主键,永不复用归档章号;volume_id 存在时把新章追加到该卷末尾。
        """
        if volume_id is not None:
            vcheck = self._query(
                "SELECT id FROM type::record('volume',$vid) LIMIT 1",
                {"vid": volume_id})
            if not vcheck:
                raise ValueError(f"create_chapter: volume '{volume_id}' 不存在")
        seq = self.max_chapter() + 1
        if seq < 1:
            seq = 1
        title = (title or "").strip() or f"第{seq}章"
        self.save_chapter(seq, "", title=title, focalizer=None)
        if volume_id is not None:
            rows = self._query(
                "SELECT seq, sort_order FROM chapter:.. "
                "WHERE (archived = NONE OR archived != true) "
                "AND volume = type::record('volume', $vid)",
                {"vid": volume_id})
            rows.sort(key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else r["seq"]))
            order = [r["seq"] for r in rows if r["seq"] != seq] + [seq]
            self.reorder_chapters(volume_id, order)
        return {"seq": seq, "title": title, "volume": volume_id}

    def archive_chapter(self, seq: int, reason: str = "") -> bool:
        """软删除章节:隐藏但保留正文、版本和所有引用。已归档则幂等 True。"""
        rows = self._query(
            "SELECT seq, archived FROM type::record('chapter', $seq)", {"seq": seq})
        if not rows:
            return False
        if rows[0].get("archived") is True:
            return True
        self._execute_write(
            "UPDATE type::record('chapter', $seq) SET archived=true, archived_at=time::now(), archive_reason=$reason",
            {"seq": seq, "reason": (reason or "").strip() or None})
        try:
            self._execute_write(
                "UPDATE canon_candidate SET status='dismissed' "
                "WHERE (seq=$seq OR chapter=$seq) AND (status='pending' OR status=NONE)",
                {"seq": seq})
        except Exception:
            pass
        return True

    def restore_chapter(self, seq: int) -> bool:
        """恢复已归档章节。未归档则幂等 True。"""
        rows = self._query(
            "SELECT seq, archived FROM type::record('chapter', $seq)", {"seq": seq})
        if not rows:
            return False
        if rows[0].get("archived") is not True:
            return True
        self._execute_write(
            "UPDATE type::record('chapter', $seq) SET archived=false, archived_at=NONE, archive_reason=NONE",
            {"seq": seq})
        return True

    def archived_chapters(self) -> list[dict]:
        """列出归档箱中的章节,只返回目录展示需要的轻量字段。"""
        rows = self._query(
            "SELECT seq, title, archived_at, archive_reason FROM chapter:.. "
            "WHERE archived = true ORDER BY seq")
        out = []
        for row in rows:
            seq = row.get("seq")
            out.append({
                "seq": seq,
                "title": row.get("title") or f"第{seq}章",
                "archived_at": str(row.get("archived_at") or ""),
                "archive_reason": row.get("archive_reason") or "",
            })
        return out

    def _chapter_impact_token(self, seq: int, references: list[dict]) -> str:
        raw = json.dumps(
            {"db": self.db_name, "type": "chapter", "seq": seq, "references": references},
            ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def chapter_lifecycle_impact(self, seq: int) -> dict | None:
        """章节永久删除前的影响清单。"""
        ch = self.get_chapter(seq)
        if not ch:
            return None
        refs = []
        prose_chars = len((ch.get("prose") or "").strip())
        if prose_chars:
            refs.append({"kind": "正文", "count": prose_chars})
        count_specs = [
            ("版本", "SELECT count() AS n FROM chapter_version WHERE seq=$seq GROUP ALL"),
            ("质量快照", "SELECT count() AS n FROM quality_snapshot_member "
             "WHERE chapter_version IN (SELECT VALUE id FROM chapter_version "
             "WHERE seq=$seq) GROUP ALL"),
            ("主编对话", "SELECT count() AS n FROM chat_message WHERE chapter=$seq GROUP ALL"),
            ("素材引用", "SELECT count() AS n FROM material_reference WHERE chapter=$seq GROUP ALL"),
            ("伏笔触及", "SELECT count() AS n FROM promise_touch WHERE chapter=$seq GROUP ALL"),
            ("母题触及", "SELECT count() AS n FROM motif_instance WHERE chapter=$seq GROUP ALL"),
            ("关系触碰", "SELECT count() AS n FROM relation_touch WHERE chapter=$seq GROUP ALL"),
            ("事件", "SELECT count() AS n FROM event WHERE story_chapter=$seq OR ingest_seq=$seq GROUP ALL"),
            ("角色状态", "SELECT count() AS n FROM char_state WHERE chapter=$seq OR ingest_seq=$seq GROUP ALL"),
            ("章级北极星", "SELECT count() AS n FROM chapter_scorecard WHERE seq=$seq GROUP ALL"),
        ]
        for kind, query in count_specs:
            n = self._safe_count(query, {"seq": seq})
            if n:
                refs.append({"kind": kind, "count": n})
        label = ch.get("title") or f"第{seq}章"
        return {
            "object": {"type": "chapter", "id": seq, "label": label},
            "references": refs,
            "recommended_action": "archive",
            "confirm_impact_token": self._chapter_impact_token(seq, refs),
        }

    def delete_chapter_permanent(self, seq: int) -> bool:
        """永久删除章节和明确以该章为 owner 的派生记录。危险操作,端点层必须 token 门禁。"""
        rows = self._query("SELECT seq FROM type::record('chapter', $seq)", {"seq": seq})
        if not rows:
            return False
        quality_refs = self._safe_count(
            "SELECT count() AS n FROM quality_snapshot_member "
            "WHERE chapter_version IN (SELECT VALUE id FROM chapter_version "
            "WHERE seq=$seq) GROUP ALL",
            {"seq": seq},
        )
        if quality_refs:
            raise ValueError(
                "章节版本仍被质量快照冻结引用，拒绝永久删除；"
                "请保留章节或先走显式质量图处置流程"
            )
        try:
            self.purge_ingest(seq)
        except Exception as e:
            logging.getLogger("scribe3.store").warning(
                "delete_chapter_permanent purge_ingest(%s) 失败,继续清章节本体: %s", seq, e)
        ev_ids = self._query(
            "SELECT VALUE id FROM event WHERE story_chapter=$seq OR ingest_seq=$seq",
            {"seq": seq})
        if ev_ids:
            self._execute_write("DELETE involves WHERE in IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE causes WHERE in IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE causal WHERE in IN $ids OR out IN $ids", {"ids": ev_ids})
            self._execute_write("DELETE event WHERE id IN $ids", {"ids": ev_ids})
        self._context_tx(
            "BEGIN TRANSACTION; "
            "LET $violations = (SELECT id FROM chapter_version WHERE seq=$seq "
            "AND quality_snapshot_ref_count > 0); "
            "IF array::len($violations) > 0 { "
            "THROW '章节版本仍被质量快照冻结引用，拒绝永久删除' }; "
            "DELETE chapter_version WHERE seq=$seq; "
            "COMMIT TRANSACTION;",
            {"seq": seq},
        )
        for query in [
            "DELETE chapter_scorecard WHERE seq=$seq",
            "DELETE chat_message WHERE chapter=$seq",
            "DELETE material_reference WHERE chapter=$seq",
            "DELETE promise_touch WHERE chapter=$seq",
            "DELETE motif_instance WHERE chapter=$seq",
            "DELETE relation_touch WHERE chapter=$seq",
            "DELETE char_state WHERE chapter=$seq OR ingest_seq=$seq",
            "DELETE ingest_unverified WHERE seq=$seq",
            "DELETE voice_evolution_flag WHERE trigger_chapter=$seq OR ingest_seq=$seq",
            "DELETE lesson WHERE chapter=$seq",
            "DELETE distill_marker WHERE chapter=$seq",
            "DELETE canon_candidate WHERE seq=$seq OR chapter=$seq OR chapter_seq=$seq",
        ]:
            try:
                self._execute_write(query, {"seq": seq})
            except Exception:
                pass
        self._execute_write("DELETE type::record('chapter', $seq)", {"seq": seq})
        return True

    def reorder_chapters(self, volume_id: str | None, order: list[int]) -> int:
        """把 order 列表中各章的 sort_order 设为卷基址+i,并更新 volume 字段。
        seq 永远不动(故事时间轴主键)。
        P2-a Fix4: 卷基址由 *1000 改为 *100000——相当于二级排序键 (volume.sort_order, chapter_index),
        单卷支持至多 100000 章而不发生跨卷撞号;未分卷基址 = 0。
        R2.5: 若 volume_id 指定的卷不存在,抛 ValueError(防幽灵卷)。
        """
        base = 0
        if volume_id:
            vrows = self._query(
                "SELECT sort_order FROM type::record('volume', $vid)",
                {"vid": volume_id})
            if not vrows:
                raise ValueError(
                    f"reorder_chapters: volume '{volume_id}' 不存在,拒绝写入幽灵卷归属。"
                )
            base = vrows[0]["sort_order"] * 100000
        for i, seq in enumerate(order):
            if volume_id:
                # record<volume> 须用 type::record() 在 SurrealQL 里构造,不能传字符串
                self._execute_write(
                    "UPDATE type::record('chapter', $seq) SET sort_order=$o, "
                    "volume=type::record('volume', $vid)",
                    {"seq": seq, "o": base + i, "vid": volume_id})
            else:
                self._execute_write(
                    "UPDATE type::record('chapter', $seq) SET sort_order=$o, volume=NONE",
                    {"seq": seq, "o": base + i})
        return len(order)

    def update_chapter_meta(self, seq: int, fields: dict) -> bool:
        """只改梗概/卷/标签/标题(白名单),不碰 prose/embedding/qc_*。
        返回 True 若章存在,False 若章不存在(404 判定由调用方处理)。

        演绎字段卫生:
        - scene_truth 实质变化 → scene_truth_revision += 1（先于 deductions 结算 next_rev）
        - involved_characters / deductions 的 character_id → role: 规范化
        - 投影 stamp：仅**新角色**或 **prose 实质变化** 才写 based_on_truth_rev；
          旧 prose 缺 based_on 保持缺省（rev>0 仍 stale，禁止全文重存洗 stale）
        """
        # 先确认章存在
        exists = self._query(
            "SELECT seq FROM type::record('chapter', $seq)", {"seq": seq})
        if not exists:
            return False
        import json
        from scribe3.deduce_helpers import (
            normalize_involved,
            prepare_deductions_for_write,
            should_bump_truth_revision,
        )
        # 读当前真相/rev/投影，供 bump 与「不洗 stale」对照
        cur_rows = self._query(
            "SELECT scene_truth, scene_truth_revision, deductions "
            "FROM type::record('chapter', $seq)",
            {"seq": seq})
        cur = cur_rows[0] if cur_rows else {}
        old_truth = (cur.get("scene_truth") or "") if cur else ""
        try:
            cur_rev = max(0, int(cur.get("scene_truth_revision") or 0))
        except (TypeError, ValueError):
            cur_rev = 0
        existing_deds: list = []
        raw_deds = cur.get("deductions") if cur else None
        if isinstance(raw_deds, str):
            try:
                existing_deds = json.loads(raw_deds) if raw_deds else []
            except (ValueError, TypeError):
                existing_deds = []
        elif isinstance(raw_deds, list):
            existing_deds = raw_deds

        # —— 真相 revision 先于任意字段循环结算（与 fields key 顺序无关）——
        next_rev = cur_rev
        if "scene_truth" in fields:
            new_truth = fields.get("scene_truth")
            if should_bump_truth_revision(old_truth, new_truth if new_truth is not None else ""):
                next_rev = cur_rev + 1

        allowed = set(CHAPTER_META_ALLOWED)
        try:
            from scribe3.feature_flags import flag_truthy
            if not flag_truthy("SCRIBE3_BEATS_WRITE_LEGACY"):
                allowed -= {"beats", "deductions", "scene_truth", "chapter_spine", "beats_meta"}
        except Exception:
            allowed -= {"beats", "deductions", "scene_truth", "chapter_spine", "beats_meta"}
        # volume 需单独处理(record link 不能传字符串参数)
        volume_id = _UNSET  # 哨兵:区分"未传 volume"与"传了 None(清空)"
        plain: dict = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "volume":
                volume_id = v   # None = 清空, str = 新卷裸 id
            elif k == "scene_truth":
                plain[k] = v
                if next_rev != cur_rev:
                    plain["scene_truth_revision"] = next_rev
            elif k == "involved_characters":
                plain[k] = json.dumps(
                    normalize_involved(v if v is not None else []),
                    ensure_ascii=False)
            elif k == "deductions":
                # 用已结算的 next_rev；仅新/改 prose 才 stamp
                prepared = prepare_deductions_for_write(
                    v if v is not None else [],
                    existing_deds,
                    next_rev,
                )
                plain[k] = json.dumps(prepared, ensure_ascii=False)
            elif k in ("beats", "deltas"):
                # list 字段存为 JSON 串(绕 SCHEMAFULL 嵌套校验,同 scene_meta);读时还原。
                plain[k] = json.dumps(v if v is not None else [], ensure_ascii=False)
            elif k in CHAPTER_JSON_META_KEYS:
                # JSON 合同：dict → JSON 串；已是 str 则原样；None → 清字段
                if v is None:
                    plain[k] = None
                else:
                    plain[k] = dump_chapter_json_meta(v)
            elif k in CHAPTER_JSON_LIST_META_KEYS:
                if v is None:
                    plain[k] = json.dumps([], ensure_ascii=False)
                else:
                    plain[k] = json.dumps(coerce_chapter_json_list(v), ensure_ascii=False)
            else:
                plain[k] = v
        # 构建 SET 子句:先处理普通字段,再追加 volume(若有)
        set_parts: list[str] = [f"{k}=$p_{k}" for k in plain]
        params: dict = {f"p_{k}": v for k, v in plain.items()}
        params["seq"] = seq
        if volume_id is not _UNSET:
            if volume_id is None:
                set_parts.append("volume=NONE")
            else:
                # R2.5: 校验目标卷存在,防幽灵卷
                vcheck = self._query(
                    "SELECT id FROM type::record('volume',$vid) LIMIT 1", {"vid": volume_id})
                if not vcheck:
                    raise ValueError(
                        f"update_chapter_meta: volume '{volume_id}' 不存在,拒绝写入幽灵卷归属。"
                    )
                set_parts.append("volume=type::record('volume', $p_volume)")
                params["p_volume"] = volume_id
        if not set_parts:
            return True
        self._execute_write(
            f"UPDATE type::record('chapter', $seq) SET {', '.join(set_parts)}",
            params)
        _emit_cache_invalidation("chapter", getattr(self, "db_name", None), store=self)
        return True

    # ── 章后统一分析缓存（跨进程；与 chapter_analysis 进程内缓存双写）──
    def set_post_analysis_cache(self, seq: int, prose: str, payload: dict) -> None:
        """落库 knowledge+settings 缓存；payload 须 JSON 可序列化。"""
        import hashlib
        import json
        import time
        prose = prose or ""
        fp = hashlib.sha256(prose.encode("utf-8")).hexdigest()[:16]
        # 只存可序列化字段；claims 由 settings 再生成
        body = {
            "prose_fp": fp,
            "knowledge": payload.get("knowledge"),
            "settings": payload.get("settings") or {},
            "format": payload.get("format"),
            "ts": int(time.time()),
        }
        try:
            raw = json.dumps(body, ensure_ascii=False)
        except Exception as e:
            logging.getLogger("scribe3.store").warning("post_analysis_cache serialize: %s", e)
            return
        # 限体积：过大则只留 knowledge 摘要标志
        if len(raw) > 400_000:
            body = {
                "prose_fp": fp,
                "knowledge": payload.get("knowledge"),
                "settings": {},
                "format": payload.get("format"),
                "ts": int(time.time()),
                "truncated": True,
            }
            raw = json.dumps(body, ensure_ascii=False)
        try:
            self._execute_write(
                "UPDATE type::record('chapter', $seq) SET "
                "post_analysis_cache=$c, post_analysis_fp=$fp, post_analysis_at=time::now() "
                "RETURN NONE",
                {"seq": int(seq), "c": raw, "fp": fp},
            )
        except Exception as e:
            # 老库未 migration：best-effort DEFINE 再试一次
            try:
                self._raw_query(
                    "DEFINE FIELD IF NOT EXISTS post_analysis_cache ON chapter TYPE option<string>;"
                )
                self._raw_query(
                    "DEFINE FIELD IF NOT EXISTS post_analysis_fp ON chapter TYPE option<string>;"
                )
                self._execute_write(
                    "UPDATE type::record('chapter', $seq) SET "
                    "post_analysis_cache=$c, post_analysis_fp=$fp, post_analysis_at=time::now() "
                    "RETURN NONE",
                    {"seq": int(seq), "c": raw, "fp": fp},
                )
            except Exception as e2:
                logging.getLogger("scribe3.store").warning(
                    "set_post_analysis_cache fail seq=%s: %s / %s", seq, e, e2)

    def get_post_analysis_cache(self, seq: int, prose: str) -> dict | None:
        """读章后分析缓存；prose 指纹不一致则视为失效。"""
        import hashlib
        import json
        prose = prose or ""
        fp = hashlib.sha256(prose.encode("utf-8")).hexdigest()[:16]
        try:
            rows = self._query(
                "SELECT post_analysis_cache, post_analysis_fp "
                "FROM type::record('chapter', $seq)",
                {"seq": int(seq)},
            )
        except Exception:
            return None
        if not rows:
            return None
        row = rows[0] or {}
        stored_fp = (row.get("post_analysis_fp") or "").strip()
        raw = row.get("post_analysis_cache")
        if not raw:
            return None
        if stored_fp and stored_fp != fp:
            return None
        try:
            body = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return None
        if not isinstance(body, dict):
            return None
        if (body.get("prose_fp") or stored_fp) and (body.get("prose_fp") or stored_fp) != fp:
            return None
        return body

    def clear_post_analysis_cache(self, seq: int) -> None:
        """显式清空章后分析缓存（改稿/强制重抽）。"""
        try:
            self._execute_write(
                "UPDATE type::record('chapter', $seq) SET "
                "post_analysis_cache=NONE, post_analysis_fp=NONE, post_analysis_at=NONE "
                "RETURN NONE",
                {"seq": int(seq)},
            )
        except Exception as e:
            logging.getLogger("scribe3.store").warning(
                "clear_post_analysis_cache seq=%s: %s", seq, e)

    def post_analysis_summary(self, seq: int, prose: str | None = None) -> dict | None:
        """只读摘要：是否命中、format、知识/设定条数（不返回全文 JSON）。"""
        import hashlib
        import json
        try:
            rows = self._query(
                "SELECT post_analysis_cache, post_analysis_fp, "
                "(IF post_analysis_at IS NONE THEN NONE ELSE <string>post_analysis_at END) AS post_analysis_at "
                "FROM type::record('chapter', $seq)",
                {"seq": int(seq)},
            )
        except Exception:
            return None
        if not rows or not rows[0].get("post_analysis_cache"):
            return {"present": False, "seq": int(seq)}
        raw = rows[0].get("post_analysis_cache")
        stored_fp = (rows[0].get("post_analysis_fp") or "").strip()
        try:
            body = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return {"present": False, "seq": int(seq), "corrupt": True}
        if not isinstance(body, dict):
            return {"present": False, "seq": int(seq), "corrupt": True}
        fp_ok = True
        if prose is not None:
            cur = hashlib.sha256((prose or "").encode("utf-8")).hexdigest()[:16]
            body_fp = (body.get("prose_fp") or stored_fp or "").strip()
            fp_ok = (not body_fp) or body_fp == cur
        kn = body.get("knowledge") if isinstance(body.get("knowledge"), dict) else {}
        settings = body.get("settings") if isinstance(body.get("settings"), dict) else {}
        def _n(key):
            v = kn.get(key) if kn else None
            return len(v) if isinstance(v, list) else 0
        set_n = 0
        for k in ("entities", "factions", "items", "terms", "world_rules", "promises", "motifs", "relations", "facts"):
            v = settings.get(k)
            if isinstance(v, list):
                set_n += len(v)
        disc = body.get("discipline") if isinstance(body.get("discipline"), dict) else None
        return {
            "present": True,
            "seq": int(seq),
            "fp_match": fp_ok,
            "format": body.get("format"),
            "at": rows[0].get("post_analysis_at"),
            "truncated": bool(body.get("truncated")),
            "knowledge": {
                "learned": _n("learned"),
                "did": _n("did"),
                "events": _n("events"),
                "arc": _n("arc"),
            },
            "settings_count": set_n,
            "events_backfilled": bool((kn or {}).get("_events_backfilled")),
            "has_discipline": bool(disc),
            "discipline_violations": list((disc or {}).get("violations") or [])[:8],
            "has_tension": bool(
                isinstance(body.get("tension"), dict)
                and (
                    body["tension"].get("rubric") is not None
                    or body["tension"].get("rubric_failed")
                )
            ),
        }


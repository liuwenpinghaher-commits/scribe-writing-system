"""统一多通道 MemoryRetriever(Task 8):四通道取数 → RRF 融合 → 分类衰减 → 正典压制。

四通道(fail-soft:任一挂了降级空,绝不崩):
  · structured:facts_at / open_promises 等【领域表】直查 → canonical 候选(不进 memory_item);
  · bm25:memory_item.tokens 全文(jieba 预分词 + BM25);
  · vector:memory_item.embedding HNSW 语义;
  · graph:memory_relation 从 bm25/vector 种子沿联想边一跳扩展。

冲突处理顺序(宪法级,计划 Task 8 原文):
  当前有效 canonical > 后续 canonical supersession > 作者明确决策 > 高信心 procedural
  > episodic > reference > uncertainty。
正典压制(MVP 可判定版):canonical 与 episodic 同 (entity,attribute) → episodic 进 rejected,
  reason="conflicts_with_canonical"。reference 绝不参与剧情真假裁决——它不受此压制。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from scribe3.memory_models import (
    MemoryCandidate,
    RejectedCandidate,
    RetrievalQuery,
    RetrievalResult,
)

_log = logging.getLogger("scribe3.memory_retrieval")

# 通道权重(计划规格第 870 行):structured 最重(正典直查最可信),graph 次之。
# M-4 记账:"recency" 是【预留死配置】——本检索器四通道不含 recency 路,
#   时间新鲜度已由 final_score 的 decay(分类半衰期)折进,故此权重当前不被 fuse 引用。
#   保留是为对齐规格并预留未来"最近对话/最近保存"独立通道;接入前它不影响任何打分。
CHANNEL_WEIGHTS = {"structured": 2.0, "bm25": 1.0, "vector": 1.0, "graph": 1.2, "recency": 0.8}

# 分类半衰期(天,计划规格第 884 行):working 最易过期,procedural 最持久。
HALF_LIFE_DAYS = {"working": 3, "episodic": 30, "procedural": 180, "reference": 90, "uncertainty": 14}


def reciprocal_rank_fusion(rankings: dict[str, list[str]], k: int = 60) -> dict[str, float]:
    """RRF 融合(计划规格第 872-878 行,逐字):
    得分 = Σ_通道 weight / (k + 通道内位次)。同一 id 跨通道命中即累加。"""
    scores: dict[str, float] = {}
    for channel, ids in rankings.items():
        # M-3:fuse 是公开函数,未知通道名不该崩;缺省权重 1.0(中性,不放大不抑制)。
        weight = CHANNEL_WEIGHTS.get(channel, 1.0)
        for rank, source_id in enumerate(ids, 1):
            scores[source_id] = scores.get(source_id, 0.0) + weight / (k + rank)
    return scores


def final_score(candidate: MemoryCandidate, now: datetime, focus_ids: set[str]) -> float:
    """最终打分(计划规格第 886-895 行,逐字):
    canonical 恒 rrf+1.0 置顶;其余 = rrf × importance × confidence × decay + focus_bonus + pin_bonus。
    唯一加固:observed_at 缺失时按 age=0(decay=1.0)而非崩——fail-soft,不改公式语义。"""
    if candidate.source_kind == "canonical":
        return candidate.rrf_score + 1.0
    if candidate.observed_at is None:
        age_days = 0.0
    else:
        age_days = max(0.0, (now - candidate.observed_at).total_seconds() / 86400)
    decay = 1.0 if candidate.pinned else 0.5 ** (age_days / HALF_LIFE_DAYS[candidate.source_kind])
    importance = 0.65 + 0.07 * candidate.importance
    confidence = 0.75 + 0.25 * candidate.confidence
    # I-2 依赖告警:linked_ids 由 Task 9 捕获管线回填(经验记忆提及的实体 id)。
    #   在回填前 _experiential_candidate 产出的候选 linked_ids 恒空 → 本 bonus 恒 0,
    #   focus 加权对真实记忆【静默不生效】。RetrievalResult.unlinked_count 记此缺口。
    focus_bonus = 0.15 if candidate.linked_ids & focus_ids else 0.0
    pin_bonus = 0.25 if candidate.pinned else 0.0
    return candidate.rrf_score * importance * confidence * decay + focus_bonus + pin_bonus


def _conflict_keys(cand: MemoryCandidate) -> set[tuple[str, str]]:
    """从候选 provenance 提取 (entity, attribute) 冲突键(与 context_assembler 同口径,
    保证正典压制在检索层与组装层裁决一致)。"""
    keys: set[tuple[str, str]] = set()
    for p in (cand.provenance or []):
        e, a = p.get("entity"), p.get("attribute")
        if e and a:
            keys.add((e, a))
    return keys


def _suppress_by_canonical(cands: list[MemoryCandidate]) -> list[RejectedCandidate]:
    """正典压制:凡 episodic 候选与任一 canonical 同 (entity,attribute) → 压制。
    只压 episodic(它宣称"发生过什么");reference 是外部参考,绝不参与真假裁决,不压。

    ⚠ I-1 依赖告警:判据是 episodic 候选 provenance 里的 (entity,attribute)。
      这两键由 Task 9 捕获管线回填;在回填前 _experiential_candidate 只写
      source_type/source_ref,不含 entity/attribute → 本压制对真实记忆【静默失效】
      (手搓 provenance 的单测能触发,真机记忆不能)。RetrievalResult.unconflictable_count
      记录这类"压制不了的" episodic 数,让缺口可观测。
    ⚠ M-2 记账:canonical 之间的 supersede/时态裁决不在此层做——canonical 候选由
      structured 通道从 facts_at(chapter) 直查,已受领域表的时态窗口(valid_from/to)
      约束,取回的本就是"当章有效正典";检索层不再对 canonical 互相 supersede。"""
    canon_keys: set[tuple[str, str]] = set()
    for c in cands:
        if c.source_kind == "canonical":
            canon_keys |= _conflict_keys(c)
    rejected: list[RejectedCandidate] = []
    if not canon_keys:
        return rejected
    for c in cands:
        if c.source_kind == "episodic" and (_conflict_keys(c) & canon_keys):
            rejected.append(RejectedCandidate(candidate=c, reason="conflicts_with_canonical"))
    return rejected


def fuse(channel_rankings: dict[str, list[str]],
         candidates: dict[str, MemoryCandidate],
         now: datetime | None = None,
         focus_ids: set[str] | None = None) -> RetrievalResult:
    """纯融合内核:多通道排名 + 候选元数据 → RetrievalResult。

    1) RRF 打分,回填每个候选的 channels / channel_ranks / rrf_score;
    2) final_score 分类衰减打分;
    3) 正典压制(canonical → episodic);
    4) 未被压制者按 final_score 降序为 selected。
    就地回填候选字段(MemoryCandidate 故意非 frozen),便于 by_id 取回带 channels 的候选。"""
    now = now or datetime.now(timezone.utc)
    focus_ids = focus_ids or set()

    # 1) RRF + 回填来路
    for channel, ids in channel_rankings.items():
        for rank, sid in enumerate(ids, 1):
            c = candidates.get(sid)
            if c is None:
                continue
            c.channels.add(channel)
            prev = c.channel_ranks.get(channel)
            if prev is None or rank < prev:   # 同通道多命中取最优位次
                c.channel_ranks[channel] = rank
    for sid, score in reciprocal_rank_fusion(channel_rankings).items():
        c = candidates.get(sid)
        if c is not None:
            c.rrf_score = score

    # 2) final_score
    all_cands = list(candidates.values())
    for c in all_cands:
        c.final_score = final_score(c, now, focus_ids)

    # 3) 正典压制
    rejected = _suppress_by_canonical(all_cands)
    rejected_ids = {r.candidate.source_id for r in rejected}

    # 4) selected 降序
    selected = sorted(
        (c for c in all_cands if c.source_id not in rejected_ids),
        key=lambda c: c.final_score, reverse=True,
    )

    # 5) telemetry(I-1/I-2):把"机制未接线"从静默变可观测。
    unconflictable = sum(1 for c in all_cands
                         if c.source_kind == "episodic" and not _conflict_keys(c))
    unlinked = sum(1 for c in all_cands
                   if c.source_kind != "canonical" and not c.linked_ids)
    if unconflictable or unlinked:
        _log.debug(
            "记忆检索接线缺口:%d 条 episodic 缺 (entity,attribute) 无法被正典压制、"
            "%d 条经验记忆缺 linked_ids 无法吃 focus 加权(待 Task 9 捕获回填)",
            unconflictable, unlinked)
    return RetrievalResult(selected=selected, rejected=rejected,
                           unconflictable_count=unconflictable, unlinked_count=unlinked)


def _coerce_dt(v) -> datetime | None:
    """把库里返回的 observed_at(datetime 或 ISO 串)统一成 aware datetime。"""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


_EXPERIENTIAL_KINDS = ("working", "episodic", "procedural", "reference", "uncertainty")


class MemoryRetriever:
    """统一记忆检索器。retrieve() 满足 Task 7 ContextAssembler 消费协议:
        retrieve(work, snapshot_dict, query, k) -> list[MemoryCandidate]
    候选属性:source_kind / source_id / text / work / provenance / confidence /
    importance / observed_at / linked_ids。"""

    def __init__(self, store):
        self.store = store

    # --- Task 7 协议入口 ---
    def retrieve(self, work: str, snapshot_dict: dict, query: str, k: int = 24) -> list[MemoryCandidate]:
        # Task 16-C:统一走【带缓存】完整结果——ContextAssembler 生产读路径经此入口,
        #   接线后自动吃 30s TTL + 表级失效缓存,并在 miss 分支记 record_retrieval_latency
        #   (retrieval_p50/p95 从 0 变真实值)。缓存语义透明:同键返回同 RetrievalResult,
        #   剧透门/正典压制/秘密屏蔽的裁决全在 retrieve_full 内,缓存不改结果只省重算。
        result = self.retrieve_full_cached(RetrievalQuery(
            work=work, snapshot=snapshot_dict or {}, query=query or "", k=k))
        return result.candidates[:k]   # 协议约定返回 ~k 条(canonical 恒置顶,不会被截掉)

    # --- 带缓存的完整结果(Task 16-B 就绪层)---
    def retrieve_full_cached(self, rq: RetrievalQuery) -> RetrievalResult:
        """按 work + 快照维度 + normalized_query + policy_version 缓存 30s 的检索结果,
        受正典 / 素材 / 记忆表级失效(记忆 supersede、素材 archive·pin、正典写入立即清)。

        Task 16-C 生产接线:ContextAssembler 经 retrieve() → 本方法把检索接进写作 envelope。"""
        from time import perf_counter

        from scribe3 import context_cache as cc
        ctx_hash = self._snapshot_cache_dim(rq.snapshot)
        key = cc.retrieval_key(rq.work, ctx_hash, rq.query)
        cached = cc.RETRIEVAL_CACHE.get(key)
        if cached is not None:
            return cached
        started = perf_counter()
        result = self.retrieve_full(rq)
        cc.record_retrieval_latency((perf_counter() - started) * 1000.0)
        cc.RETRIEVAL_CACHE.set(key, result, work=rq.work)
        return result

    @staticmethod
    def _snapshot_cache_dim(snapshot) -> str:
        """缓存键的快照维度。

        ⚠ 剧透门红线:写作路径经 ContextAssembler 传的是 snapshot.canonical_payload()
        (故意 exclude context_hash),若沿用旧写法 snapshot.get("context_hash","") 恒得
        空串 → 同 work 同 query 下【所有章共用一把键】→ 写第 5 章会命中第 20 章缓存的
        known_from=20 记忆,剧透门被缓存击穿(store 层 known_from 门反被旁路)。
        故:context_hash 显式给出时用它(存量直调方语义不变);缺失时对整份快照取稳定
        sha256——canonical_payload 含 chapter/focalizer/focus/navigation_id/work,天然使
        每章每焦点者各得一把键,剧透门/work 隔离在缓存层仍成立。

        L2 记账脚枪(Task 16-C):显式 context_hash 分支【信任调用方】——真实 ContextSnapshot 的
        context_hash 恒由 with_hash() 覆盖 chapter/focalizer/work 全字段(canonical_payload 之
        SHA-256),故安全;唯有【手搓 dict 传一个与自身内容不符的 context_hash】才会击穿按章隔离
        (如两章硬塞同一 context_hash)。生产无此路径(assembler 传 canonical_payload,不含 hash 走
        回退分支);仅测试/未来直调方需自律:要么别传 context_hash,要么保证它随快照内容变化。"""
        if not isinstance(snapshot, dict):
            return ""
        h = snapshot.get("context_hash")
        if h:
            return str(h)
        import hashlib
        import json
        raw = json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    # --- 完整结果(含 rejected,供审计/测试)---
    def retrieve_full(self, rq: RetrievalQuery) -> RetrievalResult:
        now = rq.now or datetime.now(timezone.utc)
        focus_ids = set(rq.focus_ids) | self._focus_ids_from_snapshot(rq.snapshot)
        # I-4 限知红线:从 snapshot 取当前章,经验通道按【读者/发现时间】known_from/to 过滤,
        #   杜绝"第 20 章才被知道的记忆倒灌进第 5 章"的知情倒灌。
        #   讨论模式(snapshot 无 chapter)→ chapter=None → 各经验通道 fail-open 不过滤,别误伤。
        chapter = self._chapter_of(rq.snapshot)
        candidates: dict[str, MemoryCandidate] = {}
        rankings: dict[str, list[str]] = {}

        s_ids = self._channel_structured(rq, candidates)
        if s_ids:
            rankings["structured"] = s_ids
        b_ids = self._channel_bm25(rq, candidates, chapter)
        if b_ids:
            rankings["bm25"] = b_ids
        v_ids = self._channel_vector(rq, candidates, chapter)
        if v_ids:
            rankings["vector"] = v_ids
        # graph 种子:bm25/vector 命中的经验记忆(裸 memory_item id)
        seed_raw = [s.split("mem:", 1)[1] for s in (b_ids + v_ids) if s.startswith("mem:")]
        g_ids = self._channel_graph(rq, candidates, seed_raw, chapter)
        if g_ids:
            rankings["graph"] = g_ids

        return fuse(rankings, candidates, now=now, focus_ids=focus_ids)

    @staticmethod
    def _chapter_of(snapshot: dict) -> int | None:
        """从 snapshot 取当前章(讨论模式无章 → None → 经验通道不做时态过滤)。"""
        if not isinstance(snapshot, dict):
            return None
        ch = snapshot.get("chapter")
        return int(ch) if isinstance(ch, int) else None

    # --- 焦点实体 ---
    @staticmethod
    def _focus_ids_from_snapshot(snapshot: dict) -> set[str]:
        ids: set[str] = set()
        if not isinstance(snapshot, dict):
            return ids
        focus = snapshot.get("focus")
        if isinstance(focus, dict) and focus.get("id"):
            ids.add(str(focus["id"]))
        return ids

    # --- 通道1:structured(领域表 → canonical 候选)---
    def _channel_structured(self, rq: RetrievalQuery, candidates: dict) -> list[str]:
        """facts_at / open_promises 直查作 canonical 候选。
        ⚠ 正典不复制进 memory_item:每次即时从权威领域表取,永远是当下真值。"""
        ids: list[str] = []
        chapter = rq.snapshot.get("chapter") if isinstance(rq.snapshot, dict) else None
        cap = max(rq.k * 2, 40)
        try:
            facts = self.store.facts_at(chapter if chapter is not None else 99999)
        except Exception:
            _log.debug("structured 通道 facts_at 失败,降级空", exc_info=True)
            facts = []
        for f in (facts or [])[:cap]:
            sid = getattr(f, "id", None)
            if not sid or sid in candidates:
                continue
            candidates[sid] = MemoryCandidate(
                source_kind="canonical", source_id=sid, work=rq.work,
                text=self._fact_text(f), confidence=1.0, importance=4, observed_at=None,
                provenance=[{"entity": getattr(f, "entity_id", "") or "",
                             "attribute": getattr(f, "attribute", "") or "",
                             "secret": bool(getattr(f, "secret", False))}],
            )
            ids.append(sid)
        try:
            promises = self.store.open_promises()
        except Exception:
            _log.debug("structured 通道 open_promises 失败,降级空", exc_info=True)
            promises = []
        for p in (promises or [])[:cap]:
            pid = p.get("id")
            sid = f"promise:{pid}"
            if not pid or sid in candidates:
                continue
            candidates[sid] = MemoryCandidate(
                source_kind="canonical", source_id=sid, work=rq.work,
                text=p.get("text") or "", confidence=1.0, importance=3, observed_at=None,
                provenance=[{"promise": pid}],
            )
            ids.append(sid)
        return ids

    @staticmethod
    def _fact_text(f) -> str:
        e = getattr(f, "entity_id", "") or ""
        a = getattr(f, "attribute", "") or ""
        v = getattr(f, "value", "") or ""
        return f"{e} {a} {v}".strip()

    # --- 通道2:bm25(memory_item 全文)---
    def _channel_bm25(self, rq: RetrievalQuery, candidates: dict, chapter: int | None) -> list[str]:
        try:
            raw = self.store.memory_bm25(rq.work, rq.query, k=rq.k, chapter=chapter)
        except Exception:
            _log.debug("bm25 通道失败,降级空", exc_info=True)
            return []
        return self._hydrate_experiential(rq, candidates, raw or [])

    # --- 通道3:vector(memory_item HNSW)---
    def _channel_vector(self, rq: RetrievalQuery, candidates: dict, chapter: int | None) -> list[str]:
        try:
            raw = self.store.memory_vector(rq.work, rq.query, k=rq.k, chapter=chapter)
        except Exception:
            _log.debug("vector 通道失败,降级空", exc_info=True)
            return []
        return self._hydrate_experiential(rq, candidates, raw or [])

    # --- 通道4:graph(memory_relation 一跳扩展)---
    def _channel_graph(self, rq: RetrievalQuery, candidates: dict, seed_raw: list[str],
                       chapter: int | None) -> list[str]:
        if not seed_raw:
            return []
        try:
            raw = self.store.memory_graph(rq.work, seed_raw[:3], k=rq.k, chapter=chapter)
        except Exception:
            _log.debug("graph 通道失败,降级空", exc_info=True)
            return []
        return self._hydrate_experiential(rq, candidates, raw or [])

    # --- 经验候选水合(memory_item 裸 id → MemoryCandidate,统一 source_id="mem:<id>")---
    def _hydrate_experiential(self, rq: RetrievalQuery, candidates: dict, mem_ids: list[str]) -> list[str]:
        missing = [m for m in mem_ids if f"mem:{m}" not in candidates]
        rows: dict[str, dict] = {}
        if missing:
            try:
                for r in (self.store.get_memory_items(missing) or []):
                    rows[r["id"]] = r
            except Exception:
                _log.debug("get_memory_items 失败,该通道该批降级空", exc_info=True)
                rows = {}
        ordered: list[str] = []
        for m in mem_ids:
            sid = f"mem:{m}"
            if sid not in candidates:
                row = rows.get(m)
                if row is None:
                    continue   # 拉不到行 → 跳过(fail-soft)
                candidates[sid] = self._experiential_candidate(rq, sid, row)
            ordered.append(sid)
        return ordered

    @staticmethod
    def _experiential_candidate(rq: RetrievalQuery, sid: str, row: dict) -> MemoryCandidate:
        kind = row.get("kind") or "episodic"
        if kind not in _EXPERIENTIAL_KINDS:
            kind = "episodic"   # 兜底:未知类型按 episodic(经验)处理,绝不误当 canonical
        conf = row.get("confidence")
        imp = row.get("importance")
        # Task 9 活化回填:读回 memory_item.provenance((entity,attribute)冲突键)与
        #   linked_ids(提及实体 id),再追加来源溯源项。二者补齐后:
        #   · 正典压制对真机 episodic 生效(_conflict_keys 能取到 (entity,attribute));
        #   · focus 加权对真机经验候选生效(linked_ids & focus_ids)。
        prov = [p for p in (row.get("provenance") or []) if isinstance(p, dict)]
        prov = list(prov) + [{"source_type": row.get("source_type"),
                              "source_ref": row.get("source_id")}]
        linked = {str(x) for x in (row.get("linked_ids") or []) if x}
        return MemoryCandidate(
            source_kind=kind, source_id=sid, work=rq.work,
            text=row.get("text") or row.get("summary") or "",
            confidence=float(conf) if conf is not None else 1.0,
            importance=int(imp) if imp is not None else 2,
            pinned=bool(row.get("pinned")),
            observed_at=_coerce_dt(row.get("observed_at")),
            provenance=prov, linked_ids=linked,
        )

"""Task 9 · 幂等捕获管线:把对话/写作/审批事件捕获成经验记忆,并回填活化字段。

灵魂(不是附带):Task 8 建好了四通道检索 + 正典压制 + focus 加权,但捕获管线缺席——
  · memory_item 是空表;
  · 就算有记忆,也缺 provenance 的 (entity,attribute) / linked_ids,导致正典压制与 focus
    加权对真机记忆【静默失效】(RetrievalResult.unconflictable_count / unlinked_count 记这个缺口)。
本模块把对话轮捕获成经验记忆并为回填补齐通道。【实施状态(诚实边界,勿夸大)】:
  · linked_ids:生产已接线——捕获时用领域实体反查(_domain_signals)把命中的登记
    角色/地点作 linked_ids 写入,focus 加权对真机记忆生效,unlinked_count 随之降;
  · known_from:生产已接线——捕获时以当前章填入(限知门对捕获记忆生效,防知情倒灌);
  · 正典压制所需的自由文本 (entity,attribute) 精确抽取【仍待后续】——高风险稳定断言
    (身份/血缘/生死/秘密/背叛)已被前置拦进 pending_authority_claim(不进 memory_item),
    故进 memory_item 的经验记忆当前不带精确 attribute,unconflictable_count 对它们仍 >0
    (如实哨兵,见 test_memory_capture 的生产签名测试)。塞半吊子 attribute 会误压制有效
    经验,比漏压制更伤,故不做启发式硬凑。

── 同步 drain 决策(降复杂度,见设计裁决)──────────────────────────────
计划的"同步事务 vs 异步工作者"边界,这里用【同步 drain】落地,不引后台线程(避免竞态):
  · capture_event:同步入队 outbox(event_id UNIQUE 幂等),随即【同步】drain 这一条
    (分类 → 路由 → 落 memory_item / pending_authority_claim),标记 complete/failed。
    ——之所以在 capture_event 里就 drain 单条(而非只入队),是要满足计划 Step 1 的验收:
      两次 capture 同一 turn 后 count_memory_by_source == 1,期间不调 consolidate。
  · consolidate_thread:重活的批处理端——drain 掉线残留(failed/pending)+ 压缩 working
    summary(每 8 完成 turn / session end / on_pre_compress 前触发)。
  · 保留 outbox 状态机(pending→processing→complete/failed + attempts + error):
    工作者失败【不阻断对话】,只把 failed/error/attempts 留在 outbox,并对 runtime-status
    可见(store.count_failed_memory_events)+ WARN 日志。可重试(consolidate 会再 drain)。

── 限知红线(宪法级,不可破)────────────────────────────────────────
  · 正典事实(canonical / authority claim)【绝不】写进 memory_item——一律进
    pending_authority_claim 待审。memory_item 只存经验性五类(working/episodic/procedural/
    reference/uncertainty)。fact 唯一真相源永远是领域表。
  · uncertainty 的 confidence<=0.5,不作事实注入(仅供参考,不参与真假裁决)。

── 分类器 MVP ──────────────────────────────────────────────────────
规则/关键词 + 显式 classification(测试用 classification= 优先);无显式时用轻量启发式。
不接 LLM 分类(降复杂度 + 省调用);后续可升级为 LLM/embedding 分类器。

── 审查记账(半空转,待 Task 16 收口,勿当已修)──────────────────────
  · 捕获已【恒开】:_capture_turn_memory 每轮同步 embed(有真实 embedding 成本),无 feature
    toggle 可关;而检索器【生产未接】——_get_write_retriever 恒返 None,记忆永不进写作 prompt
    (只写不读的半空转)。Task 16 须对称接线:检索接进生产 envelope + 给捕获加 toggle
    (成本可控),二者一并放开,避免"只烧 embed 不产出"的长期空转。
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

_log = logging.getLogger("scribe3.memory_capture")


# ── 事件契约 ─────────────────────────────────────────────────────────

@dataclass
class MemoryEvent:
    """捕获管线的输入事件。event_id 幂等键;payload 承载文本与可选活化字段
    (classification/entity/attribute/linked_ids/known_from 等)。"""

    event_id: str
    work: str
    event_type: str          # navigation/turn/write/approval/save/compress/session_end
    payload: dict = field(default_factory=dict)
    thread_id: str | None = None


def turn_event(text: str, *, event_id: str | None = None, work: str = "main",
               thread_id: str | None = None, classification: str | None = None,
               entity: str | None = None, attribute: str | None = None,
               value: str | None = None, linked_ids: list[str] | None = None,
               provenance: list[dict] | None = None,
               valid_from: int | None = None, valid_to: int | None = None,
               known_from: int | None = None, known_to: int | None = None) -> MemoryEvent:
    """便捷构造一个 turn 事件(app 挂点 + 测试共用)。仅装入非空键,payload 保持干净。"""
    payload: dict = {"text": text}
    for k, v in (("classification", classification), ("entity", entity),
                 ("attribute", attribute), ("value", value), ("linked_ids", linked_ids),
                 ("provenance", provenance), ("valid_from", valid_from), ("valid_to", valid_to),
                 ("known_from", known_from), ("known_to", known_to)):
        if v is not None:
            payload[k] = v
    return MemoryEvent(event_id=event_id or f"turn:{uuid.uuid4().hex[:12]}",
                       work=work, event_type="turn", payload=payload, thread_id=thread_id)


# ── 分类决策(计划 Step 5 决策表)────────────────────────────────────

@dataclass
class Classification:
    route: str              # canonical_claim | working | episodic | procedural | reference | uncertainty
    kind: str               # 经验五类之一(canonical_claim 时无意义,置 "")
    scope_type: str         # work | thread | user_global
    confidence: float
    importance: int


# 强显式正典短语(无需实体反查即判定;精确连续子串,守既有 '真实身份' 场景)。
_CANONICAL_MARKERS = ("真实身份", "其实是", "真身是", "真身为", "真名是", "身世是",
                      "本名是", "实为", "竟是")
_UNCERTAINTY_MARKERS = ("我猜", "可能", "也许", "大概", "或许", "说不定", "恐怕", "似乎", "怀疑")
_PROCEDURAL_MARKERS = ("以后", "别再", "少用", "务必", "记得", "从今往后", "每次都", "今后")
# 作者明确标为“写作偏好”的表达，语义是未来生成时须遵循的工艺约束，不能降成普通
# episodic 往事。只匹配显式偏好标签，避免把“请记住某个剧情事实”误分类为写法。
_AUTHOR_WRITING_PREFERENCE_MARKERS = ("作者偏好", "写作偏好")
_WORKING_MARKERS = ("正在", "现在", "目前", "在修", "手头", "眼下")
_EPISODIC_MARKERS = ("决定", "已经", "已决定", "定了", "删掉", "改成", "确定", "这次")

# ── 正典嫌疑判据(P0 限知宪法红线)──────────────────────────────────
# 根因修:兜底 episodic + 只 9 个精确短串会漏放身份/生死揭示('其实凶手是甲' 不含连续
# '其实是')。判据 = 【命中已登记角色/地点】+【高风险稳定断言谓词】→ 强制 canonical_claim
# 待审(不进 memory_item)。谓词聚焦【稳定属性断言】(是谁/真身/血缘/生死/秘密/背叛/情感核心),
# 用短串【分离匹配】去连续子串依赖;【排除】位置移动等易变经验(去/看见/说/在城西=经验非正典),
# 避免"所有未知都进待审"把 episodic 淹没。粗 attribute 供待审记录与后续 ingest(不塞进经验记忆)。
_PREDICATE_ATTRIBUTE: tuple[tuple[tuple[str, ...], str], ...] = (
    (("真实身份", "真身", "本名", "真名", "凶手", "内奸", "卧底", "奸细", "假扮",
      "其实是", "竟是", "实为"), "identity"),
    (("父亲", "母亲", "爹是", "娘是", "儿子", "女儿", "私生子", "私生女", "亲生",
      "血脉", "生父", "生母", "骨肉", "血亲"), "kinship"),
    (("死了", "早就死", "已死", "丧命", "身亡", "遇害", "被杀", "还活着", "没死", "未死"),
     "life_status"),
    (("背叛", "出卖", "通敌", "叛变", "叛徒", "密谋", "勾结"), "loyalty"),
    (("杀了", "杀死", "害死", "毒死", "下毒", "灭口"), "causation"),
    (("爱着", "爱上", "暗恋", "心悦"), "relationship"),
)
_RISK_PREDICATES: tuple[str, ...] = tuple(
    p for group, _attr in _PREDICATE_ATTRIBUTE for p in group)


def _risk_predicate_hits(text: str) -> list[str]:
    t = text or ""
    return [p for p in _RISK_PREDICATES if p in t]


def _risk_attribute(risk_hits: list[str]) -> str | None:
    """把命中的风险谓词粗映射为属性类(identity/kinship/life_status/…),供待审记录参考。"""
    for pred in risk_hits:
        for group, attr in _PREDICATE_ATTRIBUTE:
            if pred in group:
                return attr
    return None


def build_entity_index(store) -> list[tuple[str, list[str]]]:
    """从领域表构建 (entity_id, 名字/别名列表) 索引,供文本反查登记实体(角色 + 地点)。
    单字名(甲/乙)易误配进他词,但确是登记名,按登记语义保留;召回>洁癖(限知红线优先)。"""
    idx: list[tuple[str, list[str]]] = []
    for e in store.all_entities():
        names = [e.name] + list((getattr(e, "traits", None) or {}).get("aliases") or [])
        names = [n for n in names if n and str(n).strip()]
        if names:
            idx.append((e.id, names))
    return idx


def entity_hits_in(text: str, entity_index: list[tuple[str, list[str]]]) -> list[str]:
    t = text or ""
    hits: list[str] = []
    for eid, names in entity_index:
        if any(n in t for n in names):
            hits.append(eid)
    return hits


# 显式 classification → route 归一(material 归 reference)。
_EXPLICIT_ROUTES = {
    "canonical_claim": "canonical_claim", "authority_claim": "canonical_claim",
    "canonical": "canonical_claim", "working": "working", "episodic": "episodic",
    "procedural": "procedural", "reference": "reference", "material": "reference",
    "uncertainty": "uncertainty",
}

# route → (kind, scope_type, confidence, importance)。uncertainty 信心<=0.5(不作事实注入)。
_ROUTE_SPEC = {
    "working": ("working", "thread", 0.7, 2),
    "episodic": ("episodic", "thread", 0.8, 3),
    "procedural": ("procedural", "work", 0.9, 3),
    "reference": ("reference", "work", 0.6, 2),
    "uncertainty": ("uncertainty", "work", 0.4, 1),
}


def _route_of(text: str, explicit: str | None, *,
              entity_hits: list[str] | None = None, risk_hit: bool = False) -> str:
    if explicit:
        r = _EXPLICIT_ROUTES.get(explicit.strip().lower())
        if r:
            return r
    t = text or ""
    # 对冲优先:'我猜/可能' 的揣测是不确定,不作事实注入(即便句里有正典谓词也是揣测,不待审)。
    if any(m in t for m in _UNCERTAINTY_MARKERS):
        return "uncertainty"
    # 强显式正典短语(无需实体):真实身份/其实是…
    if any(m in t for m in _CANONICAL_MARKERS):
        return "canonical_claim"
    # 正典嫌疑:登记实体 + 高风险稳定断言谓词 → 待审(P0 限知红线,守知情倒灌)。
    if entity_hits and risk_hit:
        return "canonical_claim"
    if any(m in t for m in _AUTHOR_WRITING_PREFERENCE_MARKERS):
        return "procedural"
    if any(m in t for m in _PROCEDURAL_MARKERS):
        return "procedural"
    if any(m in t for m in _WORKING_MARKERS):
        return "working"
    if any(m in t for m in _EPISODIC_MARKERS):
        return "episodic"
    return "episodic"                    # 兜底:未知归 episodic(经验),红线由上面实体+谓词判据守


def classify(text: str, explicit: str | None = None, *,
             entity_hits: list[str] | None = None, risk_hit: bool = False) -> Classification:
    route = _route_of(text, explicit, entity_hits=entity_hits, risk_hit=risk_hit)
    if route == "canonical_claim":
        return Classification(route=route, kind="", scope_type="work",
                              confidence=1.0, importance=4)
    kind, scope_type, conf, imp = _ROUTE_SPEC[route]
    return Classification(route=route, kind=kind, scope_type=scope_type,
                          confidence=conf, importance=imp)


# 事件类型 → memory_item.source_type(turn 必须落 "chat_turn",对齐 Step 1 验收)。
_SOURCE_TYPE = {"turn": "chat_turn", "write": "write", "approval": "approval",
                "save": "save", "navigation": "navigation"}

# 每 N 完成 turn 触发一次 consolidate(计划 Step 4)。
CONSOLIDATE_EVERY = 8


class MemoryCapture:
    """幂等捕获 + 同步 drain + working summary 压缩。挂点见 app.py chat_write_post。"""

    def __init__(self, store):
        self.store = store
        self._entity_idx_cache: list[tuple[str, list[str]]] | None = None

    # ── 领域信号(P0 红线判据 + P1 linked_ids 生产接线,三处复用)────────
    @property
    def _entity_index(self) -> list[tuple[str, list[str]]]:
        """登记角色/地点名索引(每实例懒建一次,请求级新鲜;best-effort 失败降级空)。"""
        if self._entity_idx_cache is None:
            try:
                self._entity_idx_cache = build_entity_index(self.store)
            except Exception:
                _log.warning("领域实体索引构建失败,红线/linked_ids 判据降级空", exc_info=True)
                self._entity_idx_cache = []
        return self._entity_idx_cache

    def _signals(self, text: str) -> tuple[list[str], list[str]]:
        """返回 (命中登记实体 id, 命中风险谓词)。守 P0 红线 + 喂 P1 linked_ids。"""
        return entity_hits_in(text, self._entity_index), _risk_predicate_hits(text)

    def _classify(self, text: str, explicit: str | None) -> tuple[Classification, list[str], list[str]]:
        ents, risks = self._signals(text)
        return classify(text, explicit, entity_hits=ents, risk_hit=bool(risks)), ents, risks

    # ── 捕获入口 ───────────────────────────────────────────────────
    def capture_event(self, event: MemoryEvent) -> dict:
        """入队(幂等)+ 同步 drain 单条。全程 best-effort:工作者异常不外抛(不阻断对话)。"""
        try:
            self.store.enqueue_memory_event(
                event.event_id, event.work, event.event_type, event.payload,
                thread_id=event.thread_id)
        except Exception:
            _log.warning("记忆事件入队失败(忽略,不阻断对话): %s", event.event_id, exc_info=True)
            return {"status": "enqueue_failed"}

        existing = self.store.get_memory_event(event.event_id)
        if existing and existing.get("status") == "complete":
            return {"status": "complete", "idempotent": True}   # 幂等:已处理过,不重复

        result = self._drain_one(event.event_id, event.work, event.event_type,
                                 event.payload, event.thread_id)
        # 每 N 完成 turn 触发一次 consolidate(掉线残留 drain + working summary 压缩)。
        if event.event_type == "turn" and result.get("status") == "complete":
            self._maybe_consolidate(event.work, event.thread_id)
        return result

    # ── 单事件同步 drain(状态机核心)────────────────────────────────
    def _drain_one(self, event_id: str, work: str, event_type: str,
                   payload: dict, thread_id: str | None, *, claimed: bool = False) -> dict:
        # claimed=True:调用方(consolidate 的 claim_pending_events)已 CAS 置 processing +
        # attempts+1,此处不再 begin_processing_event(否则 attempts 双累加,见顺手修)。
        if not claimed:
            self.store.begin_processing_event(event_id)
        try:
            info = self._route(work, event_type, payload or {}, thread_id, event_id)
            self.store.mark_event_complete(event_id)
            return {"status": "complete", **info}
        except Exception as ex:
            # 工作者失败不阻断对话:留 failed/error/attempts 在 outbox + runtime-status 可见。
            self.store.mark_event_failed(event_id, f"{type(ex).__name__}: {ex}")
            _log.warning("记忆捕获工作者失败(留 outbox 可重试,不阻断对话): event=%s",
                         event_id, exc_info=True)
            return {"status": "failed", "error": str(ex)}

    def _route(self, work: str, event_type: str, payload: dict,
               thread_id: str | None, event_id: str) -> dict:
        # 触发型事件:直接 consolidate(compress 前 flush / 会话结束)。
        if event_type in ("compress", "session_end"):
            self.consolidate_thread(thread_id, work=work)
            return {"route": event_type}

        text = payload.get("text") or ""
        decision, ents, risks = self._classify(text, payload.get("classification"))

        # 限知红线(P0):正典揭示绝不进 memory_item,一律进待审队列。
        # entity/attribute 优先取显式 payload,否则用领域反查首个实体 + 风险谓词粗属性(供待审参考)。
        if decision.route == "canonical_claim":
            self.store.add_pending_authority_claim(
                work, text,
                entity=payload.get("entity") or (ents[0] if ents else None),
                attribute=payload.get("attribute") or _risk_attribute(risks),
                value=payload.get("value"), source_type=_SOURCE_TYPE.get(event_type, event_type),
                source_id=event_id, thread_id=thread_id)
            return {"route": "canonical_claim"}

        # 经验五类 → memory_item。P1 生产接线:
        #   · linked_ids 缺省用领域反查命中的登记实体(focus 加权对真机记忆生效);
        #   · known_from 由挂点传入的当前章填(限知门对捕获记忆生效,防知情倒灌);
        #   · attribute【故意不硬凑】——高风险断言已前置拦入待审,进此处的经验记忆自由文本
        #     属性抽取待后续,错误 attribute 会误压制有效经验(见模块顶注实施状态)。
        scope_type, scope_id = self._scope(decision, work, thread_id)
        linked = payload.get("linked_ids")
        if not linked:
            linked = ents or None
        self.store.add_memory_item(
            work=work, kind=decision.kind, text=text,
            scope_type=scope_type, scope_id=scope_id,
            source_type=_SOURCE_TYPE.get(event_type, event_type), source_id=event_id,
            confidence=decision.confidence, importance=decision.importance,
            provenance=payload.get("provenance"), linked_ids=linked,
            entity=payload.get("entity"), attribute=payload.get("attribute"),
            valid_from=payload.get("valid_from"), valid_to=payload.get("valid_to"),
            known_from=payload.get("known_from"), known_to=payload.get("known_to"))
        return {"route": decision.kind}

    @staticmethod
    def _scope(decision: Classification, work: str, thread_id: str | None) -> tuple[str, str]:
        if decision.scope_type == "thread" and thread_id:
            return "thread", thread_id
        return "work", work

    # ── 批处理端:consolidate ──────────────────────────────────────
    def _maybe_consolidate(self, work: str, thread_id: str | None) -> None:
        if not thread_id:
            return
        try:
            # P2:轻量 count(不载 payload)算水位——长篇破千 turn 也不拉全量行。
            # 边界并发下 count 可能错过恰逢 %8 的时刻,session_end/pre_compress 会兜底自愈。
            n = self.store.count_memory_events(
                work=work, thread_id=thread_id, event_type="turn", status="complete")
            if n and n % CONSOLIDATE_EVERY == 0:
                self.consolidate_thread(thread_id, work=work)
        except Exception:
            _log.warning("每 %d 轮 consolidate 触发失败(忽略)", CONSOLIDATE_EVERY, exc_info=True)

    def consolidate_thread(self, thread_id: str | None, work: str | None = None) -> dict:
        """drain 掉线残留(failed/pending 的 turn 事件)+ 从已完成 turn 压缩 working summary。
        幂等:working_summary 按 (work,thread) 唯一 UPSERT;残留 drain 只碰未完成事件。"""
        work = work or "main"
        if not thread_id:
            return {"through_turn": 0}

        # 0) 硬崩溃孤儿回收:进程在 begin_processing→mark_complete 窗口被 SIGKILL/OOM 时,
        #    事件永久卡 'processing'(claim_pending_events 只认领 pending/failed,结构性排除
        #    processing),经验记忆静默永久丢失、count_failed 看不见。起手把陈旧 processing 复位
        #    failed 可回收,再由下面的 claim 重 drain 找回。同步单进程模型:reaper 先于本次自身
        #    drain,此刻任何 processing 皆为上一进程崩溃遗留(非本次在途),复位安全(见 store 方法注)。
        self.store.reclaim_stale_processing_events(
            work=work, thread_id=thread_id, event_type="turn")

        # 1) 掉线残留 drain(仅 turn,避免把 compress/session_end 事件卷进死循环)。
        #    claimed=True:claim 已置 processing + attempts+1,_drain_one 不再重复 begin(防双累加)。
        for ev in self.store.claim_pending_events(
                work=work, thread_id=thread_id, event_type="turn"):
            self._drain_one(ev["event_id"], ev["work"], ev["event_type"],
                            ev.get("payload") or {}, ev.get("thread_id"), claimed=True)

        # 2) 从已完成 turn 压缩工作摘要。
        events = self.store.list_memory_events(
            work=work, thread_id=thread_id, event_type="turn", status="complete", limit=1000)
        goals, open_tasks, decisions, assumptions = [], [], [], []
        for ev in events:
            payload = ev.get("payload") or {}
            text = payload.get("text") or ""
            if not text:
                continue
            # 与捕获时同口径(带领域信号),使正典嫌疑句不误入工作摘要 decisions。
            route = self._classify(text, payload.get("classification"))[0].route
            if route == "working":
                open_tasks.append(text)          # 被下个工作目标 supersede(保尾部近若干条)
            elif route == "episodic":
                decisions.append(text)
            elif route == "uncertainty":
                assumptions.append(text)
            elif route == "procedural":
                goals.append(text)
            # canonical_claim / reference 不入工作摘要

        open_tasks = _tail_unique(open_tasks, 5)
        goals = _tail_unique(goals, 5)
        decisions = _tail_unique(decisions, 8)
        assumptions = _tail_unique(assumptions, 5)
        summary = "；".join(decisions[-3:] + open_tasks[-2:])[:500]
        through = len(events)
        self.store.upsert_working_summary(
            work, thread_id, through_turn=through, goals=goals, open_tasks=open_tasks,
            decisions=decisions, assumptions=assumptions, summary=summary)
        return {"through_turn": through, "goals": goals, "open_tasks": open_tasks,
                "decisions": decisions, "assumptions": assumptions, "summary": summary}

    def flush_before_compress(self, thread_id: str | None, work: str | None = None) -> dict:
        """Hermes on_pre_compress 前触发:等价 consolidate_thread(压缩前先固化工作摘要)。
        直呼路径 best-effort:压缩前 flush 失败不该拖垮压缩,失败只告警返回空。"""
        try:
            return self.consolidate_thread(thread_id, work=work)
        except Exception:
            _log.warning("flush_before_compress 失败(忽略,不阻断压缩)", exc_info=True)
            return {"through_turn": 0}


def _tail_unique(items: list[str], keep: int) -> list[str]:
    """去重(保最后出现)后取尾部 keep 条——working 的 supersede 语义:新目标压过旧目标。"""
    seen: set[str] = set()
    out: list[str] = []
    for x in reversed(items):
        if x not in seen:
            seen.add(x)
            out.append(x)
    out.reverse()
    return out[-keep:] if keep and len(out) > keep else out

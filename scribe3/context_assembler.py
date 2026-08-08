"""统一上下文与记忆系统 · 可预算、可追溯的 ContextAssembler(Task 7)。

为什么要一个"组装器"而不是继续散点拼 prompt:
- 历史教训(文档1 发现3):每新开一个注入点就泄露过一次限知秘密。散点拼装
  没有统一的预算、没有统一的溯源、没有统一的秘密屏蔽——同一条纪律要在 N 个
  函数里各写一遍,漂移不可避免。
- 本模块把"取什么 → 裁到多少 → 从哪来 → 有没有被屏蔽"收敛成一个确定性管线:
  输入 ContextSnapshot(不可变身份指纹)+ 可选 MemoryRetriever(Task 8),
  输出 ContextEnvelope(八块定序、总额有上限、每块可溯源、被省略项留痕)。

八块固定顺序(即 context_models.ContextBlock 的 Literal 顺序,不可自造分区):
  focus → global → canonical → recent → procedural → reference →
  uncertainty → provenance
每块有硬上限(BLOCK_BUDGETS),八块上限之和 == 默认总预算 10_000:
  即"每块都顶格时恰好用满总额",所以默认预算下八块永远齐全;只有把
  token_budget 调到小于八块之和时,靠后的块才会被总额门整块挤掉(降级可审计)。

三条宪法级不变量:
1. 正典优先:canonical 与冲突的 episodic 撞车 → canonical 入 canonical 块,
   episodic 进 envelope.omitted 且 reason="superseded_by_canonical"。冲突判定:
   同 (entity, attribute),或 canonical 显式 supersedes 该 episodic 的 source_id。
2. 限知秘密屏蔽:snapshot.focalizer 非空(限知章)时,canonical 块只注入焦点者
   知识帧内可见事实,secret value 物理屏蔽(复用 knowledge.project_frame 的既有
   投影 + reveal_secret=False 掩码做法);被屏蔽的源仍以 masked=True 留痕,而非
   凭空消失(context_models 的留痕范式)。
3. 无 retriever 不得崩:retriever=None 时 canonical/recent/procedural/reference/
   uncertainty 降级为直查 store 领域表;canonical 必须仍有真数据(facts/promises/
   events),其余可为空块。

token 估算:见 estimate_tokens——中文场景用 len(text) 作 1 字符≈1 token 的保守近似
(偏高 → 宁可少放也不超预算)。全模块统一走这一个函数。
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from scribe3.context_models import (
    ContextBlock,
    ContextEnvelope,
    ContextSnapshot,
    ContextSource,
)

_log = logging.getLogger("scribe3")

# 八块固定预算(顺序即 context_models.ContextBlock 的 Literal 顺序,dict 保序)。
# 上限之和 = 800+1200+2800+1600+900+1400+500+800 = 10_000 = 默认 token_budget:
# 每块顶格恰好用满,所以默认预算下八块永远齐全(见模块 docstring)。
BLOCK_BUDGETS: dict[str, int] = {
    "focus": 800,
    "global": 1200,
    "canonical": 2800,
    "recent": 1600,
    "procedural": 900,
    "reference": 1400,
    "uncertainty": 500,
    "provenance": 800,
}

# 各块标题:进正文也计入预算(estimate_tokens 含标题),空块不渲染标题(见 _render_block)。
_HEADERS: dict[str, str] = {
    "focus": "## 焦点(此刻在看)",
    "global": "## 全局(北极星·当前弧光·开放伏笔·主要角色)",
    "canonical": "## 权威事实(正典表:事实/事件/承诺/知识帧)",
    "recent": "## 近期(工作摘要·近期事件/决策)",
    "procedural": "## 工艺方法(已采纳的写作方法/教训)",
    "reference": "## 参考素材(借鉴非事实,不得当作故事内事实)",
    "uncertainty": "## 不确定(冲突·低信心·待确认)",
    "provenance": "## 溯源清单(来源 id·修订·时态·选中理由)",
}


def _author_preference_constraint(text: str) -> str:
    """把已检索的显式作者写作偏好编译成生成期可执行约束。

    记忆检索证明“系统看见了”，但普通资料式的一行不足以保证模型把偏好落实到正文。
    仅提升带明确偏好标签的条目；剧情事实、一般教训仍保持原有 procedural 渲染，避免
    把所有旧记忆误当硬约束。这里不要求复读原句，而要求在本次正文中呈现可审查的动作
    或因果结果，作者仍可在后续质量裁决中否决。
    """
    cleaned = (text or "").strip()
    if "作者偏好" not in cleaned and "写作偏好" not in cleaned:
        return f"- {cleaned}"
    return (
        "- 【作者已确认的本书写作偏好｜本次正文必须执行】" + cleaned + "\n"
        "  这是生成约束，不向读者解释来源，也不要机械复读原句；"
        "须将其落实为可观察的动作或因果，并在本次正文中实际发生。"
    )

# 参考块的固定免责前缀:素材是"借鉴非事实",任何相位都必须带此边界(计划 Step 3)。
_REFERENCE_DISCLAIMER = "(以下为可借鉴的参考素材,借鉴非照搬,更不得当作故事内事实)"

# 限知章 secret value 的物理屏蔽占位:进 prompt 的只有占位,真值物理不出现。
_SECRET_PLACEHOLDER = "(私密·帧外屏蔽)"

_MAX_CANDIDATES = 24   # 单次向 retriever 要多少候选(粗放上限,再由块预算精裁)


def estimate_tokens(text: str) -> int:
    """token 估算(全模块唯一口径)。

    近似依据:中文语料下,主流分词器多把 1 个汉字切成 ~1 个 token(标点/数字更省),
    故用 len(text) 作【保守】上界——它对中文偏高一点,对英文明显偏高,但方向一致:
    宁可高估让我们少放一点,也不要低估把 prompt 撑爆预算。预算是"安全阀"不是"精算表",
    保守即正确。全模块的裁剪/累计/溢出判定都必须走这一个函数,禁止各处 len() 各算各的。
    """
    return len(text or "")


# ---------- 组装内部工作表示(不进 envelope,仅供裁剪/溯源) ----------

@dataclass
class _Item:
    """一段候选文本 + 其溯源。block 组装的最小可裁剪单元。"""
    text: str
    source: ContextSource


def _truncate_items(header: str, items: list[_Item], budget: int
                    ) -> tuple[list[_Item], list[_Item]]:
    """把 items 贪心裁进 budget(含 header 成本),返回 (保留, 溢出)。
    保留顺序即候选顺序(retriever 已按相关度排),溢出者留给调用方记 omitted。"""
    kept: list[_Item] = []
    dropped: list[_Item] = []
    used = estimate_tokens(header)
    for it in items:
        cost = estimate_tokens("\n" + it.text)
        if used + cost <= budget:
            kept.append(it)
            used += cost
        else:
            dropped.append(it)
    return kept, dropped


def _render_block(name: str, kept: list[_Item]) -> ContextBlock:
    """把保留下来的 items 渲染成 ContextBlock。
    空块(无 item)→ text="" / token=0:标题不单独占预算(避免空块白吃 budget),
    但块本身仍在 envelope 里(八块定序合同要求块必现,哪怕为空)。"""
    if not kept:
        return ContextBlock(name=name, text="", token_estimate=0, sources=[])
    # digest 的对象是实际选入的 _Item.text，而非原始候选或带 header 的 block 文本。
    # 这样 manifest 可证明每一个来源参与了哪一段最终输入，却不保存任何正文。
    for item in kept:
        item.source.content_digest = hashlib.sha256(
            item.text.encode("utf-8")
        ).hexdigest()
    body = "\n".join(it.text for it in kept)
    text = f"{_HEADERS[name]}\n{body}"
    return ContextBlock(name=name, text=text, token_estimate=estimate_tokens(text),
                        sources=[it.source for it in kept])


def _omit(item: _Item, block_name: str, reason: str) -> dict:
    """被省略项的审计记录:只记来源身份 + 原因,不记正文(正文可能含秘密)。"""
    digest = item.source.content_digest or hashlib.sha256(
        item.text.encode("utf-8")
    ).hexdigest()
    return {
        "source_id": item.source.source_id,
        "source_kind": item.source.source_kind,
        "block": block_name,
        "reason": reason,
        "work": item.source.work,
        "revision": item.source.revision,
        "masked": item.source.masked,
        "content_digest": digest,
    }


# ---------- 正典优先冲突裁决 ----------

def _conflict_keys(cand) -> set[tuple[str, str]]:
    """从候选 provenance 提取 (entity, attribute) 冲突键。"""
    keys: set[tuple[str, str]] = set()
    for p in (getattr(cand, "provenance", None) or []):
        e, a = p.get("entity"), p.get("attribute")
        if e and a:
            keys.add((e, a))
    return keys


def _supersede_ids(canonical_cands) -> set[str]:
    """canonical 候选显式声明"取代"了哪些 source_id(provenance.supersedes 或候选级 supersedes)。"""
    ids: set[str] = set()
    for c in canonical_cands:
        for p in (getattr(c, "provenance", None) or []):
            for sid in (p.get("supersedes") or []):
                ids.add(sid)
        for sid in (getattr(c, "supersedes", None) or []):
            ids.add(sid)
    return ids


def _secret_fact_ids(store) -> set[str]:
    """从 store 派生【权威】secret fact id 集——"是否秘密"的裁决权归 store,不归 retriever。

    C1(宪法级):候选路径此前只信 retriever 传的 provenance.secret + "帧外"两条判据,
    严格弱于 store 路径的 `bool(f.secret)`:
      · 全知章(focalizer=None)→ 帧判据失效,retriever 漏标即秘密真值原文入 prompt;
      · 限知章但秘密在焦点者帧【内】且 retriever 漏标 → 同样漏。
    修法:凡候选 source_id ∈ 本集,一律屏蔽,不论 focalizer 是否为空、不论 retriever 怎么标。

    U-011(2026-07-15,作者要 fail-loud):此前"查询异常退回空集"是**反向不安全**——
    空集=秘密判据失效=真值可能入 prompt(fail-open 泄密方向)。已删除吞异常:查询失败
    直接【抛】,让 assemble 崩到 SSE error 帧、前端报"限知判定失败,本章生成中止",
    而不是悄悄漏防。宁可当场炸给作者看,也不要静默降级把泄密躲过去。
    """
    ids: set[str] = set()
    # SurrealStore:宽扫所有 secret 命题(含带 valid_to 窗口的历史秘密),最完整。
    # 有 _query = 权威路径,失败不吞(WHERE secret=true 炸了 → 往上抛)。
    q = getattr(store, "_query", None)
    if callable(q):
        rows = q("SELECT meta::id(id) AS local FROM proposition WHERE secret = true")
        ids |= {f"fact:{r['local']}" for r in (rows or [])}
    # 公共 API(兼容内存 World 及 _query 不可用):当前有效的 secret。同样不吞异常。
    for f in (store.facts_at(99999) or []):
        if getattr(f, "secret", False):
            ids.add(f.id)
    return ids


def _is_bridge_mirror(entity_id: str, attribute: str) -> bool:
    """结构性判断 (entity_id, attribute) 是否 codex_secret_bridge 造的势力 secret 字段镜像。

    委托 `codex_secret_bridge.is_faction_bridge_mirror`(单一真相源,与
    `app._is_faction_bridge_mirror` 同判据同源,防两处漂移)——canonical 不是这些镜像的
    授权注入通道,那是 `app._codex_block`/`_faction_prompt_block` 的职责(已带三档可见性、
    正确的中文字段标签);canonical 是通用"权威事实"直查/检索通道,分不清楚这些字段的
    三档语义,故无条件把它们从 canonical 候选/事实里剔除,不论 focalizer 有无、不论
    知情与否(与旧链 M6 转储泄露修复对称)。局部 import:每次调用都从源模块取最新绑定,
    不缓存旧引用(供测试 monkeypatch 源函数验证委托关系)。"""
    from scribe3.codex_secret_bridge import is_faction_bridge_mirror
    return is_faction_bridge_mirror(entity_id, attribute)


def _resolve_canonical_conflicts(candidates) -> tuple[list, list]:
    """正典优先裁决:返回 (保留候选, 被正典取代的 episodic 候选)。

    冲突判定(计划 Task 8 原文,本任务先落地可判定版本):
      episodic 候选与任一 canonical 候选同 (entity, attribute),
      或其 source_id 落在某 canonical 的 supersedes 集合里 → 判为被取代。
    只有 episodic 会被取代;canonical 恒保留(它就是权威)。
    """
    canonicals = [c for c in candidates if c.source_kind == "canonical"]
    canon_keys: set[tuple[str, str]] = set()
    for c in canonicals:
        canon_keys |= _conflict_keys(c)
    superseded_ids = _supersede_ids(canonicals)

    kept, superseded = [], []
    for c in candidates:
        if c.source_kind == "episodic":
            hit_key = bool(_conflict_keys(c) & canon_keys)
            hit_sup = c.source_id in superseded_ids
            if hit_key or hit_sup:
                superseded.append(c)
                continue
        kept.append(c)
    return kept, superseded


# ---------- 组装器主体 ----------

class ContextAssembler:
    """把快照 + 记忆候选组装成 8 块定序、有预算、可溯源的 ContextEnvelope。

    store:领域 store(SurrealStore 或兼容 World),供无 retriever 时降级直查。
    retriever:Task 8 的 MemoryRetriever(可 None)。协议:
        retrieve(work: str, snapshot_dict: dict, query: str, k: int) -> list[候选]
      候选鸭子类型:source_kind / source_id / text / work / provenance:list[dict]
      + 可选 confidence / importance / observed_at / revision / supersedes。
    token_budget:总预算(默认 10_000 = 八块上限之和)。
    """

    def __init__(self, store, retriever=None, token_budget: int = 10_000):
        self.store = store
        self.retriever = retriever
        self.token_budget = token_budget

    # --- 对外唯一入口 ---
    def assemble(self, snapshot: ContextSnapshot, user_query: str,
                 mode: str = "discussion", *,
                 retrieval_out: dict | None = None,
                 forbidden_source_kinds: tuple[str, ...] = ()) -> ContextEnvelope:
        # retrieval_out(Task 16 最后一厘米,可选可变收集器,缺省 None):非 None 时把本次
        # 检索的【完整 RetrievalResult】(含 rejected/channels)回填 retrieval_out["result"],
        # 供 _assemble_write_instructions_v1 落 memory_trace 给 ContextInspector 溯源。
        # 纯观测副作用——收集与否,candidates/envelope【逐字节等价】(见 _retrieve 注记),
        # 缺省 None → 其余调用方(讨论/导航路径)与接线前完全一致。
        # 1) 拉候选(retriever 缺失→合法降级空;retriever 存在但检索抛错→异常上抛,
        #    不再静默降级,见 _retrieve。U-011,2026-07-15,作者要 fail-loud)
        candidates = self._retrieve(snapshot, user_query, retrieval_out=retrieval_out)
        policy_omitted: list[dict] = []
        forbidden = set(forbidden_source_kinds)
        if forbidden:
            # 必须在 source adapter 改名前按候选的原始 kind 过滤：
            # episodic/working 稍后都会映射为 recent，若只看最终
            # ContextSource，请求对原始 kind 的禁用会被绕过。
            allowed_candidates = []
            source_blocks = {
                "working": "recent",
                "episodic": "recent",
            }
            for candidate in candidates:
                source_kind = str(getattr(candidate, "source_kind", "") or "")
                if source_kind in forbidden:
                    policy_omitted.append({
                        "source_id": str(getattr(candidate, "source_id", "") or ""),
                        "source_kind": source_kind,
                        "block": source_blocks.get(source_kind, source_kind),
                        "reason": "forbidden_source_kind",
                        "work": str(getattr(candidate, "work", "") or snapshot.work),
                        "revision": getattr(candidate, "revision", None),
                        "masked": bool(getattr(candidate, "masked", False)),
                        "content_digest": hashlib.sha256(
                            str(getattr(candidate, "text", "") or "").encode("utf-8")
                        ).hexdigest(),
                    })
                else:
                    allowed_candidates.append(candidate)
            candidates = allowed_candidates
        kept_cands, superseded = _resolve_canonical_conflicts(candidates)
        by_kind: dict[str, list] = defaultdict(list)
        for c in kept_cands:
            by_kind[c.source_kind].append(c)

        # 2) 逐块产出候选 item(此时不裁剪,先备齐)
        items: dict[str, list[_Item]] = {}
        items["focus"] = self._focus_items(snapshot, user_query, mode)
        items["global"] = self._global_items(snapshot)
        items["canonical"] = self._canonical_items(snapshot, by_kind.get("canonical"))
        items["recent"] = self._recent_items(
            snapshot, by_kind.get("working", []) + by_kind.get("episodic", []))
        items["procedural"] = self._procedural_items(snapshot, by_kind.get("procedural"))
        items["reference"] = self._reference_items(snapshot, by_kind.get("reference"))
        items["uncertainty"] = self._uncertainty_items(
            snapshot, by_kind.get("uncertainty"), superseded)
        # Creative Context Policy 的禁用来源必须在 render/provenance 之前
        # 移除；ContextBlock 只保留摘要，组装后已无法无损删掉对应正文。
        # 被禁用项只留不含正文的 omitted 审计记录。
        def filter_forbidden_items() -> None:
            if not forbidden:
                return
            for block_name, block_items in items.items():
                kept: list[_Item] = []
                for item in block_items:
                    if item.source.source_kind in forbidden:
                        policy_omitted.append(_omit(
                            item, block_name, "forbidden_source_kind"))
                    else:
                        kept.append(item)
                items[block_name] = kept

        filter_forbidden_items()

        # provenance 汇总前七块的来源(裁剪前的全量视图,作为清单更完整)
        items["provenance"] = self._provenance_items(items)
        # provenance 是上一步新生成的派生 item；再过一次同一禁用门，
        # 确保 forbidden_source_kinds=("provenance",) 也真正不进模型输入。
        filter_forbidden_items()

        # 3) 预算分配:每块先裁到自身上限,再受总预算门控(靠后块可能被整块挤掉)
        blocks, omitted, _used = self._allocate(items)
        omitted = policy_omitted + omitted

        # 4) 正典取代的 episodic 记入 omitted(宪法级审计:为什么没进 canonical)
        for c in superseded:
            omitted.append({
                "source_id": c.source_id,
                "source_kind": c.source_kind,
                "block": "canonical",
                "reason": "superseded_by_canonical",
                "work": str(getattr(c, "work", "") or snapshot.work),
                "revision": getattr(c, "revision", None),
                "masked": bool(getattr(c, "masked", False)),
                "content_digest": hashlib.sha256(
                    str(getattr(c, "text", "") or "").encode("utf-8")
                ).hexdigest(),
            })

        total = sum(b.token_estimate for b in blocks)
        env_hash = compute_envelope_hash(blocks, snapshot)
        return ContextEnvelope(
            snapshot=snapshot,
            blocks=blocks,
            total_token_estimate=total,
            omitted=omitted,
            assembled_at=datetime.now(timezone.utc),
            envelope_hash=env_hash,
        )

    # --- 候选拉取 ---
    def _retrieve(self, snapshot: ContextSnapshot, user_query: str,
                  retrieval_out: dict | None = None) -> list:
        # U-011(2026-07-15,作者要 fail-loud):retriever=None 是合法设计态(fabric 关时,
        # 见模块 docstring 不变量3),此分支保留不动。但此前"retriever 存在、retrieve()
        # 抛异常"也被同一 try/except 悄悄吞成 []——这正是"以为主编有全套记忆,其实这轮
        # 悄悄只有正典"的字面实现:调用方拿到的空候选列表,与"这本书真没有可检索记忆"
        # 完全无法区分。已删除该 try/except:检索失败必须【抛】,不能和"设计态空"混同。
        if self.retriever is None:
            return []
        # 默认路径(无收集器):走 Task 7 协议方法 retrieve()——与接线前【逐字节等价】。
        if retrieval_out is None:
            out = self.retriever.retrieve(
                snapshot.work, snapshot.canonical_payload(),
                user_query or "", _MAX_CANDIDATES)
            return list(out or [])
        # 收集器路径(Task 16 Inspector 溯源):拿【完整 RetrievalResult】(含 rejected/
        # channels)回填 retrieval_out,供落 memory_trace。selected 与 retrieve() 逐字节
        # 相同(retrieve() ≡ retrieve_full_cached(...).candidates[:k],同缓存键、同 k),
        # 故 envelope 字节不变——收集只是把已算出的 rejected/channels 顺带暴露出来。
        result = self._retrieve_full(snapshot, user_query)
        retrieval_out["result"] = result
        return list((getattr(result, "selected", None) or [])[:_MAX_CANDIDATES])

    def _retrieve_full(self, snapshot: ContextSnapshot, user_query: str):
        """拿一次检索的完整 RetrievalResult(含 rejected/channels,Task 16 落 memory_trace 用)。

        retriever 暴露 retrieve_full_cached(生产 MemoryRetriever)则直用——它与协议方法
        retrieve() 走同一缓存键、同一裁决(剧透门 known_from / 正典压制 / 秘密屏蔽都在其内),
        故 selected 与 retrieve() 逐字节一致;仅暴露 retrieve() 的精简/桩 retriever 则用其
        list 包一层 RetrievalResult(rejected 空,best-effort 降级)。"""
        from scribe3.memory_models import RetrievalQuery, RetrievalResult
        r = self.retriever
        full = getattr(r, "retrieve_full_cached", None)
        if callable(full):
            return full(RetrievalQuery(
                work=snapshot.work, snapshot=snapshot.canonical_payload() or {},
                query=user_query or "", k=_MAX_CANDIDATES))
        out = r.retrieve(snapshot.work, snapshot.canonical_payload(),
                         user_query or "", _MAX_CANDIDATES)
        return RetrievalResult(selected=list(out or []))

    # --- 预算分配 ---
    def _allocate(self, items: dict[str, list[_Item]]
                  ) -> tuple[list[ContextBlock], list[dict], int]:
        kept_blocks: list[ContextBlock] = []
        omitted: list[dict] = []
        used = 0
        for name in BLOCK_BUDGETS:   # dict 保序 == 八块固定顺序
            keep, drop = _truncate_items(_HEADERS[name], items.get(name, []),
                                         BLOCK_BUDGETS[name])
            for it in drop:
                omitted.append(_omit(it, name, "token_budget"))
            block = _render_block(name, keep)
            if used + block.token_estimate <= self.token_budget:
                kept_blocks.append(block)
                used += block.token_estimate
            else:
                # 总预算放不下整块 → 该块所有来源都记 token_budget 省略
                for it in keep:
                    omitted.append(_omit(it, name, "token_budget"))
        return kept_blocks, omitted, used

    # ---------------- 逐块取数 ----------------

    def _focus_items(self, snapshot: ContextSnapshot, user_query: str,
                     mode: str) -> list[_Item]:
        """focus:此刻在看什么 + 当前查询 + 焦点条目直接查(章/角色)。"""
        f = snapshot.focus
        src = ContextSource(source_id=f"focus:{f.type}:{f.id}", source_kind="focus",
                            work=snapshot.work, revision=f.source_revision)
        lines = [f"- 焦点:{f.type} · {f.label or f.id}(mode={mode})"]
        if snapshot.chapter is not None:
            lines.append(f"- 当前第 {snapshot.chapter} 章"
                         + (f",限知焦点者 {snapshot.focalizer}" if snapshot.focalizer else ""))
        if (user_query or "").strip():
            lines.append(f"- 作者此刻问:{user_query.strip()[:200]}")
        # 焦点条目直接查(fail-soft:查不到不影响 focus 块)
        detail = self._focus_detail(snapshot)
        if detail and f.type != "chapter":
            lines.append(f"- {detail}")
        out = [_Item("\n".join(lines), src)]
        if detail and f.type == "chapter" and snapshot.chapter is not None:
            out.append(_Item(
                detail,
                ContextSource(
                    source_id=f"chapter:{snapshot.chapter}:outline",
                    source_kind="focus",
                    work=snapshot.work,
                    revision=f.source_revision,
                ),
            ))
        return out

    def _focus_detail(self, snapshot: ContextSnapshot) -> str:
        f = snapshot.focus
        try:
            if f.type == "chapter" and snapshot.chapter is not None:
                ch = self.store.get_chapter(snapshot.chapter) or {}
                syn = (ch.get("synopsis") or "").strip()
                beats = []
                for beat in ch.get("beats") or []:
                    text = (
                        beat.get("text") if isinstance(beat, dict) else str(beat)
                    )
                    text = (text or "").strip()
                    if text:
                        beats.append(text)
                parts = []
                if syn:
                    parts.append("- 本章大纲:" + syn[:220])
                if beats:
                    numbered = "；".join(
                        f"{index}.{text}" for index, text in enumerate(beats, 1)
                    )
                    parts.append("- 本章节拍:" + numbered[:220])
                return "\n".join(parts)
            if f.type == "character":
                for c in (self.store.characters() or []):
                    if c.id == f.id or c.name == f.label:
                        return f"焦点角色:{c.name}"
        except Exception:
            return ""
        return ""

    def _global_items(self, snapshot: ContextSnapshot) -> list[_Item]:
        """global:北极星 + 开放伏笔 + 主要角色(全书稳定层)。

        U-011(2026-07-15,作者要 fail-loud):删掉三段 try/except→静默空值——这是
        "主编是否记得全书稳定层"的字面实现,取数失败必须让作者看见,不能悄悄退化成
        "看着像没北极星/没伏笔/没主要角色"(与真没有无区别)。"""
        out: list[_Item] = []
        # U-011: 删静默降级,失败上抛(作者要 fail-loud)
        intent = self.store.get_intent() or {}
        star = (f"北极星:读者感受={intent.get('reader_feeling') or '—'};"
                f"情感弧={intent.get('emotional_arc') or '—'};"
                f"红线={intent.get('red_lines') or '—'}")
        out.append(_Item("- " + star, ContextSource(
            source_id="intent:main", source_kind="global", work=snapshot.work)))
        # D2 质量：红线升格为「必须遵守」段，避免淹没在一长串北极星里
        red = (intent.get("red_lines") or "").strip()
        if red:
            out.append(_Item(
                "- 【作者铁律·写作宪法｜本次输出必须遵守，禁止违反或装忘】\n"
                f"  {red.replace(chr(10), '；')}",
                ContextSource(
                    source_id="intent:author_constraints",
                    source_kind="global",
                    work=snapshot.work,
                    reason="author_constraint_must_follow",
                ),
            ))
        promises = self.store.open_promises() or []
        if promises:
            txt = ";".join(
                f"第{p.get('setup_chapter')}章埋:{(p.get('text') or '')[:24]}"
                for p in promises[:6])
            out.append(_Item("- 开放伏笔:" + txt, ContextSource(
                source_id="promises:open", source_kind="global", work=snapshot.work)))
        chars = self.store.characters() or []
        if chars:
            names = "、".join(c.name for c in chars[:14])
            out.append(_Item("- 主要角色:" + names, ContextSource(
                source_id="characters:main", source_kind="global", work=snapshot.work)))
        return out

    def _canonical_items(self, snapshot: ContextSnapshot, cands) -> list[_Item]:
        """canonical:权威表。有 retriever 候选走候选(带限知屏蔽);否则降级直查 store。
        无论哪条路径,focalizer 非空时 secret value 都物理屏蔽 + 留痕 masked=True。

        D3/D5：章级 must-link（大纲/伏笔/当章事实重叠）**置顶**，优先占预算。"""
        if cands:
            base = self._canonical_from_candidates(snapshot, cands)
        else:
            base = self._canonical_from_store(snapshot)
        return self._pin_must_link(snapshot, base)

    def _pin_must_link(self, snapshot: ContextSnapshot, base: list[_Item]) -> list[_Item]:
        """把戏剧必需锚钉在 canonical 头部，避免预算裁掉关键物件/伏笔。"""
        try:
            from scribe3.memory_must_link import (
                collect_must_anchors, format_must_link_items,
            )
            anchors = collect_must_anchors(self.store, snapshot.chapter, limit=10)
            if not anchors:
                return base
            must_pairs = format_must_link_items(anchors, work=snapshot.work or "")
            must_items: list[_Item] = []
            for text, meta in must_pairs:
                must_items.append(_Item(
                    text,
                    ContextSource(
                        source_id=str(meta.get("source_id") or "must_link"),
                        source_kind="canonical",
                        work=snapshot.work,
                        reason="must_link_priority",
                    ),
                ))
            # 去重：base 中与 must 高度重叠的行后置丢弃
            must_cores = []
            for it in must_items:
                t = (it.text or "").replace("〔必需〕", "").strip()
                if len(t) >= 8:
                    must_cores.append(t[4:44] if t.startswith("- ") else t[:40])
            rest: list[_Item] = []
            for it in base:
                skip = False
                for core in must_cores:
                    if core and core in (it.text or ""):
                        skip = True
                        break
                if not skip:
                    rest.append(it)
            return must_items + rest
        except Exception as e:
            _log.warning("must_link pin failed (fail-soft keep base): %s", e)
            return base

    def _canonical_from_candidates(self, snapshot: ContextSnapshot,
                                   cands) -> list[_Item]:
        out: list[_Item] = []
        masked_ok = self._frame_fact_ids(snapshot)  # 限知章:焦点者帧内可见 fact id 集
        # C1:权威 secret 集(裁决权在 store,不在 retriever 元数据)——凡候选 source_id
        # ∈ 此集一律屏蔽,不论 focalizer 是否为空、不论 retriever 是否标 secret。
        secret_ids = _secret_fact_ids(self.store)
        for c in cands:
            # Gap-B(2026-07-15):codex_secret_bridge 造的势力 secret 字段镜像结构性剔除
            # ——不进入下面的 secret_ids/prov_secret 掩码判定(那两条信号可能失效,见
            # test_gap_b_candidate_path_survives_secret_signal_degradation),直接跳过
            # 候选本身,canonical 完全不承载(见 _is_bridge_mirror 注释)。
            if any(_is_bridge_mirror(p.get("entity") or "", p.get("attribute") or "")
                   for p in (getattr(c, "provenance", None) or [])):
                continue
            prov_secret = any(p.get("secret") for p in (getattr(c, "provenance", None) or []))
            # ① store 权威判定为 secret → 恒屏蔽(全知/限知章一致,补齐候选路径漏洞)
            # ② retriever 自标 secret → 屏蔽(信号叠加,不覆盖 store 判定)
            mask = c.source_id in secret_ids or prov_secret
            # ③ 限知章额外:帧外候选(非本焦点者可见)→ 屏蔽(留痕)而非注入
            if not mask and snapshot.focalizer and masked_ok is not None \
                    and c.source_id not in masked_ok:
                mask = True
            src = ContextSource(
                source_id=c.source_id, source_kind="canonical", work=snapshot.work,
                masked=mask, reason="secret_masked" if mask else "",
                revision=getattr(c, "revision", None))
            text = (f"- {_SECRET_PLACEHOLDER}(source={c.source_id})" if mask
                    else f"- {c.text}")
            out.append(_Item(text, src))
        return out

    def _canonical_from_store(self, snapshot: ContextSnapshot) -> list[_Item]:
        """无 retriever 降级:直查 facts/promises/events(canonical 必须有真数据)。
        限知章走 project_frame 投影 + secret 屏蔽(复用 _editor_system 的既有做法)。

        U-011(2026-07-15,作者要 fail-loud):删掉承诺/事件两段裸 except:pass——
        canonical 是"必须有真数据"的核心块,查询失败必须抛,不能静默返回残缺的
        权威事实集(残缺却不报错,比整块空更危险:看着像完整正典,实际漏项)。"""
        out: list[_Item] = []
        ch = snapshot.chapter if snapshot.chapter is not None else 99999
        if snapshot.focalizer:
            out.extend(self._canonical_frame_facts(snapshot, ch))
        else:
            out.extend(self._canonical_all_facts(snapshot, ch))
        # 承诺 + 事件(两条路径都补;它们不携私密 value)
        # U-011: 删静默降级,失败上抛(作者要 fail-loud)
        for p in (self.store.open_promises() or [])[:8]:
            pid = p.get("id") or f"promise:{p.get('setup_chapter')}"
            out.append(_Item(
                f"- 承诺:第{p.get('setup_chapter')}章埋 {(p.get('text') or '')[:40]}",
                ContextSource(source_id=str(pid), source_kind="canonical",
                              work=snapshot.work)))
        evs = self.store.events_at(ch - 1) if ch and ch > 1 else []
        for e in (evs or [])[:6]:
            if not e:
                continue
            out.append(_Item(
                f"- 近事件:{str(e.type or e.motivated_by_goal or '')}",
                ContextSource(source_id=str(getattr(e, 'id', '') or 'event'),
                              source_kind="canonical", work=snapshot.work)))
        return out

    def _canonical_frame_facts(self, snapshot: ContextSnapshot,
                               ch: int) -> list[_Item]:
        """限知章:焦点者知识帧内事实;secret value 物理屏蔽,被屏蔽源 masked=True 留痕。"""
        out: list[_Item] = []
        from scribe3.knowledge import project_frame
        frame = project_frame(self.store, snapshot.focalizer, ch or 1)
        frame_facts = frame.facts
        for f in frame_facts[:40]:
            if _is_bridge_mirror(f.entity_id, f.attribute):
                continue   # Gap-B:桥镜像结构性剔除(即便 secret=True 已掩码 value,属性名本身仍不该出现)
            mask = bool(f.secret)   # secret=True:即便焦点者知,渲染层也屏蔽,防 leak marker 穿帮
            src = ContextSource(
                source_id=f.id, source_kind="canonical", work=snapshot.work,
                masked=mask, reason="secret_masked" if mask else "")
            if mask:
                out.append(_Item(f"- {f.entity_id} · {f.attribute}:{_SECRET_PLACEHOLDER}", src))
            else:
                out.append(_Item(f"- {f.entity_id} · {f.attribute}:{f.value}", src))
        return out

    def _canonical_all_facts(self, snapshot: ContextSnapshot,
                             ch: int) -> list[_Item]:
        """全知章:facts_at 全量(私密标注但作者视角可见,对齐 _editor_system 旧行为)。

        Gap-B(2026-07-15):此前这里对 codex_secret_bridge 造的势力 secret 字段镜像
        (如 secret_agenda/origin)毫无过滤——focalizer 空(全知写作,"正常模式")时
        直接把镜像命题当"全知视角可见的私密标注事实"裸值转储,与旧链 M6 全知转储泄露
        同型(app._is_faction_bridge_mirror 当年修的那个洞,这里此前一直没同步修)。
        修法:与 app._editor_system 的 `_keep_fact` 同型,Fact 层结构性剔除桥镜像——
        canonical 不是它们的授权注入通道(那是 app._codex_block 的职责)。真实故事秘密
        (非桥接)不受影响,仍保持"私密标注但作者全知视角可见"的既有语义。"""
        out: list[_Item] = []
        # U-011(2026-07-15,作者要 fail-loud): 删静默降级,失败上抛——canonical 必须
        # 有真数据,facts_at 查询失败不能悄悄假装"这本书没有事实"。
        facts = self.store.facts_at(ch) or []
        for f in facts[:40]:
            if _is_bridge_mirror(f.entity_id, f.attribute):
                continue
            note = "(私密/伏线)" if f.secret else ""
            out.append(_Item(
                f"- {f.entity_id} · {f.attribute}:{f.value}{note}",
                ContextSource(source_id=f.id, source_kind="canonical",
                              work=snapshot.work)))
        return out

    def _frame_fact_ids(self, snapshot: ContextSnapshot) -> set[str] | None:
        """限知章焦点者帧内 fact id 集(供候选路径判可见);全知章返回 None(不过滤)。

        U-011(2026-07-15,作者要 fail-loud):删掉了"project_frame 异常返 set()"——空集
        会把该章【所有】候选误判帧外→全量掩蔽,渲染成跟真秘密同款,系统故障伪装成"这里真有
        秘密"且无人知道。现在计算失败直接【抛】,让作者看见"限知帧计算失败",而非静默伪装。"""
        if not snapshot.focalizer:
            return None
        from scribe3.knowledge import project_frame
        ch = snapshot.chapter if snapshot.chapter is not None else 1
        frame = project_frame(self.store, snapshot.focalizer, ch)
        return {f.id for f in frame.facts}

    def _recent_items(self, snapshot: ContextSnapshot, cands) -> list[_Item]:
        """recent:当前章续写锚点 + 近期 episodic/decision；无候选再补上一章结尾。

        当前章尾段是续写硬上下文，必须排在经验候选之前，不能因开启 Memory
        Fabric 而消失。U-011(2026-07-15,作者要 fail-loud):"无候选→取上一章结尾"是正常业务降级
        分支(保留);但降级分支内部包 recent_proses 的裸 except:pass 已删——查询
        本身失败必须抛,不能悄悄假装"上一章没有结尾"。"""
        out: list[_Item] = []
        ch = snapshot.chapter
        if ch is not None:
            current = self.store.get_chapter(ch) or {}
            tail = (current.get("prose") or "")[-400:].strip()
            if tail:
                out.append(_Item(
                    "- 本章已写结尾(续写须自然接上,勿重复):" + tail,
                    ContextSource(
                        source_id=f"chapter:{ch}:tail",
                        source_kind="recent",
                        work=snapshot.work,
                    ),
                ))
        if cands:
            out.extend(_Item(f"- {c.text}", ContextSource(
                source_id=c.source_id, source_kind="recent", work=snapshot.work,
                revision=getattr(c, "revision", None))) for c in cands)
            return out
        if ch and ch > 1:
            # U-011: 删静默降级,失败上抛(作者要 fail-loud)
            prev = self.store.recent_proses(ch, k=1) or []
            if prev:
                tail = (prev[0].get("prose") or "")[-240:].strip()
                if tail:
                    out.append(_Item("- 上一章结尾:" + tail, ContextSource(
                        source_id=f"prose:{prev[0].get('seq')}",
                        source_kind="recent", work=snapshot.work)))
        return out

    def _procedural_items(self, snapshot: ContextSnapshot, cands) -> list[_Item]:
        """procedural:已采纳的写作方法/教训。有候选走候选;否则降级取题材工艺规则。

        U-011(2026-07-15,作者要 fail-loud):降级分支内部包 list_craft_rules 的
        裸 except:pass 已删——查询失败必须抛,不能悄悄假装"没有工艺规则"。"""
        if cands:
            return [_Item(_author_preference_constraint(c.text), ContextSource(
                source_id=c.source_id, source_kind="procedural", work=snapshot.work))
                for c in cands]
        out: list[_Item] = []
        # U-011: 删静默降级,失败上抛(作者要 fail-loud)
        rules = self.store.list_craft_rules() or []
        for r in rules[:8]:
            txt = (r.get("rule") or r.get("text") or r.get("name") or "").strip()
            if txt:
                out.append(_Item("- 工艺:" + txt[:80], ContextSource(
                    source_id=str(r.get("id") or "craft"),
                    source_kind="procedural", work=snapshot.work)))
        return out

    def _reference_items(self, snapshot: ContextSnapshot, cands) -> list[_Item]:
        """reference:素材召回,始终带"借鉴非事实"免责。首行恒为免责声明(留痕独立源)。

        U-011(2026-07-15,作者要 fail-loud):降级分支内部包 list_materials 的裸
        except:pass 已删——查询失败必须抛,不能悄悄假装"没有素材"。"""
        out: list[_Item] = [_Item(
            _REFERENCE_DISCLAIMER,
            ContextSource(source_id="reference:disclaimer", source_kind="reference",
                          work=snapshot.work, reason="borrow_not_fact"))]
        if cands:
            for c in cands:
                out.append(_Item(f"- {c.text}", ContextSource(
                    source_id=c.source_id, source_kind="reference",
                    work=snapshot.work, reason="borrow_not_fact")))
            return out
        # 降级:直查素材库(仅列标题,不当事实)
        # U-011: 删静默降级,失败上抛(作者要 fail-loud)
        mats = self.store.list_materials() or []
        for m in mats[:6]:
            title = (m.get("title") or m.get("name") or "").strip()
            if title:
                out.append(_Item("- 素材:" + title[:60], ContextSource(
                    source_id=str(m.get("id") or "material"),
                    source_kind="reference", work=snapshot.work,
                    reason="borrow_not_fact")))
        # 只有免责声明、没有任何素材 → 视作空块(免责本身无信息量,不占块)
        return out if len(out) > 1 else []

    def _uncertainty_items(self, snapshot: ContextSnapshot, cands,
                           superseded) -> list[_Item]:
        """uncertainty:冲突 + 低信心 + 待确认。含被正典取代项的一句提示(读者仍不知)。"""
        out: list[_Item] = []
        for c in (cands or []):
            conf = getattr(c, "confidence", None)
            tag = f"(信心 {conf})" if conf is not None else ""
            out.append(_Item(f"- 待确认:{c.text}{tag}", ContextSource(
                source_id=c.source_id, source_kind="uncertainty", work=snapshot.work)))
        for c in (superseded or []):
            out.append(_Item(
                f"- 旧推测已被正典取代(存疑,勿据此写):{getattr(c, 'source_id', '')}",
                ContextSource(source_id=f"superseded:{c.source_id}",
                              source_kind="uncertainty", work=snapshot.work,
                              reason="superseded_by_canonical")))
        return out

    def _provenance_items(self, items: dict[str, list[_Item]]) -> list[_Item]:
        """provenance:前七块来源的清单(id·kind·revision·是否屏蔽)。
        只记来源身份,不复制正文(正文可能含秘密)。作为"这一份 envelope 由什么拼成"的可读清单。"""
        out: list[_Item] = []
        for name in ("focus", "global", "canonical", "recent",
                     "procedural", "reference", "uncertainty"):
            for it in items.get(name, []):
                s = it.source
                flag = " ·屏蔽" if s.masked else ""
                rev = f" rev={s.revision}" if s.revision else ""
                line = f"- [{name}] {s.source_id}({s.source_kind}){rev}{flag}"
                out.append(_Item(line, ContextSource(
                    source_id=f"prov:{s.source_id}", source_kind="provenance",
                    work=s.work, masked=s.masked, reason=s.reason,
                    revision=s.revision)))
        return out


# ---------- envelope hash 与 trace manifest ----------

def compute_envelope_hash(blocks: list[ContextBlock],
                          snapshot: ContextSnapshot) -> str:
    """envelope 身份指纹的规范化规则(计划 Step 5 由本任务定义):

    参与:每块的 (name, token_estimate, sorted(source_ids)) 三元组 +
          snapshot.context_hash,取 canonical JSON(sort_keys + 紧凑分隔 + 不转义中文)
          的 SHA-256。
    不参与:block 正文——① 正文含秘密(secret value 绝不进 hash 输入,防旁路泄露),
          ② hash 只用于识别"同一组装配方"的身份(同快照 + 同来源集 + 同预算切法 →
          同 envelope),正文字面变化不改变配方身份。
    """
    manifest = [
        [b.name, b.token_estimate, sorted(s.source_id for s in b.sources)]
        for b in blocks
    ]
    payload = {"snapshot": snapshot.context_hash, "blocks": manifest}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def envelope_trace_manifest(envelope: ContextEnvelope) -> dict:
    """给 chat_message.trace.context 用的最小 manifest(计划 Step 5)。

    只记:snapshot_revision / snapshot_hash / envelope_hash / 每块 token 与 source id /
    omitted 原因。绝不记正文——尤其 secret fact 的 value 物理不进 trace(与 hash 同因)。
    正文长时只留 source id + digest,靠 source id 回原表复原,不在 trace 重复存整段秘密。
    """
    return {
        "snapshot_revision": envelope.snapshot.revision,
        "snapshot_hash": envelope.snapshot.context_hash,
        "envelope_hash": envelope.envelope_hash,
        "total_token_estimate": envelope.total_token_estimate,
        "blocks": [
            {
                "name": b.name,
                "token_estimate": b.token_estimate,
                "source_ids": [s.source_id for s in b.sources],
                "masked_source_ids": [s.source_id for s in b.sources if s.masked],
            }
            for b in envelope.blocks
        ],
        "omitted": [
            {"source_id": o.get("source_id"), "reason": o.get("reason"),
             "block": o.get("block")}
            for o in envelope.omitted
        ],
    }


def render_envelope_text(envelope: ContextEnvelope) -> str:
    """把 envelope 渲染成可注入 prompt 的正文(仅非空块,按固定顺序拼接)。
    供 Creative Context Engine 的唯一生产写作路径渲染统一上下文段。"""
    parts = [b.text for b in envelope.blocks if b.text]
    return "\n\n".join(parts)

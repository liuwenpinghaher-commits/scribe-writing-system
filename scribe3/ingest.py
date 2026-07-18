"""章节回写(ingest):读定稿 → 抽"谁新知道什么/做了什么" → 更新知识账本(单一真相源)。

闭合写循环:主编对话写作 → 存 → ingest → 世界知识态更新 → 下章限知帧反映新知。
看见即知道:learned 给当事人发知识边;did 给当事人 + 在场 seen_by 都发边。
apply_delta 纯应用(可测,不连网);ingest_chapter 走 Hermes 抽取。
"""
from __future__ import annotations

from scribe3.critique import build_knowledge_extract_prompt, parse_knowledge_delta
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge


# ===== 方案B任务12:关系触碰抽取(角色/支线/伏笔已有 last_active/last_refresh_at 触碰追踪,
# 唯独"关系"维度真新增)。critique.py 有并行任务在改,build_knowledge_extract_prompt/
# parse_knowledge_delta 的签名与实现禁碰——本段 prompt 追加段/独立解析均只在 ingest.py 本地实现,
# 由 ingest_chapter 把追加段拼到 critique.py 产出的基础 prompt 之后、把独立解析结果并入 delta。 =====

RELATION_TOUCH_KINDS = ("冲突", "靠近", "决裂", "亏欠", "协作")


def _relation_touch_prompt_addendum() -> str:
    """「关系触碰」抽取指令段(拼接在 build_knowledge_extract_prompt 基础 prompt 之后)。
    有效触碰纪律与 promise_touch 同严:须实质推进/施压/改变关系状态/产生后果才算,
    仅提名字、寒暄带过、无实质互动的空头出场不算触碰。"""
    kinds = "/".join(RELATION_TOUCH_KINDS)
    return (
        "另外再抽【relation_touches:本章哪些角色对之间发生了对关系状态本身产生实质影响的互动】——"
        "有效触碰纪律:须实质推进/施压/改变关系状态/产生后果才算,"
        "仅提名字、寒暄带过、无实质互动的空头出场不算触碰。"
        f"每条给两个角色名(a,b)+关系变化类型(kind,只能是{kinds}之一,不得发明其他值);"
        "没有满足纪律的触碰则输出空列表。"
        "在同一行 JSON 里补充键:"
        '"relation_touches":[{"a":角色名,"b":角色名,"kind":"' + '|'.join(RELATION_TOUCH_KINDS) + '"}]。'
    )


def parse_relation_touches(reply: str) -> list[dict]:
    """从 LLM 原始回复中独立解析 relation_touches 字段(与 parse_knowledge_delta 并行、
    不改后者——critique.py 有并行任务在改,禁碰)。
    缺省容错:字段不存在 / 坏 JSON / 单条缺字段或 kind 越界 → 该条丢弃,不抛异常。"""
    import json
    import logging
    import re
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            return []
        d = json.loads(m.group(0))
        out = []
        for it in (d.get("relation_touches") or []):
            a, b, kind = it.get("a"), it.get("b"), it.get("kind")
            if a and b and kind in RELATION_TOUCH_KINDS:
                out.append({"a": a, "b": b, "kind": kind})
        return out
    except Exception as e:
        logging.getLogger("scribe3.ingest").warning(
            "parse_relation_touches 失败(fail-soft,不落关系触碰): %s | reply[:120]=%r",
            e, (reply or "")[:120])
        return []


def _resolve_char(store, name: str, seq: int, role: str) -> str | None:
    """解析角色:已存在返回 oid;不存在则登记待确认,返回 None(不建实体、不发边)。
    替换原 _ensure_char(不验即建,致幻觉角色污染 characters())。"""
    oid = f"role:{name}"
    if store.entity(oid) is not None:
        return oid
    store.add_unverified_ref(name, seq, role)
    return None


def _resolve_motif(store, name: str) -> str | None:
    """按名精确匹配已立母题,返回 motif_id;匹配不到返回 None(不建母题,与 _resolve_char 同范式)。"""
    needle = (name or "").strip()
    if not needle:
        return None
    for m in store.list_motifs():
        if (m.get("name") or "").strip() == needle:
            return m.get("id")
    return None


def _resolve_promise(open_rows: list[dict], text: str) -> str | None:
    """在给定 open 伏笔候选里按原文匹配,返回 promise id;匹配不到返回 None。
    Task5-B①:抽取 prompt 里伏笔文案截断到 40 字,>40 字伏笔 LLM 只能回截断键——
    故支持截断键匹配:needle == text.strip() 或(needle == text.strip()[:40] 且该前缀
    在候选集内唯一命中;多条同前 40 字则歧义跳过,零误匹配)。
    Task5-B③:候选由调用方传入(复用 ingest_chapter 已取的 open_promises),免每条触及重查整表。"""
    needle = (text or "").strip()
    if not needle:
        return None
    prefix_hits: list[str] = []
    for p in open_rows:
        t = (p.get("text") or "").strip()
        if t == needle:
            return p.get("id")
        if len(t) > 40 and t[:40] == needle:
            prefix_hits.append(p.get("id"))
    if len(prefix_hits) == 1:
        return prefix_hits[0]
    if len(prefix_hits) > 1:
        # Task7-C②:截断键歧义跳过要有痕迹(与 promise_touch 写失败日志对称)
        import logging
        logging.getLogger("scribe3.ingest").warning(
            "promise_touch 截断键歧义跳过(%d 条伏笔同前40字),needle=%r",
            len(prefix_hits), needle)
    return None


def _find_existing_learned_prop(store, fact_text: str) -> str | None:
    """在已有命题中查找与 fact_text 归一化后【完全相等】的"获知"类命题,返回其 oid 或 None。
    去重策略(批0 彻查 D-2):只保完全相等,不做包含匹配。
    包含匹配会把『X』与『X,但那只是假消息』误合并成一条——获知否定/限定版的角色被挂到
    未否定命题,限知帧显示与正文相反。语义相反的命题必须各自独立,正确性优先于激进去重。
    仅复用【仍生效】的命题(valid_to IS NONE):已被 supersede 的旧命题不复用。
    fail-safe:任何异常返回 None(调用方继续创建新命题)。"""
    import logging
    _log = logging.getLogger("scribe3.ingest")
    try:
        # 归一化:去首尾空白
        needle = fact_text.strip()
        if not needle:
            return None
        # 全量扫描【仍生效】的"获知"命题(数量通常较少;已 supersede 的旧命题不复用)
        rows = store._query(
            "SELECT meta::id(id) AS local, value FROM proposition "
            "WHERE attribute = '获知' AND valid_to IS NONE")
        for r in rows:
            existing = (r.get("value") or "").strip()
            if not existing:
                continue
            # 只认完全相等:去掉包含匹配分支,防相反语义误合并
            if existing == needle:
                return f"fact:{r['local']}"
    except Exception as e:
        _log.warning("learned 去重查找失败(fail-safe,将新建命题): %s", e)
    return None


def _upsert_reader_knows(store, fid: str, seq: int) -> None:
    """幂等写 reader_knows 边(批0 彻查 D-1):发边前先查该命题是否已有 reader 边,不存在才补。
    语义:叙述揭示即读者已知,与命题是否复用无关——故新建/复用命题一律补边。
    幂等:已有边则跳过(防重复边);purge_ingest 删本章 reader 边后重 ingest 会自愈补回。
    non-fatal:任何异常只告警不阻断主写。"""
    import logging
    _log = logging.getLogger("scribe3.ingest")
    try:
        existing = store._query(
            "SELECT proposition FROM reader_knows WHERE proposition = $p", {"p": fid})
        if existing:
            return   # 已有 reader 边,幂等跳过
        store.add_knowledge(KnowledgeEdge("reader", fid, since_chapter=seq,
                                          acquired_via="narrated"),
                            ingest_seq=seq)
    except Exception as _e:
        _log.warning("reader_knows 写入失败(non-fatal),命题 %s: %s", fid, _e)


def grep_back_verify(delta: dict, source_prose: str) -> dict:
    """写后 grep 回原文核对(oh-story material-decomposition.md:388-396 三纪律落地):
    合成阶段 LLM 可能"看似坐实"地编造原文没有的实体值——在 apply_delta 之前对
    【实体事实类】字段做确定性回捞核对:值能在正文里找到踪迹才算可溯源,核不到就
    标注"(原文未明确)"(报告式,宁标注不静默丢——annotate 不 drop)。

    只校验 learned.fact(角色新知道的事)与 did.action(角色所为)——这两个字段是
    知识账本(见模块头 docstring"看见即知道")的硬事实主体,理应可在正文里溯源。
    以下字段是 LLM 对正文的【推断/解读判断】,不是应逐字可查的具体断言,豁免不查:
      · arc(弧光快照,store 落库时 confidence 显式标 "inferred")
      · belief(信念信奉度量表,同样 confidence="inferred" 的心理判断)
      · voice_shift(声音触发归因,"是否值得变声"的主观判断)
      · events.goal / events.type(动机目标与事件分类标签,判断性而非逐字断言;
        events.participants 另经 _resolve_char 按已存在角色解析,已有校验)
      · motif / promise_touch(母题/伏笔命中判断,限定在"已立母题/已埋伏笔"候选集
        内选,非自由生成的新断言,误判风险由候选集本身兜底)

    判定:value 去空白标点后可见字数 <4 时不校验(4-gram 在过短文本上无意义,直接
    放行);否则取其所有连续 4-gram,任一 4-gram 在正文(同样去空白标点)中出现
    即算可溯源(部分重叠即可,容忍复述改写)。

    纯函数、确定性、不连网、不改动入参(对 delta 深拷贝后处理再返回)。
    返回 {"delta": 处理后的 delta, "dropped": [...], "annotated": [...]}。
    """
    import re
    import copy
    result_delta = copy.deepcopy(delta or {})
    dropped: list[str] = []
    annotated: list[str] = []
    clean_prose = re.sub(r"[^\w]", "", source_prose or "")

    def _traceable(clean_value: str) -> bool:
        grams = {clean_value[i:i + 4] for i in range(len(clean_value) - 3)}
        return any(g in clean_prose for g in grams)

    def _verify_field(items, field: str, label: str) -> None:
        for it in items:
            if not isinstance(it, dict):
                continue
            value = it.get(field)
            if not isinstance(value, str) or not value:
                continue
            clean_value = re.sub(r"[^\w]", "", value)
            if len(clean_value) < 4:
                continue   # 短值不校验(4-gram 无意义)
            if _traceable(clean_value):
                continue   # 可溯源
            it[field] = f"{value}(原文未明确)"
            annotated.append(f"{label}.{field}:{it.get('who') or '?'}={value!r}")

    _verify_field(result_delta.get("learned") or [], "fact", "learned")
    _verify_field(result_delta.get("did") or [], "action", "did")

    return {"delta": result_delta, "dropped": dropped, "annotated": annotated}


def apply_delta(store, delta: dict, seq: int,
                open_promises: list[dict] | None = None) -> int:
    """把知识 delta 落到 store:新知→当事人知道;所为→当事人+在场者知道。返回应用条数。
    章级幂等:先清本章既有 ingest 产出,再重写——重复 ingest 不会残留悬挂边。
    P2-E1: 每条命题同时写 reader_knows(叙述揭示即读者已知,戏剧反讽闭环)。
    S3: learned 类命题去重——近精确匹配到已有客观命题时复用,只新发 knows 边。"""
    import logging
    _log = logging.getLogger("scribe3.ingest")
    store.purge_ingest(seq)
    n = 0
    for i, it in enumerate(delta.get("learned") or []):
        who, fact = it.get("who"), it.get("fact")
        if not who or not fact:
            continue
        oid = _resolve_char(store, who, seq, "learned_who")
        if oid is None:
            continue
        # S3: 尝试复用已有近精确命题(消重复真相)
        existing_fid = _find_existing_learned_prop(store, fact)
        if existing_fid is not None:
            # 复用:不创建新命题(复用现有客观命题)
            fid = existing_fid
            _log.debug("learned 去重:复用命题 %s (文本完全相等 %r)", fid, fact[:30])
        else:
            # 新建客观命题
            fid = f"fact:k{seq}-{i}"
            store.add_fact(Fact(fid, oid, "获知", fact, valid_from=seq), ingest_seq=seq)
        # reader_knows:叙述揭示即读者已知——对新建与复用命题一律幂等 upsert
        # (D-1:复用分支旧代码不补 reader 边,重 ingest 源章 purge 后 reader 永久丢失)
        _upsert_reader_knows(store, fid, seq)
        store.add_knowledge(KnowledgeEdge(oid, fid, since_chapter=seq, acquired_via="learned"),
                           ingest_seq=seq)
        n += 1
    for j, it in enumerate(delta.get("did") or []):
        who, action = it.get("who"), it.get("action")
        if not who or not action:
            continue
        actor = _resolve_char(store, who, seq, "did_who")
        if actor is None:
            continue
        fid = f"fact:d{seq}-{j}"
        store.add_fact(Fact(fid, actor, "行动", action, valid_from=seq), ingest_seq=seq)
        for w in [who] + list(it.get("seen_by") or []):
            woid = _resolve_char(store, w, seq, "seen_by")
            if woid is None:
                continue
            store.add_knowledge(KnowledgeEdge(woid, fid,
                                              since_chapter=seq, acquired_via="saw"),
                                ingest_seq=seq)
        # 叙述揭示即读者已知:did 类事件读者也知道
        try:
            store.add_knowledge(KnowledgeEdge("reader", fid, since_chapter=seq,
                                              acquired_via="narrated"),
                                ingest_seq=seq)
        except Exception as _e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "reader_knows 写入失败(non-fatal),命题 %s: %s", fid, _e)
        n += 1
    for it in delta.get("voice_shift") or []:
        who, reason = it.get("who"), it.get("reason")
        if who and reason and hasattr(store, "add_voice_flag"):
            # 只标记(角色名),不生成独白;ingest_seq 供 purge 幂等(审计 C-2)
            store.add_voice_flag(who, seq, reason, ingest_seq=seq)
    # G4: 自动从正文抽取角色弧光(char_state)——边写边长出弧光,反哺下一章约束
    for it in delta.get("arc") or []:
        who = it.get("who")
        change_type = it.get("change_type")
        summary = it.get("summary")
        snapshot = it.get("snapshot")
        if not (who and change_type and summary):
            continue
        if change_type not in ("ability", "relation", "personality", "composite"):
            continue
        oid = _resolve_char(store, who, seq, "arc_who")
        if oid is None:
            continue
        # snapshot → after_state 按 change_type 归入对应键
        after_state: dict = {}
        if snapshot:
            if change_type == "ability":
                after_state = {"ability_snapshot": snapshot}
            elif change_type == "relation":
                after_state = {"relation_snapshot": snapshot}
            elif change_type == "personality":
                after_state = {"personality_snapshot": snapshot if isinstance(snapshot, str)
                               else str(snapshot)}
            else:  # composite
                after_state = snapshot if isinstance(snapshot, dict) else {}
        try:
            store.add_char_state(
                character_id=oid,
                chapter=seq,
                change_type=change_type,
                summary=summary,
                after_state=after_state or None,
                confidence="inferred",
                ingest_seq=seq,
            )
        except Exception as _arc_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "char_state 写入失败(non-fatal),角色 %s 章 %s: %s", who, seq, _arc_e)
    # 伏笔母题章感知:抽本章触及的已立母题 → 落 motif_instance(只在已立母题里选)
    for it in delta.get("motif") or []:
        name = it.get("motif") or it.get("name")
        if not name:
            continue
        mid = _resolve_motif(store, name)
        if mid is None:
            continue   # 解析不到的母题名跳过(fail-safe,不建母题)
        try:
            store.add_motif_instance(mid, chapter=seq,
                                     evidence=it.get("evidence") or "", ingest_seq=seq)
        except Exception as _mi_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "motif_instance 写入失败(non-fatal),母题 %s 章 %s: %s", name, seq, _mi_e)
    # 伏笔章触及:抽本章推进的已埋 open 伏笔 → promise_touch(只在已埋伏笔里选)
    # ingest_seq=seq 必须显式传:缺省=手动登记不可 purge,re-ingest 会双计 refresh_count
    touches = delta.get("promise_touch") or []
    if touches and open_promises is None:
        open_promises = store.open_promises()   # 调用方未传时兜底,只查一次
    for it in touches:
        pid = _resolve_promise(open_promises or [], it.get("text") or "")
        if pid is None:
            continue   # 解析不到的伏笔原文跳过(fail-safe,不建伏笔)
        try:
            store.add_promise_touch(pid, chapter=seq,
                                    evidence=it.get("evidence") or "", ingest_seq=seq)
        except Exception as _pt_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "promise_touch 写入失败(non-fatal),伏笔 %s 章 %s: %s", it.get("text"), seq, _pt_e)
    # 方案B任务12:关系触碰——本章角色对之间的有效触碰(有效性判定已在 prompt 抽取纪律里做,
    # 这里只做资格解析:两端角色须已存在(_resolve_char 同范式,幻觉角色不建);kind 越界丢弃。
    for it in delta.get("relation_touches") or []:
        a_name, b_name, kind = it.get("a"), it.get("b"), it.get("kind")
        if not a_name or not b_name or kind not in RELATION_TOUCH_KINDS:
            continue
        a_oid = _resolve_char(store, a_name, seq, "relation_touch_a")
        b_oid = _resolve_char(store, b_name, seq, "relation_touch_b")
        if a_oid is None or b_oid is None:
            continue   # 一方未知角色跳过(fail-safe,不建幻觉角色)
        try:
            store.add_relation_touch(a_oid, b_oid, chapter=seq, kind=kind)
        except Exception as _rt_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "relation_touch 写入失败(non-fatal),%s-%s 章 %s: %s",
                a_name, b_name, seq, _rt_e)
    # Task5: lie_belief 位移——有 lie 锚角色本章的信念信奉度 → char_state(change_type='belief')
    # 值入库前 clamp [0,100](store 不钳,调用方负责);解析不到的角色跳过(同 _resolve_char 范式)
    for it in delta.get("belief") or []:
        who, value = it.get("who"), it.get("value")
        if not who or not isinstance(value, (int, float)):
            continue
        oid = _resolve_char(store, who, seq, "belief_who")
        if oid is None:
            continue
        try:
            store.add_char_state(character_id=oid, chapter=seq, change_type="belief",
                                 summary=it.get("why") or "信念位移",
                                 lie_belief=int(max(0, min(100, value))),
                                 confidence="inferred", ingest_seq=seq)
        except Exception as _b_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "belief 写入失败(non-fatal),角色 %s 章 %s: %s", who, seq, _b_e)
    # 批D P1-5:从本章正文抽关键事件 → event 表(事件图随 ingest 自然长出,
    # 因果 QC/时间线事件泳道有真数据)。与 arc/motif 同范式:
    #   · 参与者只解析既有角色；事件抽取的槽位常会误填器物/地点，未知值直接跳过，
    #     绝不登记为待确认人物（真正的新角色由 learned/did 等人物语义字段登记）；
    #   · caused_by 指向本章更早事件序号 → causal_in 图边(causal_complete 据此判连贯);
    #   · 事件 id 用 ev:i{seq}-{k} 确定式命名 + ingest_seq=seq → purge_ingest 幂等清理;
    #   · 逐条 non-fatal 兜底,单条写库失败不阻断其余事件与整个 ingest。
    ev_specs = delta.get("events") or []
    ev_ids = [f"ev:i{seq}-{k}" for k in range(len(ev_specs))]
    # P1-5 M1:记已成功落库的事件序号——caused_by 建 causal 边前须校验被引序号确已落库,
    # 否则引用"因空 type 被跳过的幽灵事件"会 RELATE 出指向未落库事件的悬挂 causal 边。
    persisted_idx: set[int] = set()
    for k, it in enumerate(ev_specs):
        etype = (it.get("type") or "").strip()
        if not etype:
            continue   # 无类型标签的事件跳过(fail-safe)——不落库=幽灵,后续引用它不建边
        # 参与者 name→role 解析:只认合法槽位和已确认角色。这里不能调用
        # _resolve_char——LLM 很容易把“半截鱼骨”“闸底刻字”等非人物填到 OBJ，
        # 若登记 pending 会把物体送进“待确认人物”队列，污染角色库。
        participants: dict = {}
        raw_parts = it.get("participants")
        if isinstance(raw_parts, dict):
            for slot, who in raw_parts.items():
                if slot not in ("SUBJ", "OBJ", "WITNESS") or not who:
                    continue
                poid = f"role:{who}"
                if store.entity(poid) is not None:
                    participants[slot] = poid
        # caused_by → causal_in:只取指向本章更早事件的合法回指(防前指/自环/越界)
        causal_in: list = []
        for c in (it.get("caused_by") or []):
            if isinstance(c, bool):        # bool 是 int 子类,先排除
                continue
            # P1-5 M1:合法回指须满足 0<=c<k 且 c 确已落库(在 persisted_idx 内)——
            # 引用被跳过(空 type)的幽灵序号不建边,防指向未落库事件的悬挂 causal 边。
            if isinstance(c, int) and 0 <= c < k and c in persisted_idx:
                causal_in.append((ev_ids[c], "enables"))
        try:
            store.add_event(
                Event(ev_ids[k], etype, participants=participants, story_time=seq,
                      motivated_by_goal=(it.get("goal") or "").strip() or None,
                      causal_in=causal_in),
                ingest_seq=seq)
            persisted_idx.add(k)   # 落库成功才登记,供后续事件 caused_by 校验(防悬挂边)
        except Exception as _ev_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "event 写入失败(non-fatal),事件 %s 章 %s: %s", ev_ids[k], seq, _ev_e)
    return n


def ingest_chapter(store, seq: int, complete_fn, max_attempts: int = 3) -> dict:
    """读某章正文 → Hermes 抽知识 delta → 应用到 store。
    抽取是非确定的:长 JSON 偶发截断/坏格式 → parse 返回 None。单次尝试会零星 parse_failed,
    故重试至多 max_attempts 次(每次重新抽取);全失败才返回 parse_failed=True(不 purge,保留既有知识)。"""
    ch = store.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"applied": 0, "delta": {"learned": [], "did": [], "voice_shift": []}, "annotated": []}
    motif_names = [m.get("name") for m in store.list_motifs() if m.get("name")]
    promise_items = [{"id": p["id"], "text": p["text"]} for p in store.open_promises()]
    # Task5: 收集有 lie 锚的角色 → prompt belief 段(只评这些角色的信念信奉度)
    belief_chars = []
    for c in store.characters():
        a = store.char_anchors(c.id)
        if a.get("lie"):
            belief_chars.append({"name": c.name, "lie": a["lie"]})
    prompt = build_knowledge_extract_prompt(ch["prose"], motif_names=motif_names,
                                            promise_items=promise_items,
                                            belief_chars=belief_chars)
    # 方案B任务12:关系触碰段拼在基础 prompt 之后(不改 critique.py 的
    # build_knowledge_extract_prompt——该文件有并行任务在改,禁碰)。
    prompt = prompt + "\n\n" + _relation_touch_prompt_addendum()
    delta = None
    for _ in range(max(1, max_attempts)):
        reply = complete_fn(prompt)
        delta = parse_knowledge_delta(reply)
        if delta is not None:
            # relation_touches 独立解析(parse_knowledge_delta 不认得这个新键,
            # 同一份原始回复上并行取键,不改 critique.py)。
            delta["relation_touches"] = parse_relation_touches(reply)
            break
    if delta is None:
        return {"applied": -1, "parse_failed": True, "delta": None, "annotated": []}
    # B22: apply_delta 前 grep 回原文核对实体事实(learned.fact/did.action),
    # 核不到就标注"原文未明确"——防 LLM 编造原文没有的实体值悄悄坐实进知识账本。
    verify = grep_back_verify(delta, ch["prose"])
    delta = verify["delta"]
    if verify["annotated"]:
        import logging
        logging.getLogger("scribe3.ingest").warning(
            "grep_back_verify 章 %s 有 %d 处断言原文未明确核实到: %s",
            seq, len(verify["annotated"]), verify["annotated"])
    return {"applied": apply_delta(store, delta, seq, open_promises=promise_items),
            "delta": delta, "annotated": verify["annotated"]}


# ===== 方案B任务24:story-import 逆向导入——弧光五锚逆向 prompt + 解析 =====
# 背景:story-import 场景下角色没有作者预先手填的五锚(ghost/lie/truth/want/need)——
# 只有已发布章节反推出的 char_state 弧光记录(如 store.reverse_current_state 合成的快照,
# 或 list_char_states 拼出的人类可读摘要)。本节只交付"读弧光记录倒推五锚"的 prompt 构造
# 与结果解析两个纯函数,不连网、不在此处接 LLM 调用——import 端点若对每个主要角色都同步串行
# 调一次 LLM 会显著拖慢响应,故五锚逆向留作 import 完成后的【可选异步步骤】(TODO:后续任务
# 按角色排队后台调用 complete_fn(build_reverse_anchor_prompt(...)) 再用
# parse_reverse_anchors 解析写入 store.set_char_anchors)。

def build_reverse_anchor_prompt(char_name: str, states_text: str) -> str:
    """构造"由已发布章节的弧光记录倒推角色五锚"的 prompt。
    states_text:该角色弧光记录的人类可读摘要(如 reverse_current_state 快照的文本化,
    或 list_char_states 逐条 summary 拼接),为空时给兜底占位文案,不崩。"""
    body = (states_text or "").strip() or "(暂无弧光记录)"
    return (
        "你是故事弧光分析师。下面是角色「" + char_name + "」在已发布章节里的状态演变记录:\n"
        + body + "\n\n"
        "请倒推该角色这条弧光成立所必须假设的五个锚点(弧光五锚体系):\n"
        "ghost(过去的伤——此前发生、至今仍影响他的创伤/遗憾)、"
        "lie(错误信念——他因 ghost 而相信的、限制自己的错误认知)、"
        "truth(真相——他最终需要认清、能破除 lie 的真相)、"
        "want(表层欲望——他自己认为想要的东西)、"
        "need(深层需要——他真正需要但自己未必已经意识到的东西)。\n"
        "只依据给定记录合理推断,记录信息不足以支撑某项时给最保守的简短推断,"
        "不要编造与记录矛盾的细节。\n"
        '只输出一行 JSON:{"ghost":一句话,"lie":一句话,"truth":一句话,'
        '"want":一句话,"need":一句话}。'
    )


def parse_reverse_anchors(reply: str) -> dict | None:
    """解析五锚逆向 LLM 回复。
    成功:返回 {"ghost":str,"lie":str,"truth":str,"want":str,"need":str}
    (五键齐全;回复缺某键则该键补空字符串,与 char_anchors 白名单键对齐,方便调用方
    直接传给 store.set_char_anchors)。
    失败(坏 JSON / 无 JSON 块):返回 None(fail-soft,调用方不应把 None 写入 char_anchors)。"""
    import json
    import logging
    import re
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            logging.getLogger("scribe3.ingest").warning(
                "parse_reverse_anchors 无 JSON 块,五锚不回写: reply[:120]=%r", (reply or "")[:120])
            return None
        d = json.loads(m.group(0))
        return {k: str(d.get(k) or "") for k in ("ghost", "lie", "truth", "want", "need")}
    except Exception as e:
        logging.getLogger("scribe3.ingest").warning(
            "parse_reverse_anchors 失败,五锚不回写: %s | reply[:120]=%r", e, (reply or "")[:120])
        return None

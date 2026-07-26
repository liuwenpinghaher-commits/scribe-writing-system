"""北极星方案任务11 · 选择环(蓝图 §4-①):关键章 N 候选 → 确定性过滤 → 批次粗排 → 人终选。

哲学:拿 rubric 分当目标迭代打磨被证伪(评分升质量停);但在 N 个已完成候选里
**选择**,噪声可被批次聚合压制——rubric 不配当法官,够格当初筛员。多样性靠
构造保证(prompt 显式分派策略轴,PlanSearch:idea 层多样性直接预测收益),
不靠事后补救。终选与理由永远在人(理由入 lesson 流=品味复利最贵输入)。

纯编排模块(依赖注入):generate/post_check/persist_candidate/profile_fn/
judge_fn/journal 由 app 端点绑真实现;本模块零 app/store import。

调研裁决(台账 D-019):
- N=3 + 伪多样时用第 4 个未用策略重生成一次(预算花在多样性刀刃);
- rubric 排序=全循环双向 6 比较+位置对换,循环偏好/位置偏置 → consensus=False
  不给排序直接交人(强化"绝不门禁");
- 伪多样只看合同未约束的自由维度(句长CV/对话占比/标点节奏)——伏笔/delta 必达
  导致的结构同质是合同的必然产物,纳入判定会陷"重生成永不过线"死循环;
- 确定性过滤裁剪至**写前可判**子集(triage blocking:泄密/退化/ai heavy/S1)——
  蓝图列的"伏笔触达/delta 达成"需 ingest 后查库,候选未 ingest 不可判,
  留给终选人看+选后验收(诚实偏离,记台账)。
"""
from __future__ import annotations

import logging
import math

from scribe3.loop import triage

_log = logging.getLogger("scribe3.selection")

# 策略库:切入点/节奏形状/信息释放顺序 显式分派(前 3 个默认出战,第 4 个留给
# 伪多样重生成——换未用过的策略轴,绝不同参重掷)。
STRATEGIES = [
    {"key": "cold_open",
     "directive": "本候选策略【冷开场·物象切入】:从一件与主冲突相关的实物/环境细节进入,"
                  "前四分之一不出现核心冲突的正面交锋,信息释放后置,靠物象蓄压。"},
    {"key": "in_medias_res",
     "directive": "本候选策略【事中切入·快节奏】:第一句已在冲突中段,来龙去脉靠回溯碎片"
                  "补齐,信息前密后疏,节奏前紧后松。"},
    {"key": "slow_burn",
     "directive": "本候选策略【慢炖·关系先行】:先走人物关系与日常颗粒,冲突信息匀速渗漏,"
                  "最后四分之一才收紧发难。"},
    {"key": "dialogue_driven",
     "directive": "本候选策略【对话驱动·藏锋】:以对话推进主体,信息全在话缝与不说之间,"
                  "叙述只给动作与物象,零内心解说。"},
]

PSEUDO_DIST_MIN = 0.12   # 自由维度归一距离下限(自定口径,样本积累后按分位数重标定,D-019)

# L1 轻选择:只用两条差异最大的策略轴(切入 vs 节奏),短包扫描级,非三整章。
L1_STRATEGIES = [STRATEGIES[0], STRATEGIES[2]]  # cold_open + slow_burn
L1_MAX_CHARS = 800  # 短变体字数软上限(编排层截断 head;生成端应用同口径)


def is_key_chapter(meta: dict) -> bool:
    """关键章判定(蓝图:转折/开局/卷尾/反转——合同字段现成可判):
    role∈{高压,关系回收} 或含 reversal_type。无标注不触发(N 倍成本只花刀刃)。
    键名兼容:parse_chapter_meta 生产输出是 'role'(P2 真机发现:此前只认
    'chapter_role' 与 stub 测试互为假绿,真标注章被 422 拦——契约以生产源为准)。"""
    m = meta or {}
    role = m.get("role") or m.get("chapter_role")
    return (role in ("高压", "关系回收")) or bool(m.get("reversal_type"))


def round_robin_rank(texts: list[str], judge_fn) -> dict:
    """全循环双向成对比较 + 胜场聚合(D-019:pairwise>绝对分,但位置偏置全类型存在、
    且有 A>B>C>A 非传递循环——两个防线:①每对两方向各评一次(位置对换),同对两
    方向矛盾 = 位置偏置,记 inconsistent;②胜场出现并列/环 → consensus=False,
    order=None,不硬给排序(评审无共识,直接交人——rubric 绝不门禁的排序版)。"""
    n = len(texts)
    wins = {str(i): 0 for i in range(n)}
    inconsistent_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            a_first = judge_fn(texts[i], texts[j])   # i 在 A 位
            b_first = judge_fn(texts[j], texts[i])   # 位置对换,j 在 A 位
            w1 = i if a_first == "A" else j
            w2 = j if b_first == "A" else i
            if w1 != w2:
                inconsistent_pairs += 1   # 同对两方向矛盾:位置偏置信号,双方各计半场不计
                continue
            wins[str(w1)] += 2
    order = sorted(range(n), key=lambda k: -wins[str(k)])
    scores = [wins[str(k)] for k in order]
    # 共识判据:无矛盾对,且胜场严格递减(并列=环/无差别,不硬排)
    consensus = inconsistent_pairs == 0 and all(
        scores[k] > scores[k + 1] for k in range(len(scores) - 1))
    return {"wins": wins, "order": order if consensus else None,
            "consensus": consensus, "inconsistent_pairs": inconsistent_pairs,
            "comparisons": n * (n - 1)}


def _free_axis_distance(p1: dict, p2: dict) -> float:
    """合同未约束的自由维度距离(归一):句长CV(0-1.5 归一)+对话占比(天然 0-1)
    +标点节奏向量余弦距离,等权平均。"""
    d_cv = min(abs((p1.get("sent_cv") or 0) - (p2.get("sent_cv") or 0)) / 1.5, 1.0)
    d_ratio = abs((p1.get("dialogue_ratio") or 0) - (p2.get("dialogue_ratio") or 0))
    v1 = p1.get("punct_per_k") or {}
    v2 = p2.get("punct_per_k") or {}
    keys = sorted(set(v1) | set(v2))
    if keys:
        a = [v1.get(k) or 0.0 for k in keys]
        b = [v2.get(k) or 0.0 for k in keys]
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        d_punct = 1 - (sum(x * y for x, y in zip(a, b)) / (na * nb)) if na and nb else 0.0
    else:
        d_punct = 0.0
    return (d_cv + d_ratio + d_punct) / 3


def pseudo_diversity(profiles: list[dict]) -> dict:
    """伪多样判定:任意两候选自由维度距离 < PSEUDO_DIST_MIN → pseudo=True。
    只看自由维度(D-019:合同必达项导致的结构同质不纳入,防重生成死循环)。"""
    near = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            if _free_axis_distance(profiles[i], profiles[j]) < PSEUDO_DIST_MIN:
                near.append([i, j])
    return {"pseudo": bool(near), "near_pairs": near}


def run_selection(*, chapter: int, generate, post_check, persist_candidate,
                  profile_fn, judge_fn, journal, n: int = 3,
                  save_result=None) -> dict:
    """选择环编排:
    generate(strategy: dict) -> prose             按策略出候选(完整组装链+策略段)
    post_check(prose) -> dict                     /post-check 同构(过滤输入)
    persist_candidate(prose, strategy_key) -> id  候选留版本
    profile_fn(prose) -> dict                     qd 特征(伪多样判定)
    judge_fn(a, b) -> 'A'|'B'                     成对比较(rubric 初筛员)
    返回 {candidates:[{strategy,version_id,filtered,filter_reason,profile,
    rubric_rank,prose_head}], consensus, verdict:'awaiting_human', ...}——
    机器只备料,终选永远在人(宪法:rubric 只排序不门禁)。"""
    used = STRATEGIES[:n]
    cands: list[dict] = []
    gen_errors: list[str] = []
    for s in used:
        stage = f"sel_ch{chapter}_gen_{s['key']}"
        journal.start_stage(stage)
        try:
            prose = generate(s)
        except Exception as e:   # B1:一发失败不炸全部——跳过该候选、清 journal in_progress、继续其余
            _log.warning("selection 候选 %s 生成失败(跳过): %s", s["key"], e)
            gen_errors.append(f"{s['key']}:{str(e)[:80]}")
            journal.complete_stage(stage)
            continue
        journal.complete_stage(stage)
        cands.append({"strategy": s["key"], "prose": prose})
    if not cands:   # 全部失败:诚实返回 all_failed,不假装有候选(前端据此提示查网关/日帽)
        return {"chapter": chapter, "candidates": [], "consensus": None,
                "verdict": "all_failed", "gen_errors": gen_errors,
                "note": "所有候选生成失败(检查 LLM 网关/日帽);无候选可选",
                "journal_recorded": True}

    # 伪多样检测:命中→用未出战策略重生成一次(换轴,绝不同参重掷)
    pseudo_round = False
    profs = [profile_fn(c["prose"]) for c in cands]
    pd = pseudo_diversity(profs)
    if pd["pseudo"] and len(STRATEGIES) > n:
        spare = STRATEGIES[n]
        i_replace = pd["near_pairs"][0][1]   # 换掉相近对的后者
        stage = f"sel_ch{chapter}_gen_{spare['key']}"
        journal.start_stage(stage)
        try:   # B1:重生成失败不炸——保留原候选(伪多样但至少有稿),同主循环容错
            prose = generate(spare)
            cands[i_replace] = {"strategy": spare["key"], "prose": prose}
            profs[i_replace] = profile_fn(prose)
            pseudo_round = True
        except Exception as e:
            _log.warning("selection 伪多样重生成 %s 失败(保留原候选): %s", spare["key"], e)
            gen_errors.append(f"{spare['key']}(重生成):{str(e)[:80]}")
        journal.complete_stage(stage)

    # 确定性过滤(写前可判子集:triage blocking——泄密/退化/ai heavy/S1)
    journal.start_stage(f"sel_ch{chapter}_filter")
    for c, p in zip(cands, profs):
        post = post_check(c["prose"])
        tri = triage(post)
        c["profile"] = p
        c["filtered"] = tri["verdict"] == "blocking"
        c["filter_reason"] = ("、".join(sorted({b["detector"] for b in tri["blocking"]}))
                              if c["filtered"] else "")
        c["advisory_count"] = tri["advisory_count"]
        try:
            # 击杀候选仍留版(可展开审计),但 strategy 后缀 ·filtered 写入 label,
            # 供 /select/finalize 拒绝「把被杀稿定稿」(防 API 绕过前端)。
            persist_key = c["strategy"] + ("·filtered" if c["filtered"] else "")
            c["version_id"] = persist_candidate(c["prose"], persist_key)
        except Exception as e:
            _log.warning("selection 候选留版失败(继续): %s", e)
            c["version_id"] = None
    journal.complete_stage(f"sel_ch{chapter}_filter")

    # rubric 批次粗排(只对幸存者;只排序绝不门禁)
    journal.start_stage(f"sel_ch{chapter}_rank")
    alive_idx = [i for i, c in enumerate(cands) if not c["filtered"]]
    consensus = None
    if len(alive_idx) >= 2:
        rr = round_robin_rank([cands[i]["prose"] for i in alive_idx], judge_fn)
        consensus = rr["consensus"]
        if rr["order"] is not None:
            for rank, k in enumerate(rr["order"]):
                cands[alive_idx[k]]["rubric_rank"] = rank + 1
        else:
            for i in alive_idx:
                cands[i]["rubric_rank"] = None   # 评审无共识:不给排序,直接交人
    elif len(alive_idx) == 1:
        cands[alive_idx[0]]["rubric_rank"] = 1
        consensus = True
    journal.complete_stage(f"sel_ch{chapter}_rank")

    for c in cands:
        c["prose_head"] = c["prose"][:300]
        c.setdefault("rubric_rank", None)

    out_cands = [{k: v for k, v in c.items() if k != "prose"} for c in cands]
    # P2门审查 P2-2:展示序洗牌——此前候选卡顺序恒等策略序,"甲乙丙"两次就被
    # 记住(标签隐藏了、位置没盲),叠加降级排序会恒定锚向首策略。
    import random as _rnd
    _rnd.shuffle(out_cands)
    # 全灭(均被确定性过滤):诚实 verdict,前端禁止假终选、提示 force 重跑或改驱动语
    all_filtered = bool(cands) and all(c.get("filtered") for c in cands)
    verdict = "all_filtered" if all_filtered else "awaiting_human"
    note = (
        "全部候选被确定性过滤击杀(谁被杀/为什么见 filter_reason);"
        "可 force 重跑或改驱动语后重出,勿把击杀稿定稿"
        if all_filtered else
        "机器只备料:过滤明细与排序仅供参考,终选与理由在作者(理由入 lesson 流)"
    )
    result = {"chapter": chapter,
              "candidates": out_cands,
              "consensus": consensus,
              "pseudo_diversity_round": pseudo_round,
              "gen_errors": gen_errors,   # B1:部分候选生成失败(前端可提示「N 个策略未出稿」)
              "verdict": verdict,
              "journal_recorded": True,
              "note": note}
    if save_result is not None:
        try:
            save_result(result)   # P2-3:结果落 journal 旁文件,断连不丢元数据
        except Exception as e:
            _log.warning("selection 结果落盘回调失败(忽略): %s", e)
    return result


def _clip_short(text: str, max_chars: int = L1_MAX_CHARS) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    # 优先在句号/换行处切断,避免半句
    cut = t[:max_chars]
    for sep in ("。", "！", "？", "\n", "…"):
        i = cut.rfind(sep)
        if i >= max_chars // 2:
            return cut[: i + 1]
    return cut + "…"


def run_light_selection(*, chapter: int, generate, persist_variant,
                        journal=None, save_result=None,
                        max_chars: int = L1_MAX_CHARS) -> dict:
    """L1 轻选择编排:同一合同出 **2** 条策略短变体(开场/切入包,非三整章)。

    generate(strategy: dict) -> str     按策略出短稿(注入端应要求 ≤max_chars)
    persist_variant(text, strategy_key) -> id   留 light_variant 版,回 id
    无 LLM 裁判、无确定性 heavy filter(成本刀刃在 L2);人扫读后 pick。

    返回 {
      tier: 'L1',
      chapter,
      variants: [{strategy, version_id, text, text_head, directive}],
      verdict: 'awaiting_pick' | 'all_failed',
      gen_errors, note
    }
    """
    used = list(L1_STRATEGIES)
    variants: list[dict] = []
    gen_errors: list[str] = []
    for s in used:
        stage = f"sel_l1_ch{chapter}_gen_{s['key']}"
        if journal is not None:
            journal.start_stage(stage)
        try:
            raw = generate(s)
            text = _clip_short(str(raw or ""), max_chars)
            if len(text.strip()) < 40:
                raise RuntimeError(f"策略 {s['key']} 短变体过短")
            vid = None
            try:
                vid = persist_variant(text, s["key"])
            except Exception as e:
                _log.warning("L1 变体留版失败(继续): %s", e)
            variants.append({
                "strategy": s["key"],
                "directive": s.get("directive") or "",
                "version_id": vid,
                "text": text,
                "text_head": text[:200],
                "char_count": len(text),
            })
        except Exception as e:
            _log.warning("L1 变体 %s 生成失败: %s", s["key"], e)
            gen_errors.append(f"{s['key']}:{str(e)[:80]}")
        if journal is not None:
            journal.complete_stage(stage)

    if not variants:
        result = {
            "tier": "L1",
            "chapter": chapter,
            "variants": [],
            "verdict": "all_failed",
            "gen_errors": gen_errors,
            "note": "L1 两条短变体均失败(检查 LLM/日帽);可改驱动语后重试或走 L2",
            "max_chars": max_chars,
        }
    elif len(variants) == 1:
        result = {
            "tier": "L1",
            "chapter": chapter,
            "variants": variants,
            "verdict": "awaiting_pick",
            "gen_errors": gen_errors,
            "note": "仅一条短变体成功;仍可挑选或重跑/升级 L2 三候选",
            "max_chars": max_chars,
        }
    else:
        result = {
            "tier": "L1",
            "chapter": chapter,
            "variants": variants,
            "verdict": "awaiting_pick",
            "gen_errors": gen_errors,
            "note": "轻选择:扫读两条策略短包后点选;选中会写入草稿种子,再扩写成正文(非三整章成本)",
            "max_chars": max_chars,
        }
    if save_result is not None:
        try:
            save_result(result)
        except Exception as e:
            _log.warning("L1 结果落盘回调失败(忽略): %s", e)
    return result


def apply_light_pick(*, variants: list[dict], version_id: str | None = None,
                     strategy: str | None = None) -> dict:
    """从 L1 variants 中解析人的选择;返回 {strategy, text, version_id} 或 raise ValueError。

    纯函数:不碰 store。调用方负责把 text 写入 draft/种子。
    """
    if not variants:
        raise ValueError("无 L1 变体可选")
    hit = None
    if version_id:
        hit = next((v for v in variants if v.get("version_id") == version_id), None)
    if hit is None and strategy:
        hit = next((v for v in variants if v.get("strategy") == strategy), None)
    if hit is None:
        raise ValueError("未匹配到 version_id/strategy 对应的 L1 变体")
    text = (hit.get("text") or "").strip()
    if not text:
        raise ValueError("选中变体正文为空")
    return {
        "strategy": hit.get("strategy"),
        "version_id": hit.get("version_id"),
        "text": text,
        "directive": hit.get("directive") or "",
        "char_count": len(text),
    }

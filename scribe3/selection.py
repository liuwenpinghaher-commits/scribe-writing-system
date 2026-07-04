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
                  profile_fn, judge_fn, journal, n: int = 3) -> dict:
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
    for s in used:
        stage = f"sel_ch{chapter}_gen_{s['key']}"
        journal.start_stage(stage)
        prose = generate(s)
        journal.complete_stage(stage)
        cands.append({"strategy": s["key"], "prose": prose})

    # 伪多样检测:命中→用未出战策略重生成一次(换轴,绝不同参重掷)
    pseudo_round = False
    profs = [profile_fn(c["prose"]) for c in cands]
    pd = pseudo_diversity(profs)
    if pd["pseudo"] and len(STRATEGIES) > n:
        pseudo_round = True
        spare = STRATEGIES[n]
        i_replace = pd["near_pairs"][0][1]   # 换掉相近对的后者
        stage = f"sel_ch{chapter}_gen_{spare['key']}"
        journal.start_stage(stage)
        prose = generate(spare)
        journal.complete_stage(stage)
        cands[i_replace] = {"strategy": spare["key"], "prose": prose}
        profs[i_replace] = profile_fn(prose)

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
            c["version_id"] = persist_candidate(c["prose"], c["strategy"])
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

    return {"chapter": chapter,
            "candidates": [{k: v for k, v in c.items() if k != "prose"} for c in cands],
            "consensus": consensus,
            "pseudo_diversity_round": pseudo_round,
            "verdict": "awaiting_human",
            "journal_recorded": True,
            "note": "机器只备料:过滤明细与排序仅供参考,终选与理由在作者(理由入 lesson 流)"}

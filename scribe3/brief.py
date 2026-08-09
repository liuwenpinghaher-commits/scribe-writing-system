"""章前组装器:把弧光/伏笔/开环/心跳组装成「本章创作简报」,注入写作 system prompt。
设计:设计文档/2026-07-03-工艺引擎强化-design.md 第二节。
纯函数生成各 section(可测不连库);assemble_chapter_brief 是唯一连 store 的薄壳。"""
from __future__ import annotations

import json
import logging
import re

_log = logging.getLogger("scribe3")

_TIER_W = {"book": 3, "arc": 2, "chapter": 1}
_SALIENCE_GAP_MAX = 3   # 距上次露面超过此章数 → 兑现前先刷新
_REFRESH_EXHAUSTED = 3  # 刷新≥此次数仍未兑现 → 读者已猜到,升决策禁续刷(工艺 M1)
_LOOP_CAP = 12          # 开环加权上限
_M6_BUDGET_CHARS = 1200  # M6 设定注入字符预算(全知分支;超出按 always优先/priority 降序裁)

# ===== 方案B任务17 · 平台留存轴确定性指标(纯文本层)=====
# 与 scribe3/critique.py 的 _PLATFORM_RUBRICS[platform]["word_range"] 数值保持一致
# (人工同步,故意不跨模块 import——tension_deterministic 签名 (st, seq) 有状态,平台
# 确定性指标只吃纯文本、无状态,分开更干净;critique.py 的 build_platform_rubric_prompt
# 走 LLM 轴,本处只做"可用正则/计数机械判定"的那部分)。
_PLATFORM_WORD_RANGE = {
    "qidian": (2000, 4000),
    "fanqie": (1500, 2500),
    "zhihu": (8000, 13000),
}
_VISIBLE_CHAR_RE = re.compile(r"[一-鿿Ａ-ｚA-Za-z0-9]")   # 可见字符:CJK+全角/半角字母数字,剔标点空白
_QUOTE_SPAN_RE = re.compile(r"[“「][^”」]{0,2000}[”」]", re.S)   # 对话span:中文弯引号/直角引号包裹


def _visible_len(s: str) -> int:
    """可见字数(剔除标点/空白后的有效字符计数),口径同 critique._degen_visible_length。"""
    return len(_VISIBLE_CHAR_RE.findall(s or ""))


def platform_deterministic(text: str, platform: str) -> list[dict]:
    """平台留存轴里"可用正则/计数机械判定"的确定性指标(独立新函数,不动
    tension_deterministic——它签名 (st, seq) 有状态,平台确定性指标是纯文本层,
    分开更干净)。返回 [{"metric","value","ok","note"}]。

    - word_count:可见字数(剔标点/空白)+ 是否落在该平台章字数参考区间(word_range)。
    - dialogue_ratio:引号(“”「」)内可见字数 / 全文可见字数——对话密度参考,无固定
      阈值判 pass/fail(ok 恒 True,仅供作者/编排层参考)。

    爽点密度/情绪节点密度等指标需要"标注情绪节点/剧情事件"才能判——机器读不懂语义,
    不在此覆盖,走 critique.build_platform_rubric_prompt 的 LLM 轴。

    非法 platform(不在三者之内)直接 ValueError,与 critique.build_platform_rubric_prompt
    同一口径——平台留存不是默认轴,拼错平台名不该静默退化。
    """
    if platform not in _PLATFORM_WORD_RANGE:
        raise ValueError(f"未知平台: {platform!r},仅支持 {tuple(_PLATFORM_WORD_RANGE)}")
    lo, hi = _PLATFORM_WORD_RANGE[platform]
    wc = _visible_len(text)
    items = [{
        "metric": "word_count",
        "value": wc,
        "ok": lo <= wc <= hi,
        "note": f"该平台章字数参考区间 {lo}-{hi},实际可见字数 {wc}",
    }]
    quoted_len = sum(_visible_len(m.group(0)) for m in _QUOTE_SPAN_RE.finditer(text or ""))
    ratio = round(quoted_len / wc, 4) if wc else 0.0
    items.append({
        "metric": "dialogue_ratio",
        "value": ratio,
        "ok": True,   # 无固定阈值,仅供参考
        "note": f"引号内可见字数 {quoted_len} / 全文可见字数 {wc}",
    })
    return items


def arc_directive(name: str, anchors: dict, arc_plan: list[dict],
                  lie_belief: int | None, next_ch: int) -> str:
    """单角色弧光三行指令：以 arc_beat_focus 为权威（KD18），避免与逾期决策自相矛盾。"""
    from scribe3 import arc_signals as AS
    focus = AS.arc_beat_focus(
        arc_plan or [],
        belief=lie_belief,
        next_ch=next_ch,
        arc_type=(anchors or {}).get("arc_type"),
        slack=AS.ARC_BELIEF_SLACK,
    )
    return AS.arc_directive_from_focus(
        name, anchors or {}, focus, lie_belief, next_ch, plan=arc_plan or [])


def promise_directives(rows: list[dict]) -> dict:
    """按窗口态分流:in_window→软提醒;over_half→简报指令(salience 低则先刷新);
    overdue→三选一决策。返回 {reminders, directives, decisions}(均为文案列表)。"""
    reminders, directives, decisions = [], [], []
    for p in rows:
        w = p.get("window") or {}
        state, gap = w.get("state"), w.get("salience_gap") or 0
        text = (p.get("text") or "").replace("\n", " ")[:40]   # Task7-B②:清洗换行
        rc = int(p.get("refresh_count") or 0)
        if state == "in_window":
            reminders.append(f"「{text}」在兑现窗口内,适时推进")
        elif state == "over_half" and rc >= _REFRESH_EXHAUSTED:
            # 工艺引擎 M1 兑现前置门槛后半:刷新≥3 次仍未兑现 → 读者大概率已猜到,
            # 再刷新只会腻——升级为决策项,禁止继续"蓄势"。
            decisions.append(
                f"伏笔「{text}」已刷新 {rc} 次仍未兑现:读者大概率已猜到,再刷新只会腻——"
                f"本章 s3_advance_promise 兑现,或 s3_patch_promise 展期 / s3_abandon_promise 弃置,"
                f"不要再安排刷新")
        elif state == "over_half":
            if gap > _SALIENCE_GAP_MAX:
                directives.append(
                    f"伏笔「{text}」已过窗口一半且久未露面({gap}章):本章先安排一次"
                    f"不动声色的刷新(换伪装:道具/闲笔/情绪),为兑现蓄势——先刷新,勿直接兑现")
            else:
                directives.append(f"伏笔「{text}」已过窗口一半:本章应实质推进或兑现")
        elif state == "overdue":
            decisions.append(
                f"伏笔「{text}」已超兑现窗口:请作者三选一——"
                f"① s3_advance_promise 立即兑现;② s3_patch_promise 展期(改 tier/窗口);"
                f"③ s3_abandon_promise 弃置结案(status=abandoned,≠障眼法)。"
                f"障眼法另用 s3_mark_herring。系统默认本章简报持续携带直至决策。")
    return {"reminders": reminders, "directives": directives, "decisions": decisions}


# ===== 北极星任务2 · 因果欠账催收(蓝图 §3-②)=====

_CAUSAL_TOP_N = 5          # 注入量硬上限(v2 量控):违规量受制于 ingest 抽取质量,
                           # 超出只计 overflow(面板/scorecard 消费),不塞爆 brief
_CAUSAL_LOOKBACK = 8       # 催收回看窗口(章),对齐 _avoid_directive 的 lookback=8 先例


def causal_directives(violations: list[dict], no_event_data: bool,
                      top_n: int = _CAUSAL_TOP_N) -> dict:
    """把上文 causal_complete 违规转译成下一章 brief 的三选一软指令。

    violation 可能是抽取漏而非叙事漏(motivated_by_goal/causal_in 是 ingest 时
    LLM 抽取的自由文本)——所以必须是"三选一软指令"而非硬约束,给"抽取误报"留出口。
    no_event_data=True → 整段不渲染(沿用 /causal 假绿防护语义:没数据≠没欠账)。
    violations 元素:{"chapter", "event_id", "reason"};按章序倒序(最近优先)取 top_n。
    返回 {"directives": [...], "overflow": 截断条数, "total": 总违规数}。
    """
    if no_event_data or not violations:
        return {"directives": [], "overflow": 0, "total": 0}
    ordered = sorted(violations, key=lambda v: -(v.get("chapter") or 0))
    dirs = []
    for v in ordered[:top_n]:
        eid = (str(v.get("event_id") or "?")).replace("\n", " ")[:40]   # Task7-B② 清洗先例
        lack = "缺因果入边" if "causal_in" in (v.get("reason") or "") else "缺动机"
        dirs.append(
            f"上文第{v.get('chapter')}章事件「{eid}」{lack}:本章三选一——"
            f"①补交代其动机或前因;②显式转为悬念(挂 promise,tier=chapter);"
            f"③标记为抽取误报待清洗。")
    return {"directives": dirs,
            "overflow": max(0, len(ordered) - top_n),
            "total": len(ordered)}


def open_loop_ledger(rows: list[dict], cap: int = _LOOP_CAP) -> dict:
    """开环账本:tier 加权计数(book×3/arc×2/chapter×1),只计窗口态非 inactive 的 open 线。"""
    weighted = sum(_TIER_W.get(p.get("tier") or "chapter", 1)
                   for p in rows if (p.get("window") or {}).get("state") not in (None, "inactive"))
    return {"weighted": weighted, "cap": cap, "over_cap": weighted > cap}


# ===== 方案B任务19 · 跨批开放伏笔账本注入 reviewer(scribe3 DB 优势区)=====
# 背景(oh-story story-review/SKILL.md:133):审章前先读开放伏笔("预计回收章≤本章"
# 的 open promise)作"继承的开放项"注入 reviewer——oh-story 靠人工维护的伏笔.md 文件
# 做这件事(demo 实锤:51 条全 [待补充] 冻结,等于没做);scribe3 有活 DB,直接对
# promises_with_lifecycle/list_promises 的结果按窗口字段筛,不依赖任何人工台账。
def inherited_open_block(rows: list[dict], chapter: int) -> dict:
    """筛出「审查本章(chapter)时已到期/在兑现窗口内」的 open promise,组装成
    一段可直接拼进 reviewer prompt 的"继承的开放项"文案。

    到期口径(不依赖 window 计算态字段,rows 可以是 list_promises 的裸行):
    status=="open" 且满足以下任一:
      - payoff_max 非 None 且 payoff_max<=chapter(已到/超兑现窗口终点,含 overdue);
      - payoff_min<=chapter<=payoff_max(仍在兑现窗口内,尚未到终点但已该露面)。
    book 层 payoff_max 常年为 None(无远期上限),只会命中第一条为假、第二条也因
    payoff_max 为 None 而跳过——不会被误判到期,措辞/口径与 promise_directives(:90)一致。
    """
    due = []
    for p in rows:
        if p.get("status") != "open":
            continue
        pmin, pmax = p.get("payoff_min"), p.get("payoff_max")
        if pmax is not None and pmax <= chapter:
            due.append(p)
        elif pmin is not None and pmax is not None and pmin <= chapter <= pmax:
            due.append(p)
    if not due:
        return {"text": "", "items": due}
    lines = "\n".join(
        f"  · 「{(p.get('text') or '').replace(chr(10), ' ')}」(tier={p.get('tier') or 'chapter'},"
        f"兑现窗口 {p.get('payoff_min')}-{p.get('payoff_max') if p.get('payoff_max') is not None else '无上限'})"
        for p in due)
    text = ("继承的开放项(审查本章是否推进/回收了它们;未处理的要在 findings 里指出):\n" + lines)
    return {"text": text, "items": due}


def tension_deterministic(st, seq: int) -> list[dict]:
    """章后确定性张力项:进展路标 / 信息差盘点 / 开环账本。每项 {item, pass, detail, fix}。

    - promise_progress:本章(seq)是否至少推进一条 open 伏笔(promise_touch 的 last_refresh_at==seq);
      若无任何开着的 active 伏笔则视为无需推进(pass)。
    - open_loops:加权开环是否超上限(open_loop_ledger)。
    - irony_surface:读者知/在场焦点者不知的命题(戏剧反讽面)。dramatic_irony 是 knowledge.py
      的模块函数(world, focalizer, chapter);此处按本章 focalizer 计算,取不到 focalizer/知识边
      时 fail-safe 空列表(pass=False 属预期,提示主动制造信息差)。"""
    rows = st.promises_with_lifecycle(max_chapter=seq)
    touched = [p for p in rows if p.get("last_refresh_at") == seq]
    open_active = [p for p in rows if (p.get("window") or {}).get("state") not in (None, "inactive")]
    items = [{
        "item": "promise_progress",
        "pass": bool(touched) or not open_active,
        "detail": f"本章推进伏笔 {len(touched)} 条 / 开着 {len(open_active)} 条",
        "fix": "下一章至少让一条 open 伏笔产生路标级进展(关键信息/新障碍/关键决定)",
    }]
    led = open_loop_ledger(rows)
    items.append({"item": "open_loops", "pass": not led["over_cap"],
                  "detail": f"加权开环 {led['weighted']}/{led['cap']}",
                  "fix": "先收一条再开新坑"})
    # 信息差盘点:读者知而在场焦点者不知的命题数(irony 面)。空 → 提示主动制造。
    irony = []
    try:
        from scribe3.knowledge import dramatic_irony
        ch = st.get_chapter(seq) if hasattr(st, "get_chapter") else None
        foc = (ch or {}).get("focalizer")
        if foc:
            irony = dramatic_irony(st, foc, seq)
    except Exception:
        irony = []
    items.append({"item": "irony_surface", "pass": bool(irony),
                  "detail": f"读者知/角色不知命题 {len(irony)} 条",
                  "fix": "考虑向读者(而非角色)提前揭示某高危信息,把后续普通戏变成悬念戏"})
    return items


# ===== 方案B任务12 · 连续性 heat/last_touch 状态机 + 关系触碰追踪 =====
# 背景(oh-story plot-core-methods.md:254-276):角色/支线/伏笔/关系维护 heat + last_touch_chapter;
# 有效触碰判定(推进/施压/改变关系/产生后果才算,提名字不算);回顾阈值(核心角色 3-5 章/主要支线 4-6 章)。
# scribe3 既有 promise 的 last_refresh_at、char 的 last_active——本任务补统一 heat 语义 +
# 新增"关系"维度触碰追踪(真新增,不重复既有 promise_touch/heartbeat_list 逻辑)。

_HEAT_HOT_MAX = 2    # 距上次触碰 ≤2 章 → hot
_HEAT_WARM_MAX = 5   # 3~5 章 → warm;>5 章(或从未触碰)→ cold


def heat_of(last_touch: int | None, current: int) -> str:
    """纯函数:按距上次有效触碰的章数算 heat 档位。
    hot(≤2 章)/ warm(3~5 章)/ cold(>5 章,或从未触碰 last_touch=None)。"""
    if last_touch is None:
        return "cold"
    gap = current - last_touch
    if gap <= _HEAT_HOT_MAX:
        return "hot"
    if gap <= _HEAT_WARM_MAX:
        return "warm"
    return "cold"


def stale_entity_directives(rows: list[dict], next_ch: int) -> dict:
    """纯函数:cold 实体(该 warm 却 cold)生成"本章须安排有效触碰"指令段。
    rows: [{name, kind, last_touch}],kind 为 char/promise/relation 等维度标签任意字符串。
    返回 {"text": 指令段文案(无 cold 实体则空串), "items": [{name, kind, heat, last_touch}](仅 cold)}。"""
    items = []
    for r in rows:
        h = heat_of(r.get("last_touch"), next_ch)
        if h == "cold":
            items.append({"name": r.get("name"), "kind": r.get("kind"),
                         "heat": h, "last_touch": r.get("last_touch")})
    if not items:
        return {"text": "", "items": []}
    listing = "；".join(f"{i['name']}({i['kind']})" for i in items)
    text = (
        f"【连续性提醒·该 warm 却 cold】{listing} 距上次有效触碰已过久:"
        "本章须为其安排一次有效触碰(推进/施压/改变关系/产生后果才算,"
        "仅提名字/空头回调不算)。回顾阈值参考:核心角色 3-5 章一次,主要支线 4-6 章一次。"
    )
    return {"text": text, "items": items}


def heartbeat_list(chars: list[dict], next_ch: int, gap: int = 3) -> list[dict]:
    """待激活名单:有 private_agenda 且距上次活跃超过 gap 章的角色。
    last_active is None（从未活跃）视为 0 / 永久 cold，可入名单（P1b）。"""
    out = []
    for c in chars:
        agenda = (c.get("private_agenda") or "").replace("\n", " ").strip()   # Task7-B②
        last = c.get("last_active")
        if not agenda:
            continue
        # 从未活跃：当作 last_active=0，允许进入待激活
        last_n = 0 if last is None else int(last)
        if next_ch - last_n > gap:
            out.append({"name": (c["name"] or "").replace("\n", " "),   # Task8审查:name 清洗
                        "agenda": agenda, "last_active": last if last is not None else 0})
    return out


# ===== 方案B任务15 · EM/RH/TR 情绪模式库(章前按目标情绪召回)=====
# 背景(oh-story long-analyze/output-templates.md:359-370):EM-001情绪模块卡/
# RH-001爽点循环/TR-001触动点三张带 id 互引 schema;统一挂 store material 表
# kind="emotion_module",卡内容为 JSON,id 前缀 EM-/RH-/TR- 自行区分,互引用 id 字符串。
# canonical-read-order:情绪模块卡是权威真相源,拆文报告只是投影——与拆文报告冲突时
# 以本卡为准。量化门:反应篇幅比=反应字数/装逼字数,<1.5 视为爽感没接住。
# 反抄袭边界:原文专名/事件顺序/标志台词/独特设定不可照搬,迁移至少改 3 项。

def emotion_module_recall(materials: list[dict], target_emotion: str) -> dict:
    """章前按目标情绪从素材库召回 emotion_module 卡,拼成写作指令段。

    materials: 素材列表,元素需含 "kind"(=="emotion_module" 才参与召回)与卡片 JSON
    文本字段——兼容 store.list_materials() 的 "body" 字段与调用方直传的 "content" 字段
    (优先取 "content",取不到再退回 "body")。
    target_emotion: 目标情绪,子串匹配容错(卡片 emotion 字段包含 target_emotion 即命中,
    反向亦可——避免"憋屈"与"憋屈感"这类措辞差异漏召回)。
    JSON 解析失败或字段缺失的卡 fail-soft 跳过,不影响其余卡片召回。
    返回 {"text": 指令段文案(无命中则空串), "items": [命中的卡片 dict,原始 JSON 解析结果]}。
    """
    items: list[dict] = []
    if target_emotion:
        for m in materials or []:
            if (m or {}).get("kind") != "emotion_module":
                continue
            raw = m.get("content")
            if raw is None:
                raw = m.get("body")
            try:
                card = json.loads(raw) if raw else None
            except (TypeError, ValueError):
                continue
            if not isinstance(card, dict):
                continue
            emotion = card.get("emotion") or ""
            if not emotion:
                continue
            if target_emotion in emotion or emotion in target_emotion:
                items.append(card)
    if not items:
        return {"text": "", "items": []}
    cards_text = "\n".join(
        f"- 【{c.get('id', '?')}】情绪:{c.get('emotion', '?')} | "
        f"触发:{c.get('trigger', '?')} | 蓄力:{c.get('escalation', '?')} | "
        f"释放:{c.get('release', '?')}"
        for c in items
    )
    text = (
        "【情绪模块卡·权威真相源】以下卡片是本章目标情绪的权威真相源,与拆文报告冲突时"
        "以本卡为准:\n"
        f"{cards_text}\n"
        "量化门:反应篇幅比=反应字数/装逼字数,<1.5=爽感没接住——蓄力(escalation)与"
        "释放(release)后须给足角色/旁观者反应篇幅。\n"
        "反抄袭边界:原文专名/事件顺序/标志台词/独特设定不可照搬,迁移至少改 3 项。"
    )
    return {"text": text, "items": items}


# ===== Task 8 · M6 设定三态注入(纯函数)=====

def detect_mentions(text: str, entities: list[dict]) -> set[str]:
    """本章草料文本(synopsis+beats+演绎)中按 名字/别名 包含匹配命中的实体 id 集。
    Task8审查:单字(<2)名字/别名不参与子串匹配——防「玉」「柳」等误命中大量无关文本。"""
    hit = set()
    t = text or ""
    for e in entities:
        names = [e.get("name") or ""] + list(e.get("aliases") or [])
        if any(len(n) >= 2 and n in t for n in names):
            hit.add(e["id"])
    return hit


def select_injection(items: list[dict], mentioned_entities: set[str],
                     budget_chars: int = _M6_BUDGET_CHARS) -> dict:
    """三态注入 + 预算裁剪。item: {id, entity, text, mode(always/detected/never), priority}。
    always 恒进;detected 须实体被提及;never 恒不进。超预算按 (always优先, priority 降序) 裁。"""
    def _mode(i):
        return i.get("mode") or "detected"
    pool = [i for i in items if _mode(i) == "always"] + sorted(
        [i for i in items if _mode(i) == "detected" and i.get("entity") in mentioned_entities],
        key=lambda i: -(i.get("priority") or 0))
    chosen, used, dropped = [], 0, 0
    for i in pool:
        cost = len(i.get("text") or "")
        if used + cost > budget_chars and _mode(i) != "always":
            dropped += 1
            continue
        chosen.append(i)
        used += cost
    return {"chosen": chosen, "dropped": dropped, "used_chars": used}


def chapter_draft_text(ch: dict | None) -> str:
    """本章草料文本:synopsis + beats(条目 text)+ scene_truth 拼接。空章 → 空串。"""
    if not ch:
        return ""
    parts = [ch.get("synopsis") or ""]
    for b in ch.get("beats") or []:
        parts.append((b.get("text") if isinstance(b, dict) else str(b)) or "")
    parts.append(ch.get("scene_truth") or "")
    return "\n".join(p for p in parts if p)


def _fact_inject_line(f) -> str:
    """把一条 Fact 渲染成注入行内容(不含前导「- 」);secret 标私密/伏线。"""
    secret = getattr(f, "secret", False)
    return (f"{getattr(f, 'entity_id', '')} · {getattr(f, 'attribute', '')}:"
            f"{getattr(f, 'value', '')}" + ("(私密/伏线)" if secret else ""))


def assemble_injection(st, seq, budget_chars: int = _M6_BUDGET_CHARS) -> dict:
    """M6 全知分支设定注入薄壳:facts(全知)→ item → detect_mentions → select_injection。
    返回 {chosen, dropped, used_chars, fallback, facts}。

    三态是 **opt-in 特性**(Task8 审查必修1):
    - 本书从未给任何 fact 配 injection_mode → **fallback=True**,门控整体关闭,
      调用方直接走旧 facts[:28] 全量(真·向后兼容,旧书行为一字不变)。
    - 一旦 ≥1 条 fact 显式配了 injection_mode → 启用门控,逐条解析:
      · never              → 不注入;
      · detected 且挂真实实体 → 须本章草料提及该实体才注入(唯一被相关性门控的通路);
      · 其余(None / always / detected 但挂世界级命题即 entity 匹配不到真实实体)
        → **always 语义**:无条件注入,不因未提及被丢。
    注意:限知(focalizer 非空)分支不走此——先限知过滤是正确性,P0 不叠相关性过滤。"""
    # 章时间门:讨论/写作传入 seq 时只取截至本章仍有效的命题,禁止 99999 全库
    # 把未来 valid_from 事实灌进早章讨论(限知/时间一致性,2026-08 收口)。
    # seq 缺省时仍用 99999 保作者全知总览(无章上下文的横切讨论)。
    story_ch = int(seq) if seq is not None else 99999
    facts = st.facts_at(story_ch)
    any_mode = any(getattr(f, "injection_mode", None) for f in facts)
    if not any_mode:
        # 真·向后兼容:本书未配 injection_mode → 门控关闭,调用方回退旧 facts[:28]
        return {"chosen": [], "dropped": 0, "used_chars": 0, "fallback": True, "facts": facts}
    ch = st.get_chapter(seq) if seq is not None else None
    draft = chapter_draft_text(ch)
    entities = [{"id": e.id, "name": e.name,
                 "aliases": (getattr(e, "traits", None) or {}).get("aliases") or []}
                for e in st.all_entities()]
    entity_ids = {e["id"] for e in entities}
    mentioned = detect_mentions(draft, entities)
    items = []
    for f in facts:
        raw = getattr(f, "injection_mode", None)
        entity = getattr(f, "entity_id", "")
        if raw == "never":
            mode = "never"
        elif raw == "detected" and entity in entity_ids:
            mode = "detected"          # 唯一被相关性门控的通路:显式 detected + 挂真实实体
        else:
            mode = "always"            # None / always / detected-on-world-level 全走 always
        items.append({"id": getattr(f, "id", None), "entity": entity,
                      "text": _fact_inject_line(f), "mode": mode,
                      "priority": getattr(f, "priority", None)})
    sel = select_injection(items, mentioned, budget_chars)
    return {"chosen": sel["chosen"], "dropped": sel["dropped"],
            "used_chars": sel["used_chars"], "fallback": False, "facts": facts}


# ===== 方案B任务10 · 情节点字数预算契约(纯函数验证器)=====

def validate_beat_budgets(beats: list[dict], target_words: int) -> dict:
    """校验节拍(beats)字数预算求和是否落在 [target_words, target_words*1.1] 区间。

    仅当全部 beat 都带 budget 字段(非 None)才判定——旧数据(无 budget)向后兼容,
    不判、不报错,返回 ok=None。防"欠字反复回炉"/"均匀注水":
    - total < target        → ok=False, reason="under"(欠字)
    - total > target*1.1    → ok=False, reason="over"(超字)
    - 其余(区间内)          → ok=True, reason=None
    返回 {ok, total, reason}。"""
    if not beats or any(b.get("budget") is None for b in beats):
        return {"ok": None, "total": None, "reason": None}
    total = sum(b["budget"] for b in beats)
    if total > target_words * 1.1:
        return {"ok": False, "total": total, "reason": "over"}
    if total < target_words:
        return {"ok": False, "total": total, "reason": "under"}
    return {"ok": True, "total": total, "reason": None}


# ===== 方案B任务11 · 章节定位六型 + 卷级张弛基线(纯函数检测器)=====

_CHAPTER_ROLE_RE = re.compile(r"chapter_role[:：]\s*(高压|推进|修炼|关系回收|低压|信息整理)")
_PRESSURE_RE = re.compile(r"压力级[:：]\s*([1-5])")

_TENSION_WINDOW = 6   # 滑窗:6章内 pressure 全高/全低视为张弛失衡


def parse_chapter_meta(outline_text_or_beats) -> dict | None:
    """从大纲文本或节拍(beats)里解析章级定位标注:压力级(1-5)、chapter_role(六型之一)。

    入参可以是纯文本(如 synopsis 或 chapter_draft_text 的拼接结果),也可以是
    beats list[dict]/list[str](逐条 text 拼接后再解析,与其余检测器同口径)。
    正则:「压力级:N」「chapter_role:X」(全/半角冒号皆可)。
    两者都抓不到 → 返回 None(旧数据无标注,向后兼容;调用方据 None 跳过该章)。"""
    if isinstance(outline_text_or_beats, list):
        text = "\n".join(
            (b.get("text") if isinstance(b, dict) else str(b)) or ""
            for b in outline_text_or_beats)
    else:
        text = outline_text_or_beats or ""
    role_m = _CHAPTER_ROLE_RE.search(text)
    pressure_m = _PRESSURE_RE.search(text)
    if not role_m and not pressure_m:
        return None
    out: dict = {}
    if role_m:
        out["role"] = role_m.group(1)
    if pressure_m:
        out["pressure"] = int(pressure_m.group(1))
    return out


def find_tension_monotony(chapters_meta: list[dict]) -> list[dict]:
    """卷级张弛基线:全书章级 {seq, role, pressure} 序列上检测两类单调性问题。

    ①role_run:同一 chapter_role 连续出现 >3 章(oh-story 铁律"同情绪母题别连超2-3章")
      → {"kind":"role_run","role":…,"seqs":[本次连排全部 seq]}。
    ②pressure_flat:滑窗 _TENSION_WINDOW(6)章内 pressure 全 ≥4 或全 ≤2
      → {"kind":"pressure_flat","window":[窗口内各 seq]}(均衡基线非硬配额,严肃志怪取克制档,
      但长期一路高压或一路低压都是失衡)。
    缺 role/pressure 字段的章跳过(向后兼容)——不参与对应那一类检测,也不打断另一类的连续性
    判定(role_run 只看有 role 的章按序连续,pressure_flat 同理)。"""
    issues: list[dict] = []

    # ① 同 role 连续 >3 章(按 seq 排序后,忽略缺 role 的章)
    role_entries = sorted((m for m in chapters_meta if m.get("role")), key=lambda m: m["seq"])
    run_role, run_seqs = None, []
    for m in role_entries:
        if m["role"] == run_role:
            run_seqs.append(m["seq"])
        else:
            if run_role is not None and len(run_seqs) > 3:
                issues.append({"kind": "role_run", "role": run_role, "seqs": list(run_seqs)})
            run_role, run_seqs = m["role"], [m["seq"]]
    if run_role is not None and len(run_seqs) > 3:
        issues.append({"kind": "role_run", "role": run_role, "seqs": list(run_seqs)})

    # ② 滑窗 6 章内 pressure 全 ≥4 或全 ≤2(按 seq 排序后,忽略缺 pressure 的章)
    pressure_entries = sorted((m for m in chapters_meta if m.get("pressure") is not None),
                              key=lambda m: m["seq"])
    seen_windows: set[tuple] = set()
    for i in range(len(pressure_entries) - _TENSION_WINDOW + 1):
        window = pressure_entries[i:i + _TENSION_WINDOW]
        pressures = [w["pressure"] for w in window]
        if all(p >= 4 for p in pressures) or all(p <= 2 for p in pressures):
            window_seqs = tuple(w["seq"] for w in window)
            if window_seqs not in seen_windows:
                seen_windows.add(window_seqs)
                issues.append({"kind": "pressure_flat", "window": list(window_seqs)})
    return issues


def motif_directives(
    motifs: list[dict],
    touched: list[dict] | None = None,
    *,
    next_chapter: int | None = None,
    touch_map: dict | None = None,
) -> dict:
    """章前母题段:heat 调度 must_echo/avoid_overuse + 可编织清单 + 上章触及。

    真源:scribe3.motif_craft.motif_schedule_directives(非固定 top-5 全表 dump)。
    next_chapter/touch_map 缺省时退化为无 heat 的编织列表(兼容旧单测)。
    """
    from scribe3.motif_craft import motif_schedule_directives, parse_echo_terms
    if next_chapter is not None:
        return motif_schedule_directives(
            motifs or [], touch_map or {}, int(next_chapter), touched=touched)
    # 无调度上下文:仅列清单(旧路径)
    lines: list[str] = []
    for m in (motifs or [])[:5]:
        name = (m.get("name") or "").replace("\n", " ").strip()
        if not name:
            continue
        theme = (m.get("theme") or "").replace("\n", " ").strip()
        terms = parse_echo_terms(m.get("echoes"), m.get("echo_terms"))
        echoes = "/".join(terms) if terms else (m.get("echoes") or "").replace("\n", " ").strip()
        entry = name
        if theme:
            entry += f"：{theme}"
        if echoes:
            entry += f"（回声:{echoes}）"
        lines.append(entry)
    touched_lines: list[str] = []
    for it in touched or []:
        n = (it.get("name") or it.get("motif_id") or "").replace("\n", " ").strip()
        if not n:
            continue
        e = (it.get("evidence") or "").replace("\n", " ").strip()
        touched_lines.append(f"{n}" + (f"「{e}」" if e else ""))
    return {
        "lines": lines, "touched": touched_lines, "count": len(lines),
        "must_echo": [], "avoid_overuse": [],
    }


def render_brief(sections: dict) -> str:
    parts = ["## 本章创作简报(章前组装,遵守但不复述)"]
    pu = sections.get("purpose") or {}
    if pu.get("text"):   # 北极星任务6:目的合同必达清单+滚入(空 delta 章不渲染)
        parts.append(pu["text"])
    parts += list(sections.get("arcs") or [])
    pd = sections.get("promises") or {}
    if pd.get("directives"):
        parts.append("【伏笔·本章指令】\n" + "\n".join(f"- {x}" for x in pd["directives"]))
    if pd.get("decisions"):
        parts.append("【伏笔·待作者决策(阻塞级)】\n" + "\n".join(f"- {x}" for x in pd["decisions"]))
    if pd.get("reminders"):
        parts.append("【伏笔·在窗提醒】" + "；".join(pd["reminders"]))
    mo = sections.get("motifs") or {}
    if mo.get("must_echo"):
        parts.append("【母题·该回声 must_echo】\n" + "\n".join(f"- {x}" for x in mo["must_echo"]))
    if mo.get("avoid_overuse"):
        parts.append("【母题·过热避免连刷 avoid_overuse】\n"
                     + "\n".join(f"- {x}" for x in mo["avoid_overuse"]))
    if mo.get("lines"):
        parts.append("【贯穿母题·可主动编织】\n" + "\n".join(f"- {x}" for x in mo["lines"]))
    if mo.get("touched"):
        parts.append("【上章触及母题】" + "；".join(mo["touched"]))
    ca = sections.get("causal") or {}
    if ca.get("directives"):   # 北极星任务2:no_event_data/零违规 → directives 空 → 段不渲染
        note = (f"(另有 {ca['overflow']} 条欠账只落面板,未进简报)"
                if ca.get("overflow") else "")
        parts.append("【因果欠账·三选一】" + note + "\n"
                     + "\n".join(f"- {x}" for x in ca["directives"]))
    led = sections.get("loops")
    if led and led.get("weighted"):   # Task7-B④:weighted==0 不渲染(零开环无须提醒)
        warn = "——已超上限:先收一条再开新坑" if led["over_cap"] else ""
        parts.append(f"【开环账本】加权开环 {led['weighted']}/{led['cap']}{warn}")
    hb = sections.get("heartbeat") or []
    if hb:
        items = "；".join(f"{h['name']}(上次第{h['last_active']}章,其日程:{h['agenda']})" for h in hb)
        parts.append(f"【待激活角色】{items}——本章至少让其日程推进一步或被提及")
    stale = sections.get("stale") or {}
    if stale.get("text"):
        parts.append(stale["text"])
    em = sections.get("emotion_module") or {}
    if em.get("text"):
        parts.append(em["text"])
    ls = sections.get("lessons") or {}
    if ls.get("text"):   # 北极星任务8:复盘要点(软指令,空则不渲染)
        parts.append(ls["text"])
    return "\n\n".join(parts)


def assemble_chapter_brief(st, seq: int, focalizer: str = "", target_emotion: str = "") -> dict:
    """连 store 的薄壳:收集数据 → 各纯函数 → {sections, text}。seq 为即将写的章号。

    focalizer(Task7-B③ 预留,当前不参与组装):为后续限知章过滤预留——P1 可按焦点者
    知识帧过滤伏笔/弧光条目(避免向限知写作 prompt 泄露焦点者不知道的线索)。
    P0 不做:简报是给"作者视角"的创作指令,非角色知识;YAGNI,先不叠过滤。

    target_emotion(方案B任务15):可选目标情绪,默认空串不触发 EM/RH/TR 情绪模块卡召回。
    当前 assemble_chapter_brief 现有数据源(章 meta/beats)里没有现成的"目标情绪"字段,
    故留为显式可选参数——接线点留给写作端点:调用方从大纲/节拍的情绪标注(如有)或
    作者手动指定中取值后传入。"""
    from scribe3 import arc_signals as AS

    next_ch = seq
    max_ch = max(0, seq - 1)
    rows = st.promises_with_lifecycle(max_chapter=max_ch)
    arcs = []
    chars_hb = []

    # 作品级静音：不注入弧光指令/冷启动（仍组其余简报段）
    _tracking_off = False
    try:
        if hasattr(st, "get_intent") and AS.is_arc_tracking_off(st.get_intent()):
            _tracking_off = True
        else:
            from scribe3 import settings_store
            work = str(getattr(st, "db_name", None) or getattr(st, "db", None) or "main")
            if AS.is_arc_tracking_off(settings_store.get_override(f"arc_tracking:{work}")):
                _tracking_off = True
    except Exception:
        _tracking_off = False

    # 多源 last_active：char_state / relation_touch / involved_characters
    last_by_cid: dict[str, int] = {}
    try:
        for c in st.characters():
            states = st.list_char_states(c.id) or []
            if states:
                last_by_cid[c.id] = max(int(s.get("chapter") or 0) for s in states)
    except Exception as e:
        _log.debug("assemble last_active char_state: %s", e)
    try:
        for t in st.list_relation_touches() or []:
            ch = int(t.get("chapter") or 0)
            for key in ("a", "b"):
                cid = t.get(key)
                if cid:
                    last_by_cid[cid] = max(last_by_cid.get(cid, 0), ch)
    except Exception as e:
        _log.debug("assemble last_active relation_touch: %s", e)
    try:
        for ch_row in (st.chapters_lite() if hasattr(st, "chapters_lite") else []) or []:
            ch_seq = int(ch_row.get("seq") or 0)
            inv = ch_row.get("involved_characters") or []
            if not inv and hasattr(st, "get_chapter"):
                full = st.get_chapter(ch_seq) or {}
                inv = full.get("involved_characters") or []
            for ent in inv:
                if isinstance(ent, dict):
                    cid = ent.get("character_id") or ent.get("id") or ""
                else:
                    cid = str(ent or "")
                if cid:
                    if not str(cid).startswith("role:"):
                        cid = f"role:{cid}" if ":" not in str(cid) else str(cid)
                    last_by_cid[cid] = max(last_by_cid.get(cid, 0), ch_seq)
    except Exception as e:
        _log.debug("assemble last_active involved: %s", e)

    for c in st.characters():
        a = st.char_anchors(c.id)
        last_active = last_by_cid.get(c.id)
        chars_hb.append({"id": c.id, "name": c.name,
                         "private_agenda": a.get("private_agenda"),
                         "last_active": last_active})
        if _tracking_off:
            continue
        # 冷启动：主档无 lie
        if not (a.get("lie") or "").strip():
            if AS.is_main_cast_importance(
                    (c.traits or {}).get("importance") if isinstance(getattr(c, "traits", None), dict)
                    else None):
                arcs.append(AS.format_cold_start_decision(c.name, tools=True))
            continue
        plan = st.list_arc_plan(c.id) or []
        belief = st.latest_lie_belief(c.id, max_ch)
        focus = AS.arc_beat_focus(
            plan, belief=belief, next_ch=next_ch,
            arc_type=a.get("arc_type"), slack=AS.ARC_BELIEF_SLACK)
        line = arc_directive(c.name, a, plan, belief, next_ch)
        if focus and (focus.get("status") or "") in ("overdue_miss", "overdue_unmeasured"):
            line = line + "\n⚠ " + AS.format_beat_decision(c.name, focus, tools=True)
        arcs.append(line)
    if _tracking_off:
        arcs = [AS.tracking_off_message()]
    # 方案B任务12:连续性 heat/last_touch 状态机——char/promise/relation 三维度取数汇总,
    # 逐维度 fail-soft:任一维度取不到数据就跳过该维度,不影响其余维度与整体简报组装。
    stale_rows: list[dict] = []
    try:
        for c in chars_hb:
            if c.get("last_active") is not None:
                stale_rows.append({"name": c["name"], "kind": "char",
                                   "last_touch": c["last_active"]})
    except Exception as e:
        _log.debug("assemble_chapter_brief stale_rows(char) 失败: %s", e)
    try:
        for p in rows:
            if p.get("status") != "open":   # 只对仍开着的支线/伏笔催回顾,已收线的不必
                continue
            last_touch = p.get("last_refresh_at")
            if last_touch is None:
                last_touch = p.get("setup_chapter")
            stale_rows.append({"name": (p.get("text") or "")[:20], "kind": "promise",
                               "last_touch": last_touch})
    except Exception as e:
        _log.debug("assemble_chapter_brief stale_rows(promise) 失败: %s", e)
    try:
        by_pair: dict[tuple, int] = {}
        for t in st.list_relation_touches() or []:
            pair = tuple(sorted([t.get("a") or "", t.get("b") or ""]))
            ch = t.get("chapter") or 0
            by_pair[pair] = max(by_pair.get(pair, ch), ch)
        for (pa, pb), ch in by_pair.items():
            stale_rows.append({"name": f"{pa}↔{pb}", "kind": "relation", "last_touch": ch})
    except Exception as e:
        _log.debug("assemble_chapter_brief stale_rows(relation) 失败: %s", e)
    # 母题真源:list_motifs + motif_touch_map → heat 调度(must_echo/avoid_overuse)
    # + 上章触及;与写作注入 _codex_block(for_generation) 同源 motif_craft 调度。
    motif_sec = {"lines": [], "touched": [], "count": 0, "must_echo": [], "avoid_overuse": []}
    try:
        motif_rows = st.list_motifs() if hasattr(st, "list_motifs") else []
        prev_inst = []
        if max_ch and hasattr(st, "list_motif_instances"):
            prev_inst = st.list_motif_instances(max_ch) or []
        tmap = st.motif_touch_map() if hasattr(st, "motif_touch_map") else {}
        motif_sec = motif_directives(
            motif_rows or [], prev_inst, next_chapter=next_ch, touch_map=tmap)
    except Exception as e:
        _log.debug("assemble_chapter_brief motifs 失败: %s", e)
    sections = {
        "arcs": arcs,
        "promises": promise_directives(rows),
        "motifs": motif_sec,
        "loops": open_loop_ledger(rows),
        "heartbeat": heartbeat_list(chars_hb, next_ch),
        "stale": stale_entity_directives(stale_rows, next_ch),
    }
    # 北极星任务6:目的合同注入——本章必达清单 + 上章未达成滚入(与因果催收同渠道
    # 语气);fail-soft:目的数据故障不拖垮简报其余部分。
    try:
        from scribe3.purpose import parse_deltas, render_purpose_section
        _cur = parse_deltas((st.get_chapter(seq) or {}).get("deltas"))
        _prev = parse_deltas((st.get_chapter(max_ch) or {}).get("deltas")) if max_ch else []
        # P1门审查 P2-1:剔除已滚入本章合同的副本——否则同一 delta 双渲染
        # (「第N章滚入」+「第N章起未达成」两行),量控自伤+prompt 重复施压。
        _cur_keys = {(d.get("kind"), d.get("predicate")) for d in _cur}
        sections["purpose"] = render_purpose_section(
            _cur, [d for d in _prev if d.get("status") == "carried"
                   and (d.get("kind"), d.get("predicate")) not in _cur_keys])
    except Exception as e:
        _log.warning("assemble_chapter_brief purpose 段组装失败(fail-soft): %s", e)
        sections["purpose"] = {"text": "", "count": 0}
    # 北极星任务8:上章复盘要点+历史教训语义召回(沉淀环反哺边①,软指令);
    # 召回 query=本章大纲/节拍(按语境召回,CIPHER/AutoGuide 先例),k=3+相似度
    # 下限(宁缺勿滥);fail-soft:lesson 数据故障不拖垮简报。
    try:
        from scribe3.lesson import render_lessons_section
        _last_ls = (st.list_lessons(chapter=max_ch) if max_ch else [])[-3:]   # 取最新3条(P3:最老3条会让新纠偏永不注入)
        _ch_meta = st.get_chapter(seq) or {}
        _qtxt = " ".join(filter(None, [
            (_ch_meta.get("synopsis") or "").strip(),
            " ".join(((b.get("text") if isinstance(b, dict) else str(b)) or "")
                     for b in (_ch_meta.get("beats") or []))])).strip()
        _recalled = st.recall_lessons(_qtxt, k=3) if _qtxt else []
        _seen_ids = {l.get("id") for l in _last_ls}
        _recalled = [r for r in _recalled if r.get("id") not in _seen_ids]
        sections["lessons"] = render_lessons_section(_last_ls, _recalled)
    except Exception as e:
        _log.warning("assemble_chapter_brief lessons 段组装失败(fail-soft): %s", e)
        sections["lessons"] = {"text": "", "count": 0}
    # 北极星任务2:因果欠账催收——近 _CAUSAL_LOOKBACK 章倒序收集 causal_complete 违规,
    # top-5 转译三选一软指令;全窗口无事件→no_event_data 整段不渲染;取数 fail-soft
    # (causal 数据故障不拖垮简报其余部分,警告级日志,不假绿吞错)。
    try:
        from scribe3.verify import causal_complete
        viols: list[dict] = []
        any_events = False
        for ch in range(max_ch, max(0, max_ch - _CAUSAL_LOOKBACK), -1):
            if not st.events_at(ch):
                continue
            any_events = True
            for v in causal_complete(st, ch):
                viols.append({"chapter": ch, "event_id": v.event_id, "reason": v.reason})
        sections["causal"] = causal_directives(viols, no_event_data=not any_events)
    except Exception as e:
        _log.warning("assemble_chapter_brief causal 段组装失败(fail-soft 跳过): %s", e)
        sections["causal"] = {"directives": [], "overflow": 0, "total": 0}
    # Task8:M6 设定注入清单回显(与 _editor_system 全知分支同源 assemble_injection)
    # U-011(2026-07-15,作者要 fail-loud):删掉"注入异常复用 fallback=True"——
    # fallback=True 的合法语义是"本书从未配置 injection_mode"(assemble_injection
    # 内部已实现的正常业务分支,向后兼容);把真崩溃也标成 fallback=True 会让"系统
    # 故障"和"没配置"在响应里长得一模一样,作者无从分辨。查询/组装失败现在直接上抛。
    inj = assemble_injection(st, seq)
    sections["injection"] = {
        "chosen": [{"id": i.get("id"), "text": (i.get("text") or "")[:80]}
                   for i in inj["chosen"]],
        "dropped": inj["dropped"],
        "fallback": inj["fallback"],
    }
    # 方案B任务15:EM/RH/TR 情绪模式库——有 target_emotion 才召回。
    # U-011(2026-07-15,作者要 fail-loud):删掉"素材库故障静默转空"——召回失败必须
    # 让作者看见,不能悄悄变成"这轮没有情绪模块卡"(与真没有无区别)。
    mats = st.list_materials(kind="emotion_module") if target_emotion else []
    sections["emotion_module"] = emotion_module_recall(mats, target_emotion)
    return {"sections": sections, "text": render_brief(sections)}

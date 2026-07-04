"""章前组装器:把弧光/伏笔/开环/心跳组装成「本章创作简报」,注入写作 system prompt。
设计:设计文档/2026-07-03-工艺引擎强化-design.md 第二节。
纯函数生成各 section(可测不连库);assemble_chapter_brief 是唯一连 store 的薄壳。"""
from __future__ import annotations

import json
import re

_TIER_W = {"book": 3, "arc": 2, "chapter": 1}
_SALIENCE_GAP_MAX = 3   # 距上次露面超过此章数 → 兑现前先刷新
_LOOP_CAP = 12          # 开环加权上限
_M6_BUDGET_CHARS = 1200  # M6 设定注入字符预算(全知分支;超出按 always优先/priority 降序裁)


def arc_directive(name: str, anchors: dict, arc_plan: list[dict],
                  lie_belief: int | None, next_ch: int) -> str:
    """单角色弧光三行指令:当前值 + 当前拍→下一拍 + 禁止事项。
    Task7-B①:done 判定严格 <(target_chapter == next_ch 属"本章应到达该拍",
    该拍进"下一拍"指令,不得提前算已完成)。"""
    name = (name or "").replace("\n", " ")   # Task8审查:name 也补齐换行清洗
    lie = (anchors.get("lie") or "—").replace("\n", " ")   # Task7-B②:防多行伪造 section 头
    at = (anchors.get("arc_type") or "—").replace("\n", " ")   # Task8:与 lie/promise/agenda 拉齐清洗
    done = [b for b in arc_plan if b["target_chapter"] < next_ch]
    ahead = [b for b in arc_plan if b["target_chapter"] >= next_ch]
    cur = (done[-1]["beat_name"] if done else "开场常态").replace("\n", " ")   # Task8:beat_name 清洗
    nxt = (f"{(ahead[0]['beat_name'] or '').replace(chr(10), ' ')}(目标第{ahead[0]['target_chapter']}章"
           + (f",信奉度趋 {ahead[0]['lie_belief_target']}" if ahead[0].get("lie_belief_target") is not None else "")
           + ")") if ahead else "终局"
    cur_v = f"{lie_belief}" if lie_belief is not None else "未测"
    return (f"【角色弧光·{name}】弧型:{at} | 信念(Lie):「{lie}」\n"
            f"当前信奉度:{cur_v};所处节拍:{cur} → 下一拍:{nxt}\n"
            f"本章指令:朝下一拍缓移,位移须由本章事件背书。"
            f"禁止:一步顿悟、借台词明说信念、跳到终局姿态。")


def promise_directives(rows: list[dict]) -> dict:
    """按窗口态分流:in_window→软提醒;over_half→简报指令(salience 低则先刷新);
    overdue→三选一决策。返回 {reminders, directives, decisions}(均为文案列表)。"""
    reminders, directives, decisions = [], [], []
    for p in rows:
        w = p.get("window") or {}
        state, gap = w.get("state"), w.get("salience_gap") or 0
        text = (p.get("text") or "").replace("\n", " ")[:40]   # Task7-B②:清洗换行
        if state == "in_window":
            reminders.append(f"「{text}」在兑现窗口内,适时推进")
        elif state == "over_half":
            if gap > _SALIENCE_GAP_MAX:
                directives.append(
                    f"伏笔「{text}」已过窗口一半且久未露面({gap}章):本章先安排一次"
                    f"不动声色的刷新(换伪装:道具/闲笔/情绪),为兑现蓄势——先刷新,勿直接兑现")
            else:
                directives.append(f"伏笔「{text}」已过窗口一半:本章应实质推进或兑现")
        elif state == "overdue":
            decisions.append(
                f"伏笔「{text}」已超兑现窗口:请作者三选一——立即兑现 / 显式展期(改窗口) / "
                f"降级弃置(abandoned)。系统默认本章简报持续携带此项直到决策。")
    return {"reminders": reminders, "directives": directives, "decisions": decisions}


def open_loop_ledger(rows: list[dict], cap: int = _LOOP_CAP) -> dict:
    """开环账本:tier 加权计数(book×3/arc×2/chapter×1),只计窗口态非 inactive 的 open 线。"""
    weighted = sum(_TIER_W.get(p.get("tier") or "chapter", 1)
                   for p in rows if (p.get("window") or {}).get("state") not in (None, "inactive"))
    return {"weighted": weighted, "cap": cap, "over_cap": weighted > cap}


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
    """待激活名单:有 private_agenda 且距上次活跃超过 gap 章的角色。"""
    out = []
    for c in chars:
        agenda = (c.get("private_agenda") or "").replace("\n", " ").strip()   # Task7-B②
        last = c.get("last_active")
        if not agenda or last is None:
            continue
        if next_ch - last > gap:
            out.append({"name": (c["name"] or "").replace("\n", " "),   # Task8审查:name 清洗
                        "agenda": agenda, "last_active": last})
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
    facts = st.facts_at(99999)
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


def render_brief(sections: dict) -> str:
    parts = ["## 本章创作简报(章前组装,遵守但不复述)"]
    parts += list(sections.get("arcs") or [])
    pd = sections.get("promises") or {}
    if pd.get("directives"):
        parts.append("【伏笔·本章指令】\n" + "\n".join(f"- {x}" for x in pd["directives"]))
    if pd.get("decisions"):
        parts.append("【伏笔·待作者决策(阻塞级)】\n" + "\n".join(f"- {x}" for x in pd["decisions"]))
    if pd.get("reminders"):
        parts.append("【伏笔·在窗提醒】" + "；".join(pd["reminders"]))
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
    next_ch = seq
    max_ch = max(0, seq - 1)
    rows = st.promises_with_lifecycle(max_chapter=max_ch)
    arcs = []
    chars_hb = []
    for c in st.characters():
        a = st.char_anchors(c.id)
        states = st.list_char_states(c.id)
        # 留档(Task6跟进③):last_active 用 char_state 最大章是近似——露面但无弧光变化
        # 不刷新;从未有 char_state 的有日程角色永不入待激活名单。若后续有真实露面源
        # (如章 involved_characters)可替换;P1 再改。
        last_active = max((s.get("chapter") or 0) for s in states) if states else None
        chars_hb.append({"id": c.id, "name": c.name,
                         "private_agenda": a.get("private_agenda"),
                         "last_active": last_active})
        if a.get("lie"):
            arcs.append(arc_directive(c.name, a, st.list_arc_plan(c.id),
                                      st.latest_lie_belief(c.id, max_ch), next_ch))
    # 方案B任务12:连续性 heat/last_touch 状态机——char/promise/relation 三维度取数汇总,
    # 逐维度 fail-soft:任一维度取不到数据就跳过该维度,不影响其余维度与整体简报组装。
    stale_rows: list[dict] = []
    try:
        for c in chars_hb:
            if c.get("last_active") is not None:
                stale_rows.append({"name": c["name"], "kind": "char",
                                   "last_touch": c["last_active"]})
    except Exception:
        pass
    try:
        for p in rows:
            if p.get("status") != "open":   # 只对仍开着的支线/伏笔催回顾,已收线的不必
                continue
            last_touch = p.get("last_refresh_at")
            if last_touch is None:
                last_touch = p.get("setup_chapter")
            stale_rows.append({"name": (p.get("text") or "")[:20], "kind": "promise",
                               "last_touch": last_touch})
    except Exception:
        pass
    try:
        by_pair: dict[tuple, int] = {}
        for t in st.list_relation_touches() or []:
            pair = tuple(sorted([t.get("a") or "", t.get("b") or ""]))
            ch = t.get("chapter") or 0
            by_pair[pair] = max(by_pair.get(pair, ch), ch)
        for (pa, pb), ch in by_pair.items():
            stale_rows.append({"name": f"{pa}↔{pb}", "kind": "relation", "last_touch": ch})
    except Exception:
        pass
    sections = {
        "arcs": arcs,
        "promises": promise_directives(rows),
        "loops": open_loop_ledger(rows),
        "heartbeat": heartbeat_list(chars_hb, next_ch),
        "stale": stale_entity_directives(stale_rows, next_ch),
    }
    # Task8:M6 设定注入清单回显(与 _editor_system 全知分支同源 assemble_injection)
    try:
        inj = assemble_injection(st, seq)
        sections["injection"] = {
            "chosen": [{"id": i.get("id"), "text": (i.get("text") or "")[:80]}
                       for i in inj["chosen"]],
            "dropped": inj["dropped"],
            "fallback": inj["fallback"],
        }
    except Exception:
        sections["injection"] = {"chosen": [], "dropped": 0, "fallback": True}
    # 方案B任务15:EM/RH/TR 情绪模式库——有 target_emotion 才召回,取数 fail-soft
    # (素材库故障不应影响简报其余部分组装)。
    try:
        mats = st.list_materials(kind="emotion_module") if target_emotion else []
        sections["emotion_module"] = emotion_module_recall(mats, target_emotion)
    except Exception:
        sections["emotion_module"] = {"text": "", "items": []}
    return {"sections": sections, "text": render_brief(sections)}

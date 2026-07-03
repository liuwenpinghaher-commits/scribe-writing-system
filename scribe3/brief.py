"""章前组装器:把弧光/伏笔/开环/心跳组装成「本章创作简报」,注入写作 system prompt。
设计:设计文档/2026-07-03-工艺引擎强化-design.md 第二节。
纯函数生成各 section(可测不连库);assemble_chapter_brief 是唯一连 store 的薄壳。"""
from __future__ import annotations

_TIER_W = {"book": 3, "arc": 2, "chapter": 1}
_SALIENCE_GAP_MAX = 3   # 距上次露面超过此章数 → 兑现前先刷新
_LOOP_CAP = 12          # 开环加权上限
_M6_BUDGET_CHARS = 1200  # M6 设定注入字符预算(全知分支;超出按 always优先/priority 降序裁)


def arc_directive(name: str, anchors: dict, arc_plan: list[dict],
                  lie_belief: int | None, next_ch: int) -> str:
    """单角色弧光三行指令:当前值 + 当前拍→下一拍 + 禁止事项。
    Task7-B①:done 判定严格 <(target_chapter == next_ch 属"本章应到达该拍",
    该拍进"下一拍"指令,不得提前算已完成)。"""
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


def heartbeat_list(chars: list[dict], next_ch: int, gap: int = 3) -> list[dict]:
    """待激活名单:有 private_agenda 且距上次活跃超过 gap 章的角色。"""
    out = []
    for c in chars:
        agenda = (c.get("private_agenda") or "").replace("\n", " ").strip()   # Task7-B②
        last = c.get("last_active")
        if not agenda or last is None:
            continue
        if next_ch - last > gap:
            out.append({"name": c["name"], "agenda": agenda, "last_active": last})
    return out


# ===== Task 8 · M6 设定三态注入(纯函数)=====

def detect_mentions(text: str, entities: list[dict]) -> set[str]:
    """本章草料文本(synopsis+beats+演绎)中按 名字/别名 包含匹配命中的实体 id 集。"""
    hit = set()
    t = text or ""
    for e in entities:
        names = [e.get("name") or ""] + list(e.get("aliases") or [])
        if any(n and n in t for n in names):
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
    fallback=True:全部 facts 无 injection_mode 且无任何命中 → 调用方回退旧 facts[:28] 防零注入。
    注意:限知(focalizer 非空)分支不走此——先限知过滤是正确性,P0 不叠相关性过滤。"""
    facts = st.facts_at(99999)
    ch = st.get_chapter(seq) if seq is not None else None
    draft = chapter_draft_text(ch)
    entities = [{"id": e.id, "name": e.name,
                 "aliases": (getattr(e, "traits", None) or {}).get("aliases") or []}
                for e in st.all_entities()]
    mentioned = detect_mentions(draft, entities)
    items, any_mode = [], False
    for f in facts:
        mode = getattr(f, "injection_mode", None)
        if mode:
            any_mode = True
        items.append({"id": getattr(f, "id", None), "entity": getattr(f, "entity_id", ""),
                      "text": _fact_inject_line(f), "mode": mode or "detected",
                      "priority": getattr(f, "priority", None)})
    sel = select_injection(items, mentioned, budget_chars)
    return {"chosen": sel["chosen"], "dropped": sel["dropped"],
            "used_chars": sel["used_chars"],
            "fallback": (not sel["chosen"]) and (not any_mode), "facts": facts}


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
    return "\n\n".join(parts)


def assemble_chapter_brief(st, seq: int, focalizer: str = "") -> dict:
    """连 store 的薄壳:收集数据 → 各纯函数 → {sections, text}。seq 为即将写的章号。

    focalizer(Task7-B③ 预留,当前不参与组装):为后续限知章过滤预留——P1 可按焦点者
    知识帧过滤伏笔/弧光条目(避免向限知写作 prompt 泄露焦点者不知道的线索)。
    P0 不做:简报是给"作者视角"的创作指令,非角色知识;YAGNI,先不叠过滤。"""
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
    sections = {
        "arcs": arcs,
        "promises": promise_directives(rows),
        "loops": open_loop_ledger(rows),
        "heartbeat": heartbeat_list(chars_hb, next_ch),
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
    return {"sections": sections, "text": render_brief(sections)}

"""写作层(移植自 scribe_mcp 的质量核心,改读 SurrealDB):
确定性富上下文注入 —— 北极星/角色声音/设定/主线记忆/最近章梗概/上一章结尾/语义召回 + antislop 约束。
这是产出标杆质量的命门;生成调用本身在 generate.py(走 Hermes)。
"""
from __future__ import annotations

# 反 AI 腔/反趋均值的文学约束(自包含,不依赖旧 scribe_mcp)
CONSTRAINT_BLOCK = (
    "【文学约束·写作时必须遵守(反 AI 腔/反趋均值)】\n"
    "1. show 不 tell:用动作/感官/细节呈现情绪,禁止「他感到悲伤/愤怒/绝望」式直说。\n"
    "2. 克制:不写顿悟升华尾句、不写「总而言之/这一刻他明白了」;让画面收尾,把判断留给读者。\n"
    "3. 意外性:每段至少一处不落俗套——期望反转、代价放大、或信息不对称;拒绝可预测的顺滑。\n"
    "4. 具体优先:用专有的物、动作、数字,替代「一抹弧度/一丝寒意/五味杂陈」这类通用模板。\n"
    "5. 禁用清单(出现即视为失败):嘴角勾起一抹弧度、眼底闪过一丝、一股暖流涌上心头、"
    "命运的齿轮、空气仿佛凝固、千言万语化作、…般的存在、值得一提的是。\n"
    "6. 节奏:长短句交错,避免连续同构句;副词(缓缓/轻轻/微微)整段不超过 1 次。"
)


def constraint_block() -> str:
    return CONSTRAINT_BLOCK


def build_writing_context(d, work: str, seq: int) -> str:
    """组装写第 seq 章的富上下文(只用 < seq 的记忆,不剧透)。d 为 Domain。"""
    parts: list[str] = []
    intent = d.get_intent(work) or {}
    if intent.get("reader_feeling"):
        parts.append(f"【北极星】这本书要让读者感受到:{intent['reader_feeling']}")
    if intent.get("core_emotional_arc"):
        parts.append(f"【情感弧·全书走向】{intent['core_emotional_arc']}")
    if intent.get("red_lines"):
        parts.append("【红线·绝不可破】" + ";".join(intent["red_lines"]))

    # 相关性注入:只给本章相关角色(开着伏笔关联/近章点名),不再全塞,聚焦在场人物
    chars = d.relevant_characters(work, seq) if hasattr(d, "relevant_characters") else d.list_characters(work)
    if chars:
        def _c(c):
            mot = (c.get("motivation") or "").strip()
            base = f"{c['name']}({mot[:20]})" if mot else c.get("name", "")
            if (c.get("voice") or "").strip():
                base += f"〔声音:{c['voice'][:16]}〕"
            samples = [s for s in (c.get("voice_samples") or []) if s][:2]
            if samples:  # 声音样本=防 OOC 命门,每次写到该角色都给范本
                base += "〔样本:" + "/".join(s[:22] for s in samples) + "〕"
            if (c.get("core_contradiction") or "").strip():
                base += f"〔矛盾:{c['core_contradiction'][:28]}〕"
            # 内核 Truth-Chart:伤/谎/欲/需/惧 —— 驱动弧光,主编据此写人物的自欺与挣扎(乱世铜炉式人物深度)
            kern = [f"{lbl}:{(c.get(k) or '').strip()[:24]}" for k, lbl in
                    (("wound", "伤"), ("lie", "谎"), ("want", "欲"), ("need", "需"), ("fear", "惧"))
                    if (c.get(k) or "").strip()]
            if kern:
                base += "〔内核 " + " ".join(kern) + "〕"
            return base
        parts.append("【须保持一致的角色(声音/样本/矛盾不可漂移)】" + "；".join(_c(c) for c in chars[:15]))

    # Progressions 时间门:只注入 chapter_seq<=当前位置的最新角色状态(防剧透,乱世铜炉"信息延迟揭晓")
    if hasattr(d, "latest_char_states_upto"):
        states = d.latest_char_states_upto(work, seq)
        states = [s for s in states if (s.get("state_desc") or "").strip()]
        if states:
            parts.append("【人物当前状态·至本章为止(勿写出尚未发生的未来状态)】" + "；".join(
                f"{s.get('character','')}:{s['state_desc'][:40]}" for s in states[:15]))

    # 母题:核心意象的隐喻网,务必自然织入(乱世铜炉判据1)
    motifs = d.list_motifs(work) if hasattr(d, "list_motifs") else []
    if motifs:
        def _m(m):
            seg = [m.get("name", "")]
            if m.get("bound_theme"):
                seg.append("主题:" + m["bound_theme"][:40])
            if m.get("metaphor_unfolding"):
                seg.append("隐喻:" + m["metaphor_unfolding"][:50])
            echoes = [e for e in (m.get("material_echoes") or []) if e][:4]
            if echoes:
                seg.append("物质回声(可织入,勿生硬点题):" + "/".join(echoes))
            return "｜".join(seg)
        parts.append("【核心意象/母题(贯穿全书,自然织入)】\n" + "\n".join("· " + _m(m) for m in motifs[:4]))

    sets = d.list_settings(work)
    if sets:
        parts.append("【关键设定(不可矛盾)】" + ";".join(
            (s.get("text") or s.get("name") or "")[:30] for s in sets[:15]))
        # 力量体系:代价/限制/会出什么乱子,违背即穿帮(乱世铜炉判据2)
        powers = [s for s in sets if (s.get("type") == "力量体系") and (s.get("fields"))]
        if powers:
            def _p(s):
                f = s.get("fields") or {}
                bits = [s.get("name", "")]
                for k, lbl in (("cost", "代价"), ("limitations", "限制"), ("trouble_it_causes", "会出什么乱子")):
                    if f.get(k):
                        bits.append(f"{lbl}:" + str(f[k])[:40])
                return "｜".join(bits)
            parts.append("【规则·代价与限制(写到该力量时严格遵守)】\n" + "\n".join("· " + _p(s) for s in powers[:6]))

    # 伏笔·承诺线:① 本章该做的节点(带具体引导/效果)② 开着的承诺节奏总览 —— 引导主编"这章具体怎么写"
    all_f = d.list_foreshadows_status(work)
    open_f = [f for f in all_f if f.get("state") in ("planted", "triggered")]
    # ① 本章节点指令:落在本章±1、未完成的 beat,带 guidance + 局部效果 + 戏剧反讽框架
    _KIND = {"plant": "埋", "reinforce": "强化", "misdirect": "误导", "twist": "转折", "payoff": "回收"}
    todo = []
    for f in all_f:
        desc = f.get("promise") or f.get("summary") or ""
        for b in (f.get("beats") or []):
            if b.get("done") or abs((b.get("chapter") or 0) - seq) > 1:
                continue
            g = b.get("guidance") or "按计划处理"
            eff = b.get("effect") or (f.get("payoff_effect") if b.get("kind") == "payoff" else "")
            sub = f"·隐蔽度{b['subtlety']}" if b.get("subtlety") else ""
            irony = "｜读者已知、角色不知,写出戏剧反讽的煎熬" if f.get("audience_knows") and b.get("kind") == "payoff" else ""
            lk = f"〔涉及{'/'.join(f.get('links') or [])}〕" if f.get("links") else ""
            todo.append(f"· [{_KIND.get(b.get('kind'), '节点')}{sub}] {desc}{lk} → 本章:{g}{('｜效果:' + eff) if eff else ''}{irony}")
    if todo:
        parts.append("【本章承诺·节点指令(这是本章该埋/强化/回收的具体动作,照此处理)】\n" + "\n".join(todo[:8]))
    # ② 开着的承诺·节奏总览(适时推进/回收,勿堆砌勿遗忘)
    if open_f:
        def _f(f):
            plant = f.get("chapter") or 0
            echoes = f.get("echoes") or []
            last = max(echoes) if echoes else plant
            span, quiet = max(0, seq - plant), max(0, seq - last)
            if span >= 12 and quiet >= 8:
                tag = "(已开太久且久未提及 → 宜回收或强化)"
            elif span >= 6:
                tag = "(可考虑推进/回收)"
            else:
                tag = ""
            desc = f.get("promise") or f.get("summary") or ""
            eff = f"·求{f['intended_effect']}" if f.get("intended_effect") else ""
            lk = f"·涉及{'/'.join(f.get('links') or [])}" if f.get("links") else ""
            return f"· [{f.get('ftype') or '伏笔'}{eff}] {desc}(埋第{plant}章{lk}){tag}"
        open_f.sort(key=lambda f: f.get("chapter") or 0)   # 最久未动的最该照顾,排前
        parts.append(
            "【伏笔·承诺线·待回收(照顾节奏:适时埋钩子/推进/回收,勿一次性堆砌,勿让其凭空消失)】\n"
            + "\n".join(_f(f) for f in open_f[:8]))

    # 统一线模型:各实体本章节点指令(角色弧光/母题复现/设定逐章发展,把"伏笔节点指令"泛化到所有线)
    if hasattr(d, "list_entity_beats"):
        _ET = {"character": "角色", "motif": "母题", "setting": "设定", "place": "地点",
               "faction": "阵营", "item": "物品", "location": "地点"}
        eb = [b for b in d.list_entity_beats(work)
              if not b.get("done") and abs((b.get("chapter") or 0) - seq) <= 1]
        if eb:
            lines = []
            for b in eb:
                et = _ET.get(b.get("etype"), b.get("etype") or "线")
                g = b.get("guidance") or "按计划处理"
                eff = f"｜效果:{b['effect']}" if b.get("effect") else ""
                lines.append(f"· [{et}·{b.get('entity')}] 本章:{g}{eff}")
            parts.append("【本章·各线指令(角色弧光/母题复现/设定逐章发展,照此处理)】\n" + "\n".join(lines[:10]))
        # 各线健康:久未推进且未兑现的线 → 提醒适时复现/推进(别让角色弧光/母题凭空消失)
        if hasattr(d, "entity_lines_health"):
            stale = [h for h in d.entity_lines_health(work) if h.get("overdue")]
            if stale:
                ws = [f"· [{_ET.get(h.get('etype'), h.get('etype'))}·{h.get('entity')}] 自第{h.get('last_chapter')}章起久未推进且未兑现,适时复现/推进/收束"
                      for h in stale[:6]]
                parts.append("【线·久未推进告警】\n" + "\n".join(ws))

    glob = d.get_global_memory(work)
    if glob:
        parts.append("【全书主线记忆(至此为止)】" + glob[:400])

    recent = d.list_chapter_memories(work, upto=seq - 1)[-3:]
    if recent:
        parts.append("【最近章节梗概】\n" + "\n".join(
            f"第{m['seq']}章:{m['text']}" for m in recent))

    prev_tail = ""
    if seq > 1:
        prevch = next((c for c in d.list_chapters(work) if c.get("seq") == seq - 1), None)
        if prevch:
            content = d.latest_prose(d._idpart(prevch["id"]))
            if content.strip():
                prev_tail = content
                parts.append("【上一章结尾·需自然衔接】…" + content[-180:])

    # 语义召回:用上一章尾或北极星做 query,召回相关旧内容防久远冲突(best-effort)
    rq = (prev_tail[-200:] or intent.get("reader_feeling", "")).strip()
    if rq:
        try:
            hits = d.search(work, rq, k=3)
            recalled = [h.get("text", "") for h in hits
                        if h.get("text") and h.get("text")[:30] not in prev_tail]
            if recalled:
                parts.append("【相关前文·语义召回(保持一致,勿矛盾)】\n"
                             + "\n".join("· " + r[:120] for r in recalled[:3]))
        except Exception:
            pass

    parts.append(CONSTRAINT_BLOCK)
    return "\n".join(parts)

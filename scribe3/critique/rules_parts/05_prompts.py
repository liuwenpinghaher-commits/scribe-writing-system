# part 05_prompts (shared namespace; do not import standalone)
def build_discipline_prompt(text: str, brief: str = "", known: dict | None = None) -> str:
    kb = ""
    if known:
        lines = "\n".join(f"  · {who} 只知道:{('、'.join(facts[:8]) or '(仅其私密内核)')}"
                          for who, facts in known.items())
        kb = ("\n\n【各角色截至本章已知(判 knowledge_leak 的事实依据;角色说出此清单之外的他人私密=泄露)】\n"
              + lines)
    return (
        ANTI_SYCOPHANCY + "\n\n"
        "你是叙事结构【纪律判官】。下面是一章志怪小说。本章的命题/纪律要求:\n" +
        (brief or DEFAULT_DISCIPLINE_BRIEF) +
        "\n\n判定是否违反以下纪律(任一即违规):\n"
        "① double_climax:出现第二场打斗/救援/开挂,或偷跑了本不属于本章的后续剧情、凭空发明新登场角色;\n"
        "② voice_collapse:声细如蚊/半截就断的 terse 角色崩成大段流畅独白、系统结算音、或与主角同温;\n"
        "③ exposition_dump:大段身世/前史/规则的集中倾泻(本该零星渗出);\n"
        "④ knowledge_leak:某角色说出或表现出知晓【其视角不可能知道】的他人私密信息;\n"
        "⑤ god_view:只有叙述者断言焦点人物无法观察到的他人内心/秘密、未来结果，或替读者盖棺定论"
        "（如“谁都看得出他在撒谎”）才标记。感官描写、比喻、焦点人物的当下推断均不算 god_view；"
        "没有可逐字指出的全知断言就判守纪。\n"
        "若违规,找出正文里【复发/穿帮开始的前一句】(从这句之后整段都该砍掉),逐字填入 cut_after。\n"
        '只输出一行 JSON:{"ok": true/false, "violations": ["double_climax"...], "cut_after": "复发前最后一句的原文逐字,守纪则空"}。'
        + kb + "\n\n【正文】\n" + text)


def parse_discipline(reply: str) -> dict:
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            # 回复里连 JSON 都没有=同样是解析失败形态(fail-open 放行但计 degraded)
            _log.warning("parse_discipline 无 JSON,纪律默认放行 | reply[:120]=%r", (reply or "")[:120])
            return {"ok": True, "violations": [], "extra": [], "cut_after": "",
                    "parse_failed": True}
        d = json.loads(m.group(0))
        # 批次二(D-024 真机发现):生产 LLM 往 violations 混塞自由文本("未处理开放项:…"),
        # 与五类标签求交保序;其余进 extra 不丢(人可读,不参与共振/升格判定)。
        raw_v = [str(v) for v in (d.get("violations") or [])]
        return {"ok": bool(d.get("ok", True)),
                "violations": [v for v in raw_v if v in DISCIPLINE_KINDS],
                "extra": [v for v in raw_v if v not in DISCIPLINE_KINDS],
                "cut_after": (d.get("cut_after") or "").strip()}
    except Exception as e:
        _log.warning("parse_discipline 失败,纪律默认放行: %s | reply[:120]=%r", e, (reply or "")[:120])
        # 审计 E-2/#58:fail-open 保持(不误拦),但带 parse_failed 标记供上游计
        # degraded——此前解析失败只有日志,"没查"被静默当"没病"(纪律判假绿口)。
        return {"ok": True, "violations": [], "extra": [], "cut_after": "",
                "parse_failed": True}


def semantic_repair_gate(original: str, candidate: str, original_qc: dict, candidate_qc: dict,
                         original_leaks: list, candidate_leaks: list, discipline: dict) -> dict:
    """语义修复落库门：任何质量退化均拒绝候选，原稿由调用方保留。"""
    def total(flags: dict) -> int:
        return sum(len(v) if isinstance(v, (list, tuple, set)) else int(v or 0)
                   for v in (flags or {}).values())

    reasons = []
    if len(candidate or "") < len(original or "") * 0.85:
        reasons.append("length")
    if total(candidate_qc) > total(original_qc):
        reasons.append("quality")
    if len(candidate_leaks or []) > len(original_leaks or []):
        reasons.append("leaks")
    if discipline.get("degraded") or discipline.get("violations") or discipline.get("parse_failed"):
        reasons.append("discipline")
    return {"ok": not reasons, "reasons": reasons,
            "original_chars": len(original or ""), "candidate_chars": len(candidate or "")}


def build_voice_fold_prompt(current_profile: dict | None, flags: list[dict]) -> str:
    """构建声音演变折叠 prompt。
    current_profile: 当前 voice_profile dict(可为 None/空)。
    flags: list[{character, trigger_chapter, reason, id}]。
    要求 LLM 输出一行 JSON,至少含 style_summary;可含 tone_rules/catchphrases。
    """
    profile_str = "（尚无声音指纹,请从零建立）"
    if current_profile:
        parts = []
        if current_profile.get("style_summary"):
            parts.append(f"style_summary: {current_profile['style_summary']}")
        if current_profile.get("tone_rules"):
            parts.append(f"tone_rules: {current_profile['tone_rules']}")
        if current_profile.get("catchphrases"):
            parts.append(f"catchphrases: {current_profile['catchphrases']}")
        if parts:
            profile_str = "\n".join(parts)

    flag_lines = "\n".join(
        f"  · 第{f.get('trigger_chapter', '?')}章:{f.get('reason', '')}"
        for f in flags
    )

    return (
        "你是专业小说声音编辑。下面是某角色的当前声音指纹,以及情节驱动的声音演变信号。\n\n"
        "【当前声音指纹】\n" + profile_str + "\n\n"
        "【情节声音演变信号(需要折叠进声音指纹)】\n" + flag_lines + "\n\n"
        "请根据上述演变信号,输出一个**更新后**的声音指纹 JSON,反映角色经历这些情节后声音的演变。\n"
        "字段要求:style_summary(必填,一句话描述), tone_rules(选填,list), catchphrases(选填,list)。\n"
        "保持风格克制,不要为角色代写台词,只描述声音特征的变化。\n"
        '只输出一行 JSON,例如:{"style_summary":"...", "tone_rules":["..."], "catchphrases":["..."]}\n'
        "不要任何解释或额外文字。"
    )


def parse_voice_profile_from_fold(reply: str) -> dict | None:
    """解析 LLM 声音折叠回复。
    成功:返回含 style_summary 的 dict。
    失败(坏 JSON / 无 style_summary):返回 None(调用方据此 fail-soft,不改现有 profile)。
    """
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            _log.warning("parse_voice_profile_from_fold 无 JSON 块: reply[:120]=%r",
                         (reply or "")[:120])
            return None
        d = json.loads(m.group(0))
        if not d.get("style_summary"):
            _log.warning("parse_voice_profile_from_fold: 缺 style_summary,拒绝: %r", d)
            return None
        return d
    except Exception as e:
        _log.warning("parse_voice_profile_from_fold 失败: %s | reply[:120]=%r",
                     e, (reply or "")[:120])
        return None


def build_knowledge_extract_prompt(prose: str, motif_names: list[str] | None = None,
                                   promise_items: list[dict] | None = None,
                                   belief_chars: list[dict] | None = None,
                                   motif_echoes: dict | None = None) -> str:
    motif_seg = ""
    motif_schema = ""
    if motif_names:
        names = "、".join(motif_names)
        echo_line = ""
        if motif_echoes:
            bits = []
            for n, terms in motif_echoes.items():
                if terms:
                    bits.append(f"{n}还会以「{'、'.join(list(terms)[:8])}」回来")
            if bits:
                echo_line = "隐性回声也算触及：" + "；".join(bits) + "。"
        motif_seg = (
            f"再抽【motif:本章触及了以下【已立母题】中的哪些({names})——"
            f"{echo_line}"
            "只能从这些里选,严禁发明新母题;每条给母题名(motif)+本章一句体现它的引文(evidence);"
            "没触及则输出空列表】。\n")
        motif_schema = ',"motif":[{"motif":母题名,"evidence":引文}]'
    promise_seg = ""
    promise_schema = ""
    if promise_items:
        listing = "；".join(f"「{(p.get('text') or '')[:40]}」" for p in promise_items)
        promise_seg = (
            f"再抽【promise_touch:本章推进/呼应/兑现了以下【已埋伏笔】中的哪些({listing})——"
            "只能从这些里选,严禁发明;仅出现相近意象或字眼、并不指向该悬念的不算触及;"
            "每条给伏笔原文片段(text,须与上列某条逐字对应)"
            "+本章一句体现推进的引文(evidence);没触及则输出空列表】。\n")
        promise_schema = ',"promise_touch":[{"text":伏笔原文,"evidence":引文}]'
    belief_seg = ""
    belief_schema = ""
    if belief_chars:
        desc = "；".join(f"{c['name']}(其信念:「{c['lie']}」)" for c in belief_chars)
        belief_seg = (
            f"再抽【belief:下列角色本章结束时对各自核心错误信念的信奉度(0-100,{desc})——"
            "只评这些角色;每条给角色名(who)+信奉度(value)+一句依据(why);"
            "本章无相关表现的角色不输出】。\n")
        belief_schema = ',"belief":[{"who":角色名,"value":0到100整数,"why":依据}]'
    return (
        "读下面一章小说正文,抽取本章【各角色新知道了什么(learned)、做了什么且被谁看见(did)】——"
        "用于维护'谁知道什么'的知识账本(防后续章里某角色说出他视角不可能知道的信息)。"
        "再抽【voice_shift:哪些角色这章经历了可能改变其说话方式/声音的重大事件(创伤/背叛/重大转折/身份剧变)】——"
        "只列谁+什么事,不要替他写新独白。\n"
        "再抽【arc:哪些角色在本章经历了可量化的弧光质变——能力获得/丧失、重要关系建立/破裂、性格明显转折】——"
        "每条列:角色名(who)、变化类型(change_type:ability/relation/personality)、"
        "一句话摘要(summary)、快照(snapshot:对 ability 填{技能:状态}、"
        "对 relation 填{对象角色:关系描述}、对 personality 填字符串描述)。"
        "没有明确弧光质变时 arc 输出空列表。\n"
        "再抽【events:本章推动剧情的关键情节事件(动作/冲突/转折,通常 2-6 个)】——"
        "每条列:事件类型短标签(type,≤12字,如「对峙」「揭露」「立誓」)、"
        "参与者(participants:{SUBJ:主动方角色名, OBJ:受动方角色名, WITNESS:在场见证角色名};"
        "各槽只能填写具体人物姓名，器物、地点、刻字、自然现象和抽象事物不得填入；"
        "只填有的槽位,没有人物的槽位省略)、该事件为何发生的动机/目标(goal,一句话)、"
        "因果来由(caused_by:本章前面第几个事件直接导致了它,填其序号数组(从0起,只能指向本章更早的事件);"
        "本章第一个填空数组[]。若后续事件是切换人物/地点/时间后的独立场景根,caused_by 填[]并给"
        "causal_root_reason(明确写出为何另起场景链);其他后续事件不得空[])。"
        "按事件在本章的发生先后顺序输出;没有明确事件时 events 输出空列表。\n"
        + motif_seg + promise_seg + belief_seg +
        '只输出一行 JSON:{"learned":[{"who":角色名,"fact":新知道的事(短句)}],'
        '"did":[{"who":角色名,"action":所为(短句),"seen_by":[在场看见的角色名]}],'
        '"voice_shift":[{"who":角色名,"reason":重大事件(短句)}],'
        '"arc":[{"who":角色名,"change_type":"ability|relation|personality",'
        '"summary":一句话摘要,"snapshot":{...}}],'
        '"events":[{"type":类型标签,"participants":{"SUBJ":角色名,"OBJ":角色名,"WITNESS":角色名},'
        '"goal":动机目标,"caused_by":[前序事件序号],"causal_root_reason":独立场景理由(仅无前因时)}]'
        + motif_schema + promise_schema + belief_schema + '}。\n\n'
        "【正文】\n" + prose)


def parse_knowledge_delta(reply: str) -> dict | None:
    """解析 LLM 回复的知识 delta JSON。
    成功:返回 {"learned":..., "did":..., "voice_shift":..., "arc":...}(四字段均为 list)。
    arc 字段为可选——旧模型/旧响应不含该字段时默认空列表(向后兼容,不破坏现有调用)。
    失败(坏 JSON / 截断 / 无 {} 匹配):返回 None——调用方据此跳过 purge,防止数据丢失。"""
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            _log.warning("parse_knowledge_delta 无 JSON 块,知识不回写: reply[:120]=%r", (reply or "")[:120])
            return None
        d = json.loads(m.group(0))
        return {"learned": list(d.get("learned") or []), "did": list(d.get("did") or []),
                "voice_shift": list(d.get("voice_shift") or []),
                "arc": list(d.get("arc") or []),
                "motif": list(d.get("motif") or []),
                "promise_touch": list(d.get("promise_touch") or []),
                "belief": list(d.get("belief") or []),
                # 批D P1-5:事件抽取。旧模型/旧响应不含该字段时默认空列表(向后兼容)。
                "events": list(d.get("events") or [])}
    except Exception as e:
        _log.warning("parse_knowledge_delta 失败,知识不回写: %s | reply[:120]=%r", e, (reply or "")[:120])
        return None


def build_tension_rubric_prompt(prose: str) -> str:
    """张力盲评 prompt:戏剧问题/结局语法/价值反转/微张力荒漠/续读钩子/节奏失败模式,
    单次调用合并评审。

    方案B任务13新增两条节奏失败模式轴(oh-story emotional-methods.md 语义判定,
    LLM 通读判断,确定性正则判不了):
    - pacing_flat:   连续≥5节没有情绪转折即"太平"(读者会跳读)。
    - pacing_rushed: 转折前铺垫不足3节即"太赶"(反转没立住);或反转后交代解释
      超过2000字即"烂尾"(高潮后拖沓收不住)。
    """
    return (
        ANTI_SYCOPHANCY + "\n\n"
        "你是叙事张力评审。读下面一章小说正文,只输出一个 JSON(不要任何其他文字):\n"
        '{"dramatic_question":{"present":布尔,"answered_escalated":布尔,"note":一句},'
        '"outcomes":[{"scene":场景一句概括,"type":"yes"|"yes_but"|"no_and"|"no"}],'
        '"value_shift":{"present":布尔,"note":"哪个价值从什么极翻到什么极"},'
        '"micro_tension":{"deserts":[连续500字以上无POV情绪对立/念头交战的段落开头8字]},'
        '"hook":{"present":布尔,"type":"危险临近|信息截断|选择悬置|反转|不祥预示|无","strength":"strong"|"soft"},'
        '"pacing_flat":{"present":布尔,"note":一句},'
        '"pacing_rushed":{"present":布尔,"note":一句}}\n'
        "判定标准:dramatic_question=本章是否有一个悬着的小问题且章末被回答并升级;"
        "outcomes=各场景结局语法(顺利达成记 yes——它是泄气信号);"
        "value_shift=至少一场发生价值极性反转;hook=章末最后几行是否有续读钩子;"
        "pacing_flat=是否存在连续5节以上没有任何情绪转折(太平,读者会跳读);"
        "pacing_rushed=是否存在转折前铺垫不足3节就发生(太赶,反转立不住),"
        "或反转后交代解释超过2000字仍未收住(烂尾)。\n\n"
        f"正文:\n{prose}")


def parse_tension_report(raw: str) -> dict | None:
    """解析张力盲评 JSON。镜像 parse_knowledge_delta:提取首个 {...} 块,json.loads,失败返 None。
    坏 JSON / 截断 / 空 / None 一律 fail-safe 返回 None,调用方据此标 rubric_failed 不崩。"""
    try:
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            _log.warning("parse_tension_report 无 JSON 块: raw[:120]=%r", (raw or "")[:120])
            return None
        return json.loads(m.group(0))
    except Exception as e:
        _log.warning("parse_tension_report 失败: %s | raw[:120]=%r", e, (raw or "")[:120])
        return None


def build_reversal_rubric_prompt(prose: str, beat_meta: dict | None) -> str:
    """反转机检 rubric prompt(oh-story reversal-toolkit.md 7类反转)。

    beat_meta 无 reversal_type(空 dict / None)→ 本章未标注反转,不审,返回空串
    (镜像 _deduction_block/_outline_block 的"无内容即空串"约定)。
    beat_meta 含 reversal_type → 组装:7类枚举说明 + 本章反转声明(type/setup_clues/
    reveal_position_pct)+ 4 条机检轴 + 输出契约(与方案B任务18 normalize_findings 的
    FindingsSchema 六字段一致,供多 reviewer 结果统一合并)+ ANTI_SYCOPHANCY。

    悬念/伏笔边界(oh-story hooks-suspense.md):不建新表——短期悬念对应 promise
    账本里 tier:chapter(本章内起落即兑现的钩子),长期伏笔对应 tier:arc/book
    (跨章/跨卷才兑现);两账本语义分离,reversal 的 setup_clues 多数指向后者,
    评审时须按此区分对待,不得混为一谈。
    """
    if not beat_meta or not beat_meta.get("reversal_type"):
        return ""
    rtype = beat_meta.get("reversal_type")
    if rtype not in _REVERSAL_TYPES:
        # Minor(收尾清理批):reversal_type 拼写漂移仍照常生成 prompt——LLM 消费
        # 容忍拼写漂移(rtype 只作为展示文案拼进 prompt),这里只留日志线索供排查,
        # 不阻断评审流程。
        _log.warning("build_reversal_rubric_prompt 未知 reversal_type=%r,仅支持 %s",
                     rtype, _REVERSAL_TYPES)
    clues = beat_meta.get("setup_clues") or []
    pct = beat_meta.get("reveal_position_pct")
    types_list = "、".join(_REVERSAL_TYPES)
    clues_str = "；".join(str(c) for c in clues) if clues else "(未标注)"
    return (
        ANTI_SYCOPHANCY + "\n\n"
        "你是叙事反转机制评审。反转共 7 类(" + types_list + ")。\n"
        f"本章声明的反转:类型={rtype};铺垫线索(setup_clues)={clues_str};"
        f"揭示位置(reveal_position_pct)={pct}。\n"
        "悬念/伏笔边界:短期悬念(本章内起落的钩子)记 tier:chapter;长期伏笔"
        "(跨章/跨卷才兑现)记 tier:arc/book——两账本语义分离,本反转的铺垫属于哪一账本,"
        "评审时须区分对待,不得混为一谈。\n"
        "检查以下 4 项机检轴(任一命中即问题):\n"
        "① setup_insufficient:声明的铺垫线索(setup_clues)少于 3 处,或正文里找不到"
        "对应线索的真实着落;\n"
        "② reveal_overlong:揭示/交代反转真相的文字超过 300 字(该收在动作与留白,"
        "不该大段解说);\n"
        "③ unearned_new_info:揭示时引入了前文完全未出现过的新信息(伏笔没有真正埋过,"
        "反转是硬凭空冒出来的);\n"
        "④ position_out_of_range:揭示位置(reveal_position_pct)越出本章 50%-85% 的"
        "最佳区间(太早显得仓促无蓄力,太晚来不及消化)。\n"
        '只输出一行 JSON:{"findings":[{"severity":"S1"|"S2"|"S3"|"S4",'
        '"category":"structure"|"character"|"prose"|"consistency"|"platform"|'
        '"factual"|"format"|"causal"|"rule_boundary","location":定位,"evidence":引文,'
        '"issue":问题描述,"fix":修复建议}],"verdict":"APPROVE"|"CONCERNS"|"REJECT"}。\n\n'
        f"正文:\n{prose}")


def parse_reversal_report(raw: str) -> dict | None:
    """解析反转机检 JSON。镜像 parse_tension_report:提取首个 {...} 块,json.loads,
    坏 JSON / 截断 / 空 / None 一律 fail-safe 返回 None,调用方据此标 rubric_failed 不崩。"""
    try:
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            _log.warning("parse_reversal_report 无 JSON 块: raw[:120]=%r", (raw or "")[:120])
            return None
        return json.loads(m.group(0))
    except Exception as e:
        _log.warning("parse_reversal_report 失败: %s | raw[:120]=%r", e, (raw or "")[:120])
        return None


def build_platform_rubric_prompt(prose: str, platform: str) -> str:
    """平台留存轴 rubric prompt(oh-story rubrics/{qidian,fanqie,zhihu}.md 提炼)。

    非法 platform(不在三者之内)直接 ValueError——平台留存不是内在戏剧轴的默认项,
    拼错平台名不该静默退化成某个平台的规则,调用方须显式确认平台。

    输出契约与 build_reversal_rubric_prompt 同一套统一 FindingsSchema(六字段 +
    severity S1-S4 + category 固定 "platform" + verdict APPROVE|CONCERNS|REJECT),
    供多 reviewer 结果经 normalize_findings/merge_verdicts 统一合并。

    接线说明(app 端点接线不在本任务,app.py 被并行任务占用):按 work.target_platform
    非空才调用本函数(严肃向作品默认不传 platform,平台轴整体不触发)。
    """
    rubric = _PLATFORM_RUBRICS.get(platform)
    if rubric is None:
        raise ValueError(f"未知平台: {platform!r},仅支持 {tuple(_PLATFORM_RUBRICS)}")
    det = "\n".join(f"  · {d}" for d in rubric["deterministic"])
    axes = "\n".join(f"  · {a}" for a in rubric["llm_axes"])
    lo, hi = rubric["word_range"]
    return (
        ANTI_SYCOPHANCY + "\n\n"
        f"你是【{rubric['name']}】平台留存评审。读下面一章小说正文,评估其在本平台的读者"
        f"留存表现(该平台章节字数参考区间:{lo}-{hi} 字)。\n"
        "【平台惯例口径(部分可由确定性指标核验,供你判断严重度时参考)】\n" + det + "\n"
        "【平台留存轴(逐项判定,任一命中即问题)】\n" + axes + "\n\n"
        '只输出一行 JSON:{"findings":[{"severity":"S1"|"S2"|"S3"|"S4",'
        '"category":"platform","location":定位,"evidence":引文,'
        '"issue":问题描述,"fix":修复建议}],"verdict":"APPROVE"|"CONCERNS"|"REJECT"}。\n\n'
        f"正文:\n{prose}")


def parse_platform_report(raw: str) -> dict | None:
    """解析平台留存评审 JSON。镜像 parse_tension_report 的容错(提取首个 {...} 块,
    json.loads,坏 JSON/截断/空/None 一律 fail-safe 返回 None)。

    额外两步归一化(平台轴接入统一编排前置清洗):
    - findings 过 normalize_findings 清洗(非法 severity/category 整条丢弃,按
      severity 排序);
    - verdict 非法值(不在 APPROVE/CONCERNS/REJECT 三者)归 CONCERNS——保守,不能盖章。
    """
    try:
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            _log.warning("parse_platform_report 无 JSON 块: raw[:120]=%r", (raw or "")[:120])
            return None
        d = json.loads(m.group(0))
    except Exception as e:
        _log.warning("parse_platform_report 失败: %s | raw[:120]=%r", e, (raw or "")[:120])
        return None
    verdict = d.get("verdict")
    if verdict not in ("APPROVE", "CONCERNS", "REJECT"):
        if verdict is not None:
            _log.warning("parse_platform_report 遇到非法 verdict,按 CONCERNS 计: %r", verdict)
        verdict = "CONCERNS"
    return {"findings": normalize_findings(d.get("findings") or []), "verdict": verdict}


def build_reasoning_audit_prompt(rules_text: str, events_text: str) -> str:
    """5 类推理一致性审计 prompt(oh-story consistency-checker.md 第三步:推理型一致性
    审查,移植其 5 类审计维度 + 证据链输出格式要求)。

    5 类(任一命中即问题):
    ① 规则边界悖论——规则的适用条件/例外条件/触发代价被"按规则应该不能发生却发生了"
      或"例外条件被无限扩大"打破;
    ② 设定层级冲突——世界级规则/势力级规则/角色个人能力/一次性道具效果分层,下位设定
      无解释覆盖上位设定(局部例外必须有来源/代价/章节证据);
    ③ 跨章因果链——对核心事件建立「原因→条件→行动→结果→后果」链,检查是否缺关键
      条件、结果反向否定原因、后果被遗忘,或前章设下的限制在后章无解释消失;
    ④ 规则可滥用漏洞——能力/金手指/制度规则是否存在显而易见的无限刷资源/零成本规避
      风险/绕过主线冲突的用法(前文已给出限制但后文忘用才报,"还可以更好玩"不算);
    ⑤ 代价一致性——能力/交易/复活/治疗/突破等高收益行为,核对既定代价是否每次兑现、
      强度是否前后跳变、是否只在方便时存在、是否被无成本绕过。

    rules_text/events_text 任一为空(None 或去空白后为空串)→ 相应节标注"(无数据)",
    prompt 仍照常生成——不因缺一半数据就整体放弃审计(例如仅凭事件链也能看出因果
    断裂,仅凭规则文本也能看出层级冲突)。

    输出契约:FindingsSchema 六字段(severity/category/location/evidence/issue/fix)+
    verdict,与 build_reversal_rubric_prompt/build_platform_rubric_prompt 同一套统一
    schema,供 normalize_findings/merge_verdicts 统一合并;evidence 字段固定按证据链
    格式填写"前提/规则→触发→矛盾→需裁决"四段(oh-story 原文对推理型 finding 的格式
    硬性要求),不得只填半句结论。category 收窄映射:①②④(规则类)→"rule_boundary";
    ③(因果链)→"causal";⑤(代价一致性)→"consistency"。
    """
    rules_block = rules_text.strip() if rules_text and rules_text.strip() else "(无数据)"
    events_block = events_text.strip() if events_text and events_text.strip() else "(无数据)"
    return (
        ANTI_SYCOPHANCY + "\n\n"
        "你是世界规则推理一致性审计员(oh-story consistency-checker 第三步:推理型一致性"
        "审查)。只依据下面提供的设定规则与事件链中已写明、或可由其直接推出的事实审计,"
        "不补设定、不替作者创作。\n\n"
        "审计以下 5 类(任一命中即问题):\n"
        "① rule_boundary·规则边界悖论:规则的适用条件/例外条件/触发代价,是否出现"
        "「按规则应该不能发生却发生了」或「例外条件被无限扩大」;\n"
        "② rule_boundary·设定层级冲突:世界级规则/势力级规则/角色个人能力/一次性道具"
        "效果——下位设定是否无解释覆盖上位设定(局部例外须有来源/代价/章节证据);\n"
        "③ causal·跨章因果链:对核心事件建立「原因→条件→行动→结果→后果」链,是否缺"
        "关键条件、结果反向否定原因、后果被遗忘,或前章设下的限制在后章无解释消失;\n"
        "④ rule_boundary·规则可滥用漏洞:能力/金手指/制度规则是否存在显而易见的无限刷"
        "资源/零成本规避风险/绕过主线冲突的用法(前文已限制但后文忘用才报,\"还可以更"
        "好玩\"不算);\n"
        "⑤ consistency·代价一致性:高收益行为(能力/交易/复活/治疗/突破)的既定代价是否"
        "每次兑现、强度是否前后跳变、是否被无成本绕过。\n\n"
        "【证据链输出契约】命中的 finding,其 evidence 字段必须按以下四段顺序完整填写,"
        "不得只填半句结论:「前提/规则:…；触发事件:…；矛盾点:…；需裁决:…」。\n\n"
        "【水字数征兆·附加判据(rules/story-consistency.md:28,与上述 5 类一并审计,"
        "category 记 \"prose\")】以下两条无法用规则/计数确定性判定,一并交你审议:"
        "全章对话无新信息;连续 2 章无冲突。\n\n"
        "【设定规则】\n" + rules_block + "\n\n"
        "【事件链】\n" + events_block + "\n\n"
        '只输出一行 JSON:{"findings":[{"severity":"S1"|"S2"|"S3"|"S4",'
        '"category":"rule_boundary"|"causal"|"consistency"|"prose","location":定位,'
        '"evidence":"前提/规则:…；触发:…；矛盾:…；需裁决:…","issue":问题描述,'
        '"fix":修复建议}],"verdict":"APPROVE"|"CONCERNS"|"REJECT"}。')


def parse_reasoning_audit(raw: str) -> dict | None:
    """解析推理一致性审计 JSON。镜像 parse_platform_report 的容错(提取首个 {...} 块,
    json.loads,坏 JSON/截断/空/None 一律 fail-safe 返回 None)+ normalize_findings 清洗
    + verdict 非法值归 CONCERNS(保守,不能盖章)。"""
    try:
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            _log.warning("parse_reasoning_audit 无 JSON 块: raw[:120]=%r", (raw or "")[:120])
            return None
        d = json.loads(m.group(0))
    except Exception as e:
        _log.warning("parse_reasoning_audit 失败: %s | raw[:120]=%r", e, (raw or "")[:120])
        return None
    verdict = d.get("verdict")
    if verdict not in ("APPROVE", "CONCERNS", "REJECT"):
        if verdict is not None:
            _log.warning("parse_reasoning_audit 遇到非法 verdict,按 CONCERNS 计: %r", verdict)
        verdict = "CONCERNS"
    return {"findings": normalize_findings(d.get("findings") or []), "verdict": verdict}



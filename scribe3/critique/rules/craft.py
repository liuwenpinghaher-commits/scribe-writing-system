"""Critique rules family: craft (package C · importable)."""
from __future__ import annotations

from scribe3.critique.rules import prompts as _prev_mod

globals().update({
    k: v for k, v in vars(_prev_mod).items()
    if not k.startswith("__")
})

def find_god_view(text: str) -> list[dict]:
    """上帝视角/解释腔语言指纹(oh-story anti-ai-writing 模式8)。对话内豁免(叙述层才算破 POV)。
    与 verify.find_leaks(知识帧事实泄露)分工:此处只查静态语言指纹,report-only,宁可漏不滥杀。"""
    s = text or ""
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    for kind, pat in _GOD_VIEW_PATTERNS:
        for m in pat.finditer(s):
            if _in_any_span(m.start(), m.end(), quoted):
                continue
            out.append({"kind": kind, "phrase": m.group(0), "range": [m.start(), m.end()]})
    return out


def find_duplicate_lines(text: str, min_chars: int = 6) -> list[dict]:
    """检测精确重复的整行或整句(>=2次,字符总长>=min_chars)。

    切分策略:先按换行拆行,再对每行按中文句末标点(。！？…)拆句
    (分隔符附在前一句末,保留句末标点使句子有自然长度);
    归一化首尾空白后做完全相同比对。
    排除:纯标点/空串、字符总长不足 min_chars 的短句。
    返回 [{"line": <重复的句/行>, "count": <次数>}],按 count 降序。
    """
    from collections import Counter

    raw = text or ""
    segments: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 用带 capture group 的 split 保留分隔符,再把分隔符拼回前一句
        parts = _SENT_DELIM_CAP.split(line)
        buf = ""
        for part in parts:
            if _SENT_DELIM_CAP.fullmatch(part):
                # 这是标点分隔符:追加到当前缓冲区,然后 flush
                buf += part
                normed = buf.strip()
                if normed:
                    segments.append(normed)
                buf = ""
            else:
                buf += part
        # 行末无句末标点时 flush 余量
        normed = buf.strip()
        if normed:
            segments.append(normed)

    counts: Counter[str] = Counter(segments)
    out: list[dict] = []
    for seg, cnt in counts.items():
        if cnt < 2:
            continue
        # 排除字符总长不足 min_chars 的短句(含标点一起算)
        if len(seg) < min_chars:
            continue
        # 排除纯标点/空串
        if _PUNCT_ONLY.match(seg):
            continue
        out.append({"line": seg, "count": cnt})

    out.sort(key=lambda x: -x["count"])
    return out


def find_parallelism(text: str, min_run: int = 3, prefix_len: int = 2) -> list[dict]:
    """检测排比/同句式复读(AI 抒情腔):连续 >=min_run 个句子以相同的起首
    (前 prefix_len 个汉字)开头,或相邻句反复用同一引导词(就像/穿过/有些/不是…)。

    乱世铜炉志怪笔记体忌排比抒情;opus 评判反复点名"同句式≥3连"是 AI 腔。
    切句:按换行 + 中文句末标点(。!?…)+ 逗号分句(排比常以逗号断)。
    归一:剥离起首引号/破折号等装饰符后取前 prefix_len 个汉字为指纹。
    返回 [{"prefix": <起首>, "count": <连排数>, "sample": <首句>}],按 count 降序。
    仅在指纹是汉字(非纯标点/数字)时计入。
    引号内(台词/弹幕)豁免——体裁正常形态,只判叙述层排比。
    """
    text = _strip_quoted(text)
    raw = text or ""
    # 句/读切分:句末标点与逗号、顿号都作为排比分句边界
    pieces: list[str] = []
    for line in raw.split("\n"):
        for seg in re.split(r"[。！？…,，、;；\n]", line):
            seg = seg.strip().lstrip("\"'“”‘’—…·　 ")
            if seg:
                pieces.append(seg)

    def fp(s: str) -> str:
        # 取前 prefix_len 个汉字作指纹
        han = re.findall(r"[一-鿿]", s)
        return "".join(han[:prefix_len]) if len(han) >= prefix_len else ""

    out: list[dict] = []
    i = 0
    n = len(pieces)
    while i < n:
        f = fp(pieces[i])
        if not f:
            i += 1
            continue
        j = i + 1
        while j < n and fp(pieces[j]) == f:
            j += 1
        run = j - i
        if run >= min_run:
            out.append({"prefix": f, "count": run, "sample": pieces[i][:24]})
        i = j if j > i else i + 1

    out.sort(key=lambda x: -x["count"])
    return out


def find_poetic_fragments(text: str, max_len: int = 6) -> list[dict]:
    """诗化分行/拟声悬停检测(AI 抒情/恐怖腔):孤立的短句(非对白)独立成行,或拟声词成行。
    排除对白行(含引号)与纯标点。返回 [{"line","kind","ending"}];kind=onomatopoeia|fragment,
    ending=True 表示该碎句正是全文末行(章节拟声/单字煞尾——opus 评判明令禁止)。"""
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    out: list[dict] = []
    n = len(lines)
    for i, l in enumerate(lines):
        if len(l) > max_len:
            continue
        if any(q in l for q in "“”\"'「」『』"):  # 对白,放过
            continue
        if _PUNCT_ONLY.match(l):
            continue
        kind = "onomatopoeia" if _ONOMAT_LINE.match(l) else "fragment"
        out.append({"line": l, "kind": kind, "ending": i == n - 1})
    return out


def find_unbalanced_quotes(text: str) -> list[dict]:
    """引号开闭不配对(中文“”/「」)。返回失衡项;空列表=配对正常。"""
    t = text or ""
    issues: list[dict] = []
    for op, cl in (("“", "”"), ("「", "」"), ("『", "』")):
        a, b = t.count(op), t.count(cl)
        if a != b:
            issues.append({"pair": op + cl, "open": a, "close": b})
    if t.count('"') % 2:
        issues.append({"pair": '"', "count": t.count('"')})
    return issues


def find_watch_regression(text: str) -> list[dict]:
    """更次倒退检测:文中更次(一更→五更)序列若非单调递增(后文更次 < 已达最大更次)即报。
    志怪夜戏常见硬伤——开篇四更、后文又'三更'。返回倒退点 [{"label","pos","after_max"}]。"""
    seq = []
    for m in re.finditer(r"[一二两三四五]更", text or ""):
        w = _WATCH_MAP.get(m.group(0))
        if w:
            seq.append((m.start(), w, m.group(0)))
    out: list[dict] = []
    mx = 0
    for pos, w, label in seq:
        if w < mx:
            out.append({"label": label, "pos": pos, "after_max": mx})
        mx = max(mx, w)
    return out


def find_emotion_telling(text: str, allow_patterns: list[str] | None = None,
                         short_mode: bool = False) -> list[dict]:
    """检测叙述层直陈情绪/直接评语/思想转述的句子(确定性正则,宁缺勿滥)。

    方案B任务13:情绪表达4级(oh-story style-craft.md)是一条"直写 < 思想 < 神态 <
    动作"的表达质量阶梯——直写情绪词最生硬,动作/神态侧写最含蓄高级。本检测器只
    上报前两级(L1/L2)确定性可判的 telling,L3(神态)/L4(动作)是合法的 showing
    手法,语义上不该报——因此不扫描,不构成检测规则。

    规则(L1,level=1,直写):
    - emotion_word: (他|她|它)?(感到|觉得|心里|心中|心头)(一阵|一)?(情绪词)
    - verdict:      (他|她)(其实)?(不是|是)(个)?(坏人|好人|善人|恶人)
    - cliche(weak): 心里像被什么(揪|攥|堵)住 等标签化套语

    规则(L2,level=2,思想转述):
    - thought_report: 心中暗道|心想|心道|暗想|暗忖——用叙述层动词直接转述人物内心
      念头,不点名具体情绪词,但仍是 telling(比直写情绪词含蓄一级,仍非 showing)。

    对话内情感词处理:粗略去除中文弯引号包裹片段后再扫描(减少误报)。
    返回 [{"span": <命中片段>, "kind": "emotion_word"|"verdict"|"cliche"|"thought_report",
    "level": 1|2}](kind/span 字段向后兼容既有调用方)。

    allow_patterns(方案B任务14):题材豁免正则,来自 craft_rule allow_pattern——前置
    skip 判定(减法),命中 span 匹配任一 allow 正则即放行不报。与其余检测器同一豁免
    机制,独立于本函数既有的 level 分级逻辑(B13),不改动分级判定,只在收录前多一道
    豁免过滤。

    short_mode(方案B任务16):短篇模式开关——短篇要直写情绪+审判金句(见
    scribe3/genres.py 四题材包的 keep_list),长篇的"留白/克制"引擎(craft.py
    ENGINES["restraint"])全线让位。short_mode=True 时本检测器直接返回 []
    (不做任何 telling 判定,视图层/AI味定档不再因直写情绪而扣分),优先级高于
    allow_patterns(两者语义重叠时 short_mode 是更彻底的整体开关)。
    """
    if short_mode:
        return []
    s = _strip_dialogue(text or "")
    allow_pats = [re.compile(p) for p in (allow_patterns or [])]

    def _allowed(span: str) -> bool:
        return bool(allow_pats) and any(rx.search(span) for rx in allow_pats)

    out: list[dict] = []

    for m in _EMOTION_WORD_RE.finditer(s):
        if _allowed(m.group(0)):
            continue
        out.append({"span": m.group(0), "kind": "emotion_word", "level": 1})

    for m in _VERDICT_RE.finditer(s):
        if _allowed(m.group(0)):
            continue
        out.append({"span": m.group(0), "kind": "verdict", "level": 1})

    for m in _CLICHE_RE.finditer(s):
        # 避免与 emotion_word 重叠上报
        span = m.group(0)
        if _allowed(span):
            continue
        if not any(r["span"] in span or span in r["span"] for r in out):
            out.append({"span": span, "kind": "cliche", "level": 1})

    for m in _THOUGHT_REPORT_RE.finditer(s):
        if _allowed(m.group(0)):
            continue
        out.append({"span": m.group(0), "kind": "thought_report", "level": 2})

    return out


def emotion_telling_summary(text: str, hits: list[dict] | None = None) -> dict:
    """情绪表达4级分级聚合(方案B任务13),供整章定档/前端聚合展示消费。

    按 find_emotion_telling 命中的 level 拆分 L1(直写)/L2(思想转述)计数:
      l1_count / l2_count  各级命中数
      l1_ratio             l1_count / 句数(句子按 [。！？\\n] 切分,与 aggregate_ai_grade
                            _SENT_SPLIT 同口径)
      total                L1+L2 合计命中数

    hits 可选:调用方已算好 find_emotion_telling(text) 结果时直接传入复用,避免重算
    (见 aggregate_ai_grade 的 C 指标用法);缺省则内部现算。
    """
    hits = find_emotion_telling(text) if hits is None else hits
    l1_count = sum(1 for h in hits if h.get("level") == 1)
    l2_count = sum(1 for h in hits if h.get("level") == 2)
    sent_count = len([s for s in _SENT_SPLIT.split(text or "") if s.strip()]) or 1
    return {
        "l1_count": l1_count,
        "l2_count": l2_count,
        "l1_ratio": l1_count / sent_count,
        "total": len(hits),
    }


def discipline_truncate(text: str, brief: str, complete_fn, known: dict | None = None) -> dict:
    """判定违规→复发点靠后(留≥40%)则截到复发点;复发太早只标记不砍(交回重生)。"""
    v = parse_discipline(complete_fn(build_discipline_prompt(text, brief, known)))
    extra = v.get("extra") or []
    _pf = {"parse_failed": True} if v.get("parse_failed") else {}
    if v["ok"] or not v["cut_after"]:
        return {"text": text, "violations": v["violations"], "extra": extra,
                "changed": False, **_pf}
    idx = text.find(v["cut_after"])
    if idx < 0:
        return {"text": text, "violations": v["violations"], "extra": extra, "changed": False}
    cut = text[:idx + len(v["cut_after"])]
    if len(cut) < len(text) * 0.4:
        return {"text": text, "violations": v["violations"], "extra": extra,
                "changed": False, "cut_after": v["cut_after"]}
    return {"text": cut, "violations": v["violations"], "extra": extra, "changed": True}


def _degen_visible_length(s: str) -> int:
    """可见字数(剔除标点/空白后的有效字符计数),移植自 JS visibleLength。"""
    return len(_DEGEN_VISIBLE_RE.findall(s or ""))


def _degen_body_lines(text: str) -> list[dict]:
    """按行拆分 + 剔除空行,记录每行【去首尾空白后的内容】在原始 text 里的起始 offset,
    供各子检测器还原 range。"""
    body: list[dict] = []
    pos = 0
    for raw in (text or "").split("\n"):
        trimmed = raw.strip()
        if trimmed:
            lead = len(raw) - len(raw.lstrip())
            body.append({"start": pos + lead, "line": trimmed})
        pos += len(raw) + 1  # +1 补回被 split 吃掉的换行符
    return body


def _degen_adjacent_repeat(body: list[dict]) -> list[dict]:
    """紧邻整行一字不差重复(即时循环)。range 指向第二次出现处。"""
    out: list[dict] = []
    for i in range(1, len(body)):
        cur, prev = body[i], body[i - 1]
        if cur["line"] != prev["line"]:
            continue
        if _degen_visible_length(_strip_quoted(cur["line"])) < ADJACENT_MIN_LEN:
            continue
        out.append({
            "kind": "adjacent_repeat",
            "severity": "blocking",
            "phrase": cur["line"],
            "range": [cur["start"], cur["start"] + len(cur["line"])],
        })
    return out


def _degen_sentence_loop(body: list[dict]) -> list[dict]:
    """长句(引号外、可见字数≥REPEAT_MIN_LEN)出现≥REPEAT_MIN_COUNT 次判为打转。
    只豁免引号内台词,引号外叙述句(含"叙述+引号内物件"混合行)仍参与计数。
    range 指向该句第二次出现处(方案A任务5要求,与 JS 的"首次出现"不同)。

    定位:句子在【剥引号文本】上计数,经 _strip_quoted_with_map 的下标映射精确还原回
    原文区间——混合行(叙述+引号)的句子若跨过引号片段,range/phrase 为原文里覆盖该句
    首尾字符的连续区间(中间夹着的引号片段一并包含,保证 phrase == 原文[start:end])。
    """
    counts: dict[str, int] = {}
    # (句子, 行, 行内起, 行内止):起止为原文行坐标,入队时即映射好,回填不再 find
    occurrences: list[tuple[str, dict, int, int]] = []
    for b in body:
        stripped, idx_map = _strip_quoted_with_map(b["line"])
        # 用 finditer 取非分隔符连续段(与 re.split 的非空片段等价),自带片段起点
        for m in re.finditer(r"[^。！？!?]+", stripped):
            piece = m.group(0)
            st = piece.strip()
            if _degen_visible_length(st) < REPEAT_MIN_LEN:
                continue
            lead = len(piece) - len(piece.lstrip())
            ss = m.start() + lead          # st 在剥引号文本里的 [ss, se)
            se = ss + len(st)
            line_start = idx_map[ss]                # 映射回原文行坐标
            line_end = idx_map[se - 1] + 1
            counts[st] = counts.get(st, 0) + 1
            occurrences.append((st, b, line_start, line_end))
    flagged = {s for s, c in counts.items() if c >= REPEAT_MIN_COUNT}
    if not flagged:
        return []
    out: list[dict] = []
    seen: dict[str, int] = {}
    for st, b, line_start, line_end in occurrences:
        if st not in flagged:
            continue
        seen[st] = seen.get(st, 0) + 1
        if seen[st] != 2:  # 只在第二次出现时报一条(range 指向第二次出现处)
            continue
        out.append({
            "kind": "sentence_loop",
            "severity": "blocking",
            "phrase": b["line"][line_start:line_end],  # 原文精确子串,与 range 逐字一致
            "range": [b["start"] + line_start, b["start"] + line_end],
            "count": counts[st],
        })
    return out


def _degen_placeholders(body: list[dict]) -> list[dict]:
    """占位符/拒绝语/乱码/英文 AI 腔泄漏。一行只报一条(命中优先级同 JS 数组顺序)。"""
    out: list[dict] = []
    for b in body:
        line = b["line"]
        dialogue = _degen_visible_length(_strip_quoted(line)) < 2
        for pat, kind, hard in _DEGEN_PLACEHOLDER_PATTERNS:
            if not hard and dialogue:
                continue  # soft 拒绝语在对话行里可能是正常台词,豁免
            m = pat.search(line)
            if not m:
                continue
            start, end = b["start"] + m.start(), b["start"] + m.end()
            out.append({
                "kind": kind,
                "severity": "blocking",
                "phrase": m.group(0),  # 精确匹配片段,与 range 保持一致(range 不变量)
                "range": [start, end],
            })
            break  # 一行一条足矣
    return out


def _degen_meta_leak(body: list[dict], quoted_ranges: list[tuple[int, int]]) -> list[dict]:
    """工程词泄漏:tier1 优先于 tier2(命中 tier1 即跳过 tier2,同一行不叠报)。
    首个内容行若是章节标题("第N章…")豁免,避免每章标题都被 tier2 的"第X章"命中误报。
    tier1 命中落在【引号内】(_quoted_ranges)降级 advisory;tier2 恒 advisory。"""
    out: list[dict] = []
    first_seen = False
    for b in body:
        line = b["line"]
        if not first_seen:
            first_seen = True
            if _DEGEN_TITLE_RE.match(line):
                continue
        m = _DEGEN_META_TIER1_RE.search(line)
        if m:
            start, end = b["start"] + m.start(), b["start"] + m.end()
            dialogue = _in_any_span(start, end, quoted_ranges)
            out.append({
                "kind": "meta_leak",
                "tier": 1,
                "severity": "advisory" if dialogue else "blocking",
                "phrase": m.group(0),
                "range": [start, end],
            })
            continue  # tier1 命中即可,不再叠 tier2
        m = _DEGEN_META_TIER2_RE.search(line)
        if m:
            start, end = b["start"] + m.start(), b["start"] + m.end()
            out.append({
                "kind": "meta_leak",
                "tier": 2,
                "severity": "advisory",
                "phrase": m.group(0),
                "range": [start, end],
            })
    return out


def _degen_truncated(body: list[dict]) -> list[dict]:
    """全文最后一个非空行未以句末/收尾标点结束 → 疑似被模型中途切断。
    phrase/range 取行尾最多 24 字(不经 compact,保证 range 精确指向 phrase,不含全行)。"""
    if not body:
        return []
    last = body[-1]
    if _DEGEN_TRUNCATED_END_RE.search(last["line"]):
        return []
    tail = last["line"][-24:]
    tail_start = last["start"] + len(last["line"]) - len(tail)
    return [{
        "kind": "truncated",
        "severity": "advisory",
        "phrase": tail,
        "range": [tail_start, tail_start + len(tail)],
    }]


def find_degeneration(text: str) -> list[dict]:
    """模型退化指纹汇总检测(report-only):复读/打转 + 占位拒绝语泄漏 + 工程词泄漏
    (tier1/tier2)+ 中途截断。移植自 oh-story check-degeneration.js,阈值/正则逐字对照,
    仅 truncated 的 severity 按方案A任务5要求由 blocking 降级为 advisory。
    返回统一 {"kind","severity","phrase","range"[,"tier"]}。
    """
    s = text or ""
    body = _degen_body_lines(s)
    quoted = _quoted_ranges(s)
    out: list[dict] = []
    out.extend(_degen_adjacent_repeat(body))
    out.extend(_degen_sentence_loop(body))
    out.extend(_degen_placeholders(body))
    out.extend(_degen_meta_leak(body, quoted))
    out.extend(_degen_truncated(body))
    return out


def find_rhythm_uniformity(text: str) -> dict | None:
    """句长方差/burstiness 量化(GPTZero/DetectGPT/Binoculars 公认头号 AI 破绽:句长分布
    异常均匀=节拍器)。report-only,不改写、不阻塞。

    做法:剥引号(_strip_quoted)只算叙述句的可见字长(复用 _DEGEN_VISIBLE_RE,与 A5
    退化检测同口径),按句末标点切句 → 句长序列 → CV(变异系数=标准差/均值)+
    相邻句长差比(缺乏突变的另一侧写照,单独用 CV 会被"逐渐变长的等差数列"骗过)。
    两者都低于阈值才判 verdict="uniform"(节拍器),否则"ok"。
    句数 < _RHYTHM_MIN_SENTS 时样本太薄,直接返回 None(不判,不误报短章/片段)。
    """
    s = _strip_quoted(text or "")
    lens = [n for n in (_degen_visible_length(seg) for seg in re.split(r"[。！？!?…]+", s)) if n > 0]
    if len(lens) < _RHYTHM_MIN_SENTS:
        return None
    mean = sum(lens) / len(lens)
    sigma = (sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5
    cv = sigma / mean if mean else 0.0
    adj = [abs(a - b) for a, b in zip(lens, lens[1:])]
    mean_adj_ratio = (sum(adj) / len(adj) / mean) if adj and mean else 0.0
    verdict = "uniform" if (cv < _RHYTHM_CV_FLOOR and mean_adj_ratio < _RHYTHM_ADJ_FLOOR) else "ok"
    return {"cv": round(cv, 3), "sigma": round(sigma, 1), "mean": round(mean, 1),
            "mean_adj_ratio": round(mean_adj_ratio, 3), "n_sentences": len(lens), "verdict": verdict}


def _ai_grade_tier(value: float, light_max: float, medium_max: float) -> str:
    """三档判定:value < light_max → light;light_max <= value <= medium_max → medium;
    value > medium_max → heavy(与 6 指标"轻<X/中X-Y/重>Y"的区间语义对齐)。"""
    if value < light_max:
        return "light"
    if value <= medium_max:
        return "medium"
    return "heavy"


def aggregate_ai_grade(flags: dict, text: str, precomputed: dict | None = None,
                       short_mode: bool = False) -> dict:
    """整章 AI 味定档聚合:quality_flags(text) 的分项命中 → 6 指标(千字/占比口径,轻中重
    三档)→ 7-Gate 骨架(A-G)→ 章级 grade(light/medium/heavy)。

    6 指标(oh-story story-deslop SKILL.md AI味6指标):
      ① banned_density   ai_tics 里 banned_word/contextual_word 命中数/千字(可见字数口径)
      ② parallel_run      find_parallelism(text) 的最大连排 count(真机冒烟修复见下方
                           ②parallel_run 计算处注释——不再掺入 flags["structural"])
      ③ psych_ratio       find_emotion_telling(text) 命中数 / 句子数(百分比)
      ④ dialogue_tag_density  「XX说/道」型提示语命中数/千字
      ⑤ rhythm_uniform    flags["rhythm"] 的 verdict(ok=轻/uniform=重,无中档;缺失=轻)
      ⑥ repeat_density    (flags["repetition"] + find_duplicate_lines(text) 命中数)/千字

    7-Gate 映射(附录§H.2,A-G 对应禁用词/句式套路/心理告知/节奏均匀/对话腔调/结尾升华/
    解释腔上帝感):详见各 gate_*_hit 计算处注释。

    flags 里缺的键(旧调用方传部分 dict)一律 .get 容错;text 为空/纯空白返回 light 空骨架。

    precomputed(计划A尾巾 A8-Important 修复):调用方(/post-check)在调用本函数前往往
    已经对同一份 text 跑过 find_duplicate_lines/find_emotion_telling/find_parallelism/
    find_poetic_fragments(拼装 duplicate_lines/emotion_telling/parallelism/
    poetic_fragments 等响应字段),本函数原先又对同一 text 重算一遍这四个检测器——
    纯浪费。precomputed 允许调用方把已算好的结果直接传进来复用,键名与上述四个检测器
    同名;缺哪个键就现算哪个,兼容 /check 等没有预算过的旧调用方(不传即整体现算,
    行为与修复前一致)。

    short_mode(方案B任务16):短篇模式开关,透传自 find_emotion_telling。True 时
    ③psych_ratio 强制归零(不管 precomputed 是否带了 emotion_telling 键,short_mode
    整体覆盖——短篇直写情绪不算 AI 味),Gate C(心理告知)因而不会触发。"""
    flags = flags or {}
    text = text or ""
    precomputed = precomputed or {}
    indicator_names = ("banned_density", "parallel_run", "psych_ratio",
                        "dialogue_tag_density", "rhythm_uniform", "repeat_density")
    if not text.strip():
        return {
            "grade": "light",
            "gates": {g: {"hit": False, "count": 0} for g in "ABCDEFG"},
            "gates_hit": [],
            "indicators": {name: {"value": "ok" if name == "rhythm_uniform" else 0, "tier": "light"}
                           for name in indicator_names},
        }

    ai_tics = flags.get("ai_tics") or []
    structural = flags.get("structural") or []
    purple = flags.get("purple") or []
    god_view = flags.get("god_view") or []
    repetition = flags.get("repetition") or []
    rhythm = flags.get("rhythm")

    visible = _degen_visible_length(text)
    per_k = 1000.0 / visible if visible else 0.0

    # ①banned_density
    banned_hits = [h for h in ai_tics if h.get("kind") in ("banned_word", "contextual_word")]
    banned_density = len(banned_hits) * per_k
    banned_tier = _ai_grade_tier(banned_density, _AI_GRADE_BANNED_LIGHT, _AI_GRADE_BANNED_MEDIUM)

    # ②parallel_run(真机冒烟修复 2026-07-04):只采信 find_parallelism 的最大连排数,
    # 不再掺入 flags["structural"] 的 count。根因:find_structural_repeats 的
    # anaphora/short 两种 kind 的 "count" 字段都是【全章总命中条数】(anaphora 是
    # collections.Counter 对"同 3 字开头句子"的全局出现次数,short 是"极短断句"
    # 的全章总条数),不是"连续排比的连排长度"。真机验收章节实测:第三人称限知
    # 视角主角名字(如"苏纸鸢")在整章散布着当主语开头是完全正常的中文叙事形态,
    # 243 句里出现 23 次、但从未连续相邻——却被当年实现直接当"最大连排数"喂给
    # parallel_run,6 个已人工验收章节因此全部误判 heavy(见
    # tests/test_critique.py::test_parallel_run_ignores_scattered_whole_chapter_opener_tally
    # 复现)。find_parallelism 才是真正逐句比对相邻指纹的连续排比检测器,其 count
    # 语义与 parallel_run 的"最大连排数"定义一致,真机验收章节实测其值稳定在
    # 3~4(见 tools/calibrate_ai_grade.py 标定注释),量级远小于 structural 的全章
    # 计数,不会再被虚高污染。structural 的 anaphora/short 命中仍完整保留在
    # flags["structural"] 里供 /post-check 等端点做"全章重复主语/开头"的编辑提示,
    # 以及下方 Gate D(短句节奏)继续读取 short kind——只是不再喂给 parallel_run。
    parallelism_hits = (precomputed["parallelism"] if "parallelism" in precomputed
                        else find_parallelism(text))
    parallel_counts = [p.get("count", 0) for p in parallelism_hits]
    parallel_run = max(parallel_counts) if parallel_counts else 0
    parallel_tier = _ai_grade_tier(parallel_run, _AI_GRADE_PARALLEL_LIGHT, _AI_GRADE_PARALLEL_MEDIUM)

    # ③psych_ratio(方案B任务13:改用 emotion_telling_summary 同口径统计,复用其
    # L1+L2 命中计数,不再自己重复一遍"数命中"逻辑;total=len(emotion_hits) 恒成立,
    # 与修复前数值等价——旧调用方文本从无 L2 思想转述模式,l2_count 恒为 0)
    if short_mode:
        emotion_hits: list[dict] = []
    else:
        emotion_hits = (precomputed["emotion_telling"] if "emotion_telling" in precomputed
                        else find_emotion_telling(text))
    emo_summary = emotion_telling_summary(text, hits=emotion_hits)
    sent_count = len([s for s in _SENT_SPLIT.split(text) if s.strip()]) or 1
    psych_ratio = emo_summary["total"] / sent_count * 100
    psych_tier = _ai_grade_tier(psych_ratio, _AI_GRADE_PSYCH_LIGHT, _AI_GRADE_PSYCH_MEDIUM)

    # ④dialogue_tag_density
    dialogue_hits = len(_AI_GRADE_DIALOGUE_TAG_RE.findall(text))
    dialogue_density = dialogue_hits * per_k
    dialogue_tier = _ai_grade_tier(dialogue_density, _AI_GRADE_DIALOGUE_LIGHT,
                                   _AI_GRADE_DIALOGUE_MEDIUM)

    # ⑤rhythm_uniform:二值指标,无中档;None(句数不足未判)按轻处理
    rhythm_verdict = rhythm.get("verdict") if isinstance(rhythm, dict) else None
    rhythm_tier = "heavy" if rhythm_verdict == "uniform" else "light"

    # ⑥repeat_density
    dup_lines = (precomputed["duplicate_lines"] if "duplicate_lines" in precomputed
                else find_duplicate_lines(text))
    repeat_count = len(repetition) + len(dup_lines)
    repeat_density = repeat_count * per_k
    repeat_tier = _ai_grade_tier(repeat_density, _AI_GRADE_REPEAT_LIGHT, _AI_GRADE_REPEAT_MEDIUM)

    indicators = {
        "banned_density": {"value": round(banned_density, 2), "tier": banned_tier},
        "parallel_run": {"value": parallel_run, "tier": parallel_tier},
        "psych_ratio": {"value": round(psych_ratio, 2), "tier": psych_tier},
        "dialogue_tag_density": {"value": round(dialogue_density, 2), "tier": dialogue_tier},
        "rhythm_uniform": {"value": rhythm_verdict or "ok", "tier": rhythm_tier},
        "repeat_density": {"value": round(repeat_density, 2), "tier": repeat_tier},
    }

    # ---- 7-Gate 映射(附录§H.2)----
    # A 禁用词:ai_tics 的 banned_word/contextual_word 命中且 banned_density 达"中"档(含重)
    gate_a_hit = bool(banned_hits) and _GRADE_ORDER[banned_tier] >= _GRADE_ORDER["medium"]

    # B 句式套路:not_a_but_b(否定翻转)+ toxic_pattern(毒句式)+ purple(升华/抒情直陈)
    # 命中数合计 >= 1
    not_a_but_b_hits = [h for h in ai_tics if h.get("kind") == "not_a_but_b"]
    toxic_hits = [h for h in ai_tics if h.get("kind") == "toxic_pattern"]
    gate_b_count = len(not_a_but_b_hits) + len(toxic_hits) + len(purple)
    gate_b_hit = gate_b_count >= 1

    # C 心理告知:psych_ratio 达"中"档(含重)
    gate_c_hit = _GRADE_ORDER[psych_tier] >= _GRADE_ORDER["medium"]

    # D 节奏均匀:rhythm uniform 或 structural.short(极短断句滥用)或 poetic_fragments 命中
    short_structural = [s for s in structural if s.get("kind") == "short"]
    poetic_hits = (precomputed["poetic_fragments"] if "poetic_fragments" in precomputed
                  else find_poetic_fragments(text))
    gate_d_hit = rhythm_verdict == "uniform" or bool(short_structural) or bool(poetic_hits)
    gate_d_count = (1 if rhythm_verdict == "uniform" else 0) + len(short_structural) + len(poetic_hits)

    # E 对话腔调:dialogue_tag_density 达"中"档(含重)
    gate_e_hit = _GRADE_ORDER[dialogue_tier] >= _GRADE_ORDER["medium"]

    # F 结尾升华 / G 解释腔上帝感:god_view 按 kind 拆分,sublimation 归 F,其余归 G
    sublimation_hits = [h for h in god_view if h.get("kind") == "sublimation"]
    other_god_hits = [h for h in god_view if h.get("kind") != "sublimation"]
    gate_f_hit = len(sublimation_hits) >= 1
    gate_g_hit = len(other_god_hits) >= 1

    gates = {
        "A": {"hit": gate_a_hit, "count": len(banned_hits)},
        "B": {"hit": gate_b_hit, "count": gate_b_count},
        "C": {"hit": gate_c_hit, "count": len(emotion_hits)},
        "D": {"hit": gate_d_hit, "count": gate_d_count},
        "E": {"hit": gate_e_hit, "count": dialogue_hits},
        "F": {"hit": gate_f_hit, "count": len(sublimation_hits)},
        "G": {"hit": gate_g_hit, "count": len(other_god_hits)},
    }
    gates_hit = [g for g in "ABCDEFG" if gates[g]["hit"]]

    # grade:6 指标最高档;命中 Gate 数 >= _AI_GRADE_HEAVY_GATE_COUNT 强制 heavy
    # (oh-story"4+ Gate 有问题=重度")。
    tiers = [banned_tier, parallel_tier, psych_tier, dialogue_tier, rhythm_tier, repeat_tier]
    grade = max(tiers, key=lambda t: _GRADE_ORDER[t])
    if len(gates_hit) >= _AI_GRADE_HEAVY_GATE_COUNT:
        grade = "heavy"

    return {"grade": grade, "gates": gates, "gates_hit": gates_hit, "indicators": indicators}



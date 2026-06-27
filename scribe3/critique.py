"""移植自 scribe2/critique.py 的确定性 QC 纯函数(已验证资产)。

跨段复读/排比开头/单字断句/升华句——prompt 规则治不了已生成文本,确定性扫描+定向删才拦得住。
纯函数(无 DB/无网络),作渲染层质检兜底。语义级违规(双高潮/声音崩)是另一路(LLM 判官,后续)。
"""
import json
import logging
import re

_log = logging.getLogger("scribe3.critique")

_PUNCT_ONLY = re.compile(r"^[，。！？、；：「」『』“”‘’…—\-\d\s]+$")


def find_repetitions(text: str, n: int = 8, min_count: int = 3, top: int = 10) -> list[dict]:
    """长度≥n、出现≥min_count 次的子串(去重叠,保留最长代表)。跨段复读是单遍长程生成典型病。"""
    from collections import Counter
    s = re.sub(r"\s+", "", text or "")
    if len(s) < n:
        return []
    grams = Counter(s[i:i + n] for i in range(len(s) - n + 1))
    cand = [(g, c) for g, c in grams.items() if c >= min_count and not _PUNCT_ONLY.match(g)]
    cand.sort(key=lambda x: (-x[1], -len(x[0])))
    chosen: list[tuple[str, int]] = []
    for g, c in cand:
        if any(g in cg for cg, _ in chosen):
            continue
        chosen.append((g, c))
    return [{"phrase": g, "count": c} for g, c in chosen[:top]]


def _cjk_ngrams(text: str, n: int) -> set[str]:
    """正文去空白后所有含中文的 n-gram 集合(用于跨文本逐字比对)。"""
    s = re.sub(r"\s+", "", text or "")
    return {s[i:i + n] for i in range(len(s) - n + 1)
            if re.search(r"[一-鿿]", s[i:i + n]) and not _PUNCT_ONLY.match(s[i:i + n])}


def _is_allowed(phrase: str, allow: set[str] | None) -> bool:
    """phrase 是否属于"刻意母题/专名"白名单(含任一 allow 词即放行)。
    乱世铜炉式母题(奈何谷/镇煞钉/大元炼真经/三百六十…)本应跨章复现,不算懒惰复读。"""
    if not allow:
        return False
    return any(a and a in phrase for a in allow)


def find_cross_chapter_repetitions(
    text: str, prior_texts: list[str], n: int = 8, top: int = 30,
    allow: set[str] | None = None,
) -> list[dict]:
    """新章中【逐字出现过在任一前文章节】的 ≥n 字独特子串(跨章复读)。

    单遍长程生成的典型病:模型在第 N 章自然复用自己偏爱的措辞/意象,而逐章 `find_repetitions`
    只扫单章内部、完全查不到这种跨章逐字搬运。这里把"新章 ∩ 前文"的逐字重叠揪出来——
    这是把"重复"从'事后逐章删'升级为'可跨章度量、可在生成时预防'的关键检测原语。

    allow:刻意母题/专名白名单——含其中任一词的短语放行(它们本应复现,不算懒惰复读),
    使指标只反映"动作/句式的偷懒重打",更贴近乱世铜炉对母题手法的纵容。

    返回去重叠后的最长代表短语 + 命中的前文章节序号(prior_idx,0-based)。
    """
    if not text or not prior_texts:
        return []
    new_grams = _cjk_ngrams(text, n)
    if not new_grams:
        return []
    prior_grams: dict[str, list[int]] = {}
    for idx, pt in enumerate(prior_texts):
        for g in _cjk_ngrams(pt, n):
            prior_grams.setdefault(g, []).append(idx)
    hits = [(g, prior_grams[g]) for g in new_grams
            if g in prior_grams and not _is_allowed(g, allow)]
    # 去重叠:长串优先,被它包含的短串丢弃,保留最长代表。
    hits.sort(key=lambda gv: (-len(gv[0]), gv[0]))
    chosen: list[tuple[str, list[int]]] = []
    for g, idxs in hits:
        if any(g in cg for cg, _ in chosen):
            continue
        chosen.append((g, idxs))
    return [{"phrase": g, "prior_chapters": idxs} for g, idxs in chosen[:top]]


def distinctive_phrases(text: str, n: int = 8, top: int = 40,
                        allow: set[str] | None = None) -> list[str]:
    """从一章正文里抽"独特措辞/意象"短语(≥n 字、含中文、剔标点),供下一章生成时作'避免逐字复用'清单。

    取每个起点的 n-gram 后做去重叠(保留较前出现的代表),再截断 top。这是源头预防的物料:
    把前文已用过的招式喂进写作 prompt,让模型在【生成时】就避开,而不是事后再删。
    allow:刻意母题/专名白名单——这些本应复现,不进"避免"清单(否则会逼模型回避母题、伤害质感)。
    """
    s = re.sub(r"\s+", "", text or "")
    seen: list[str] = []
    i = 0
    while i <= len(s) - n:
        g = s[i:i + n]
        if re.search(r"[一-鿿]", g) and not _PUNCT_ONLY.match(g) and not _is_allowed(g, allow):
            seen.append(g)
            i += n  # 跳过整段,避免相邻重叠 n-gram 刷屏
        else:
            i += 1
        if len(seen) >= top:
            break
    return seen


def cross_repetition_sentences(text: str, prior_texts: list[str], n: int = 8,
                               allow: set[str] | None = None) -> list[dict]:
    """定位本章中含【跨章逐字复读短语】的句子(定向改写目标)。
    与 find_cross_chapter_repetitions 同源,落到句子粒度。返回 [{sentence, phrases}]。"""
    hits = find_cross_chapter_repetitions(text, prior_texts, n=n, allow=allow)
    if not hits:
        return []
    phrases = [h["phrase"] for h in hits]
    sents = [s for s in re.split(r"(?<=[。！？\n])", text or "") if s.strip()]
    out: list[dict] = []
    for s in sents:
        cleaned = re.sub(r"\s+", "", s)
        hit = [p for p in phrases if p in cleaned]
        if hit:
            out.append({"sentence": s.strip(), "phrases": hit})
    return out


def rewrite_cross_repetitions(text: str, prior_texts: list[str], complete_fn,
                              n: int = 8, allow: set[str] | None = None) -> dict:
    """确定性事后跨章改写——系统哲学:'prompt 规则治不了已生成文本,确定性扫描+定向[改]才拦得住'。

    1) 确定性定位含跨章复读的句子;2) 逐句调 complete_fn 定向改写(换措辞/感官/句式,保意保限知);
    3) 字符串替换回原文。比'prompt 预防'可靠:不依赖模型记住上百条禁用词,只精准改犯规句。
    返回 {prose, rewritten, before, after}。complete_fn(prompt, system)->str。
    """
    before = len(find_cross_chapter_repetitions(text, prior_texts, n=n, allow=allow))
    targets = cross_repetition_sentences(text, prior_texts, n=n, allow=allow)
    if not targets:
        return {"prose": text, "rewritten": 0, "before": before, "after": before}
    new = text
    done = 0
    sys = ("你是小说定向改写器。只改写给你的这一句:保持原意、情节、限知视角、语气与上下文衔接完全不变,"
           "但**换一种措辞/感官/句式**,使其不再与前文逐字雷同。只输出改写后的这一句正文,不要引号、不要解释。")
    for t in targets:
        sent = t["sentence"]
        prompt = (f"前文已用过这些措辞(本句须避开逐字复用):{'、'.join(t['phrases'])}\n\n"
                  f"待改写的句子:{sent}")
        try:
            rw = (complete_fn(prompt, sys) or "").strip().strip('"“”')
        except Exception:
            rw = ""
        if rw and rw != sent and len(rw) >= 4:
            new = new.replace(sent, rw, 1)
            done += 1
    after = len(find_cross_chapter_repetitions(new, prior_texts, n=n, allow=allow))
    return {"prose": new, "rewritten": done, "before": before, "after": after}


_EDGE = re.compile(r'^[\s"\'“”‘’「」『』,，、:：;；…—]+|[\s"\'“”‘’「」『』,，、:：;；…—]+$')
_HAS_CJK = re.compile(r'[一-鿿]')


def find_structural_repeats(text: str, min_anaphora: int = 4, max_short: int = 4) -> list[dict]:
    """排比开头(同3字开头≥min_anaphora句)+ 单字/极短断句滥用。字面 n-gram 查不到这些。"""
    from collections import Counter
    raw = re.split(r"[。！？\n]+", text or "")
    sents = [t for t in (_EDGE.sub("", s) for s in raw) if t]
    out: list[dict] = []
    openers = Counter(s[:3] for s in sents if len(s) >= 4 and not _PUNCT_ONLY.match(s[:3]))
    for op, c in openers.items():
        if c >= min_anaphora:
            out.append({"phrase": f"{op}…(排比开头)", "count": c, "kind": "anaphora"})
    short = [s for s in sents if 1 <= len(s) <= 2 and _HAS_CJK.search(s)]
    if len(short) > max_short:
        out.append({"phrase": "单字/极短断句(如 " + "/".join(short[:5]) + ")", "count": len(short), "kind": "short"})
    return sorted(out, key=lambda x: -x["count"])[:8]


LUANSHI_PURPLE_SEEDS = [
    r"原来[^。！？\n]{0,30}(就|早就|从一开始|没的选|没得选)",
    r"从[^,，。\n]{1,18}那一刻起",
    r"像[^。！？\n]{0,12}[滴颗][^。！？\n]{0,8}眼泪",
    r"影子[被]?拉得很[长短]",
    r"(有些|有的)[^。！？\n,，]{0,14}(就再也|再也)[^。！？\n]{0,14}",
    r"他知道[，,][^。！？\n]{0,4}(回不去|没的选|不一样了)",
    r"走下去|刀山火海",
]

_PURPLE_PATS = LUANSHI_PURPLE_SEEDS
_PURPLE_RE = [re.compile(p) for p in _PURPLE_PATS]


def find_purple_prose(text: str, extra_patterns: list[str] | None = None) -> list[dict]:
    """升华/抒情/主题直陈句:替读者下结论、硬塞命运隐喻——冷笔大忌。生成后扫描+删。
    通用正则跨题材;题材专属升华句经 extra_patterns 注入(来自 craft_rule purple_regex)。"""
    pats = list(_PURPLE_RE) + [re.compile(p) for p in (extra_patterns or [])]
    out: list[dict] = []
    for s in re.split(r"(?<=[。！？\n])", text or ""):
        st = s.strip()
        if st and any(rx.search(st) for rx in pats):
            out.append({"phrase": st[:30], "kind": "purple"})
    return out


# 通用 AI 腔硬检(E1/E2,题材无关,来自 hermes-novel hard-checks)
_NOT_A_BUT_B = re.compile(r"不是.{1,15}——是")


def find_ai_tics(text: str) -> list[dict]:
    """E1 破折号全章>5;E2「不是A——是B」句式(LLM 最常见的伪深刻制造器)。"""
    out: list[dict] = []
    dash = (text or "").count("——")
    wc = len("".join((text or "").split()))
    if wc > 0 and dash * 1000 / wc > 2:
        out.append({"kind": "em_dash", "count": dash})
    for m in _NOT_A_BUT_B.finditer(text or ""):
        out.append({"kind": "not_a_but_b", "phrase": m.group(0)})
    return out


# 过度解释/过度饱和(留白引擎的确定性兜底;保守阈值,宁可漏不滥杀)
_EXPLAIN = ["这意味着", "也就是说", "换句话说", "正是因为", "说明了", "其实是", "无非是", "不过是", "正因如此"]
_EMO_LABEL = ["愤怒", "悲伤", "恐惧", "绝望", "痛苦", "欣喜", "喜悦", "忧伤", "焦虑", "孤独", "兴奋", "悲痛"]
_SIMILE_WORDS = ["仿佛", "如同", "宛如", "好似", "犹如"]            # 明确比喻词
_SIMILE_LIKE = re.compile(r"像[^,，。！？\n]{1,10}(一样|般|似的|似地)")  # "像…一样"精确模式,避开"好像/图像"


def find_oversaturation(text: str, per_k_explain: float = 3.0,
                        per_k_emo: float = 5.0, per_k_simile: float = 6.0) -> list[dict]:
    """过度解释/过度饱和检测(每千字密度超保守阈值)。留白引擎的确定性兜底。"""
    s = text or ""
    n = len("".join(s.split())) or 1
    k = n / 1000.0
    explain = sum(s.count(w) for w in _EXPLAIN)
    emo = sum(s.count(w) for w in _EMO_LABEL)
    simile = sum(s.count(w) for w in _SIMILE_WORDS) + len(_SIMILE_LIKE.findall(s))
    out: list[dict] = []
    for label, cnt, thr in (("explain", explain, per_k_explain),
                            ("emo_label", emo, per_k_emo),
                            ("simile", simile, per_k_simile)):
        if cnt / k > thr:
            out.append({"kind": label, "count": cnt, "per_k": round(cnt / k, 1)})
    return out


def quality_flags(text: str, extra_patterns: list[str] | None = None) -> dict:
    """聚合五类确定性质检(渲染层兜底)。extra_patterns 来自本书 craft_rule purple_regex。"""
    return {
        "repetition": find_repetitions(text),
        "structural": find_structural_repeats(text),
        "purple": find_purple_prose(text, extra_patterns),
        "ai_tics": find_ai_tics(text),
        "oversaturation": find_oversaturation(text),
    }


# ==== LLM 语义判官(纪律闸)——确定性检测的盲区:双高潮/声音崩/解说倾泻/知识泄露 ====
def build_discipline_prompt(text: str, brief: str = "", known: dict | None = None) -> str:
    kb = ""
    if known:
        lines = "\n".join(f"  · {who} 只知道:{('、'.join(facts[:8]) or '(仅其私密内核)')}"
                          for who, facts in known.items())
        kb = ("\n\n【各角色截至本章已知(判 knowledge_leak 的事实依据;角色说出此清单之外的他人私密=泄露)】\n"
              + lines)
    return (
        "你是叙事结构【纪律判官】。下面是一章志怪小说。本章的命题/纪律要求:\n" +
        (brief or "(默认:乱世铜炉式克制——单一戏剧主线、不偷跑后续章剧情、terse 角色不大段独白、不解说倾泻)") +
        "\n\n判定是否违反以下纪律(任一即违规):\n"
        "① double_climax:出现第二场打斗/救援/开挂,或偷跑了本不属于本章的后续剧情、凭空发明新登场角色;\n"
        "② voice_collapse:声细如蚊/半截就断的 terse 角色崩成大段流畅独白、系统结算音、或与主角同温;\n"
        "③ exposition_dump:大段身世/前史/规则的集中倾泻(本该零星渗出);\n"
        "④ knowledge_leak:某角色说出或表现出知晓【其视角不可能知道】的他人私密信息。\n"
        "若违规,找出正文里【复发/穿帮开始的前一句】(从这句之后整段都该砍掉),逐字填入 cut_after。\n"
        '只输出一行 JSON:{"ok": true/false, "violations": ["double_climax"...], "cut_after": "复发前最后一句的原文逐字,守纪则空"}。'
        + kb + "\n\n【正文】\n" + text)


def parse_discipline(reply: str) -> dict:
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        d = json.loads(m.group(0)) if m else {}
        return {"ok": bool(d.get("ok", True)), "violations": list(d.get("violations") or []),
                "cut_after": (d.get("cut_after") or "").strip()}
    except Exception as e:
        _log.warning("parse_discipline 失败,纪律默认放行: %s | reply[:120]=%r", e, (reply or "")[:120])
        return {"ok": True, "violations": [], "cut_after": ""}   # 解析失败不阻断(fail-open)


def discipline_truncate(text: str, brief: str, complete_fn, known: dict | None = None) -> dict:
    """判定违规→复发点靠后(留≥40%)则截到复发点;复发太早只标记不砍(交回重生)。"""
    v = parse_discipline(complete_fn(build_discipline_prompt(text, brief, known)))
    if v["ok"] or not v["cut_after"]:
        return {"text": text, "violations": v["violations"], "changed": False}
    idx = text.find(v["cut_after"])
    if idx < 0:
        return {"text": text, "violations": v["violations"], "changed": False}
    cut = text[:idx + len(v["cut_after"])]
    if len(cut) < len(text) * 0.4:
        return {"text": text, "violations": v["violations"], "changed": False, "cut_after": v["cut_after"]}
    return {"text": cut, "violations": v["violations"], "changed": True}


# ==== 知识账本抽取(定稿时抽"本章谁新知道什么/做了什么",喂单一真相源)====
def build_knowledge_extract_prompt(prose: str) -> str:
    return (
        "读下面一章小说正文,抽取本章【各角色新知道了什么(learned)、做了什么且被谁看见(did)】——"
        "用于维护'谁知道什么'的知识账本(防后续章里某角色说出他视角不可能知道的信息)。"
        "再抽【voice_shift:哪些角色这章经历了可能改变其说话方式/声音的重大事件(创伤/背叛/重大转折/身份剧变)】——"
        "只列谁+什么事,不要替他写新独白。\n"
        '只输出一行 JSON:{"learned":[{"who":角色名,"fact":新知道的事(短句)}],'
        '"did":[{"who":角色名,"action":所为(短句),"seen_by":[在场看见的角色名]}],'
        '"voice_shift":[{"who":角色名,"reason":重大事件(短句)}]}。\n\n'
        "【正文】\n" + prose)


def parse_knowledge_delta(reply: str) -> dict | None:
    """解析 LLM 回复的知识 delta JSON。
    成功:返回 {"learned":..., "did":..., "voice_shift":...}(三字段均为 list)。
    失败(坏 JSON / 截断 / 无 {} 匹配):返回 None——调用方据此跳过 purge,防止数据丢失。"""
    try:
        m = re.search(r"\{.*\}", reply or "", re.S)
        if not m:
            _log.warning("parse_knowledge_delta 无 JSON 块,知识不回写: reply[:120]=%r", (reply or "")[:120])
            return None
        d = json.loads(m.group(0))
        return {"learned": list(d.get("learned") or []), "did": list(d.get("did") or []),
                "voice_shift": list(d.get("voice_shift") or [])}
    except Exception as e:
        _log.warning("parse_knowledge_delta 失败,知识不回写: %s | reply[:120]=%r", e, (reply or "")[:120])
        return None

# part 02_repetition (shared namespace; do not import standalone)
def find_repetitions(text: str, n: int = 8, min_count: int = 3, top: int = 10) -> list[dict]:
    """长度≥n、出现≥min_count 次的子串(去重叠,保留最长代表)。跨段复读是单遍长程生成典型病。
    引号内(台词/弹幕)豁免——体裁正常形态,只判叙述层复读。"""
    from collections import Counter
    text = _strip_quoted(text)
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
            if re.search(r"[一-鿿]", s[i:i + n]) and not _PUNCT_ONLY.match(s[i:i + n])
            # 跨越句末标点的拼接片段（如“。季棠从袖中摸出”）既不是完整可读短语，
            # 也无法映射回 cross_repetition_sentences 的单句改写目标。
            and not any(p in s[i:i + n] for p in "。！？\n")
            # 说话人标签跨越引号边界（如 “。”沈砚说。季棠）不是可读复读，
            # 真正的台词内容仍会由完全落在引号内部的 n-gram 参与比对。
            and not any(q in s[i:i + n] for q in '“”"')}


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
                              n: int = 8, allow: set[str] | None = None,
                              max_targets: int | None = None) -> dict:
    """确定性事后跨章改写——系统哲学:'prompt 规则治不了已生成文本,确定性扫描+定向[改]才拦得住'。

    1) 确定性定位含跨章复读的句子;2) 逐句调 complete_fn 定向改写(换措辞/感官/句式,保意保限知);
    3) 字符串替换回原文。比'prompt 预防'可靠:不依赖模型记住上百条禁用词,只精准改犯规句。
    返回 {prose, rewritten, before, after}。complete_fn(prompt, system)->str。
    """
    before = len(find_cross_chapter_repetitions(text, prior_texts, n=n, allow=allow))
    targets = cross_repetition_sentences(text, prior_texts, n=n, allow=allow)
    if max_targets is not None:
        targets = targets[:max(0, int(max_targets))]
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
    # 与章内精修同一质量门：未净减少时整体回退，不能把只改了表面措辞的正文写回。
    if done == 0 or after >= before:
        return {"prose": text, "rewritten": 0, "before": before, "after": before}
    return {"prose": new, "rewritten": done, "before": before, "after": after}


def find_near_duplicate_paragraphs(text: str, sim: float | None = None, min_len: int | None = None,
                                   allow: set[str] | None = None) -> list[dict]:
    """近似(非逐字)重复段落/句子检测——补 find_repetitions(精确8gram)/find_duplicate_lines
    (精确整句)之间的盲区。分幕拼接处常把上一幕结尾的画面换几个字重写一遍(逐字检测器全查不到);
    min_len=25 兼顾段落级与句子级近似(实证:结局章两相邻句"他躺在自己的棺材里…前半全同后半改几字"
    落在段落级 40 阈值外,漏检)。切段(按行),对够长的段两两算字符级相似度(difflib,对'大段逐字
    相同+局部改字'敏感,优于 n-gram Jaccard),超阈值则后一段判为近似;含 allow 母题词的段落对放行。
    返回 [{"paragraph","sim","dup_of"}](后段原文)。"""
    from difflib import SequenceMatcher
    sim = sim if sim is not None else _th("craft.near_dup_sim")
    min_len = min_len if min_len is not None else _th("craft.near_dup_min_len")
    paras = [p.strip() for p in re.split(r"\n+", text or "") if len(p.strip()) >= min_len]
    out: list[dict] = []
    flagged: set[int] = set()
    for j in range(len(paras)):
        if j in flagged:
            continue
        pj = paras[j]
        for i in range(j):
            pi = paras[i]
            r = SequenceMatcher(None, pj, pi).ratio()
            if r >= sim and not (_is_allowed(pj, allow) or _is_allowed(pi, allow)):
                out.append({"paragraph": pj, "sim": round(r, 2), "dup_of": pi[:20]})
                flagged.add(j)
                break
    return out


def intra_repetition_sentences(text: str, allow: set[str] | None = None) -> list[dict]:
    """定位本章内需定向改写的问题句(章内治层的定位原语,与 cross_repetition_sentences 对称)。
    覆盖四类章内硬伤,每句附改写提示 hint:
      · repetition         同一 ≥8 字近字短语出现≥3 次 → 除首现句外,含它的句子标记改写
      · duplicate_lines    整句一字不差出现≥2 次 → 除首现外,后续标记改写
      · structural         连续排比开头(anaphora,前3字相同)→ 保留前2句,多余的标记改写打散
      · near_dup_paragraph 近似(非逐字)重复段落(分幕拼接盲区)→ 后段逐句标记改写
    统一切句(含 …)、在剥引号后的叙述层匹配(不误改台词)、全分支吃 allow 母题白名单。
    同一句被多类命中时只保留一条(先命中者优先),按出现顺序返回 [{"sentence","hint"}]。"""
    if not text:
        return []
    sents = [s for s in _INTRA_SENT_SPLIT.split(text) if s.strip()]
    marked: dict[str, str] = {}
    order: list[str] = []

    def _mark(sentence: str, hint: str):
        key = sentence.strip()
        if key and key not in marked:
            marked[key] = hint
            order.append(key)

    # ① 章内近字复读:在剥引号的叙述层匹配复读短语(不误改台词),保首现、改后续
    for rep in find_repetitions(text):
        phrase = rep.get("phrase", "")
        if not phrase or _is_allowed(phrase, allow):
            continue
        seen_first = False
        for s in sents:
            if phrase in re.sub(r"\s+", "", _strip_quoted(s)):
                if not seen_first:
                    seen_first = True
                    continue
                _mark(s, f"本句与前文重复了『{phrase}』,请换一种措辞/感官写法,不要逐字复用。")

    # ② 整句一字不差重复:保首现、改后续(过 allow,母题谶语/咒语不动)
    dup_lines = {d["line"] for d in find_duplicate_lines(text) if not _is_allowed(d["line"], allow)}
    if dup_lines:
        first_seen: set[str] = set()
        for s in sents:
            key = s.strip()
            if key in dup_lines:
                if key not in first_seen:
                    first_seen.add(key)
                    continue
                _mark(s, "本句与前文一字不差地重复了,请彻底改写成不同的表达,保持情节不变。")

    # ③ 排比开头堆砌:保前2、打散其余(op 过 allow,在剥引号的叙述层匹配)
    for x in (y for y in find_structural_repeats(text) if y.get("kind") == "anaphora"):
        op = x["phrase"].split("…")[0]
        if len(op) < 2 or _is_allowed(op, allow):
            continue
        kept = 0
        for s in sents:
            head = re.sub(r'^[\s"\'“”‘’「」『』,，、:：;；…—]+', "", _strip_quoted(s))[:len(op)]
            if head == op:
                if kept < 2:
                    kept += 1
                    continue
                _mark(s, f"本句与前几句都用『{op}』开头形成排比,请改用不同的句子开头打破排比,保持原意。")

    # ③b 短断句滥用：只有检测器已同时满足数量与密度阈值时才处理，避免干预正常节奏。
    if any(x.get("kind") == "short" for x in find_structural_repeats(text)):
        for s in sents:
            core = re.sub(r"[。！？…\s]+$", "", _EDGE.sub("", _strip_quoted(s)))
            if 1 <= len(core) <= 2 and _HAS_CJK.search(core):
                _mark(s, "本章短断句过密，请把这个动作/说话标签改成自然完整的叙述，保持情节不变。")

    # ④ 近似重复段落(分幕拼接盲区,S-005):后段逐句标记改写
    for nd in find_near_duplicate_paragraphs(text, allow=allow):
        for s in _INTRA_SENT_SPLIT.split(nd["paragraph"]):
            if len(s.strip()) >= 6:
                _mark(s, "本段与前文某段高度重复(仅换了几个字重写同一画面),请彻底改写成推进叙事的新内容或删繁。")

    # ④b 文风提示可定位到完整句，交给同一限知和净减少门改写，不能只报警不治理。
    for hit in find_purple_prose(text):
        phrase = str(hit.get("phrase") or "")
        for s in sents:
            if phrase and phrase in s:
                _mark(s, f"本句有过度修辞的文风提示「{phrase}」，请改得具体、克制，不新增事实。")
                break

    # ⑤ AI 腔:检测器给的是问题短语/符号，精修必须提升到完整句，才能在不改情节的
    # 前提下替换掉否定翻转、密集破折号等模式，而不是只在质检面板里报警。
    for sentence, bad in _ai_tic_rewrite_sentences(text, allow=allow):
        _mark(sentence, f"本句含AI腔模式「{bad}」,请改成直接、具体的叙述，保留情节与限知，不用否定翻转、破折号堆砌或公式化强调。")

    return [{"sentence": k, "hint": marked[k]} for k in order]


def rewrite_intra_chapter_issues(text: str, complete_fn, allow: set[str] | None = None,
                                 max_rounds: int = 2, max_targets: int | None = None) -> dict:
    """章内治层(与 rewrite_cross_repetitions 对称·章内维度):定位本章内 repetition/
    duplicate_lines/排比/近似重复段 的问题句 → 逐句定向改写(保意保限知保声音)→ 按句界替换回原文。

    长章(分幕拼接)易在章内自我复读/堆排比/换字重写同一画面,而 rewrite_cross_repetitions 只治
    跨章,二者互补。改写器强约束限知(绝不点破未揭示悬念)——改写同样可能泄密。迭代至多 max_rounds
    轮(排比一轮可能打散不尽)。**回滚门**:若改写后问题数未净减少(after≥before)则整体回退,绝不
    落一个更差的版本(review P1-2)。幂等:无问题原样返回、不调 LLM。返回 {prose,rewritten,before,after}。"""
    def _count(t: str) -> int:
        reps = len([r for r in find_repetitions(t) if not _is_allowed(r.get("phrase", ""), allow)])
        dups = len([d for d in find_duplicate_lines(t) if not _is_allowed(d.get("line", ""), allow)])
        struct = len([x for x in find_structural_repeats(t) if x.get("kind") == "anaphora"
                      and not _is_allowed(x["phrase"].split("…")[0], allow)])
        short = len([x for x in find_structural_repeats(t) if x.get("kind") == "short"])
        near = len(find_near_duplicate_paragraphs(t, allow=allow))
        purple = len(find_purple_prose(t))
        ai_tics = len(_ai_tic_rewrite_sentences(t, allow=allow))
        return reps + dups + struct + short + near + purple + ai_tics

    before = _count(text)
    if before == 0:
        return {"prose": text, "rewritten": 0, "before": 0, "after": 0}
    sysmsg = ("你是小说定向改写器。只改写给你的这一句:保持原意、情节、人物与上下文衔接完全不变;"
              "**严守限知视角——绝不添加视角人物此刻不知道的信息,绝不点破尚未向读者揭示的核心悬念/秘密**;"
              "保持冷笔克制的叙述声音,不堆辞藻、不抒情升华。按要求换措辞或句式。"
              "只输出改写后的这一句正文,不要引号、不要解释。")
    new = text
    done = 0
    remaining_targets = max(1, int(max_targets)) if max_targets is not None else None
    for _ in range(max(1, max_rounds)):
        targets = intra_repetition_sentences(new, allow=allow)
        if not targets:
            break
        # HTTP 端点按批次上限执行时，明确可保义改写的 AI 腔应优先于“排比开头”这类
        # 可能在台词/引号边界上无法安全替换的目标，确保每批都先产生可验证的净改善。
        targets.sort(key=lambda target: 0 if "AI腔模式" in target["hint"] else 1)
        if remaining_targets is not None:
            targets = targets[:remaining_targets]
        changed = False
        for t in targets:
            sent = t["sentence"]
            if sent not in new:
                continue
            prompt = f"{t['hint']}\n\n待改写的句子:{sent}"
            try:
                rw = (complete_fn(prompt, sysmsg) or "").strip().strip('"“”')
            except Exception:
                rw = ""
            if rw and rw != sent and len(rw) >= 4 and _valid_rewrite(rw, sent):
                replaced = _replace_whole_sentence(new, sent, rw)
                if replaced != new:
                    new = replaced
                    done += 1
                    changed = True
        if remaining_targets is not None:
            remaining_targets -= len(targets)
            if remaining_targets <= 0:
                break
        if not changed:
            break
    after = _count(new)
    # 回滚门(review P1-2):问题数没有净减少 → 整体回退,绝不落更差的版本
    if done == 0 or after >= before:
        return {"prose": text, "rewritten": 0, "before": before, "after": before}
    return {"prose": new, "rewritten": done, "before": before, "after": after}



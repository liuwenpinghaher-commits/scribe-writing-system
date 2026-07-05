"""北极星方案任务9 · QD 多样性档案(蓝图 §5 P1 提前项,防"loop 打磨磨平个性")。

章级文体特征六元组(全部纯确定性:正则+计数,零 LLM)+ 分布单调告警;
特征轴同时供选择环(任务11)当行为空间(取互相关最低的 2-3 轴)。

口径出处(调研报告,自定项如实标注):
- 引号配对切分=公共前置(Eisenberg&Finlayson:不去引号 POV 判定掉 13pt);
- 断句:句末点号{。!?…}(GB/T 15834-2011,分号冒号不断)+引号后断(HarvestText);
- 对话占比=配对引号内字符比(Language Log 法);同作者可漂 30pt → 只做书内自比告警;
- MTLD 字级 0.72 阈(英文经验值,中文字级适用性未查到先例——自定,面板标注);
- 虚词表:红楼梦考证传统(陈炳藻 14/李贤平 47)取常用 24 字;
- 告警:SPC 连续 8 点同侧 + 基线偏离 15pt(创作域无先例,工业规则移植——自定嫁接)。
"""
from __future__ import annotations

import math
import re

_QUOTE_PAIRS = {"“": "”", "「": "」", "『": "』"}
_QUOTE_CLOSE = set(_QUOTE_PAIRS.values())
_SENT_END = "。!?"
_VISIBLE_RE = re.compile(r"[一-鿿A-Za-z0-9]")
# 虚词表(字级,红楼梦研究传统常用集;字级绕开分词依赖)
FUNC_WORDS = ("的", "地", "得", "了", "着", "过", "就", "都", "也", "又", "才",
              "把", "被", "让", "从", "向", "对", "于", "而", "与", "及", "或",
              "在", "是")
_FIRST_PERSON_RE = re.compile(r"我们|我|咱")
_PSYCH_RE = re.compile(r"心想|暗道|暗想|心道|寻思|琢磨|知道|明白|觉得|意识到")
_PUNCT_KEYS = {"comma": ",,、", "period": "。", "exclaim_q": "!?!?",
               "ellipsis": "…", "dash": "—", "quote": "“”「」『』\"'"}

CV_FLAT_RUN = 8          # SPC Western Electric/Nelson 连续 8 点同侧(移植)
DIALOGUE_JUMP_PT = 0.15  # 对话占比偏离书内基线告警线(15pt,自定)


def split_quoted(text: str) -> tuple[str, int, int]:
    """引号配对切分:返回 (narration 叙述层文本, 引号内字符数, 总字符数)。
    栈式配对;不平衡(漏闭合)时残缺段并回叙述层(奇偶回退,Language Log 先例)。"""
    s = text or ""
    narration_parts: list[str] = []
    quoted_chars = 0
    buf: list[str] = []
    open_q: str | None = None
    qbuf: list[str] = []
    for ch in s:
        if open_q is None:
            if ch in _QUOTE_PAIRS:
                open_q = ch
                qbuf = []
            else:
                buf.append(ch)
        else:
            if ch == _QUOTE_PAIRS[open_q]:
                quoted_chars += len(qbuf)
                open_q = None
                qbuf = []
            else:
                qbuf.append(ch)
    if open_q is not None:   # 漏闭合:回退并入叙述层
        buf.extend(qbuf)
    narration_parts.append("".join(buf))
    return "".join(narration_parts), quoted_chars, len(s)


def sentence_lengths(text: str) -> list[int]:
    """按国标句末点号断句(分号冒号不断);句末标点后紧跟后引号 → 引号后断
    (HarvestText 规则)。句长=去空白可见字符数;空句剔除。"""
    s = text or ""
    sents: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        buf.append(ch)
        if ch in _SENT_END or ch == "…":
            j = i + 1
            while j < len(s) and s[j] in "…!?。":   # 连续标点(如……/?!)并入
                buf.append(s[j])
                j += 1
            while j < len(s) and s[j] in _QUOTE_CLOSE:   # 引号后断
                buf.append(s[j])
                j += 1
            sents.append("".join(buf))
            buf = []
            i = j
        else:
            i += 1
    if buf:
        sents.append("".join(buf))
    out = []
    for x in sents:
        n = len(_VISIBLE_RE.findall(x))
        if n:
            out.append(n)
    return out


def _mtld_char(chars: list[str], threshold: float = 0.72) -> float:
    """字级 MTLD(McCarthy & Jarvis 2010,前后向平均)。中文字级适用性属自定口径。"""
    def _one_dir(seq: list[str]) -> float:
        factors = 0.0
        types: set[str] = set()
        tokens = 0
        for c in seq:
            tokens += 1
            types.add(c)
            ttr = len(types) / tokens
            if ttr <= threshold:
                factors += 1
                types = set()
                tokens = 0
        if tokens:
            ttr = len(types) / tokens if tokens else 1.0
            if ttr < 1.0:
                factors += (1 - ttr) / (1 - threshold)
        return len(seq) / factors if factors else float(len(seq))
    if len(chars) < 20:
        return 0.0
    return round((_one_dir(chars) + _one_dir(list(reversed(chars)))) / 2, 2)


def chapter_style_profile(text: str, focalizer: str | None = None) -> dict:
    """章级文体六元组(纯确定性)。pov.mode:叙述层第一人称率 >1/千字 → first
    (代词计数近乎定义性信号,F1 0.928 先例);psych_per_k 供限知漂移参考(自定口径)。"""
    narration, quoted_chars, total = split_quoted(text)
    lens = sentence_lengths(text)
    mean = (sum(lens) / len(lens)) if lens else 0.0
    var = (sum((x - mean) ** 2 for x in lens) / len(lens)) if lens else 0.0
    cv = (math.sqrt(var) / mean) if mean else 0.0
    visible = _VISIBLE_RE.findall(text or "")
    k = (len(visible) / 1000.0) or 1e-9
    nar_visible_n = len(_VISIBLE_RE.findall(narration)) or 1
    nk = nar_visible_n / 1000.0
    fp = len(_FIRST_PERSON_RE.findall(narration))
    psych = len(_PSYCH_RE.findall(narration))
    func_vec = {w: round(((text or "").count(w)) / k, 3) for w in FUNC_WORDS}
    punct = {name: round(sum((text or "").count(c) for c in chars) / k, 3)
             for name, chars in _PUNCT_KEYS.items()}
    return {
        "sent_cv": round(cv, 4),
        "sent_mean": round(mean, 2),
        "sent_n": len(lens),
        "dialogue_ratio": round(quoted_chars / total, 4) if total else 0.0,
        "mtld_char": _mtld_char(visible),
        "func_word_per_k": func_vec,
        "punct_per_k": punct,
        "pov": {"mode": "first" if (fp / nk if nk else 0) > 1.0 else "third",
                "declared_focalizer": focalizer or "",   # 与机械信号交叉校验用(元数据声明)
                "first_person_per_k": round(fp / nk, 3) if nk else 0.0,
                "psych_per_k": round(psych / nk, 3) if nk else 0.0},
    }


def style_drift_alerts(profiles: list[dict]) -> list[dict]:
    """分布单调告警(书内自比;数据不足不硬判——没凑够窗口就不说话,绝不假绿):
    ① sent_cv_flattening:最近 CV_FLAT_RUN 章句长 CV 全部低于全书中位(SPC 连续
      同侧移植,创作域无先例属自定嫁接);
    ② dialogue_ratio_jump:最新章对话占比偏离前段均值 > DIALOGUE_JUMP_PT
      (≥4 章才判;同作者可漂 30pt,故只做书内基线自比)。
    告警只进面板,不进任何门禁(QD 是监控不是闸门)。"""
    alerts: list[dict] = []
    ps = sorted(profiles or [], key=lambda p: p.get("seq") or 0)
    cvs = [p.get("sent_cv") for p in ps if p.get("sent_cv") is not None]
    # SPC 语义:中心线取基线期(排除近期窗口)——若把塌平段算进中位,
    # 中心线会被拉低到塌平值,漂移永远测不出(实现时踩过的坑,勿回退)。
    if len(cvs) >= CV_FLAT_RUN + 3:
        base = cvs[:-CV_FLAT_RUN]
        med = sorted(base)[len(base) // 2]
        recent = cvs[-CV_FLAT_RUN:]
        if all(c < med for c in recent):
            alerts.append({
                "rule": "sent_cv_flattening",
                "detail": f"最近 {CV_FLAT_RUN} 章句长 CV 全部低于全书中位 {med:.3f}(疑似节拍磨平)",
                "note": "SPC 连续同侧规则移植,创作域无先例,阈值属自定口径——仅供人判断"})
    ratios = [p.get("dialogue_ratio") for p in ps if p.get("dialogue_ratio") is not None]
    if len(ratios) >= 4:
        base = sum(ratios[:-1]) / len(ratios[:-1])
        if abs(ratios[-1] - base) > DIALOGUE_JUMP_PT:
            alerts.append({
                "rule": "dialogue_ratio_jump",
                "detail": (f"最新章对话占比 {ratios[-1]:.2f} 偏离书内基线 {base:.2f} "
                           f"超 {DIALOGUE_JUMP_PT:.0%}"),
                "note": "书内自比口径(同作者生涯可漂 30pt,不设绝对带)——仅供人判断"})
    return alerts

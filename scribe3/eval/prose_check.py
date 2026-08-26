"""Distribution monitor for sample scenes. Read-only. Zero LLM.

**This is not a gate.** Four rounds showed that any threshold the model can see
turns into a template: a ≤1 simile line produced zero similes, a ≥30% redundancy
line produced shredded four-word turns, a ≥15% long-turn line produced
info-dumping monologues, and the phatic whitelist below still literally contains
「你吃了没」— the very line three samples shared when the author called them
identical. Surface statistics cannot steer token-by-token sampling; they only
tell you how far a draft sits from the two reference books.

So: no pass/fail in the report, no thresholds in the prompt, no wiring into the
生成 path. The author is the only verdict. `check_prose` keeps boolean fields
for regression pins only.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from scribe3.eval.motif_split import BLACKLIST_TERMS

CHECK_KEYWORDS: tuple[str, ...] = (
    "明喻密度",
    "句长标准差",
    "26字以上",
    "最长一句",
    "对话冗余",
    "答非所问",
    "开篇事件",
    "结尾总结",
    "跨篇重复",
    "内心活动占比",
    "职业词命中",
    "角色句长",
    "话说一半",
    "无信息回合",
    "不接话茬",
    "执念复现",
    "物件复现",
    "卡片原句",
    "少用「像",
    "允许废话",
    "不要每句都推进",
    "前三百字必须",
    "不是……而是",
    "改不回去的事",
)

# 只认真明喻。旧式 `[像如]同?...` 会吞掉「如果 / 如此 / 如今」，把铜炉算成
# 2.69/千字；按本式重算是 0.80，诡秘 1.07。区间据此下调。
_SIMILE = re.compile(
    r"好像|好似|仿佛|犹如|宛如|恰似|如同"
    r"|(?<![图想录画影偶雕头肖群音])像(?![素样话章框机册])"
)
_Q = re.compile(r"[「『“\"]([^」』”\"]+)[」』”\"]")
_NOT_BUT = re.compile(r"不是.{0,24}而是|不是为了|像一个.{0,20}那样")
_PROCESS = re.compile(r"小票|硬币|第[一二三四五六]遍|一遍|数的是|填了|格子")
_IRREVERSIBLE = re.compile(
    r"开闸|焊死|划掉|不见了|伸进|卡死|泄压|塞进|撞见|失灵|停电|砸|碎了|打开门"
)
_FILLER = re.compile(r"^(嗯|啊|哦|额|那个|不是这个|等一下|你听我说|我倒|随便|行吧|知道了)[。！？…]*$")
_INTERRUPT = re.compile(r"——|…$|……$|你听我说|话没说完|打断")
_NONANSWER = re.compile(r"^(对了|我想起来|你吃了|今天天气|我跟你讲|说起来)")
_HALF = re.compile(r"(……|…|——)\s*$")
_TRIVIAL = frozenset({"嗯", "好", "对", "是", "哦", "啊", "行", "没有"})
# 纯寒暄 / 纯应声：不带任何情节信息的回合
_PHATIC = re.compile(
    r"^(哎|哟|嗯|哦|啊|唉|行|好|对|是|没有|知道了|还那样|回来了|走了|"
    r"你吃了|吃了没|你忙|几家|身体|多大了|下班|辛苦)"
)

SIMILE_MIN, SIMILE_MAX = 0.4, 1.5  # 铜炉 0.83 / 诡秘 1.07（同一正则重算）
SD_MIN = 12.0
MAX_LEN_MIN = 60
PHATIC_MIN = 0.12
LONG_TURN = 30  # 触发「不接话茬」判定的台词长度
IGNORE_GAP = 40  # 长台词后至少这么多字的叙述才算没人接

# 两本参照的实测分布，用本文件同一套函数算出，供对照，不作阈值。
REF: dict[str, dict[str, float]] = {
    "乱世铜炉": {
        "simile_per_k": 0.83,
        "sd": 41.7,
        "max_len": 1729,
        "phatic_ratio": 0.203,
        "ignored_per_k": 109.8,
        "half_ratio": 0.078,
    },
    "诡秘之主": {
        "simile_per_k": 1.07,
        "sd": 41.9,
        "max_len": 1545,
        "phatic_ratio": 0.131,
        "ignored_per_k": 48.9,
        "half_ratio": 0.063,
    },
}

_METRIC_LABELS: tuple[tuple[str, str, str], ...] = (
    ("simile_per_k", "明喻 /千字", "{:.2f}"),
    ("sd", "对白句长标准差", "{:.1f}"),
    ("max_len", "最长一句", "{:.0f}"),
    ("phatic_ratio", "无信息回合", "{:.0%}"),
    ("ignored_per_k", "不接话茬 /千回合", "{:.0f}"),
    ("half_ratio", "话说一半", "{:.0%}"),
)


def extract_prose(md: str) -> str:
    if "## 正文" in md:
        body = md.split("## 正文", 1)[1]
        if "## " in body:
            body = body.split("## ", 1)[0]
        return body.strip()
    return md.strip()


def _chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def _turns(prose: str) -> list[str]:
    return [m.group(1).strip() for m in _Q.finditer(prose)]


def _stdev(nums: list[float]) -> float:
    if len(nums) < 2:
        return 0.0
    mean = sum(nums) / len(nums)
    var = sum((x - mean) ** 2 for x in nums) / len(nums)
    return math.sqrt(var)


def _echoes(cur: str, prev: str, k: int = 3) -> bool:
    """当前回合是否在复述上一回合（≥k 字连续重叠）。真实对话大量如此。"""
    return any(cur[i : i + k] in prev for i in range(len(cur) - k + 1))


def _phatic_turns(turns: list[str]) -> list[str]:
    out = []
    for i, t in enumerate(turns):
        prev = turns[i - 1] if i else ""
        if _PHATIC.match(t) or (prev and _echoes(t, prev)):
            out.append(t)
    return out


def _ignored_turns(prose: str) -> int:
    """一方说完长台词，另一方不接话、径自去做别的事，中间隔着叙述。"""
    ms = list(_Q.finditer(prose))
    hits = 0
    for cur, nxt in zip(ms, ms[1:]):
        if len(cur.group(1).strip()) < LONG_TURN:
            continue
        if _chars(prose[cur.end() : nxt.start()]) >= IGNORE_GAP:
            hits += 1
    return hits


def _dialogue_stats(prose: str) -> dict:
    turns = _turns(prose)
    lens = [len(t) for t in turns]
    n = len(lens)
    return {
        "turns": turns,
        "n": n,
        "sd": _stdev([float(x) for x in lens]) if n else 0.0,
        "long_ratio": (sum(1 for x in lens if x >= 26) / n) if n else 0.0,
        "max_len": max(lens) if lens else 0,
    }


def check_prose_v3(md: str) -> dict:
    prose = extract_prose(md)
    n = max(1, _chars(prose))
    similes = _SIMILE.findall(prose)
    simile_per_k = len(similes) / (n / 1000)
    turns = _turns(prose)
    filler = [t for t in turns if _FILLER.match(t) or len(t) <= 4]
    redun = (len(filler) / len(turns)) if turns else 0.0
    interrupts = _INTERRUPT.findall(prose)
    nonanswers = [t for t in turns if _NONANSWER.match(t)]
    qa_hits = len(interrupts) + len(nonanswers)
    head = re.sub(r"\s+", "", prose)[:300]
    tail = re.sub(r"\s+", "", prose)[-150:]
    open_ok = bool(_IRREVERSIBLE.search(head)) and not _PROCESS.search(head)
    end_ok = _NOT_BUT.search(tail) is None
    motif_hits = [t for t in BLACKLIST_TERMS if t in prose]
    checks = [
        {"name": "明喻密度", "ok": simile_per_k <= 1.0, "detail": f"{simile_per_k:.2f}/千字，v3线≤1"},
        {"name": "对话冗余率", "ok": redun >= 0.30, "detail": f"{redun:.0%}，v3线≥30%"},
        {"name": "答非所问", "ok": qa_hits >= 2, "detail": f"{qa_hits} 处"},
        {"name": "开篇事件", "ok": open_ok, "detail": "前300字不可逆且非流程"},
        {"name": "结尾总结句", "ok": end_ok, "detail": "最后150字无点题"},
        {"name": "母题黑名单", "ok": not motif_hits, "detail": "命中 " + ("、".join(motif_hits) if motif_hits else "无")},
    ]
    return {
        "n_chars": n,
        "n_red": sum(1 for c in checks if not c["ok"]),
        "n_ok": sum(1 for c in checks if c["ok"]),
        "checks": checks,
    }


def check_prose(md: str, premise: dict | None = None) -> dict:
    prose = extract_prose(md)
    n = max(1, _chars(prose))
    similes = list(_SIMILE.finditer(prose))
    simile_per_k = len(similes) / (n / 1000)
    d = _dialogue_stats(prose)
    tail = re.sub(r"\s+", "", prose)[-150:]
    motif_hits = [t for t in BLACKLIST_TERMS if t in prose]
    phatic = _phatic_turns(d["turns"])
    phatic_ratio = (len(phatic) / d["n"]) if d["n"] else 0.0
    ignored = _ignored_turns(prose)
    half = sum(1 for t in d["turns"] if _HALF.search(t))
    end_simile = 0
    for para in re.split(r"\n\s*\n", prose):
        p = para.strip()
        if not p:
            continue
        last = p.split("。")[-1]
        if _SIMILE.search(last) and ("那样" in last or "不是" in last):
            end_simile += 1
    jargon_ok, detail_j = True, "无语域卡"
    tic_ok, detail_t = True, "无语域卡"
    prop_ok, detail_p = True, "无语域卡"
    card_ok, detail_c = True, "无语域卡"
    if premise and premise.get("cast"):
        cast = premise["cast"]
        hits_roles = sum(
            1 for c in cast if sum(1 for w in c.get("jargon") or [] if w in prose) >= 3
        )
        jargon_ok = hits_roles >= 2
        detail_j = f"{hits_roles} 个角色各≥3 职业词"

        tics = [(c.get("name"), c.get("tic")) for c in cast if c.get("tic")]
        recur = [nm for nm, t in tics if prose.count(t) >= 2]
        tic_ok = not tics or len(recur) >= 2
        detail_t = f"{len(recur)}/{len(tics)} 个角色执念复现≥2 次"

        props = premise.get("props") or []
        back = [p for p in props if prose.count(p) >= 2]
        prop_ok = not props or len(back) == len(props)
        missing = [p for p in props if p not in back]
        detail_p = f"{len(back)}/{len(props)} 件物件复现" + (
            f"；只出现一次：{'、'.join(missing)}" if missing else ""
        )

        # 卡片上的例句被原样搬进正文 = 又一次照抄检查表
        lifted = [c["catchphrase"] for c in cast if c.get("catchphrase") and c["catchphrase"] in prose]
        card_ok = not lifted
        detail_c = "原样搬运 " + ("、".join(lifted) if lifted else "无")

    checks = [
        {
            "name": "明喻密度",
            "ok": SIMILE_MIN <= simile_per_k <= SIMILE_MAX,
            "detail": f"{simile_per_k:.2f}/千字，区间 {SIMILE_MIN}-{SIMILE_MAX}（原文 0.80/1.07）",
        },
        {
            "name": "明喻位置",
            "ok": end_simile == 0,
            "detail": f"段末总结位明喻 {end_simile}，线=0",
        },
        {
            "name": "对白句长标准差",
            "ok": d["sd"] >= SD_MIN,
            "detail": f"SD={d['sd']:.1f}，线≥{SD_MIN:.0f}",
        },
        {
            "name": "最长一句对白",
            "ok": d["max_len"] >= MAX_LEN_MIN,
            "detail": f"{d['max_len']} 字，线≥{MAX_LEN_MIN}",
        },
        {
            "name": "无信息回合",
            "ok": phatic_ratio >= PHATIC_MIN,
            "detail": f"{phatic_ratio:.0%}（寒暄/应声/复述对方），线≥{PHATIC_MIN:.0%}",
        },
        {
            "name": "不接话茬",
            "ok": ignored >= 1,
            "detail": f"{ignored} 处：一方说完长台词，另一方径自做别的",
        },
        {
            "name": "话说一半",
            "ok": half >= 1,
            "detail": f"省略号/破折号收尾 {half} 处",
        },
        {
            "name": "职业词命中",
            "ok": jargon_ok,
            "detail": detail_j,
        },
        {
            "name": "执念复现",
            "ok": tic_ok,
            "detail": detail_t,
        },
        {
            "name": "物件复现",
            "ok": prop_ok,
            "detail": detail_p,
        },
        {
            "name": "卡片原句",
            "ok": card_ok,
            "detail": detail_c,
        },
        {
            "name": "结尾总结句",
            "ok": _NOT_BUT.search(tail) is None,
            "detail": "最后150字无点题句",
        },
        {
            "name": "母题黑名单",
            "ok": not motif_hits,
            "detail": "命中 " + ("、".join(motif_hits) if motif_hits else "无"),
        },
    ]
    return {
        "n_chars": n,
        "n_red": sum(1 for c in checks if not c["ok"]),
        "n_ok": sum(1 for c in checks if c["ok"]),
        "checks": checks,
        "dialogue": {k: d[k] for k in ("n", "sd", "long_ratio", "max_len")},
        "metrics": {
            "simile_per_k": simile_per_k,
            "sd": d["sd"],
            "max_len": float(d["max_len"]),
            "phatic_ratio": phatic_ratio,
            "ignored_per_k": (ignored / d["n"] * 1000) if d["n"] else 0.0,
            "half_ratio": (half / d["n"]) if d["n"] else 0.0,
        },
        "facts": {
            "母题黑名单命中": "、".join(motif_hits) or "无",
            "卡片例句原样出现": detail_c,
            "角色执念复现": detail_t,
            "物件复现": detail_p,
            "职业词命中": detail_j,
        },
    }


def _shared_quotes(texts: list[str]) -> list[str]:
    sets = []
    for md in texts:
        turns = {t for t in _turns(extract_prose(md)) if t not in _TRIVIAL and len(t) >= 2}
        sets.append(turns)
    shared: set[str] = set()
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            shared |= sets[i] & sets[j]
    return sorted(shared)


def check_corpus(texts: list[str]) -> dict:
    singles = [check_prose(t) for t in texts]
    sds = [s["dialogue"]["sd"] for s in singles]
    longs = [s["dialogue"]["long_ratio"] for s in singles]
    maxes = [s["dialogue"]["max_len"] for s in singles]
    similes = []
    for t in texts:
        prose = extract_prose(t)
        n = max(1, _chars(prose))
        similes.append(len(_SIMILE.findall(prose)) / (n / 1000))
    shared = _shared_quotes(texts)
    checks = [
        {
            "name": "对白句长标准差",
            "ok": min(sds) >= SD_MIN,
            "detail": f"各篇 SD={','.join(f'{x:.1f}' for x in sds)}，线≥{SD_MIN:.0f}",
        },
        {
            "name": "最长一句对白",
            "ok": min(maxes) >= MAX_LEN_MIN,
            "detail": f"各篇最长 {maxes}，线≥{MAX_LEN_MIN}",
        },
        {
            "name": "明喻密度",
            "ok": all(SIMILE_MIN <= x <= SIMILE_MAX for x in similes),
            "detail": f"各篇 {','.join(f'{x:.2f}' for x in similes)}，区间 {SIMILE_MIN}-{SIMILE_MAX}",
        },
        {
            "name": "跨篇重复对白",
            "ok": len(shared) == 0,
            "detail": "重复 " + ("、".join(shared[:8]) if shared else "无"),
        },
    ]
    return {
        "n_red": sum(1 for c in checks if not c["ok"]),
        "n_ok": sum(1 for c in checks if c["ok"]),
        "checks": checks,
        "shared": shared,
        "singles": singles,
    }


def format_report(report: dict) -> str:
    """对照表，无判定。

    刻意不输出「过/红」与总分：只要报告里有及格线，人就会去追全绿，
    监控迟早又变回门禁——前四轮都是这么塌的。
    """
    m = report.get("metrics") or {}
    a, b = REF["乱世铜炉"], REF["诡秘之主"]
    lines = [
        "## 分布对照（只读监控 · 不作判据 · 不进提示）",
        "",
        "| 项 | 本稿 | 乱世铜炉 | 诡秘之主 |",
        "|---|---|---|---|",
    ]
    for key, label, fmt in _METRIC_LABELS:
        if key not in m:
            continue
        lines.append(
            f"| {label} | {fmt.format(m[key])} | {fmt.format(a[key])} | {fmt.format(b[key])} |"
        )
    facts = report.get("facts") or {}
    if facts:
        lines += ["", "事实项（陈述，不是评分）：", ""]
        lines += [f"- {k}：{v}" for k, v in facts.items()]
    lines += [
        "",
        "数值本身不是好坏，离参照近也不等于写得好。作者判断是唯一裁决。",
    ]
    return "\n".join(lines)


_DRAW = re.compile(r"抽签[：:]\s*(p\d+)")


def load_premise(pid: str) -> dict | None:
    f = Path(__file__).with_name("premises.json")
    if not f.exists():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    items = data.get("premises", data) if isinstance(data, dict) else data
    return next((p for p in items if p.get("id") == pid), None)


def check_file(path: Path) -> dict:
    md = Path(path).read_text(encoding="utf-8")
    m = _DRAW.search(md)
    return check_prose(md, load_premise(m.group(1)) if m else None)


if __name__ == "__main__":
    import sys

    paths = [Path(a) for a in sys.argv[1:]]
    if len(paths) == 1:
        r = check_file(paths[0])
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print(format_report(r))
    else:
        texts = [p.read_text(encoding="utf-8") for p in paths]
        r = check_corpus(texts)
        print(json.dumps({k: r[k] for k in ("n_ok", "n_red", "checks", "shared")}, ensure_ascii=False, indent=2))
        print(format_report(r))

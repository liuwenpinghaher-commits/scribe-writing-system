#!/usr/bin/env python3
"""C6-3 LLM-as-judge 评测harness —— 用 critique 评改环的 rubric 给样本打分。

两类用例:
  1) golden_bad:已知应低分的 AI 腔样本。若模型/prompt 退化让它们打高分 → 评测失败(回归门)。
  2) golden_good:已知应高分的克制具体样本。

离线(默认):用内置桩 judge 自检 harness 逻辑(无网络,可进 CI)。
在线(--live):用火山 doubao 真评分,产出真实分数报告。

用法:
  python eval/run_eval.py            # 离线自检
  python eval/run_eval.py --live     # 真实 LLM 评分
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.critique import parse_critique, build_critique_prompt  # noqa: E402

GOLDEN_BAD = [
    "他嘴角勾起一抹弧度,眼底闪过一丝寒意。总而言之,这一刻他明白了一切。命运的齿轮开始转动。",
    "一股暖流涌上心头,仿佛整个世界都静止了。千言万语化作一声叹息。",
]
GOLDEN_GOOD = [
    "雨砸在铁皮棚上,断断续续。沈砚把烟摁进积水里,火星嗤地灭了。"
    "身后门轴响了一下,他没回头,只把右手挪到腰侧——那里空着,枪三天前就被收走了。"
    "脚步停在两米外。\n"
    "“你来晚了。”对方先开口。\n"
    "他这才转身。来人撑着伞,伞沿压得很低,露出的下巴上有道旧疤,是他三年前亲手留下的。"
    "沈砚笑了一下,那笑没到眼睛里:“伞借我半边,谈完你想杀我,随你。”",
]


def _stub_judge(prompt: str) -> str:
    """离线桩:正文里命中已知套路词就给低分,否则高分(仅自检 harness)。"""
    body = prompt.split("正文:\n", 1)[-1]
    bad = any(w in body for w in ["弧度", "暖流", "命运的齿轮", "世界都静止", "千言万语"])
    s = 2 if bad else 4
    keys = ["texture", "surprise", "emotion_truth", "pace", "voice", "anti_slop",
            "intent_resonance", "coherence"]
    return '{"scores":{' + ",".join(f'"{k}":{s}' for k in keys) + '}}'


# 阈值:好坏样本实测清晰分离(坏~1.2,好~3.4)。单评有噪声,故用两评取均值降噪(工程6 双评)。
BAD_MAX = 2.5
GOOD_MIN = 3.0


def _score(complete_fn, text: str) -> float:
    """两评取均值,降低单次 judge 噪声。"""
    vals = []
    for _ in range(2):
        c = parse_critique(complete_fn(build_critique_prompt(text, "")))
        if c["overall"]:
            vals.append(c["overall"])
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def run(complete_fn) -> int:
    fails = 0
    print(f"== golden_bad(应 < {BAD_MAX})==")
    for t in GOLDEN_BAD:
        ov = _score(complete_fn, t)
        ok = ov < BAD_MAX
        print(f"  {'OK' if ok else 'XX'} overall={ov} :: {t[:24]}")
        fails += 0 if ok else 1
    print(f"== golden_good(应 >= {GOOD_MIN})==")
    for t in GOLDEN_GOOD:
        ov = _score(complete_fn, t)
        ok = ov >= GOOD_MIN
        print(f"  {'OK' if ok else 'XX'} overall={ov} :: {t[:24]}")
        fails += 0 if ok else 1
    print(f"\n{'✅ 评测通过' if not fails else f'❌ {fails} 项不达标'}")
    return 1 if fails else 0


def main() -> int:
    if "--live" in sys.argv:
        import scribe_mcp.api as a
        if not (a._VOLC_BASE and a._VOLC_KEY):
            print("无火山配置,无法 --live"); return 2
        return run(lambda p: a._volc_complete(p, role="critique"))
    return run(_stub_judge)


if __name__ == "__main__":
    sys.exit(main())

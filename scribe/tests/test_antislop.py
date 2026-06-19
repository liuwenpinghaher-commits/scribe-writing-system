"""反 AI 腔规则库自检(纯 stdlib,可离线验证)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.antislop import detect, slop_density  # noqa: E402


SLOP = (
    "这一刻,他终于明白了什么是真正的勇气。总而言之,他不是懦夫,而是英雄。"
    "他心中充满了无比的喜悦,仿佛整个世界都静止了。"
)
CLEAN = (
    "他把烟摁灭在窗台上,火星溅了一下。楼下传来铁门合拢的闷响。"
    "他没有回头,只把外套领子竖起来,走进雨里。"
)


def test_slop_is_flagged():
    hits = detect(SLOP)
    rules = {h["rule"] for h in hits}
    # 应命中:顿悟尾句、总结升华、不是…而是、情感直说、世界静止
    for expect in ("epiphany_tail", "summary_uplift", "not_a_but_b",
                   "emotion_telling", "cliche_world"):
        assert expect in rules, f"漏检 {expect};实得 {rules}"
    assert any(h["severity"] == "high" for h in hits)


def test_clean_text_low_density():
    assert detect(CLEAN) == [], f"干净文本误报:{detect(CLEAN)}"
    assert slop_density(CLEAN) == 0.0
    assert slop_density(SLOP) > slop_density(CLEAN)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

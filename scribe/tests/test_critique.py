"""C1-3 文学评改环 自检:解析鲁棒;不达标触发 revise;达标不改(用桩 complete_fn)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.critique import parse_critique, critique_revise, build_critique_prompt  # noqa: E402


def test_parse():
    good = '{"scores":{"texture":2,"surprise":2,"emotion_truth":3,"pace":3,"voice":4,"anti_slop":2,"intent_resonance":3,"coherence":4},"issues":["太套路"],"worst_dims":["texture","anti_slop"]}'
    c = parse_critique(good)
    assert c["overall"] < 3.5 and c["pass"] is False
    assert "texture" in c["worst_dims"]
    hi = '{"scores":{"texture":5,"surprise":4,"emotion_truth":4,"pace":4,"voice":5,"anti_slop":4,"intent_resonance":4,"coherence":5}}'
    assert parse_critique(hi)["pass"] is True
    # 脏输出兜底不崩
    assert parse_critique("模型抽风没给JSON")["pass"] is False


def test_revise_loop():
    calls = {"n": 0}

    def fake(prompt: str) -> str:
        # 第一次(critique)给低分;若是 revise prompt 则返回改稿;再 critique 给高分
        if "只输出一行 JSON" in prompt or "打 1–5 分" in prompt:
            calls["n"] += 1
            if calls["n"] == 1:
                return '{"scores":{"texture":2,"surprise":2,"emotion_truth":2,"pace":3,"voice":3,"anti_slop":2,"intent_resonance":3,"coherence":3},"issues":["套路化"],"worst_dims":["texture"]}'
            return '{"scores":{"texture":4,"surprise":4,"emotion_truth":4,"pace":4,"voice":4,"anti_slop":4,"intent_resonance":4,"coherence":4}}'
        return "改好的更具体的正文。"  # revise 返回

    r = critique_revise("原始套路正文。", "脊背发凉", fake, max_rounds=1)
    assert r["improved"] is True
    assert r["final"] == "改好的更具体的正文。"
    assert r["rounds"][0]["revised_applied"] is True

    # 达标则不改
    r2 = critique_revise("好正文", "", lambda p: '{"scores":{"texture":5,"surprise":4,"emotion_truth":4,"pace":4,"voice":4,"anti_slop":5,"intent_resonance":4,"coherence":4}}')
    assert r2["improved"] is False and r2["final"] == "好正文"


def test_prompt_has_dims():
    p = build_critique_prompt("正文", "悬疑")
    assert "意外性" in p and "无AI腔" in p and "悬疑" in p


def _run():
    for fn in [test_parse, test_revise_loop, test_prompt_has_dims]:
        fn(); print(f"  ✓ {fn.__name__}")
    print("\n通过。")


if __name__ == "__main__":
    _run()

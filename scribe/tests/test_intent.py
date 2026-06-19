"""P0-7 偏离检测 纯函数自检(红线归一化 + verdict 鲁棒解析)。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.intent import red_lines, parse_verdict, build_prompt  # noqa: E402


def test_red_lines_normalize():
    # 字符串视为 hard;对象保留 level;非法 level 归 hard
    intent = {"do_not_betray": json.dumps(
        ["主角不能圣母", {"text": "不要狗血", "level": "soft"}, {"text": "x", "level": "bogus"}],
        ensure_ascii=False)}
    r = red_lines(intent)
    assert r[0] == {"text": "主角不能圣母", "level": "hard"}
    assert r[1] == {"text": "不要狗血", "level": "soft"}
    assert r[2]["level"] == "hard"
    assert red_lines({}) == []  # 空安全


def test_parse_verdict():
    assert parse_verdict('{"status":"hard_violation","reason":"主角圣母了"}')["status"] == "hard_violation"
    # 带前后缀文字也能抽
    assert parse_verdict('好的。{"status":"aligned","reason":"ok"} 以上')["status"] == "aligned"
    # 关键词回退
    assert parse_verdict("这一章明显偏离了主线")["status"] == "soft_deviation"
    # 兜底 aligned
    assert parse_verdict("无明显问题")["status"] == "aligned"
    # reason 截断不报错
    assert "status" in parse_verdict("")


def test_build_prompt_contains_redlines():
    p = build_prompt({"reader_feeling": "脊背发凉"}, "正文内容",
                     [{"text": "不能圣母", "level": "hard"}])
    assert "脊背发凉" in p and "[hard] 不能圣母" in p and "正文内容" in p


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

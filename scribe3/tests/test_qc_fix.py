"""Test QC dash threshold fix (G枢纽 P34).

破折号:按每千字密度归一化,避免长章必误报。
"""
from scribe3.critique import find_ai_tics


class TestDashFix:
    """破折号:按每千字密度归一化(P34)"""

    def test_long_text_doesnt_false_positive(self):
        long_text = "。".join(["一段正常的小说正文内容" * 10 for _ in range(100)])[:5000]
        long_text += "——断——开——思——考——停——顿——"
        results = find_ai_tics(long_text)
        dash_results = [r for r in results if r["kind"] == "em_dash"]
        assert len(dash_results) == 0, "每千字<2个破折号不应误报"

    def test_short_text_with_many_dashes_detected(self):
        text = "——断开——思考——停顿——继续——再次——中断——"
        results = find_ai_tics(text)
        dash_results = [r for r in results if r["kind"] == "em_dash"]
        assert len(dash_results) >= 1, "短文本密集破折号应检测到"

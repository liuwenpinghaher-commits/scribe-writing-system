"""质量任务对偶发非 JSON 输出的恢复合同。"""

from scribe3.quality.evaluator import QualityEvaluator, RawDimensionJudgment


def test_quality_dimension_allows_two_json_repairs_before_failing():
    """两次偶发结构化失配后，第三次真实调用仍应有恢复机会。"""
    captured = {}

    class Client:
        def complete_json_with_result(self, _messages, **kwargs):
            captured.update(kwargs)
            return RawDimensionJudgment(), None

    evaluator = QualityEvaluator(object(), Client())
    evaluator._complete_dimension([{"role": "user", "content": "质量判断"}])

    assert captured["max_repairs"] == 2

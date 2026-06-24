"""Test Circuit Breaker pattern for LLM calls (优化#3).

熔断器:连续失败 N 次后熔断(快速失败),冷却后试探(半开),成功则闭合。
与重试互补:重试处理瞬时抖动,熔断器处理持续故障(如 doubao 服务降级)。
"""
import time

import pytest


class TestCircuitBreaker:
    def test_starts_closed(self):
        from scribe3.llm import CircuitBreaker

        cb = CircuitBreaker(threshold=5, cooldown=30)
        assert cb.allow() is True

    def test_opens_after_consecutive_failures(self):
        from scribe3.llm import CircuitBreaker

        cb = CircuitBreaker(threshold=3, cooldown=60)
        assert cb.allow() is True
        cb.record_failure()
        assert cb.allow() is True
        cb.record_failure()
        assert cb.allow() is True
        cb.record_failure()
        assert cb.allow() is False  # 熔断中

    def test_success_resets_failure_count(self):
        from scribe3.llm import CircuitBreaker

        cb = CircuitBreaker(threshold=5, cooldown=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.allow() is True

    def test_half_open_after_cooldown(self, monkeypatch):
        from scribe3.llm import CircuitBreaker

        cb = CircuitBreaker(threshold=2, cooldown=1)
        fake_now = time.time()

        cb.record_failure()
        cb.record_failure()
        assert cb.allow() is False  # 熔断中

        # 冷却后 → 半开
        fake_now += 2
        monkeypatch.setattr(time, "time", lambda: fake_now)
        assert cb.allow() is True  # 冷却已过,试探通过

    def test_passing_probe_closes_circuit(self, monkeypatch):
        from scribe3.llm import CircuitBreaker

        cb = CircuitBreaker(threshold=2, cooldown=1)
        fake_now = time.time()

        cb.record_failure()
        cb.record_failure()
        fake_now += 2
        monkeypatch.setattr(time, "time", lambda: fake_now)

        assert cb.allow() is True  # 半开,探针通过
        cb.record_success()
        assert cb.allow() is True  # 已闭合

    def test_failing_probe_reopens(self, monkeypatch):
        from scribe3.llm import CircuitBreaker

        cb = CircuitBreaker(threshold=2, cooldown=1)
        fake_now = time.time()

        cb.record_failure()
        cb.record_failure()
        fake_now += 2
        monkeypatch.setattr(time, "time", lambda: fake_now)

        assert cb.allow() is True  # 半开
        cb.record_failure()
        assert cb.allow() is False  # 重新熔断,并重置冷却

    def test_default_threshold_and_cooldown(self):
        from scribe3.llm import CircuitBreaker

        cb = CircuitBreaker()
        assert cb.threshold == 5
        assert cb.cooldown == 60

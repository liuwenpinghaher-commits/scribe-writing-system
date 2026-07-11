"""Task 15 · Spectron 影子适配器与严格采用门禁测试。

为什么这样测:Spectron(surrealdb[spectron] + spectron_integration_hermes_agent)是
SurrealDB 官方记忆/检索方案,本任务让它能【只读影子】跑在自建检索旁做对比,
但**绝不替换生产结果**,且只有满足严格门禁才可采用。两个官方包截至交付日仍未在
PyPI 发布(find_spec 均为 None),所以这里锁死三条安全不变量:
  1. 包未发布 → detect_spectron 恒关(设计正确态,不是缺陷);
  2. 影子结果永不替换主路(choose_production_result 恒返回 primary);
  3. 影子任何异常(超时/认证/无溯源)只记 error,不抛、不降级主路;
  4. 采用门禁六硬条件同时满足才可采用,任一不满足即拒。
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scribe3.memory_models import MemoryCandidate, RetrievalResult
from scribe3.spectron_adapter import (
    AdoptionMetrics,
    SpectronAvailability,
    SpectronShadowAdapter,
    adoption_gate,
    choose_production_result,
    detect_spectron,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = Path(__file__).parent / "fixtures" / "context_memory_gold.json"


def _result(ids: list[str]) -> RetrievalResult:
    """按给定 source_id 列表造一个 RetrievalResult(用 canonical 占位,只关心 .ids)。"""
    return RetrievalResult(selected=[
        MemoryCandidate(source_kind="canonical", source_id=sid, text="", work="w")
        for sid in ids
    ])


def _passing_metrics(**overrides) -> AdoptionMetrics:
    """一组"六条件全过"的度量;测试再逐条 override 成不合格来验证门禁会拒。"""
    base = dict(
        packages_available=True,
        versions_lockable=True,
        clean_days=14,
        p0_p1_incidents=0,
        baseline_ndcg_at_10=0.80,
        spectron_ndcg_at_10=0.90,   # 相对提升 12.5% ≥ 5%
        baseline_p95_ms=100.0,
        spectron_p95_ms=110.0,      # 比值 1.10 ≤ 1.20
        provenance_coverage=1.0,
        backup_restore_audit_forget_covered=True,
        spectron_hermes_provider_enabled=True,
        scribe3_memory_provider_enabled=False,  # 互斥满足
    )
    base.update(overrides)
    return AdoptionMetrics(**base)


# ---------- Step 1:计划规定的两条失败测试 ----------

def test_spectron_is_disabled_when_documented_packages_are_unavailable(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    state = detect_spectron()
    assert state.enabled is False
    assert state.reason == "sdk_or_integration_missing"


def test_shadow_result_never_replaces_primary_result():
    primary = _result(["fact:a"])
    shadow = _result(["memory:b"])
    chosen = choose_production_result(primary, shadow, shadow_mode=True)
    assert chosen.ids == ["fact:a"]


# ---------- detect_spectron:现网恒关 + 双包齐备才开 ----------

def test_detect_spectron_disabled_in_current_environment():
    # 真实运行环境:两个官方包均未发布,恒返回不可用。
    state = detect_spectron()
    assert state.enabled is False
    assert state.reason == "sdk_or_integration_missing"


def test_detect_spectron_enabled_when_both_specs_present(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: sentinel)
    state = detect_spectron()
    assert state.enabled is True
    assert state.reason == "available"


def test_detect_spectron_disabled_when_only_one_present(monkeypatch):
    def only_sdk(name):
        return object() if name == "surrealdb.spectron" else None
    monkeypatch.setattr(importlib.util, "find_spec", only_sdk)
    assert detect_spectron().enabled is False


# ---------- choose_production_result:任何情形恒 primary ----------

def test_choose_production_ignores_shadow_when_shadow_mode_false():
    primary = _result(["fact:a"])
    shadow = _result(["memory:b"])
    assert choose_production_result(primary, shadow, shadow_mode=False).ids == ["fact:a"]


def test_choose_production_with_no_shadow_returns_primary():
    primary = _result(["fact:a"])
    assert choose_production_result(primary, None).ids == ["fact:a"]


# ---------- 采样门:10% 阈值可确定性验证 ----------

def test_should_sample_respects_rate_threshold():
    adapter = SpectronShadowAdapter(sample_rate=0.10)
    assert adapter.should_sample(roll=0.05) is True
    assert adapter.should_sample(roll=0.50) is False
    assert adapter.should_sample(roll=0.10) is False  # 边界:>= rate 不采样


# ---------- 影子在包未发布时恒不运行:只记录,不降级 ----------

def test_shadow_observe_disabled_records_error_without_raising():
    adapter = SpectronShadowAdapter(
        availability=SpectronAvailability(False, "sdk_or_integration_missing"))
    obs = adapter.observe("query", force_sample=True)
    assert obs.sampled is True
    assert obs.ran is False
    assert obs.error == "spectron_unavailable"
    assert adapter.errors  # shadow error 被记录


def test_shadow_not_sampled_returns_inert_observation():
    adapter = SpectronShadowAdapter(sample_rate=0.0)  # 恒不采样
    obs = adapter.observe("query")
    assert obs.sampled is False
    assert obs.ran is False
    assert obs.error is None


# ---------- 影子客户端异常(超时/认证)只记 error,不抛不降级主路 ----------

def test_shadow_client_exception_is_swallowed_and_primary_unaffected():
    def boom_factory():
        class _C:
            def retrieve(self, q):
                raise TimeoutError("spectron timeout")
        return _C()
    adapter = SpectronShadowAdapter(
        availability=SpectronAvailability(True, "available"),
        client_factory=boom_factory)
    obs = adapter.observe("q", force_sample=True)
    assert obs.ran is False
    assert obs.error and "shadow_error" in obs.error
    # 主路完全不受影响
    primary = _result(["fact:a"])
    assert choose_production_result(primary, None).ids == ["fact:a"]


def test_shadow_missing_provenance_records_error_not_degrade():
    class _Hit:
        def __init__(self, sid):
            self.source_id = sid
            self.provenance = []  # 无溯源
    def factory():
        class _C:
            def retrieve(self, q):
                return [_Hit("memory:x")]
        return _C()
    adapter = SpectronShadowAdapter(
        availability=SpectronAvailability(True, "available"),
        client_factory=factory)
    obs = adapter.observe("q", force_sample=True)
    assert obs.provenance_complete is False
    assert obs.error == "missing_provenance"


def test_shadow_successful_observation_records_ids_ranks_latency():
    class _Hit:
        def __init__(self, sid):
            self.source_id = sid
            self.provenance = [{"entity": "1"}]
    def factory():
        class _C:
            def retrieve(self, q):
                return [_Hit("memory:a"), _Hit("memory:b")]
        return _C()
    adapter = SpectronShadowAdapter(
        availability=SpectronAvailability(True, "available"),
        client_factory=factory)
    obs = adapter.observe("q", force_sample=True)
    assert obs.ran is True
    assert obs.candidate_ids == ("memory:a", "memory:b")
    assert obs.ranks == (1, 2)
    assert obs.provenance_complete is True
    assert obs.latency_ms is not None
    assert not adapter.errors


# ---------- 采用门禁:全过 / 任一不满足即拒 ----------

def test_adoption_gate_all_conditions_met():
    decision = adoption_gate(_passing_metrics())
    assert decision.can_adopt is True
    assert decision.unmet == ()


@pytest.mark.parametrize("override,expected_unmet", [
    (dict(packages_available=False), "packages_lockable"),
    (dict(versions_lockable=False), "packages_lockable"),
    (dict(clean_days=13), "clean_14_days"),
    (dict(p0_p1_incidents=1), "clean_14_days"),
    (dict(spectron_ndcg_at_10=0.82), "ndcg_lift"),        # 2.5% < 5%
    (dict(baseline_ndcg_at_10=0.0), "ndcg_lift"),         # 基线 0 无法证明提升
    (dict(spectron_p95_ms=130.0), "latency_and_provenance"),  # 1.30 > 1.20
    (dict(provenance_coverage=0.99), "latency_and_provenance"),  # 溯源非 100%
    (dict(backup_restore_audit_forget_covered=False), "backup_forget_coverage"),
    (dict(scribe3_memory_provider_enabled=True), "provider_mutual_exclusion"),  # 两者同开
])
def test_adoption_gate_rejects_when_single_condition_unmet(override, expected_unmet):
    decision = adoption_gate(_passing_metrics(**override))
    assert decision.can_adopt is False
    assert expected_unmet in decision.unmet


def test_adoption_gate_rejects_in_current_state_packages_unavailable():
    # 现网真实态:全默认(包未发布)→ 第一条即 False → 恒不可采用。
    decision = adoption_gate(AdoptionMetrics())
    assert decision.can_adopt is False
    assert "packages_lockable" in decision.unmet


def test_adoption_gate_checks_expose_each_condition():
    decision = adoption_gate(_passing_metrics(clean_days=0))
    assert set(decision.checks) == {
        "packages_lockable", "clean_14_days", "ndcg_lift",
        "latency_and_provenance", "backup_forget_coverage",
        "provider_mutual_exclusion",
    }
    assert decision.checks["clean_14_days"] is False


# ---------- CLI:包未发布 exit 0;--require-available exit 2;gold 缺失仍优雅 ----------

def test_cli_exits_zero_when_packages_unavailable(tmp_path):
    out = tmp_path / "shadow.json"
    proc = subprocess.run(
        [sys.executable, "-m", "scribe3.tools.spectron_shadow_eval",
         "--gold", str(GOLD_PATH), "--output", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["spectron"]["enabled"] is False
    assert report["spectron"]["reason"] == "sdk_or_integration_missing"
    assert report["shadow_ran"] is False
    assert report["adoption"]["can_adopt"] is False
    assert "enabled=false" in proc.stdout


def test_cli_require_available_exits_two_when_unavailable(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "scribe3.tools.spectron_shadow_eval",
         "--gold", str(GOLD_PATH), "--output", str(tmp_path / "r.json"),
         "--require-available"],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_cli_exits_zero_even_when_gold_missing(tmp_path):
    # 包未发布时无需读 gold 也能 exit 0(不吐裸 traceback)。
    proc = subprocess.run(
        [sys.executable, "-m", "scribe3.tools.spectron_shadow_eval",
         "--gold", str(tmp_path / "不存在.json"), "--output", str(tmp_path / "r.json")],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr

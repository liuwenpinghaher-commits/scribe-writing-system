"""Spectron 影子适配器与严格采用门禁(Task 15)。

Spectron 是 SurrealDB 官方记忆/检索方案(`surrealdb[spectron]` +
`spectron_integration_hermes_agent`)。本模块让它能【只读影子】跑在自建检索
(Task 8 memory_retrieval)旁边做对比,但**绝不替换生产结果**,且只有满足严格
门禁才可进入读流量。

三条安全不变量(测试锁死,任何改动不得破坏):
  1. **恒关优先**:两个官方包截至交付日均未在 PyPI 发布(find_spec 皆 None),
     detect_spectron 恒返回 (False, "sdk_or_integration_missing")。这是设计正确态,
     不是缺陷——门禁在包发布前恒关。
  2. **影子永不替换主**:choose_production_result 恒返回 primary。shadow 只作候选
     id/排名/延迟/溯源完整性的旁路记录,永不进生产 LLM、永不写生产。
  3. **影子失败不降级**:影子超时、认证错、结果无溯源,只记 shadow error,不抛异常、
     不影响主路。

零业务依赖:本模块只 import 标准库 + Task 8 的 memory_models(纯模型),
不 import store/llm/embed,任何一端都能安全引用,CI 秒级可跑。

边界说明(诚实):Step 3 的"10% 采样影子流"需接生产检索路径,但自建检索目前尚无
prompt 生产调用方(Task 16 envelope 灰度才接线),故影子采样的 app.py 集成属
**Task 16 检索接线**。本模块交付"框架就绪 + 门禁 + 恒关",客户端与生产接线待
Task 16 / 官方包发布后激活。
"""
from __future__ import annotations

import importlib.util
import random
import time
from dataclasses import dataclass, field

from scribe3.memory_models import RetrievalResult

# ---- 常量:门禁阈值集中一处,便于审计与调参 ----
DEFAULT_SAMPLE_RATE = 0.10          # Step 3:10% 采样并行调 Spectron
REQUIRED_CLEAN_DAYS = 14            # Step 4:连续 14 天无 P0/P1 事故
MIN_NDCG_LIFT = 0.05               # Step 4:gold nDCG@10 相对提升 ≥ 5%
MAX_LATENCY_RATIO = 1.20           # Step 4:p95 延迟 ≤ 主路 × 1.20
REQUIRED_PROVENANCE_COVERAGE = 1.0  # Step 4:溯源覆盖须 100%

# 官方包的 import 名(find_spec 用)与 PyPI 分发名(读版本用)
_SDK_SPEC = "surrealdb.spectron"
_INTEGRATION_SPEC = "spectron_integration_hermes_agent"
_SDK_DIST = "surrealdb"
_INTEGRATION_DIST = "spectron-integration-hermes-agent"


# ======================================================================
# Step 2:发布可用性检测
# ======================================================================

@dataclass(frozen=True)
class SpectronAvailability:
    """Spectron 是否可用的判定。enabled=False 是包未发布时的正确态。"""

    enabled: bool
    reason: str
    sdk_version: str | None = None
    integration_version: str | None = None


def _dist_version(dist_name: str) -> str | None:
    """尽力读分发版本;读不到返回 None(包未发布路径不会走到这里)。"""
    try:
        from importlib.metadata import version
        return version(dist_name)
    except Exception:
        return None


def detect_spectron() -> SpectronAvailability:
    """检测两个官方包是否都可导入。

    注意:必须以 `importlib.util.find_spec` 属性访问方式调用(而非
    `from importlib.util import find_spec`),这样测试对 importlib.util.find_spec
    的 monkeypatch 才能生效。
    """
    sdk = importlib.util.find_spec(_SDK_SPEC)
    integration = importlib.util.find_spec(_INTEGRATION_SPEC)
    if not sdk or not integration:
        return SpectronAvailability(False, "sdk_or_integration_missing")
    return SpectronAvailability(
        enabled=True,
        reason="available",
        sdk_version=_dist_version(_SDK_DIST),
        integration_version=_dist_version(_INTEGRATION_DIST),
    )


# ======================================================================
# 生产结果选择:影子永不替换主(安全核心)
# ======================================================================

def choose_production_result(
    primary: RetrievalResult,
    shadow: RetrievalResult | None = None,
    shadow_mode: bool = True,
) -> RetrievalResult:
    """生产结果恒为主路 primary。

    无论 shadow_mode 真假、无论 shadow 是否命中更多候选,shadow 永不替换 primary。
    这是 Task 15 的安全底线:Spectron 只做旁路对比,决不接管生产读结果。
    """
    return primary


# ======================================================================
# Step 3:只读影子流(客户端待 Task 16 / 官方包发布接线)
# ======================================================================

@dataclass(frozen=True)
class ShadowObservation:
    """一次影子观测的记录:只存候选 id/排名/延迟/溯源完整性,绝不含 context 正文。"""

    sampled: bool                       # 是否被 10% 采样命中
    ran: bool                           # 影子检索是否真正跑成
    error: str | None = None            # shadow error 分类(超时/认证/无溯源/不可用)
    candidate_ids: tuple[str, ...] = ()  # Spectron 返回的候选 source_id(按排名)
    ranks: tuple[int, ...] = ()          # 对应位次(1 起)
    latency_ms: float | None = None      # 影子延迟(仅统计,不进主路)
    provenance_complete: bool | None = None  # 全部候选是否都带溯源


class SpectronShadowAdapter:
    """只读影子适配器:并行调 Spectron 做对比,但决不触碰生产结果。

    - `should_sample`:10% 采样门(可传 roll 做确定性测试)。
    - `observe`:执行一次影子观测。**永不抛异常、永不降级主路**——包未发布、无客户端、
      超时、认证错、结果无溯源,一律只记 shadow error 并返回带 error 的观测。
    - `client_factory`:返回一个具备 `retrieve(query) -> list[hit]` 的 Spectron 客户端;
      hit 需带 `.source_id` 与 `.provenance`。当前无真实客户端(官方包未发布 + 生产
      检索接线属 Task 16),故默认 None。
    """

    def __init__(
        self,
        availability: SpectronAvailability | None = None,
        sample_rate: float = DEFAULT_SAMPLE_RATE,
        client_factory=None,
        rng: random.Random | None = None,
    ) -> None:
        self.availability = availability if availability is not None else detect_spectron()
        self.sample_rate = sample_rate
        self._client_factory = client_factory
        self._rng = rng if rng is not None else random.Random()
        self.errors: list[str] = []

    def _record_error(self, error: str) -> None:
        self.errors.append(error)

    def should_sample(self, roll: float | None = None) -> bool:
        """10% 采样门:roll < sample_rate 才采样(roll 缺省用内部 rng)。"""
        r = roll if roll is not None else self._rng.random()
        return r < self.sample_rate

    def observe(
        self,
        query,
        *,
        force_sample: bool = False,
        roll: float | None = None,
    ) -> ShadowObservation:
        """执行一次影子观测。契约:任何失败都只记录、返回带 error 的观测,决不抛/降级。"""
        sampled = force_sample or self.should_sample(roll)
        if not sampled:
            return ShadowObservation(sampled=False, ran=False)

        # 包未发布 / 恒关:只记录不运行。
        if not self.availability.enabled:
            self._record_error("spectron_unavailable")
            return ShadowObservation(sampled=True, ran=False, error="spectron_unavailable")

        # 无客户端(官方包已发布但生产检索接线待 Task 16):记录后返回,不降级。
        if self._client_factory is None:
            self._record_error("no_spectron_client")
            return ShadowObservation(sampled=True, ran=False, error="no_spectron_client")

        try:
            client = self._client_factory()
            started = time.perf_counter()
            hits = client.retrieve(query)
            latency_ms = (time.perf_counter() - started) * 1000.0
        except Exception as exc:  # 超时/认证/任何异常:只记 shadow error,不抛不降级
            self._record_error(f"shadow_error:{type(exc).__name__}")
            return ShadowObservation(
                sampled=True, ran=False, error=f"shadow_error:{type(exc).__name__}")

        candidate_ids = tuple(getattr(h, "source_id", "") for h in hits)
        ranks = tuple(range(1, len(hits) + 1))
        provenance_complete = all(getattr(h, "provenance", None) for h in hits)
        if not provenance_complete:
            # 无溯源:记为 shadow error,但仍返回候选(供审计),绝不降级主路。
            self._record_error("missing_provenance")
            return ShadowObservation(
                sampled=True, ran=True, error="missing_provenance",
                candidate_ids=candidate_ids, ranks=ranks,
                latency_ms=latency_ms, provenance_complete=False)

        return ShadowObservation(
            sampled=True, ran=True,
            candidate_ids=candidate_ids, ranks=ranks,
            latency_ms=latency_ms, provenance_complete=True)


# ======================================================================
# Step 4:采用门禁(六硬条件,同时满足才可进 50% 读流量)
# ======================================================================

@dataclass(frozen=True)
class AdoptionMetrics:
    """采用门禁的输入度量。默认全"不合格",对应包未发布的现网真实态。

    字段对应计划 Step 4 六条件:
      1. packages_available + versions_lockable —— 官方包可安装且版本可锁定;
      2. clean_days + p0_p1_incidents —— 连续 14 天无 P0/P1 数据丢失或 work 泄漏;
      3. baseline/spectron_ndcg_at_10 —— gold nDCG@10 相对提升 ≥ 5%;
      4. baseline/spectron_p95_ms + provenance_coverage —— p95 ≤ 主路×1.20 且溯源 100%;
      5. backup_restore_audit_forget_covered —— 备份/恢复/审计/忘却覆盖派生数据;
      6. spectron_hermes_provider_enabled + scribe3_memory_provider_enabled —— provider 互斥
         (用 Spectron Hermes provider 必须关 scribe3-memory,两者不得同开)。
    """

    packages_available: bool = False
    versions_lockable: bool = False
    clean_days: int = 0
    p0_p1_incidents: int = 0
    baseline_ndcg_at_10: float = 0.0
    spectron_ndcg_at_10: float = 0.0
    baseline_p95_ms: float = 0.0
    spectron_p95_ms: float = 0.0
    provenance_coverage: float = 0.0
    backup_restore_audit_forget_covered: bool = False
    spectron_hermes_provider_enabled: bool = False
    scribe3_memory_provider_enabled: bool = False


@dataclass(frozen=True)
class AdoptionDecision:
    """门禁裁决:can_adopt 全过才 True;checks 逐条留痕;unmet 列未过条件。"""

    can_adopt: bool
    checks: dict[str, bool] = field(default_factory=dict)
    unmet: tuple[str, ...] = ()


def adoption_gate(metrics: AdoptionMetrics) -> AdoptionDecision:
    """纯函数门禁:六条件同时为真才 can_adopt=True,任一为假即拒并列入 unmet。

    包未发布时 packages_available 默认 False → packages_lockable 恒 False → 恒不可采用。
    """
    ndcg_lift_ok = (
        metrics.baseline_ndcg_at_10 > 0.0
        and (metrics.spectron_ndcg_at_10 - metrics.baseline_ndcg_at_10)
        / metrics.baseline_ndcg_at_10 >= MIN_NDCG_LIFT
    )
    latency_ok = (
        metrics.baseline_p95_ms > 0.0
        and metrics.spectron_p95_ms <= metrics.baseline_p95_ms * MAX_LATENCY_RATIO
    )
    checks = {
        # 1. 官方包可安装且版本可锁定
        "packages_lockable": metrics.packages_available and metrics.versions_lockable,
        # 2. 连续 14 天无 P0/P1 数据丢失或 work 泄漏
        "clean_14_days": metrics.clean_days >= REQUIRED_CLEAN_DAYS
        and metrics.p0_p1_incidents == 0,
        # 3. gold nDCG@10 比自建高 ≥ 5%
        "ndcg_lift": ndcg_lift_ok,
        # 4. p95 延迟 ≤ 主路 20% 且溯源 100%
        "latency_and_provenance": latency_ok
        and metrics.provenance_coverage >= REQUIRED_PROVENANCE_COVERAGE,
        # 5. 备份/恢复/审计/忘却覆盖 Spectron 派生数据
        "backup_forget_coverage": metrics.backup_restore_audit_forget_covered,
        # 6. provider 互斥:用 Spectron provider 必须关 scribe3-memory
        "provider_mutual_exclusion": not (
            metrics.spectron_hermes_provider_enabled
            and metrics.scribe3_memory_provider_enabled
        ),
    }
    unmet = tuple(name for name, ok in checks.items() if not ok)
    return AdoptionDecision(can_adopt=not unmet, checks=checks, unmet=unmet)

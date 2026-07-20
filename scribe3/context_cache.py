"""统一上下文系统 · Task 16-B:性能层门面(feature flags / TTL 缓存 + 表级失效 / 运行指标)。

为什么单独一个叶子模块:embedding 在 embed.py、检索在 memory_retrieval.py、指标上报在
app.py 都要用到同一套缓存/失效/开关原语。本模块【零业务依赖】(不 import app/store/llm/
embed),与 context_models / memory_models 同层,任何一端都能安全引用而不成环。

诚实边界(做实 vs 就绪):
- 【做实】feature flags 门面 + GET /capabilities 上报;embedding sha256 缓存在 embed.py。
- 【做实】cross_work / memory pending·failed / spectron / 会话数 等指标当前有真实值。
- 【做实】RETRIEVAL_CACHE 已在 MEMORY_FABRIC 开启时进入统一写作 envelope 读路径，
  并以 TTL + 表级失效约束；关闭时明确不实例化 retriever。GLOBAL_CARD_CACHE 仍只有
  helper/测试消费，尚无生产调用方。
- 【做实】retrieval 延迟 / 上下文 token / stale 拒绝均已接入 record_*；没有样本时
  如实上报 0 / None，不代表统一 assembler 未启用。

铁律:失效永远优先于命中——任何可能致「限知泄露 / 正典过期 / 秘密」错乱的缓存,失效必须
及时(正典写入 / 记忆 supersede / 素材 archive·pin 立即清 + 正典 bump authority_revision)。
宁可缓存命中率低,不返回脏的正典 / 限知数据。TTL(60s/30s)+ 表级失效双保险。
approval 决策与 stale revision 检查【绝不缓存】(安全,本模块不提供其缓存 API)。
"""
from __future__ import annotations

import math
import os
import threading
import time
from collections import OrderedDict, deque

# ───────────────────────── feature flags ─────────────────────────

_TRUE = {"1", "true", "yes", "on"}

# 四个有真实执行语义的灰度开关(默认全关;经后端 capabilities 下发)。
FLAGS = (
    "SCRIBE3_CONTEXT_SNAPSHOT_V1",     # 已存在(context_service),纳入统一上报
    "SCRIBE3_EDITORIAL_THREAD_V1",
    "SCRIBE3_MEMORY_FABRIC_V1",
    "SCRIBE3_CONTEXT_INSPECTOR_V1",
)


def flag_enabled(name: str) -> bool:
    """统一开关判定:先读设置中心(DB 覆盖→env→默认,热生效),未登记名
    回落旧 env 语义(向前兼容)。默认关 → 与开关引入前【字节等价】。"""
    try:
        from scribe3.settings import get_setting
        return bool(get_setting(name))
    except KeyError:
        return os.environ.get(name, "").strip().lower() in _TRUE


# 检索结果缓存键的策略版本:检索策略/融合口径变更须 bump,使旧缓存键自然失效。
RETRIEVAL_POLICY_VERSION = "1"


# ───────────────────────── TTL 缓存 + 表级失效 ─────────────────────────

# 正典表:写这些表须 bump authority_revision 且清 global / retrieval 缓存。
_CANONICAL_TABLES = frozenset({"proposition", "promise", "knows", "reader_knows"})
_MATERIAL_TABLES = frozenset({"material"})
_MEMORY_TABLES = frozenset({"memory_item"})


class TTLCache:
    """线程安全的 TTL + LRU 缓存,支持按 work 作用域的表级失效。

    entry = (expires_at, work, value)。tables 为空 = 订阅所有表级失效;
    非空 = 只被订阅表的失效事件触及。clock 可注入(测试用假时钟免真实 sleep)。"""

    def __init__(self, ttl_seconds: float, *, maxsize: int = 256, name: str = "",
                 tables=(), clock=time.monotonic):
        self.ttl = float(ttl_seconds)
        self.maxsize = int(maxsize)
        self.name = name
        self.tables = frozenset(tables)
        self._clock = clock
        self._d: "OrderedDict[object, tuple]" = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        _register_cache(self)

    def get(self, key):
        with self._lock:
            entry = self._d.get(key)
            if entry is None:
                self.misses += 1
                return None
            expires_at, _work, value = entry
            if expires_at <= self._clock():
                self._d.pop(key, None)      # 过期即淘汰(不返脏)
                self.misses += 1
                return None
            self._d.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key, value, *, work=None):
        with self._lock:
            if key in self._d:
                self._d.pop(key)
            self._d[key] = (self._clock() + self.ttl, work, value)
            while len(self._d) > self.maxsize:
                self._d.popitem(last=False)   # LRU 驱逐

    def invalidate(self, work=None):
        """work=None 清全部;否则只清该 work 的条目(过清安全,漏清危险)。"""
        with self._lock:
            if work is None:
                self._d.clear()
                return
            for k in [k for k, (_e, w, _v) in self._d.items() if w == work]:
                self._d.pop(k, None)

    def clear(self):
        self.invalidate(None)

    def stats(self) -> dict:
        with self._lock:
            return {"name": self.name, "size": len(self._d),
                    "hits": self.hits, "misses": self.misses, "ttl": self.ttl}


# 全体缓存登记表(表级失效事件按 tables 订阅广播)。
_ALL_CACHES: list = []
_REGISTRY_LOCK = threading.RLock()


def _register_cache(cache: TTLCache) -> None:
    with _REGISTRY_LOCK:
        _ALL_CACHES.append(cache)


def _register_for_test(cache: TTLCache) -> None:
    """测试用:确保临时构造的 TTLCache 已登记进失效广播(构造时已自动登记,幂等)。"""
    with _REGISTRY_LOCK:
        if cache not in _ALL_CACHES:
            _ALL_CACHES.append(cache)


# authority_revision:正典写入的单调计数(per work)。global card 缓存键含它——
# 正典一变,新键即与旧条目错开(双保险之一,另一为直接 invalidate)。
_authority_rev: dict[str, int] = {}
_authority_lock = threading.RLock()
# 可观测:各表发出过多少次表级失效事件(不含任何秘密,仅计数)。
_invalidation_counts: dict[str, int] = {}


def authority_revision(work: str) -> int:
    with _authority_lock:
        return _authority_rev.get(work or "", 0)


def _bump_authority(work: str) -> None:
    with _authority_lock:
        _authority_rev[work or ""] = _authority_rev.get(work or "", 0) + 1


def _reset_authority_for_test(work: str) -> None:
    with _authority_lock:
        _authority_rev.pop(work or "", None)


def emit_invalidation(table: str, work: str | None = None) -> None:
    """表级失效事件:清订阅该表的缓存;正典表额外 bump authority_revision。

    正典写入 / 记忆 supersede / 素材 archive·pin 的 store 写点调用本函数。
    best-effort、绝不抛错(失效比命中优先,但也绝不阻断写主链路)。"""
    try:
        with _REGISTRY_LOCK:
            _invalidation_counts[table] = _invalidation_counts.get(table, 0) + 1
            caches = list(_ALL_CACHES)
        if table in _CANONICAL_TABLES and work is not None:
            _bump_authority(work)
        for cache in caches:
            if not cache.tables or table in cache.tables:
                cache.invalidate(work)
    except Exception:
        # 失效登记/广播的任何异常都不得冒泡到写路径(写正确性 > 缓存卫生)。
        pass


def invalidation_counts() -> dict:
    with _REGISTRY_LOCK:
        return dict(_invalidation_counts)


# ── 具体缓存实例 ──
# GlobalContextCard:work + authority_revision,60s;正典写入即失效。
GLOBAL_CARD_CACHE = TTLCache(60, maxsize=128, name="global_card", tables=_CANONICAL_TABLES)
# RetrievalResult:work + context_hash + normalized_query + policy_version,30s;
#   正典 / 素材 / 记忆表级失效(记忆 supersede、素材 archive·pin、正典写入)即清。
RETRIEVAL_CACHE = TTLCache(
    30, maxsize=256, name="retrieval",
    tables=_CANONICAL_TABLES | _MATERIAL_TABLES | _MEMORY_TABLES)


def retrieval_key(work: str, context_hash: str, query: str,
                  policy_version: str = RETRIEVAL_POLICY_VERSION) -> tuple:
    """RetrievalResult 缓存键:work + context_hash + normalized_query + policy_version。"""
    norm_q = " ".join((query or "").split())
    return (work or "", context_hash or "", norm_q, policy_version)


def global_card_key(work: str) -> tuple:
    """GlobalContextCard 缓存键:work + 当前 authority_revision。

    L1 记账警示(Task 16-C):本键【仅 work 维】,不含 chapter/focalizer。当前 GLOBAL_CARD_CACHE
    休眠(cached_global_card 无生产调用方),且"全局卡"按定义是 work 级稳定层(北极星/开放伏笔/
    主要角色,与章/焦点者无关),故 work 维内容安全。但若将来把 chapter/focalizer 相关内容并入
    global card 再接线,【必须先给键补 chapter/focalizer 维】,否则限知章会命中错章/错焦点者的缓存
    卡(与 RETRIEVAL_CACHE 的 _snapshot_cache_dim 同类风险)。接线前务必复核本注释。"""
    return (work or "", authority_revision(work or ""))


def cached_global_card(work: str, build_fn):
    """就绪 helper:按 work+authority_revision 缓存 60s 的全局上下文卡。

    诚实边界:当前 assembler v1 默认关、无生产消费方,故无生产命中;接线后即生效。"""
    key = global_card_key(work)
    cached = GLOBAL_CARD_CACHE.get(key)
    if cached is not None:
        return cached
    value = build_fn()
    GLOBAL_CARD_CACHE.set(key, value, work=work)
    return value


# ───────────────────────── 运行指标采集骨架 ─────────────────────────

class _Histogram:
    """定长滑动窗直方图(线程安全)。用于 retrieval 延迟 / 上下文 token 的分位数。"""

    def __init__(self, maxlen: int = 1024):
        self._d: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def record(self, value: float) -> None:
        with self._lock:
            self._d.append(float(value))

    def percentile(self, p: float):
        with self._lock:
            data = sorted(self._d)
        if not data:
            return None
        if len(data) == 1:
            return data[0]
        k = (len(data) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        return data[f] + (data[c] - data[f]) * (k - f)

    def count(self) -> int:
        with self._lock:
            return len(self._d)

    def clear(self) -> None:
        with self._lock:
            self._d.clear()


_RETRIEVAL_LATENCY = _Histogram()
_CONTEXT_TOKENS = _Histogram()
_STALE_REJECTIONS = 0
_stale_lock = threading.Lock()


def record_retrieval_latency(ms: float) -> None:
    """检索耗时(毫秒)采样。当前唯一填充点是 retrieve_full_cached 的 miss 分支;
    生产读路径接进(16-C)后自然有量。"""
    _RETRIEVAL_LATENCY.record(ms)


def record_context_tokens(n: int) -> None:
    """组装 envelope 的 token 估算采样(待 16-C assembler 生产接线填充)。"""
    _CONTEXT_TOKENS.record(n)


def record_stale_rejection() -> None:
    """stale revision 被拒一次(待写入 Run / chat 绑定的 stale 路径接线填充)。"""
    global _STALE_REJECTIONS
    with _stale_lock:
        _STALE_REJECTIONS += 1


def metrics_snapshot() -> dict:
    """检索/组装侧指标只读快照。绝不含 prompt / 秘密——只有计数与分位数。"""
    with _stale_lock:
        stale = _STALE_REJECTIONS
    return {
        "retrieval_p50": _RETRIEVAL_LATENCY.percentile(50),
        "retrieval_p95": _RETRIEVAL_LATENCY.percentile(95),
        "retrieval_samples": _RETRIEVAL_LATENCY.count(),
        "context_tokens_p95": _CONTEXT_TOKENS.percentile(95),
        "context_tokens_samples": _CONTEXT_TOKENS.count(),
        "stale_rejections": stale,
    }


def reset_metrics_for_test() -> None:
    global _STALE_REJECTIONS
    _RETRIEVAL_LATENCY.clear()
    _CONTEXT_TOKENS.clear()
    with _stale_lock:
        _STALE_REJECTIONS = 0

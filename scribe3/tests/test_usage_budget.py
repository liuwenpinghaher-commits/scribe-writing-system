"""H-10 全系统预算 TDD:跨进程共享日帽台账 + token usage 聚合 + /ai/usage 端点。

背景(v018 审查 H-10):原日帽是进程内计数——app(:3321)与 MCP stdio 进程各持
一个 _daily,系统真实调用数 = 各进程之和,UI 显示的"剩余额度"失真。本批改为
SQLite 共享台账(SCRIBE3_LLM_LEDGER 指路径,测试经 conftest 隔离到 tmp),
SQLite 故障 fail-open 回退进程内计数(帽是成本保险丝,不因台账故障阻断写作)。
"""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import scribe3.llm as L
import scribe3.usage as U


# ===== 1. 共享台账本体 =====

def test_tick_shared_across_instances(tmp_path, monkeypatch):
    """两个"进程"(独立调用点)共用一条账:合计达帽即拦,证明帽是系统级。"""
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(tmp_path / "l.sqlite3"))
    assert U.tick(cap=3) == "shared"
    assert U.tick(cap=3) == "shared"
    # 模拟另一进程:清掉本进程内计数,共享台账应仍记得前两笔
    U._proc_daily[0], U._proc_daily[1] = "", 0
    assert U.tick(cap=3) == "shared"
    with pytest.raises(RuntimeError, match="日调用上限"):
        U.tick(cap=3)


def test_used_today_reads_shared(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(tmp_path / "l.sqlite3"))
    U.tick(cap=10)
    U.tick(cap=10)
    used, scope = U.used_today()
    assert used == 2 and scope == "shared"


def test_tick_zero_cap_is_unlimited_but_still_records_usage(tmp_path, monkeypatch):
    """cap=0 只关闭阻断，调用账仍须逐笔递增。"""
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(tmp_path / "l.sqlite3"))
    for _ in range(3):
        assert U.tick(cap=0) == "shared"
    assert U.used_today() == (3, "shared")


def test_tick_fail_open_on_ledger_error(tmp_path, monkeypatch):
    """台账路径不可写 → 回退进程内计数,不拦正常调用(fail-open),但进程帽仍生效。"""
    bad = tmp_path / "not_a_dir_file"
    bad.write_text("x")
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(bad / "l.sqlite3"))  # 父"目录"是文件 → 必失败
    U._proc_daily[0], U._proc_daily[1] = "", 0
    assert U.tick(cap=2) == "process"
    assert U.tick(cap=2) == "process"
    with pytest.raises(RuntimeError, match="日调用上限"):
        U.tick(cap=2)


def test_tick_zero_cap_fail_open_still_records_usage(tmp_path, monkeypatch):
    """共享台账故障时，cap=0 仍不阻断，并在进程账中逐笔递增。"""
    bad = tmp_path / "not_a_dir_file"
    bad.write_text("x")
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(bad / "l.sqlite3"))
    U._proc_daily[0], U._proc_daily[1] = "", 0
    for _ in range(3):
        assert U.tick(cap=0) == "process"
    assert U.used_today() == (3, "process")


def test_reset_today_clears_both(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(tmp_path / "l.sqlite3"))
    U.tick(cap=5)
    U.reset_today()
    used, _ = U.used_today()
    assert used == 0


def test_provider_usage_records_and_aggregates_tokens_separately(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(tmp_path / "l.sqlite3"))

    assert U.record_provider_usage(
        provider="deepseek",
        model="deepseek-chat",
        transport="httpx",
        status="completed",
        http_status=200,
        usage={
            "prompt_tokens": 11,
            "completion_tokens": 5,
            "total_tokens": 16,
            "prompt_cache_hit_tokens": 7,
            "prompt_cache_miss_tokens": 4,
        },
    ) is True
    assert U.record_provider_usage(
        provider="deepseek",
        model="deepseek-chat",
        transport="httpx",
        status="http_error",
        http_status=429,
    ) is True

    summary = U.provider_usage_summary(days=7)
    assert summary["cost_amount"] is None
    assert summary["pricing_status"] == "not_configured"
    groups = summary["days"][0]["groups"]
    completed = next(group for group in groups if group["status"] == "completed")
    failed = next(group for group in groups if group["status"] == "http_error")
    assert completed == {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "transport": "httpx",
        "status": "completed",
        "http_status": 200,
        "calls": 1,
        "input_tokens": 11,
        "output_tokens": 5,
        "total_tokens": 16,
        "prompt_cache_hit_tokens": 7,
        "prompt_cache_miss_tokens": 4,
    }
    assert failed["calls"] == 1
    assert failed["http_status"] == 429
    assert failed["total_tokens"] == 0


def test_provider_usage_concurrent_writes_are_atomic(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_LLM_LEDGER", str(tmp_path / "l.sqlite3"))

    def record(_index):
        return U.record_provider_usage(
            provider="deepseek",
            model="deepseek-chat",
            transport="httpx",
            status="completed",
            http_status=200,
            usage={"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(record, range(32)))

    assert results == [True] * 32
    group = U.provider_usage_summary(days=1)["days"][0]["groups"][0]
    assert group["calls"] == 32
    assert group["input_tokens"] == 64
    assert group["output_tokens"] == 32
    assert group["total_tokens"] == 96


def test_provider_usage_sqlite_failure_is_fail_soft(monkeypatch):
    secret_sentinel = "provider-ledger-private-sentinel"

    def broken_connect():
        raise sqlite3.OperationalError(f"ledger unavailable {secret_sentinel}")

    monkeypatch.setattr(U, "_connect", broken_connect)
    assert U.record_provider_usage(
        provider="deepseek",
        model="deepseek-chat",
        transport="httpx",
        status="completed",
        usage={"total_tokens": 3},
    ) is False
    assert U.provider_usage_summary(days=7) == {
        "days": [],
        "cost_amount": None,
        "pricing_status": "not_configured",
        "error": "provider_usage_unavailable",
    }


# ===== 2. llm.py 接线(_tick_daily/daily_remaining 走共享台账)=====

def test_llm_cap_shared_across_processes(monkeypatch):
    """llm 层日帽以共享台账为准:清进程计数(模拟另一进程)后第 3 笔仍被拦。
    (SCRIBE3_LLM_LEDGER 已由 conftest autouse 隔离到 tmp)"""
    monkeypatch.setattr(L, "_cap", lambda: 2)
    L._reset_daily_counter()

    class FakeClient:
        def complete(self, _messages, **_kwargs):
            from scribe3.deepseek_client import CompletionResult, ProviderIdentity, OFFICIAL_API_BASE
            return CompletionResult(
                content="ok",
                model="deepseek-chat",
                usage={},
                finish_reason="stop",
                identity=ProviderIdentity(
                    provider="deepseek",
                    api_base=OFFICIAL_API_BASE,
                    model="deepseek-chat",
                    official=True,
                    transport="httpx",
                ),
            )

    monkeypatch.setattr(L, "DeepSeekClient", FakeClient, raising=False)
    monkeypatch.setattr(
        L,
        "HermesAuth",
        lambda: (_ for _ in ()).throw(AssertionError("tool-free path reached HermesAuth")),
    )
    monkeypatch.setattr(
        L.httpx,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("tool-free path reached legacy HTTP transport")
        ),
    )
    assert L.hermes_complete("a") == "ok"
    assert L.hermes_complete("b") == "ok"
    U._proc_daily[0], U._proc_daily[1] = "", 0   # 模拟另一进程视角
    with pytest.raises(RuntimeError, match="日调用上限"):
        L.hermes_complete("c")
    L._reset_daily_counter()


def test_daily_remaining_reflects_shared(monkeypatch):
    monkeypatch.setattr(L, "_cap", lambda: 10)
    L._reset_daily_counter()
    U.tick(cap=10)
    U.tick(cap=10)
    assert L.daily_remaining() == 8
    L._reset_daily_counter()


def test_daily_remaining_is_none_when_cap_is_unlimited(monkeypatch):
    monkeypatch.setattr(L, "_cap", lambda: 0)
    assert L.daily_remaining() is None


# ===== 3. store.usage_summary:trace 表 token 聚合 =====

def test_usage_summary_aggregates_traces(store):
    store.add_chat_message(1, "draft", "assistant", "回1", trace={
        "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}})
    store.add_chat_message(1, "draft", "assistant", "回2", trace={
        "usage": {"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}})
    store.add_chat_message(1, "draft", "user", "问(无usage)", trace={})
    store.upsert_ai_run_trace("run_x", status="completed",
                              usage={"input_tokens": 30, "output_tokens": 5, "total_tokens": 35})
    s = store.usage_summary(days=7)
    assert s["days"], "至少聚出今天一天"
    today = s["days"][0]
    assert today["responses"]["calls"] == 2
    assert today["responses"]["input_tokens"] == 150
    assert today["responses"]["output_tokens"] == 30
    assert today["runs"]["calls"] == 1
    assert today["runs"]["total_tokens"] == 35
    assert today["total"]["total_tokens"] == 215


def test_usage_summary_empty_store(store):
    s = store.usage_summary(days=7)
    assert s["days"] == []


# ===== 4. /ai/usage 端点 =====

def test_ai_usage_endpoint(store, monkeypatch):
    import scribe3.app as A
    from scribe3 import settings as S

    A.set_store(store)
    public = {"llm.model": "deepseek-chat", "SCRIBE3_DAILY_CALL_CAP": 100}
    monkeypatch.setattr(S, "get_public_setting", public.__getitem__, raising=False)
    L._reset_daily_counter()
    U.tick(cap=100)
    store.add_chat_message(2, "draft", "assistant", "回", trace={
        "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}})
    r = TestClient(A.app).get("/ai/usage").json()
    assert r["cap"]["cap"] == 100
    assert r["cap"]["used_today"] == 1
    assert r["cap"]["remaining"] == 99
    assert r["cap"]["unlimited"] is False
    assert r["cap"]["scope"] == "shared"
    assert r["tokens"]["days"][0]["total"]["total_tokens"] == 12
    assert r["provider_usage"] == {
        "days": [],
        "cost_amount": None,
        "pricing_status": "not_configured",
    }
    L._reset_daily_counter()


def test_ai_usage_endpoint_keeps_provider_usage_separate_from_trace_tokens(
    store,
    monkeypatch,
):
    import scribe3.app as A

    A.set_store(store)
    provider_usage = {
        "days": [{
            "day": "2026-07-20",
            "groups": [{
                "provider": "deepseek",
                "model": "deepseek-chat",
                "transport": "httpx",
                "status": "completed",
                "http_status": 200,
                "calls": 1,
                "input_tokens": 8,
                "output_tokens": 2,
                "total_tokens": 10,
                "prompt_cache_hit_tokens": 6,
                "prompt_cache_miss_tokens": 2,
            }],
        }],
        "cost_amount": None,
        "pricing_status": "not_configured",
    }
    monkeypatch.setattr(U, "provider_usage_summary", lambda days: provider_usage)
    store.add_chat_message(2, "draft", "assistant", "回", trace={
        "usage": {"input_tokens": 3, "output_tokens": 1, "total_tokens": 4}})

    payload = TestClient(A.app).get("/ai/usage").json()

    assert payload["provider_usage"] == provider_usage
    assert payload["tokens"]["days"][0]["total"]["total_tokens"] == 4
    assert payload["provider_usage"]["days"][0]["groups"][0]["total_tokens"] == 10


def test_ai_usage_endpoint_exposes_only_safe_official_provider_evidence(
    store, tmp_path, monkeypatch
):
    """identity/model/cap/key 均走窄接口，冷缓存下禁用宽读取仍可成功。"""
    import scribe3.app as A
    from scribe3 import settings as S, settings_store
    from scribe3.deepseek_client import OFFICIAL_API_BASE

    A.set_store(store)
    cold_db = tmp_path / "provider-public-settings.sqlite3"
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(cold_db))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.delenv("SCRIBE3_DAILY_CALL_CAP", raising=False)
    S.invalidate_cache()
    assert cold_db.exists() is False
    forbidden = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("provider evidence attempted to read setting values")
    )
    monkeypatch.setattr(S, "get_setting", forbidden)
    monkeypatch.setattr(S, "settings_snapshot", forbidden)
    monkeypatch.setattr(settings_store, "get_all_overrides", forbidden)

    response = TestClient(A.app).get("/ai/usage")
    assert response.status_code == 200
    provider = response.json()["provider"]
    assert provider == {
        "provider": "deepseek",
        "api_base": OFFICIAL_API_BASE,
        "model": "deepseek-chat",
        "official": True,
        "transport": "direct",
        "key_present": True,
    }
    assert type(provider["key_present"]) is bool
    assert "key_configured" not in provider
    assert response.json()["cap"]["cap"] == 0
    assert cold_db.exists() is False


def test_ai_usage_endpoint_preserves_empty_sqlite_model_without_broad_read(
    store, tmp_path, monkeypatch
):
    import scribe3.app as A
    from scribe3 import settings as S, settings_store

    A.set_store(store)
    db = tmp_path / "provider-empty-model.sqlite3"
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(db))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    settings_store.set_override("llm.model", json.dumps(""))
    settings_store.set_override("SCRIBE3_DAILY_CALL_CAP", json.dumps(0))
    S.invalidate_cache()

    forbidden = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("empty explicit model fell back to a broad setting reader")
    )
    monkeypatch.setattr(S, "get_setting", forbidden)
    monkeypatch.setattr(S, "settings_snapshot", forbidden)
    monkeypatch.setattr(settings_store, "get_all_overrides", forbidden)

    response = TestClient(A.app).get("/ai/usage")
    assert response.status_code == 200
    assert response.json()["provider"]["model"] == ""


def test_ai_usage_endpoint_reports_missing_explicit_provider_key(store, monkeypatch):
    import scribe3.app as A
    from scribe3 import settings as S

    A.set_store(store)
    calls = []
    monkeypatch.setattr(
        S,
        "is_explicitly_configured",
        lambda key: calls.append(key) or False,
        raising=False,
    )
    monkeypatch.setattr(
        S,
        "settings_snapshot",
        lambda: (_ for _ in ()).throw(AssertionError("usage endpoint must not load settings snapshot")),
    )

    provider = TestClient(A.app).get("/ai/usage").json()["provider"]
    assert provider["key_present"] is False
    assert "key_configured" not in provider
    assert calls == ["DEEPSEEK_API_KEY"]


def test_ai_usage_endpoint_reports_unlimited_cap(store, monkeypatch):
    import scribe3.app as A
    from scribe3 import settings as S

    A.set_store(store)
    public = {"llm.model": "deepseek-chat", "SCRIBE3_DAILY_CALL_CAP": 0}
    monkeypatch.setattr(S, "get_public_setting", public.__getitem__, raising=False)
    L._reset_daily_counter()
    U.tick(cap=0)
    cap = TestClient(A.app).get("/ai/usage").json()["cap"]
    assert cap == {
        "cap": 0,
        "used_today": 1,
        "remaining": None,
        "unlimited": True,
        "scope": "shared",
    }
    L._reset_daily_counter()


def test_ai_usage_endpoint_reads_one_consistent_cap_snapshot(store, monkeypatch):
    """热设置/并发变化时，cap 对象只能由同一次 cap 与 used 快照计算。"""
    import scribe3.app as A
    from scribe3 import settings as S

    A.set_store(store)
    cap_values = iter((100, 200))
    used_values = iter(((4, "shared"), (90, "process")))
    calls = {"model": 0, "cap": 0, "used": 0}

    def varying_public(key):
        if key == "llm.model":
            calls["model"] += 1
            return "deepseek-chat"
        if key == "SCRIBE3_DAILY_CALL_CAP":
            calls["cap"] += 1
            return next(cap_values)
        raise AssertionError(f"unexpected public setting: {key}")

    def varying_used():
        calls["used"] += 1
        return next(used_values)

    monkeypatch.setattr(S, "get_public_setting", varying_public, raising=False)
    monkeypatch.setattr(U, "used_today", varying_used)
    cap = TestClient(A.app).get("/ai/usage").json()["cap"]
    assert cap == {
        "cap": 100,
        "used_today": 4,
        "remaining": 96,
        "unlimited": False,
        "scope": "shared",
    }
    assert calls == {"model": 1, "cap": 1, "used": 1}


def test_ai_usage_endpoint_store_failure_failsoft(store, monkeypatch):
    """store 聚合挂 → 只回稳定错误码，底层异常/secret 不序列化。"""
    import scribe3.app as A
    A.set_store(store)
    secret_sentinel = "usage-summary-private-sentinel"
    monkeypatch.setattr(type(store), "usage_summary",
                        lambda self, days=7: (_ for _ in ()).throw(RuntimeError(
                            f"Authorization: Bearer {secret_sentinel}"
                        )))
    r = TestClient(A.app).get("/ai/usage")
    assert r.status_code == 200
    assert r.json()["tokens"] == {"days": [], "error": "usage_summary_unavailable"}
    serialized = json.dumps(r.json(), ensure_ascii=False)
    assert secret_sentinel not in serialized
    assert "Authorization" not in serialized
    assert "Bearer" not in serialized

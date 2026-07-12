"""Phase 2 读点迁移:flags/llm/critique/memory 逐步接设置中心,热生效。"""
import pytest
from scribe3 import settings


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    settings.invalidate_cache()
    yield
    settings.invalidate_cache()


def test_flag_enabled_reads_settings_db():
    from scribe3.context_cache import flag_enabled
    assert flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is False   # 字节等价:无覆盖=关
    settings.put_setting("SCRIBE3_MEMORY_FABRIC_V1", True)
    assert flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is True    # 热生效,无需重启


def test_flag_enabled_env_still_works(monkeypatch):
    from scribe3.context_cache import flag_enabled
    monkeypatch.setenv("SCRIBE3_SPECTRON_SHADOW", "on")
    settings.invalidate_cache()
    assert flag_enabled("SCRIBE3_SPECTRON_SHADOW") is True     # env 路径不破坏


def test_flag_enabled_unknown_name_falls_back_env(monkeypatch):
    from scribe3.context_cache import flag_enabled
    monkeypatch.setenv("SOME_FUTURE_FLAG", "1")
    assert flag_enabled("SOME_FUTURE_FLAG") is True            # 未登记名回落旧 env 语义


def test_context_snapshot_flag_reads_settings_db():
    """消除双路径分裂:context_service 的判定也必须吃到 DB 覆盖。"""
    from scribe3 import context_service
    assert context_service.context_snapshot_flag_enabled() is False   # 字节等价:无覆盖=关
    settings.put_setting("SCRIBE3_CONTEXT_SNAPSHOT_V1", True)
    assert context_service.context_snapshot_flag_enabled() is True    # 热生效


def test_assembler_flag_reads_settings_db():
    """消除双路径分裂:app 写作链的 assembler 判定也必须吃到 DB 覆盖。"""
    from scribe3.app import _context_assembler_enabled
    assert _context_assembler_enabled() is False                       # 字节等价:无覆盖=关
    settings.put_setting("SCRIBE3_CONTEXT_ASSEMBLER_V1", True)
    assert _context_assembler_enabled() is True                        # 热生效


def test_llm_daily_cap_hot(monkeypatch):
    import scribe3.llm as llm
    calls = {}
    monkeypatch.setattr("scribe3.usage.tick", lambda cap: calls.setdefault("cap", cap))
    settings.put_setting("SCRIBE3_DAILY_CALL_CAP", 42)
    llm._tick_daily()
    assert calls["cap"] == 42          # 改日帽下一次调用即生效,无需重启


def test_llm_model_default_from_settings():
    import scribe3.llm as llm
    settings.put_setting("llm.model", "test-model-x")
    assert llm.default_model() == "test-model-x"
    assert llm.max_retries() == 3

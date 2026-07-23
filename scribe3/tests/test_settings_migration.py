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
    assert flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is True    # 产品默认开
    settings.put_setting("SCRIBE3_MEMORY_FABRIC_V1", False)
    assert flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is False   # DB 覆盖热生效
    settings.put_setting("SCRIBE3_MEMORY_FABRIC_V1", True)
    assert flag_enabled("SCRIBE3_MEMORY_FABRIC_V1") is True


def test_removed_nonfunctional_flags_are_not_user_settings():
    keys = {item.key for item in settings.REGISTRY}
    assert "SCRIBE3_SPECTRON_SHADOW" not in keys
    assert "SCRIBE3_CONTEXT_ASSEMBLER_V1" not in keys
    with pytest.raises(KeyError):
        settings.put_setting("SCRIBE3_SPECTRON_SHADOW", True)
    with pytest.raises(KeyError):
        settings.put_setting("SCRIBE3_CONTEXT_ASSEMBLER_V1", True)


def test_flag_enabled_unknown_name_falls_back_env(monkeypatch):
    from scribe3.context_cache import flag_enabled
    monkeypatch.setenv("SOME_FUTURE_FLAG", "1")
    assert flag_enabled("SOME_FUTURE_FLAG") is True            # 未登记名回落旧 env 语义


def test_context_snapshot_flag_reads_settings_db():
    """消除双路径分裂:context_service 的判定也必须吃到 DB 覆盖。"""
    from scribe3 import context_service
    assert context_service.context_snapshot_flag_enabled() is True   # 产品默认开
    settings.put_setting("SCRIBE3_CONTEXT_SNAPSHOT_V1", False)
    assert context_service.context_snapshot_flag_enabled() is False  # DB 覆盖热生效
    settings.put_setting("SCRIBE3_CONTEXT_SNAPSHOT_V1", True)
    assert context_service.context_snapshot_flag_enabled() is True


def test_assembler_compatibility_capability_is_always_enabled():
    """旧能力键只表达统一内核事实，不再是用户可切换设置。"""
    from scribe3.app import _context_assembler_enabled
    assert _context_assembler_enabled() is True


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


def test_critique_thresholds_hot():
    from scribe3.critique import find_near_duplicate_paragraphs
    a = "他躺在自己的棺材里,数着头顶的木纹,一直数到天亮才闭眼。"
    b = "他躺在自己的棺材里,数着头顶的木纹,数到三更便闭了眼。"
    text = a + "\n" + b
    assert find_near_duplicate_paragraphs(text) != []          # 默认 0.7 命中
    settings.put_setting("craft.near_dup_sim", 0.99)
    assert find_near_duplicate_paragraphs(text) == []          # 调高阈值热生效


def test_critique_banned_density_hot():
    from scribe3 import critique
    settings.put_setting("craft.banned_density_per_k", 45.0)   # 注册表 max=50,99 越界
    assert critique._th("craft.banned_density_per_k") == 45.0


def test_memory_weights_hot():
    from scribe3 import memory_retrieval as mr
    assert mr.channel_weights()["structured"] == 2.0
    settings.put_setting("memory.weight_structured", 5.0)
    assert mr.channel_weights()["structured"] == 5.0
    settings.put_setting("memory.half_life_working", 7)
    assert mr.half_life_days()["working"] == 7

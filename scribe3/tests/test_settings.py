import json
import pytest
from scribe3 import settings, settings_store


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    settings.invalidate_cache()
    yield
    settings.invalidate_cache()


def test_priority_default_env_db(monkeypatch):
    # 默认值
    assert settings.get_setting("SCRIBE3_DAILY_CALL_CAP") == 500
    # env 覆盖默认
    monkeypatch.setenv("SCRIBE3_DAILY_CALL_CAP", "600")
    settings.invalidate_cache()
    assert settings.get_setting("SCRIBE3_DAILY_CALL_CAP") == 600
    # DB 覆盖 env
    settings.put_setting("SCRIBE3_DAILY_CALL_CAP", 800)
    assert settings.get_setting("SCRIBE3_DAILY_CALL_CAP") == 800


def test_bool_flag_env_semantics(monkeypatch):
    # 与 context_cache._TRUE 口径逐字一致:'1'/'true'/'yes'/'on' 为真
    assert settings.get_setting("SCRIBE3_MEMORY_FABRIC_V1") is False
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "on")
    settings.invalidate_cache()
    assert settings.get_setting("SCRIBE3_MEMORY_FABRIC_V1") is True


def test_validation_rejects_out_of_range():
    with pytest.raises(ValueError):
        settings.put_setting("SCRIBE3_DAILY_CALL_CAP", -1)
    with pytest.raises(ValueError):
        settings.put_setting("craft.near_dup_sim", 2.0)   # max 1.0
    with pytest.raises(KeyError):
        settings.put_setting("no.such.key", 1)


def test_reset_falls_back():
    settings.put_setting("craft.near_dup_sim", 0.9)
    assert settings.get_setting("craft.near_dup_sim") == 0.9
    settings.reset_setting("craft.near_dup_sim")
    assert settings.get_setting("craft.near_dup_sim") == 0.7


def test_dotted_keys_ignore_env(monkeypatch):
    # 点分新键不受同名 env 影响(env 只对全大写既有键生效)
    monkeypatch.setenv("craft.near_dup_sim", "0.1")
    settings.invalidate_cache()
    assert settings.get_setting("craft.near_dup_sim") == 0.7


def test_snapshot_masks_secret():
    settings.put_setting("SCRIBE3_API_TOKEN", "tok-abc")
    snap = {s["key"]: s for s in settings.settings_snapshot()}
    item = snap["SCRIBE3_API_TOKEN"]
    assert item["value"] is None and item["is_set"] is True
    assert "tok-abc" not in json.dumps(snap, ensure_ascii=False)
    # 内部读取仍拿真值
    assert settings.get_setting("SCRIBE3_API_TOKEN") == "tok-abc"


def test_hot_write_invalidates_same_process():
    settings.put_setting("craft.banned_density_per_k", 5.0)
    assert settings.get_setting("craft.banned_density_per_k") == 5.0  # 无需等 TTL

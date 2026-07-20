import json
import os

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
    assert settings.get_setting("SCRIBE3_DAILY_CALL_CAP") == 0
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


def test_is_set_semantics_for_nonempty_default_secret(monkeypatch):
    # is_set 语义 = 是否被显式配置过;非空默认值(root)不算已配置
    monkeypatch.delenv("SCRIBE3_SURREAL_PASS", raising=False)
    snap = {s["key"]: s for s in settings.settings_snapshot()}
    assert snap["SCRIBE3_SURREAL_PASS"]["is_set"] is False
    settings.put_setting("SCRIBE3_SURREAL_PASS", "s3cr3t")
    snap = {s["key"]: s for s in settings.settings_snapshot()}
    assert snap["SCRIBE3_SURREAL_PASS"]["is_set"] is True
    assert snap["SCRIBE3_SURREAL_PASS"]["value"] is None  # 仍然掩码


def test_coerce_int_rejects_fractional_float():
    # int 键收到非整数 float 不许静默截断
    with pytest.raises(ValueError):
        settings.put_setting("SCRIBE3_LIVE_MAX", 3.5)
    # 整数值 float 可接受(无信息丢失)
    settings.put_setting("SCRIBE3_LIVE_MAX", 4.0)
    assert settings.get_setting("SCRIBE3_LIVE_MAX") == 4


def test_coerce_wraps_typeerror_as_valueerror():
    # int/float 收到 None 等不可转值,统一抛 ValueError(与 docstring 契约一致)
    with pytest.raises(ValueError):
        settings.put_setting("SCRIBE3_LIVE_MAX", None)
    with pytest.raises(ValueError):
        settings.put_setting("craft.near_dup_sim", None)


def test_apply_restart_overrides_injects_env(monkeypatch):
    # str 项:DB 覆盖灌进 os.environ
    monkeypatch.delenv("SCRIBE3_WORK", raising=False)
    settings.put_setting("SCRIBE3_WORK", "book2")
    settings.apply_restart_overrides()
    assert os.environ["SCRIBE3_WORK"] == "book2"
    # bool 项(注册表 restart 项现无 bool,临时注册验证小写序列化)
    fake = settings.Setting("SCRIBE3_FAKE_RESTART_BOOL", "flags", "bool", False, "restart", "测试用")
    monkeypatch.setattr(settings, "REGISTRY", settings.REGISTRY + (fake,))
    monkeypatch.setitem(settings._BY_KEY, fake.key, fake)
    monkeypatch.delenv(fake.key, raising=False)
    settings_store.set_override(fake.key, json.dumps(True))
    settings.invalidate_cache()
    settings.apply_restart_overrides()
    assert os.environ[fake.key] == "true"   # 小写,符合 _TRUE 口径


def test_apply_restart_overrides_skips_bad_values(monkeypatch):
    monkeypatch.delenv("SCRIBE3_LIVE_MAX", raising=False)
    monkeypatch.delenv("SCRIBE3_READ_MCP_LABEL", raising=False)
    # 坏值(非法 JSON)被跳过,好值照常灌注
    settings_store.set_override("SCRIBE3_LIVE_MAX", "not-a-json{{{")
    settings_store.set_override("SCRIBE3_READ_MCP_LABEL", json.dumps("ok_label"))
    settings.invalidate_cache()
    settings.apply_restart_overrides()
    assert "SCRIBE3_LIVE_MAX" not in os.environ
    assert os.environ["SCRIBE3_READ_MCP_LABEL"] == "ok_label"
    # 超范围值(max 64)同样跳过
    settings_store.set_override("SCRIBE3_LIVE_MAX", json.dumps(999))
    settings.invalidate_cache()
    settings.apply_restart_overrides()
    assert "SCRIBE3_LIVE_MAX" not in os.environ


def test_ttl_converges_cross_process(monkeypatch):
    import time as _time
    # 先热缓存
    assert settings.get_setting("craft.near_dup_sim") == 0.7
    # 模拟另一进程直接写存储(绕过本进程 put_setting 的缓存失效)
    settings_store.set_override("craft.near_dup_sim", json.dumps(0.55))
    # TTL 未到:仍读缓存旧值
    assert settings.get_setting("craft.near_dup_sim") == 0.7
    # 时间前进 2s+:自然收敛看到新值
    base = _time.monotonic()
    monkeypatch.setattr(settings.time, "monotonic", lambda: base + 3.0)
    assert settings.get_setting("craft.near_dup_sim") == 0.55
    monkeypatch.undo()
    # invalidate_cache 也能立即看到
    settings_store.set_override("craft.near_dup_sim", json.dumps(0.44))
    settings.invalidate_cache()
    assert settings.get_setting("craft.near_dup_sim") == 0.44


def test_bad_override_warns_once_per_key(caplog):
    import logging
    settings._warned_keys.clear()
    settings_store.set_override("craft.near_dup_sim", "not-a-json{{{")
    settings.invalidate_cache()
    with caplog.at_level(logging.WARNING, logger="scribe3.settings"):
        assert settings.get_setting("craft.near_dup_sim") == 0.7  # 回落默认
        assert settings.get_setting("craft.near_dup_sim") == 0.7
    hits = [r for r in caplog.records if "craft.near_dup_sim" in r.getMessage()]
    assert len(hits) == 1   # 按 key 只告警一次,防日志风暴

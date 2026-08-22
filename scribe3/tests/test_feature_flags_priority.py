"""get_flag 三级：SQLite 台账 > env > FLAG_REGISTRY 默认。"""
from __future__ import annotations

import json
import os

from scribe3 import feature_flags as ff
from scribe3 import settings_store


def test_get_flag_db_beats_env_beats_default(monkeypatch, tmp_path):
    key = "SCRIBE3_RECALL_PLAYBOOK"
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "flags.sqlite3"))
    monkeypatch.delenv(key, raising=False)

    assert ff.get_flag(key) == "1"

    monkeypatch.setenv(key, "1")
    assert ff.get_flag(key) == "1"

    settings_store.set_override(key, json.dumps(False))
    assert ff.get_flag(key) == "0"
    assert ff.flag_truthy(key) is False

    settings_store.set_override(key, json.dumps(True))
    assert ff.flag_truthy(key) is True

    settings_store.delete_override(key)
    assert ff.get_flag(key) == "1"


def test_hot_flag_db_override_injected_to_env(monkeypatch, tmp_path):
    from scribe3 import settings
    key = "SCRIBE3_HYBRID_SEARCH_NATIVE"
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "hot.sqlite3"))
    monkeypatch.delenv(key, raising=False)
    settings_store.set_override(key, json.dumps(False))
    settings.invalidate_cache()
    settings.apply_restart_overrides()
    assert os.environ.get(key) == "false"
    assert ff.flag_truthy(key) is False


def test_get_flag_default_when_unset(monkeypatch, tmp_path):
    key = "SCRIBE3_OUTLINE_STATUS_GATE"
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "flags2.sqlite3"))
    monkeypatch.delenv(key, raising=False)
    assert ff.get_flag(key) == "1"
    assert ff.flag_truthy(key) is True


def test_overlap_keys_share_flag_registry_name():
    from scribe3.settings import REGISTRY
    flags = {f.name: f.default for f in ff.FLAG_REGISTRY}
    settings = {s.key: s.default for s in REGISTRY if s.key in flags}
    overlap = set(settings)
    assert len(overlap) == 61
    # 运行时读值走 get_flag（台账>env>FLAG_REGISTRY）。设置中心只做展示/写入，
    # 不再另起旗名。个别键的展示默认与 FLAG 字符串默认类型不同，以 FLAG_REGISTRY 为准。

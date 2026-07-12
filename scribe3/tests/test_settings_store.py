import json
from scribe3 import settings_store as ss


def test_override_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    assert ss.get_all_overrides() == {}
    ss.set_override("SCRIBE3_DAILY_CALL_CAP", json.dumps(800), old_json=None)
    assert json.loads(ss.get_all_overrides()["SCRIBE3_DAILY_CALL_CAP"]) == 800
    ss.delete_override("SCRIBE3_DAILY_CALL_CAP", old_json=json.dumps(800))
    assert ss.get_all_overrides() == {}


def test_audit_rows_masked_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    ss.set_override("SCRIBE3_API_TOKEN", json.dumps("tok-123"), old_json=None, mask=True)
    rows = ss.audit_rows(limit=10)
    assert rows[0]["key"] == "SCRIBE3_API_TOKEN"
    assert "tok-123" not in json.dumps(rows, ensure_ascii=False)  # 审计绝不落明文
    assert rows[0]["new"] == "«secret»"


def test_read_fail_soft(tmp_path, monkeypatch):
    # 路径指向不可写目录仍不抛:读回空 dict(fail-soft),写才抛
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", "/dev/null/nope/s.sqlite3")
    assert ss.get_all_overrides() == {}

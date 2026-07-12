import json
from scribe3 import settings_store as ss


def test_override_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    assert ss.get_all_overrides() == {}
    ss.set_override("SCRIBE3_DAILY_CALL_CAP", json.dumps(800))
    assert json.loads(ss.get_all_overrides()["SCRIBE3_DAILY_CALL_CAP"]) == 800
    ss.delete_override("SCRIBE3_DAILY_CALL_CAP")
    assert ss.get_all_overrides() == {}


def test_audit_rows_masked_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    ss.set_override("SCRIBE3_API_TOKEN", json.dumps("tok-123"), mask=True)
    rows = ss.audit_rows(limit=10)
    assert rows[0]["key"] == "SCRIBE3_API_TOKEN"
    assert "tok-123" not in json.dumps(rows, ensure_ascii=False)  # 审计绝不落明文
    assert rows[0]["new"] == "«secret»"


def test_read_fail_soft(tmp_path, monkeypatch):
    # 路径指向不可写目录仍不抛:读回空 dict(fail-soft),写才抛
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", "/dev/null/nope/s.sqlite3")
    assert ss.get_all_overrides() == {}


def test_upsert_same_key_audit_old_atomic(tmp_path, monkeypatch):
    # 同 key 二次 set:值为最新;审计新增一条且 old=第一次的值(事务内原子读,不信调用方)
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    ss.set_override("SCRIBE3_DAILY_CALL_CAP", json.dumps(800))
    ss.set_override("SCRIBE3_DAILY_CALL_CAP", json.dumps(900))
    assert json.loads(ss.get_all_overrides()["SCRIBE3_DAILY_CALL_CAP"]) == 900
    rows = ss.audit_rows(limit=10)
    assert len(rows) == 2
    assert rows[0]["old"] == json.dumps(800)
    assert rows[0]["new"] == json.dumps(900)
    assert rows[1]["old"] is None


def test_delete_audit_records_old(tmp_path, monkeypatch):
    # delete 后审计存在 old=旧值 / new=None 的记录
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    ss.set_override("SCRIBE3_DAILY_CALL_CAP", json.dumps(800))
    ss.delete_override("SCRIBE3_DAILY_CALL_CAP")
    rows = ss.audit_rows(limit=10)
    assert rows[0]["old"] == json.dumps(800)
    assert rows[0]["new"] is None


def test_sensitive_key_masked_without_flag(tmp_path, monkeypatch):
    # 调用方忘传 mask,key 含 TOKEN 也绝不落明文(存储层兜底)
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    ss.set_override("SCRIBE3_API_TOKEN", json.dumps("tok-456"))
    rows = ss.audit_rows(limit=10)
    assert "tok-456" not in json.dumps(rows, ensure_ascii=False)
    assert rows[0]["new"] == "«secret»"
    ss.delete_override("SCRIBE3_API_TOKEN")
    rows = ss.audit_rows(limit=10)
    assert "tok-456" not in json.dumps(rows, ensure_ascii=False)
    assert rows[0]["old"] == "«secret»"
    assert rows[0]["new"] is None

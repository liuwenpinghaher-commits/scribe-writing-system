import pytest
from fastapi.testclient import TestClient

from scribe3 import gateway_files as gf


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    d = tmp_path / "profiles" / "scribe3"
    d.mkdir(parents=True)
    (d / "SOUL.md").write_text("我是主编", encoding="utf-8")
    (d / ".env").write_text("API_SERVER_PORT=8643\nAPI_SERVER_KEY=sk-secret\n", encoding="utf-8")
    return tmp_path


def test_list_masks_env_secrets(home):
    files = {f["id"]: f for f in gf.list_files()}
    soul = files["scribe3/SOUL.md"]
    assert soul["content"] == "我是主编" and soul["exists"]
    env = files["scribe3/.env"]
    assert "sk-secret" not in env["content"]
    assert "API_SERVER_KEY=••••" in env["content"]


def test_write_requires_hash_and_backs_up(home):
    files = {f["id"]: f for f in gf.list_files()}
    soul = files["scribe3/SOUL.md"]
    gf.write_file("scribe3/SOUL.md", "我是新主编", base_sha256=soul["sha256"])
    assert (home / "profiles" / "scribe3" / "SOUL.md").read_text(encoding="utf-8") == "我是新主编"
    baks = list((home / "profiles" / "scribe3").glob("SOUL.md.bak.*"))
    assert len(baks) == 1 and baks[0].read_text(encoding="utf-8") == "我是主编"
    with pytest.raises(gf.StaleFileError):
        gf.write_file("scribe3/SOUL.md", "再改", base_sha256=soul["sha256"])   # hash 已变 → 409


def test_masked_env_lines_restored_on_save(home):
    files = {f["id"]: f for f in gf.list_files()}
    env = files["scribe3/.env"]
    edited = env["content"].replace("API_SERVER_PORT=8643", "API_SERVER_PORT=9999")
    gf.write_file("scribe3/.env", edited, base_sha256=env["sha256"])
    saved = (home / "profiles" / "scribe3" / ".env").read_text(encoding="utf-8")
    assert "API_SERVER_PORT=9999" in saved
    assert "API_SERVER_KEY=sk-secret" in saved   # 掩码行原样还原,密钥不丢


def test_whitelist_rejects_traversal(home):
    with pytest.raises(gf.NotAllowedError):
        gf.write_file("../outside.txt", "x", base_sha256="")
    with pytest.raises(gf.NotAllowedError):
        gf.write_file("scribe3/config.yaml/../../../etc/passwd", "x", base_sha256="")


@pytest.fixture()
def client(home, monkeypatch, tmp_path):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    from scribe3 import settings
    settings.invalidate_cache()
    import scribe3.app as A
    return TestClient(A.app)


def test_api_put_rejects_whitelist_outside_403(client):
    r = client.put("/gateway/files", json={
        "id": "scribe3/../../etc/passwd", "content": "x", "base_sha256": "",
    })
    assert r.status_code == 403


def test_api_put_stale_hash_409(client):
    files = {f["id"]: f for f in gf.list_files()}
    soul = files["scribe3/SOUL.md"]
    r = client.put("/gateway/files", json={
        "id": "scribe3/SOUL.md", "content": "手滑改动", "base_sha256": "deadbeef" + soul["sha256"][8:],
    })
    assert r.status_code == 409

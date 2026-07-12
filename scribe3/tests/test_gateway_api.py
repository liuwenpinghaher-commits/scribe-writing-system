import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    from scribe3 import settings
    settings.invalidate_cache()
    import scribe3.app as A
    return TestClient(A.app)


def test_gateway_status_shape(client, monkeypatch):
    import httpx
    def fake_get(url, timeout):
        class R: status_code = 200
        if "8643" in url:
            return R()
        raise httpx.ConnectError("down")
    monkeypatch.setattr("httpx.get", fake_get)
    r = client.get("/gateway/status")
    assert r.status_code == 200
    by = {g["name"]: g for g in r.json()["gateways"]}
    assert by["responses"]["online"] is True
    assert by["default"]["online"] is False
    assert by["runs"]["profile"] == "scribe3_write"


def test_gateway_status_401_counts_as_online(client, monkeypatch):
    # 钉住语义:online = 端口有 HTTP 响应(<500)。401 鉴权失败也算在线,
    # 防止未来被改成 ==200 导致鉴权失败误报红灯。
    def fake_get(url, timeout):
        class R: status_code = 401
        return R()
    monkeypatch.setattr("httpx.get", fake_get)
    r = client.get("/gateway/status")
    assert r.status_code == 200
    gateways = r.json()["gateways"]
    assert len(gateways) == 3
    assert all(g["online"] is True for g in gateways)


def test_gateway_restart_polls(client, monkeypatch):
    ran = {}
    monkeypatch.setattr("os.path.isfile", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: ran.setdefault("cmd", a[0]))
    monkeypatch.setattr("httpx.get", lambda url, timeout: type("R", (), {"status_code": 200})())
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.post("/gateway/restart", json={"profile": "scribe3"})
    assert r.status_code == 200 and r.json()["online"] is True
    assert "nohup" in ran["cmd"] and "-p scribe3" in ran["cmd"]


def test_gateway_restart_rejects_unknown_profile(client):
    assert client.post("/gateway/restart", json={"profile": "evil"}).status_code == 422


def test_gateway_restart_missing_hermes_bin_fails_fast(client, tmp_path, monkeypatch):
    # hermes CLI 不存在时预检直接失败(毫秒级),不空等 30s 轮询、不拉起进程。
    from scribe3 import settings
    settings.put_setting("gateway.hermes_bin", str(tmp_path / "nope"))
    ran = {}
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: ran.setdefault("cmd", a[0]))
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.post("/gateway/restart", json={"profile": "scribe3"})
    assert r.status_code == 200
    body = r.json()
    assert body["online"] is False and "不存在" in body["message"]
    assert "cmd" not in ran  # 预检失败,绝不拉起进程


def test_gateway_restart_poll_timeout_reports_failure(client, monkeypatch):
    # 钉住"不假成功"铁律:30 轮探活全失败 → online False + 如实报文案。
    import httpx
    monkeypatch.setattr("os.path.isfile", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: None)
    def raise_get(url, timeout):
        raise httpx.ConnectError("down")
    monkeypatch.setattr("httpx.get", raise_get)
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.post("/gateway/restart", json={"profile": "scribe3"})
    assert r.status_code == 200
    body = r.json()
    assert body["online"] is False and "未探活成功" in body["message"]


def test_dashboard_status(client, monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, timeout: type("R", (), {"status_code": 200})())
    r = client.get("/gateway/dashboard/status")
    assert r.status_code == 200 and r.json()["online"] is True
    assert "9119" in r.json()["url"]


def test_dashboard_start_polls_and_reports(client, monkeypatch):
    ran = {}
    monkeypatch.setattr("os.path.isfile", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: ran.setdefault("cmd", a[0]))
    monkeypatch.setattr("httpx.get", lambda url, timeout: type("R", (), {"status_code": 200})())
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.post("/gateway/dashboard/start")
    assert r.status_code == 200 and r.json()["online"] is True
    assert "nohup" in ran["cmd"] and "dashboard --no-open" in ran["cmd"]


def test_dashboard_start_missing_bin_fails_fast(client, monkeypatch):
    ran = {}
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: ran.setdefault("cmd", a[0]))
    from scribe3 import settings as S
    S.put_setting("gateway.hermes_bin", "/nope/hermes")
    r = client.post("/gateway/dashboard/start")
    assert r.json()["online"] is False and "cmd" not in ran

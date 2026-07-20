"""统一设置中心 · Task 3:/settings REST 四端点 TDD。

契约:
- GET /settings:全量元数据(值/来源/默认/danger,secret 掩码)。
- GET /settings/audit:变更审计(必须先于 /settings/{key} 注册,防被吞)。
- PUT /settings/{key}:校验写入 SQLite 覆盖台账,越界 422,未登记键 404。
- POST /settings/{key}/reset:删覆盖值回落 env/默认。

测试绝不碰生产 SQLite 台账(SCRIBE3_SETTINGS_DB 隔离到 tmp_path),且不需要
真实 SurrealDB(/settings 端点不碰 store)。
"""
import pytest
from fastapi.testclient import TestClient

import scribe3.app as A


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("SCRIBE3_DAILY_CALL_CAP", raising=False)
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "s.sqlite3"))
    from scribe3 import settings
    settings.invalidate_cache()
    return TestClient(A.app)


def test_get_settings_metadata(client):
    r = client.get("/settings")
    assert r.status_code == 200
    items = {i["key"]: i for i in r.json()["settings"]}
    assert items["SCRIBE3_DAILY_CALL_CAP"]["value"] == 0
    assert items["SCRIBE3_DAILY_CALL_CAP"]["category"] == "llm"
    assert items["SCRIBE3_DAILY_CALL_CAP"]["desc"] == "0=无限，正整数=成本保险丝"
    assert items["SCRIBE3_SURREAL_PASS"]["value"] is None   # secret 永不回显


def test_put_validate_and_reset(client):
    assert client.put("/settings/SCRIBE3_DAILY_CALL_CAP", json={"value": 800}).status_code == 200
    items = {i["key"]: i for i in client.get("/settings").json()["settings"]}
    assert items["SCRIBE3_DAILY_CALL_CAP"]["value"] == 800
    assert items["SCRIBE3_DAILY_CALL_CAP"]["source"] == "db"
    assert client.put("/settings/SCRIBE3_DAILY_CALL_CAP", json={"value": -5}).status_code == 422
    assert client.put("/settings/no.such.key", json={"value": 1}).status_code == 404
    assert client.post("/settings/SCRIBE3_DAILY_CALL_CAP/reset").status_code == 200
    items = {i["key"]: i for i in client.get("/settings").json()["settings"]}
    assert items["SCRIBE3_DAILY_CALL_CAP"]["value"] == 0


def test_audit_endpoint(client):
    client.put("/settings/craft.near_dup_sim", json={"value": 0.8})
    rows = client.get("/settings/audit").json()["rows"]
    assert rows[0]["key"] == "craft.near_dup_sim"


def test_audit_limit_clamped_both_sides(client):
    # 负数 LIMIT 在 SQLite 语义 = 不限量(全表),必须在参数校验层双侧夹紧
    assert client.get("/settings/audit", params={"limit": -1}).status_code == 422
    assert client.get("/settings/audit", params={"limit": 500}).status_code == 422
    assert client.get("/settings/audit", params={"offset": -1}).status_code == 422
    assert client.get("/settings/audit", params={"limit": 200, "offset": 0}).status_code == 200


def test_put_settings_requires_bearer_token(client, monkeypatch):
    # _auth_middleware 每请求读模块级 A._API_TOKEN(非闭包快照),可直接 patch
    monkeypatch.setattr(A, "_API_TOKEN", "tok-x")
    assert client.put("/settings/SCRIBE3_DAILY_CALL_CAP", json={"value": 700}).status_code == 401
    r = client.put("/settings/SCRIBE3_DAILY_CALL_CAP", json={"value": 700},
                   headers={"Authorization": "Bearer tok-x"})
    assert r.status_code == 200

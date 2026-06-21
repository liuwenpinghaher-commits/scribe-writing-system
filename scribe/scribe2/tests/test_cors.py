"""CORS:前端(:3310)跨域调后端(:3320),浏览器预检 OPTIONS 必须放行。
缺 CORS 中间件时 OPTIONS /works → 405,前端报"无法连接领域 API"。
"""
from fastapi.testclient import TestClient

from scribe2.app import app


def test_cors_preflight_allows_browser_origin():
    c = TestClient(app)
    r = c.options("/works", headers={
        "Origin": "http://localhost:3310",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "x-owner-id",
    })
    assert r.status_code == 200, f"预检应放行,实得 {r.status_code}"
    assert r.headers.get("access-control-allow-origin"), "缺 Access-Control-Allow-Origin 头"

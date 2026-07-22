"""LIVE 路径凭证须与 store 同源(env/settings),禁止仅硬编码 root/root。"""
from __future__ import annotations

import inspect

import scribe3.live as live


def test_live_credentials_helper_uses_env(monkeypatch):
    monkeypatch.setenv("SCRIBE3_SURREAL_USER", "scribe3_app")
    monkeypatch.setenv("SCRIBE3_SURREAL_PASS", "not-root-secret")
    u, p = live._live_credentials()
    assert u == "scribe3_app"
    assert p == "not-root-secret"


def test_live_stream_source_has_no_hardcoded_root_signin():
    src = inspect.getsource(live)
    assert 'signin({"username": "root", "password": "root"})' not in src
    assert "_live_credentials" in src
    assert "SCRIBE3_SURREAL_USER" in src

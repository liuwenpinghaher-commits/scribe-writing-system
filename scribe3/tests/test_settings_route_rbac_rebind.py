"""Shipped path: settings_put after FunctionType rebind must not NameError; author denied."""
from __future__ import annotations

import types
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


def test_rebound_settings_put_author_denied_gateway(monkeypatch):
    """Reproduce production rebind: globals = app_impl-like dict with helpers injected."""
    from scribe3.api.routers import settings_gateway as sg
    from scribe3 import settings as S

    # Fake core namespace like app_impl
    core = types.ModuleType("fake_app_impl")
    core.__dict__.update({
        "HTTPException": HTTPException,
        # settings module free names used by put_setting path
    })
    # Inject what production _bind_and_register must inject
    core.__dict__["_request_is_admin"] = lambda: False  # author
    core.__dict__["_require_admin_api"] = sg._require_admin_api

    # Also need settings in globals for put - settings_put imports settings inside
    put = types.FunctionType(
        sg.settings_put.__code__,
        core.__dict__,
        "settings_put",
        sg.settings_put.__defaults__,
        sg.settings_put.__closure__,
    )
    # After rebind, LOAD_GLOBAL _request_is_admin must resolve
    assert "_request_is_admin" in put.__globals__

    # Author cannot write HERMES_API
    with pytest.raises(HTTPException) as ei:
        put("HERMES_API", SimpleNamespace(value="http://evil"))
    assert ei.value.status_code == 403

    # Author can write craft key (no 403 from audience)
    core.__dict__["_request_is_admin"] = lambda: False
    # put_setting may hit settings_store — monkeypatch
    monkeypatch.setattr(S, "put_setting", lambda k, v: {"key": k, "value": v, "effect": "hot"})
    # Need put to see S from import inside - import is local, ok
    out = put("craft.banned_density_per_k", SimpleNamespace(value=2.0))
    assert out["key"] == "craft.banned_density_per_k"


def test_rebound_settings_put_admin_allowed_gateway(monkeypatch):
    from scribe3.api.routers import settings_gateway as sg
    from scribe3 import settings as S

    core = types.ModuleType("fake_app_impl")
    core.__dict__["_request_is_admin"] = lambda: True
    core.__dict__["HTTPException"] = HTTPException
    put = types.FunctionType(
        sg.settings_put.__code__,
        core.__dict__,
        "settings_put",
        sg.settings_put.__defaults__,
        sg.settings_put.__closure__,
    )
    monkeypatch.setattr(S, "put_setting", lambda k, v: {"key": k, "value": v, "effect": "hot"})
    out = put("HERMES_API", SimpleNamespace(value="http://127.0.0.1:8642/v1"))
    assert out["key"] == "HERMES_API"


def test_bind_and_register_injects_helpers():
    """_bind_and_register must put helpers on app_impl."""
    from scribe3.api import app_impl as core
    from scribe3.api.routers import settings_gateway as sg
    # re-run bind
    sg._bind_and_register()
    assert callable(getattr(core, "_request_is_admin", None))
    assert callable(getattr(core, "_require_admin_api", None))


def test_codex_bind_injects_l1_helper():
    """重绑定后 add_char 等必须在 app_impl 里找得到 _codex_l1_http。"""
    from scribe3.api import app_impl as core
    from scribe3.api.routers import codex
    codex._bind_and_register()
    assert callable(getattr(core, "_codex_l1_http", None))

"""Hermes overlay 分档键存在性（git 内模板，不碰真 ~/.hermes）。"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HERMES = ROOT / "deploy" / "hermes"


def _load(name: str) -> dict:
    return yaml.safe_load((HERMES / name).read_text(encoding="utf-8"))


def test_default_overlay_fast_tier_and_empty_tools():
    d = _load("overlay.default.yaml")
    assert d["platform_toolsets"]["api_server"] == []
    assert d["agent"]["gateway_timeout"] == 300
    assert abs(float(d["compression"]["threshold"]) - 0.40) < 1e-6


def test_scribe3_overlay_mid_tier_read_only():
    d = _load("overlay.scribe3.yaml")
    assert d["platform_toolsets"]["api_server"] == ["scribe3_read"]
    assert d["agent"]["gateway_timeout"] == 900
    assert abs(float(d["compression"]["threshold"]) - 0.50) < 1e-6


def test_write_overlay_long_tier():
    d = _load("overlay.scribe3_write.yaml")
    assert set(d["platform_toolsets"]["api_server"]) == {"scribe3_read", "scribe3_write"}
    assert d["agent"]["gateway_timeout"] == 1800
    assert abs(float(d["compression"]["threshold"]) - 0.55) < 1e-6

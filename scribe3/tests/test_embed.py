"""嵌入缓存在固定目录，不进 macOS 临时文件夹。"""
from __future__ import annotations

import os


def test_fastembed_cache_defaults_off_tmpdir(monkeypatch, tmp_path):
    monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
    monkeypatch.delenv("SCRIBE3_FASTEMBED_CACHE", raising=False)
    from scribe3.embed import DEFAULT_FASTEMBED_CACHE, apply_fastembed_cache_env

    p = apply_fastembed_cache_env()
    assert p == DEFAULT_FASTEMBED_CACHE
    assert "/var/folders" not in p
    assert os.path.isdir(p)

    override = tmp_path / "fe"
    monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
    monkeypatch.setenv("SCRIBE3_FASTEMBED_CACHE", str(override))
    p2 = apply_fastembed_cache_env()
    assert p2 == str(override)
    assert override.is_dir()

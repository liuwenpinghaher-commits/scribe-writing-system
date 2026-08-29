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


def test_textembedding_gets_cache_dir_and_skips_hf_when_cached(monkeypatch, tmp_path):
    """本地已有模型时不许再去 HuggingFace 等超时。"""
    import scribe3.embed as E

    captured = {}

    class FakeTE:
        def __init__(self, model_name=None, cache_dir=None, **kw):
            captured["model_name"] = model_name
            captured["cache_dir"] = cache_dir
            captured["kw"] = kw

        def embed(self, texts):
            return [[0.0] * 4 for _ in texts]

    cache = tmp_path / "fe"
    cache.mkdir()
    (cache / "fast-bge-small-zh-v1.5").mkdir()
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(cache))
    monkeypatch.setattr("fastembed.TextEmbedding", FakeTE)
    E._model = None
    E._m()
    assert captured["cache_dir"] == str(cache)
    assert captured["kw"].get("local_files_only") is True
    E._model = None


def test_jieba_cache_defaults_off_tmpdir(monkeypatch, tmp_path):
    monkeypatch.delenv("SCRIBE3_JIEBA_CACHE", raising=False)
    from scribe3.runtime_cache import DEFAULT_JIEBA_CACHE, apply_jieba_cache_env

    p = apply_jieba_cache_env()
    assert p == DEFAULT_JIEBA_CACHE
    assert "/var/folders" not in p
    override = tmp_path / "jieba.cache"
    monkeypatch.setenv("SCRIBE3_JIEBA_CACHE", str(override))
    p2 = apply_jieba_cache_env()
    assert p2 == str(override)
    import jieba
    assert jieba.dt.cache_file == str(override)

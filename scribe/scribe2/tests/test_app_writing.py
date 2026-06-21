"""Build1:scribe2 REST 写作面——圣经 CRUD + 生成 action + 自动章记忆 ingest + memory。
LLM 经 app._complete(可 monkeypatch),无需 hermes 在跑。"""
from fastapi.testclient import TestClient

import scribe2.app as appmod
from scribe2.app import app, get_domain
from scribe2.conn import domain_from


def _setup(db):
    d = domain_from(db); d.s.init_schema()
    app.dependency_overrides[get_domain] = lambda: d
    return d, TestClient(app), {"X-Owner-Id": "u1"}


def test_bible_crud(db):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "九原渡"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/author-intent",
              json={"reader_feeling": "苍凉克制", "red_lines": ["不煽情"]}, headers=H)
        assert c.get(f"/works/{w}/author-intent", headers=H).json()["reader_feeling"] == "苍凉克制"
        c.post(f"/works/{w}/characters",
               json={"name": "渡叔", "motivation": "守渡四十年", "voice": "极静带谶语"}, headers=H)
        chars = c.get(f"/works/{w}/characters", headers=H).json()
        assert any(x["name"] == "渡叔" and x["voice"] == "极静带谶语" for x in chars)
        c.post(f"/works/{w}/foreshadows",
               json={"summary": "长明灯某夜灭", "chapter": 1, "importance": "high"}, headers=H)
        assert any(f["summary"] == "长明灯某夜灭"
                   for f in c.get(f"/works/{w}/foreshadows", headers=H).json())
    finally:
        app.dependency_overrides.clear()


def test_generate_action(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/author-intent", json={"reader_feeling": "苍凉克制"}, headers=H)
        c.post(f"/works/{w}/characters", json={"name": "渡叔", "voice": "极静带谶语"}, headers=H)
        seen = {}

        def fake(prompt, **k):
            seen["p"] = prompt
            return "渡叔立于船头,独眼望浊浪。"
        monkeypatch.setattr(appmod, "_complete", fake)
        r = c.post(f"/works/{w}/chapters/1/actions/continue",
                   json={"instruction": "写渡叔夜渡", "target_chars": 300}, headers=H)
        assert r.status_code == 200 and "渡叔立于船头" in r.json()["content"]
        assert "苍凉克制" in seen["p"] and "极静带谶语" in seen["p"] and "写渡叔夜渡" in seen["p"]
    finally:
        app.dependency_overrides.clear()


def test_ingest_builds_memory(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        ch = c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "夜渡"}, headers=H).json()["chapter_id"]
        c.post(f"/works/{w}/chapters/{ch}/prose",
               json={"content": "渡叔立于船头,独眼望浊浪,阿砚蜷在供桌下。"}, headers=H)
        monkeypatch.setattr(appmod, "_complete",
                            lambda prompt, **k: "第一章:渡叔夜渡,阿砚躲庙中。")
        r = c.post(f"/works/{w}/chapters/1/ingest", headers=H)
        assert r.status_code == 200
        mem = c.get(f"/works/{w}/memory", headers=H).json()
        assert any(m["seq"] == 1 for m in mem["chapters"])
        assert "渡叔夜渡" in mem["global"]    # 确定性 rollup 把章梗概拼进全局
    finally:
        app.dependency_overrides.clear()


def test_critique_and_consistency(db, monkeypatch):
    d, c, H = _setup(db)
    try:
        w = c.post("/works", json={"title": "书"}, headers=H).json()["work_id"]
        c.put(f"/works/{w}/author-intent", json={"reader_feeling": "苍凉克制"}, headers=H)
        ch = c.put(f"/works/{w}/chapters", json={"seq": 1, "title": "夜渡"}, headers=H).json()["chapter_id"]
        c.post(f"/works/{w}/chapters/{ch}/prose",
               json={"content": "渡叔立于船头,独眼望浊浪。"}, headers=H)
        # critique:mock 返回 8 维评分 JSON
        monkeypatch.setattr(appmod, "_complete", lambda p, **k: (
            '{"scores":{"texture":4,"surprise":3,"emotion_truth":4,"pace":4,'
            '"voice":5,"anti_slop":4,"intent_resonance":3,"coherence":4},'
            '"issues":["意外性不足"],"worst_dims":["surprise"]}'))
        r = c.post(f"/works/{w}/chapters/1/critique", json={"revise": False}, headers=H).json()
        assert r["critique"]["overall"] > 0 and len(r["critique"]["scores"]) == 8
        # consistency:mock 返回矛盾 flags
        monkeypatch.setattr(appmod, "_complete", lambda p, **k: '{"flags":["渡叔年龄前后矛盾"]}')
        chk = c.post(f"/works/{w}/chapters/1/check", headers=H).json()
        assert "渡叔年龄前后矛盾" in chk["flags"]
        flags = c.get(f"/works/{w}/consistency-flags", headers=H).json()
        assert any(f["detail"] == "渡叔年龄前后矛盾" for f in flags)
    finally:
        app.dependency_overrides.clear()

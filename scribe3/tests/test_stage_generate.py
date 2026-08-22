"""五层管线入口：旧阶段 410，落库走真实 store 协议。禁止 Surreal。"""
from __future__ import annotations

from scribe3.playbook.memory_store import TABLES
from scribe3.stage_generate import (
    _as_playbook_store,
    normalize_stage,
    stage_ready,
    stage_spec,
    thicken_stage,
)


def test_old_stage_names_are_gone():
    from scribe3.playbook.stages import reject_gone_stage
    for name in ("outline", "beats", "chapter_design", "plan"):
        hit = reject_gone_stage(name)
        assert hit is not None
        assert hit["http"] == 410
        assert "duty" in hit["message"]
    assert normalize_stage("write") == "final"
    assert reject_gone_stage("design") is None


def test_stage_spec_teaches_five_layers():
    spec = stage_spec("design")
    assert spec["short_kernel"] == "duty → design → deduce → draft → final"
    gone = stage_spec("outline")
    assert gone.get("gone") is True


def test_stage_ready_reads_frozen_row():
    class St:
        def get_frozen(self, table, seq):
            if table == "duty_card" and seq == 2:
                return {"status": "frozen", "sha": "abc"}
            return None

    hit = stage_ready({}, "design", store=St(), seq=2)
    assert hit["ok"] is True
    miss = stage_ready({}, "design", store=St(), seq=3)
    assert hit["ok"] is True
    assert miss["ok"] is False
    assert miss["code"] == "stage_not_ready"


def test_as_playbook_store_keeps_surreal_protocol():
    class SurrealLike:
        def get_frozen(self, table, seq):
            return None

        def insert(self, table, rec):
            return rec

        def next_version(self, table, seq):
            return 1

        def mark_superseded(self, table, seq, version):
            return None

    st = SurrealLike()
    assert _as_playbook_store(st) is st


def test_thicken_stage_persists_via_store_insert():
    inserts: list[tuple[str, str]] = []

    class St:
        def __init__(self):
            self.rows = {t: [] for t in TABLES}

        def list_versions(self, table, seq):
            return [dict(r) for r in self.rows[table] if int(r.get("seq") or 0) == int(seq)]

        def next_version(self, table, seq):
            vers = [int(r.get("version") or 0) for r in self.list_versions(table, seq)]
            return (max(vers) + 1) if vers else 1

        def get_frozen(self, table, seq):
            for rec in reversed(self.list_versions(table, seq)):
                if rec.get("status") == "frozen":
                    return rec
            return None

        def get_by_sha(self, table, sha):
            for rec in self.rows[table]:
                if rec.get("sha") == sha:
                    return rec
            return None

        def insert(self, table, rec):
            inserts.append((table, str(rec.get("status") or "")))
            self.rows[table].append(dict(rec))
            return rec

        def mark_superseded(self, table, seq, version):
            for rec in self.rows[table]:
                if int(rec.get("seq") or 0) == int(seq) and int(rec.get("version") or 0) == int(version):
                    rec["status"] = "superseded"

        def list_by_play_sha(self, table, play_sha):
            return []

        def characters(self):
            return [{"name": "沈烛若", "id": "role:沈烛若"}]

    def llm(prompt, max_tokens=2048, system="", temperature=0.8):
        if "立四件事" in prompt or "立\"责任\"" in prompt:
            import json
            return json.dumps({
                "must_happen": "沈烛若把碎片按回胸口",
                "bill": "四十二度成了他的常态",
                "who": ["沈烛若"],
                "forbidden_reveal": ["炉认主"],
                "line_to_touch": None,
            }, ensure_ascii=False)
        if "你是审稿的" in prompt or "五问" in prompt or "六问" in prompt or "七问" in prompt or "八问" in prompt or "九问" in prompt:
            import json
            return json.dumps({
                "answers": [{"q": 1, "evidence": "按回", "answer": "yes", "reason": "过"}],
                "verdict": "pass",
                "opinion": "",
            }, ensure_ascii=False)
        return "x"

    st = St()
    out = thicken_stage("duty", {}, llm_fn=llm, persist_fn=lambda f: None, seq=1, st=st)
    assert out.get("ok") is True, out
    assert ("duty_card", "frozen") in inserts
    assert st.get_frozen("duty_card", 1)


def test_thicken_final_skips_existing_prose_without_persist_or_llm():
    called = []
    persisted = []

    def llm(prompt, max_tokens=2048, **kw):
        called.append(prompt)
        return "x"

    def persist(fields):
        persisted.append(fields)

    out = thicken_stage(
        "final",
        {"prose": "墙比他想象中湿。" * 20},
        llm_fn=llm,
        persist_fn=persist,
        seq=1,
        extra="",
        st=None,
    )
    assert out.get("skipped") is True
    assert out.get("ok") is True
    assert "prose" not in out
    assert not called
    assert not persisted

    out2 = thicken_stage(
        "final",
        {"prose": "墙比他想象中湿。" * 20},
        llm_fn=llm,
        persist_fn=persist,
        seq=1,
        extra="force=1",
        st=None,
    )
    assert not out2.get("skipped")

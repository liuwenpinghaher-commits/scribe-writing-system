"""讨论驱动能力编排 · 驱动 shipped resolve/catalog/proposal/API。"""
from __future__ import annotations

import pytest

from scribe3.mcp._common import WRITE_GATED
from scribe3.orchestration.catalog import (
    CATALOG,
    all_write_tools_in_catalog,
    list_domains,
    primary_domain_ids,
)
from scribe3.orchestration.proposal import apply_proposal_ops, build_write_proposal
from scribe3.orchestration.resolve import (
    apply_ui_directive_events,
    evaluate_turn,
    resolve_work_package,
)
from scribe3.orchestration import package_state


@pytest.fixture(autouse=True)
def _clean_orch(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "orch.sqlite3"))
    package_state.clear_ram()
    yield
    package_state.clear_ram()


# —— Catalog 结构完备 ——

def test_catalog_covers_primary_domains():
    domains = set(list_domains())
    need = {
        "intent.northstar",
        "codex.character", "codex.faction", "codex.item", "codex.term", "codex.world_rule",
        "relation.character", "fact.proposition", "knowledge.record",
        "promise.plant", "promise.lifecycle", "motif.manage", "clue.manage",
        "structure.volume", "structure.chapter",
        "chapter.outline", "chapter.beats", "chapter.deduce",
        "prose.generate", "craft.rules", "qc.review",
    }
    assert need <= domains, f"缺域: {need - domains}"
    assert len(CATALOG) >= 20


def test_catalog_write_tools_subset_of_write_gated_or_empty():
    """世界写工具名须落在 WRITE_GATED；prose 域允许空写列表。"""
    for c in CATALOG:
        for t in c.get("write_tools") or ():
            assert t in WRITE_GATED, f"{c['domain']} tool {t} not in WRITE_GATED"
    # 至少一个写工具在 catalog 中
    assert all_write_tools_in_catalog() & WRITE_GATED


# —— Resolve 三样板域 ——

def test_resolve_character_write_intent():
    pkg = resolve_work_package("请把角色沈砚的恐惧写入设定库并审批", work="w1", chapter=3)
    assert pkg["domain"] == "codex.character"
    assert "s3_patch_character" in pkg["write_tools"] or "s3_add_character" in pkg["write_tools"]
    assert pkg["required_outcome"] == "write_proposal"
    assert pkg["use_world_write_run"] is True
    ui = pkg["ui_directive"]
    assert ui.get("entry") == "codex"
    assert (ui.get("node") or {}).get("type") == "character"
    assert "total_score" not in pkg


def test_resolve_outline_intent():
    pkg = resolve_work_package("请起草第12章大纲", work="w1", chapter=12)
    assert pkg["domain"] == "chapter.outline"
    assert "s3_patch_chapter_plan" in pkg["write_tools"] or "s3_patch_chapter_meta" in pkg["write_tools"]
    assert pkg["ui_directive"].get("phase") == "outline"
    assert pkg["chapter"] == 12 or (pkg.get("focus") or {}).get("ref") == 12


def test_resolve_promise_lifecycle_intent():
    pkg = resolve_work_package("请兑现第3章埋的伏笔", work="w1", chapter=5)
    assert pkg["domain"] in ("promise.lifecycle", "promise.plant")
    tools = set(pkg["write_tools"])
    assert tools & {
        "s3_advance_promise", "s3_plant_promise", "s3_touch_promise",
        "s3_abandon_promise", "s3_patch_promise",
    }
    assert pkg["required_outcome"] == "write_proposal"


def test_resolve_promise_plant_not_stolen_by_protagonist_word():
    """口语「埋一个承诺…主角…」不得被「主角」抢到 codex.character。"""
    pkg = resolve_work_package(
        "埋一个承诺：主角会在终局前揭开母亲失踪真相",
        work="w1",
        chapter=2,
    )
    assert pkg["domain"] == "promise.plant"
    assert "s3_plant_promise" in pkg["write_tools"]
    assert (pkg["ui_directive"].get("node") or {}).get("type") == "promise"


def test_resolve_prose_not_world_write():
    pkg = resolve_work_package("请写本章完整正文", work="w1", chapter=2, phase="final")
    assert pkg["domain"].startswith("prose.")
    assert pkg["use_world_write_run"] is False
    assert pkg["required_outcome"] == "prose_proposal"


# —— 空谈策略 ——

def test_evaluate_turn_empty_talk_incomplete():
    pkg = resolve_work_package("更新角色甲的档案", work="w")
    ev = evaluate_turn(pkg, tools_called=[], approved_writes=[])
    assert ev["status"] == "incomplete"
    assert ev["remedy"]["code"] == "empty_talk_no_write"
    assert ev["fake_written"] is False


def test_evaluate_turn_tools_without_approve_awaiting():
    pkg = resolve_work_package("写入角色乙", work="w")
    write = (pkg["write_tools"] or ["s3_add_character"])[0]
    ev = evaluate_turn(pkg, tools_called=[write], approved_writes=[])
    assert ev["status"] == "awaiting_approval"
    assert ev["status"] != "applied"


def test_evaluate_turn_approved_applied():
    pkg = resolve_work_package("写入角色丙", work="w")
    write = (pkg["write_tools"] or ["s3_patch_character"])[0]
    ev = evaluate_turn(pkg, tools_called=[write], approved_writes=[write])
    assert ev["status"] == "applied"


# —— 未批准不落库 ——

def test_proposal_reject_does_not_call_executor():
    pkg = resolve_work_package("埋一条伏笔铜炉", work="w", chapter=1)
    prop = build_write_proposal(pkg, [
        {"tool": "s3_plant_promise", "args": {"text": "铜炉", "setup_chapter": 1}, "label": "铜炉"},
    ])
    calls = []

    def plant(**kw):
        calls.append(kw)
        return {"status": "written", "id": "x"}

    out = apply_proposal_ops(prop, decision="reject", executors={"s3_plant_promise": plant})
    assert out["status"] == "declined"
    assert calls == []
    assert all(op["status"] == "declined" for op in out["ops"])


def test_proposal_approve_plants_via_executor():
    pkg = resolve_work_package("s3_plant_promise 埋铜炉", work="w", chapter=1)
    prop = build_write_proposal(pkg, [
        {"tool": "s3_plant_promise", "args": {"text": "铜炉三响", "setup_chapter": 1}},
    ])
    store = []

    def plant(**kw):
        store.append(kw.get("text"))
        return {"status": "written", "text": kw.get("text")}

    out = apply_proposal_ops(prop, decision="approve", executors={"s3_plant_promise": plant})
    assert out["status"] == "applied"
    assert store == ["铜炉三响"]


# —— UI directive 三域 ——

def test_ui_events_character_outline_promise():
    ch = resolve_work_package("更新角色沈砚设定", work="w")
    evs = apply_ui_directive_events(ch["ui_directive"])
    types = {e["type"] for e in evs}
    assert "s3-right-tab" in types
    assert "selection" in types or "s3-open-capability" in types
    sel = next((e for e in evs if e["type"] == "selection"), None)
    if sel:
        assert sel["detail"]["node"]["type"] == "character"

    ol = resolve_work_package("起草第7章大纲", work="w", chapter=7)
    evs2 = apply_ui_directive_events(ol["ui_directive"])
    phase_ev = next((e for e in evs2 if e["type"] == "s3-chapter-phase"), None)
    assert phase_ev is not None
    assert phase_ev["detail"]["phase"] == "outline"
    assert phase_ev["detail"]["seq"] == 7

    pr = resolve_work_package("兑现伏笔", work="w")
    evs3 = apply_ui_directive_events(pr["ui_directive"])
    assert any(
        e["type"] == "selection" and e["detail"]["node"]["type"] == "promise"
        for e in evs3
    )


# —— 持久化 ——

def test_package_state_persists_across_ram_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "p.sqlite3"))
    package_state.clear_ram()
    pkg = resolve_work_package("写入角色丁", work="bookA")
    package_state.set_active("bookA", pkg)
    package_state.clear_ram()
    again = package_state.get_active("bookA")
    assert again is not None
    assert again["domain"] == pkg["domain"]
    assert again["id"] == pkg["id"]


# —— HTTP ——

def test_http_orchestration_resolve_and_evaluate(monkeypatch, tmp_path):
    import scribe3.app as A
    from fastapi.testclient import TestClient
    from scribe3.orchestration import package_state

    monkeypatch.setenv("SCRIBE3_SETTINGS_DB", str(tmp_path / "http_orch.sqlite3"))
    package_state.clear_ram()

    class Mini:
        pass

    st = Mini()
    A.set_store(st, work="test")
    monkeypatch.setattr(A, "_store_for", lambda w="main": st, raising=False)
    c = TestClient(A.app)

    r = c.get("/orchestration/catalog?work=test")
    assert r.status_code == 200, r.text
    assert r.json()["count"] >= 20
    assert "codex.character" in r.json()["domains"]

    r = c.post("/orchestration/resolve?work=test", json={
        "message": "请更新角色沈砚的恐惧并写入",
        "chapter": 2,
        "activate": True,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["package"]["domain"] == "codex.character"
    assert body["use_world_write_run"] is True
    assert body["ui_events"]
    assert "total_score" not in body

    r2 = c.post("/orchestration/evaluate-turn?work=test", json={
        "tools_called": [],
        "approved_writes": [],
    })
    assert r2.status_code == 200, r2.text
    assert r2.json()["evaluation"]["status"] == "incomplete"

    # outline
    r3 = c.post("/orchestration/resolve?work=test", json={
        "message": "起草第9章大纲",
        "chapter": 9,
    })
    assert r3.json()["package"]["domain"] == "chapter.outline"
    assert r3.json()["package"]["ui_directive"]["phase"] == "outline"

    # promise plant approve execute
    r4 = c.post("/orchestration/resolve?work=test", json={
        "message": "s3_plant_promise 埋铜炉伏笔",
        "chapter": 1,
    })
    pkg = r4.json()["package"]
    assert "s3_plant_promise" in pkg["write_tools"]

    class PlantStore:
        def __init__(self):
            self.promises = []

        def plant_promise(self, text, setup_chapter, kind="promise", tier="chapter", resolution=""):
            row = {"id": "p1", "text": text, "setup_chapter": setup_chapter, "status": "open"}
            self.promises.append(row)
            return row

    st2 = PlantStore()
    monkeypatch.setattr(A, "_store_for", lambda w="main": st2, raising=False)
    prop = {
        "id": "prop_t",
        "ops": [{"tool": "s3_plant_promise", "args": {"text": "铜炉", "setup_chapter": 1}, "label": "铜炉"}],
        "ui_after": pkg.get("ui_directive"),
        "write_tools": pkg.get("write_tools"),
    }
    # 未批准 execute 路径用 decision reject
    r5 = c.post("/orchestration/proposal/apply?work=test", json={
        "proposal": prop, "decision": "reject", "execute": True,
    })
    assert r5.status_code == 200
    assert st2.promises == []

    r6 = c.post("/orchestration/proposal/apply?work=test", json={
        "proposal": prop, "decision": "approve", "execute": True,
    })
    assert r6.status_code == 200, r6.text
    assert len(st2.promises) == 1
    assert st2.promises[0]["text"] == "铜炉"

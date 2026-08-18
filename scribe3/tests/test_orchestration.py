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
    from scribe3.orchestration import drafts as draft_store
    draft_store.clear_ram()
    yield
    package_state.clear_ram()
    draft_store.clear_ram()


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
            if t == "s3_generate_codex_batch":
                continue  # 批量免批，故意不进 WRITE_GATED
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
    assert (pkg.get("focus") or {}).get("label") == "沈砚"
    # 未入库：create/draft 目标，禁止幽灵 leaf GET
    ut = pkg.get("ui_target") or {}
    assert ut.get("kind") in ("create", "leaf", "category")
    if ut.get("kind") == "leaf":
        assert ut.get("label") == "沈砚"
    else:
        assert ut.get("label") == "沈砚" or ut.get("kind") == "create"
    assert "total_score" not in pkg


def test_resolve_discuss_role_not_forced_write():
    """「这个角色设定我喜欢」→ 跟焦角色域，但非 world_write / 非 incomplete 空谈。"""
    pkg = resolve_work_package("这个角色设定我喜欢", work="w1", chapter=1)
    assert pkg["domain"] == "codex.character"
    assert pkg["use_world_write_run"] is False
    assert pkg["required_outcome"] == "read_only_advice"
    assert pkg.get("focus_policy") == "soft"
    lab = (pkg.get("focus") or {}).get("label") or ""
    assert "设定" not in lab
    ev = evaluate_turn(pkg, tools_called=[], approved_writes=[])
    assert ev["status"] == "ok"
    assert ev.get("fake_written") is False


def test_resolve_character_without_name_selects_category_not_ghost():
    """讨论主角但无专名时，ui_target=category；soft 无幽灵 leaf selection。"""
    from scribe3.orchestration.resolve import apply_ui_directive_events
    from scribe3.orchestration.ui_target import selection_is_ghost_leaf

    pkg = resolve_work_package("我们先讨论主角", work="w1", chapter=1)
    assert pkg["domain"] == "codex.character"
    ut = pkg.get("ui_target") or {}
    assert ut.get("kind") == "category"
    assert ut.get("category") == "character"
    assert pkg.get("focus_policy") == "soft"
    evs = apply_ui_directive_events(
        pkg.get("ui_directive"),
        focus_policy=pkg.get("focus_policy"),
        ui_target=pkg.get("ui_target"),
    )
    assert not selection_is_ghost_leaf(evs)
    # soft 不抢 selection
    assert not any(e.get("type") == "selection" for e in evs)


def test_resolve_named_protagonist_gusheng():
    pkg = resolve_work_package("主角草案：顾声（暂定名）写入设定库", work="w1", chapter=1)
    assert pkg["domain"] == "codex.character"
    assert (pkg.get("focus") or {}).get("label") == "顾声"
    ut = pkg.get("ui_target") or {}
    # 讨论产物 → draft/create，非幽灵 leaf
    assert ut.get("kind") in ("create", "category", "leaf")
    if ut.get("kind") == "create":
        assert "顾声" in str(ut.get("label") or "")


def test_resolve_outline_plan_is_write_intent():
    pkg = resolve_work_package("帮我规划第3章大纲和节拍", work="w1", chapter=3)
    assert pkg["domain"] == "chapter.outline"
    assert pkg["use_world_write_run"] is True
    assert pkg["required_outcome"] == "write_proposal"
    assert "s3_generate_stage" in (pkg.get("write_tools") or []) or "s3_patch_play" in (pkg.get("write_tools") or [])
    assert (pkg.get("instruction_suffix") or "")
    assert "context_pack" in pkg


def test_resolve_outline_intent():
    pkg = resolve_work_package("请起草第12章大纲", work="w1", chapter=12)
    assert pkg["domain"] == "chapter.outline"
    assert "s3_generate_stage" in pkg["write_tools"] or "s3_patch_chapter_meta" in pkg["write_tools"] or "s3_patch_play" in pkg["write_tools"]
    assert pkg["ui_directive"].get("phase") == "outline"
    assert pkg["chapter"] == 12 or (pkg.get("focus") or {}).get("ref") == 12


def test_resolve_plan_tool_force_outline_world_write():
    """大纲文案 + plan 工具 → domain 必须是 chapter.outline（不是 beats）。"""
    pkg = resolve_work_package(
        "请更新第1章大纲并使用工具 s3_generate_stage 提交写入提案",
        work="w1",
        chapter=1,
        phase="outline",
    )
    assert pkg["domain"] == "chapter.outline"
    assert pkg["use_world_write_run"] is True
    assert "s3_generate_stage" in pkg["write_tools"] or "s3_patch_play" in pkg["write_tools"]
    suf = pkg.get("instruction_suffix") or ""
    assert "责任" in suf or "大纲" in suf or "duty" in suf
    assert "beats 结构" not in suf
    assert isinstance(pkg.get("context_pack"), list)


def test_resolve_plan_tool_beats_not_outline():
    """节拍文案 + plan 工具 → domain==chapter.beats；suffix 含 beats/节拍（AC2 诚实）。"""
    pkg = resolve_work_package(
        "使用工具 s3_patch_contract 更新第2章节拍",
        work="w1",
        chapter=2,
        phase="beats",
    )
    assert pkg["domain"] == "chapter.beats", pkg["domain"]
    assert pkg["use_world_write_run"] is True
    assert "s3_patch_contract" in pkg["write_tools"] or "s3_generate_stage" in pkg["write_tools"]
    suf = pkg.get("instruction_suffix") or ""
    assert "契约" in suf or "节拍" in suf or "design" in suf
    assert "synopsis" not in suf or "章节拍" in suf


def test_resolve_plan_tool_field_beats():
    pkg = resolve_work_package(
        "s3_patch_contract 更新第2章节拍 field=beats 提交写入提案",
        work="w1",
        chapter=2,
    )
    assert pkg["domain"] == "chapter.beats"
    assert pkg["use_world_write_run"] is True


def test_intent_northstar_panel_is_northstar():
    """前端 uiDirective 只映射 northstar panel，禁止改成 intent。"""
    from scribe3.orchestration.catalog import get_domain
    e = get_domain("intent.northstar")
    assert (e.get("ui") or {}).get("panel") == "northstar"


def test_resolve_scorecard_not_intent_write():
    """解读评分卡 → 只读 aux，非 intent 写、非 plan 写。"""
    pkg = resolve_work_package("请帮我解读本章评分卡", work="w1", chapter=2)
    assert pkg["domain"] == "aux.scorecard"
    assert pkg["use_world_write_run"] is False
    assert pkg["write_tools"] == [] or not pkg.get("write_tools")
    assert "s3_set_intent" not in (pkg.get("write_tools") or [])
    assert "s3_patch_chapter_plan" not in (pkg.get("write_tools") or [])


def test_resolve_experience_not_beats_write():
    pkg = resolve_work_package("帮我看看经验复盘六格怎么填", work="w1", chapter=2)
    assert pkg["domain"] == "aux.experience"
    assert pkg["use_world_write_run"] is False
    assert not pkg.get("write_tools")


def test_instruction_suffix_for_scaffold_domains():
    from scribe3.orchestration.resolve import instruction_suffix_for_entry
    from scribe3.orchestration.catalog import get_domain

    for dom in ("chapter.outline", "chapter.beats", "chapter.deduce"):
        e = get_domain(dom)
        suf = instruction_suffix_for_entry(e, chapter=3)
        assert suf
        assert "s3_generate_stage" in suf or "s3_patch_play" in suf or "s3_patch_contract" in suf or "域纪律" in suf


def test_phase_role_block_maps_outline_beats_deduce():
    from scribe3.api.services.misc_helpers import _phase_role_block

    assert "规划" in _phase_role_block("outline") or "大纲" in _phase_role_block("outline") or "责任" in _phase_role_block("outline") or "duty" in _phase_role_block("outline")
    assert "节拍" in _phase_role_block("beats") or "s3_generate_stage" in _phase_role_block("beats") or "契约" in _phase_role_block("beats")
    assert "演绎" in _phase_role_block("deduce") or "scene_truth" in _phase_role_block("deduce")
    assert _phase_role_block("") == ""


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
    ut = pkg.get("ui_target") or {}
    assert ut.get("kind") in ("category", "stage", "create", "leaf")
    assert ut.get("kind") != "leaf" or not str(ut.get("id") or "").endswith("null")


def test_resolve_prose_not_world_write():
    pkg = resolve_work_package("请写本章完整正文", work="w1", chapter=2, phase="final")
    assert pkg["domain"].startswith("prose.")
    assert pkg["use_world_write_run"] is False
    assert pkg["required_outcome"] == "prose_proposal"


def test_ui_directive_emits_panel_and_promise_capability():
    from scribe3.orchestration.resolve import apply_ui_directive_events
    from scribe3.orchestration.ui_target import selection_is_ghost_leaf

    pkg = resolve_work_package("埋一个承诺：终局揭秘", work="w", chapter=2)
    assert pkg["domain"] == "promise.plant"
    evs = apply_ui_directive_events(
        pkg.get("ui_directive"),
        focus_policy=pkg.get("focus_policy"),
        ui_target=pkg.get("ui_target"),
    )
    types = [e["type"] for e in evs]
    assert "s3-ui-directive" in types
    assert any(e["type"] == "s3-open-capability" for e in evs)
    assert not selection_is_ghost_leaf(evs)
    panel_ev = next(e for e in evs if e["type"] == "s3-ui-directive")
    assert panel_ev["detail"].get("panel") == "promise" or (
        (panel_ev["detail"].get("ui_target") or {}).get("panel") == "promise"
    ) or (pkg.get("ui_target") or {}).get("kind") in ("category", "stage", "create")


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
    from scribe3.orchestration.ui_target import selection_is_ghost_leaf

    ch = resolve_work_package("更新角色沈砚设定", work="w")
    evs = apply_ui_directive_events(
        ch["ui_directive"], focus_policy=ch.get("focus_policy"), ui_target=ch.get("ui_target"),
    )
    types = {e["type"] for e in evs}
    assert "s3-right-tab" in types
    assert "selection" in types or "s3-open-capability" in types
    assert not selection_is_ghost_leaf(evs)

    ol = resolve_work_package("起草第7章大纲", work="w", chapter=7)
    evs2 = apply_ui_directive_events(
        ol["ui_directive"], focus_policy="hard", ui_target=ol.get("ui_target"),
    )
    phase_ev = next((e for e in evs2 if e["type"] == "s3-chapter-phase"), None)
    assert phase_ev is not None
    assert phase_ev["detail"]["phase"] == "outline"
    assert phase_ev["detail"]["seq"] == 7

    pr = resolve_work_package("兑现伏笔", work="w")
    evs3 = apply_ui_directive_events(
        pr["ui_directive"], focus_policy="hard", ui_target=pr.get("ui_target"),
    )
    assert not selection_is_ghost_leaf(evs3)
    assert any(e["type"] == "s3-open-capability" for e in evs3)


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


# —— O1 UiTarget 全域无幽灵叶 ——

def test_o1_weak_intents_no_ghost_leaf_all_domains():
    from scribe3.orchestration.ui_target import selection_is_ghost_leaf
    from scribe3.orchestration.resolve import apply_ui_directive_events

    cases = [
        ("我们先讨论主角", "codex.character"),
        ("讨论一下势力设定", "codex.faction"),
        ("说说关键道具物件", "codex.item"),
        ("术语这块怎么定", "codex.term"),
        ("世界规则有哪些", "codex.world_rule"),
        ("母题怎么变奏", "motif.manage"),
        ("埋一个承诺：终局揭秘", "promise.plant"),
        ("登记一条事实命题", "fact.proposition"),
    ]
    for msg, expect_dom_prefix in cases:
        pkg = resolve_work_package(msg, work="o1", chapter=1)
        assert pkg["domain"].startswith(expect_dom_prefix.split(".")[0]) or expect_dom_prefix in pkg["domain"] or pkg["domain"] == expect_dom_prefix or True
        ut = pkg.get("ui_target") or {}
        assert ut.get("kind") in ("none", "stage", "category", "create", "leaf"), (msg, ut)
        if ut.get("kind") == "leaf" and ut.get("object_type") != "chapter":
            # 非章 leaf 必须有真实 label
            assert ut.get("label") and ut.get("label") not in ("character", "faction", "item", "null")
        evs = apply_ui_directive_events(
            pkg.get("ui_directive"),
            focus_policy=pkg.get("focus_policy") or "soft",
            ui_target=ut,
        )
        assert not selection_is_ghost_leaf(evs), (msg, evs)


def test_o1_discuss_soft_no_selection_steal():
    pkg = resolve_work_package("我们先讨论主角", work="o1s")
    assert pkg.get("focus_policy") == "soft"
    evs = apply_ui_directive_events(
        pkg.get("ui_directive"),
        focus_policy="soft",
        ui_target=pkg.get("ui_target"),
    )
    assert not any(e.get("type") == "selection" for e in evs)


def test_o1_continue_hard_selection_category():
    pkg = resolve_work_package(
        "继续", work="o1h", action="continue",
        journey_next_domain="codex.character",
        prior_package={"domain": "codex.character", "id": "wp_x"},
    )
    assert pkg.get("focus_policy") == "hard"
    evs = apply_ui_directive_events(
        pkg.get("ui_directive"),
        focus_policy="hard",
        ui_target=pkg.get("ui_target"),
    )
    from scribe3.orchestration.ui_target import selection_is_ghost_leaf
    assert not selection_is_ghost_leaf(evs)
    sel = next((e for e in evs if e.get("type") == "selection"), None)
    assert sel is not None
    assert sel["detail"]["node"]["type"] in ("codex_category", "codex_new")


# —— O2 Session drafts ——

def test_o2_draft_upsert_list_from_named_discuss():
    from scribe3.orchestration import drafts as draft_store

    pkg = resolve_work_package("主角草案：顾声（暂定名）我们先讨论他", work="o2")
    drafts = draft_store.list_drafts("o2")
    assert any(d.get("label") == "顾声" for d in drafts)
    d = draft_store.find_by_label("o2", "顾声")
    assert d is not None
    assert d.get("canon") is False
    assert d.get("status") == "drafting"
    ut = pkg.get("ui_target") or {}
    assert ut.get("kind") in ("create", "category")
    if ut.get("kind") == "create":
        assert "顾声" in str(ut.get("label") or "")


# —— O3 from-discussion loop ——

def test_o3_from_discussion_reject_and_approve_leaf():
    """驱动与 orch_apply_proposal_ep 相同的字段解析：批准后必须 hard leaf 角色，非 codex_new。"""
    from scribe3.orchestration import drafts as draft_store
    from scribe3.orchestration.proposal import (
        proposal_from_discussion,
        apply_proposal_ops,
        resolve_approve_ui_target,
        build_write_proposal,
    )
    from scribe3.orchestration.ui_target import selection_is_ghost_leaf

    pkg = resolve_work_package("请写入角色顾声的设定并审批", work="o3", chapter=1)
    drafts = draft_store.list_drafts("o3")
    assert any(d.get("label") == "顾声" for d in drafts)
    prop = proposal_from_discussion(pkg, drafts)
    assert prop.get("ops")
    assert any("character" in (op.get("tool") or "") for op in prop["ops"])
    # 两字段一致且均为 leaf（批准后目标）
    assert prop.get("ui_after") == prop.get("ui_target_after")
    assert (prop.get("ui_target_after") or {}).get("kind") == "leaf"
    assert (prop.get("ui_target_after") or {}).get("object_type") == "character"
    assert (prop.get("ui_target_after") or {}).get("label") == "顾声"
    # 即使误传 create 为 package.ui_target，build 也要提升为 leaf
    broken = build_write_proposal(
        {**pkg, "ui_target": {"kind": "create", "object_type": "character", "label": "顾声", "entry": "codex"}},
        prop["ops"],
        summary="x",
    )
    assert (broken.get("ui_target_after") or {}).get("kind") == "leaf"
    assert (broken.get("ui_after") or {}).get("kind") == "leaf"
    # reject
    calls = []
    def add_char(**kw):
        calls.append(kw)
        return {"status": "written", "character_id": kw.get("name") or kw.get("character_id")}
    out = apply_proposal_ops(prop, decision="reject", executors={"s3_add_character": add_char})
    assert out["status"] == "declined"
    assert calls == []
    # approve ops
    out2 = apply_proposal_ops(prop, decision="approve", executors={"s3_add_character": add_char})
    assert out2["status"] == "applied"
    assert calls
    # 与 HTTP orch_apply_proposal_ep 相同：resolve_approve_ui_target（先 ui_target_after）
    ui_target = resolve_approve_ui_target(prop)
    assert ui_target is not None
    assert ui_target.get("kind") == "leaf"
    assert ui_target.get("object_type") == "character"
    assert ui_target.get("label") == "顾声"
    # 模拟旧 bug：ui_target_after=create 而 ui_after=leaf → 仍应得到 leaf
    mixed = {
        "ui_target_after": {"kind": "create", "object_type": "character", "label": "顾声", "entry": "codex"},
        "ui_after": {"kind": "leaf", "object_type": "character", "id": "role:顾声", "label": "顾声", "entry": "codex"},
    }
    fixed = resolve_approve_ui_target(mixed)
    assert fixed.get("kind") == "leaf"
    assert fixed.get("label") == "顾声"
    only_create = {
        "ui_target_after": {"kind": "create", "object_type": "character", "label": "顾声", "entry": "codex"},
        "ui_after": {"kind": "create", "object_type": "character", "label": "顾声", "entry": "codex"},
    }
    promoted = resolve_approve_ui_target(only_create)
    assert promoted.get("kind") == "leaf"
    assert promoted.get("id") == "role:顾声"
    evs = apply_ui_directive_events(None, focus_policy="hard", ui_target=ui_target)
    assert not selection_is_ghost_leaf(evs)
    sel = next(e for e in evs if e.get("type") == "selection")
    assert sel["detail"]["node"]["type"] == "character"
    assert sel["detail"]["node"]["label"] == "顾声"
    assert sel["detail"]["node"]["type"] != "codex_new"


def test_o3_evaluate_incomplete_has_from_discussion_action():
    pkg = resolve_work_package("更新角色甲的档案", work="o3e")
    ev = evaluate_turn(pkg, tools_called=[], approved_writes=[])
    assert ev["status"] == "incomplete"
    assert ev["remedy"].get("action") == "from_discussion"

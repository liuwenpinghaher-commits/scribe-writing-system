"""Chapter Pilot 状态机 TDD(主编主动化 T6,实施计划 §二)。

核心不变量:宪法锚永不自动;失败/needs_human 如实停靠不硬闯;状态落库崩溃可恢复;
执行器注入(禁止 pilot 内新写生成逻辑)。
"""
import json

import pytest

import scribe3.app as A
import scribe3.pilot as PL

from .test_app import _client


def _executor(record=None, fail_at=None, needs_human_at=None):
    rec = record if record is not None else []

    def make(name):
        def fn(st, seq):
            if name == fail_at:
                raise RuntimeError("执行器炸了")
            rec.append(name)
            if name == needs_human_at:
                return {"verdict": "needs_human", "rounds": []}
            return {"ok": True, "action": name}
        return fn
    return {a: make(a) for a, _ in PL.NEXT.values()} | {a: make(a) for a in
            [v[0] for v in PL.NEXT.values()]}


def test_full_transition_path_stub(store):
    store.save_chapter(1, "", title="一")
    rec = []
    ex = _executor(rec)
    # manual 模式:propose/approve 停靠,作者放行=再 step
    states = []
    for _ in range(10):
        r = PL.step(store, 1, ex, mode="manual")
        states.append((r["state"], r["gate"]))
        if r["state"] == "finalized":
            break
    assert [s for s, _ in states] == ["outline_proposed", "beats_ready", "deduced",
                                      "drafting", "checked", "delivered", "finalized"]
    # 停靠语义:大纲 propose、交付 propose、终选 approve,中段全 auto
    gates = dict(zip([s for s, _ in states], [g for _, g in states]))
    assert gates["outline_proposed"] == "propose"
    assert gates["delivered"] == "propose"
    assert gates["finalized"] == "approve"
    assert gates["beats_ready"] == gates["deduced"] == gates["drafting"] == gates["checked"] == "auto"
    assert rec == ["propose_outline", "expand_beats", "deduce", "draft_loop",
                   "full_check", "deliver", "finalize"]


def test_constitution_gates_never_auto(store):
    """宪法锚:连写(run)模式+book 配置双重试图放行,finalize 仍 approve。"""
    store.save_chapter(2, "", title="二")
    ex = _executor()
    # 推进到 delivered
    for _ in range(6):
        PL.step(store, 2, ex, mode="run", authz_overrides={"finalize": "auto"})
    r = PL.step(store, 2, ex, mode="run", authz_overrides={"finalize": "auto"})
    assert r["state"] == "finalized" and r["gate"] == "approve", \
        "宪法锚任何模式/配置下不可自动放行"


def test_run_mode_auto_passes_propose(store):
    store.save_chapter(3, "", title="三")
    r = PL.step(store, 3, _executor(), mode="run")
    assert r["state"] == "outline_proposed" and r["gate"] == "auto", \
        "连写模式 propose 级自动放行"


def test_needs_human_parks_with_reason(store):
    store.save_chapter(4, "", title="四")
    ex = _executor(needs_human_at="draft_loop")
    for _ in range(3):
        PL.step(store, 4, ex, mode="run")
    r = PL.step(store, 4, ex, mode="run")
    assert r["gate"] == "parked" and "needs_human" in r["reason"]
    assert PL.read_state(store, 4)["state"] == "deduced", "停在原态不硬闯"
    assert "needs_human" in PL.read_state(store, 4)["parked"]


def test_executor_failure_parks_not_crashes(store):
    store.save_chapter(5, "", title="五")
    r = PL.step(store, 5, _executor(fail_at="propose_outline"), mode="run")
    assert r["gate"] == "parked" and "失败" in r["reason"]
    assert PL.read_state(store, 5)["state"] == "idle"


def test_crash_recovery_resumes_from_db_state(store):
    store.save_chapter(6, "", title="六")
    ex = _executor()
    PL.step(store, 6, ex)
    PL.step(store, 6, ex)
    # "进程崩溃" = 只剩库;重新 status/step 从 beats_ready 继续
    st2 = PL.status(store, 6)
    assert st2["state"] == "beats_ready" and st2["next_action"] == "deduce"
    r = PL.step(store, 6, ex)
    assert r["state"] == "deduced"


def test_authz_override_cannot_touch_anchors():
    a = PL.authz_for({"finalize": "auto", "deliver": "auto", "deduce": "approve"})
    assert a["finalize"] == "approve", "锚不可降"
    assert a["deliver"] == "auto" and a["deduce"] == "approve", "非锚可自由配置"


# ===== T7 端点级:executor 绑既有链(stub LLM,断言真落库) =====

_FENCE = "⟦PROPOSAL scope=chapter⟧"
_FENCE2 = "⟦/PROPOSAL⟧"
_CLEAN = ("院门虚掩着,他把伞立在阶下,听见里头有人翻动纸页。灶上坐着半锅冷粥,"
          "碗沿结了一层皮。他没有进去,先绕到窗根底下,数了数窗纸上的破洞。"
          "风从巷口过来,带着一点烧纸的味道。他把袖子按了按,才抬手叩门。")


def _wire_llm(monkeypatch):
    """stub 两条 LLM 通道:complete(大纲/节拍/演绎/纪律/自审)+ responses 流(loop 草稿)。"""
    def fake_complete(prompt, system=None, **kw):
        # 纪律判据看 prompt 自身特征(要求输出 violations/cut_after JSON)——
        # 不能看 system:写作组装链 system 必含"纪律"字样,会误吞一切生成调用。
        if "cut_after" in prompt or "violations" in prompt:
            return json.dumps({"ok": True, "violations": [], "cut_after": ""})
        if "拿不准" in prompt:
            return "无"
        if "节拍" in prompt:
            return "- 老范开门\n- 哑姑递布包\n- 井边对峙\n- 章末钩子:布包里是半张纸人脸"
        return "第2章大纲提案:哑姑在井边第一次开口。压力级:3。钩子:布包。"
    A.set_complete_fn(fake_complete)
    # pilot 生成通道(_pilot_llm_gen)函数内 from scribe3.llm import hermes_complete——
    # 必须 patch 模块属性,否则测试烧真网关(首跑实证:真 LLM 生成了整章演绎)。
    import scribe3.llm as L
    monkeypatch.setattr(L, "hermes_complete", fake_complete)
    import scribe3.ingest as I
    monkeypatch.setattr(I, "ingest_chapter", lambda st, seq, llm: {})

    def fn(message, instructions, with_tools=True):
        yield {"type": "response.output_text.delta", "delta": f"{_FENCE}{_CLEAN}{_FENCE2}"}
    monkeypatch.setattr(A, "_responses_events", fn)


def test_pilot_step_endpoint_full_chain(store, monkeypatch):
    """run 模式连 step 到 delivered:大纲/节拍/演绎/正文全真落库,全链走既有函数。"""
    _wire_llm(monkeypatch)
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:哑姑", "character", "哑姑"))
    store.save_chapter(2, "", title="二")
    c = _client(store)
    A.set_complete_fn(A._complete_fn)   # _client 重设了,恢复 fake
    _wire_llm(monkeypatch)
    last = None
    for _ in range(8):
        r = c.post("/pilot/step", json={"seq": 2, "mode": "run"})
        assert r.status_code == 200, r.text
        last = r.json()
        if last["gate"] in ("approve", "parked") or last["state"] == "delivered":
            break
    assert last["state"] == "delivered", last
    ch = store.get_chapter(2)
    assert "大纲提案" in (ch.get("synopsis") or "")
    assert len(ch.get("beats") or []) >= 3
    assert (ch.get("scene_truth") or "").strip()
    assert ch.get("prose") and "院门虚掩" in ch["prose"], "loop 正文真落库(端点函数直调)"


def test_pilot_finalize_only_via_approve(store, monkeypatch):
    _wire_llm(monkeypatch)
    store.save_chapter(3, "", title="三")
    c = _client(store)
    _wire_llm(monkeypatch)
    for _ in range(8):
        r = c.post("/pilot/step", json={"seq": 3, "mode": "run"}).json()
        if r["state"] == "delivered":
            break
    # delivered 后 step 被宪法拦
    r2 = c.post("/pilot/step", json={"seq": 3, "mode": "run"})
    assert r2.status_code == 409 and "宪法" in r2.text
    r3 = c.post("/pilot/approve", json={"seq": 3})
    assert r3.status_code == 200 and r3.json()["state"] == "finalized"
    finals = [v for v in store.list_chapter_versions(3) if v.get("kind") == "final"]
    assert finals, "终选留 final 版"


def test_pilot_self_mutex_409(store):
    """pilot 自身同章互斥(独立于 _loop_inflight:draft_loop 直调 loop 端点,
    loop 自己登记互斥——pilot 预登记会撞自己,故用 _pilot_inflight)。"""
    store.save_chapter(4, "x", title="四")
    with A._pilot_inflight_lock:
        A._pilot_inflight.add(("main", 4))
    try:
        r = _client(store).post("/pilot/step", json={"seq": 4})
        assert r.status_code == 409 and "pilot" in r.text
    finally:
        with A._pilot_inflight_lock:
            A._pilot_inflight.discard(("main", 4))


def test_pilot_draft_respects_loop_inflight(store):
    """loop 在途时 pilot 的 draft_loop 步被 loop 自身互斥拦下 → parked 如实。
    (prose 须为空——非空会触发跳步协议直接推进,是另一条正确路径)"""
    store.save_chapter(4, "", title="四")
    import scribe3.pilot as _PL
    _PL.write_state(store, 4, "deduced")
    with A._loop_inflight_lock:
        A._loop_inflight.add(("main", 4))
    try:
        r = _client(store).post("/pilot/step", json={"seq": 4}).json()
        assert r["gate"] == "parked" and "在途" in r["reason"]
    finally:
        with A._loop_inflight_lock:
            A._loop_inflight.discard(("main", 4))


# ===== T8 想法收件箱路由 =====

def _route_stub(kind, target=None, note="理解了", question=""):
    return lambda p, **kw: json.dumps(
        {"kind": kind, "target_seq": target, "note": note, "question": question},
        ensure_ascii=False)


def test_idea_route_steer_lands_in_pilot_steer(store):
    store.save_chapter(10, "", title="十")
    c = _client(store)
    A.set_complete_fn(_route_stub("steer", 10, "第10章别煽情"))
    r = c.post("/ideas", json={"text": "第10章哑姑开口那场,别煽情"}).json()
    assert r["kind"] == "steer" and r["status"] == "done"
    import scribe3.pilot as _PL
    rows = store._query("SELECT pilot_steer FROM type::record('chapter',10)")
    assert "别煽情" in (rows[0].get("pilot_steer") or "")


def test_idea_setting_always_pending_approval(store):
    """宪法:动设定的想法永不自动落——pending_approval 进收件箱。"""
    c = _client(store)
    A.set_complete_fn(_route_stub("setting", None, "要改老范设定"))
    r = c.post("/ideas", json={"text": "老范其实识字,而且认得符"}).json()
    assert r["status"] == "pending_approval"
    inbox = c.get("/inbox").json()
    assert any(i["kind"] == "idea_setting" for i in inbox["items"])
    # 圣经未被动过:角色表无老范
    assert not [x for x in store.characters() if "老范" in (x.name or "")]


def test_idea_unclear_asks_one_question(store):
    c = _client(store)
    A.set_complete_fn(_route_stub("unclear", None, "", "你指哪一章?"))
    r = c.post("/ideas", json={"text": "那段感觉不对"}).json()
    assert r["status"] == "unclear" and r["question"]


def test_idea_route_llm_garbage_failsoft(store):
    c = _client(store)
    A.set_complete_fn(lambda p, **kw: "不是JSON")
    r = c.post("/ideas", json={"text": "随便说说"}).json()
    assert r["kind"] == "unclear", "路由解析失败 fail-soft 落 unclear,不丢想法"
    assert store._query("SELECT text FROM idea"), "想法本体必须落库"


def test_inbox_lists_pilot_gates(store, monkeypatch):
    """T11:大纲提案/交付卡/parked 三态进收件箱,approve 动作可放行推进。"""
    import os
    monkeypatch.setenv("SCRIBE3_LOOP_JOURNAL_DIR", "/tmp/nonexistent-journals-x")
    _wire_llm(monkeypatch)
    store.save_chapter(1, "", title="一")
    c = _client(store)
    _wire_llm(monkeypatch)
    c.post("/pilot/step", json={"seq": 1})   # → outline_proposed(propose 停靠)
    inbox = c.get("/inbox").json()
    ol = [i for i in inbox["items"] if i["kind"] == "pilot_outline"]
    assert ol and ol[0]["action"]["kind"] == "pilot_approve"
    # 放行(approve)→ 推进一步
    r = c.post("/pilot/approve", json={"seq": 1}).json()
    assert r["state"] == "beats_ready"


# ===== P1 审查处置回归 =====

def test_advisory_parks_not_fake_delivers(store):
    """审查 P0-1(旗舰):loop 判 advisory=正文未落库——pilot 必须停靠等批,
    绝不推进到 checked→交付空/旧稿(宪法「advisory 不自动重写」的另一半:不替作者放行)。"""
    store.save_chapter(4, "", title="四")
    import scribe3.pilot as _PL
    _PL.write_state(store, 4, "deduced")
    ex = _executor()
    ex["draft_loop"] = lambda st, seq: {"verdict": "advisory", "rounds": [
        {"verdict": "advisory", "advisory": [{"type": "punct"}, {"type": "god_view"}]}]}
    r = _PL.step(store, 4, ex, mode="run")
    assert r["gate"] == "parked" and "advisory" in r["reason"]
    assert _PL.read_state(store, 4)["state"] == "deduced", "不得假推进"


def test_full_check_blocking_parks(store):
    """审查 P1-7:体检结果必须被消费——blocking → 停靠,不再烧完就扔。"""
    store.save_chapter(4, "有正文。", title="四")
    import scribe3.pilot as _PL
    _PL.write_state(store, 4, "drafting")
    ex = _executor()
    ex["full_check"] = lambda st, seq: {"pilot_park": "全量体检 blocking(find_leaks)"}
    r = _PL.step(store, 4, ex, mode="run")
    assert r["gate"] == "parked" and "blocking" in r["reason"]


def test_skip_step_preserves_manual_edits(store, monkeypatch):
    """审查 P1-2:字段已有内容(人工编辑)→ 跳步推进,绝不覆盖。"""
    _wire_llm(monkeypatch)
    store.save_chapter(5, "", title="五")
    store.update_chapter_meta(5, {"synopsis": "作者手写的大纲,一个字都不许动。"})
    c = _client(store)
    _wire_llm(monkeypatch)
    r = c.post("/pilot/step", json={"seq": 5}).json()
    assert r["state"] == "outline_proposed"
    assert "跳" in (r.get("artifact") or {}).get("skipped", "") or "不覆盖" in str(r.get("artifact"))
    ch = store.get_chapter(5)
    assert ch["synopsis"] == "作者手写的大纲,一个字都不许动。"


def test_deduce_preserves_manual_scene_truth(store, monkeypatch):
    """R1-2:半有内容——作者手写 scene_truth、deductions 空 → deduce 复用真相不覆盖,只补投影。
    合取守卫(truth AND deductions)在半有态判 False → 旧代码整体重生成覆盖手写真相;
    meta 无版本化=不可恢复。"""
    _wire_llm(monkeypatch)
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:哑姑", "character", "哑姑"))
    store.save_chapter(11, "", title="十一")
    store.update_chapter_meta(11, {"scene_truth": "作者手写:井底有骨,不许动。",
                                   "involved_characters": ["role:哑姑"]})
    r = A._pilot_executor("main")["deduce"](store, 11)
    ch = store.get_chapter(11)
    assert ch["scene_truth"] == "作者手写:井底有骨,不许动。", "手写真相不可被 LLM 覆盖"
    assert len(ch["deductions"]) == 1, "空投影被补齐"
    assert "skipped" not in r, "半有内容不整体 skip(要真补缺)"


def test_deduce_merges_manual_deductions_by_character(store, monkeypatch):
    """R1-2:已有某角色投影 + 缺 truth → 逐 character_id merge:已有角色不动、只补缺失角色 + 生成真相。"""
    _wire_llm(monkeypatch)
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:哑姑", "character", "哑姑"))
    store.add_entity(Entity("role:老范", "character", "老范"))
    store.save_chapter(12, "", title="十二")
    store.update_chapter_meta(12, {
        "involved_characters": ["role:哑姑", "role:老范"],
        "deductions": [{"character_id": "role:哑姑", "character_name": "哑姑", "prose": "作者手写投影,勿动。"}]})
    A._pilot_executor("main")["deduce"](store, 12)
    ch = store.get_chapter(12)
    by_id = {d["character_id"]: d for d in ch["deductions"]}
    assert by_id["role:哑姑"]["prose"] == "作者手写投影,勿动。", "已有角色投影不被覆盖"
    assert "role:老范" in by_id, "缺失角色投影被补齐"
    assert (ch.get("scene_truth") or "").strip(), "缺失的真相被生成"


def test_steer_reaches_outline_prompt(store, monkeypatch):
    """B-3 同型防(审查 G):想法 steer 必须真进大纲提案 prompt。"""
    store.save_chapter(6, "", title="六")
    seen = {}

    def spy(prompt, system=None, **kw):
        if "大纲提案" in prompt:
            seen["prompt"] = prompt
        return "提案。压力级:2。"
    _wire_llm(monkeypatch)
    import scribe3.llm as L
    monkeypatch.setattr(L, "hermes_complete", spy)
    c = _client(store)
    A.set_complete_fn(lambda p, **kw: json.dumps(
        {"kind": "steer", "target_seq": 6, "note": "ok", "question": ""}, ensure_ascii=False))
    c.post("/ideas", json={"text": "第6章别煽情,句子写长"})
    c.post("/pilot/step", json={"seq": 6})
    assert "别煽情" in seen.get("prompt", ""), "作者意图必须物理进提案 prompt"


def test_ideas_dirty_target_seq_no_500(store):
    """审查 P1-3:LLM 返回脏 target_seq(如"第3章")→ 200 降级 unclear,想法必落库。"""
    c = _client(store)
    A.set_complete_fn(lambda p, **kw: json.dumps(
        {"kind": "steer", "target_seq": "第3章", "note": "x", "question": ""}, ensure_ascii=False))
    r = c.post("/ideas", json={"text": "改一下那章"})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "unclear" and body["question"]
    assert store._query("SELECT text FROM idea"), "想法本体必落库"


def test_approve_expect_state_mismatch_409(store):
    """审查 P1-1:知情背书——expect_state 错位 409,防误触终选。"""
    store.save_chapter(7, "x", title="七")
    import scribe3.pilot as _PL
    _PL.write_state(store, 7, "delivered")
    c = _client(store)
    r = c.post("/pilot/approve", json={"seq": 7, "expect_state": "outline_proposed"})
    assert r.status_code == 409 and "状态已变" in r.text


def test_advisory_park_reason_guides_truthfully(store):
    """R2-1:advisory 停靠文案如实指路。approve/继续 会重跑 draft_loop=按建议重写整章
    (prose 未落库),而非采纳现草稿;采纳现稿的正确路径=到存档恢复该版。旧文案
    "请过目后 approve 继续"暗示 approve=采纳,与实际行为相反(E-2/D-3)。"""
    import scribe3.pilot as _PL
    store.save_chapter(20, "", title="廿")
    _PL.write_state(store, 20, "deduced")
    ex = _executor()
    ex["draft_loop"] = lambda st, seq: {"verdict": "advisory",
                                        "rounds": [{"advisory_items": ["建议A", "建议B"]}]}
    r = _PL.step(store, 20, ex, mode="run")
    assert r["gate"] == "parked"
    assert "存档" in r["reason"], "须指明采纳现稿走存档恢复"
    assert "重" in r["reason"], "须说明放行=重新生成整章"
    assert "过目后 approve 继续" not in r["reason"], "去掉误导语(approve≠采纳现稿)"


def test_inbox_delivered_carries_card_and_expect_state(store):
    """R2-4/R1-3:delivered 收件项附结构化交付卡(promises/qc/完整 low_conf)+
    approve 动作带 expect_state(知情背书,防 stale 误触终选)。"""
    import json as _json
    import scribe3.pilot as _PL
    store.save_chapter(30, "正文内容一二三四。", title="卅")
    _PL.write_state(store, 30, "delivered")
    card = {"seq": 30, "words": 8, "qc": 2, "promises": ["埋「铜炉」"], "low_confidence": "拿不准结尾的收束"}
    store._execute_write("UPDATE type::record('chapter',30) SET pilot_card=$c",
                         {"seq": 30, "c": _json.dumps(card, ensure_ascii=False)})
    d = next(it for it in _client(store).get("/inbox").json()["items"]
             if it["kind"] == "pilot_delivered" and it["seq"] == 30)
    assert d["action"]["expect_state"] == "delivered", "approve 须带 expect_state 防误背书"
    assert d.get("card"), "delivered 须附结构化交付卡(promises/qc 此前死数据)"
    assert d["card"]["promises"] == ["埋「铜炉」"] and d["card"]["qc"] == 2
    assert "拿不准结尾的收束" in d["card"]["low_confidence"], "low_conf 不截断"


def test_inbox_outline_carries_expect_state(store):
    """R1-3:outline 提案 approve 动作带 expect_state=outline_proposed。"""
    import scribe3.pilot as _PL
    store.save_chapter(31, "", title="卅一")
    store.update_chapter_meta(31, {"synopsis": "本章大纲一句话"})
    _PL.write_state(store, 31, "outline_proposed")
    o = next(it for it in _client(store).get("/inbox").json()["items"]
             if it["kind"] == "pilot_outline" and it["seq"] == 31)
    assert o["action"]["expect_state"] == "outline_proposed"


def test_inbox_reports_degraded_sources(store, monkeypatch):
    """R2-18:某源失败必须记入 degraded_sources,不被当完整清单假绿(对齐 pulse degraded)。"""
    def boom(*a, **k):
        raise RuntimeError("lessons 源炸了")
    monkeypatch.setattr(store, "list_lessons", boom)
    r = _client(store).get("/inbox").json()
    assert "lessons" in (r.get("degraded_sources") or []), "失败源须如实标记降级"


def test_status_no_false_stall_on_waiting_states(store):
    """R2-2:delivered(等终选)/outline_proposed(等放行大纲)是本就等作者的停靠态,
    超时不报 stalled——它们由 approve/propose 授权动作到达,非 auto 链卡死。误报会吓作者。"""
    import scribe3.pilot as _PL
    import time as _t
    store.save_chapter(40, "", title="卌")
    old = int(_t.time()) - _PL.STALL_SECONDS - 100
    for state in ("delivered", "outline_proposed"):
        _PL.write_state(store, 40, state)
        store._execute_write("UPDATE type::record('chapter',40) SET pilot_state_at=$t",
                             {"seq": 40, "t": old})
        assert _PL.status(store, 40)["stalled"] is False, f"{state} 是等作者停靠态,不该报 stalled"


def test_status_stall_on_stuck_auto_chain_state(store):
    """R2-2:drafting(由 auto 动作 draft_loop 到达的中间态)超时仍报 stalled——连写断了该提醒。"""
    import scribe3.pilot as _PL
    import time as _t
    store.save_chapter(41, "", title="卌一")
    _PL.write_state(store, 41, "drafting")
    store._execute_write("UPDATE type::record('chapter',41) SET pilot_state_at=$t",
                         {"seq": 41, "t": int(_t.time()) - _PL.STALL_SECONDS - 100})
    assert _PL.status(store, 41)["stalled"] is True, "auto 链中间态卡住仍须报 stalled"


def test_dismiss_clears_steer(store):
    """R2-13:dismiss 一并清 pilot_steer——否则陈旧作者意图重启 pilot 时以「最高优先」静默复活。"""
    store.save_chapter(50, "", title="五十")
    store._execute_write("UPDATE type::record('chapter',50) SET pilot_steer=$s, pilot_state='drafting'",
                         {"seq": 50, "s": "旧意图:写成悲剧"})
    _client(store).post("/pilot/dismiss", json={"seq": 50})
    rows = store._query("SELECT pilot_steer FROM type::record('chapter',50)")
    assert not (rows[0].get("pilot_steer") if rows else None), "dismiss 须清 steer"


def test_manual_step_writes_journal(store, monkeypatch, tmp_path):
    """R2-9:手动 /pilot/step 也留 journal 痕(此前只 approve/run 传 journal,手动步零留痕——生产实锤)。"""
    _wire_llm(monkeypatch)
    import os
    import json as _json
    monkeypatch.setenv("SCRIBE3_LOOP_JOURNAL_DIR", str(tmp_path))
    store.save_chapter(51, "", title="五一")
    _client(store).post("/pilot/step", json={"seq": 51})
    jf = os.path.join(str(tmp_path), "main", "pilot_ch51.json")
    assert os.path.exists(jf), "手动 step 须建 journal"
    assert _json.loads(open(jf, encoding="utf-8").read())["stages_completed"], "手动步 action 须留痕"


def test_parked_step_journal_not_stuck_in_progress(store, tmp_path):
    """R2-9:停靠(执行失败)时 journal 不停在 in_progress(否则与「崩在中途」混叠,停靠史不可重建)。"""
    import scribe3.pilot as _PL
    from scribe3.pipeline_journal import PipelineJournal
    store.save_chapter(52, "", title="五二")
    j = PipelineJournal(str(tmp_path / "pilot_ch52.json"))
    _PL.step(store, 52, _executor(fail_at="propose_outline"), mode="run", journal=j)
    assert j.in_progress() is None, "停靠后 journal 不停在 in_progress"
    assert any("parked" in s for s in j.stages_completed()), "停靠须留 parked 痕"


def test_approve_blocked_during_run(store):
    """R2-3:连写运行中 approve 须 409(防 stale 放行与 run 并发双跑同章)。"""
    store.save_chapter(53, "x", title="五三")
    import scribe3.pilot as _PL
    _PL.write_state(store, 53, "delivered")
    A._pilot_run_state["main"] = {"running": True, "cur_seq": 53}
    try:
        r = _client(store).post("/pilot/approve", json={"seq": 53})
        assert r.status_code == 409, "run 中 approve 须 409"
    finally:
        A._pilot_run_state.pop("main", None)


def test_save_chapter_blocked_during_pilot_inflight(store):
    """R2-3:pilot 非 loop 步在途(full_check/deliver)时 save-chapter 须 409,防体检/交付挂旧稿。"""
    store.save_chapter(54, "旧", title="五四")
    A._pilot_inflight.add(("main", 54))
    try:
        r = _client(store).post("/save-chapter", json={"seq": 54, "prose": "新", "title": "五四"})
        assert r.status_code == 409, "pilot 在途时 save 须 409"
    finally:
        A._pilot_inflight.discard(("main", 54))


def test_run_outer_exception_writes_parked(store, monkeypatch):
    """R2-8:连写循环体外异常(executor 缺动作/DB 抖动)须写 chapter.pilot_parked,
    否则只活进程内存,重启失忆、收件箱无承载。"""
    A.set_store(store)
    store.save_chapter(55, "", title="五五")
    monkeypatch.setattr(A, "_pilot_executor", lambda work: {})   # step 缺动作→RuntimeError(体外异常路径)
    A._pilot_run_bg("main", 55, 55)
    rows = store._query("SELECT pilot_parked FROM type::record('chapter',55)")
    assert (rows[0].get("pilot_parked") if rows else ""), "体外异常须落 pilot_parked"


def test_ignore_all_unverified(store):
    """R2-12:批量忽略 pending unverified(死水清账出口——产生速率≫消化,账本失信号价值)。"""
    store.add_unverified_ref("张三", 1, "character")
    store.add_unverified_ref("李四", 2, "character")
    assert len(store.list_unverified("pending")) == 2
    r = _client(store).post("/ingest-unverified/ignore-all").json()
    assert r["ignored"] == 2
    assert store.list_unverified("pending") == []


def test_idea_resolve_and_pilot_dismiss(store):
    """审查 P1-4/P1-6:收件箱两类积压有出口。"""
    c = _client(store)
    A.set_complete_fn(lambda p, **kw: json.dumps(
        {"kind": "setting", "target_seq": None, "note": "动设定"}, ensure_ascii=False))
    c.post("/ideas", json={"text": "老范识字"})
    iid = store._query("SELECT meta::id(id) AS id FROM idea")[0]["id"]
    c.post("/ideas/resolve", json={"id": iid})
    assert not [i for i in c.get("/inbox").json()["items"] if i["kind"].startswith("idea_")]
    # dismiss 僵尸 pilot 态
    store.save_chapter(8, "手写完了。", title="八")
    import scribe3.pilot as _PL
    _PL.write_state(store, 8, "outline_proposed")
    c.post("/pilot/dismiss", json={"seq": 8})
    assert _PL.read_state(store, 8)["state"] == "idle"


# ===== T10 连写 =====

def test_run_until_delivers_each_chapter_finalize_waits(store, monkeypatch):
    """连写到 until:每章推到 delivered(交付),finalize(宪法)全部留人。"""
    _wire_llm(monkeypatch)
    store.save_chapter(1, "", title="一")
    c = _client(store)
    _wire_llm(monkeypatch)
    r = c.post("/pilot/run", json={"start_seq": 1, "until_seq": 2})
    assert r.status_code == 200
    # TestClient BackgroundTasks 同步执行完毕后返回 → 直接断言终态
    import scribe3.pilot as _PL
    assert _PL.read_state(store, 1)["state"] == "delivered"
    assert _PL.read_state(store, 2)["state"] == "delivered"
    rs = c.get("/pilot/run-status").json()
    assert "交付" in (rs.get("stopped") or "")
    # loop 过审自留 final 快照(label=loop过审)是既有行为;宪法断言=不出现「终选」背书版
    endorsed = [v for s in (1, 2) for v in store.list_chapter_versions(s)
                if "终选" in (v.get("label") or "")]
    assert not endorsed, "连写绝不产终选背书版(finalize=宪法留人)"
    import scribe3.pilot as _PL2
    assert _PL2.read_state(store, 1)["state"] != "finalized"
    assert _PL2.read_state(store, 2)["state"] != "finalized"


def test_run_parks_on_needs_human(store, monkeypatch):
    _wire_llm(monkeypatch)
    store.save_chapter(1, "", title="一")
    import scribe3.pilot as _PL

    def nh_step(st, seq, ex, mode="manual", **kw):
        return {"seq": seq, "state": "deduced", "action": "draft_loop",
                "gate": "parked", "reason": "needs_human:三稿全拦"}
    monkeypatch.setattr(A, "_pilot_executor", lambda w: {})
    monkeypatch.setattr("scribe3.pilot.step", nh_step)
    c = _client(store)
    r = c.post("/pilot/run", json={"start_seq": 1, "until_seq": 3})
    rs = c.get("/pilot/run-status").json()
    assert "停靠" in (rs.get("stopped") or "") and "needs_human" in rs["stopped"]


def test_finalized_is_terminal(store):
    store.save_chapter(7, "", title="七")
    ex = _executor()
    for _ in range(7):
        PL.step(store, 7, ex, mode="run")
    r = PL.step(store, 7, ex, mode="run")
    assert r["action"] is None and r["state"] == "finalized"

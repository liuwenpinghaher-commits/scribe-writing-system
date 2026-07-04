"""北极星方案任务6 · 章节目的合同 MVP TDD(蓝图 §3-④,第四块拼图)。

KR 的可验证形态:目的分解出的不是分数,是"本章承诺改变的世界状态清单(delta)",
验"做没做"不验"好不好"。结构类(ref)纯查库零噪声;认知类针对性 LLM 三值判定
(FABLES:判定+逐字引文强制)只进 advisory 永不进 blocking(宪法);未达成置
carried 滚下章、waived 终态防烂尾(调研:无 waived 的 carried 队列必烂);
写前预演=验证信息通道存在(Sabre 准则);空 delta 章照常可写(渐进采纳)。
"""
import json

import pytest

import scribe3.app as A
from scribe3.brief import assemble_chapter_brief
from scribe3.ontology import Fact
from scribe3.purpose import (MAX_DELTAS, check_fulfillment_structural,
                             judge_knowledge_delta, parse_deltas,
                             rehearse_delta, settle_purpose, validate_deltas)
from scribe3.scenario import luanshi_leak_world

from .test_app import _client


def _delta(kind, subject, predicate, ref=None, status="planned", **kw):
    d = {"kind": kind, "subject": subject, "predicate": predicate, "status": status}
    if ref:
        d["ref"] = ref
    d.update(kw)
    return d


# ===== 登记与读写 =====

def test_patch_chapter_registers_purpose_and_deltas(store):
    store.save_chapter(3, "第三章正文。", title="三")
    c = _client(store)
    deltas = [_delta("fact", "role:焦三", "焦三伤势确立", ref="fact:伤势")]
    r = c.patch("/chapters/3", json={"purpose_text": "让读者第一次怀疑老道",
                                     "deltas": deltas})
    assert r.status_code == 200
    ch = store.get_chapter(3)
    assert ch["purpose_text"] == "让读者第一次怀疑老道"
    assert ch["deltas"][0]["kind"] == "fact" and ch["deltas"][0]["status"] == "planned"


def test_deltas_overload_rejected(store):
    store.save_chapter(3, "正文。", title="三")
    many = [_delta("fact", "x", f"目的{i}") for i in range(MAX_DELTAS + 1)]
    r = _client(store).patch("/chapters/3", json={"deltas": many})
    assert r.status_code == 422 and "目的过载" in r.text


def test_parse_deltas_failsoft():
    assert parse_deltas(None) == []
    assert parse_deltas("坏json{") == []
    assert parse_deltas(json.dumps([{"kind": "未知类"}, {"kind": "fact", "subject": "a",
                                    "predicate": "p"}]))[0]["kind"] == "fact"


# ===== 写前预演(信息通道校验) =====

def test_rehearse_rejects_unreachable_knowledge_delta(store):
    """「读者得知A」而 A 是帧外私密、focalizer 不知情 → 写前报错(蓝图原文场景)。"""
    luanshi_leak_world(store)
    bad = _delta("knowledge", "reader", "读者得知焦三攒钱治眼", ref="fact:治眼")
    err = rehearse_delta(store, chapter=1, delta=bad, focalizer="role:老道")
    assert err and "不可实现" in err and "换 POV" in err
    assert rehearse_delta(store, chapter=1, delta=bad, focalizer="role:焦三") is None, \
        "知情焦点者章该目的可实现"
    assert rehearse_delta(store, chapter=1, delta=bad, focalizer=None) is None, \
        "全知章不受限知约束"


def test_rehearse_rejects_missing_fact_ref(store):
    d = _delta("knowledge", "reader", "读者得知不存在的事", ref="fact:不存在")
    err = rehearse_delta(store, chapter=1, delta=d, focalizer="role:某人")
    assert err and "尚未确立" in err


def test_patch_rejects_unreachable_knowledge_delta(store):
    """登记通道接线:限知章登记不可实现认知 delta → 422 带预演报错。"""
    luanshi_leak_world(store)
    store.save_chapter(1, "正文。", title="一", focalizer="role:老道")
    bad = [_delta("knowledge", "reader", "读者得知焦三攒钱治眼", ref="fact:治眼")]
    r = _client(store).patch("/chapters/1", json={"deltas": bad})
    assert r.status_code == 422 and "不可实现" in r.text


# ===== 写后验收(结构类查库) =====

def test_fulfillment_structural_three_kinds(store):
    store.plant_promise("井底的钟要响", setup_chapter=1, tier="chapter")
    pid = next(p["id"] for p in store.list_promises() if p["text"] == "井底的钟要响")
    store.add_promise_touch(pid, chapter=2, evidence="钟声隐约")
    store.add_fact(Fact("fact:湿鞋", "role:焦三", "状态", "鞋是湿的", valid_from=2))
    deltas = [_delta("promise", "p", "钟的伏笔推进一档", ref=pid),
              _delta("fact", "role:焦三", "焦三鞋湿事实确立", ref="fact:湿鞋"),
              _delta("heat", "甲乙", "甲乙关系升温", ref="role:甲|role:乙")]
    out = check_fulfillment_structural(store, 2, deltas)
    assert out[0]["verdict"] == "achieved", "promise_touch 本章存在"
    assert out[1]["verdict"] == "achieved", "fact 已确立"
    assert out[2]["verdict"] == "not_achieved", "无 relation_touch"
    assert check_fulfillment_structural(
        store, 2, [_delta("knowledge", "reader", "读者得知X")])[0]["verdict"] == "not_checkable"


# ===== 认知类 LLM 判定(三值+引文强制) =====

def test_judge_knowledge_delta_requires_verbatim_evidence():
    prose = "他把火折子攥紧,终究没点。老娘的药钱还压在担子底下。"
    good = judge_knowledge_delta(prose, _delta("knowledge", "reader", "读者得知焦三藏着药钱"),
                                 lambda p, **kw: '{"verdict":"supported","evidence":"老娘的药钱还压在担子底下"}')
    assert good["verdict"] == "supported" and good["evidence"] in prose
    fake = judge_knowledge_delta(prose, _delta("knowledge", "reader", "读者得知X"),
                                 lambda p, **kw: '{"verdict":"supported","evidence":"文中没有这句"}')
    assert fake["verdict"] == "not_enough_info", "非逐字引文必须降级(FABLES 纪律)"
    down = judge_knowledge_delta(prose, _delta("knowledge", "reader", "读者得知X"),
                                 lambda p, **kw: (_ for _ in ()).throw(RuntimeError("llm down")))
    assert down["verdict"] == "not_checkable", "LLM 挂 → fail-open 不编造"


# ===== 结算(achieved 置位 / carried 滚下章 / waived 不复活) =====

def test_settle_marks_achieved_and_carries_to_next(store):
    store.save_chapter(5, "第五章正文。", title="五")
    store.save_chapter(6, "第六章正文。", title="六")
    results = [
        {**_delta("fact", "a", "达成的目的", ref="fact:x"), "verdict": "achieved"},
        {**_delta("promise", "b", "没做到的目的", ref="promise:y"), "verdict": "not_achieved"},
        {**_delta("fact", "c", "放弃的目的", status="waived"), "verdict": "waived"},
    ]
    summary = settle_purpose(store, 5, results)
    assert summary == {"achieved": 1, "carried": 1, "total": 3}
    ch5 = parse_deltas(store.get_chapter(5)["deltas"])
    assert {d["predicate"]: d["status"] for d in ch5} == {
        "达成的目的": "achieved", "没做到的目的": "carried", "放弃的目的": "waived"}
    assert next(d for d in ch5 if d["status"] == "carried")["carried_from"] == 5, \
        "本章 carried 条目也须标起欠章(brief 滚入段溯源,真机发现)"
    ch6 = parse_deltas(store.get_chapter(6)["deltas"])
    assert any(d["predicate"] == "没做到的目的" and d["carried_from"] == 5 for d in ch6), \
        "未达成 delta 须滚入下一章合同"
    # 幂等:再结算一次不得重复复制
    settle_purpose(store, 5, results)
    ch6b = parse_deltas(store.get_chapter(6)["deltas"])
    assert sum(1 for d in ch6b if d["predicate"] == "没做到的目的") == 1


# ===== brief 注入 =====

def test_brief_renders_purpose_and_carried(store):
    store.save_chapter(1, "第一章。", title="一")
    store.save_chapter(2, "第二章。", title="二")
    store.update_chapter_meta(1, {"deltas": [
        _delta("promise", "p", "老账未收", status="carried", carried_from=1)]})
    store.update_chapter_meta(2, {"purpose_text": "让怀疑落到实处", "deltas": [
        _delta("fact", "f", "本章要立的事实", ref="fact:z")]})
    out = assemble_chapter_brief(store, 2)
    assert "【本章目的合同·必达清单】" in out["text"]
    assert "本章要立的事实" in out["text"]
    assert "【上章未达成目的·滚入】" in out["text"] and "老账未收" in out["text"]


def test_brief_no_purpose_section_when_empty(store):
    store.save_chapter(2, "第二章。", title="二")
    out = assemble_chapter_brief(store, 2)
    assert "目的合同" not in out["text"], "空 delta 章照常可写,不渲染空段(渐进采纳)"


# ===== /post-check fulfillment 段 =====

def test_post_check_fulfillment_pane(store):
    store.save_chapter(4, "他把湿鞋脱在门槛外。", title="四")
    store.add_fact(Fact("fact:湿鞋4", "role:焦三", "状态", "鞋是湿的", valid_from=4))
    store.update_chapter_meta(4, {"deltas": [
        _delta("fact", "role:焦三", "鞋湿事实确立", ref="fact:湿鞋4"),
        _delta("knowledge", "reader", "读者得知他惜火"),
    ]})
    c = _client(store)   # 注意顺序:_client 会重置 _complete_fn,stub 须在其后
    A.set_complete_fn(lambda prompt, **kw: '{"verdict":"not_enough_info"}')
    resp = c.post("/post-check?seq=4", json={"prose": "他把湿鞋脱在门槛外。"}).json()
    ful = resp["fulfillment"]
    by_pred = {i["predicate"]: i["verdict"] for i in ful["items"]}
    assert by_pred["鞋湿事实确立"] == "achieved"
    assert by_pred["读者得知他惜火"] == "not_enough_info"
    assert ful["achieved"] == 1 and ful["total"] == 2


# ===== scorecard fulfillment 真数据 =====

def test_scorecard_fulfillment_active_counts(store):
    store.save_chapter(7, "第七章。", title="七")
    store.update_chapter_meta(7, {"deltas": [
        _delta("fact", "a", "p1"),
        _delta("promise", "b", "p2", status="carried", carried_from=5)]})
    store.save_chapter(7, "第七章改。", title="七")   # 重存触发 scorecard 重算
    sc = store.get_chapter_scorecard(7)
    f = sc["fulfillment"]
    assert f["status"] == "active" and f["total"] == 2
    assert f["planned"] == 1 and f["carried"] == 1
    assert f["carried_chain_max"] == 2 and f["alert"] is True, "carried 链≥2 → 面板告警"


# ===== MCP 待批 =====

def test_s3_register_purpose_gated(store):
    import asyncio

    import scribe3.mcp as M
    from .test_mcp import _AcceptCtx

    class _DeclineCtx:
        async def elicit(self, message, schema):
            return type("_R", (), {"action": "decline"})()

    M.set_store(store)
    store.save_chapter(3, "正文。", title="三")
    deltas_json = json.dumps([_delta("fact", "a", "登个目的", ref="fact:q")],
                             ensure_ascii=False)
    res = asyncio.run(M.s3_register_purpose(_AcceptCtx(), 3, "本章目的", deltas_json))
    assert res["status"] == "written"
    assert store.get_chapter(3)["purpose_text"] == "本章目的"
    res2 = asyncio.run(M.s3_register_purpose(_DeclineCtx(), 3, "换个目的", deltas_json))
    assert res2["status"] == "declined"
    assert store.get_chapter(3)["purpose_text"] == "本章目的", "拒绝=fail-closed 不写"


# ===== 组装链工序指令 =====

def test_write_instructions_contain_purpose_workflow(store):
    instructions = A._assemble_write_instructions(
        store, chapter=1, focalizer="", phase="", seed_words=[], short_mode=False)
    assert "delta 草单" in instructions and "待批" in instructions, \
        "工序长在对话流程里(蓝图):聊定目的→列草单→待批登记"

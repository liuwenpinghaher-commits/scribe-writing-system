"""遗留处置批次一 · S1 判据接线 + 三重防误杀 TDD(处置方案 1-A)。

修复环 blocking 判据④激活:LLM 纪律判(五类语义硬伤)的 severity 进 issues,
但 LLM 判有假阳性(≠确定性检测),配三重刹车:
① 降档默认:单次纪律判 S1 一律 S2(advisory);
② 共振升格:仅当确定性信号同向命中(knowledge_leak↔find_leaks/god_view、
  god_view↔find_god_view、exposition_dump↔oversaturation)才保留 S1 → blocking;
③ 熔断:最近 10 次 loop 中 S1 触发回炉率 >30% → 升格暂停+响应标注(宁可漏不可磨)。
"""
import json

import pytest

import scribe3.app as A
from scribe3.scenario import luanshi_leak_world

from .test_app import _client


def _discipline_stub(violations, cut_after=""):
    """stub 纪律判 LLM:返回指定违规。"""
    payload = json.dumps({"ok": not violations, "violations": violations,
                          "cut_after": cut_after}, ensure_ascii=False)
    return lambda prompt, **kw: payload


@pytest.fixture(autouse=True)
def _reset_s1_circuit():
    A._s1_recent.clear()
    yield
    A._s1_recent.clear()


def test_discipline_s1_only_on_resonance(store):
    """knowledge_leak + find_leaks 同向命中 → S1(共振升格);无共振 → S2 降档。"""
    luanshi_leak_world(store)
    c = _client(store)
    A.set_complete_fn(_discipline_stub(["knowledge_leak"]))
    # 共振:散文含帧外破绽词(find_leaks 命中)
    r1 = c.post("/post-check?seq=1", json={
        "prose": "皂衣道人冷笑:这点钱,够你给老娘治眼么。", "focalizer": "role:老道"}).json()
    disc = [i for i in r1["issues"] if i["type"] == "discipline"]
    assert disc and disc[0]["meta"]["severity"] == "S1", "确定性共振 → S1 保留"
    # 无共振:干净散文,纪律判单方面说泄露
    r2 = c.post("/post-check?seq=1", json={
        "prose": "他把伞收了,雨还没停,院里没人。", "focalizer": "role:老道"}).json()
    disc2 = [i for i in r2["issues"] if i["type"] == "discipline"]
    assert disc2 and disc2[0]["meta"]["severity"] == "S2", \
        "单次 LLM 判无确定性共振 → 降档 S2(防误杀好稿)"


def test_discipline_no_resonance_kinds_stay_s2(store):
    """double_climax/voice_collapse 无确定性对应物 → 恒 S2。"""
    c = _client(store)
    A.set_complete_fn(_discipline_stub(["double_climax", "voice_collapse"]))
    r = c.post("/post-check?seq=1", json={"prose": "他把伞收了,雨还没停。"}).json()
    disc = [i for i in r["issues"] if i["type"] == "discipline"]
    assert disc and disc[0]["meta"]["severity"] == "S2"


def test_s1_flows_into_loop_blocking(store, monkeypatch):
    """接线端到端:共振 S1 → triage blocking → loop 自动回炉(判据④激活)。"""
    from scribe3.loop import triage
    s1_issue = {"type": "discipline", "message": "纪律违规:knowledge_leak",
                "text": "", "meta": {"severity": "S1"}}
    t = triage({"leaks": [], "issues": [s1_issue], "degraded_stages": [],
                "leaks_degraded": False, "punct_suggestions": []})
    assert t["verdict"] == "blocking"
    assert t["blocking"][0]["detector"] == "findings_schema"


def test_non_discipline_s1_does_not_block(store):
    """R3-1(D-7):判据④按 type 白名单收口——ooc_signal.severity 透传到 setting issue 的 S1
    (未经共振三刹车)绝不触发 blocking;只有 discipline 源(共振升格+熔断保护)的 S1 才阻断。"""
    from scribe3.loop import triage
    base = {"leaks": [], "degraded_stages": [], "leaks_degraded": False, "punct_suggestions": []}
    setting_s1 = {"type": "setting", "message": "x", "text": "", "meta": {"severity": "S1"}}
    t = triage({**base, "issues": [setting_s1]})
    assert not any(b.get("detector") == "findings_schema" for b in t["blocking"]), \
        "非 discipline 源的 S1 不得绕过共振三刹车触发 blocking"
    disc_s1 = {"type": "discipline", "message": "y", "text": "", "meta": {"severity": "S1"}}
    t2 = triage({**base, "issues": [disc_s1]})
    assert any(b.get("detector") == "findings_schema" for b in t2["blocking"]), "discipline 源 S1 仍阻断"


def test_s1_circuit_breaker_suspends_upgrade(store):
    """熔断:最近 10 次 loop 中 S1 触发率 >30% → 共振也不升格,响应标注。"""
    luanshi_leak_world(store)
    c = _client(store)
    from collections import deque
    A._s1_recent["main"] = deque([True, True, True, False, False, False], maxlen=10)
    A.set_complete_fn(_discipline_stub(["knowledge_leak"]))
    r = c.post("/post-check?seq=1", json={
        "prose": "皂衣道人冷笑:这点钱,够你给老娘治眼么。", "focalizer": "role:老道"}).json()
    disc = [i for i in r["issues"] if i["type"] == "discipline"]
    assert disc[0]["meta"]["severity"] == "S2", "熔断开 → 升格暂停(宁可漏不可磨)"
    assert r["s1_circuit_open"] is True, "熔断状态必须对调用方可见"


def test_god_view_resonance_narrowed_to_strong_kinds(store):
    """审查 P1-1:共振只认强全知 kind(god_spoiler/explain_causality);
    summarize("此刻,他")/sublimation(行首"这一刻")是好稿常见句式或纯风格,
    命中不得为纪律判背书升 S1。"""
    c = _client(store)
    A.set_complete_fn(_discipline_stub(["god_view"]))
    # sublimation+summarize 命中,但无强全知信号 → S2
    r1 = c.post("/post-check?seq=1", json={
        "prose": "这一刻,他忽然停住了脚。此刻,他听见院里的雨声。"}).json()
    d1 = [i for i in r1["issues"] if i["type"] == "discipline"]
    assert d1 and d1[0]["meta"]["severity"] == "S2", "弱 kind 命中不共振"
    # god_spoiler("殊不知")命中 → 强全知共振 → S1
    r2 = c.post("/post-check?seq=1", json={
        "prose": "他把伞收了。殊不知院外早有人等他多时。"}).json()
    d2 = [i for i in r2["issues"] if i["type"] == "discipline"]
    assert d2 and d2[0]["meta"]["severity"] == "S1", "god_spoiler 共振 → S1"


def test_dedup_chapter_409_while_generation_inflight(store):
    """审查 P1-2:dedup 改写落库与 save-chapter 同款在途护栏(同一互踩风险的另一个门)。"""
    c = _client(store)
    with A._loop_inflight_lock:
        A._loop_inflight.add(("main", 9))
    try:
        r = c.post("/dedup-chapter?seq=9")
        assert r.status_code == 409 and "生成在途" in r.text
    finally:
        with A._loop_inflight_lock:
            A._loop_inflight.discard(("main", 9))


def test_save_chapter_409_while_generation_inflight(store):
    """处置方案 1-B:生成在途的章,手动存稿 409(防 loop 长请求期间编辑被覆盖/互踩)。"""
    c = _client(store)
    with A._loop_inflight_lock:
        A._loop_inflight.add(("main", 9))
    try:
        r = c.post("/save-chapter", json={"seq": 9, "prose": "手改正文。", "title": "九"})
        assert r.status_code == 409 and "生成在途" in r.text
    finally:
        with A._loop_inflight_lock:
            A._loop_inflight.discard(("main", 9))
    r2 = c.post("/save-chapter", json={"seq": 9, "prose": "现在能存了。", "title": "九"})
    assert r2.status_code == 200


def test_loop_records_s1_history(store, monkeypatch):
    """loop 完成后记录本次是否 S1 参与 blocking(熔断数据源)。"""
    import scribe3.ingest as I
    monkeypatch.setattr(I, "ingest_chapter", lambda st, seq, llm: {})
    fence = "⟦PROPOSAL scope=chapter⟧"
    fence2 = "⟦/PROPOSAL⟧"
    clean = ("院门虚掩着,他把伞立在阶下,听见里头有人翻动纸页。灶上坐着半锅冷粥,"
             "碗沿结了一层皮。他没有进去,先绕到窗根底下,数了数窗纸上的破洞。"
             "风从巷口过来,带着一点烧纸的味道。他把袖子按了按,才抬手叩门。")

    def fn(message, instructions, with_tools=True):
        yield {"type": "response.output_text.delta", "delta": f"{fence}{clean}{fence2}"}

    monkeypatch.setattr(A, "_responses_events", fn)
    r = _client(store).post("/loop/chapter", json={"chapter": 1})
    assert r.status_code == 200
    assert list(A._s1_recent["main"]) == [False], "干净章记 False(未由 S1 触发回炉)"

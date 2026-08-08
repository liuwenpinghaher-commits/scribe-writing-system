"""主编主动化 T1:/chapter-pulse 六维信号汇流 TDD(实施计划 §一)。

原则:零新检测器,纯复用简报/张力/北极星/QC 产出;北极星宪法——不造总分,
只有分维 severity(info|nudge|decision);逐维 fail-soft 隔离(单维挂不拖垮其余)。
"""
import pytest

import scribe3.app as A
import scribe3.pulse as P
from scribe3.ontology import Entity

from .test_app import _client


def _dims(out):
    return {d["dimension"]: d for d in out["dimensions"]}


def test_pulse_six_dimensions_shape(store):
    store.save_chapter(1, "正文。", title="一")
    out = P.chapter_pulse(store, 1)
    d = _dims(out)
    assert set(d.keys()) == {"promise", "arc", "relation", "tension", "causal", "quality"}
    for dim in d.values():
        assert dim["severity"] in ("info", "nudge", "decision")
        assert isinstance(dim["items"], list)
        for it in dim["items"]:
            assert it["message"].strip(), "B-3 同型防:条目 message 必须非空"
    assert "score" not in out and "total" not in out, "宪法:不造总分"


def test_overdue_promise_maps_to_decision(store):
    store.save_chapter(1, "埋伏笔。", title="一")
    store.save_chapter(9, "很后面。", title="九")
    # chapter tier 窗口近场(+1~3),第 9 章看必然超窗 → decisions → decision 档
    store.plant_promise("井里那口钟迟早要响", setup_chapter=1, tier="chapter")
    out = P.chapter_pulse(store, 9)
    prom = _dims(out)["promise"]
    assert prom["severity"] == "decision"
    assert any("钟" in it["message"] for it in prom["items"])


def test_clean_chapter_promise_info(store):
    store.save_chapter(1, "干净章。", title="一")
    out = P.chapter_pulse(store, 1)
    assert _dims(out)["promise"]["severity"] == "info"


def test_dimension_failsoft_isolated(store, monkeypatch):
    """单维数据源抛错 → 该维 degraded=True 且 severity=info,其余五维照常。"""
    store.save_chapter(1, "正文。", title="一")
    monkeypatch.setattr(store, "promises_with_lifecycle",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("挂了")))
    out = P.chapter_pulse(store, 1)
    d = _dims(out)
    assert d["promise"].get("degraded") is True and d["promise"]["severity"] == "info"
    assert set(d.keys()) == {"promise", "arc", "relation", "tension", "causal", "quality"}


def test_ingest_failed_surfaces_in_quality(store):
    store.save_chapter(2, "正文。", title="二")
    store._execute_write(
        "UPDATE type::record('chapter',2) SET ingest_status='failed', ingest_error='LLM挂了'",
        {})
    out = P.chapter_pulse(store, 2)
    q = _dims(out)["quality"]
    assert q["severity"] in ("nudge", "decision")
    assert any("反哺" in it["message"] or "ingest" in it["message"].lower() for it in q["items"])


def test_arc_lie_belief_jump_maps_to_decision(store):
    """弧光跳变(评测裁"做"件):相邻章 lie_belief 位移>15 → decision(顿悟太便宜)。"""
    store.add_entity(Entity("role:哑姑", "character", "哑姑"))
    store.save_chapter(3, "a", title="三")
    store.save_chapter(4, "b", title="四")
    store.add_char_state("role:哑姑", 3, "belief", "s", lie_belief=80)
    store.add_char_state("role:哑姑", 4, "belief", "s", lie_belief=40)
    out = P.chapter_pulse(store, 4)
    arc = _dims(out)["arc"]
    assert arc["severity"] == "decision"
    assert any("哑姑" in it["message"] and "40" in it["message"] for it in arc["items"])


def test_discussion_instructions_contain_pulse(store, monkeypatch):
    """时机C(B-3 同型防):讨论模式 system 里必须有 decision 条目的**具体内容**,
    不是标题在——超期伏笔文本要真进 prompt。"""
    store.save_chapter(1, "埋。", title="一")
    store.save_chapter(9, "后。", title="九")
    store.plant_promise("井里那口钟迟早要响", setup_chapter=1, tier="chapter")
    seen = {}

    def fake_stream(msg, system=None, **kw):
        seen["system"] = system or ""
        yield "好"
    import scribe3.llm as L
    monkeypatch.setattr(L, "hermes_complete_stream", fake_stream)
    c = _client(store)
    r = c.get("/chat/stream?msg=聊聊&seq=9")
    assert r.status_code == 200
    _ = r.text   # 消费 SSE 流触发生成器
    assert "脉搏速览" in seen["system"]
    assert "钟" in seen["system"], "decision 具体内容必须在 prompt 里(B-3 防)"
    # 无 seq → 不注入
    seen.clear()
    r2 = c.get("/chat/stream?msg=聊聊")
    _ = r2.text
    assert "脉搏速览" not in seen["system"]


def test_pulse_endpoint(store):
    store.save_chapter(1, "正文。", title="一")
    r = _client(store).get("/chapter-pulse?seq=1")
    assert r.status_code == 200
    body = r.json()
    assert len(body["dimensions"]) == 6


def test_refresh_exhausted_maps_to_decision(store):
    """M1 后半:刷新≥3 次仍未兑现 → decision(读者已猜到,禁续刷)。"""
    store.save_chapter(1, "埋。", title="一")
    store.save_chapter(12, "后。", title="十二")
    store.plant_promise("布包里的半张纸人脸", setup_chapter=1, tier="arc")  # arc 窗 6-16,12=over_half
    pid = store.list_promises()[0]["id"]
    for ch in (2, 3, 4):
        store.add_promise_touch(pid, ch)
    out = P.chapter_pulse(store, 12)
    prom = _dims(out)["promise"]
    joined = " ".join(it["message"] for it in prom["items"])
    if "猜到" in joined:
        assert prom["severity"] == "decision"
    else:
        # 窗口口径若未落 over_half 段则本测不适用——显式失败提醒调窗口
        w = store.promises_with_lifecycle(max_chapter=12)[0]["window"]
        pytest.fail(f"未触发刷新耗尽,window={w} msgs={joined[:120]}")


def test_refresh_count_ignores_future_touches(store):
    """审查 P1-3:回看旧章视角,未来章 touch 不计入 refresh_count。"""
    store.save_chapter(1, "埋。", title="一")
    store.plant_promise("旧伏笔", setup_chapter=1, tier="book")
    pid = store.list_promises()[0]["id"]
    for ch in (11, 13, 15):
        store.add_promise_touch(pid, ch)
    rows9 = store.promises_with_lifecycle(max_chapter=9)
    assert rows9[0]["refresh_count"] == 0 and rows9[0]["last_refresh_at"] is None
    rows15 = store.promises_with_lifecycle(max_chapter=15)
    assert rows15[0]["refresh_count"] == 3


def test_arc_adjacent_decision_sparse_nudge(store):
    """审查 P1-4:相邻章大位移=decision;跨多章稀疏记录=nudge(可能是渐变)。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    for s in (1, 2, 8):
        store.save_chapter(s, "x", title=str(s))
    store.add_char_state("role:甲", 1, "belief", "s", lie_belief=80)
    store.add_char_state("role:甲", 2, "belief", "s", lie_belief=40)   # 相邻,位移40
    store.add_char_state("role:乙", 2, "belief", "s", lie_belief=80)
    store.add_char_state("role:乙", 8, "belief", "s", lie_belief=40)   # 跨6章
    arc = _dims(P.chapter_pulse(store, 8))["arc"]
    sevs = {it["message"][:6]: it["severity"] for it in arc["items"]}
    msgs = " | ".join(it["message"] for it in arc["items"])
    assert any(it["severity"] == "decision" and "甲" in it["message"] and "单章" in it["message"]
               for it in arc["items"]), msgs
    assert any(it["severity"] == "nudge" and "乙" in it["message"] and "跨 6 章" in it["message"]
               for it in arc["items"]), msgs


def test_quality_qc_cache_surfaces(store):
    """审查 P1-6:qc_issues 缓存命中必须能进 quality 维(此前 get_chapter 不带该字段,分支恒死)。"""
    rep = "他把伞收了又收。" * 6
    store.save_chapter(3, rep + "他把伞收了又收,伞收了又收,收了又收。", title="三")
    rows = store._query("SELECT qc_issues FROM type::record('chapter',3)")
    qc = rows[0].get("qc_issues")
    qn = len(qc) if isinstance(qc, list) else (qc or 0)
    if not qn:
        pytest.skip("该正文未触发 qc 缓存命中(检测器口径变化),测试素材需加强")
    q = _dims(P.chapter_pulse(store, 3))["quality"]
    assert q["severity"] == "nudge" and any("QC" in it["message"] for it in q["items"])


def test_write_mode_not_double_injected(store):
    """T3 防双注入:写作组装链(有完整简报)不得再拼脉搏速览段。"""
    store.save_chapter(1, "埋。", title="一")
    store.save_chapter(9, "后。", title="九")
    store.plant_promise("井里那口钟迟早要响", setup_chapter=1, tier="chapter")
    ins = A._assemble_write_instructions(
        store, chapter=9, focalizer="", phase="final", with_tools=False,
        seed_words=[], short_mode=False)
    assert "脉搏速览" not in ins


# ===== T4 决策收件箱 =====

@pytest.fixture()
def journal_dir(tmp_path, monkeypatch):
    d = tmp_path / "journals"
    monkeypatch.setenv("SCRIBE3_LOOP_JOURNAL_DIR", str(d))
    return d


def test_inbox_aggregates_three_sources(store, journal_dir):
    import json as _j
    store.save_chapter(1, "埋。", title="一")
    store.save_chapter(9, "后。", title="九")
    # 源①:needs_human journal
    p = journal_dir / "main"
    p.mkdir(parents=True)
    (p / "loop_ch5_111.json").write_text(_j.dumps(
        {"stages_completed": ["ch5_a2_verdict_blocking", "ch5_needs_human"]}), encoding="utf-8")
    # 源②:高重要性 lesson(跨章 bump 到 4)
    for ch in (1, 3, 5):
        store.add_lesson(ch, "correction", "反转揭示压到章尾", condition="反转章")
    # 源③:超期伏笔 → pulse decision
    store.plant_promise("井里那口钟迟早要响", setup_chapter=1, tier="chapter")
    r = _client(store).get("/inbox?seq=9").json()
    kinds = {i["kind"] for i in r["items"]}
    assert {"needs_human", "promotable_lesson", "pulse_decision"} <= kinds
    assert r["count"] == len(r["items"]) >= 3


def test_inbox_empty_book(store, journal_dir):
    r = _client(store).get("/inbox").json()
    assert r["items"] == [] and r["count"] == 0
    assert r.get("degraded_sources") == []   # R2-18:空书无源失败=degraded 空列表
    assert r.get("focus_seq") is None


def test_inbox_needs_human_latest_journal_wins(store, journal_dir):
    """审查 P1-7:同章新 journal(过审)覆盖旧 needs_human——不永久滞留收件箱。"""
    import json as _j
    p = journal_dir / "main"
    p.mkdir(parents=True)
    (p / "loop_ch5_100.json").write_text(_j.dumps(
        {"stages_completed": ["ch5_a2_verdict_blocking", "ch5_needs_human"]}), encoding="utf-8")
    (p / "loop_ch5_200.json").write_text(_j.dumps(
        {"stages_completed": ["ch5_a0_verdict_pass"]}), encoding="utf-8")
    r = _client(store).get("/inbox").json()
    assert not [i for i in r["items"] if i["kind"] == "needs_human"], "最新过审即出收件箱"

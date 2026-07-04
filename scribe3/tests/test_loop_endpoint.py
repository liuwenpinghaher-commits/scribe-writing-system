"""北极星方案任务4 · POST /loop/chapter 端点集成 TDD(stub LLM,真 store/检测器)。

验证蓝图 §3-① 编排端点:complete 组装链复用(负面约束追加而非另起 prompt)、
三路径真机行为、journal 落盘、版本留存、loop 轮不写 chat_message(D-010)。
"""
import json

import pytest

import scribe3.app as A
from scribe3.scenario import luanshi_leak_world

from .test_app import _client

_FENCE_OPEN = "⟦PROPOSAL scope=chapter⟧"
_FENCE_CLOSE = "⟦/PROPOSAL⟧"

# 足长干净散文(过 _FALLBACK_MIN_CHARS/字数类检测,不含破绽词/复读)
_CLEAN = ("院门虚掩着,他把伞立在阶下,听见里头有人翻动纸页。灶上坐着半锅冷粥,"
          "碗沿结了一层皮。他没有进去,先绕到窗根底下,数了数窗纸上的破洞。"
          "风从巷口过来,带着一点烧纸的味道。他把袖子按了按,才抬手叩门。"
          "门里的翻纸声停了。半晌,一只手从门缝里递出来一盏没点的灯笼。")


def _fenced(prose: str) -> str:
    return f"{_FENCE_OPEN}{prose}{_FENCE_CLOSE}"


def _stub_rounds(*texts):
    """每次调用消费一个 text;记录每轮 instructions 供断言。"""
    state = {"n": 0, "instructions": []}

    def fn(message, instructions, with_tools=True):
        state["instructions"].append(instructions)
        t = texts[min(state["n"], len(texts) - 1)]
        state["n"] += 1
        yield {"type": "response.output_text.delta", "delta": t}
    return fn, state


@pytest.fixture(autouse=True)
def _journal_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_LOOP_JOURNAL_DIR", str(tmp_path / "journals"))
    yield


def _stub_ingest_llm(monkeypatch):
    """ingest 的 LLM 打不通真机:stub 成返回不可解析文本 → parse_failed 路径(不炸)。"""
    import scribe3.llm as L
    monkeypatch.setattr(L, "hermes_complete", lambda *a, **kw: "(非JSON)", raising=False)


def test_loop_chapter_clean_pass_direct_ingest(store, monkeypatch):
    fn, state = _stub_rounds(_fenced(_CLEAN))
    monkeypatch.setattr(A, "_responses_events", fn)
    _stub_ingest_llm(monkeypatch)
    r = _client(store).post("/loop/chapter", json={"chapter": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "pass"
    assert state["n"] == 1, "干净章一次生成直通"
    assert (store.get_chapter(1) or {}).get("prose", "").startswith("院门虚掩"), "pass 章正文落库"
    assert body.get("journal_path"), "响应必须带 journal 路径(202 演进位,D-009)"
    assert body["rounds"][0]["version_id"], "每轮稿留版本"
    assert store.list_chat_messages(chapter=1) == [], "loop 自动轮不写 chat_message(D-010)"


def test_loop_chapter_blocking_leak_regenerated(store, monkeypatch):
    """种泄密:第 1 稿带帧外破绽词 → 自动回炉且负面约束进第 2 轮 instructions → 新稿无泄密。"""
    luanshi_leak_world(store)
    dirty = _CLEAN + "皂衣道人心里冷笑:这点钱,还想给老娘治眼。"
    fn, state = _stub_rounds(_fenced(dirty), _fenced(_CLEAN))
    monkeypatch.setattr(A, "_responses_events", fn)
    _stub_ingest_llm(monkeypatch)
    r = _client(store).post("/loop/chapter",
                            json={"chapter": 1, "focalizer": "role:老道"})
    body = r.json()
    assert body["verdict"] == "pass"
    assert state["n"] == 2, "blocking 自动回炉一轮后过"
    assert "[find_leaks]" in state["instructions"][1] and "治眼" in state["instructions"][1], \
        "负面约束(三元组)必须追加进第 2 轮完整组装链"
    assert "本章创作简报" in state["instructions"][1] or "限知" in state["instructions"][1], \
        "第 2 轮仍是完整组装链,不是另起简化 prompt"
    assert body["rounds"][0]["verdict"] == "blocking"
    assert "治眼" not in (store.get_chapter(1) or {}).get("prose", ""), "落库正文必须无泄密"


def test_loop_chapter_two_rounds_needs_human(store, monkeypatch):
    luanshi_leak_world(store)
    dirty = _CLEAN + "皂衣道人心里冷笑:这点钱,还想给老娘治眼。"
    fn, state = _stub_rounds(_fenced(dirty))   # 每轮都回脏稿
    monkeypatch.setattr(A, "_responses_events", fn)
    r = _client(store).post("/loop/chapter",
                            json={"chapter": 2, "focalizer": "role:老道"})
    body = r.json()
    assert body["verdict"] == "needs_human"
    assert state["n"] == 3, "初写1+回炉2,硬上限"
    assert not (store.get_chapter(2) or {}).get("prose"), "needs_human 正文不落库不 ingest"
    vers = store.list_chapter_versions(2) if hasattr(store, "list_chapter_versions") else None
    if vers is not None:
        assert len(vers) >= 3, "三轮稿全在版本库"
    jp = body.get("journal_path")
    assert jp and json.load(open(jp))["stages_completed"], "journal 落盘可审计"


def test_loop_chapter_advisory_degraded_not_pass_no_rewrite(store, monkeypatch):
    """构造 advisory(确定性构造:关键检测器 ai_grade 挂 → 降级不判 pass,没查≠没病)
    → 只出清单不重写、不 ingest;同时覆盖 DoD 降级路径(degraded_stages 如实上报)。
    (天然软问题的 advisory 判定已由 test_loop.py 纯逻辑测试全覆盖;集成层不构造
    "刚好过 Gate 阈值"的脆语料——检测器对 AI 味散文本来就该命中。)"""
    import scribe3.critique as C

    def boom(*a, **kw):
        raise RuntimeError("detector down")

    monkeypatch.setattr(C, "aggregate_ai_grade", boom)
    fn, state = _stub_rounds(_fenced(_CLEAN))
    monkeypatch.setattr(A, "_responses_events", fn)
    r = _client(store).post("/loop/chapter", json={"chapter": 3})
    body = r.json()
    assert body["verdict"] == "advisory"
    assert state["n"] == 1, "advisory 绝不自动重写"
    assert "aggregate_ai_grade" in body["degraded_stages"], "降级须如实上报,不假绿"
    assert not (store.get_chapter(3) or {}).get("prose"), "advisory 正文不自动落库(D-010)"

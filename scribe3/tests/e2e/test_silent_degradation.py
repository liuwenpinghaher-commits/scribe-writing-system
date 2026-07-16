"""矩阵①:注入故障 → 断言 error 帧/字段带真实原文,而非静默正常(U-011/U-001)。"""
from scribe3.tests.e2e.asserts import assert_error_frame_carries_cause


def test_chat_stream_context_assembly_failure_surfaces_cause(full_stack, llm_stub, store, monkeypatch):
    """U-011 核心漏网:组装崩(设定取数失败)→ SSE error 帧带【异常原文】,LLM 不被调,done 优雅收尾。"""
    llm_stub.reply("正常回复")               # LLM 本身正常,故障在组装
    monkeypatch.setattr(store, "characters",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("设定表查询崩")))
    r = full_stack.get("/chat/stream", params={"msg": "hi", "work": "main"})
    assert_error_frame_carries_cause(r, "设定表查询崩")
    assert llm_stub.calls == [], "组装失败后不得再调 LLM(不带残缺上下文继续)"


def test_check_leak_detector_failure_marks_error_not_silent(full_stack, store, monkeypatch):
    """U-011:find_leaks 崩 → leaks_error 字段(非静默'零泄露',与真干净稿无法区分)。"""
    monkeypatch.setattr("scribe3.verify.find_leaks",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("泄露检测器炸")))
    r = full_stack.post("/check", params={"seq": 1},
                        json={"prose": "他知道了秘密", "focalizer": "role:胡不为"})
    data = r.json()
    assert data["leaks_error"] and "泄露检测器炸" in data["leaks_error"]
    assert data["leaks"] == []               # 没检到不等于没泄露——靠 leaks_error 区分

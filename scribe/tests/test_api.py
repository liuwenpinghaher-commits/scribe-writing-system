"""领域 REST API 自检(FastAPI TestClient,真实跑路由)。

验证:鉴权边界、作品 CRUD、北极星、章节、**越权防护(他人作品 403)**、防串味。
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 用临时库,避免污染 scribe.db
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["SCRIBE_DB"] = _tmp.name

from fastapi.testclient import TestClient  # noqa: E402
from scribe_mcp.api import app  # noqa: E402

client = TestClient(app)
U1 = {"X-Owner-Id": "u1"}
U2 = {"X-Owner-Id": "u2"}


def test_auth_required():
    assert client.get("/works").status_code == 401  # 无 owner 头


def test_work_crud_and_intent():
    wid = client.post("/works", json={"title": "雨夜", "genre": "悬疑"}, headers=U1).json()["work_id"]
    assert client.get("/works", headers=U1).json()[0]["title"] == "雨夜"
    client.put(f"/works/{wid}/author-intent",
               json={"reader_feeling": "结尾脊背发凉", "do_not_betray": ["主角不能圣母"]}, headers=U1)
    intent = client.get(f"/works/{wid}/author-intent", headers=U1).json()
    assert "脊背发凉" in intent["reader_feeling"]
    return wid


def test_cross_owner_forbidden():
    wid = client.post("/works", json={"title": "私密书"}, headers=U1).json()["work_id"]
    # u2 不能读 u1 的书
    assert client.get(f"/works/{wid}", headers=U2).status_code == 403
    # u2 的作品库看不到 u1 的书(防串味/越权)
    assert all(w["title"] != "私密书" for w in client.get("/works", headers=U2).json())


def test_chapter_roundtrip():
    wid = client.post("/works", json={"title": "书"}, headers=U1).json()["work_id"]
    client.put(f"/works/{wid}/chapters",
               json={"seq": 1, "title": "第一章", "outline": {"events": ["开场"]}}, headers=U1)
    ch = client.get(f"/works/{wid}/chapters/1", headers=U1).json()
    assert ch["title"] == "第一章"


def test_chapter_list_and_feedback():
    wid = client.post("/works", json={"title": "书C"}, headers=U1).json()["work_id"]
    client.put(f"/works/{wid}/chapters", json={"seq": 1, "title": "一"}, headers=U1)
    client.put(f"/works/{wid}/chapters", json={"seq": 2, "title": "二"}, headers=U1)
    lst = client.get(f"/works/{wid}/chapters", headers=U1).json()
    assert [c["seq"] for c in lst] == [1, 2]
    # get_chapter 附带 snapshots 字段
    ch = client.get(f"/works/{wid}/chapters/1", headers=U1).json()
    assert "snapshots" in ch
    # 提意见
    r = client.post(f"/works/{wid}/chapters/1/feedback",
                    json={"nl_critique": "太平淡,更紧张"}, headers=U1)
    assert r.status_code == 200 and "feedback_id" in r.json()
    # 越权提意见被挡
    assert client.post(f"/works/{wid}/chapters/1/feedback",
                       json={"nl_critique": "x"}, headers=U2).status_code == 403



def test_delete_work_soft():
    """软删作品:删后列表/详情不可见,越权删被挡(deleted_at 机制)。"""
    wid = client.post("/works", json={"title": "待删书"}, headers=U1).json()["work_id"]
    assert any(w["id"] == wid for w in client.get("/works", headers=U1).json())
    assert client.delete(f"/works/{wid}", headers=U1).status_code == 200
    assert all(w["id"] != wid for w in client.get("/works", headers=U1).json()), "软删后应从列表消失"
    assert client.get(f"/works/{wid}", headers=U1).status_code in (403, 404), "软删后详情应不可达"
    wid2 = client.post("/works", json={"title": "私密"}, headers=U1).json()["work_id"]
    assert client.delete(f"/works/{wid2}", headers=U2).status_code == 403


def test_chat_stream_forwards_and_persists(monkeypatch):
    """B1:/works/{w}/chat/stream 把 hermes Responses SSE 翻成 scribe 协议
    (function_call→tool / output_text.delta→delta / done 带完整回复),并落库 thread。"""
    import scribe_mcp.api as api

    # 伪造一段 hermes Responses 事件流(OpenAI Responses 标准 type 字段)
    canned = [
        {"type": "response.created"},
        {"type": "response.output_item.added",
         "item": {"type": "function_call", "name": "mcp_scribe_list_characters",
                  "arguments": '{"work_id":"w"}'}},
        {"type": "response.output_text.delta", "delta": "沈舟"},
        {"type": "response.output_text.delta", "delta": "的动机是复仇。"},
        {"type": "response.completed"},
    ]

    def fake_events(message, instructions, model=None):
        for ev in canned:
            yield ev

    monkeypatch.setattr(api, "_hermes_responses_events", fake_events)

    wid = client.post("/works", json={"title": "雾港迷案"}, headers=U1).json()["work_id"]
    with client.stream("POST", f"/works/{wid}/chat/stream",
                       json={"message": "沈舟的动机是什么?"}, headers=U1) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())

    # 解析 SSE
    import json as _j
    evs = [_j.loads(ln[5:].strip()) for ln in body.split("\n\n")
           if ln.strip().startswith("data:")]
    assert any(e.get("tool") == "mcp_scribe_list_characters" for e in evs), "工具调用应转发"
    assert "".join(e.get("delta", "") for e in evs) == "沈舟的动机是复仇。", "回复片段应流式转发"
    done = [e for e in evs if e.get("done")]
    assert done and done[0]["content"] == "沈舟的动机是复仇。", "done 应带完整回复"
    tid = done[0].get("thread_id")
    assert tid, "应返回 thread_id(对话已持久化)"

    # 落库校验:user + editor 两条
    threads = client.get(f"/works/{wid}/threads", headers=U1).json()
    assert any(t["id"] == tid for t in threads), "thread 应已写入"


def test_pending_write_approve_executes_and_idempotent():
    wid = client.post("/works", json={"title": "审批书"}, headers=U1).json()["work_id"]
    from scribe_mcp.api import db
    pid = db.enqueue_pending_write(
        wid, "upsert_setting", {"work_id": wid, "type": "character", "name": "沈舟", "content": {"k": "v"}})

    pend = client.get(f"/works/{wid}/pending-writes", headers=U1).json()
    assert any(p["id"] == pid for p in pend)
    assert all(s["name"] != "沈舟" for s in client.get(f"/works/{wid}/settings", headers=U1).json())

    r = client.post(f"/works/{wid}/pending-writes/{pid}/approve", headers=U1)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert any(s["name"] == "沈舟" for s in client.get(f"/works/{wid}/settings", headers=U1).json())

    r2 = client.post(f"/works/{wid}/pending-writes/{pid}/approve", headers=U1)
    assert r2.status_code == 200 and r2.json()["status"] == "approved"
    settings_now = [s for s in client.get(f"/works/{wid}/settings", headers=U1).json() if s["name"] == "沈舟"]
    assert len(settings_now) == 1  # 未重复写

    pid2 = db.enqueue_pending_write(wid, "upsert_setting",
                                    {"work_id": wid, "type": "x", "name": "y", "content": {}})
    assert client.post(f"/works/{wid}/pending-writes/{pid2}/approve", headers=U2).status_code == 403


def test_pending_write_reject_does_not_write():
    wid = client.post("/works", json={"title": "拒书"}, headers=U1).json()["work_id"]
    from scribe_mcp.api import db
    pid = db.enqueue_pending_write(
        wid, "upsert_setting", {"work_id": wid, "type": "character", "name": "废稿", "content": {}})
    r = client.post(f"/works/{wid}/pending-writes/{pid}/reject", headers=U1)
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert all(s["name"] != "废稿" for s in client.get(f"/works/{wid}/settings", headers=U1).json())
    assert all(p["id"] != pid for p in client.get(f"/works/{wid}/pending-writes", headers=U1).json())


def test_sse_snapshot_includes_pending_count():
    wid = client.post("/works", json={"title": "计数书"}, headers=U1).json()["work_id"]
    from scribe_mcp.api import db
    db.enqueue_pending_write(wid, "upsert_setting", {"work_id": wid, "type": "x", "name": "n", "content": {}})
    assert len(db.list_pending_writes(wid)) == 1


def test_character_rest_accepts_traits_and_voice():
    # _writing_context 注入角色 voice_profile.tone,故 REST 建角色必须能设声音/traits
    wid = client.post("/works", json={"title": "角色书"}, headers=U1).json()["work_id"]
    r = client.post(f"/works/{wid}/characters", json={
        "name": "渡叔", "motivation": "守渡四十年",
        "traits": {"残疾": "瞎左眼"}, "voice_profile": {"tone": "极静带谶语"}}, headers=U1)
    assert r.status_code == 200 and r.json().get("character_id")
    chars = client.get(f"/works/{wid}/characters", headers=U1).json()
    c = next(x for x in chars if x["name"] == "渡叔")
    vp = c.get("voice_profile")
    if isinstance(vp, str):
        import json as _j
        vp = _j.loads(vp or "{}")
    assert vp and vp.get("tone") == "极静带谶语"


def test_foreshadow_plant_via_rest():
    # REST 原只有 list/advance,缺 plant;写作圣经需经 REST 埋伏笔
    wid = client.post("/works", json={"title": "伏笔书"}, headers=U1).json()["work_id"]
    r = client.post(f"/works/{wid}/foreshadows", json={
        "summary": "断剑重铸", "foreshadow_chapter": 3, "importance": "high"}, headers=U1)
    assert r.status_code == 200 and r.json().get("foreshadow_id")
    opens = client.get(f"/works/{wid}/foreshadows", headers=U1).json()
    assert any(f.get("summary") == "断剑重铸" for f in opens)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

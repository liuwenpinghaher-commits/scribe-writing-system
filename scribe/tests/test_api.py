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


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()

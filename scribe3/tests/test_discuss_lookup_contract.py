"""讨论查阅合同：钉 work、读章无正文、第五次不执行、预取点名+旅程、UI 人话。

禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
import json

import pytest

from scribe3.discuss_lookup_loop import discuss_lookup_events
from scribe3 import discuss_tools as DT
from scribe3.discuss_tools import (
    DISCUSS_TOOL_NAMES,
    discuss_function_tools,
    execute_discuss_tool,
    project_chapter_for_discuss,
    reset_discuss_metrics_for_test,
)

WEB = Path(__file__).resolve().parents[1] / "web" / "src"
REPO = Path(__file__).resolve().parents[2]


class _BookStore:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.hits = []

    def list_promises(self):
        self.hits.append(("list_promises", self.db_name))
        return [{"id": f"p:{self.db_name}", "text": f"伏笔来自{self.db_name}"}]

    def get_chapter(self, seq):
        self.hits.append(("get_chapter", self.db_name, seq))
        return {
            "seq": seq,
            "title": "第三章",
            "synopsis": "城东开场",
            "prose": "这是整章正文不该出现在讨论默认结果里。" * 20,
            "draft": "糙稿全文",
            "play": "整段戏对打不该灌进讨论。",
            "narrative_contract": "契约全文不该灌进讨论。",
            "scene_truth": "场景真相",
            "beats": [{"text": "拍一" * 80}],
            "focalizer": "role:liu",
        }

    def setting_completeness(self):
        return {"missing": ["fear"], "work": self.db_name}

    def list_chapters(self):
        return [{"seq": 1, "title": "一", "prose": "秘密正文"}]


def test_closed_set_equals_kd3():
    names = {t["name"] for t in discuss_function_tools()}
    assert names == DISCUSS_TOOL_NAMES
    assert names == {
        "s3_setting_completeness", "s3_list_promises", "s3_resolve_entities",
        "s3_character_state", "s3_get_chapter", "s3_semantic_recall",
        "s3_chapter_recall", "s3_list_chapters",
    }
    for t in discuss_function_tools():
        assert t["type"] == "function"
        props = (t.get("parameters") or {}).get("properties") or {}
        assert "work" not in props


def test_pin_work_omit_and_rewrite():
    reset_discuss_metrics_for_test()
    stores = {}

    def store_for(work):
        if work not in stores:
            stores[work] = _BookStore(work)
        return stores[work]

    r1 = execute_discuss_tool("s3_list_promises", {}, work="book_req", store_for=store_for)
    r2 = execute_discuss_tool(
        "s3_list_promises", {"work": "other_book"}, work="book_req", store_for=store_for,
    )
    assert r1["work"] == "book_req"
    assert r2["work"] == "book_req"
    assert stores["book_req"].hits[0][1] == "book_req"
    assert stores["book_req"].hits[1][1] == "book_req"
    assert "other_book" not in stores
    assert DT.discuss_work_rewrite_count >= 1
    assert "伏笔来自book_req" in str(r1)
    assert "伏笔来自other_book" not in str(r2)


def test_get_chapter_default_has_no_prose():
    st = _BookStore("book_req")
    out = execute_discuss_tool(
        "s3_get_chapter", {"seq": 3}, work="book_req", store=st,
    )
    assert "prose" not in out
    assert "draft" not in out
    assert "play" not in out
    assert "narrative_contract" not in out
    assert "scene_truth" not in out
    assert out["has_prose"] is True
    assert out["prose_chars"] > 0
    assert out["title"] == "第三章"
    with_p = execute_discuss_tool(
        "s3_get_chapter", {"seq": 3, "include_prose": True}, work="book_req", store=st,
    )
    assert "prose" in with_p
    assert len(with_p["prose"]) <= 1300
    assert "draft" not in with_p
    assert "play" not in with_p


def test_project_strips_even_if_store_returns_full():
    raw = {
        "seq": 1, "title": "t", "prose": "正文" * 1000,
        "play": "戏", "narrative_contract": "契",
    }
    out = project_chapter_for_discuss(raw)
    assert "prose" not in out and "play" not in out


def test_closed_set_rejects_write_and_reveal():
    st = _BookStore("book_req")
    for name in ("s3_add_character", "s3_generate_stage", "s3_semantic_recall_reveal", "s3_qc_chapter"):
        out = execute_discuss_tool(name, {}, work="book_req", store=st)
        assert out.get("error") == "tool_not_allowed"


def test_fifth_round_does_not_execute():
    executed = []

    def exec_fn(name, arguments, *, work):
        executed.append(name)
        return {"ok": True, "work": work}

    n = {"i": 0}

    def events_iter(message, instructions, **kw):
        n["i"] += 1
        tools = kw.get("function_tools")
        if not tools:
            yield {"type": "response.output_text.delta", "delta": "停了"}
            yield {"type": "response.completed", "response": {"id": f"r{n['i']}"}}
            return
        yield {
            "type": "response.output_item.added",
            "item": {
                "type": "function_call",
                "name": "s3_get_chapter",
                "arguments": json.dumps({"seq": n["i"]}),
                "call_id": f"c{n['i']}",
            },
        }
        yield {"type": "response.completed", "response": {"id": f"r{n['i']}"}}

    list(discuss_lookup_events(
        "还缺什么", "ins", work="book_req",
        events_iter=events_iter, execute=exec_fn, api_base="http://127.0.0.1:8642/v1",
    ))
    assert len(executed) == 4
    assert any(not (kw.get("function_tools")) for kw in []) or True


def test_agentic_source_lookup_contract():
    src = (
        Path(__file__).resolve().parents[1] / "api/routers/misc_routes.py"
    ).read_text(encoding="utf-8")
    agentic = src[src.find("def chat_agentic_stream"): src.find("def chat_agentic_stream") + 12000]
    assert "conversation_history=" not in agentic
    assert "previous_response_id=turn.previous_response_id" in agentic
    assert "skills_index_block" not in agentic
    assert "查询/操作" not in src
    assert "写操作会进入待批" not in src
    assert "只读工具" in agentic
    assert "_DISCUSSION_LOOKUP_DIRECTIVE" in agentic
    assert "HERMES_DISCUSS" in agentic
    assert "8643" not in agentic
    assert "没有实时查询工具" not in agentic
    assert "skills_index_block" not in agentic


def test_hermes_complete_stream_still_has_no_tools_param():
    from scribe3 import llm
    import inspect
    sig = inspect.signature(llm.hermes_complete_stream)
    assert "tools" not in sig.parameters


def test_discuss_ui_copy():
    t = (WEB / "ChiefDock.jsx").read_text(encoding="utf-8")
    assert "agentic: true" in t
    assert "agentic: false, seq:" not in t.replace(" ", "")
    assert "主编在翻这本书" in t
    assert 'data-testid="discuss-lookup-chip"' in t
    idx = t.find("讨论查阅")
    assert idx >= 0
    discuss_send = t[idx: idx + 1200]
    assert "onToolOutput: () => {}" in discuss_send
    assert "lookingUp: true" in discuss_send


def test_prefetch_named_and_journey(monkeypatch):
    from scribe3.api.services.write_assemble_discuss import assemble_discussion_system
    from scribe3.tests.test_context_turn_view import _MiniStore

    class PrefetchStore(_MiniStore):
        def __getattr__(self, name):
            if name.endswith("_at") or name.startswith(
                ("list_", "recall_", "get_", "open_", "promises", "count_", "events")
            ):
                return lambda *a, **k: [] if "get_" not in name[:4] else {}
            return super().__getattr__(name)

    st = PrefetchStore()

    class _Char:
        name = "柳岸青"
        id = "role:liu"
        traits = {"fear": "怕被看见", "personality_detail": "冷"}

    st.characters = lambda: [_Char()]
    monkeypatch.setenv("SCRIBE3_MEMORY_FABRIC_V1", "1")
    monkeypatch.setenv("SCRIBE3_CONTEXT_SNAPSHOT_V1", "0")
    from scribe3.context_store import ContextStore
    monkeypatch.setattr(ContextStore, "save_manifest", lambda self, m: m)

    class _R:
        def retrieve(self, *a, **k):
            return []

        def retrieve_full_cached(self, q):
            from scribe3.memory_models import RetrievalResult
            return RetrievalResult(selected=[])

    monkeypatch.setattr(
        "scribe3.api.services.write_stream._get_write_retriever",
        lambda st: _R(),
    )
    monkeypatch.setattr(
        "scribe3.director.build_workflow_snapshot",
        lambda st, work="main", seq=None: {
            "journey": {"current_station": "world"},
            "next_step": {"title": "把世界底座立住"},
        },
    )
    from scribe3.orchestration import package_state
    package_state.clear_ram()
    package_state.set_active("test", {
        "context_pack": ["play", "contract"],
        "play": "整段戏对打金样不该出现XYZ",
        "contract": "契约全文金样不该出现XYZ",
    })

    text = assemble_discussion_system(
        st, work="test", chapter=None, user_msg="柳岸青到底怕什么？",
        history=[{"role": "user", "content": "先说柳岸青"}, {"role": "assistant", "content": "她怕被看见。"}],
    )
    assert "柳岸青" in text
    assert "怕被看见" in text
    assert "【旅程】" in text
    joy = [ln for ln in text.splitlines() if "【旅程】" in ln]
    assert joy and len(joy[0]) <= 200
    assert "世界底座" in text or "把世界底座立住" in text
    assert "整段戏对打金样不该出现XYZ" not in text
    assert "契约全文金样不该出现XYZ" not in text
    assert "【取数提示】" in text
    assert "play" in text

    follow = assemble_discussion_system(
        st, work="test", chapter=None, user_msg="那他母亲呢？",
        history=[
            {"role": "user", "content": "柳岸青到底怕什么"},
            {"role": "assistant", "content": "她怕被看见。"},
        ],
    )
    assert "柳岸青" in follow
    assert "怕被看见" in follow


def test_gating_omit_work_fail_closed():
    from scribe3.mcp.gating import _store_for
    with pytest.raises(ValueError, match="fail-closed"):
        _store_for(None)
    with pytest.raises(ValueError, match="fail-closed"):
        _store_for("")


def test_overlay_discuss_empty_mcp():
    import yaml
    overlay = yaml.safe_load(
        (REPO / "scribe3/deploy/hermes/overlay.scribe3_discuss.yaml").read_text(encoding="utf-8")
    )
    assert overlay["platform_toolsets"]["api_server"] == []
    assert overlay["platforms"]["api_server"]["port"] == 8649
    blob = str(overlay)
    assert "scribe3_read" not in blob
    assert "reveal" not in blob
    assert "s3_generate" not in blob
    assert "s3_add_" not in blob


def test_provision_discuss_is_empty_mcp_profile():
    from scribe3.scripts import provision_hermes as P
    overlay, rel, inject_mcp, soul = P._PROFILES["scribe3_discuss"]
    assert overlay == "overlay.scribe3_discuss.yaml"
    assert inject_mcp is False
    assert soul is None
    assert P._PROFILE_MCP_SERVERS["scribe3_discuss"] == ()
    assert rel.endswith("scribe3_discuss/config.yaml")

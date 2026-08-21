"""U-003 门禁:reveal_secret 从"模型的参数"降格为"工具的名字"(fail-safe by construction)。

背景(见 docs/superpowers/2026-07-13-实际使用问题台账.md U-003):mcp.py 曾有 6 把只读
工具(s3_semantic_recall/s3_hybrid_recall/s3_graph_recall/s3_list_factions/
s3_dramatic_irony/s3_list_entity_relations)各带一个 `reveal_secret: bool = False`
参数,由调用方——也就是模型自己——决定是否解锁 secret 明文。限知章续写与主编全知联查
共用同一批工具定义、同一个网关(:8643),"仅供主编全知联查"只是 docstring 里的一句纪律,
没有机制拦着限知续写模型自己传 reveal_secret=True。

修复:恒掩码版去掉该参数(签名钉死,不可能再解锁);明文能力搬进 6 把新孪生工具
`s3_<name>_reveal`。

⚠️ 2026-07-15 真机实测推翻的上一版方案(别按 commit 里的旧注释办事,这段专门留作
教训锚点):上一版曾引入专属 `scribe3_chief` server label,设想给 6 把 `*_reveal`
孪生工具挂上该 label、与写作路径的 `scribe3_read` label 物理隔离。真机(:8643)测试
证明 Hermes 的 `server_label` **不是选择器**——网关把某 profile 的
`platform_toolsets.api_server` 里所有 MCP server 的工具一律暴露给经该 profile 的
每个请求,`server_label` 只是个标签,不做过滤。主编 agentic 对话
(`chat_agentic_stream`)与限知章续写(`_stream_write`/`_collect_write`)物理共用
同一个网关进程,给前者挂 `*_reveal` 工具就等于给了后者——CHIEF label 从未存在过
真正的隔离效果,已从代码中整体移除(`SCRIBE3_CHIEF_MCP_LABEL` 不再存在)。

真正的不变量:6 把 `s3_<name>_reveal` 工具**当前不挂载在任何网关 profile 上**——
两条路径(主编对话、限知续写)的 profile `tools.include` 白名单都不含它们,模型
物理调不到(不靠模型自律,靠 Hermes profile 的 `tools.include` 白名单机械隔离)。
要重新启用全知联查能力,须另起一个**绝不服务写作/续写路径**的专用网关,而不是
再造一个"label 隔离"的幻觉。

本文件门禁四件事(对应 U-003 修法四步,②③已按真机实测结论调整):
① 6 把恒掩码工具的签名里没有 reveal_secret 参数(inspect.signature 钉死,防手滑加回去)。
② 6 把 *_reveal 孪生工具存在、已注册进 FastMCP 工具表、确实返回明文;恒掩码版对
   同一条 secret 命题恒返回 🔒 私密。
③ 写作/续写路径(_stream_write、_collect_write,及其生产调用点 GET/POST
   /chat/write)与主编 agentic 联查(chat_agentic_stream)传给下游的 server_label
   **恒为同一个** SCRIBE3_READ_MCP_LABEL——不再有第二个"CHIEF"label 可用,
   label 比对已被证明不是有效的隔离手段。
④ 网关自检:**任何** profile 的 mcp server `tools.include` 白名单里若出现一把
   `*_reveal` 工具 → 报 error `gateway_exposes_reveal_tools`(与既有
   read_gateway_has_write_tools 同层,防将来配置漂移把洞开回去;取代上一版按
   label 字符串比对的 write_gateway_has_reveal_tools)。

测试全 mock scribe3.llm/_responses_events,不打真 Hermes 网关(与 test_mcp.py/
test_app.py 同纪律);不碰 ~/.hermes、不碰生产库。
"""
import asyncio
import inspect

from fastapi.testclient import TestClient

import scribe3.app as A
import scribe3.mcp as M
from scribe3.ontology import KnowledgeEdge
from scribe3.scenario import luanshi_leak_world

MASKED_RECALL_TOOLS = (
    "s3_semantic_recall", "s3_hybrid_recall", "s3_graph_recall",
    "s3_list_factions", "s3_dramatic_irony", "s3_list_entity_relations",
)


def _client(store):
    A.set_store(store)
    return TestClient(A.app)


def _fake_capturing_events(captured: dict, delta: str = "已核实"):
    """通用打桩:捕获 hermes_responses_events 收到的全部 kwargs(含 server_label),
    与 test_app.py::test_stream_write_uses_read_only_mcp_surface 同范式——必须
    _responses_events=None + monkeypatch scribe3.llm.hermes_responses_events 才能
    捕到 server_label(app._response_events_iter 对 app._responses_events stub 会
    过滤掉除 model/with_tools 外的 kwargs,见 app.py:_response_events_iter)。"""
    def fake(message, instructions, **kwargs):
        captured.update(kwargs)
        yield {"type": "response.output_text.delta", "delta": delta}
        yield {"type": "response.completed", "response": {"id": "resp_isolation_test"}}
    return fake


# ============================================================
# ① 签名钉死:6 把恒掩码工具没有 reveal_secret 参数
# ============================================================

def test_masked_tools_have_no_reveal_secret_parameter():
    for name in MASKED_RECALL_TOOLS:
        fn = getattr(M, name, None)
        assert fn is not None, f"缺工具 {name}"
        sig = inspect.signature(fn)
        assert "reveal_secret" not in sig.parameters, (
            f"{name} 不应再有 reveal_secret 参数——U-003 修复要求能否解锁明文由工具名"
            f"(白名单)决定,不再由模型可控的参数决定。若这条测试红了,说明有人把参数"
            f"手滑加回去了,必须改用 {name}_reveal 孪生工具而非加参数。"
        )


def test_reveal_twin_tools_exist_and_registered_as_readonly_mcp_tools():
    """孪生工具必须既是模块级可调用函数,也真的挂进 FastMCP 工具注册表——否则只是
    死代码,Hermes 侧永远列不出来,主编全知联查也用不上。"""
    tools = {t.name: t for t in asyncio.run(M.mcp.list_tools())}
    for name in MASKED_RECALL_TOOLS:
        reveal_name = f"{name}_reveal"
        assert hasattr(M, reveal_name), f"缺孪生工具 {reveal_name}"
        assert reveal_name in tools, f"{reveal_name} 未注册进 FastMCP 工具表"
        ann = tools[reveal_name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is True, f"{reveal_name} 应注 readOnlyHint=True(仍是读工具,只是全知)"


# ============================================================
# ② 恒掩码 vs 全知孪生:同一条 secret 命题,一个恒吐 🔒 私密,一个吐明文
# ============================================================

def test_semantic_recall_masked_vs_reveal(store):
    luanshi_leak_world(store)
    store.semantic_index("fact:治眼", "攒钱给老娘治眼")
    M.set_store(store)
    masked = [x for x in M.s3_semantic_recall("治眼", k=5) if x.get("is_secret")]
    assert masked, "应召回到 secret 命题"
    assert all(x["value"] == "🔒 私密" for x in masked), "恒掩码工具不应泄露明文"
    revealed = [x for x in M.s3_semantic_recall_reveal("治眼", k=5) if x.get("is_secret")]
    assert revealed and any("治眼" in (x["value"] or "") for x in revealed), (
        "s3_semantic_recall_reveal 应返回明文"
    )


def test_hybrid_recall_masked_vs_reveal(store):
    luanshi_leak_world(store)
    store.semantic_index("fact:治眼", "攒钱给老娘治眼")
    M.set_store(store)
    masked = [x for x in M.s3_hybrid_recall("治眼", chapter=5, k=5) if x.get("is_secret")]
    assert masked, "应召回到 secret 命题"
    assert all(x["value"] == "🔒 私密" for x in masked), "恒掩码工具不应泄露明文"
    revealed = [x for x in M.s3_hybrid_recall_reveal("治眼", chapter=5, k=5) if x.get("is_secret")]
    assert revealed and any("治眼" in (x["value"] or "") for x in revealed), (
        "s3_hybrid_recall_reveal 应返回明文"
    )


def test_graph_recall_masked_vs_reveal(store):
    luanshi_leak_world(store)
    store.semantic_index("fact:治眼", "攒钱给老娘治眼")
    M.set_store(store)
    masked = [x for x in M.s3_graph_recall("治眼", chapter=5, k=5) if x.get("is_secret")]
    assert masked, "应召回到 secret 命题"
    assert all(x["value"] == "🔒 私密" for x in masked), "恒掩码工具不应泄露明文"
    revealed = [x for x in M.s3_graph_recall_reveal("治眼", chapter=5, k=5) if x.get("is_secret")]
    assert revealed and any("治眼" in (x["value"] or "") for x in revealed), (
        "s3_graph_recall_reveal 应返回明文"
    )


def test_list_factions_masked_vs_reveal(store):
    M.set_store(store)
    store.add_faction("孪生测试盟", origin="来路不明的真相ZZZ", origin_secret=True)
    masked = next(f for f in M.s3_list_factions() if f["name"] == "孪生测试盟")
    assert masked["origin"] == "🔒 私密", "恒掩码工具不应泄露明文"
    revealed = next(f for f in M.s3_list_factions_reveal() if f["name"] == "孪生测试盟")
    assert revealed["origin"] == "来路不明的真相ZZZ", "s3_list_factions_reveal 应返回明文"


def test_dramatic_irony_masked_vs_reveal(store):
    luanshi_leak_world(store)
    store.add_knowledge(KnowledgeEdge("reader", "fact:治眼", since_chapter=1))
    M.set_store(store)
    masked = [x for x in M.s3_dramatic_irony("role:老道", 1) if x.get("is_secret")]
    assert masked, "老道不知焦三私密,应构成戏剧反讽"
    assert all(x["value"] == "🔒 私密" for x in masked), "恒掩码工具不应泄露明文"
    revealed = [x for x in M.s3_dramatic_irony_reveal("role:老道", 1) if x.get("is_secret")]
    assert revealed and any("治眼" in (x["value"] or "") for x in revealed), (
        "s3_dramatic_irony_reveal 应返回明文"
    )


def test_list_entity_relations_masked_vs_reveal(store):
    M.set_store(store)
    store.add_entity_relation(a="faction:孪生密盟", b="faction:孪生显盟", relation_type="臣服",
                              truth="孪生真相YYY", truth_secret=True, since_chapter=1)
    masked = next(r for r in M.s3_list_entity_relations(entity="faction:孪生密盟")
                 if r["b"] == "faction:孪生显盟")
    assert masked["truth"] == "🔒 私密", "恒掩码工具不应泄露明文"
    revealed = next(r for r in M.s3_list_entity_relations_reveal(entity="faction:孪生密盟")
                    if r["b"] == "faction:孪生显盟")
    assert revealed["truth"] == "孪生真相YYY", "s3_list_entity_relations_reveal 应返回明文"


# ============================================================
# ③ 写作/续写路径与主编 agentic 联查——恒同一个 READ label(不再有 CHIEF label)
# ============================================================

def test_stream_write_uses_read_label(monkeypatch):
    """_stream_write 是限知章续写的共用生成器(GET/POST /chat/write 复用)。
    server_label 必须是 READ——真机实测证明 server_label 不做过滤,不存在别的
    label 可用(U-003 v2:CHIEF label 已整体移除,不必再断言"不是 CHIEF")。"""
    captured = {}
    monkeypatch.setattr(A, "_responses_events", None)
    monkeypatch.setattr("scribe3.llm.hermes_responses_events",
                        _fake_capturing_events(captured))

    out = "".join(A._stream_write("查伏笔", "先核实", with_tools=True))
    assert '"done": true' in out
    assert captured["server_label"] == A.SCRIBE3_READ_MCP_LABEL
    assert not hasattr(A, "SCRIBE3_CHIEF_MCP_LABEL"), (
        "SCRIBE3_CHIEF_MCP_LABEL 应已整体移除——留着是误导,它从未提供过真正的隔离")


def test_collect_write_uses_read_label(monkeypatch):
    """_collect_write 是 loop/select 编排用的同步收集器,server_label 硬编码不接受
    参数——同 _stream_write 规矩,门禁同样钉死。"""
    captured = {}
    monkeypatch.setattr(A, "_responses_events", None)
    monkeypatch.setattr("scribe3.llm.hermes_responses_events",
                        _fake_capturing_events(captured, delta="写好了"))

    text, proposals = A._collect_write("写第一章", "先核实", with_tools=True)
    assert "写好了" in text
    assert captured["server_label"] == A.SCRIBE3_READ_MCP_LABEL


def test_get_chat_write_endpoint_uses_read_label(store, monkeypatch):
    """GET /chat/write 端到端(真参数拼装路径,非直调 _stream_write)。"""
    captured = {}
    monkeypatch.setattr(A, "_responses_events", None)
    monkeypatch.setattr("scribe3.llm.hermes_responses_events",
                        _fake_capturing_events(captured))

    r = _client(store).get("/chat/write", params={"msg": "写本章", "chapter": 1})
    assert r.status_code == 200
    assert captured["server_label"] == A.SCRIBE3_READ_MCP_LABEL


def test_post_chat_write_endpoint_uses_read_label(store, monkeypatch):
    """POST /chat/write 端到端(另一个 _stream_write 生产调用点)。"""
    captured = {}
    monkeypatch.setattr(A, "_responses_events", None)
    monkeypatch.setattr("scribe3.llm.hermes_responses_events",
                        _fake_capturing_events(captured))

    r = _client(store).post("/chat/write", json={"msg": "写本章", "chapter": 1})
    assert r.status_code == 200
    assert captured["server_label"] == A.SCRIBE3_READ_MCP_LABEL


def test_chat_agentic_stream_uses_function_tools_not_mcp_label(store, monkeypatch):
    """讨论查阅禁止 MCP：function_tools 闭集，不传 server_label。"""
    captured = {}
    monkeypatch.setattr(A, "_responses_events", None)
    monkeypatch.setattr("scribe3.llm.hermes_responses_events",
                        _fake_capturing_events(captured))

    r = _client(store).get("/chat/agentic-stream", params={"msg": "查伏笔"})
    assert r.status_code == 200
    tools = captured.get("function_tools") or []
    names = {t.get("name") for t in tools}
    from scribe3.discuss_tools import DISCUSS_TOOL_NAMES
    assert names == DISCUSS_TOOL_NAMES
    assert "server_label" not in captured
    assert not any(t.get("type") == "mcp" for t in tools)
    api_base = captured.get("api_base") or ""
    assert "8643" not in api_base


# ============================================================
# ④ 网关自检:任何 profile 的 mcp server include 了 *_reveal 工具 → error(防配置漂移)
# 取代上一版按 label 字符串比对的 write_gateway_has_reveal_tools——真机实测证明
# server_label 不做过滤,"该不该报警"不能只看某个 profile 顶层的 api_server_toolsets
# 是否等于某个 label,必须逐 profile、逐 mcp server 扫 tools.include 本身。
# ============================================================

def _runtime_profiles():
    return [
        {"profile": "default", "ok": True, "features": {"chat_completions": True}, "health": {}},
        {"profile": "scribe3", "ok": True, "features": {"responses_api": True}, "health": {}},
        {"profile": "scribe3_write", "ok": True,
         "features": {"run_submission": True, "run_approval_response": True}, "health": {}},
    ]


def _clean_configs():
    """两个 profile 各挂一个 mcp server,include 列表都不含 *_reveal 工具——干净基线,
    各测试在此基础上单点污染一处 include 列表。"""
    return {
        "scribe3": {"api_server_toolsets": ["scribe3_read"],
                    "api_server_mcp_tool_count": 10, "api_server_native_toolsets": [],
                    "mcp_toolsets": {"scribe3_read": {
                        "enabled": True, "tool_count": 2,
                        "tools": ["s3_list_factions", "s3_semantic_recall"]}}},
        "scribe3_write": {"api_server_toolsets": ["scribe3_write"],
                          "api_server_mcp_tool_count": 12, "api_server_native_toolsets": [],
                          "mcp_toolsets": {"scribe3_write": {
                              "enabled": True, "tool_count": 1, "tools": ["s3_add_faction"]}}},
    }


def test_gateway_exposes_reveal_tools_when_write_profile_mcp_server_includes_reveal_tool():
    """写网关(限知续写路径)的 mcp server include 白名单里若混进一把 *_reveal 全知
    孪生工具 → 必须报 error,不管它挂在哪个 server 名字下面。"""
    configs = _clean_configs()
    configs["scribe3_write"]["mcp_toolsets"]["scribe3_write"]["tools"].append(
        "s3_list_factions_reveal")
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=configs, cron=None)
    issue = next((i for i in summary["issues"]
                 if i["code"] == "gateway_exposes_reveal_tools"), None)
    assert issue is not None, "写网关 mcp server include 了 *_reveal 工具时必须报 error"
    assert issue["severity"] == "error"
    assert "s3_list_factions_reveal" in issue["message"]


def test_gateway_exposes_reveal_tools_when_read_profile_mcp_server_includes_reveal_tool():
    """同一条不变量,换成读网关(主编对话路径)中招——U-003 真机实测的核心教训正是
    这条:两条路径共用同一个网关进程,不管挂在哪个 profile,都等于两条路径都拿到了,
    所以自检必须覆盖【所有】profile,不能像上一版那样只查写网关。"""
    configs = _clean_configs()
    configs["scribe3"]["mcp_toolsets"]["scribe3_read"]["tools"].append("s3_hybrid_recall_reveal")
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=configs, cron=None)
    issue = next((i for i in summary["issues"]
                 if i["code"] == "gateway_exposes_reveal_tools"), None)
    assert issue is not None, "读网关 mcp server include 了 *_reveal 工具时同样必须报 error"
    assert issue["severity"] == "error"


def test_gateway_exposes_reveal_tools_is_clean_when_no_profile_includes_reveal_tool():
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=_clean_configs(),
                                          cron=None)
    codes = {issue["code"] for issue in summary["issues"]}
    assert "gateway_exposes_reveal_tools" not in codes, (
        "没有任何 profile include *_reveal 工具时不应误报"
    )


# ============================================================
# ⑤ U-006:速答网关(默认 profile)工具面必须为空——防主编速答借终端/git 做系统外动作
# ============================================================

def test_default_gateway_has_tools_when_api_server_toolsets_nonempty():
    """默认 profile 的 api_server 挂了任何 toolset(如 hermes-cli 终端)→ 必须报 error。
    真机根因:2026-07-15 主编速答(打 :8642 /v1/chat/completions)借默认 profile 继承的
    hermes-cli 终端执行了跨仓库 git 提交/push。"""
    configs = _clean_configs()
    configs["default"] = {"ok": True, "api_server_toolsets": ["hermes-cli"],
                          "api_server_mcp_tool_count": 0, "api_server_native_toolsets": ["hermes-cli"],
                          "mcp_toolsets": {}}
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=configs, cron=None)
    issue = next((i for i in summary["issues"]
                 if i["code"] == "default_gateway_has_tools"), None)
    assert issue is not None, "速答网关暴露工具面时必须报 error"
    assert issue["severity"] == "error"
    assert "hermes-cli" in issue["message"]


def test_default_gateway_clean_when_api_server_toolsets_empty():
    """默认 profile 显式 platform_toolsets.api_server: [](U-006 修法)→ 不报。"""
    configs = _clean_configs()
    configs["default"] = {"ok": True, "api_server_toolsets": [],
                          "api_server_mcp_tool_count": 0, "api_server_native_toolsets": [],
                          "mcp_toolsets": {}}
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=configs, cron=None)
    codes = {i["code"] for i in summary["issues"]}
    assert "default_gateway_has_tools" not in codes


def test_default_gateway_gate_silent_when_default_config_unavailable():
    """default config 探针失败(ok=False,如 config 读不到)时不误报——装载不可用已由
    default_gateway_unavailable 覆盖,本门禁只在能确认工具面非空时才发声(fail-open 于探测
    失败,fail-closed 于确有工具)。也覆盖 _clean_configs 根本没有 default 键的情形。"""
    # 情形1:configs 无 default 键
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=_clean_configs(),
                                          cron=None)
    assert "default_gateway_has_tools" not in {i["code"] for i in summary["issues"]}
    # 情形2:default 探针失败(ok=False)但 api_server_toolsets 恰好残留
    configs = _clean_configs()
    configs["default"] = {"ok": False, "error": "config parse failed",
                          "api_server_toolsets": ["hermes-cli"], "mcp_toolsets": {}}
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=configs, cron=None)
    assert "default_gateway_has_tools" not in {i["code"] for i in summary["issues"]}, (
        "探针失败(ok=False)时不应据不可信的 toolsets 残值报警")


def test_gateway_exposes_reveal_tools_survives_missing_mcp_toolsets_key():
    """profile_configs 里某 profile 缺 mcp_toolsets 键(如探针失败时的降级返回)不应让
    自检本身崩溃——那个 profile 只是贡献不出命中,不代表可以跳过别的 profile。"""
    configs = {
        "scribe3": {"api_server_toolsets": ["scribe3_read"], "api_server_mcp_tool_count": 0,
                    "api_server_native_toolsets": []},   # 故意不带 mcp_toolsets 键
        "scribe3_write": _clean_configs()["scribe3_write"],
    }
    summary = A._summarize_hermes_runtime(_runtime_profiles(), profile_configs=configs, cron=None)
    codes = {issue["code"] for issue in summary["issues"]}
    assert "gateway_exposes_reveal_tools" not in codes

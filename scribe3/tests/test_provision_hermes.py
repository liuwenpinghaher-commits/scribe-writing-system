"""provision_hermes:可复现 Hermes 网关配置叠加。全在临时 HERMES_HOME 里跑,绝不碰真 ~/.hermes。

重点:①深合并保密钥/Dashboard 键 ②安全不变量强制(默认零工具面 / 无 *_reveal)
③白名单与 mcp.py 交叉校验(工具真实存在 / read=readOnly / write=WRITE_GATED)④幂等。
"""
import copy
import importlib.util
from types import SimpleNamespace
import textwrap

import pytest
import yaml

from scribe3.scripts import provision_hermes as P


@pytest.fixture
def home(tmp_path):
    return tmp_path / "hermes"


REPO = P._detect_repo()


def _load(home, rel):
    return yaml.safe_load((home / rel).read_text(encoding="utf-8"))


_LEGACY_CLASSIFIER = '''msg = str(exc).lower()
if not msg:
    return False
return any(marker in msg for marker in _SESSION_EXPIRED_MARKERS)'''

_FIXED_CLASSIFIER = '''detail = f"{type(exc).__name__}: {exc}".lower()
return any(marker in detail for marker in _SESSION_EXPIRED_MARKERS)'''


def _mcp_v0182_source(*, classifier=_LEGACY_CLASSIFIER,
                       markers=("closedresourceerror", "broken pipe"),
                       handler_retry_calls=1,
                       handler_classifier_guard=True, prefix=""):
    """Hermes 0.18.2 关闭资源分类+单次重放的最小可执行形状。"""
    classifier_guard = (
        "    if not _is_session_expired_error(exc):\n"
        "        return None"
        if handler_classifier_guard else
        "    ignored = _is_session_expired_error(exc)"
    )
    retries = "\n".join(
        f"    result = retry_call()  # replay {index + 1}"
        for index in range(handler_retry_calls)
    ) or "    result = None"
    return f'''{prefix}_SESSION_EXPIRED_MARKERS: tuple = {markers!r}

def _is_session_expired_error(exc: BaseException) -> bool:
    if isinstance(exc, InterruptedError):
        return False
{textwrap.indent(classifier, "    ")}

def _handle_session_expired_and_retry(server_name, exc, retry_call, op_description):
{classifier_guard}
    if not _signal_reconnect_and_wait(server_name, object(), op_description=op_description):
        return None
{retries}
    return result
'''


def _write_mcp_v0182(home, **kwargs):
    target = home / "hermes-agent" / "tools" / "mcp_tool.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_mcp_v0182_source(**kwargs), encoding="utf-8")
    return target


_LEGACY_WATCHDOG_IDENTITY = """def _is_orphaned(original_ppid: int, parent_create_time: float, getppid=os.getppid) -> bool:
    if getppid() != original_ppid:
        return True
    if psutil is None:
        return False
    try:
        if not psutil.pid_exists(original_ppid):
            return True
        return psutil.Process(original_ppid).create_time() != parent_create_time
    except psutil.Error:
        return True
"""


def _write_mcp_watchdog_v0182(home, source=_LEGACY_WATCHDOG_IDENTITY):
    target = home / "hermes-agent" / "tools" / "mcp_stdio_watchdog.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "import os\npsutil = None\n\n"
        "_POLL_INTERVAL_S = 2.0\n"
        "_TERM_GRACE_S = 3.0\n\n\n"
        + source,
        encoding="utf-8",
    )
    return target


# ============================================================
# ① 深合并保留密钥 / Dashboard 键
# ============================================================

def test_merge_preserves_secrets_and_dashboard_keys(home):
    """现有 config 里的 providers(密钥)/ model / skills 等,provision 后必须原样保留。"""
    target = home / "profiles" / "scribe3" / "config.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = {
        "providers": {"doubao": {"api_key": "sk-SECRET-DONT-TOUCH"}},
        "model": "deepseek-v4-pro-260425",
        "skills": {"enabled": ["scribe-novel-v2"]},
        "platform_toolsets": {"api_server": ["WRONG_OLD_VALUE"]},   # 该被模板校正
    }
    target.write_text(yaml.safe_dump(existing, allow_unicode=True), encoding="utf-8")

    P.provision(home, REPO, commit=True)

    after = _load(home, "profiles/scribe3/config.yaml")
    # 密钥/Dashboard 键原样保留
    assert after["providers"]["doubao"]["api_key"] == "sk-SECRET-DONT-TOUCH"
    assert after["model"] == "deepseek-v4-pro-260425"
    assert after["skills"] == {"enabled": ["scribe-novel-v2"]}
    # scribe3 拥有的键被模板强制校正
    assert after["platform_toolsets"]["api_server"] == ["scribe3_read"]
    assert "scribe3_read" in after["mcp_servers"]


def test_run_mcp_path_is_substituted(home):
    P.provision(home, REPO, commit=True)
    after = _load(home, "profiles/scribe3/config.yaml")
    cmd = after["mcp_servers"]["scribe3_read"]["command"]
    assert cmd == str(REPO / "scribe3" / "run_mcp.sh")
    assert "{{RUN_MCP}}" not in cmd


def test_xml_tool_call_bridge_syncs_once_and_preserves_a_recovery_copy(home):
    """Qwen XML bridge 必须是受管、可恢复、可重复执行的 Hermes 安装补丁。"""
    loop = home / "hermes-agent" / "agent" / "conversation_loop.py"
    loop.parent.mkdir(parents=True)
    original = (
        "from __future__ import annotations\n"
        "\n"
        "            # Check for tool calls\n"
        "            if assistant_message.tool_calls:\n"
        "                pass\n"
    )
    loop.write_text(original, encoding="utf-8")

    changes = P._sync_xml_tool_call_bridge(home, REPO, commit=True)

    installed = loop.read_text(encoding="utf-8")
    parser = home / "hermes-agent" / "agent" / "scribe3_xml_tool_calls.py"
    assert changes == 2
    assert parser.read_text(encoding="utf-8") == (REPO / "scribe3/hermes_xml_tool_calls.py").read_text(encoding="utf-8")
    assert installed.count(P._XML_TOOL_CALL_BRIDGE_MARKER) == 1
    assert "from agent.scribe3_xml_tool_calls import extract_xml_tool_calls" in installed
    backups = list(loop.parent.glob("conversation_loop.py.bak.scribe3-xml-*"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == original

    assert P._sync_xml_tool_call_bridge(home, REPO, commit=True) == 0
    assert loop.read_text(encoding="utf-8") == installed
    assert len(list(loop.parent.glob("conversation_loop.py.bak.scribe3-xml-*"))) == 1


def test_xml_tool_call_bridge_refuses_unknown_hermes_source(home):
    """上游结构变动时必须失败，不得把“已安装”当成事实。"""
    loop = home / "hermes-agent" / "agent" / "conversation_loop.py"
    loop.parent.mkdir(parents=True)
    loop.write_text("from __future__ import annotations\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="锚点"):
        P._sync_xml_tool_call_bridge(home, REPO, commit=True)


def test_mcp_closed_resource_recovery_patch_is_semantic_idempotent_and_recoverable(home):
    """Hermes stdio 空消息 ClosedResourceError 必须进入既有重连重放路径。"""
    target = _write_mcp_v0182(home)
    original = target.read_text(encoding="utf-8")

    assert P._sync_mcp_closed_resource_recovery(home, commit=True) == 1

    spec = importlib.util.spec_from_file_location("patched_mcp_tool", target)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    from anyio import ClosedResourceError

    assert module._is_session_expired_error(ClosedResourceError()) is True
    assert module._is_session_expired_error(RuntimeError("")) is False
    backups = list(target.parent.glob("mcp_tool.py.bak.scribe3-closed-resource-*"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == original

    assert P._sync_mcp_closed_resource_recovery(home, commit=True) == 0
    assert len(list(target.parent.glob("mcp_tool.py.bak.scribe3-closed-resource-*"))) == 1


def test_mcp_closed_resource_recovery_dry_run_has_no_file_side_effects(home):
    """commit=False 只验证+报计划，不改源码、不建备份。"""
    target = _write_mcp_v0182(home)
    before = target.read_text(encoding="utf-8")

    assert P._sync_mcp_closed_resource_recovery(home, commit=False) == 1

    assert target.read_text(encoding="utf-8") == before
    assert list(target.parent.glob("mcp_tool.py.bak.scribe3-closed-resource-*")) == []


def test_mcp_closed_resource_recovery_missing_install_fails_loud(home):
    with pytest.raises(RuntimeError, match="找不到"):
        P._sync_mcp_closed_resource_recovery(home, commit=False)


@pytest.mark.parametrize("decoy", [
    P._MCP_CLOSED_RESOURCE_RECOVERY_MARKER + "\n",
    'detail = f"{type(exc).__name__}: {exc}".lower()\n',
])
def test_mcp_closed_resource_recovery_rejects_decoy_fixed_evidence(home, decoy):
    """marker/detail 在目标函数之外不得被当成已同步。"""
    _write_mcp_v0182(home, prefix=decoy)

    with pytest.raises(RuntimeError, match="位置|半补丁|结构"):
        P._sync_mcp_closed_resource_recovery(home, commit=False)


def test_mcp_closed_resource_recovery_rejects_duplicate_legacy_anchor(home):
    """全文出现第二个 legacy 块时拒绝只替换第一处。"""
    duplicate = '''def unrelated_duplicate(exc):
    msg = str(exc).lower()
    if not msg:
        return False
    return any(marker in msg for marker in _SESSION_EXPIRED_MARKERS)

'''
    _write_mcp_v0182(home, prefix=duplicate)

    with pytest.raises(RuntimeError, match="唯一|多处"):
        P._sync_mcp_closed_resource_recovery(home, commit=True)


def test_mcp_closed_resource_recovery_requires_closedresource_marker(home):
    _write_mcp_v0182(home, markers=("broken pipe", "end of file"))

    with pytest.raises(RuntimeError, match="closedresourceerror"):
        P._sync_mcp_closed_resource_recovery(home, commit=False)


@pytest.mark.parametrize("handler_retry_calls", [0, 2])
def test_mcp_closed_resource_recovery_preserves_exactly_one_retry_boundary(
        home, handler_retry_calls):
    """受管补丁只能依托 Hermes 现有的一次重放边界。"""
    _write_mcp_v0182(
        home,
        classifier=_FIXED_CLASSIFIER,
        handler_retry_calls=handler_retry_calls,
    )

    with pytest.raises(RuntimeError, match="单次重放|重连"):
        P._sync_mcp_closed_resource_recovery(home, commit=False)


def test_mcp_closed_resource_recovery_requires_classifier_control_flow_guard(home):
    """只调用分类器但忽略结果时，任意异常都会被重连重放，必须拒绝。"""
    _write_mcp_v0182(
        home,
        classifier=_FIXED_CLASSIFIER,
        handler_classifier_guard=False,
    )

    with pytest.raises(RuntimeError, match="guard|控制流|判定"):
        P._sync_mcp_closed_resource_recovery(home, commit=False)


def test_mcp_closed_resource_recovery_patch_refuses_unknown_hermes_source(home):
    """Hermes 上游键路变动时 fail-loud，不得盲改客户端生命周期。"""
    target = home / "hermes-agent" / "tools" / "mcp_tool.py"
    target.parent.mkdir(parents=True)
    target.write_text("def unrelated():\n    return True\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="锚点"):
        P._sync_mcp_closed_resource_recovery(home, commit=True)


def test_mcp_watchdog_parent_identity_tolerates_small_clock_drift_and_keeps_pid_reuse_guard(home):
    """同一 PPID 的 macOS create_time 小漂移不能误杀，明显差异仍须拦 PID 复用。"""
    target = _write_mcp_watchdog_v0182(home)
    original = target.read_text(encoding="utf-8")

    assert P._sync_mcp_watchdog_parent_identity(home, commit=True) == 1

    spec = importlib.util.spec_from_file_location("patched_mcp_watchdog", target)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class FakeProcess:
        def __init__(self, create_time):
            self._create_time = create_time

        def create_time(self):
            return self._create_time

    class FakePsutilError(Exception):
        pass

    def fake_psutil(actual_create_time):
        return SimpleNamespace(
            Error=FakePsutilError,
            pid_exists=lambda _pid: True,
            Process=lambda _pid: FakeProcess(actual_create_time),
        )

    module.psutil = fake_psutil(100.0)
    assert module._is_orphaned(123, 101.0, getppid=lambda: 123) is False
    assert module._is_orphaned(123, 100.0, getppid=lambda: 999) is True

    module.psutil = fake_psutil(110.0)
    assert module._is_orphaned(123, 100.0, getppid=lambda: 123) is True

    backups = list(target.parent.glob(
        "mcp_stdio_watchdog.py.bak.scribe3-parent-identity-*"
    ))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == original
    assert P._sync_mcp_watchdog_parent_identity(home, commit=True) == 0


def test_mcp_watchdog_parent_identity_dry_run_is_side_effect_free(home):
    target = _write_mcp_watchdog_v0182(home)
    before = target.read_text(encoding="utf-8")

    assert P._sync_mcp_watchdog_parent_identity(home, commit=False) == 1

    assert target.read_text(encoding="utf-8") == before
    assert not list(target.parent.glob(
        "mcp_stdio_watchdog.py.bak.scribe3-parent-identity-*"
    ))


def test_mcp_watchdog_parent_identity_accepts_upstream_guard_comments(home):
    """Hermes 0.18.2 的守卫分支含注释，语义验证不得因注释拒绝。"""
    commented = _LEGACY_WATCHDOG_IDENTITY.replace(
        "    if psutil is None:\n        return False",
        "    if psutil is None:\n"
        "        # No reliable staleness check available; fall back to ppid.\n"
        "        # This comment is part of the upstream Hermes source.\n"
        "        return False",
    )
    _write_mcp_watchdog_v0182(home, source=commented)

    assert P._sync_mcp_watchdog_parent_identity(home, commit=False) == 1


def test_mcp_watchdog_parent_identity_rejects_source_drift(home):
    drifted = _LEGACY_WATCHDOG_IDENTITY.replace(
        "if getppid() != original_ppid:",
        "if getppid() == original_ppid:",
    )
    _write_mcp_watchdog_v0182(home, source=drifted)

    with pytest.raises(RuntimeError, match="PPID|结构|锚点"):
        P._sync_mcp_watchdog_parent_identity(home, commit=True)


def test_provision_applies_watchdog_parent_identity_before_any_profile_write(
        home, monkeypatch):
    calls = []

    def racing_patch(_home, *, commit):
        calls.append(commit)
        if commit:
            raise RuntimeError("watchdog source drifted before commit")
        return 1

    monkeypatch.setattr(P, "_sync_mcp_watchdog_parent_identity", racing_patch)

    with pytest.raises(RuntimeError, match="watchdog source drifted"):
        P.provision(
            home,
            REPO,
            commit=True,
            profiles=("scribe3_write",),
            sync_crons=False,
            install_mcp_watchdog_parent_identity=True,
        )

    assert calls == [True]
    assert not (home / "profiles" / "scribe3_write" / "config.yaml").exists()


def test_cli_forwards_watchdog_parent_identity_install_flag(home, monkeypatch):
    captured = {}

    def fake_provision(_home, _repo, **kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(P, "provision", fake_provision)

    with pytest.raises(SystemExit) as exited:
        P.main([
            "--hermes-home", str(home),
            "--profile", "scribe3_write",
            "--skip-crons",
            "--install-mcp-watchdog-parent-identity",
        ])

    assert exited.value.code == 0
    assert captured["install_mcp_watchdog_parent_identity"] is True


def test_provision_applies_runtime_patch_before_any_profile_write(home, monkeypatch):
    """commit 阶段补丁验证失败时，profile 配置不得已经落盘。"""
    calls = []

    def racing_patch(_home, *, commit):
        calls.append(commit)
        if commit:
            raise RuntimeError("source drifted before commit")
        return 1

    monkeypatch.setattr(P, "_sync_mcp_closed_resource_recovery", racing_patch)

    with pytest.raises(RuntimeError, match="source drifted"):
        P.provision(
            home,
            REPO,
            commit=True,
            profiles=("scribe3_write",),
            sync_crons=False,
            install_mcp_closed_resource_recovery=True,
        )

    assert calls == [True]
    assert not (home / "profiles" / "scribe3_write" / "config.yaml").exists()


def test_provision_corrects_profile_env_port_without_touching_secrets(home):
    """Hermes 的 API_SERVER_PORT 环境变量优先于 YAML；必须由 provision 纠正。"""
    env = home / "profiles" / "scribe3_deduce" / ".env"
    env.parent.mkdir(parents=True)
    env.write_text("OPENAI_API_KEY=keep-private\nAPI_SERVER_PORT=8644\nOTHER=keep\n", encoding="utf-8")

    P.provision(home, REPO, commit=True)

    text = env.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=keep-private" in text
    assert "OTHER=keep" in text
    assert "API_SERVER_PORT=8645" in text
    assert "API_SERVER_PORT=8644" not in text


def test_provision_can_apply_only_preview_profile_without_cron_side_effects(home, monkeypatch):
    """Gate B 的增量部署不得顺带创建 cron 或改动既有 profile。"""
    cron_calls = []
    monkeypatch.setattr(P, "_sync_crons", lambda *_args, **_kwargs: cron_calls.append(True))

    result = P.provision(
        home, REPO, commit=True,
        profiles=("scribe3_deduce_preview",), sync_crons=False,
    )

    assert result["ok"] is True
    assert (home / "profiles/scribe3_deduce_preview/config.yaml").exists()
    assert not (home / "profiles/scribe3/config.yaml").exists()
    assert not (home / "profiles/scribe3_write/config.yaml").exists()
    assert not (home / "profiles/scribe3_deduce/config.yaml").exists()
    assert cron_calls == []


def test_preview_profile_physically_contains_only_deduce_read_mcp(home):
    """Hermes 会注册 config 中全部 MCP server，预览网关不能仅靠标签隔离。"""
    P.provision(home, REPO, commit=True,
                profiles=("scribe3_deduce_preview",), sync_crons=False)

    preview = _load(home, "profiles/scribe3_deduce_preview/config.yaml")

    assert set(preview["mcp_servers"]) == {"scribe3_deduce_read"}


def test_write_profile_overrides_existing_auto_tool_enforcement(home):
    """DeepSeek 写 profile 由 auto 升为 true，不能因 diff 漏掉 agent 而假装已同步。"""
    P.provision(home, REPO, commit=True, profiles=("scribe3_write",), sync_crons=False)
    target = home / "profiles" / "scribe3_write" / "config.yaml"
    before = _load(home, "profiles/scribe3_write/config.yaml")
    before["agent"]["tool_use_enforcement"] = "auto"
    before["providers"] = {"custom": {"api_key": "keep-private"}}
    target.write_text(yaml.safe_dump(before, allow_unicode=True), encoding="utf-8")

    P.provision(home, REPO, commit=True, profiles=("scribe3_write",), sync_crons=False)

    after = _load(home, "profiles/scribe3_write/config.yaml")
    assert after["agent"]["tool_use_enforcement"] is True
    assert after["providers"]["custom"]["api_key"] == "keep-private"


# ============================================================
# ② 安全不变量强制(写库前的硬门)
# ============================================================

def test_default_profile_zero_toolface_enforced(home):
    """默认 profile 若现有 config 误挂了 hermes-cli,provision 后必须被强制清空(U-006)。"""
    target = home / "config.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(
        {"platform_toolsets": {"api_server": ["hermes-cli"]}, "providers": {"x": {"key": "K"}}},
        allow_unicode=True), encoding="utf-8")
    P.provision(home, REPO, commit=True)
    after = _load(home, "config.yaml")
    assert after["platform_toolsets"]["api_server"] == []      # U-006 强制
    assert after["providers"] == {"x": {"key": "K"}}           # 密钥仍在


def test_invariant_blocks_write_if_reveal_tool_sneaks_in(home, monkeypatch):
    """若共享 mcp_servers.yaml 被人塞进一把 *_reveal 工具,_assert_invariants 必须拦下(U-003)。"""
    orig = P._build_overlay

    def poisoned(profile, repo):
        ov = orig(profile, repo)
        if "mcp_servers" in ov:
            server = next(iter(ov["mcp_servers"].values()))
            server["tools"]["include"].append("s3_list_factions_reveal")
        return ov
    monkeypatch.setattr(P, "_build_overlay", poisoned)

    res = P.provision(home, REPO, commit=True)
    assert res["ok"] is False
    # 拒绝写入:scribe3 profile 不该落盘
    assert not (home / "profiles" / "scribe3" / "config.yaml").exists()


def test_invariant_blocks_unknown_mcp_toolset_alias_before_profile_write(
        home, monkeypatch):
    """platform_toolsets 必须引用 mcp_servers 裸键，禁止不存在的 mcp-* 别名。"""
    orig = P._build_overlay

    def poisoned(profile, repo):
        overlay = orig(profile, repo)
        if profile == "scribe3_write":
            overlay["platform_toolsets"]["api_server"] = [
                "mcp-scribe3_read", "mcp-scribe3_write",
            ]
        return overlay

    monkeypatch.setattr(P, "_build_overlay", poisoned)

    result = P.provision(
        home,
        REPO,
        commit=True,
        profiles=("scribe3_write",),
        sync_crons=False,
    )

    assert result["ok"] is False
    assert not (home / "profiles/scribe3_write/config.yaml").exists()


# ============================================================
# ③ 白名单与 mcp.py 交叉校验(模板不许和真实工具漂移)
# ============================================================

def test_whitelists_match_mcp_reality():
    """deploy/hermes/mcp_servers.yaml 的 include 列表必须与 mcp.py 一致:
    · 每个工具在 mcp.py 真实存在(防手抄错字 / 删了工具没删模板)
    · 任何 include 里绝无 *_reveal(U-003 结构性保证)
    · scribe3_read 全是 readOnly 工具;scribe3_write 全是 WRITE_GATED 工具
    """
    import inspect
    import scribe3.mcp as M

    mcp_yaml = yaml.safe_load((P._DEPLOY_DIR / "mcp_servers.yaml").read_text(encoding="utf-8"))
    read_inc = mcp_yaml["scribe3_read"]["tools"]["include"]
    write_inc = mcp_yaml["scribe3_write"]["tools"]["include"]

    # 所有真实 @mcp.tool 名(FastMCP 注册的)——用模块属性判定
    existing = {n for n in dir(M) if n.startswith("s3_") and callable(getattr(M, n))}

    for t in read_inc + write_inc:
        assert t in existing, f"模板里的工具 {t} 在 mcp.py 不存在(手抄错 / 已删)"
        assert not t.endswith("_reveal"), f"{t} 是 *_reveal 全知工具,绝不可进任何白名单(U-003)"

    # 读写白名单互斥(同一把工具不该两边都挂)
    assert set(read_inc).isdisjoint(set(write_inc)), (
        f"读写白名单重叠: {set(read_inc) & set(write_inc)}")
    # 每个【需审批】的写工具(WRITE_GATED)都必须暴露在写网关——否则审批写链路缺工具。
    # (反过来不成立:写白名单还含 s3_save_chapter/s3_ingest_chapter 等免审批的写操作。)
    assert M.WRITE_GATED <= set(write_inc), (
        f"WRITE_GATED 写工具没全挂上写网关,缺: {M.WRITE_GATED - set(write_inc)}")
    # read 白名单不得混进任何需审批的写工具
    assert set(read_inc).isdisjoint(M.WRITE_GATED), (
        f"read 白名单混进了写工具: {set(read_inc) & M.WRITE_GATED}")


def test_structure_write_profile_can_read_chapter_and_volume_context():
    """建章/建卷种子先核实现状，写 profile 的只读面必须提供这两个真实工具。"""
    mcp_yaml = yaml.safe_load((P._DEPLOY_DIR / "mcp_servers.yaml").read_text(encoding="utf-8"))
    read_inc = set(mcp_yaml["scribe3_read"]["tools"]["include"])

    assert {"s3_list_chapters", "s3_list_volumes"} <= read_inc


# ============================================================
# ④ 幂等
# ============================================================

def test_idempotent(home):
    P.provision(home, REPO, commit=True)
    snap = {rel: (home / rel).read_text(encoding="utf-8")
            for rel in ("config.yaml", "profiles/scribe3/config.yaml",
                        "profiles/scribe3_write/config.yaml")}
    res2 = P.provision(home, REPO, commit=True)   # 再跑一次
    assert res2["ok"] is True
    for rel, text in snap.items():
        assert (home / rel).read_text(encoding="utf-8") == text, f"{rel} 第二次跑发生了变化,不幂等"


def test_soul_written_only_when_missing(home):
    # 新建:SOUL 应写入
    P.provision(home, REPO, commit=True)
    soul = home / "profiles" / "scribe3" / "SOUL.md"
    assert soul.exists() and "主编" in soul.read_text(encoding="utf-8")
    # 改动 SOUL 后再跑:不该被覆盖(保留用户调优)
    soul.write_text("我自己改过的身份", encoding="utf-8")
    P.provision(home, REPO, commit=True)
    assert soul.read_text(encoding="utf-8") == "我自己改过的身份"


def test_fresh_deploy_from_empty_home(home):
    """全新机器(HERMES_HOME 空):provision 应建出各阶段 profile 且满足最小权限。"""
    res = P.provision(home, REPO, commit=True)
    assert res["ok"] is True
    assert _load(home, "config.yaml")["platform_toolsets"]["api_server"] == []
    read = _load(home, "profiles/scribe3/config.yaml")
    assert read["platform_toolsets"]["api_server"] == ["scribe3_read"]
    assert read["agent"]["tool_use_enforcement"] is True
    w = _load(home, "profiles/scribe3_write/config.yaml")
    assert w["platform_toolsets"]["api_server"] == ["scribe3_read", "scribe3_write"]
    assert w["platforms"]["api_server"]["port"] == 8644
    assert w["mcp_discovery_timeout"] == 10.0
    # DeepSeek 不在 Hermes 的 auto tool-use enforcement 白名单中。写入 profile
    # 若保留 auto 会口头承诺调用 s3_* 却直接 completed，审批链永远不出现。
    assert w["agent"]["tool_use_enforcement"] is True
    deduce = _load(home, "profiles/scribe3_deduce/config.yaml")
    assert deduce["platform_toolsets"]["api_server"] == ["scribe3_deduce_read", "scribe3_deduce_write"]
    assert deduce["platforms"]["api_server"]["port"] == 8645
    assert deduce["mcp_discovery_timeout"] == 10.0
    assert deduce["agent"]["tool_use_enforcement"] is True
    assert deduce["mcp_servers"]["scribe3_deduce_write"]["tools"]["include"] == [
        "s3_patch_chapter_plan", "s3_generate_stage",
    ]
    preview = _load(home, "profiles/scribe3_deduce_preview/config.yaml")
    assert preview["platform_toolsets"]["api_server"] == ["scribe3_deduce_read"]
    assert preview["platforms"]["api_server"]["port"] == 8646
    # Qwen/TokenPlan 的 MCP schema 首次发现可能超过 Hermes 默认 1.5 秒；
    # 预览必须和成功的写入 profile 一样等待完成，否则模型只能把工具调用输出成文本。
    assert preview["mcp_discovery_timeout"] == 10.0
    assert preview["agent"]["tool_use_enforcement"] is True


# ============================================================
# ⑤ 后端启动守卫(_gateway_security_violations)——部署到任何地方的最后防线
# ============================================================

def _write(home, rel, cfg):
    import yaml as _y
    p = home / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_y.safe_dump(cfg, allow_unicode=True), encoding="utf-8")


def test_guard_flags_default_gateway_with_tools(home):
    import scribe3.app as A
    _write(home, "config.yaml", {"platform_toolsets": {"api_server": ["hermes-cli"]}})
    v = A._gateway_security_violations(home=home)
    assert any("默认网关" in x and "U-006" in x for x in v)


def test_guard_flags_reveal_tool_in_any_profile(home):
    import scribe3.app as A
    _write(home, "config.yaml", {"platform_toolsets": {"api_server": []}})
    _write(home, "profiles/scribe3/config.yaml", {
        "platform_toolsets": {"api_server": ["scribe3_read"]},
        "mcp_servers": {"scribe3_read": {"enabled": True,
                        "tools": {"include": ["s3_list_factions", "s3_list_factions_reveal"]}}}})
    v = A._gateway_security_violations(home=home)
    assert any("_reveal" in x and "U-003" in x for x in v)


def test_guard_clean_after_provision(home):
    """provision 后的配置(本测试自己 provision)守卫应零违规——闭环验证。"""
    import scribe3.app as A
    P.provision(home, REPO, commit=True)
    assert A._gateway_security_violations(home=home) == []


def test_assert_mcp_sdk_blocks_when_venv_cannot_import(home, tmp_path):
    venv_py = home / "hermes-agent" / "venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text("#!/bin/sh\nexit 1\n")
    venv_py.chmod(0o755)
    with pytest.raises(SystemExit, match="缺少 MCP SDK"):
        P._assert_mcp_sdk(home)


def test_assert_mcp_sdk_skips_without_venv(home):
    P._assert_mcp_sdk(home)


def test_guard_silent_when_config_absent(home):
    """全新机器还没 provision(config 读不到)→ 不误报(交给部署流程/运行时门禁)。"""
    import scribe3.app as A
    assert A._gateway_security_violations(home=home) == []

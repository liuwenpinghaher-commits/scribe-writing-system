"""provision_hermes:可复现 Hermes 网关配置叠加。全在临时 HERMES_HOME 里跑,绝不碰真 ~/.hermes。

重点:①深合并保密钥/Dashboard 键 ②安全不变量强制(默认零工具面 / 无 *_reveal)
③白名单与 mcp.py 交叉校验(工具真实存在 / read=readOnly / write=WRITE_GATED)④幂等。
"""
import copy

import pytest
import yaml

from scribe3.scripts import provision_hermes as P


@pytest.fixture
def home(tmp_path):
    return tmp_path / "hermes"


REPO = P._detect_repo()


def _load(home, rel):
    return yaml.safe_load((home / rel).read_text(encoding="utf-8"))


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
            ov["mcp_servers"]["scribe3_read"]["tools"]["include"].append("s3_list_factions_reveal")
        return ov
    monkeypatch.setattr(P, "_build_overlay", poisoned)

    res = P.provision(home, REPO, commit=True)
    assert res["ok"] is False
    # 拒绝写入:scribe3 profile 不该落盘
    assert not (home / "profiles" / "scribe3" / "config.yaml").exists()


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
    """全新机器(HERMES_HOME 空):provision 应建出三个 config 且满足所有不变量。"""
    res = P.provision(home, REPO, commit=True)
    assert res["ok"] is True
    assert _load(home, "config.yaml")["platform_toolsets"]["api_server"] == []
    assert _load(home, "profiles/scribe3/config.yaml")["platform_toolsets"]["api_server"] == ["scribe3_read"]
    w = _load(home, "profiles/scribe3_write/config.yaml")
    assert w["platform_toolsets"]["api_server"] == ["scribe3_read", "scribe3_write"]
    assert w["platforms"]["api_server"]["port"] == 8644


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


def test_guard_silent_when_config_absent(home):
    """全新机器还没 provision(config 读不到)→ 不误报(交给部署流程/运行时门禁)。"""
    import scribe3.app as A
    assert A._gateway_security_violations(home=home) == []

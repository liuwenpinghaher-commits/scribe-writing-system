"""可复现地把 scribe3 拥有的 Hermes 网关配置叠加进 ~/.hermes(部署到任何地方都一致)。

背景/设计见 scribe3/deploy/hermes/README.md。一句话:三个 profile 的网关配置此前全靠手动
配在部署机上、一行不在 git;本脚本把 scribe3【拥有】的那部分(platform_toolsets 安全不变量 /
mcp_servers 工具白名单 / 端口 / 主编身份)纳入 git,幂等叠加进 ~/.hermes,密钥与 Dashboard
管的键原样保留。

关键性质:
- **叠加(深合并),不整文件覆写**:overlay 里只有 scribe3 拥有的键 → 深合并只动这些键,
  providers/secrets/model/skills/cron 等(密钥 + Dashboard 管)天然不被触碰。
- **幂等**:现状已合模板 → dry-run 显示零变更;可反复跑。
- **机器路径参数化**:mcp_servers.command 的 {{RUN_MCP}} 按 --repo 替换成绝对路径。
- **默认 dry-run**:只打印将改什么;--commit 才真写,且先备份 .bak.<ms>。
- **安全不变量强制**:写库前断言默认 profile 零工具面 + 任何 include 无 *_reveal;不满足则
  拒绝写入(fail-closed)。

用法:
  python -m scribe3.scripts.provision_hermes                 # dry-run(缺省 ~/.hermes + 自动探测 repo)
  python -m scribe3.scripts.provision_hermes --commit        # 真写
  HERMES_HOME=/tmp/h python -m scribe3.scripts.provision_hermes --repo /path/to/repo --commit
"""
from __future__ import annotations

import argparse
import copy
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

# 安全不变量常量(与 mcp.py / app._summarize_hermes_runtime 的门禁同源语义)
REVEAL_SUFFIX = "_reveal"

_DEPLOY_DIR = Path(__file__).resolve().parent.parent / "deploy" / "hermes"
# profile → (overlay 文件, 目标 config 相对 HERMES_HOME 的路径, 是否注入共享 mcp_servers, SOUL 模板)
_PROFILES = {
    "default": ("overlay.default.yaml", "config.yaml", False, None),
    "scribe3": ("overlay.scribe3.yaml", "profiles/scribe3/config.yaml", True, "SOUL.scribe3.md"),
    "scribe3_write": ("overlay.scribe3_write.yaml", "profiles/scribe3_write/config.yaml", True,
                      "SOUL.scribe3_write.md"),
}


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """把 overlay 深合并进 base 的副本:dict 递归合并,其它类型(含 list)直接被 overlay 覆盖。
    list 覆盖而非追加是刻意的——工具白名单 / platform_toolsets 要精确强制(删掉的工具要真消失)。"""
    out = copy.deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _run_mcp_path(repo: Path) -> str:
    return str(repo / "scribe3" / "run_mcp.sh")


def _build_overlay(profile: str, repo: Path) -> dict:
    overlay_file, _, inject_mcp, _ = _PROFILES[profile]
    overlay = _load_yaml(_DEPLOY_DIR / overlay_file)
    if inject_mcp:
        mcp = _load_yaml(_DEPLOY_DIR / "mcp_servers.yaml")
        run_mcp = _run_mcp_path(repo)
        for server in mcp.values():
            if isinstance(server, dict) and server.get("command") == "{{RUN_MCP}}":
                server["command"] = run_mcp
        overlay["mcp_servers"] = mcp
    return overlay


def _assert_invariants(profile: str, merged: dict) -> list[str]:
    """返回违规列表(空=通过)。这些是【写库前】的硬门,不满足则拒绝写(fail-closed)。"""
    violations = []
    if profile == "default":
        api = ((merged.get("platform_toolsets") or {}).get("api_server")) or []
        if api:
            violations.append(f"默认 profile 的 api_server 工具面非空({api})——速答不得挂任何工具(U-006)")
    # 任何 profile:mcp server 的 include 里绝无 *_reveal(U-003)
    for sname, server in (merged.get("mcp_servers") or {}).items():
        if not isinstance(server, dict):
            continue
        include = (((server.get("tools") or {}) if isinstance(server.get("tools"), dict) else {})
                   .get("include")) or []
        reveal = [t for t in include if str(t).endswith(REVEAL_SUFFIX)]
        if reveal:
            violations.append(f"{sname}.include 含 *_reveal 全知工具({reveal})——挂网关即泄密(U-003)")
    return violations


def _diff_keys(before: dict, after: dict, prefix="") -> list[str]:
    """只报 scribe3 关心的键的变化(平铺路径),不刷屏整份 config。"""
    changes = []
    owned = ("platform_toolsets", "platforms", "mcp_servers", "fallback_providers")
    keys = owned if prefix == "" else sorted(set(before) | set(after))
    for k in keys:
        b, a = before.get(k), after.get(k)
        if b == a:
            continue
        path = f"{prefix}{k}"
        if isinstance(b, dict) and isinstance(a, dict):
            changes.extend(_diff_keys(b, a, path + "."))
        elif isinstance(b, list) and isinstance(a, list):
            added = [x for x in a if x not in b]
            removed = [x for x in b if x not in a]
            parts = []
            if added:
                parts.append("+" + ", ".join(map(str, added)))
            if removed:
                parts.append("-" + ", ".join(map(str, removed)))
            changes.append(f"  {path}: {'; '.join(parts) if parts else f'{b!r} → {a!r}'}")
        else:
            changes.append(f"  {path}: {b!r} → {a!r}")
    return changes


def provision(hermes_home: Path, repo: Path, *, commit: bool) -> dict:
    if not _DEPLOY_DIR.exists():
        raise SystemExit(f"模板目录不存在: {_DEPLOY_DIR}")
    run_mcp = Path(_run_mcp_path(repo))
    print(f"  HERMES_HOME: {hermes_home}")
    print(f"  repo:        {repo}")
    print(f"  run_mcp.sh:  {run_mcp}  {'✅存在' if run_mcp.exists() else '⚠不存在(路径对不对?)'}")
    print(f"  模式:        {'COMMIT(真写)' if commit else 'DRY-RUN(只看不写)'}")
    print("  " + "=" * 60)

    total_changes = 0
    all_ok = True
    for profile, (_, rel, _, soul_tpl) in _PROFILES.items():
        target = hermes_home / rel
        before = _load_yaml(target)
        overlay = _build_overlay(profile, repo)
        after = _deep_merge(before, overlay)

        violations = _assert_invariants(profile, after)
        if violations:
            all_ok = False
            print(f"  ❌ [{profile}] 安全不变量违规,拒绝写入:")
            for v in violations:
                print(f"       {v}")
            continue

        changes = _diff_keys(before, after)
        soul_change = _soul_status(hermes_home, rel, soul_tpl)
        if not changes and not soul_change:
            print(f"  ✅ [{profile}] 已合模板,无变更(幂等)")
            continue
        total_changes += len(changes)
        print(f"  · [{profile}] {target}")
        for c in changes:
            print(c)
        if soul_change:
            print(f"    {soul_change}")

        if commit:
            if before:   # 已存在才备份(空=新建无可备)
                bak = target.with_suffix(target.suffix + f".bak.{int(time.time() * 1000)}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, bak)
                print(f"    备份 → {bak.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(yaml.safe_dump(after, allow_unicode=True, sort_keys=False),
                              encoding="utf-8")
            _write_soul_if_missing(hermes_home, rel, soul_tpl)
            print("    ✅ 已写入")

    _sync_crons(hermes_home, commit=commit)

    print("  " + "=" * 60)
    if not all_ok:
        print("  ⛔ 存在安全不变量违规,未全部写入。修模板后重跑。")
        return {"ok": False}
    if commit:
        print("  ✅ provision 完成。")
    else:
        print(f"  DRY-RUN:共 {total_changes} 处将变更。加 --commit 真写。")
    return {"ok": True, "changes": total_changes}


def _sync_crons(hermes_home: Path, *, commit: bool) -> None:
    """P2:cron 任务声明式同步(deploy/hermes/crons.yaml + scripts/)。

    幂等纪律:按 name 匹配——`hermes cron list` 里已存在的任务绝不动(可能有用户手工调优);
    只创建缺失的。脚本拷到 ~/.hermes/scripts/(--no-agent 哨兵:空 stdout=静默,失败才响)。
    dry-run 零副作用(不 subprocess、不写文件),测试可安全跑。"""
    cfg = _load_yaml(_DEPLOY_DIR / "crons.yaml")
    jobs = (cfg or {}).get("jobs") or []
    if not jobs:
        return
    scripts_src = _DEPLOY_DIR / "scripts"
    if not commit:
        for j in jobs:
            print(f"  · [cron] 计划(dry-run):{j['name']} @ {j['schedule']} script={j['script']}")
        return
    # 1) 脚本落位(内容一致即跳过)
    sdir = hermes_home / "scripts"
    for f in sorted(scripts_src.glob("*.sh")):
        tgt = sdir / f.name
        if tgt.exists() and tgt.read_text(encoding="utf-8") == f.read_text(encoding="utf-8"):
            print(f"  ✅ [cron脚本] {f.name} 已同步")
            continue
        sdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, tgt)
        tgt.chmod(0o755)
        print(f"  ✅ [cron脚本] {f.name} 已写入")
    # 2) 任务注册(name 幂等;list 失败如实报,不静默跳过)
    try:
        existing = subprocess.run(["hermes", "cron", "list"], capture_output=True,
                                  text=True, timeout=30).stdout
    except Exception as e:
        print(f"  ❌ hermes cron list 失败({e})——脚本已就位,任务需手动 create(命令见 crons.yaml)")
        return
    for j in jobs:
        name = j["name"]
        if name in existing:
            print(f"  ✅ [cron] {name} 已存在(幂等跳过,不覆盖)")
            continue
        cmd = ["hermes", "cron", "create", j["schedule"], "--name", name,
               "--script", j["script"], "--deliver", j.get("deliver", "local")]
        if j.get("no_agent", True):
            cmd.append("--no-agent")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            print(f"  ❌ [cron] {name} 创建失败:{(r.stderr or r.stdout).strip()[:200]}")
        else:
            print(f"  ✅ [cron] {name} 已创建({j['schedule']})")


def _soul_dir(hermes_home: Path, rel: str) -> Path:
    return (hermes_home / rel).parent


def _soul_status(hermes_home: Path, rel: str, soul_tpl: str | None) -> str:
    if not soul_tpl:
        return ""
    dst = _soul_dir(hermes_home, rel) / "SOUL.md"
    if dst.exists():
        return ""   # 不覆盖既有身份(可能有你的调优)
    return f"SOUL.md 缺失 → 将写入主编身份模板({soul_tpl})"


def _write_soul_if_missing(hermes_home: Path, rel: str, soul_tpl: str | None) -> None:
    if not soul_tpl:
        return
    dst = _soul_dir(hermes_home, rel) / "SOUL.md"
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_DEPLOY_DIR / soul_tpl, dst)


def _detect_repo() -> Path:
    # 本文件在 <repo>/scribe3/scripts/provision_hermes.py
    return Path(__file__).resolve().parent.parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser(description="叠加 scribe3 Hermes 网关配置(可复现部署)")
    ap.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
    ap.add_argument("--repo", default=None, help="scribe3 repo 根(缺省自动探测)")
    ap.add_argument("--commit", action="store_true", help="真写(缺省 dry-run)")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _detect_repo()
    res = provision(Path(args.hermes_home).expanduser(), repo, commit=args.commit)
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()

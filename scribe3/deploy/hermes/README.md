# scribe3 Hermes 网关配置(可复现部署)

**问题**:此前三个 Hermes 网关 profile 的全部配置(工具白名单、`platform_toolsets`、
端口、主编身份)都手动配在部署机的 `~/.hermes/` 里,**一行都不在 git**。换机器 / 重装
Hermes / 部署到别处,就得手动重建——U-006(速答网关误挂终端工具面能跑 git)只是你会漏掉
的其中一项(台账 U-006)。

**方案**:把 scribe3 **拥有**的那部分网关配置纳入 git,用 `provision_hermes.py`
幂等地叠加进 `~/.hermes`。部署 = 跑一次 provision = 配置在任何地方都正确。

## 为什么是「叠加(overlay)」而不是「整文件模板」

一个 Hermes profile config 有 60-74 个顶层键,混着三类东西:

| 类别 | 例子 | 归属 | 本方案怎么处理 |
|---|---|---|---|
| **scribe3 拥有** | `platform_toolsets` / `mcp_servers`(工具白名单)/ `platforms`(端口) | 本 repo | **模板化 + 强制**(overlay 里,provision 时覆盖同名键) |
| **密钥** | `providers` 的 API key / `secrets` / `.env` | 部署机,**绝不进 git** | **原样保留**(overlay 里根本没有这些键,深合并不碰它们) |
| **Dashboard 管的** | `model` / `model_catalog` / `auxiliary` / `skills` / `cron` | Hermes 官方 Dashboard | **原样保留**(同上) |

所以 provision 是**深合并**:overlay 的键覆盖,其余全留。密钥和 Dashboard 配置天然不受
影响——因为 overlay 文件里压根没有那些键。

## 部署顺序(deploy anywhere)

```bash
# 1. 装 Hermes,用官方 Dashboard 配好 providers/模型(密钥、机器相关——Hermes 的事)
# 2. 叠加 scribe3 网关配置(本方案;--repo 缺省=自动探测本 repo 位置)
scribe3/.venv/bin/python -m scribe3.scripts.provision_hermes            # dry-run 先看
scribe3/.venv/bin/python -m scribe3.scripts.provision_hermes --commit   # 真写(自动备份)
# 3. 起三个网关(launchd/systemd/docker,OS 相关——见 DEPLOY.md)
# 4. 起后端;启动守卫会校验安全不变量,配置不对就响亮报错
```

## 文件

- `overlay.default.yaml` — 默认 profile(:8642 速答/渲染/判官):**零工具面**(U-006 不变量)。
- `overlay.scribe3.yaml` — 读 profile(:8643 agentic 只读):挂 scribe3_read。
- `overlay.scribe3_write.yaml` — 写 profile(:8644 Runs/审批):挂 scribe3_read + scribe3_write。
- `mcp_servers.yaml` — 两个 scribe3 profile **共享**的 MCP server 定义(工具白名单单一真相源;
  `{{RUN_MCP}}` 由 provision 按本 repo 位置替换成绝对路径)。
- `SOUL.scribe3.md` / `SOUL.scribe3_write.md` — 主编身份(仅在目标不存在时写,不覆盖你的调优)。

## 安全不变量(provision 强制 + 测试钉死 + 启动守卫复核)

1. 默认 profile `platform_toolsets.api_server == []`(速答不得有任何工具 → 防跑 git/终端,U-006)。
2. 任何 profile 的任何 mcp server `tools.include` **绝无** `*_reveal` 全知孪生工具(U-003)。
3. read include 全是 readOnly 工具;write include 全是 WRITE_GATED 工具(与 mcp.py 交叉校验)。

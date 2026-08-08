# Demo 部署机磁盘卫生

> 机型约 **40G** 系统盘。验收只打已部署栈，但仍会因 **Docker 构建层** 与 **部署临时文件** 涨满。

## 现象与根因

| 堆积物 | 典型体积 | 根因 |
|--------|----------|------|
| Docker `<none>` 悬空镜像 | 数 GB～10G+ | `compose up --build` 每次重建 backend/frontend，旧镜像失去 tag 却不删 |
| BuildKit cache | 1～3G | 多次 build 未 `builder prune` |
| `/tmp/scribe3-*.tgz`、`web-src.tgz` | 数 MB～百 MB | `deploy_demo.sh` scp 后未删除 |
| `/tmp/scribe3-web-verify` 等 | 数百 MB | 临时验证目录未清 |
| `app/scribe3/web/node_modules` | ~400MB | `frontend` 模式 `npm ci` 落在宿主机挂载目录且构建后未删 |

**不是**业务 Surreal 数据卷（demo 上数据相对小）。

## 正常路径（应优先）

| 模式 | 是否易堆镜像 | 说明 |
|------|----------------|------|
| `./scripts/deploy_demo.sh hot` | 否 | 只热更 Python 源码 |
| `./scripts/deploy_demo.sh frontend` | 低 | `docker run --rm node` 构建；脚本会删 `node_modules` + 清 tarball + 轻 prune |
| `./scripts/deploy_demo.sh full` | **高** | `compose --build`；`deploy.sh` 成功后 **必须** image/builder prune |
| GHA / 手工反复 build | **高** | 同上 |

## 一键清理

```bash
# 从开发机
./scripts/deploy_demo.sh prune

# 或在 demo 上
docker image prune -f
docker builder prune -f
rm -f /tmp/web-src.tgz /tmp/scribe3-hot.tgz /tmp/scribe3-deploy.tgz
rm -rf /opt/scribe3/app/scribe3/web/node_modules
```

**不要**默认 `docker system prune -a`：会删掉未在跑、但仍可能要回滚的 tag 镜像。

## 脚本已内置的防护（2026-08）

1. `deploy/prod/scripts/deploy.sh`：健康检查通过（及失败收尾）后 `image prune` + `builder prune`，并删 deploy tarball。  
2. `scripts/deploy_demo.sh frontend`：`npm run build` 后 `rm -rf node_modules`；删 `/tmp/web-src.tgz`；轻 prune。  
3. `scripts/deploy_demo.sh hot`：重启后删 `/tmp/scribe3-hot.tgz`。  
4. `scripts/deploy_demo.sh prune`：人工卫生入口。  

## 监控建议

```bash
ssh ubuntu@82.157.130.140 'df -h /; docker system df; docker images -f dangling=true -q | wc -l'
```

- `/` 使用率 **>85%**：先 `prune` 再部署。  
- dangling 镜像 **>20**：说明有人在走 full/compose build 且 prune 未跑通。  

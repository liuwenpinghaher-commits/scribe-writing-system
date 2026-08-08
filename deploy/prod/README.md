# scribe3 生产部署（腾讯云轻量）

目标机示例：`ubuntu@82.157.130.140`（Ubuntu 24.04，Docker 已装）。

## 架构

```text
浏览器 → :80 nginx(frontend)
            ├─ /        SPA
            └─ /api/*   → backend:3321 → SurrealDB(surrealkv)
                              ↓ 172.18.0.1 (docker bridge)
                         Hermes :8642 / :8643 / :8644（宿主机 systemd）
```

- 代码与 compose：`/opt/scribe3/app`
- 数据：`/opt/scribe3/data/{surreal,settings,backups}`
- **主部署（默认）**：开发机执行 `./scripts/deploy_demo.sh`（SSH 热更 backend，**不依赖 GitHub Actions**）
- **支路（可选）**：Actions `deploy-lighthouse` 仅 `workflow_dispatch` 手动触发；挂了不影响日常上线

## 本机 SSH 注意

若本机开了代理/VPN（常见 `utun0` + `198.18.0.0/15`），直连会卡在 SSH banner。绕过示例：

```bash
# 绑定到局域网网卡 IP（ifconfig en0）
ssh -b 192.168.101.114 -i ~/Downloads/gro01_openssh.pem -o IdentitiesOnly=yes ubuntu@82.157.130.140
```

私钥需 OpenSSH 格式；腾讯云下载的 PKCS#1 PEM 可用：

```bash
cp gro01.pem gro01_openssh.pem
chmod 600 gro01_openssh.pem
ssh-keygen -p -f gro01_openssh.pem -N '' -P ''
```

密码登录在绑定密钥后通常被禁用，以密钥为准。

## 首次上线清单

### 1. 服务器 bootstrap

```bash
# 在已能 SSH 登录的机器上
sudo bash -c 'apt-get update && apt-get install -y git'
# 若私有仓：先给 ubuntu 配 deploy key 或 HTTPS token
sudo git clone https://github.com/liuwenpinghaher-commits/scribe-writing-system.git /opt/scribe3/app
sudo chown -R ubuntu:ubuntu /opt/scribe3
cd /opt/scribe3/app
sudo bash deploy/prod/scripts/bootstrap_server.sh
```

### 2. 配置 `.env`

```bash
cp deploy/prod/.env.example deploy/prod/.env
# 编辑 SURREAL_PASS、API_SERVER_KEY、PUBLIC_HOST 等
chmod 600 deploy/prod/.env
```

### 3. 起栈

```bash
bash deploy/prod/scripts/deploy.sh
# 打开 http://82.157.130.140/
curl -fsS http://127.0.0.1/api/health
```

### 4. 迁本地数据

开发机：

```bash
bash deploy/prod/scripts/export_local_data.sh
# 产出 /tmp/scribe3-cloud-migrate-*.tgz
scp -b <LAN_IP> -i <key> /tmp/scribe3-cloud-migrate-*.tgz ubuntu@82.157.130.140:/tmp/
```

服务器：

```bash
bash /opt/scribe3/app/deploy/prod/scripts/import_data.sh /tmp/scribe3-cloud-migrate-XXXX.tgz
```

### 5. Hermes 全栈

```bash
bash /opt/scribe3/app/deploy/prod/scripts/install_hermes.sh
# Linux 上容器访问宿主机网关：绑 Docker 网桥（非 127.0.0.1）
# systemd drop-in 示例：Environment=API_SERVER_HOST=172.18.0.1
# deploy/prod/.env 中 HERMES_* 指向 http://172.18.0.1:8642|8643|8644/v1
sudo systemctl restart hermes-gateway hermes-gateway-scribe3 hermes-gateway-scribe3-write
docker compose -f deploy/prod/docker-compose.yml --env-file deploy/prod/.env up -d backend
curl -fsS http://127.0.0.1/api/gateway/status
```

当前实例已验证：`default/responses/runs` 三网关 `online:true`；deduce 系列未装可忽略。

### 6. 日常部署（主路径，不经 GitHub Actions）

在开发机 / Grok 工作区（能 SSH 到 demo）：

```bash
# 推荐：Python backend 热更（轻量、不 rebuild 镜像）
./scripts/deploy_demo.sh
# 或
./scripts/deploy_demo.sh hot

# 服务器能 git fetch 时：pull origin/main 后热应用
./scripts/deploy_demo.sh server-git

# 改了 Dockerfile/compose/前端构建时：整树 + compose rebuild（重）
./scripts/deploy_demo.sh full
```

默认：`DEPLOY_HOST=82.157.130.140`，`SSH_KEY=~/.ssh/id_tencent_lh`。

**不依赖** `git push`、**不依赖** Actions 分钟数 / Runner。GitHub 不通时照常上线。

### 7. GitHub Actions 支路（可选，手动）

`deploy-lighthouse` **已取消 push 自动触发**，仅 Actions 页 **Run workflow**。  
需要 secrets 时再配；缺省可完全不用。

| Secret | 含义 |
|--------|------|
| `DEPLOY_HOST` | `82.157.130.140` |
| `DEPLOY_USER` | `ubuntu` |
| `DEPLOY_SSH_KEY` | runner→服务器私钥全文 |
| `DEPLOY_PORT` | 可选，默认 22 |

## 日常

```bash
# 主路径：本机热更
./scripts/deploy_demo.sh

# 服务器上仅重建 compose（已有代码时）
bash /opt/scribe3/app/deploy/prod/scripts/deploy.sh

# 日志
docker compose -f /opt/scribe3/app/deploy/prod/docker-compose.yml --env-file /opt/scribe3/app/deploy/prod/.env logs -f --tail=100
journalctl -u hermes-gateway -u hermes-gateway-scribe3 -u hermes-gateway-scribe3-write -f
```

## 安全建议

- 修改默认 `SURREAL_PASS`，DB **不要**映射到公网
- 生产考虑设置 `SCRIBE3_API_TOKEN` 并在前端带 Bearer
- 防火墙只开 22/80/443；Hermes 端口仅监听 `127.0.0.1`
- 密钥与 `.env` 永不进 git


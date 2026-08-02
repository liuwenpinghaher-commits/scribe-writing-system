# scribe3 生产部署（腾讯云轻量）

目标机示例：`ubuntu@82.157.130.140`（Ubuntu 24.04，Docker 已装）。

## 架构

```text
浏览器 → :80 nginx(frontend)
            ├─ /        SPA
            └─ /api/*   → backend:3321 → SurrealDB(surrealkv)
                              ↓ host.docker.internal
                         Hermes :8642 / :8643 / :8644（宿主机 systemd）
```

- 代码与 compose：`/opt/scribe3/app`
- 数据：`/opt/scribe3/data/{surreal,settings,backups}`
- 自动更新：GitHub Actions `deploy-lighthouse` 在 `push main` 后 SSH 到服务器执行 `deploy.sh`（**不经开发者本机**）

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
# 确认 8642/8643/8644
docker compose -f deploy/prod/docker-compose.yml --env-file deploy/prod/.env restart backend
```

### 6. GitHub Actions 自动部署

在 GitHub 仓库 Settings → Secrets and variables → Actions 添加：

| Secret | 含义 |
|--------|------|
| `DEPLOY_HOST` | `82.157.130.140` |
| `DEPLOY_USER` | `ubuntu` |
| `DEPLOY_SSH_KEY` | 服务器 `authorized_keys` 对应的**私钥**全文 |
| `DEPLOY_PORT` | 可选，默认 22 |
| `DEPLOY_REPO_DIR` | 可选，默认 `/opt/scribe3/app` |

服务器需能 `git fetch` 私有仓：给 `ubuntu` 配 read-only deploy key，或 `gh auth` / credential。

之后每次 `git push origin main`，Actions 在云端 SSH 执行 `deploy.sh`。

## 日常

```bash
# 仅更新代码/镜像
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


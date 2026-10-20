# L1 认证与多用户隔离规格（Scribe3）

**状态**: 已定稿并与实现同步  
**公开入口**: `https://tonglu.example.com`（旧 `www.example.com` / `example.com` 301），同源 SPA + `/api`  
**隔离档位**: **L1** — 单进程、同一 Surreal、按 `owner_user_id` 逻辑隔离  

---

## 1. 目标

1. 公网打开写作系统时，**先通过人机登录门禁**（用户名 + 密码），不得以「粘贴 `SCRIBE3_API_TOKEN`」为产品主路径。  
2. 浏览器会话使用服务端签发的 **HttpOnly Cookie**，不把长期共享 API 密钥写入 `localStorage` 作为主闸。  
3. 同一部署内多名作者 **逻辑隔离**：用户 A 只能列出/创建/打开/变更自己的作品（work slug）；用户 B 不能列出或读写 A 的作品。  
4. 不引入每用户容器 / 每用户独立 Surreal 实例（非 L2/L3）。  
5. **管理台（admin）**：角色 `admin` 可在 UI/API 增删改查账号、跨账号管理书籍归属、查看操作审计；普通 `author` 不可访问 `/admin/*`。

---

## 2. 登录与会话模型

### 2.1 启用条件

| 环境变量 | 含义 |
|----------|------|
| `SCRIBE3_AUTH_ENABLED=1` | 开启会话门禁；**未登录访问受保护 API → 401** |
| `SCRIBE3_SESSION_SECRET` | 签名会话 Cookie 的密钥（启用时必填，生产强随机） |
| `SCRIBE3_BOOTSTRAP_USERS` | 首次启动灌库：`user1:pass1,user2:pass2`（仅当用户表为空时写入，密码以 PBKDF2 哈希落库） |
| `SCRIBE3_LEGACY_OWNER` | 无 `owner_user_id` 的历史作品视同归属该用户名（默认 `admin`） |
| `SCRIBE3_API_TOKEN` | **可选、次要**：机器/CLI 的 Bearer；**不是**浏览器登录 UX |

未设 `SCRIBE3_AUTH_ENABLED` 时：保持历史行为（本地/单测默认可直接访问），便于开发与存量测试。

### 2.2 HTTP 契约

| 方法路径 | 未登录 | 说明 |
|----------|--------|------|
| `POST /auth/login` | 放行 | body: `{ "username", "password" }`；成功 `Set-Cookie: s3_session=...` |
| `POST /auth/logout` | 放行 | 清除 Cookie |
| `GET /auth/me` | 401 或 200 | 当前用户 `{ "username" }` |
| `GET /health` `/ready` | 放行 | 探活，无敏感数据 |
| **其余应用 API** | **401**（启用时） | 需有效会话 **或** 合法机器 Bearer |

### 2.3 Cookie 规则

- 名称: `s3_session`  
- 属性: `HttpOnly`；生产建议 `Secure`（`SCRIBE3_SESSION_SECURE=1` 或 HTTPS 推断）；`SameSite=Lax`；`Path=/`  
- 载荷: 签名的 `username` + `exp`（HMAC-SHA256），TTL 默认 7 天（`SCRIBE3_SESSION_TTL_HOURS`）  
- 前端请求: `credentials: 'include'`（同源 `/api`）  
- **禁止**将 `SCRIBE3_API_TOKEN` 作为登录表单主字段；SSE 优先依赖 Cookie，不再把共享密钥挂在 `?token=` 作为主路径

### 2.4 密码

- 存储: `pbkdf2_sha256$<salt>$<hex>`（stdlib，无额外依赖）  
- 校验: 恒定时间比较  
- 登录失败: 401，不区分「用户不存在 / 密码错误」的细节枚举（统一文案）

---

## 3. L1 作品归属与隔离

### 3.1 数据模型

- 仍为一书一 Surreal DB：`NS=scribe3 / DB=<slug>`  
- 注册表 `scribe3/_reg` 表 `work` 增加字段 **`owner_user_id`**（字符串，对应用户 username）  
- 不新建 per-user 进程或 per-user NS

### 3.2 规则

| 操作 | 规则 |
|------|------|
| **列出** `GET /works`、`GET /works/archived` | 仅返回 `effective_owner(work) == 当前用户` |
| **创建** `POST /works` | 写入 `owner_user_id = 当前用户` |
| **重命名 / 废弃 / 恢复 / 永久删除** `/works/{slug}...` | 必须拥有该 slug，否则 **403** |
| **任意 `?work=<slug>` 业务 API** | 必须拥有该 slug，否则 **403**；不存在可 **404** |
| **省略 `?work=` 的业务 API** | 与 handler 一致回落 `SCRIBE3_WORK`/`main`，**仍做归属校验**（禁止靠省略绕过） |
| **全局路由**（`/works` 列表/创建、`/settings*`、`/auth*`、`/health`、`/capabilities`、`/gateway*`、`/ai/runtime-status`） | 不做单书归属；列表结果仍按 owner 过滤 |
| **工作域 AI 路由**（`/ai/runs*`、`/ai/usage` 等带 `work` 的） | **按 effective work 做归属**（与 `/entities` 相同；禁止靠前缀白名单绕过） |
| **历史无 owner 的作品** | `effective_owner = owner_user_id or SCRIBE3_LEGACY_OWNER`（默认 `admin`） |

### 3.3 失败语义

- 未登录: **401** `{ "detail": "authentication required" }`（或等价）  
- 已登录但非所有者: **403** `{ "detail": "work access denied" }`  
- 不因「猜 slug」而把他人作品混入列表

### 3.4 非目标（明确不做）

- L2：每用户独立 Surreal NS/DB 容器  
- L3：每用户独立后端容器  
- OAuth/OIDC/SSO、Cloudflare Access、Authelia（可作为外围文档可选层，非本规格必达）  
- 组织/团队/RBAC（仅 owner）  
- 自动迁移全部历史书到多用户以外的复杂策略（仅 legacy owner 归属）  
- Hermes/MCP 进程内多租户完整绑定（HTTP L1 为门禁验收线；MCP 残留风险见下）

---

## 4. 架构位置（实现约束）

```
Browser (tonglu.example.com)
  → nginx (TLS, / + /api)
    → FastAPI
         Auth middleware (session cookie | machine bearer)
         Ownership gate (work query /works/{slug})
         Handlers → store registry (owner_user_id) → per-work DB
```

- 纯函数（密码、会话签发/解析、归属判定）可单测，不依赖 UI。  
- 会话用户通过 contextvar 注入 `list_works` / `create_work`，避免改动全部 endpoint 签名。  
- `SCRIBE3_API_TOKEN` 仅机器路径；浏览器主路径为 Cookie。

---

## 5. 前端

- 登录页：用户名 + 密码 → `POST /auth/login`（`credentials: 'include'`）  
- 启动：`GET /auth/me`；失败进登录页  
- `fetch` 包装：默认 `credentials: 'include'`；401 → 登录；**不再**以 `localStorage` 的 API token 为主闸  
- 域名: 生产 Cookie 面向 `tonglu.example.com` 同源部署（旧主域仅 301）

---

## 6. 生产引导

1. 设置 `SCRIBE3_AUTH_ENABLED=1`、`SCRIBE3_SESSION_SECRET`（长随机）、`SCRIBE3_BOOTSTRAP_USERS=admin:<强密码>`  
2. 历史单租户书无 owner 时，将管理员用户名与 `SCRIBE3_LEGACY_OWNER` 对齐（默认 `admin`）  
3. 仅暴露 443；backend/Surreal/Hermes 不对公网  
4. 可选：保留 `SCRIBE3_API_TOKEN` 给运维脚本，勿写入前端构建产物  

---

## 7. 验收对照

| 规格条 | 验收 |
|--------|------|
| 会话登录非 token 粘贴 | 登录 API + 前端为 username/password |
| 无会话拒绝 | 受保护 API → 401 |
| A/B 隔离 | A 列表不含 B 的 work；B 访问 A 的 slug → 403 |
| L1 同进程 | 无 per-user 容器；owner 在注册表 |
| 公开域 | 文档与部署假设 `tonglu.example.com` |

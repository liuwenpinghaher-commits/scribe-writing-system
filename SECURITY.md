# 安全策略 (Security Policy)

## 1. 支持版本 (Supported Versions)

目前铜炉写作系统 (`scribe-writing-system` / `scribe3`) 仅对主线 `main` 分支（基于 SurrealDB 3.2.x + FastAPI + React 19 的 `scribe3` 架构）提供安全更新支持：

| 版本 / 分支 | 支持状态 |
| :--- | :--- |
| `main` (`scribe3` v3.x) | ✅ 支持 (Supported) |
| 历史归档 (`scribe` / `scribe2`) | ❌ 已停止维护 (Deprecated) |

---

## 2. 核心安全机制

1. **运行轨迹凭据自动脱敏（At-Rest Trace Redaction）**：
   - `scribe3` 在将 AI 运行轨迹（`tool_outputs`、`raw_events`、`error`）写入 SurrealDB 前，会自动通过 `context_security` 脱敏器剥离所有 `Authorization: Bearer`、`Basic`、`Proxy-Authorization`、`api_key`、`sk-*` 令牌，以及作品世界观中标记为 `secret=True` 的未公开事实真值，确保数据库中永不落盘明文密钥。
2. **会话门禁与机器令牌分离（L1 Auth Isolation）**：
   - 公网或多人部署时，通过 `SCRIBE3_AUTH_ENABLED=1` 启用基于 `HttpOnly` + `SameSite=Lax` + HMAC-SHA256 签名 Cookie 的会话鉴权，密码采用 PBKDF2 哈希存储，严禁在前端构建产物或 URL 查询参数中暴露 `SCRIBE3_API_TOKEN`。
3. **写门控与跨租户作品隔离**：
   - 默认关闭紧急未审批 REST 写接口（`SCRIBE3_EMERGENCY_REST_WRITE=0`），设定变更须经过可追溯的审批提案流（Proposal & Approval Audit）。
   - 所有携带或省略 `?work=` 参数的 API 均执行作品归属校验，防止越权访问。
4. **本地回环默认绑定**：
   - 开发与 E2E 测试默认仅绑定 `127.0.0.1` 回环地址，不向公网暴露 SurrealDB (`:8000`/`:8001`) 或内部推理网关端口。

---

## 3. 报告安全漏洞 (Reporting a Vulnerability)

如果你在仓库中发现了潜在的安全漏洞（例如鉴权绕过、跨作品越权、Prompt 秘密泄露或凭据脱敏遗漏）：

1. **请勿在公开的 GitHub Issue 中直接披露漏洞利用细节。**
2. 请通过 GitHub 仓库的 **Security Advisories -> Report a vulnerability** 私密通道提交报告，或联系仓库维护者（`liuwenpinghaher-commits`）。
3. 报告请包含：
   - 漏洞所在模块、文件与复现步骤；
   - 影响范围评估（如是否涉及未授权读写或凭据泄露）；
   - 建议的修复方案（如有）。
4. 维护者将在收到报告后 **72 小时内** 确认受理，并在修复补丁与回归测试合并后公开致谢。

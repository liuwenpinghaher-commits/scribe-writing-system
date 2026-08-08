# 发版 / 热更冒烟清单（demo）

> 每次 push 部署或热更 backend/Hermes 后勾选。  
> 验证对象 = **已部署 demo**，不另起栈。

## 必跑（H3）

```bash
# 1) 应用 + Surreal
./scripts/smoke_s32.sh
# 或 demo: /home/ubuntu/smoke_s32.sh

# 2) Hermes 三网关
./scripts/smoke_hermes_gateways.sh
# 或 demo: /home/ubuntu/smoke_hermes_gateways.sh

# 3) 分档不变量
./scripts/check_hermes_tiers.sh
```

| # | 检查 | 通过 |
|---|------|------|
| R1 | smoke_s32 全绿 | |
| R2 | smoke_hermes 全绿，8642 tools=[] | |
| R3 | check_hermes_tiers 三档 timeout/comp/tools | |
| R4 | 三 unit active | |

## 改动相关（按需）

| 改动类型 | 加跑 |
|----------|------|
| Surreal / store | `probe_s32_hotpath` 或 memory_e2e（可选） |
| 备份相关 | `backup_surreal_demo` + 两阶段 restore 抽样 |
| write/SSE | API 一次 `/chat/write`（需 context 三件套） |

## 安全不变量（永远）

- 8642 `platform_toolsets.api_server == []`
- 8643 仅 `scribe3_read`
- 8644 `scribe3_read` + `scribe3_write`
- 剧情记忆不进 Hermes memory

## 参考

- Hermes 分档：`docs/ops/hermes-h0-h1-runbook.md`
- Surreal 3.2：`docs/ops/surrealdb-3.2.4-runbook.md`
- 验收总表：`docs/ops/s32-acceptance-checklist.md`

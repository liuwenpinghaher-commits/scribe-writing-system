# 发版 / 热更冒烟清单（demo）· 铜炉 tonglu

> 每次 push 部署或热更 backend/Hermes 后勾选。  
> 验证对象 = **已部署 demo**，不另起栈。  
> **Smoke 只证明主路径在跑**，不钉死小版本，不替代深度回归。  
> 产品名 **铜炉** / 拼音 **tonglu**；路径中的 `scribe3` 为历史兼容，见 `docs/brand/README.md`。

## 必跑（存活）

```bash
./scripts/smoke_s32.sh                 # 应用 + 库 + 登录 + 作品 API
./scripts/smoke_hermes_gateways.sh     # 三网关 models + 短 completion
```

| # | 检查 | 通过标准 |
|---|------|----------|
| R1 | smoke_s32 | exit 0：ready/health/登录/works/chapters/codex |
| R2 | smoke_hermes | exit 0：三 unit + models + 8642 completion |

## 可选（配置卫生，非存活）

```bash
./scripts/check_hermes_tiers.sh        # 工具面安全 + 推荐分档（数值默认仅 NOTE）
STRICT_TIERS=1 ./scripts/check_hermes_tiers.sh   # 数值也必须与推荐表一致时才用
```

| # | 检查 | 说明 |
|---|------|------|
| R3 | tiers | **默认**：8642 无写工具等安全项才 fail；timeout/comp 不一致只 NOTE |
| R4 | 版本号 | **不作为 fail 条件**；smoke 里仅打印参考 |

## 改动相关（按需加深）

| 改动类型 | 加跑 |
|----------|------|
| Surreal / store | probe / memory_e2e（可选） |
| write/SSE | 一次带 context 的 `/chat/write` |
| 备份 | export + 两阶段 restore 抽样 |

## 安全（产品不变量，不是「暂时不做」）

- 8642 速答 **不应** 暴露写库/终端工具面（`STRICT_TOOLS=1` 默认检查）  
- 写世界仍走 8644 + 审批  
- 剧情记忆在 Surreal，不靠 Hermes memory  

「暂时不做语音」等 **不写进 smoke fail 条件**。

## 参考

- Hermes 分档：`docs/ops/hermes-h0-h1-runbook.md`  
- Surreal：`docs/ops/surrealdb-3.2.4-runbook.md`  

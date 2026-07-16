# Scribe3 E2E 测试

两档结构(设计见 `docs/superpowers/specs/2026-07-16-e2e骨架重建-design.md`)。

## 确定性档(每次 PR / CI 自动)

六类失效模式的负路径回归,真打端点/SSE/组装/检测器/store,只 mock LLM 边界。秒级、不烧网关。

```bash
scribe3/.venv/bin/python -m pytest scribe3/tests/e2e -q   # 或 make e2e-det
```

覆盖:①静默降级 / ②写了读不到 / ③限知泄露 / ④工具面越界 / ⑤集成断裂 / ⑥失忆。

## 前端 L2 冒烟(CI 自动 / 本地 `make e2e-frontend`)

独立临时后端(临时 surreal,绝不碰生产),验证前端真机链路通 + 零 console 崩。

```bash
make e2e-frontend        # = scripts/e2e_ci.sh
```

**生产保护**:3311/3321 被占用时 fail-loud 拒绝运行(防误连本机生产后端把测试书写进生产库)。

## 真调档(nightly / 本地 `make e2e-real`)

真起前后端 + 真 Hermes 网关,走完整写作旅程。断言结构/链路/护栏到界面/字数,不钉正文内容。

```bash
make e2e-real            # 需本机 Hermes 网关(:8643/:8644)+ 端口 3311/3321 空闲
```

公共 CI 无凭证跑不了真调,见 `.github/workflows/nightly.yml`(留 self-hosted 接口)。

## 文件

- `lib.mjs` — Playwright 真机操作(从 `pw.mjs` 提炼,两档共用)
- `frontend_smoke.mjs` — L2 前端冒烟(确定性,不调 LLM)
- `full_journey.mjs` — 真调档完整旅程(真网关)

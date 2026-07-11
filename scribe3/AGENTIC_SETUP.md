# scribe3 主编 agentic 网关搭建(可复现)

完整 agentic 主编需要两个**独立的 scribe3 Hermes 网关**:读网关负责普通联查/讨论,写网关负责会改状态的 Runs + Approval。它们与用户主网关(default profile,:8642)隔离。本文记录搭建步骤——profile 配置在 `~/.hermes/`
仓库外,故在此存档。

## 架构

```
前端 :3311 → scribe3 后端 :3321 ──/chat/agentic-stream── scribe3 read  :8643 /v1/responses
                            └────/ai/runs────────────── scribe3 write :8644 /v1/runs
                                                             ↓
                          scribe3 MCP(stdio, run_mcp.sh)── s3_* 工具
                                                             ↓
                                          SurrealDB :8001 (NS=scribe3, db=<work>)
```

- **速答模式**(lite)走 default :8642 `/chat/completions`(纯 LLM,无工具),无需本网关。
- **联查实证模式**(agentic)走 :8643 `/v1/responses`,profile 只暴露 `scribe3_read`。
- **写入审批模式**(Runs)走 :8644 `/v1/runs`,profile 暴露 `scribe3_read + scribe3_write`。

## 搭建步骤

1. **scribe3 MCP 启动脚本**(已在仓库):[run_mcp.sh](run_mcp.sh) —— cd 仓库根 + `scribe3/.venv/bin/python -m scribe3.mcp`(连已运行的 :8001,不 spawn surreal,故中文路径 panic 坑无关)。

2. **建 profile**(若无):`hermes profile create scribe3`;`hermes profile create scribe3_write`。

3. **profile config**(`~/.hermes/profiles/scribe3/config.yaml`)挂 MCP,并把 API server 工具面限定为只读:
   ```yaml
   mcp_servers:
     scribe3_read:
       command: "/Users/miaoma/Downloads/写作 3.0/scribe3/run_mcp.sh"
       enabled: true
       tools:
         include: [s3_list_works, ...]
         resources: false
         prompts: false
     scribe3_write:
       command: "/Users/miaoma/Downloads/写作 3.0/scribe3/run_mcp.sh"
       enabled: true
       tools:
         include: [s3_save_chapter, ...]
         resources: false
         prompts: false
   platform_toolsets:
     api_server: [scribe3_read]
   ```

4. **写 profile config**(`~/.hermes/profiles/scribe3_write/config.yaml`)复用同一 MCP,但 API server 工具面包含读 + 写:
   ```yaml
   platform_toolsets:
     api_server: [scribe3_read, scribe3_write]
   ```

5. **profile .env 端口**—— **.env 的 `API_SERVER_PORT` 覆盖 config.yaml**,必须同改:
   ```
   # ~/.hermes/profiles/scribe3/.env
   API_SERVER_PORT=8643

   # ~/.hermes/profiles/scribe3_write/.env
   API_SERVER_PORT=8644
   ```
   (`API_SERVER_KEY` 与 default 相同,后端 `llm._api_key()` 读 `~/.hermes/.env` 即可复用。)

6. **起网关**:`hermes -p scribe3 gateway run --replace`;`hermes -p scribe3_write gateway run --replace`(后台常驻)。验证:
   - `hermes -p scribe3 mcp test scribe3_read` → 连接成功。
   - `hermes -p scribe3_write mcp test scribe3_write` → 连接成功。
   - `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8643/v1/models` → 401(up,需鉴权)。
   - `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8644/v1/models` → 401(up,需鉴权)。

7. **profile SOUL.md(稳定层身份,H-06)**——`~/.hermes/profiles/scribe3/SOUL.md` 与
   `~/.hermes/profiles/scribe3_write/SOUL.md` 已从默认 Hermes 人格换成 scribe3 主编身份
   + 恒定纪律(剧情事实只进 SurrealDB、s3_ 工具必带 work、写入必待批)。写盘即对新会话
   生效,无需重启网关。注意:章/相位级写作纪律**不放这里**——那些留在每请求 instructions
   (doubao 无 prompt cache 收益,且要保住末尾 recency 强化)。

8. **体检**:`scribe3/scripts/hermes_smoke.sh`(只读)/ `--live`(烧 1 笔)一键验证三网关
   健康、capabilities、skills、cron;升级演练流程见 `HERMES_UPGRADE_EVAL.md`。

## 已知边界

- **多书 work**:s3_ 工具必须显式传 `work`;后端会在 instructions 注入当前 work 硬约束。
- **写工具走 elicitation 待批**:agentic 流里主编调写工具(s3_add_* 等)会触发审批;非交互上下文 fail-closed(不写),只读工具不受影响。

## 真机验证(2026-06-23)

问「列未回收伏笔」→ 主编自调 `s3_list_promises` → 取回真实 17 伏笔,按章节(第0章世界法则…第5章还丹)+ 类型(人物承诺/悬念/契诃夫之枪)作答。端到端通。
